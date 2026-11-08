import numpy as np
import pytest

from sat_iot_pass_planner.passes import flat_site
from sat_iot_pass_planner.terrain import horizon_from_profile, mask_at


def test_wall_gives_45_degrees():
    # a 1000 m high wall 1000 m away seen from sea level: 45 degrees (curvature drop at 1 km is 0.08 m)
    d = np.array([0, 500, 1000, 1500])
    h = np.array([0, 0, 1000, 1000])
    assert horizon_from_profile(d, h, 0.0) == pytest.approx(45.0, abs=0.01)


def test_flat_terrain_horizon_is_not_positive():
    d = np.linspace(0, 40000, 400)
    assert horizon_from_profile(d, np.zeros_like(d), 0.0) <= 0.0


def test_site_above_terrain_has_negative_horizon():
    d = np.linspace(100, 10000, 100)
    assert horizon_from_profile(d, np.full_like(d, 500.0), 1500.0) < -5


def test_curvature_lowers_distant_ridge():
    far = horizon_from_profile([30000], [1000], 0.0)
    assert far < np.degrees(np.arctan2(1000, 30000))


def test_nan_heights_are_ignored():
    got = horizon_from_profile([100, 200, 300], [np.nan, 100.0, np.nan], 0.0)
    assert got == pytest.approx(np.degrees(np.arctan2(100, 200)), abs=0.01)


def test_all_nan_returns_zero():
    assert horizon_from_profile([100, 200], [np.nan, np.nan], 0.0) == 0.0


def test_first_sample_on_site_is_ignored():
    assert horizon_from_profile([0.0, 5.0], [500.0, 500.0], 0.0) == 0.0


def test_mask_interpolates_between_azimuth_steps():
    assert mask_at(45.0, [0.0, 10.0, 20.0, 10.0], 90.0) == pytest.approx(5.0)


def test_mask_wraps_around_north():
    hz = [10.0, 0.0, 0.0, 20.0]
    assert mask_at(315.0, hz, 90.0) == pytest.approx(15.0)
    assert mask_at(-45.0, hz, 90.0) == pytest.approx(15.0)


def test_mask_vectorised():
    out = mask_at(np.array([0.0, 90.0, 180.0]), [1.0, 2.0, 3.0, 4.0], 90.0)
    assert out.tolist() == [1.0, 2.0, 3.0]


def test_flat_site_mask_is_zero():
    assert flat_site(46.0, 8.0).mask(np.array([10.0, 200.0])).tolist() == [0.0, 0.0]


def test_committed_masks_are_complete_and_plausible(sites):
    assert len(sites) == 5
    for s in sites.values():
        assert len(s.horizon_deg) == 180
        assert -10 < min(s.horizon_deg) and max(s.horizon_deg) < 60


def test_ridge_horizon_lower_than_valley(sites):
    assert np.mean(sites["schilthorn_ridge"].horizon_deg) + 10 < np.mean(sites["lauterbrunnen_valley"].horizon_deg)
