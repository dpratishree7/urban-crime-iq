from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .model_store import store
from .routers import forecast, hotspots, meta, olap, patterns, violence

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()          # models are loaded once, when the API starts
    yield


app = FastAPI(title="Crime Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(olap.router)
app.include_router(hotspots.router)
app.include_router(forecast.router)
app.include_router(violence.router)
app.include_router(patterns.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": store.loaded()}