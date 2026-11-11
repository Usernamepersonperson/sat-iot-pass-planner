import json

import pytest

from sat_iot_pass_planner.cli import main
from sat_iot_pass_planner.synthetic import load_synthetic
from sat_iot_pass_planner.tle import cache_path, save_snapshot


def test_validate_command_passes(capsys):
    assert main(["validate"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_passes_command_prints_stats(capsys):
    assert main(["passes", "--synthetic", "--site", "schilthorn_ridge", "--days", "1", "--limit", "3"]) == 0
    out = capsys.readouterr().out
    assert "link_terrain" in out and "max el" in out


def test_schedule_command_writes_json(tmp_path):
    p = tmp_path / "s.json"
    assert main(["schedule", "--synthetic", "--site", "lauterbrunnen_valley", "--hours", "24", "--out", str(p)]) == 0
    data = json.loads(p.read_text())
    assert data["windows"] and "note" in data


def test_unknown_site_is_an_error():
    with pytest.raises(KeyError):
        main(["passes", "--synthetic", "--site", "nowhere"])


def test_empty_cache_with_no_fetch_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="fetch-tle"):
        main(["passes", "--site", "schilthorn_ridge", "--no-fetch", "--cache-dir", str(tmp_path)])


def test_passes_command_reads_the_cache_when_present(tmp_path, capsys):
    tles, _ = load_synthetic()
    save_snapshot(tles, "test cache", "active", cache_path("active", tmp_path))
    assert main(["passes", "--site", "schilthorn_ridge", "--days", "0.5", "--no-fetch", "--cache-dir", str(tmp_path)]) == 0
    assert "link_terrain" in capsys.readouterr().out


def test_fetch_command_keeps_a_recent_cache_without_network(tmp_path, capsys):
    tles, _ = load_synthetic(per_class=2)
    save_snapshot(tles, "test cache", "active", cache_path("active", tmp_path))
    assert main(["fetch-tle", "--cache-dir", str(tmp_path)]) == 0
    assert "kept" in capsys.readouterr().out


def test_demo_runs_offline_on_synthetic_data(tmp_path):
    out = tmp_path / "r"
    assert main(["demo", "--synthetic", "--days", "1", "--probes", "100", "--out", str(out)]) == 0
    res = json.loads((out / "results.json").read_text())
    assert res["orbit_data"]["synthetic"] is True
    assert (out / "figure.png").exists() and (out / "post-figure.png").exists()
