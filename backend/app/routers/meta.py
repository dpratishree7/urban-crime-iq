from fastapi import APIRouter
from sqlalchemy import text

from ..db import engine
from ..schemas import Area, MetaResponse, SummaryResponse

router = APIRouter(prefix="/api", tags=["meta"])


def _column(conn, sql: str) -> list:
    return [row[0] for row in conn.execute(text(sql))]


@router.get("/meta", response_model=MetaResponse)
def meta():
    with engine.connect() as conn:
        areas = conn.execute(text(
            "SELECT DISTINCT community_area, area_name FROM dim_location "
            "ORDER BY community_area")).all()
        return MetaResponse(
            years=_column(conn, "SELECT DISTINCT year FROM dim_date ORDER BY year"),
            months=list(range(1, 13)),
            seasons=["WINTER", "SPRING", "SUMMER", "FALL"],
            districts=_column(conn, "SELECT DISTINCT district FROM dim_location ORDER BY district"),
            community_areas=[Area(id=a[0], name=a[1]) for a in areas],
            crime_types=_column(conn, "SELECT DISTINCT primary_type FROM dim_crime_type ORDER BY primary_type"),
            crime_groups=_column(conn, "SELECT DISTINCT crime_group FROM dim_crime_type ORDER BY crime_group"),
            location_groups=_column(conn, "SELECT DISTINCT location_group FROM dim_location_type ORDER BY location_group"),
        )


@router.get("/summary", response_model=SummaryResponse)
def summary():
    with engine.connect() as conn:
        total, arrests, violent = conn.execute(text(
            "SELECT SUM(crime_count), SUM(arrest_count), "
            "SUM(CASE WHEN is_violent THEN crime_count ELSE 0 END) "
            "FROM mv_crime_summary")).one()
        top_type, top_count = conn.execute(text(
            "SELECT primary_type, SUM(crime_count) AS n FROM mv_crime_summary "
            "GROUP BY primary_type ORDER BY n DESC LIMIT 1")).one()
        d_from, d_to = conn.execute(text(
            "SELECT MIN(full_date), MAX(full_date) FROM dim_date")).one()
    total, arrests, violent = int(total), int(arrests), int(violent)
    return SummaryResponse(
        total_crimes=total,
        top_crime_type=top_type,
        top_crime_type_count=int(top_count),
        arrest_rate_pct=round(arrests * 100 / total, 1),
        violent_share_pct=round(violent * 100 / total, 1),
        date_from=str(d_from),
        date_to=str(d_to),
    )