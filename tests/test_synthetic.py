from datetime import UTC, datetime

import pytest
from sgp4.api import WGS72, Satrec

from sat_iot_pass_planner import synthetic as S
from sat_iot_pass_planner import tle as T
from sat_iot_pass_planner.analysis import DEFAULT_SETS, build_sets


def test_every_line_has_valid_layout_and_checksum():
    for t in S.synthetic_tles(per_class=10):
        assert len(t.line1) == len(t.line2) == 69
        assert T.checksum_ok(t.line1) and T.checksum_ok(t.line2)


def test_checksum_matches_reference_lines():
    l1 = "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753"
    l2 = "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667"
    assert S.checksum(l1) == int(l1[68]) and S.checksum(l2) == int(l2[68])


def test_text_roundtrips_through_the_normal_parser():
    tles = S.synthetic_tles(per_class=5)
    assert T.parse_tle_text(S.synthetic_text(tles)) == tles


def test_sets_are_clearly_labelled_synthetic():
    tles = S.synthetic_tles(per_class=3)
    text = S.synthetic_text(tles)
    assert all(ln.startswith("SYNTHETIC ") for ln in text.splitlines()[::3])
    assert all(t.line1[9:17].strip() == "SYNTH" and t.norad >= S.FIRST_NORAD for t in tles)
    assert S.load_synthetic(per_class=3)[1]["synthetic"] is True


def test_generation_is_deterministic_per_seed():
    assert S.synthetic_tles(seed=4) == S.synthetic_tles(seed=4)
    assert S.synthetic_tles(seed=4) != S.synthetic_tles(seed=5)


def test_parameters_survive_the_text_encoding():
    ep = datetime(2026, 3, 1, 6, 0, tzinfo=UTC)
    t = S.make_tle(80001, ep, 97.5, 10.0, 0.0012, 90.0, 180.0, S.mean_motion_rev_day(520.0))
    assert t.inclination_deg == pytest.approx(97.5)
    assert t.eccentricity == pytest.approx(0.0012)
    assert t.altitude_km == pytest.approx(520.0, abs=0.01)
    assert abs((t.epoch - ep).total_seconds()) < 1e-3


def test_mean_motion_of_known_orbits():
    # Kepler period at 400 km is 5553.6 s (15.557 rev/day); 1.0027 rev/day at geostationary radius (42164 km)
    assert S.mean_motion_rev_day(400.0) == pytest.approx(86400 / 5553.6, abs=0.002)
    assert S.mean_motion_rev_day(42164.0 - T.R_EQ_KM) == pytest.approx(1.0027, abs=1e-3)


@pytest.mark.parametrize(
    "x, field", [(1.0e-4, " 10000-3"), (2.8098e-5, " 28098-4"), (-3.5e-4, "-35000-3"), (0.0, " 00000-0")]
)
def test_bstar_field(x, field):
    assert S._exp_field(x) == field


def test_sgp4_accepts_synthetic_sets():
    for t in S.synthetic_tles(per_class=4):
        sat = Satrec.twoline2rv(t.line1, t.line2, WGS72)
        e, r, _v = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF)
        assert e == 0 and 6600 < sum(c * c for c in r) ** 0.5 < 7300


def test_every_orbit_class_is_populated_for_the_demo():
    chosen = build_sets(S.synthetic_tles(), DEFAULT_SETS)
    assert all(len(v) == 24 for v in chosen.values())
    assert all(T.in_class(t, cls) for cls, v in chosen.items() for t in v)


@pytest.mark.parametrize("kwargs", [{"norad": 0}, {"norad": 100000}, {"eccentricity": 1.0}, {"inclination_deg": 181.0}])
def test_make_tle_rejects_bad_parameters(kwargs):
    base = dict(
        norad=80001,
        epoch=S.SYNTHETIC_EPOCH,
        inclination_deg=97.0,
        raan_deg=0.0,
        eccentricity=0.001,
        arg_perigee_deg=0.0,
        mean_anomaly_deg=0.0,
        mean_motion=15.0,
    )
    with pytest.raises(ValueError):
        S.make_tle(**{**base, **kwargs})
