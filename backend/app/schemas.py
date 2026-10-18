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