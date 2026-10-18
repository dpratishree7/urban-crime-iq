
"""
Urban Crime IQ — Generate K-Means hotspot map.

Run from project root:
    python ml/generate_hotspots_map.py

Reads the saved cluster summary; does not retrain K-Means.
No external basemap tiles are used.
"""

from pathlib import Path

import folium
import pandas as pd


# --------------------------------------------------
# 1. Paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "ml" / "results"
INPUT_PATH = RESULTS / "hotspot_clusters.csv"
OUTPUT_PATH = RESULTS / "hotspots_map.html"


# --------------------------------------------------
# 2. Load and validate cluster summary
# --------------------------------------------------

if not INPUT_PATH.exists():
    raise FileNotFoundError(
        f"Cluster summary not found: {INPUT_PATH}\n"
        "Run python ml/train_kmeans.py first."
    )

clusters = pd.read_csv(INPUT_PATH)

required = {
    "cluster",
    "centre_lat",
    "centre_lon",
    "size",
    "share_pct",
    "top_crime_type",
    "top_crime_share_pct",
    "risk_level",
}

missing = required - set(clusters.columns)

if missing:
    raise ValueError(
        f"Missing columns in hotspot_clusters.csv: {sorted(missing)}"
    )

clusters = clusters.dropna(
    subset=["centre_lat", "centre_lon"]
).copy()

if clusters.empty:
    raise ValueError("No valid cluster centres found.")

if not clusters["centre_lat"].between(-90, 90).all():
    raise ValueError("Invalid latitude found in cluster summary.")

if not clusters["centre_lon"].between(-180, 180).all():
    raise ValueError("Invalid longitude found in cluster summary.")


# --------------------------------------------------
# 3. Create map without external tiles
# --------------------------------------------------

centre = [
    float(clusters["centre_lat"].mean()),
    float(clusters["centre_lon"].mean()),
]

m = folium.Map(
    location=centre,
    zoom_start=10,
    tiles=None,
    control_scale=True,
)

# Dark background for a clean, tile-free presentation.
m.get_root().header.add_child(
    folium.Element(
        """
        <style>
        .leaflet-container {
            background: #1b1b1b !important;
        }
        </style>
        """
    )
)

colours = {
    "High": "#ef4444",
    "Medium": "#f59e0b",
    "Low": "#eab308",
}

# --------------------------------------------------
# 4. Add interactive cluster markers
# --------------------------------------------------

for row in clusters.itertuples(index=False):

    cluster_id = int(row.cluster)
    size = int(row.size)
    share = float(row.share_pct)
    top_share = float(row.top_crime_share_pct)

    # Keep marker sizes within a reasonable visual range.
    radius = max(7, min(22, 7 + share * 0.7))

    risk_level = str(row.risk_level)
    colour = colours.get(risk_level, "#60a5fa")

    popup_html = f"""
    <div style="font-family:Arial,sans-serif;min-width:220px;">
        <h3 style="margin:0 0 8px;">Cluster {cluster_id}</h3>
        <b>Relative incident-volume tier:</b> {risk_level}<br>
        <b>Sample incidents:</b> {size:,}<br>
        <b>Sample share:</b> {share:.2f}%<br>
        <b>Most common crime group:</b> {row.top_crime_type}<br>
        <b>Top group share:</b> {top_share:.1f}%<br>
        <hr>
        <i>Not a population-adjusted crime-risk measure.</i>
    </div>
    """

    folium.CircleMarker(
        location=[
            float(row.centre_lat),
            float(row.centre_lon),
        ],
        radius=radius,
        color=colour,
        weight=2,
        fill=True,
        fill_color=colour,
        fill_opacity=0.75,
        popup=folium.Popup(popup_html, max_width=330),
        tooltip=f"Cluster {cluster_id} | {risk_level} volume tier",
    ).add_to(m)


# --------------------------------------------------
# 5. Add a compact legend
# --------------------------------------------------

legend_html = """
<div style="
position:fixed;
bottom:30px;
left:30px;
z-index:9999;
background:#252525;
color:white;
padding:12px 15px;
border:1px solid #666;
border-radius:8px;
font-family:Arial,sans-serif;
font-size:13px;
">
<b>Relative incident-volume tiers</b><br>
<span style="color:#ef4444;">&#9679;</span> High<br>
<span style="color:#f59e0b;">&#9679;</span> Medium<br>
<span style="color:#eab308;">&#9679;</span> Low<br>
<small>Not population-adjusted risk</small>
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))


# --------------------------------------------------
# 6. Save HTML
# --------------------------------------------------

m.save(str(OUTPUT_PATH))

print("=" * 55)
print("HOTSPOT MAP GENERATED")
print("=" * 55)
print(f"Clusters displayed: {len(clusters)}")
print(f"Output: {OUTPUT_PATH}")
print("External basemap: disabled")
print("K-Means retraining: not performed")
