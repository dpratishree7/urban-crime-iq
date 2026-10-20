from fastapi import APIRouter

from ..model_store import store
from ..schemas import Cluster, HotspotsResponse

router = APIRouter(prefix="/api", tags=["hotspots"])


@router.get("/hotspots", response_model=HotspotsResponse)
def hotspots():
    df = store.clusters.sort_values("size", ascending=False)
    clusters = [
        Cluster(
            cluster=int(r.cluster),
            centre_lat=float(r.centre_lat),
            centre_lon=float(r.centre_lon),
            sample_size=int(r.size),
            share_pct=round(float(r.share_pct), 1),
            top_crime_type=str(r.top_crime_type),
            top_crime_share_pct=round(float(r.top_crime_share_pct), 1),
            risk_level=str(r.risk_level),
        )
        for r in df.itertuples()
    ]
    return HotspotsResponse(
        k=int(store.kmeans["k"]),
        sample_total=sum(c.sample_size for c in clusters),
        risk_basis=str(store.kmeans["risk_level_basis"]),
        note=("Cluster sizes are counts within the sample of crimes used to train "
              "K-Means, not totals for all crimes. Clusters are exploratory spatial "
              "groupings, not predictions of individual crime risk."),
        clusters=clusters,
    )