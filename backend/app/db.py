import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parents[2] / ".env")   # .env in the project root

url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL is not set. Check your .env file in the project root.")

engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=2)