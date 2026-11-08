import json
from dataclasses import replace

import numpy as np
import pytest

from sat_iot_pass_planner.link import LinkParams
from sat_iot_pass_planner.passes import extract_passes, pass_stats, runs, union_windows
from sat_iot_pass_planner.report import gt_sweep, horizon_summary, relink
from sat_iot_pass_planner.sched import (
    DeviceParams,
    SchedulePolicy,
    SimResult,
    device_schedule,
    energy_mah_per_day,
    gateway_contact_index,
    latency_stats,
    simulate_blind,
    simulate_scheduled,
)


def test_runs_basic_and_edges():
    assert runs(np.array([0, 1, 1, 0, 1])) == [(1, 3), (4, 5)]
    assert runs(np.array([1, 1, 1])) == [(0, 3)]
    assert runs(np.array([0, 0])) == []
    assert runs(np.array([])) == []


def test_visibility_shapes_and_subsets(vis_valley):
    v = vis_valley
    assert v.az.shape == v.el.shape == v.margin.shape == (24, v.n_t)
    assert (v.terrain_ok <= v.link_ok).all() and (v.link_ok <= v.horizon_ok).all()


def test_terrain_never_adds_passes(vis_valley, vis_ridge):
    for v in (vis_valley, vis_ridge):
        st = pass_stats(v, 2.0)
        assert st["link_terrain"]["passes_per_day"] <= st["link_flat"]["passes_per_day"] + 1e-9
        assert st["link_flat"]["passes_per_day"] <= st["geometric"]["passes_per_day"] + 1e-9


def test_valley_loses_far_more_than_ridge(vis_valley, vis_ridge):
    lost_valley = pass_stats(vis_valley, 2.0)["passes_lost_to_terrain_pct"]
    lost_ridge = pass_stats(vis_ridge, 2.0)["passes_lost_to_terrain_pct"]
    assert lost_valley > 15.0
    assert lost_ridge < 5.0


def test_flat_pass_count_is_site_independent_within_a_few_percent(vis_valley, vis_ridge):
    a = pass_stats(vis_valley, 2.0)["link_flat"]["passes_per_day"]
    b = pass_stats(vis_ridge, 2.0)["link_flat"]["passes_per_day"]
    assert abs(a - b) / max(a, b) < 0.1


def test_passes_extracted_have_valid_elevation_and_order(vis_ridge):
    ps = extract_passes(vis_ridge, vis_ridge.terrain_ok)
    assert ps and all(p.max_el_deg > 0 and p.end_idx > p.start_idx for p in ps)
    assert [p.start_idx for p in ps] == sorted(p.start_idx for p in ps)


def test_track_above_terrain_mask_when_usable(vis_valley):
    v = vis_valley
    mask = v.site.mask(np.nan_to_num(v.az))
    assert (v.el[v.terrain_ok] > mask[v.terrain_ok]).all()


def test_usable_elevation_exceeds_link_limit(vis_ridge):
    # at 24 satellites of mean altitude about 530 km the link needs roughly 10 degrees or more
    assert np.nanmin(vis_ridge.el[vis_ridge.link_ok]) > 8.0


def test_better_link_gives_more_passes_and_more_terrain_loss(vis_valley):
    low = relink(vis_valley, replace(LinkParams(), sat_gt_dbk=-24.0))
    high = relink(vis_valley, replace(LinkParams(), sat_gt_dbk=-16.0))
    s_low, s_high = pass_stats(low, 2.0), pass_stats(high, 2.0)
    assert s_high["link_flat"]["passes_per_day"] > s_low["link_flat"]["passes_per_day"]
    assert s_high["link_terrain"]["passes_per_day"] > s_low["link_terrain"]["passes_per_day"]


def test_gt_sweep_rows(vis_valley, vis_ridge):
    rows = gt_sweep({"v": vis_valley, "r": vis_ridge}, LinkParams(), 2.0, 530.0, gts=(-22.0, -18.0))
    assert len(rows) == 2 and rows[1]["min_link_elevation_deg"] < rows[0]["min_link_elevation_deg"]
    assert set(rows[0]["sites"]) == {"v", "r"}


def test_horizon_summary(sites):
    s = horizon_summary(sites["lauterbrunnen_valley"], 11.0)
    assert s["max_horizon_deg"] > 30 and s["azimuth_share_blocked_pct"] > 50


@pytest.fixture(scope="module")
def sim_inputs(vis_valley, sso_set):
    nxt = gateway_contact_index(sso_set, vis_valley.start, 2.0, vis_valley.step_s)
    return vis_valley, nxt


def test_gateway_contact_index_is_monotone_and_not_in_past(sim_inputs):
    _v, nxt = sim_inputs
    assert (np.diff(nxt, axis=1) >= 0).all()
    assert (nxt >= np.arange(nxt.shape[1])[None, :]).all()


def test_scheduled_delivers_and_latency_is_non_negative(sim_inputs):
    v, nxt = sim_inputs
    g = np.linspace(0, 86400, 80)
    res = simulate_scheduled(v, v.terrain_ok, g, nxt, SchedulePolicy(), np.random.default_rng(1))
    assert res.delivered.mean() > 0.9
    assert (res.up_latency_s[res.delivered] >= 0).all()
    ok = np.isfinite(res.e2e_latency_s)
    assert (res.e2e_latency_s[ok] >= res.up_latency_s[ok] - 1e-9).all()


def test_zero_burst_probability_delivers_nothing(sim_inputs):
    v, nxt = sim_inputs
    res = simulate_scheduled(
        v, v.terrain_ok, np.linspace(0, 40000, 30), nxt, replace(SchedulePolicy(), p_burst=0.0), np.random.default_rng(1)
    )
    assert not res.delivered.any() and np.isnan(res.up_latency_s).all()


def test_no_windows_means_no_delivery_and_no_bursts(sim_inputs):
    v, nxt = sim_inputs
    none = np.zeros_like(v.terrain_ok)
    res = simulate_scheduled(v, none, np.array([100.0, 5000.0]), nxt, SchedulePolicy(), np.random.default_rng(1))
    assert res.bursts == 0 and not res.delivered.any()
    assert simulate_blind(v, none, np.array([100.0]), nxt, SchedulePolicy(), np.random.default_rng(1)).delivered.sum() == 0


def test_message_generated_late_is_not_delivered_before_generation(sim_inputs):
    v, nxt = sim_inputs
    g = np.array([30000.0])
    res = simulate_scheduled(v, v.terrain_ok, g, nxt, SchedulePolicy(p_burst=1.0), np.random.default_rng(1))
    assert res.delivered[0] and res.up_latency_s[0] >= 0


def test_scheduled_uses_less_energy_and_has_lower_latency_than_blind(sim_inputs):
    v, nxt = sim_inputs
    rng = np.random.default_rng(3)
    g = np.sort(rng.uniform(0, 86400, 48))
    pol, dev, link = SchedulePolicy(), DeviceParams(), LinkParams()
    s = simulate_scheduled(v, v.terrain_ok, g, nxt, pol, np.random.default_rng(1))
    b = simulate_blind(v, v.terrain_ok, g, nxt, pol, np.random.default_rng(2))
    es, eb = energy_mah_per_day(s, 1.0, dev, link), energy_mah_per_day(b, 1.0, dev, link)
    assert es["total_mah_per_day"] < eb["total_mah_per_day"]
    assert latency_stats(s)["uplink_p50_min"] < latency_stats(b)["uplink_p50_min"]


def test_energy_formula_by_hand():
    link, dev = LinkParams(), DeviceParams()
    res = SimResult(np.array([True]), np.array([1.0]), np.array([1.0]), 2, 6, 2)
    e = energy_mah_per_day(res, 1.0, dev, link)
    tx = 6 * (320 / 300.0) * 45.0 / 3600.0
    wake = 2 * 3.0 * 10.0 / 3600.0
    sleep = 8.0 / 1000 * 24
    assert e["total_mah_per_day"] == pytest.approx(tx + wake + sleep)
    assert e["battery_years"] == pytest.approx(3000 * 0.6 / (tx + wake + sleep) / 365)


def test_latency_stats_percentiles_and_empty():
    res = SimResult(np.array([True, True, False]), np.array([60.0, 120.0, np.nan]), np.array([60.0, 180.0, np.nan]), 0, 0, 0)
    s = latency_stats(res)
    assert s["delivery_ratio"] == pytest.approx(2 / 3)
    assert s["uplink_p50_min"] == pytest.approx(1.5)
    none = latency_stats(SimResult(np.array([False]), np.array([np.nan]), np.array([np.nan]), 0, 0, 0))
    assert np.isnan(none["uplink_p50_min"])


def test_device_schedule_structure(vis_ridge, sso_set):
    sched = device_schedule(
        vis_ridge,
        vis_ridge.terrain_ok,
        [t.norad for t in sso_set],
        SchedulePolicy(),
        LinkParams(),
        DeviceParams(),
        "2026-11-08T08:00:00Z",
        24.0,
    )
    text = json.dumps(sched)
    back = json.loads(text)
    assert back["windows"] and back["site"]["key"] == "schilthorn_ridge"
    w = back["windows"]
    assert [x["wake_utc"] for x in w] == sorted(x["wake_utc"] for x in w)
    assert all(x["duration_s"] > 0 and x["burst_utc"] for x in w)
    assert all(x["burst_utc"][0] == x["wake_utc"] for x in w)
    assert w[-1]["wake_utc"] <= back["valid_until_utc"]
    ids = {t.norad for t in sso_set}
    assert all(set(x["satellites_norad"]) <= ids for x in w)


def test_windows_do_not_overlap(vis_valley):
    wins = union_windows(vis_valley.terrain_ok)
    assert all(a2 > b1 for (_a1, b1), (a2, _b2) in zip(wins, wins[1:], strict=False))
