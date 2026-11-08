"""Terrain horizon masks from the swisstopo height profile service (swissALTI3D, 2 m model).

For every azimuth a ray is sampled out to ``max_km`` and the largest elevation angle to any terrain point is kept,
with an Earth-curvature and standard-refraction correction. The result (one number per azimuth) is the minimum
elevation a satellite must have to be seen from the site. Only the small mask files are committed, not the DEM.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .geo import EARTH_R_MEAN, grid_convergence_deg, lv95_to_wgs84, wgs84_to_lv95

PROFILE_URL = "https://api3.geo.admin.ch/rest/services/profile.json"
# (start_m, end_m, points): fine near field, coarser far field; 200 points is the service limit.
SEGMENTS = ((0.0, 3000.0, 150), (3000.0, 15000.0, 200), (15000.0, 40000.0, 200))
REFRACTION_K = 0.13  # standard atmosphere, effective Earth radius factor 1/(1-k)
MIN_DIST_M = 20.0  # ignore the sample on top of the site itself


def horizon_from_profile(dist_m: Sequence[float], alt_m: Sequence[float], site_alt_m: float) -> float:
    """Highest elevation angle (deg) to a terrain profile seen from a point at ``site_alt_m``.

    ``dist_m`` is horizontal distance from the site, ``alt_m`` the terrain height at that distance.
    Curvature drop (1-k) d^2 / 2R is subtracted so distant ridges are not over-estimated.
    NaN heights (outside the DEM) are ignored.
    """
    d = np.asarray(dist_m, dtype=float)
    h = np.asarray(alt_m, dtype=float)
    ok = np.isfinite(h) & (d >= MIN_DIST_M)
    if not ok.any():
        return 0.0
    d, h = d[ok], h[ok]
    drop = (1 - REFRACTION_K) * d**2 / (2 * EARTH_R_MEAN * 1000.0)
    ang = np.degrees(np.arctan2(h - site_alt_m - drop, d))
    return float(ang.max())


def horizon_to_arrays(horizon_deg: Sequence[float], step_deg: float) -> tuple[np.ndarray, np.ndarray]:
    az = np.arange(0.0, 360.0, step_deg)
    return az, np.asarray(horizon_deg, dtype=float)


def mask_at(az_deg: np.ndarray | float, horizon_deg: Sequence[float], step_deg: float) -> np.ndarray:
    """Interpolate the horizon mask (periodic) at arbitrary azimuths."""
    h = np.asarray(horizon_deg, dtype=float)
    a = np.asarray(az_deg, dtype=float) % 360.0
    x = a / step_deg
    i0 = np.floor(x).astype(int) % len(h)
    i1 = (i0 + 1) % len(h)
    f = x - np.floor(x)
    return h[i0] * (1 - f) + h[i1] * f


def _query(points_lv95: list[tuple[float, float]], n: int) -> list[dict]:
    geom = {"type": "LineString", "coordinates": [list(p) for p in points_lv95]}
    qs = urllib.parse.urlencode({"geom": json.dumps(geom), "sr": 2056, "nb_points": n, "distinct_points": "true"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{PROFILE_URL}?{qs}", timeout=60) as r:  # noqa: S310 (fixed https host)
                return json.loads(r.read())
        except Exception:  # noqa: BLE001 - retry on any transient network error
            if attempt == 3:
                raise
    return []


def fetch_ray(e0: float, n0: float, grid_bearing_deg: float, max_km: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
    """Terrain profile (distance, height) along one ray in LV95 plane coordinates."""
    b = math.radians(grid_bearing_deg)
    ue, un = math.sin(b), math.cos(b)
    dists, alts = [], []
    for a, z, n in SEGMENTS:
        if a >= max_km * 1000:
            break
        z = min(z, max_km * 1000)
        prof = _query([(e0 + ue * a, n0 + un * a), (e0 + ue * z, n0 + un * z)], n)
        for p in prof:
            v = p["alts"].get("DTM2")
            dists.append(a + p["dist"])
            alts.append(float("nan") if v is None else float(v))
    return np.array(dists), np.array(alts)


def site_elevation(lat: float, lon: float) -> float:
    e, n = wgs84_to_lv95(lat, lon)
    prof = _query([(e, n), (e + 1.0, n)], 2)
    return float(prof[0]["alts"]["DTM2"])


def fetch_horizon(lat: float, lon: float, step_deg: float = 2.0, max_km: float = 40.0, workers: int = 8) -> dict:
    """Download profiles around a site and return the horizon mask record."""
    e0, n0 = wgs84_to_lv95(lat, lon)
    alt0 = site_elevation(lat, lon)
    conv = grid_convergence_deg(lat, lon)
    azs = np.arange(0.0, 360.0, step_deg)

    def one(az: float) -> float:
        d, h = fetch_ray(e0, n0, az - conv, max_km)
        return horizon_from_profile(d, h, alt0)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        hz = list(ex.map(one, azs))
    return {"ground_elevation_m": alt0, "step_deg": step_deg, "max_km": max_km, "horizon_deg": [round(x, 2) for x in hz]}


__all__ = [
    "fetch_horizon",
    "horizon_from_profile",
    "mask_at",
    "horizon_to_arrays",
    "lv95_to_wgs84",
]
