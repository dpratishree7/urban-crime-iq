
"""
Urban Crime IQ — Phase 8.1: K-Means Hotspot Clustering

Run from project root:
    python ml/train_kmeans.py
    python ml/train_kmeans.py 8

Input:
    data/processed/coordinates.parquet

Outputs:
    ml/models/kmeans.pkl
    ml/results/kmeans_k_scores.csv
    ml/results/hotspot_clusters.csv
    ml/results/hotspots_map.html       (if Folium is installed)
    docs/screenshots/10_kmeans_elbow_silhouette.png
    docs/screenshots/11_kmeans_clusters.png

Method:
    - Latitude/longitude only for clustering.
    - Local equirectangular approximation in kilometres.
    - Evaluate K=5..15 using inertia and sampled silhouette.
    - Automatic selection by highest sampled silhouette score.
    - Optional command-line K override within 5..15.
"""

import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


# ============================================================
# 1. Configuration and paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "data" / "processed" / "coordinates.parquet"
MODEL_DIR = ROOT / "ml" / "models"
RESULTS_DIR = ROOT / "ml" / "results"
SHOTS_DIR = ROOT / "docs" / "screenshots"

for directory in (MODEL_DIR, RESULTS_DIR, SHOTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "kmeans.pkl"
SCORES_PATH = RESULTS_DIR / "kmeans_k_scores.csv"
SUMMARY_PATH = RESULTS_DIR / "hotspot_clusters.csv"
MAP_PATH = RESULTS_DIR / "hotspots_map.html"

ELBOW_PATH = SHOTS_DIR / "10_kmeans_elbow_silhouette.png"
CLUSTER_PLOT_PATH = SHOTS_DIR / "11_kmeans_clusters.png"

SEED = 42
K_VALUES = list(range(5, 16))
SILHOUETTE_SAMPLE_SIZE = 10_000


# ============================================================
# 2. Validate optional command-line K
# ============================================================

requested_k = None

if len(sys.argv) > 2:
    raise SystemExit(
        "Usage: python ml/train_kmeans.py [K]\n"
        "K must be between 5 and 15."
    )

if len(sys.argv) == 2:
    try:
        requested_k = int(sys.argv[1])
    except ValueError:
        raise SystemExit("K must be an integer between 5 and 15.")

    if requested_k not in K_VALUES:
        raise SystemExit("K must be between 5 and 15.")


# ============================================================
# 3. Load and validate coordinates
# ============================================================

print("=" * 68)
print("URBAN CRIME IQ — K-MEANS HOTSPOT CLUSTERING")
print("=" * 68)

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Input not found: {DATA_PATH}\n"
        "Run python ml/prepare_tables.py first."
    )

df = pd.read_parquet(DATA_PATH)

required_columns = {"latitude", "longitude", "crime_group"}
missing_columns = required_columns - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Required columns are missing: {sorted(missing_columns)}"
    )

original_rows = len(df)

df = df.dropna(subset=["latitude", "longitude"]).copy()

# Reject impossible geographic coordinates.
valid_geo = (
    df["latitude"].between(-90, 90)
    & df["longitude"].between(-180, 180)
)

df = df.loc[valid_geo].copy()

df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df = df.dropna(subset=["latitude", "longitude"]).copy()

# Also reject non-finite coordinates.
finite = (
    np.isfinite(df["latitude"].to_numpy(dtype=float))
    & np.isfinite(df["longitude"].to_numpy(dtype=float))
)
df = df.loc[finite].copy()
df.reset_index(drop=True, inplace=True)

if len(df) < max(K_VALUES):
    raise ValueError("Not enough valid coordinate records.")

print(f"Input rows: {original_rows:,}")
print(f"Valid coordinate rows: {len(df):,}")
print(f"Rows excluded: {original_rows - len(df):,}")
print(f"Unique coordinate pairs: {df[['latitude', 'longitude']].drop_duplicates().shape[0]:,}")

# The clustering features are strictly latitude and longitude.
lat = df["latitude"].to_numpy(dtype=float)
lon = df["longitude"].to_numpy(dtype=float)


# ============================================================
# 4. Project geographic coordinates into local kilometres
# ============================================================
# This is a local equirectangular approximation, not an exact
# geodesic calculation. All model fitting and prediction must
# use these same saved constants.

LAT0 = float(np.mean(lat))
KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON = 111.32 * np.cos(np.radians(LAT0))

if KM_PER_DEG_LON <= 0:
    raise ValueError("Invalid longitude projection scale.")

def to_xy(latitude, longitude):
    """Convert latitude/longitude to local x/y coordinates in km."""
    latitude = np.asarray(latitude, dtype=float)
    longitude = np.asarray(longitude, dtype=float)

    x_km = longitude * KM_PER_DEG_LON
    y_km = latitude * KM_PER_DEG_LAT

    return np.column_stack((x_km, y_km))


X = to_xy(lat, lon)

print(f"Projection reference latitude: {LAT0:.6f}")
print(f"Latitude scale: {KM_PER_DEG_LAT:.3f} km/degree")
print(f"Longitude scale: {KM_PER_DEG_LON:.3f} km/degree")


# ============================================================
# 5. Evaluate K = 5..15
# ============================================================

rng = np.random.default_rng(SEED)
sample_size = min(SILHOUETTE_SAMPLE_SIZE, len(X))
sample_indices = rng.choice(len(X), size=sample_size, replace=False)
X_sample = X[sample_indices]

score_rows = []
candidate_models = {}

print(f"\nEvaluating K=5..15; silhouette sample={sample_size:,}")

for k in K_VALUES:
    print(f"Fitting K={k}...", flush=True)

    candidate = KMeans(
        n_clusters=k,
        n_init=10,
        max_iter=300,
        random_state=SEED,
    )

    candidate.fit(X)

    # Predict labels for the same fixed subset used for every K.
    sample_labels = candidate.predict(X_sample)

    score = silhouette_score(X_sample, sample_labels)

    score_rows.append({
        "k": k,
        "inertia": float(candidate.inertia_),
        "silhouette_score": float(score),
        "sample_size": sample_size,
        "random_state": SEED,
    })

    candidate_models[k] = candidate

    print(
        f"  inertia={candidate.inertia_:,.2f} | "
        f"silhouette={score:.4f}"
    )

scores = pd.DataFrame(score_rows)
scores.to_csv(SCORES_PATH, index=False)

if requested_k is None:
    selected_k = int(
        scores.loc[scores["silhouette_score"].idxmax(), "k"]
    )
    selection_method = "highest sampled silhouette score"
else:
    selected_k = requested_k
    selection_method = "command-line override"

print(f"\nSelected K: {selected_k} ({selection_method})")


# ============================================================
# 6. Plot elbow and silhouette diagnostics
# ============================================================

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

axes[0].plot(scores["k"], scores["inertia"], marker="o")
axes[0].axvline(selected_k, linestyle="--", alpha=0.7)
axes[0].set_title("Elbow Method")
axes[0].set_xlabel("Number of clusters (K)")
axes[0].set_ylabel("Inertia (km²)")
axes[0].set_xticks(K_VALUES)
axes[0].grid(alpha=0.3)

axes[1].plot(
    scores["k"],
    scores["silhouette_score"],
    marker="o",
)
axes[1].axvline(selected_k, linestyle="--", alpha=0.7)
axes[1].set_title("Silhouette Score")
axes[1].set_xlabel("Number of clusters (K)")
axes[1].set_ylabel("Sampled silhouette score")
axes[1].set_xticks(K_VALUES)
axes[1].grid(alpha=0.3)

fig.suptitle("Urban Crime IQ — K-Means Model Selection")
fig.tight_layout()
fig.savefig(ELBOW_PATH, dpi=160, bbox_inches="tight")
plt.close(fig)


# ============================================================
# 7. Assign final clusters and create summaries
# ============================================================

# Reuse the already-fitted candidate model for the selected K.
# This keeps the reported score and final model consistent.
model = candidate_models[selected_k]
df["cluster"] = model.labels_

summary_rows = []

for cluster_id in range(selected_k):
    part = df.loc[df["cluster"] == cluster_id]

    if part.empty:
        top_crime = "NONE"
        top_crime_share = 0.0
        centre_lat = np.nan
        centre_lon = np.nan
    else:
        crime_counts = part["crime_group"].value_counts(dropna=True)
        top_crime = (
            str(crime_counts.index[0])
            if not crime_counts.empty
            else "UNKNOWN"
        )
        top_crime_share = (
            float(crime_counts.iloc[0] / len(part) * 100)
            if not crime_counts.empty
            else 0.0
        )
        centre_lat = float(part["latitude"].mean())
        centre_lon = float(part["longitude"].mean())

    summary_rows.append({
        "cluster": cluster_id,
        "centre_lat": centre_lat,
        "centre_lon": centre_lon,
        "size": len(part),
        "share_pct": len(part) / len(df) * 100,
        "top_crime_type": top_crime,
        "top_crime_share_pct": top_crime_share,
    })

clusters = pd.DataFrame(summary_rows)

# Descriptive tiers based on relative cluster sizes only.
# These are NOT validated measures of crime risk.
clusters["risk_level"] = pd.qcut(
    clusters["size"].rank(method="first"),
    q=3,
    labels=["Low", "Medium", "High"],
).astype(str)

clusters["risk_basis"] = "relative recorded incident count; not population-adjusted risk"

clusters = (
    clusters.sort_values("size", ascending=False)
    .reset_index(drop=True)
)

clusters.to_csv(SUMMARY_PATH, index=False)

print("\nCluster summary:")
print(clusters.round(3).to_string(index=False))


# ============================================================
# 8. Static cluster plot
# ============================================================

fig, ax = plt.subplots(figsize=(10, 7))

ax.scatter(
    df["longitude"],
    df["latitude"],
    c=df["cluster"],
    cmap="tab20",
    s=3,
    alpha=0.35,
    rasterized=True,
)

# Cluster centres from the model's projected coordinates.
centres_xy = model.cluster_centers_

centre_lon = centres_xy[:, 0] / KM_PER_DEG_LON
centre_lat = centres_xy[:, 1] / KM_PER_DEG_LAT

ax.scatter(
    centre_lon,
    centre_lat,
    marker="X",
    s=130,
    c="black",
    edgecolors="white",
    linewidths=0.8,
    label="Cluster centres",
    zorder=5,
)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title(f"Chicago Crime Coordinate Clusters (K={selected_k})")
ax.legend()
ax.grid(alpha=0.2)

fig.tight_layout()
fig.savefig(CLUSTER_PLOT_PATH, dpi=160, bbox_inches="tight")
plt.close(fig)


# ============================================================
# 9. Save reusable model artifact
# ============================================================

best_score = float(
    scores.loc[scores["k"] == selected_k, "silhouette_score"].iloc[0]
)

artifact = {
    "model": model,
    "k": selected_k,
    "lat0": LAT0,
    "km_per_deg_lat": KM_PER_DEG_LAT,
    "km_per_deg_lon": KM_PER_DEG_LON,
    "features": ["latitude", "longitude"],
    "coordinate_units": "local projected kilometres (approximate)",
    "selection_method": selection_method,
    "sampled_silhouette_score": best_score,
    "silhouette_sample_size": sample_size,
    "random_state": SEED,
    "risk_levels": dict(
        zip(clusters["cluster"].astype(int), clusters["risk_level"])
    ),
    "risk_level_basis": "relative cluster incident count; not population-adjusted risk",
}

joblib.dump(artifact, MODEL_PATH)

print(f"\nSaved model: {MODEL_PATH}")
print(f"Saved K scores: {SCORES_PATH}")
print(f"Saved cluster summary: {SUMMARY_PATH}")
print(f"Saved model-selection plot: {ELBOW_PATH}")
print(f"Saved cluster plot: {CLUSTER_PLOT_PATH}")


# ============================================================
# 10. Optional interactive Folium map
# ============================================================

try:
    import folium

    map_object = folium.Map(
        location=[float(np.mean(lat)), float(np.mean(lon))],
        zoom_start=10,
        tiles=None,
    )

    colours = {
        "High": "red",
        "Medium": "orange",
        "Low": "blue",
    }

    for row in clusters.itertuples(index=False):
        if pd.isna(row.centre_lat) or pd.isna(row.centre_lon):
            continue

        radius = 5 + min(float(row.share_pct), 15) * 0.8

        popup_html = (
            f"<b>Cluster {row.cluster}</b><br>"
            f"Relative incident-volume tier: {row.risk_level}<br>"
            f"Recorded incidents in sample: {row.size:,}<br>"
            f"Sample share: {row.share_pct:.2f}%<br>"
            f"Most common crime group: {row.top_crime_type}<br>"
            f"Top group share: {row.top_crime_share_pct:.1f}%"
        )

        folium.CircleMarker(
            location=[row.centre_lat, row.centre_lon],
            radius=radius,
            color=colours[row.risk_level],
            fill=True,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"Cluster {row.cluster} — {row.risk_level} volume tier",
        ).add_to(map_object)

    folium.LayerControl().add_to(map_object)

    map_object.save(str(MAP_PATH))
    print(f"Saved interactive map: {MAP_PATH}")

except ImportError:
    print(
        "\nFolium is not installed; interactive map skipped. "
        "Install it with: python -m pip install folium"
    )


# ============================================================
# 11. Final report
# ============================================================

print("\n" + "=" * 68)
print("K-MEANS EXPERIMENT COMPLETED")
print("=" * 68)
print(f"Selected K: {selected_k}")
print(f"Sampled silhouette score: {best_score:.4f}")
print("Remember: cluster volume is not the same as crime risk.")
