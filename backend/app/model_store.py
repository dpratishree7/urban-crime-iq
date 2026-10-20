from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # project root
MODELS = ROOT / "ml" / "models"
ASSETS = ROOT / "ml" / "results" / "api_assets"


class ModelStore:
    """Holds every model and lookup table. Loaded once, when the API starts."""

    def __init__(self):
        self.kmeans = None
        self.clusters = None

    def load(self):
        self.kmeans = joblib.load(MODELS / "kmeans.pkl")
        self.clusters = pd.read_csv(ASSETS / "hotspot_clusters.csv")
        print(f"Loaded K-Means: k={self.kmeans['k']}, "
              f"{len(self.clusters)} cluster rows")

    def loaded(self) -> list[str]:
        names = {"kmeans": self.kmeans}
        return [name for name, obj in names.items() if obj is not None]


store = ModelStore()