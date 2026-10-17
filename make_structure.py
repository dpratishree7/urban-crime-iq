from pathlib import Path

folders = [
    "data/raw", "data/external", "data/processed",
    "notebooks", "etl", "sql",
    "ml/models", "ml/results",
    "backend/app/routers",
    "docs/report", "docs/slides", "docs/screenshots",
]
files = [
    "README.md", ".gitignore", ".env.example",
    "etl/clean.py", "etl/enrich.py", "etl/features.py", "etl/load_db.py",
    "sql/schema.sql", "sql/load.sql", "sql/olap_queries.sql", "sql/views.sql",
    "ml/train_kmeans.py", "ml/train_regression.py",
    "ml/train_tree.py", "ml/train_apriori.py",
    "backend/requirements.txt",
    "backend/app/__init__.py", "backend/app/routers/__init__.py",
    "backend/app/main.py", "backend/app/db.py",
    "backend/app/schemas.py", "backend/app/model_store.py",
    "backend/app/routers/meta.py", "backend/app/routers/olap.py",
    "backend/app/routers/hotspots.py", "backend/app/routers/forecast.py",
    "backend/app/routers/violence.py", "backend/app/routers/patterns.py",
]
for f in folders:
    Path(f).mkdir(parents=True, exist_ok=True)
for f in files:
    Path(f).touch()
print("Done")