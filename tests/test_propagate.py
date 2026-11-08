from datetime import UTC, datetime

import numpy as np
import pytest

from sat_iot_pass_planner.geo import geodetic_to_ecef
from sat_iot_pass_planner.propagate import (
    datetime_to_jd,
    gmst_rad,
    look_angles,
    sky_track,
    teme_to_ecef,
    time_grid,
)
from sat_iot_pass_planner.validate import gmst_example, run_validation, sgp4_against_reference


def test_jd_of_j2000_epoch():
    jd0, f = datetime_to_jd(datetime(2000, 1, 1, 12, 0, tzinfo=UTC))
    assert jd0 + f == pytest.approx(2451545.0, abs=1e-9)


def test_jd_vallado_example():
    jd0, f = datetime_to_jd(datetime(1992, 8, 20, 12, 14, tzinfo=UTC))
    assert jd0 + f == pytest.approx(2448855.009722222, abs=1e-8)


def test_gmst_matches_published_example():
    assert gmst_example()["error_deg"] < 1e-6


def test_gmst_advances_one_sidereal_day_per_day():
    jd = np.array([2451545.0, 2451546.0])
    g = gmst_rad(jd, np.zeros(2))
    delta = np.degrees((g[1] - g[0]) % (2 * np.pi))
    assert delta == pytest.approx(0.98564736, abs=1e-5)  # 360.98564736 - 360


def test_time_grid_length_and_spacing():
    jd, fr = time_grid(datetime(2026, 11, 8, 6, tzinfo=UTC), 1.0, 60.0)
    assert jd.size == 1441
    t = jd + fr
    assert np.allclose(np.diff(t) * 86400, 60.0, atol=1e-3)


def test_time_grid_fraction_stays_in_unit_interval():
    _jd, fr = time_grid(datetime(2026, 11, 8, 23, 30, tzinfo=UTC), 2.0, 600.0)
    assert fr.min() >= 0.0 and fr.max() < 1.0


def test_teme_to_ecef_preserves_norm_and_z():
    r = np.array([[[7000.0, 1000.0, 500.0], [0.0, 7000.0, -200.0]]])
    jd = np.array([2460000.5, 2460000.5])
    fr = np.array([0.1, 0.6])
    out = teme_to_ecef(r, jd, fr)
    assert np.allclose(np.linalg.norm(out, axis=-1), np.linalg.norm(r, axis=-1))
    assert np.allclose(out[..., 2], r[..., 2])


def test_look_angles_zenith():
    site = (46.5, 8.0, 1000.0)
    sat = geodetic_to_ecef(*site) * 1.0 + (geodetic_to_ecef(46.5, 8.0, 1000 + 550_000) - geodetic_to_ecef(*site))
    az, el, rng = look_angles(sat[None, :], *site)
    assert el[0] == pytest.approx(90.0, abs=1e-6)
    assert rng[0] == pytest.approx(550.0, abs=1e-6)


def test_look_angles_due_north_and_east():
    lat, lon = 46.5, 8.0
    north = geodetic_to_ecef(lat + 3.0, lon, 500_000)
    east = geodetic_to_ecef(lat, lon + 3.0, 500_000)
    az_n, el_n, _ = look_angles(north[None, :], lat, lon, 0.0)
    az_e, _, _ = look_angles(east[None, :], lat, lon, 0.0)
    assert az_n[0] == pytest.approx(0.0, abs=0.5) or az_n[0] == pytest.approx(360.0, abs=0.5)
    assert 80.0 < az_e[0] < 100.0
    assert 0 < el_n[0] < 90


def test_look_angles_below_horizon_is_negative():
    far = geodetic_to_ecef(-46.5, 188.0, 550_000)
    _, el, _ = look_angles(far[None, :], 46.5, 8.0, 0.0)
    assert el[0] < -20


def test_sgp4_matches_published_verification_set():
    r = sgp4_against_reference()
    assert r["cases"] >= 30 and r["states_compared"] >= 500
    assert r["max_position_error_km"] < 1e-5


def test_full_validation_passes():
    assert run_validation()["passed"]


def test_satellite_height_is_plausible(sso_set, sites, start):
    jd, fr = time_grid(start, 0.2, 60.0)
    az, el, rng = sky_track(sso_set[:3], jd, fr, sites["interlaken_valley"].lat, sites["interlaken_valley"].lon, 600.0)
    assert np.isfinite(rng).all()
    assert rng.min() > 400.0 and rng.max() < 14000.0
    assert ((az >= 0) & (az < 360)).all()


def test_matches_independent_library():
    skyfield = pytest.importorskip("skyfield.api")
    from sat_iot_pass_planner.tle import Tle

    l1 = "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753"
    l2 = "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667"
    t0 = datetime(2000, 6, 28, 21, 0, tzinfo=UTC)
    jd, fr = time_grid(t0, 0.5, 600.0)
    az, el, _ = sky_track([Tle(5, l1, l2)], jd, fr, 46.5, 8.0, 800.0)
    ts = skyfield.load.timescale(builtin=True)
    sat = skyfield.EarthSatellite(l1, l2, "x", ts)
    topos = skyfield.wgs84.latlon(46.5, 8.0, elevation_m=800.0)
    times = ts.utc(2000, 6, 28, 21, 0, np.arange(jd.size) * 600.0)
    alt, azi, _ = (sat - topos).at(times).altaz()
    # UTC-as-UT1 and no polar motion: sub-0.1 degree agreement expected
    d_el = np.abs(el[0] - alt.degrees)
    assert np.nanmax(d_el) < 0.1
