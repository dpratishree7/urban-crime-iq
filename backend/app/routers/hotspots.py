import numpy as np
from fastapi import APIRouter, HTTPException

from ..model_store import store
from ..schemas import Cluster, HotspotsResponse, LookupRequest, LookupResponse

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


# Rough bounding box of Chicago; K-Means would assign any point on Earth to a cluster
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 41.60, 42.05, -87.95, -87.50


@router.post("/hotspots/lookup", response_model=LookupResponse)
def lookup(req: LookupRequest):
    if req.community_area is not None:
        point = store.area_points.get(req.community_area)
        if point is None:
            raise HTTPException(503, "Area locations are not available right now")
        lat, lon, name = point
        mode = "community_area"
        note = ("Cluster at the average location of this area's recorded crimes. "
                "Areas near a cluster border can span more than one cluster.")
    else:
        lat, lon, name = req.latitude, req.longitude, None
        mode = "coordinates"
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            raise HTTPException(422, "These coordinates are outside Chicago")
        note = "Nearest cluster centre to this point."

    cluster = store.predict_cluster(lat, lon)
    row = store.clusters.loc[store.clusters["cluster"] == cluster].iloc[0]
    centre = store.kmeans["model"].cluster_centers_[cluster]
    distance = float(np.hypot(*(store.to_km(lat, lon)[0] - centre)))
    return LookupResponse(
        mode=mode, community_area=req.community_area, area_name=name,
        latitude=round(lat, 5), longitude=round(lon, 5),
        cluster=cluster, risk_level=str(row.risk_level),
        top_crime_type=str(row.top_crime_type),
        distance_to_centre_km=round(distance, 2),
        centre_lat=float(row.centre_lat), centre_lon=float(row.centre_lon),
        note=note,
    )