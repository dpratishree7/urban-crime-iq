from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from .db import engine

ROOT = Path(__file__).resolve().parents[2]          # project root
MODELS = ROOT / "ml" / "models"
ASSETS = ROOT / "ml" / "results" / "api_assets"


class ModelStore:
    """Holds every model and lookup table. Loaded once, when the API starts."""

    def __init__(self):
        self.kmeans = None
        self.clusters = None
        self.area_points = {}          # community_area -> (lat, lon, name)

    def load(self):
        self.kmeans = joblib.load(MODELS / "kmeans.pkl")
        self.clusters = pd.read_csv(ASSETS / "hotspot_clusters.csv")
        self._check_kmeans()
        self._load_area_points()
        print(f"Loaded K-Means: k={self.kmeans['k']}, "
              f"{len(self.clusters)} cluster rows, {len(self.area_points)} area locations")

    def to_km(self, lat: float, lon: float) -> np.ndarray:
        """Same projection as ml/train_kmeans.py: x = longitude, y = latitude, in km."""
        x = lon * float(self.kmeans["km_per_deg_lon"])
        y = lat * float(self.kmeans["km_per_deg_lat"])
        return np.array([[x, y]])

    def predict_cluster(self, lat: float, lon: float) -> int:
        return int(self.kmeans["model"].predict(self.to_km(lat, lon))[0])

    def _check_kmeans(self):
        """Each saved cluster centre must map back to its own cluster."""
        for r in self.clusters.itertuples():
            got = self.predict_cluster(r.centre_lat, r.centre_lon)
            if got != int(r.cluster):
                raise RuntimeError(
                    f"K-Means self-check failed: centre of cluster {r.cluster} "
                    f"was assigned to cluster {got}. Check the km projection.")
        print("K-Means self-check passed")

    def _load_area_points(self):
        sql = ("SELECT l.community_area, MAX(l.area_name) AS area_name, "
               "AVG(f.latitude) AS lat, AVG(f.longitude) AS lon "
               "FROM fact_crime f JOIN dim_location l ON l.location_key = f.location_key "
               "WHERE f.latitude IS NOT NULL GROUP BY l.community_area")
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(sql)).all()
            self.area_points = {int(r.community_area): (float(r.lat), float(r.lon), r.area_name)
                                for r in rows}
        except Exception as exc:       # the API still starts without the database
            print("WARNING: could not load area locations:", exc)

    def loaded(self) -> list[str]:
        names = {"kmeans": self.kmeans}
        return [name for name, obj in names.items() if obj is not None]


store = ModelStore()