"""SGP4 propagation and the TEME -> Earth-fixed -> topocentric chain (numpy, vectorised over satellites x times)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from sgp4.api import WGS72, Satrec, SatrecArray

from .geo import enu_matrix, geodetic_to_ecef
from .tle import Tle


def datetime_to_jd(dt: datetime) -> tuple[float, float]:
    """Julian date split as (jd at 0h UT, day fraction). UTC is used as UT1 (error < 0.9 s, under 0.5 km on the ground)."""
    dt = dt.astimezone(UTC)
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd0 = jdn - 0.5
    frac = (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6) / 86400.0
    return float(jd0), frac


def time_grid(start: datetime, days: float, step_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Arrays (jd, fr) covering ``days`` from ``start`` every ``step_s`` seconds."""
    n = int(round(days * 86400 / step_s)) + 1
    jd0, f0 = datetime_to_jd(start)
    fr = f0 + np.arange(n) * step_s / 86400.0
    jd = jd0 + np.floor(fr)
    return jd, fr - np.floor(fr)


def gmst_rad(jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
    """Greenwich mean sidereal time (IAU-82, Vallado eq. 3-45)."""
    t = ((np.asarray(jd) - 2451545.0) + np.asarray(fr)) / 36525.0
    sec = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * t + 0.093104 * t**2 - 6.2e-6 * t**3
    return np.deg2rad((sec / 240.0) % 360.0)


def teme_to_ecef(r_teme: np.ndarray, jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
    """Rotate TEME positions (..., n_t, 3) to Earth-fixed (polar motion and equation of the equinoxes neglected)."""
    th = gmst_rad(jd, fr)
    c, s = np.cos(th), np.sin(th)
    x, y, z = r_teme[..., 0], r_teme[..., 1], r_teme[..., 2]
    return np.stack([c * x + s * y, -s * x + c * y, z], axis=-1)


def propagate_teme(tles: list[Tle], jd: np.ndarray, fr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """TEME position (n_sat, n_t, 3) in km and a boolean ok mask (False where SGP4 reports an error)."""
    sats = [Satrec.twoline2rv(t.line1, t.line2, WGS72) for t in tles]
    err, r, _v = SatrecArray(sats).sgp4(jd, fr)
    return r, err == 0


def look_angles(r_ecef: np.ndarray, lat_deg: float, lon_deg: float, alt_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Azimuth (deg, from north, clockwise), elevation (deg), slant range (km) from a site."""
    site = geodetic_to_ecef(lat_deg, lon_deg, alt_m)
    rot = enu_matrix(lat_deg, lon_deg)
    enu = (r_ecef - site) @ rot.T
    e, n, u = enu[..., 0], enu[..., 1], enu[..., 2]
    rng = np.sqrt(e**2 + n**2 + u**2)
    el = np.degrees(np.arcsin(np.clip(u / rng, -1, 1)))
    az = np.degrees(np.arctan2(e, n)) % 360.0
    return az, el, rng


def sky_track(tles: list[Tle], jd: np.ndarray, fr: np.ndarray, lat: float, lon: float, alt_m: float):
    """Look angles of every satellite at every time; samples with SGP4 errors become NaN."""
    r, ok = propagate_teme(tles, jd, fr)
    az, el, rng = look_angles(teme_to_ecef(r, jd, fr), lat, lon, alt_m)
    for a in (az, el, rng):
        a[~ok] = np.nan
    return az, el, rng
