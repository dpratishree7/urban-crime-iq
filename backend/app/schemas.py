from pydantic import BaseModel


class Area(BaseModel):
    id: int
    name: str


class MetaResponse(BaseModel):
    years: list[int]
    months: list[int]
    seasons: list[str]
    districts: list[int]
    community_areas: list[Area]
    crime_types: list[str]
    crime_groups: list[str]
    location_groups: list[str]


class SummaryResponse(BaseModel):
    total_crimes: int
    top_crime_type: str
    top_crime_type_count: int
    arrest_rate_pct: float
    violent_share_pct: float
    date_from: str
    date_to: str


class LevelRow(BaseModel):
    label: str
    crimes: int


class RollupResponse(BaseModel):
    level: str
    filters: dict
    rows: list[LevelRow]


class DrilldownResponse(BaseModel):
    hierarchy: str
    from_level: str
    from_value: str
    next_level: str
    rows: list[LevelRow]


class TypeRow(BaseModel):
    crime_type: str
    crimes: int
    arrests: int
    arrest_rate_pct: float


class SliceResponse(BaseModel):
    filters: dict
    total_crimes: int
    total_arrests: int
    arrest_rate_pct: float
    by_crime_type: list[TypeRow]


class AreaRate(BaseModel):
    community_area: int
    area_name: str
    population: int
    crimes: int
    crimes_per_1000: float


class TopAreasResponse(BaseModel):
    filters: dict
    rows: list[AreaRate]


class HeatCell(BaseModel):
    day_of_week: int          # 0 = Monday
    hour: int
    crimes: int


class HeatmapResponse(BaseModel):
    filters: dict
    cells: list[HeatCell]

class Cluster(BaseModel):
    cluster: int
    centre_lat: float
    centre_lon: float
    sample_size: int
    share_pct: float
    top_crime_type: str
    top_crime_share_pct: float
    risk_level: str


class HotspotsResponse(BaseModel):
    k: int
    sample_total: int
    risk_basis: str
    note: str
    clusters: list[Cluster]