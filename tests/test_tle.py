import gzip
from datetime import UTC, datetime

import pytest

from sat_iot_pass_planner import tle as T

# Element set from the public SGP4 verification set (Vallado et al., AIAA 2006-6753), catalogue number 5.
L1 = "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753"
L2 = "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667"


def _line1(norad: int, epoch_day: str = "26312.25250495") -> str:
    body = f"1 {norad:05d}U 03031E   {epoch_day}  .00000343  00000+0  16698-3 0  999"
    return body + str(_cs(body))


def _line2(norad: int, inc: float = 98.6754, mm: float = 14.24408402) -> str:
    body = f"2 {norad:05d} {inc:8.4f} 319.0248 0010423 123.8047 236.4126 {mm:11.8f}21218"
    return body + str(_cs(body))


def _cs(body: str) -> int:
    return sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in body[:68]) % 10


def _make(norad: int, inc: float, mm: float, epoch_day: str = "26312.25250495") -> T.Tle:
    return T.Tle(norad, _line1(norad, epoch_day)[:69], _line2(norad, inc, mm)[:69])


def test_checksum_accepts_reference_lines():
    assert T.checksum_ok(L1) and T.checksum_ok(L2)


def test_checksum_rejects_corrupted_line():
    assert not T.checksum_ok(L1[:20] + "9" + L1[21:])


def test_checksum_rejects_short_line():
    assert not T.checksum_ok("1 00005U")


def test_parse_three_line_format():
    out = T.parse_tle_text(f"SOME NAME\n{L1}\n{L2}\n")
    assert len(out) == 1 and out[0].norad == 5


def test_parse_two_line_format_and_crlf():
    out = T.parse_tle_text(f"{L1}\r\n{L2}\r\n")
    assert [t.norad for t in out] == [5]


def test_parse_skips_garbage_and_bad_checksum():
    bad = L2[:-1] + "0"
    assert T.parse_tle_text(f"junk\n{L1}\n{bad}\nmore junk\n") == []


def test_parse_skips_mismatched_catalogue_numbers():
    other = "2 00006" + L2[7:]
    assert T.parse_tle_text(f"{L1}\n{other}\n") == []


def test_parse_empty_text():
    assert T.parse_tle_text("") == []


def test_orbit_elements_from_reference_set():
    t = T.parse_tle_text(f"{L1}\n{L2}")[0]
    assert t.inclination_deg == pytest.approx(34.2682)
    assert t.eccentricity == pytest.approx(0.1859667)
    assert t.altitude_km == pytest.approx(2256, abs=15)


def test_epoch_parsing():
    t = T.parse_tle_text(f"{L1}\n{L2}")[0]
    assert t.epoch.year == 2000
    assert t.epoch.timetuple().tm_yday == 179


def test_in_class_boundaries():
    sso = _make(1, 98.0, 15.1)  # about 570 km
    assert T.in_class(sso, "sso") and not T.in_class(sso, "mid")
    mid = _make(2, 53.0, 15.1)
    assert T.in_class(mid, "mid") and not T.in_class(mid, "sso")
    low = _make(3, 98.0, 16.0)  # about 290 km, too low
    assert not T.in_class(low, "sso")


def test_select_set_is_deterministic_and_sized():
    tles = [_make(100 + i, 98.0, 15.1) for i in range(40)]
    a = T.select_set(tles, "sso", 10, seed=1)
    b = T.select_set(tles, "sso", 10, seed=1)
    c = T.select_set(tles, "sso", 10, seed=2)
    assert a == b and len(a) == 10 and a != c
    assert [t.norad for t in a] == sorted(t.norad for t in a)


def test_select_set_returns_all_when_fewer_candidates():
    tles = [_make(100 + i, 98.0, 15.1) for i in range(5)]
    assert len(T.select_set(tles, "sso", 50)) == 5


def test_select_set_drops_old_epochs():
    tles = [_make(1, 98.0, 15.1, "26312.25000000"), _make(2, 98.0, 15.1, "26300.25000000")]
    assert [t.norad for t in T.select_set(tles, "sso", 5, max_epoch_age_days=2.0)] == [1]


def test_select_set_unknown_class_and_empty_input():
    with pytest.raises(KeyError):
        T.select_set([_make(1, 98.0, 15.1)], "geo", 3)
    assert T.select_set([], "sso", 3) == []


def test_anonymise_removes_names():
    text = T.anonymise([T.Tle(5, L1, L2)])
    assert text.splitlines()[0] == "SAT 5" and len(text.splitlines()) == 3


def test_snapshot_roundtrip(tmp_path):
    p = tmp_path / "snap.tle.gz"
    T.save_snapshot([T.Tle(5, L1, L2)], "test", "x", p)
    tles, meta = T.load_snapshot(p)
    assert tles == [T.Tle(5, L1, L2)] and meta["count"] == 1
    with gzip.open(p, "rt") as f:
        assert f.read().startswith("SAT 5")


def test_committed_snapshot_has_no_object_names_and_is_dated():
    tles, meta = T.load_snapshot()
    assert len(tles) > 50
    with gzip.open(T.DATA_DIR / "tle_snapshot.tle.gz", "rt") as f:
        names = [ln for i, ln in enumerate(f.read().splitlines()) if i % 3 == 0]
    assert all(n.startswith("SAT ") for n in names)
    assert datetime.fromisoformat(meta["newest_epoch_utc"].replace("Z", "+00:00")) > datetime(2026, 1, 1, tzinfo=UTC)
