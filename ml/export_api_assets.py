
"""
Phase 9: Export validated ML assets for the backend/frontend team.

Run from the repository root:
    python ml/export_api_assets.py

This script does not train models or modify the database.
"""

from pathlib import Path
import json

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
MODELS = ROOT / "ml" / "models"
RESULTS = ROOT / "ml" / "results"
OUT = RESULTS / "api_assets"

OUT.mkdir(parents=True, exist_ok=True)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def save_csv(df: pd.DataFrame, filename: str) -> None:
    path = OUT / filename
    df.to_csv(path, index=False)
    print(f"[OK] {path.relative_to(ROOT)} ({len(df):,} rows)")


def save_json(data, filename: str) -> None:
    path = OUT / filename
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"[OK] {path.relative_to(ROOT)}")


# --------------------------------------------------
# 1. Check required inputs
# --------------------------------------------------
required = [
    DATA / "area_info.parquet",
    DATA / "area_day.parquet",
    DATA / "weather_daily.parquet",
    DATA / "crimes_features.parquet",
    RESULTS / "hotspot_clusters.csv",
    RESULTS / "regression_metrics.csv",
    RESULTS / "tree_metrics.csv",
    MODELS / "kmeans.pkl",
    MODELS / "regression.pkl",
    MODELS / "tree.pkl",
    MODELS / "rules.csv",
]

for path in required:
    require_file(path)


# --------------------------------------------------
# 2. Export area-level census information
# --------------------------------------------------
area_info = pd.read_parquet(DATA / "area_info.parquet")

if "community_area" not in area_info.columns:
    raise ValueError("area_info.parquet is missing community_area")

if area_info["community_area"].duplicated().any():
    raise ValueError("Duplicate community_area IDs in area_info.parquet")

area_info = area_info.sort_values("community_area")
save_csv(area_info, "area_census.csv")


# --------------------------------------------------
# 3. Export latest actual crime counts per area
# --------------------------------------------------
area_day = pd.read_parquet(DATA / "area_day.parquet")
area_day["date"] = pd.to_datetime(area_day["date"])

required_columns = {"community_area", "date", "crime_count"}
if not required_columns.issubset(area_day.columns):
    raise ValueError(
        f"area_day.parquet must contain {sorted(required_columns)}"
    )

latest_date = area_day["date"].max()
latest = area_day.loc[area_day["date"] == latest_date].copy()

if latest["community_area"].duplicated().any():
    raise ValueError("Multiple rows per area on the latest date")

latest = latest[
    ["community_area", "date", "crime_count"]
].sort_values("community_area")

if latest["community_area"].nunique() != 77:
    raise ValueError(
        "Expected 77 community areas on the latest date; "
        f"found {latest['community_area'].nunique()}"
    )

save_csv(latest, "latest_area_crime_counts.csv")


# --------------------------------------------------
# 4. Export cluster centres and summaries
# --------------------------------------------------
clusters = pd.read_csv(RESULTS / "hotspot_clusters.csv")

centre_columns = {
    "cluster", "centre_lat", "centre_lon"
}
if not centre_columns.issubset(clusters.columns):
    raise ValueError(
        "hotspot_clusters.csv is missing cluster centre columns"
    )

save_csv(clusters, "hotspot_clusters.csv")

centres = clusters[
    ["cluster", "centre_lat", "centre_lon"]
].copy()
save_csv(centres, "cluster_centres.csv")


# --------------------------------------------------
# 5. Export historical monthly weather averages
# --------------------------------------------------
weather = pd.read_parquet(DATA / "weather_daily.parquet")
weather["date"] = pd.to_datetime(weather["date"])

if not {"date", "temperature", "rainfall"}.issubset(weather.columns):
    raise ValueError("Unexpected weather_daily.parquet schema")

weather_monthly = (
    weather.assign(month=weather["date"].dt.month)
    .groupby("month", as_index=False)
    .agg(
        avg_temperature=("temperature", "mean"),
        avg_rainfall=("rainfall", "mean"),
        historical_days=("date", "count"),
    )
)

save_csv(weather_monthly, "historical_monthly_weather.csv")


# --------------------------------------------------
# 6. Export dropdown options
# --------------------------------------------------
crimes = pd.read_parquet(DATA / "crimes_features.parquet")

dropdowns = {}

for column in ["district", "community_area", "location_group"]:
    if column not in crimes.columns:
        raise ValueError(f"Missing dropdown column: {column}")

    values = crimes[column].dropna().unique().tolist()

    # Convert NumPy scalar values into regular Python values.
    values = [
        value.item() if hasattr(value, "item") else value
        for value in values
    ]

    dropdowns[column] = sorted(values)

save_json(dropdowns, "dropdown_options.json")


# --------------------------------------------------
# 7. Export domestic-versus-violent diagnostic
# --------------------------------------------------
domestic = crimes[["domestic", "is_violent"]].dropna().copy()

diagnostic_counts = (
    pd.crosstab(
        domestic["domestic"],
        domestic["is_violent"],
        margins=False,
    )
    .rename_axis("domestic")
    .reset_index()
)

save_csv(diagnostic_counts, "domestic_violent_counts.csv")

diagnostic_rates = (
    domestic.groupby("domestic", as_index=False)
    .agg(
        incidents=("is_violent", "size"),
        violent_share=("is_violent", "mean"),
    )
)
save_csv(diagnostic_rates, "domestic_violent_rates.csv")


# --------------------------------------------------
# 8. Export model metadata and existing evaluation
# --------------------------------------------------
model_metadata = {}

for name in ["kmeans", "regression", "tree"]:
    model_path = MODELS / f"{name}.pkl"
    artifact = joblib.load(model_path)

    # Export descriptive metadata, not serialized model objects.
    if not isinstance(artifact, dict):
        raise ValueError(
            f"{name}.pkl is expected to contain a metadata dictionary"
        )

    metadata = {
        key: value
        for key, value in artifact.items()
        if key not in {"model", "baseline", "enhanced", "pipeline"}
    }

    model_metadata[name] = metadata

save_json(model_metadata, "model_metadata.json")

save_csv(
    pd.read_csv(RESULTS / "regression_metrics.csv"),
    "regression_metrics.csv",
)
save_csv(
    pd.read_csv(RESULTS / "tree_metrics.csv"),
    "tree_metrics.csv",
)

rules = pd.read_csv(MODELS / "rules.csv")
save_csv(rules, "association_rules.csv")


# --------------------------------------------------
# 9. Export manifest and data freshness information
# --------------------------------------------------
manifest = {
    "project": "Urban Crime IQ",
    "purpose": "Phase 9 API assets",
    "latest_crime_data_date": latest_date.strftime("%Y-%m-%d"),
    "latest_weather_data_date": weather["date"].max().strftime("%Y-%m-%d"),
    "community_areas_on_latest_date": int(
        latest["community_area"].nunique()
    ),
    "cluster_count": int(clusters["cluster"].nunique()),
    "weather_asset_note": (
        "Historical monthly averages only; not a live weather forecast."
    ),
    "crime_count_note": (
        "Latest observed daily counts. These are not future predictions."
    ),
    "cluster_risk_note": (
        "Risk levels represent relative recorded incident counts, "
        "not population-adjusted crime risk."
    ),
    "files": sorted(
        path.name for path in OUT.iterdir() if path.is_file()
    ),
}

save_json(manifest, "manifest.json")

print("\nPhase 9 asset export completed.")
print(f"Output folder: {OUT}")
