import numpy as np
import pytest

from sat_iot_pass_planner.geo import (
    enu_matrix,
    geodetic_to_ecef,
    grid_convergence_deg,
    lv95_to_wgs84,
    wgs84_to_lv95,
)


def test_lv95_origin_matches_published_reference_point():
    # swisstopo reference: old observatory Bern = LV95 (2600000, 1200000) = 46.9510827861 N, 7.4386324175 E
    lat, lon = lv95_to_wgs84(2600000, 1200000)
    assert lat == pytest.approx(46.95108, abs=2e-5)
    assert lon == pytest.approx(7.43863, abs=2e-5)


def test_lv95_roundtrip_within_metres():
    e, n = wgs84_to_lv95(46.5936, 7.9086)
    lat, lon = lv95_to_wgs84(e, n)
    assert lat == pytest.approx(46.5936, abs=1e-4)
    assert lon == pytest.approx(7.9086, abs=1e-4)


def test_lv95_known_easting_northing_ordering():
    e1, n1 = wgs84_to_lv95(46.6, 8.0)
    e2, n2 = wgs84_to_lv95(46.7, 8.1)
    assert e2 > e1 and n2 > n1


def test_ecef_equator_radius():
    r = geodetic_to_ecef(0, 0, 0)
    assert r[0] == pytest.approx(6378.137, abs=1e-6)
    assert abs(r[1]) < 1e-9 and abs(r[2]) < 1e-9


def test_ecef_pole_is_polar_radius():
    r = geodetic_to_ecef(90, 0, 0)
    assert r[2] == pytest.approx(6356.752, abs=1e-2)


def test_ecef_altitude_adds_radially_at_equator():
    assert geodetic_to_ecef(0, 0, 1000)[0] == pytest.approx(6379.137, abs=1e-6)


def test_enu_matrix_is_orthonormal_and_up_is_radial():
    m = enu_matrix(46.5, 8.0)
    assert np.allclose(m @ m.T, np.eye(3), atol=1e-12)
    up = geodetic_to_ecef(46.5, 8.0, 1000) - geodetic_to_ecef(46.5, 8.0, 0)
    assert np.allclose(m[2], up / np.linalg.norm(up), atol=1e-9)


def test_grid_convergence_zero_on_central_meridian_and_small_east_of_it():
    assert grid_convergence_deg(46.9, 7.43958333) == pytest.approx(0.0, abs=1e-9)
    assert grid_convergence_deg(46.6, 8.0) == pytest.approx(0.41, abs=0.02)
