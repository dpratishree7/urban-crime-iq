from typing import Literal

from fastapi import APIRouter, Query

from ..model_store import store
from ..schemas import PatternsResponse, Rule

router = APIRouter(prefix="/api", tags=["patterns"])

Outcome = Literal["THEFT", "BATTERY", "ALL OTHER"]

ORDER = ["district", "is_weekend", "location_group", "time_of_day", "season"]
PHRASES = {
    "time_of_day": {"MORNING": "in the morning", "AFTERNOON": "in the afternoon",
                    "EVENING": "in the evening", "NIGHT": "at night"},
    "is_weekend": {"weekday": "on weekdays", "weekend": "on weekends"},
}
OUTCOME_TEXT = {"THEFT": "theft crimes", "BATTERY": "battery crimes",
                "ALL OTHER": "in the 'all other' crime group"}


def phrase(key: str, value: str) -> str:
    if key == "district":
        return f"in district {int(value[1:])}"
    if key == "location_group":
        return f"at {value.lower()} locations"
    if key == "season":
        return f"in {value.lower()}"
    return PHRASES[key][value]


def describe(rule: dict) -> str:
    c = rule["conditions"]
    parts = [phrase(k, c[k]) for k in ORDER if k in c]
    return (f"{rule['confidence'] * 100:.0f}% of recorded crimes {' '.join(parts)} are "
            f"{OUTCOME_TEXT[rule['outcome']]}, {rule['lift']:.1f} times as often as "
            f"across all crimes.")


@router.get("/patterns", response_model=PatternsResponse)
def patterns(
    district: str | None = Query(None, pattern=r"^D\d{2}$", description="for example D11"),
    location_group: Literal["COMMERCIAL", "RESIDENTIAL", "STREET", "OTHER", "SCHOOL", "TRANSPORT"] | None = None,
    time_of_day: Literal["MORNING", "AFTERNOON", "EVENING", "NIGHT"] | None = None,
    is_weekend: Literal["weekday", "weekend"] | None = None,
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"] | None = None,
    outcome: Outcome | None = None,
    limit: int = Query(10, ge=1, le=50),
):
    chosen = {k: v for k, v in {"district": district, "location_group": location_group,
                                "time_of_day": time_of_day, "is_weekend": is_weekend,
                                "season": season}.items() if v is not None}
    found = store.match_rules(chosen, outcome)
    shown = found[:limit]

    districts = sorted({r["conditions"]["district"] for r in store.rules
                        if "district" in r["conditions"]})
    if found:
        message = f"{len(found)} pattern(s) match; showing the {len(shown)} with the highest lift."
    elif district is not None and district not in districts:
        message = (f"No strong pattern found for district {district}. Rules exist only for "
                   f"districts {', '.join(districts)}.")
    else:
        message = ("No strong pattern found for these conditions. Only combinations that occur "
                   "often enough in the data produce a rule.")

    return PatternsResponse(
        chosen=chosen,
        matched=len(found),
        returned=len(shown),
        rules=[Rule(conditions=r["conditions"], outcome=r["outcome"],
                    support_pct=round(r["support"] * 100, 2),
                    confidence_pct=round(r["confidence"] * 100, 1),
                    lift=round(r["lift"], 2), meaning=describe(r)) for r in shown],
        districts_with_rules=districts,
        settings={"min_support": 0.01, "min_confidence": 0.3, "sample_rows": 150000,
                  "time_of_day_excludes_default_timestamps": True},
        message=message,
        note=("Association rules describe how often things occur together in this dataset. "
              "They do not show that one thing causes another. Only rules above the minimum "
              "support and confidence are kept, and only THEFT, BATTERY and ALL OTHER appear "
              "as outcomes. Rules were mined from a sample of 150,000 incidents."),
    )