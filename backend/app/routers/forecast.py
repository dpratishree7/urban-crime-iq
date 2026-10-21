import pandas as pd
from fastapi import APIRouter, HTTPException

from ..model_store import store
from ..schemas import ActualDay, ForecastRequest, ForecastResponse, PredictedDay

router = APIRouter(prefix="/api", tags=["forecast"])


def _model_mae() -> float:
    """Test-set MAE of the saved model, for the 'typical error' shown with the forecast."""
    for m in store.regression["metrics"]:
        if m["model"] == "Linear regression: + census + weather":
            return round(float(m["MAE"]), 2)
    return float("nan")


@router.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if req.community_area not in store.census.index:
        raise HTTPException(404, f"Unknown community area {req.community_area}")
    try:
        actual, preds = store.forecast(req.community_area, req.days)
    except Exception as exc:
        raise HTTPException(503, f"Could not build the forecast right now: {exc}")

    name = str(store.census.loc[req.community_area, "area_name"])
    recent = actual.tail(30)
    return ForecastResponse(
        community_area=req.community_area,
        area_name=name,
        data_as_of=str(store.data_as_of.date()),
        days=req.days,
        forecast=[PredictedDay(date=str(d.date()), predicted_crimes=round(p, 1))
                  for d, p in preds],
        recent_actuals=[ActualDay(date=str(d.date()), crimes=int(v))
                        for d, v in recent.items()],
        model_mae_all_areas=_model_mae(),
        note=("Expected daily crimes for this area, starting the day after the last day "
              "in our data. Later days use earlier predictions, so accuracy falls with "
              "distance. Weather is the monthly historical average, not a weather "
              "forecast. The typical error (MAE) is per area per day, measured on 2025 "
              "to 2026 test data for next-day predictions."),
    )