import gzip
from datetime import UTC, datetime, timedelta

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


def test_select_set_ignores_forward_dated_epochs_outside_the_class():
    leo = [_make(1, 98.0, 15.1, "26315.50000000"), _make(2, 98.0, 15.1, "26314.90000000")]
    high = _make(3, 63.0, 2.0, "26319.50000000")  # high orbit, epoch 4 days later
    assert [t.norad for t in T.select_set([*leo, high], "sso", 5, max_epoch_age_days=2.0)] == [1, 2]


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
    assert T.meta_path(p).name == "snap.meta.json"
    tles, meta = T.load_snapshot(p)
    assert tles == [T.Tle(5, L1, L2)] and meta["count"] == 1
    with gzip.open(p, "rt") as f:
        assert f.read().startswith("SAT 5")


def test_no_orbit_data_ships_with_the_package():
    shipped = [p.name for p in T.DATA_DIR.iterdir()]
    assert not [n for n in shipped if ".tle" in n or "omm" in n.lower() or n.startswith("tle_")]


class _Resp:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.text.encode()


def _stub(text, calls):
    def opener(req, timeout):
        calls.append(req)
        return _Resp(text)

    return opener


def test_fetch_sends_project_user_agent_and_no_email():
    calls = []
    T.fetch_celestrak("active", opener=_stub("x", calls))
    ua = calls[0].get_header("User-agent")
    assert ua == T.USER_AGENT and "sat-iot-pass-planner" in ua and "@" not in ua
    assert calls[0].full_url == T.CELESTRAK_URL.format(group="active")


def test_fetch_rejects_odd_group_names():
    with pytest.raises(ValueError):
        T.fetch_celestrak("active&FORMAT=json", opener=_stub("", []))


def test_fetch_to_cache_writes_name_free_dated_snapshot(tmp_path):
    calls = []
    path, n = T.fetch_to_cache("active", tmp_path, opener=_stub(f"SOME OBJECT NAME\n{L1}\n{L2}\n", calls))
    assert n == 1 and len(calls) == 1 and path == tmp_path / "tle_active.tle.gz"
    with gzip.open(path, "rt") as f:
        assert f.read().splitlines()[0] == "SAT 5"
    tles, meta = T.load_snapshot(path)
    assert tles == [T.Tle(5, L1, L2)] and meta["group"] == "active" and meta["fetched_utc"].endswith("Z")


def test_fetch_to_cache_is_polite_within_two_hours(tmp_path):
    calls = []
    text = f"{L1}\n{L2}\n"
    T.fetch_to_cache("active", tmp_path, opener=_stub(text, calls))
    _, n = T.fetch_to_cache("active", tmp_path, opener=_stub(text, calls))
    assert n == 0 and len(calls) == 1
    later = datetime.now(UTC) + timedelta(hours=2, minutes=1)
    _, n = T.fetch_to_cache("active", tmp_path, opener=_stub(text, calls), now=later)
    assert n == 1 and len(calls) == 2


def test_fetch_to_cache_refuses_a_rate_limit_message(tmp_path):
    with pytest.raises(T.FetchRefused):
        T.fetch_to_cache("active", tmp_path, opener=_stub("GP data has not updated since your last download", []))
    assert not (tmp_path / "tle_active.tle.gz").exists()


def test_load_cached_downloads_once_on_first_use(tmp_path):
    calls = []
    tles, _ = T.load_cached("active", tmp_path, opener=_stub(f"{L1}\n{L2}\n", calls))
    tles2, _ = T.load_cached("active", tmp_path, opener=_stub("", calls))
    assert tles == tles2 == [T.Tle(5, L1, L2)] and len(calls) == 1


def test_load_cached_without_fetch_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        T.load_cached("active", tmp_path, auto_fetch=False)


def test_cache_dir_env_and_override(tmp_path, monkeypatch):
    monkeypatch.setenv(T.CACHE_ENV, str(tmp_path / "env"))
    assert T.cache_dir() == tmp_path / "env"
    assert T.cache_dir(tmp_path / "x") == tmp_path / "x"
    monkeypatch.delenv(T.CACHE_ENV)
    assert T.cache_dir().name == "cache"
