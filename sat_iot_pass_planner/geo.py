"""Small geodesy helpers: WGS84 <-> ECEF, ENU rotation, WGS84 <-> Swiss LV95 (swisstopo approximate formulas)."""

from __future__ import annotations

import math

import numpy as np

WGS84_A = 6378.137  # km
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)
EARTH_R_MEAN = 6371.0088  # km, used only for the terrain curvature term


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
    """Geodetic WGS84 to ECEF, kilometres."""
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    h = alt_m / 1000.0
    return np.array(
        [
            (n + h) * math.cos(lat) * math.cos(lon),
            (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1 - WGS84_E2) + h) * math.sin(lat),
        ]
    )


def enu_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Rows are the East, North, Up unit vectors expressed in ECEF."""
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    return np.array([[-so, co, 0.0], [-sl * co, -sl * so, cl], [cl * co, cl * so, sl]])


def wgs84_to_lv95(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """swisstopo approximate formula (about 1 m accuracy inside Switzerland). Returns (E, N)."""
    p = (lat_deg * 3600 - 169028.66) / 10000
    lam = (lon_deg * 3600 - 26782.5) / 10000
    e = 2600072.37 + 211455.93 * lam - 10938.51 * lam * p - 0.36 * lam * p**2 - 44.54 * lam**3
    n = 1200147.07 + 308807.95 * p + 3745.25 * lam**2 + 76.63 * p**2 - 194.56 * lam**2 * p + 119.79 * p**3
    return e, n


def lv95_to_wgs84(e: float, n: float) -> tuple[float, float]:
    """swisstopo approximate inverse formula. Returns (lat, lon)."""
    y = (e - 2600000) / 1e6
    x = (n - 1200000) / 1e6
    lam = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x**2 - 0.0436 * y**3
    phi = 16.9023892 + 3.238272 * x - 0.270978 * y**2 - 0.002528 * x**2 - 0.0447 * y**2 * x - 0.0140 * x**3
    return phi * 100 / 36, lam * 100 / 36


def grid_convergence_deg(lat_deg: float, lon_deg: float, lon0_deg: float = 7.43958333) -> float:
    """Meridian convergence of the LV95 projection (first-order); grid bearing = true azimuth - convergence."""
    return (lon_deg - lon0_deg) * math.sin(math.radians(lat_deg))
