"""Wildfire hotspot clustering via DBSCAN (scikit-learn optional)."""
from __future__ import annotations

from dataclasses import dataclass

try:
    import numpy as np
    from sklearn.cluster import DBSCAN

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


@dataclass
class HotspotCluster:
    cluster_id: int
    centroid_lat: float
    centroid_lon: float
    hotspot_count: int
    mean_frp: float
    risk: str


def _classify_risk(count: int, mean_frp: float) -> str:
    if mean_frp > 200 or count > 50:
        return "extreme"
    if mean_frp > 100 or count > 20:
        return "high"
    if mean_frp > 30 or count > 5:
        return "moderate"
    return "low"


def cluster_hotspots(
    points: list[tuple[float, float, float]],
    eps_km: float = 50.0,
    min_samples: int = 3,
) -> list[HotspotCluster]:
    """Cluster fire hotspots using DBSCAN with haversine metric.

    Args:
        points: list of (lat, lon, frp) tuples
        eps_km: neighbourhood radius in km (default 50 km)
        min_samples: minimum points to form a cluster

    Returns sorted list of HotspotCluster (largest first).
    """
    if not points:
        return []

    if not _HAS_SKLEARN:
        # Fallback: treat all points as one cluster
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        frps = [p[2] for p in points]
        mean_frp = sum(frps) / len(frps)
        return [
            HotspotCluster(
                cluster_id=0,
                centroid_lat=sum(lats) / len(lats),
                centroid_lon=sum(lons) / len(lons),
                hotspot_count=len(points),
                mean_frp=mean_frp,
                risk=_classify_risk(len(points), mean_frp),
            )
        ]

    coords = np.array([(p[0], p[1]) for p in points])
    frps = np.array([p[2] for p in points])

    # eps converted to radians for haversine
    eps_rad = eps_km / 6371.0
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, algorithm="ball_tree", metric="haversine")
    labels = db.fit_predict(np.radians(coords))

    clusters: list[HotspotCluster] = []
    for label in set(labels):
        if label == -1:
            continue
        mask = labels == label
        cluster_lats = coords[mask, 0]
        cluster_lons = coords[mask, 1]
        cluster_frps = frps[mask]
        mean_frp = float(cluster_frps.mean())
        count = int(mask.sum())
        clusters.append(
            HotspotCluster(
                cluster_id=int(label),
                centroid_lat=float(cluster_lats.mean()),
                centroid_lon=float(cluster_lons.mean()),
                hotspot_count=count,
                mean_frp=round(mean_frp, 2),
                risk=_classify_risk(count, mean_frp),
            )
        )

    return sorted(clusters, key=lambda c: c.hotspot_count, reverse=True)
