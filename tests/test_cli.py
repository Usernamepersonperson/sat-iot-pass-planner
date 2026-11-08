import json

from sat_iot_pass_planner.cli import main


def test_validate_command_passes(capsys):
    assert main(["validate"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_passes_command_prints_stats(capsys):
    assert main(["passes", "--site", "schilthorn_ridge", "--days", "1", "--limit", "3"]) == 0
    out = capsys.readouterr().out
    assert "link_terrain" in out and "max el" in out


def test_schedule_command_writes_json(tmp_path):
    p = tmp_path / "s.json"
    assert main(["schedule", "--site", "lauterbrunnen_valley", "--hours", "24", "--out", str(p)]) == 0
    data = json.loads(p.read_text())
    assert data["windows"] and "note" in data


def test_unknown_site_is_an_error():
    try:
        main(["passes", "--site", "nowhere"])
    except KeyError:
        return
    raise AssertionError("expected KeyError")
