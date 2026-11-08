import numpy as np
import pytest

from sat_iot_pass_planner.link import (
    LinkParams,
    airtime_s,
    fspl_db,
    margin_db,
    max_doppler_khz,
    min_link_elevation_deg,
    slant_range_km,
)


def test_fspl_known_value():
    # 32.44 + 20 log10(868) + 20 log10(1000) = 151.21 dB
    assert fspl_db(1000.0, 868.0) == pytest.approx(151.21, abs=0.01)


def test_fspl_doubling_distance_adds_6db():
    assert fspl_db(2000.0, 868.0) - fspl_db(1000.0, 868.0) == pytest.approx(6.02, abs=0.01)


def test_slant_range_zenith_equals_altitude():
    assert slant_range_km(90.0, 550.0) == pytest.approx(550.0, abs=1e-6)


def test_slant_range_horizon_is_long():
    assert 2500 < slant_range_km(0.0, 550.0) < 2900


def test_slant_range_decreases_with_elevation():
    r = slant_range_km(np.array([5.0, 20.0, 60.0]), 550.0)
    assert r[0] > r[1] > r[2]


def test_margin_decreases_with_range():
    p = LinkParams()
    assert margin_db(1000.0, 60.0, p) > margin_db(2000.0, 10.0, p)


def test_margin_improves_one_for_one_with_eirp():
    a = margin_db(1500.0, 30.0, LinkParams(eirp_dbm=14.0))
    b = margin_db(1500.0, 30.0, LinkParams(eirp_dbm=17.0))
    assert b - a == pytest.approx(3.0, abs=1e-9)


def test_margin_drops_3db_when_data_rate_doubles():
    a = margin_db(1500.0, 30.0, LinkParams(data_rate_bps=300.0))
    b = margin_db(1500.0, 30.0, LinkParams(data_rate_bps=600.0))
    assert a - b == pytest.approx(3.01, abs=0.01)


def test_min_elevation_default_is_plausible():
    e = min_link_elevation_deg(530.0)
    assert e is not None and 5.0 < e < 25.0


def test_min_elevation_falls_with_better_gt():
    assert min_link_elevation_deg(530.0, LinkParams(sat_gt_dbk=-18.0)) < min_link_elevation_deg(
        530.0, LinkParams(sat_gt_dbk=-24.0)
    )


def test_link_never_closes_with_tiny_eirp():
    assert min_link_elevation_deg(530.0, LinkParams(eirp_dbm=-20.0)) is None


def test_min_elevation_rises_with_altitude():
    assert min_link_elevation_deg(900.0) > min_link_elevation_deg(450.0)


def test_doppler_order_of_magnitude():
    assert 15.0 < max_doppler_khz(550.0, 868.0) < 25.0


def test_airtime_matches_bits_over_rate():
    assert airtime_s(24, 16, LinkParams(data_rate_bps=300.0)) == pytest.approx(320 / 300.0)


@pytest.mark.parametrize("kw", [{"freq_mhz": 0.0}, {"data_rate_bps": -1.0}])
def test_invalid_params_rejected(kw):
    with pytest.raises(ValueError):
        LinkParams(**kw)
