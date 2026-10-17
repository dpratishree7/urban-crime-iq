# Urban Crime IQ — Phase 9 Handover

## Status

The ML training artifacts and initial API export assets are prepared for backend/frontend integration. The export script is `ml/export_api_assets.py`.

## Model artifacts

- `ml/models/kmeans.pkl` — saved K-Means model and metadata.
- `ml/models/regression.pkl` — regression model artifacts and feature metadata.
- `ml/models/tree.pkl` — Decision Tree pipeline and feature metadata.
- `ml/models/rules.csv` — selected Apriori association rules.

## Exported API assets

Generated under `ml/results/api_assets/`:

- `area_census.csv` — census attributes for community areas.
- `latest_area_crime_counts.csv` — latest observed crime count for each area, including its date.
- `hotspot_clusters.csv` and `cluster_centres.csv` — cluster summaries and coordinates.
- `historical_monthly_weather.csv` — historical monthly weather averages, not a live forecast.
- `dropdown_options.json` — district, community-area and location-group options.
- `domestic_violent_counts.csv` and `domestic_violent_rates.csv` — descriptive diagnostic outputs.
- `regression_metrics.csv` and `tree_metrics.csv` — existing model evaluation results.
- `association_rules.csv` — exported association rules.
- `model_metadata.json` and `manifest.json` — model metadata and asset freshness notes.

## Backend integration notes

1. Load serialized models using the appropriate trusted local model-loading mechanism.
2. Preserve the feature order, encodings and preprocessing used during training.
3. Validate request inputs and handle missing or invalid area IDs.
4. Use the manifest's data-as-of date when displaying latest observed counts.
5. Do not present historical monthly weather averages as a real seven-day weather forecast.
6. Explain that K-Means risk tiers are based on relative recorded incident counts, not population-adjusted risk.
7. Keep database operations separate from this export step. Do not run `etl/load_db.py` as part of API asset generation.

## Frontend integration notes

- Populate district, community-area and location-group dropdowns from `dropdown_options.json`.
- Label the latest crime-count date in the interface.
- Label monthly weather data as historical averages.
- Show model metrics with their correct definitions; R² is not classification accuracy.
- Present hotspot clusters as exploratory spatial groupings, not validated predictions of individual crime risk.

## Evaluation caveats

- Regression test performance: enhanced model MAE 2.4306, RMSE 3.4128, R² 0.7994.
- The enhanced model's improvement over lag + calendar is marginal.
- Domestic status and violent classification are associated in the dataset; this is descriptive and not causal evidence.
- Association rules describe co-occurrence, not causation.

## Ownership boundary

Phase 9 provides model artifacts, metadata, and precomputed assets. Backend API endpoints, frontend UI implementation, and end-to-end integration remain with their assigned owners.


