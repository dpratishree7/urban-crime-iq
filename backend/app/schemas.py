from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class LookupRequest(BaseModel):
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    community_area: int | None = Field(None, ge=1, le=77)

    @model_validator(mode="after")
    def check_inputs(self):
        has_point = self.latitude is not None or self.longitude is not None
        if has_point and self.community_area is not None:
            raise ValueError("Send either latitude and longitude, or community_area, not both")
        if has_point and (self.latitude is None or self.longitude is None):
            raise ValueError("latitude and longitude must be sent together")
        if not has_point and self.community_area is None:
            raise ValueError("Send latitude and longitude, or community_area")
        return self


class LookupResponse(BaseModel):
    mode: str
    community_area: int | None
    area_name: str | None
    latitude: float
    longitude: float
    cluster: int
    risk_level: str
    top_crime_type: str
    distance_to_centre_km: float
    centre_lat: float
    centre_lon: float
    note: str

class ForecastRequest(BaseModel):
    community_area: int = Field(ge=1, le=77)
    days: int = Field(7, ge=1, le=7)


class PredictedDay(BaseModel):
    date: str
    predicted_crimes: float


class ActualDay(BaseModel):
    date: str
    crimes: int


class ForecastResponse(BaseModel):
    community_area: int
    area_name: str
    data_as_of: str
    days: int
    forecast: list[PredictedDay]
    recent_actuals: list[ActualDay]
    model_mae_all_areas: float
    note: str

VALID_DISTRICTS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20,
                   22, 24, 25, 31}          # the 23 districts in the warehouse (/api/meta)


class ViolenceRequest(BaseModel):
    hour: int = Field(ge=0, le=23)
    domestic: bool
    day_of_week: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"]
    location_group: Literal["COMMERCIAL", "OTHER", "RESIDENTIAL", "SCHOOL", "STREET", "TRANSPORT"]
    community_area: int = Field(ge=1, le=77)
    district: int

    @field_validator("district")
    @classmethod
    def check_district(cls, v):
        if v not in VALID_DISTRICTS:
            raise ValueError(f"district {v} does not exist; valid districts: {sorted(VALID_DISTRICTS)}")
        return v


class ViolenceResponse(BaseModel):
    probability_violent: float
    prediction: str
    threshold: float
    average_violent_share_pct: float
    relative_to_average: float
    model_accuracy_pct: float
    model_precision_violent_pct: float
    model_recall_violent_pct: float
    note: str

class Rule(BaseModel):
    conditions: dict[str, str]
    outcome: str
    support_pct: float
    confidence_pct: float
    lift: float
    meaning: str


class PatternsResponse(BaseModel):
    chosen: dict[str, str]
    matched: int
    returned: int
    rules: list[Rule]
    districts_with_rules: list[str]
    settings: dict
    message: str
    note: str