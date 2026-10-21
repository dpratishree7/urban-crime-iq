from fastapi import APIRouter

from ..model_store import store
from ..schemas import ViolenceRequest, ViolenceResponse

router = APIRouter(prefix="/api/predict", tags=["violence"])

THRESHOLD = 0.5


def _tree_metrics() -> dict:
    """Test-set metrics of the saved tree (and the majority-class baseline)."""
    out = {}
    for m in store.tree["metrics"]:
        if m["model"].startswith("Baseline"):
            out["baseline"] = m
        elif m["model"].startswith("Decision Tree"):
            out["tree"] = m
    return out


@router.post("/violence", response_model=ViolenceResponse)
def predict_violence(req: ViolenceRequest):
    p = store.predict_violence(
        hour=req.hour, domestic=int(req.domestic), day_of_week=req.day_of_week,
        season=req.season, location_group=req.location_group,
        community_area=req.community_area, district=req.district)

    metrics = _tree_metrics()
    # the baseline accuracy is the non-violent share of the test set
    average_violent = 1.0 - float(metrics["baseline"]["accuracy"])
    tree = metrics["tree"]

    return ViolenceResponse(
        probability_violent=round(p, 3),
        prediction="violent" if p >= THRESHOLD else "non-violent",
        threshold=THRESHOLD,
        average_violent_share_pct=round(average_violent * 100, 1),
        relative_to_average=round(p / average_violent, 2),
        model_accuracy_pct=round(float(tree["accuracy"]) * 100, 1),
        model_precision_violent_pct=round(float(tree["precision_violent"]) * 100, 1),
        model_recall_violent_pct=round(float(tree["recall_violent"]) * 100, 1),
        note=("Screening estimate from time, place and whether the incident was "
              "domestic; it is not a verdict about any real incident. About a third of "
              "all recorded incidents are violent, so a probability near that average "
              "means the inputs add little information. The model catches only part of "
              "all violent incidents (see recall), so a low probability does not mean "
              "an incident is safe. Incidents with a default timestamp were excluded "
              "from training."),
    )