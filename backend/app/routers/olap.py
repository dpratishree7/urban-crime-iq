from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from ..db import engine
from ..schemas import (AreaRate, DrilldownResponse, HeatCell, HeatmapResponse, LevelRow,
                       RollupResponse, SliceResponse, TopAreasResponse, TypeRow)

router = APIRouter(prefix="/api/olap", tags=["olap"])

Season = Literal["WINTER", "SPRING", "SUMMER", "FALL"]
Level = Literal["year", "month", "day", "hour", "city", "district", "beat"]

# ---- two data sources: the small summary view, or the full fact table ----
MV = {
    "from": "mv_crime_summary m",
    "crimes": "SUM(m.crime_count)",
    "arrests": "SUM(m.arrest_count)",
    "cols": {"year": "m.year", "month": "m.month", "season": "m.season",
             "district": "m.district", "crime_type": "m.primary_type"},
}
FACT = {
    "from": ("fact_crime f JOIN dim_date d ON d.date_key = f.date_key "
             "JOIN dim_location l ON l.location_key = f.location_key "
             "JOIN dim_crime_type c ON c.crime_type_key = f.crime_type_key"),
    "crimes": "COUNT(*)",
    "arrests": "SUM(f.arrest::int)",
    "cols": {"year": "d.year", "month": "d.month", "season": "d.season",
             "district": "l.district", "crime_type": "c.primary_type",
             "day": "d.full_date", "hour": "f.hour", "beat": "l.beat"},
}
FACT_ONLY = {"day", "hour", "beat"}          # levels the summary view cannot answer

LABEL = {
    "year": "{year}::text",
    "month": "{year}::text || '-' || LPAD({month}::text, 2, '0')",
    "day": "{day}::text",
    "hour": "{hour}::text",
    "city": "'Chicago'",
    "district": "{district}::text",
    "beat": "{beat}",
}
SORT = {
    "year": "{year}", "month": "{year} * 100 + {month}", "day": "{day}",
    "hour": "{hour}", "district": "{district}", "beat": "{beat}",
}
TIME_NEXT = {"year": "month", "month": "day", "day": "hour"}
PLACE_NEXT = {"city": "district", "district": "beat"}


def get_filters(
    year: list[int] | None = Query(None),
    month: list[int] | None = Query(None),
    district: list[int] | None = Query(None),
    crime_type: list[str] | None = Query(None),
    season: list[Season] | None = Query(None),
) -> dict:
    raw = {"year": year, "month": month, "district": district,
           "crime_type": crime_type, "season": season}
    return {k: v for k, v in raw.items() if v}


def build_where(cols: dict, filters: dict):
    parts, params = [], {}
    for name, value in filters.items():              # names come from our own dicts
        parts.append(f"{cols[name]} = ANY(:{name})")
        params[name] = value
    return (" WHERE " + " AND ".join(parts)) if parts else "", params


def run_level(level: str, filters: dict) -> list[LevelRow]:
    src = FACT if (level in FACT_ONLY or "day" in filters) else MV
    cols = src["cols"]
    where, params = build_where(cols, filters)
    label = LABEL[level].format(**cols)
    sql = f"SELECT {label} AS label, {src['crimes']} AS crimes FROM {src['from']}{where}"
    if level != "city":
        sort = SORT[level].format(**cols)
        sql += f" GROUP BY {sort}, {label} ORDER BY {sort}"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).all()
    return [LevelRow(label=str(r.label), crimes=int(r.crimes or 0)) for r in rows]


@router.get("/rollup", response_model=RollupResponse)
def rollup(level: Level, filters: dict = Depends(get_filters)):
    return RollupResponse(level=level, filters=filters, rows=run_level(level, filters))


@router.get("/drilldown", response_model=DrilldownResponse)
def drilldown(hierarchy: Literal["time", "place"], level: Level, value: str = "",
              filters: dict = Depends(get_filters)):
    nxt = (TIME_NEXT if hierarchy == "time" else PLACE_NEXT).get(level)
    if nxt is None:
        raise HTTPException(400, f"'{level}' has no lower level in the {hierarchy} hierarchy")
    try:
        if hierarchy == "time" and level == "year":
            extra = {"year": [int(value)]}
        elif hierarchy == "time" and level == "month":
            y, m = value.split("-")
            extra = {"year": [int(y)], "month": [int(m)]}
        elif hierarchy == "time" and level == "day":
            extra = {"day": [date.fromisoformat(value)]}
        elif level == "city":
            extra = {}
        else:                                              # place, district
            extra = {"district": [int(value)]}
    except ValueError:
        raise HTTPException(400, f"Invalid value '{value}' for level '{level}'")
    merged = {**filters, **extra}                          # the clicked value wins
    return DrilldownResponse(hierarchy=hierarchy, from_level=level, from_value=value,
                             next_level=nxt, rows=run_level(nxt, merged))


def _pct(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


@router.get("/slice", response_model=SliceResponse)
def slice_(filters: dict = Depends(get_filters)):
    where, params = build_where(MV["cols"], filters)
    sql = ("SELECT m.primary_type AS crime_type, SUM(m.crime_count) AS crimes, "
           "SUM(m.arrest_count) AS arrests FROM mv_crime_summary m"
           f"{where} GROUP BY m.primary_type ORDER BY crimes DESC")
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).all()
    by_type = [TypeRow(crime_type=r.crime_type, crimes=int(r.crimes), arrests=int(r.arrests),
                       arrest_rate_pct=_pct(int(r.arrests), int(r.crimes))) for r in rows]
    total = sum(r.crimes for r in by_type)
    arrests = sum(r.arrests for r in by_type)
    return SliceResponse(filters=filters, total_crimes=total, total_arrests=arrests,
                         arrest_rate_pct=_pct(arrests, total), by_crime_type=by_type)


@router.get("/top-areas", response_model=TopAreasResponse)
def top_areas(limit: int = Query(10, ge=1, le=77), min_population: int = Query(0, ge=0),
              filters: dict = Depends(get_filters)):
    where, params = build_where(FACT["cols"], filters)
    sql = ("SELECT l.community_area, l.area_name, MAX(l.population) AS population, "
           "COUNT(*) AS crimes, "
           "ROUND(COUNT(*) * 1000.0 / MAX(l.population), 1) AS crimes_per_1000 "
           f"FROM {FACT['from']}{where} "
           "GROUP BY l.community_area, l.area_name "
           "HAVING MAX(l.population) >= :min_population "
           "ORDER BY crimes_per_1000 DESC LIMIT :limit")
    params.update(min_population=min_population, limit=limit)
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).all()
    return TopAreasResponse(filters=filters, rows=[
        AreaRate(community_area=r.community_area, area_name=r.area_name,
                 population=int(r.population), crimes=int(r.crimes),
                 crimes_per_1000=float(r.crimes_per_1000)) for r in rows])


@router.get("/heatmap", response_model=HeatmapResponse)
def heatmap(filters: dict = Depends(get_filters)):
    where, params = build_where(FACT["cols"], filters)
    sql = ("SELECT d.day_of_week AS dow, f.hour AS hour, COUNT(*) AS crimes "
           f"FROM {FACT['from']}{where} GROUP BY d.day_of_week, f.hour")
    with engine.connect() as conn:
        found = {(r.dow, r.hour): int(r.crimes) for r in conn.execute(text(sql), params)}
    cells = [HeatCell(day_of_week=d, hour=h, crimes=found.get((d, h), 0))
             for d in range(7) for h in range(24)]
    return HeatmapResponse(filters=filters, cells=cells)