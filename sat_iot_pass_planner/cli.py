"""Command line: demo, validate, fetch-tle, fetch-terrain, passes, schedule."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .analysis import DEFAULT_SETS, build_sets, default_start, run_all
from .link import LinkParams
from .passes import compute_visibility, extract_passes, load_sites, pass_stats
from .plots import main_figure, post_figure, sky_figure, timeline_figure
from .report import gt_markdown, gt_sweep, policy_markdown, results_markdown, site_report
from .sched import DeviceParams, SchedulePolicy, device_schedule, dump_schedule
from .tle import DATA_DIR, ORBIT_CLASSES, fetch_celestrak, load_snapshot, parse_tle_text, save_snapshot
from .validate import run_validation

SITE_ORDER = ["interlaken_valley", "lauterbrunnen_valley", "eiger_north_face_base", "kleine_scheidegg_saddle", "schilthorn_ridge"]


def _link_from_args(a) -> LinkParams:
    base = LinkParams()
    return replace(
        base,
        eirp_dbm=a.eirp_dbm if a.eirp_dbm is not None else base.eirp_dbm,
        sat_gt_dbk=a.gt_dbk if a.gt_dbk is not None else base.sat_gt_dbk,
        freq_mhz=a.freq_mhz if a.freq_mhz is not None else base.freq_mhz,
        data_rate_bps=a.rate_bps if a.rate_bps is not None else base.data_rate_bps,
    )


def _add_link_args(p):
    p.add_argument("--eirp-dbm", type=float)
    p.add_argument("--gt-dbk", type=float)
    p.add_argument("--freq-mhz", type=float)
    p.add_argument("--rate-bps", type=float)


def cmd_validate(_a) -> int:
    v = run_validation()
    sg, gm = v["sgp4"], v["gmst"]
    print(
        f"SGP4 vs published reference: {sg['cases']} cases, {sg['states_compared']} states, max position error {sg['max_position_error_km']:.2e} km"
    )
    print(f"GMST vs Vallado example 3-5: error {gm['error_deg']:.2e} deg")
    print("PASS" if v["passed"] else "FAIL")
    return 0 if v["passed"] else 1


def cmd_fetch_tle(a) -> int:
    text = fetch_celestrak(a.group)
    tles = parse_tle_text(text)
    if not tles:
        print(
            "no element sets parsed; CelesTrak may be rate-limiting (one request per group per 2 h):", text[:200], file=sys.stderr
        )
        return 1
    path = save_snapshot(tles, "CelesTrak GP data (celestrak.org), TLE format", a.group)
    print(f"saved {len(tles)} element sets to {path}")
    return 0


def cmd_fetch_terrain(_a) -> int:
    import datetime

    from .terrain import fetch_horizon

    sites = json.loads((DATA_DIR / "sites.json").read_text())
    out = {
        "_meta": {
            "source": "swisstopo height profile service (swissALTI3D, 2 m DTM), api3.geo.admin.ch/rest/services/profile.json",
            "licence": "swisstopo OGD, free use with source attribution (Source: swisstopo)",
            "fetched": datetime.date.today().isoformat(),
        }
    }
    for k, s in sites.items():
        out[k] = fetch_horizon(s["lat"], s["lon"])
        print(k, out[k]["ground_elevation_m"], "m")
    (DATA_DIR / "horizons.json").write_text(json.dumps(out, indent=1))
    return 0


def _load(a):
    snap, meta = load_snapshot()
    return snap, meta


def cmd_passes(a) -> int:
    snap, _ = _load(a)
    sites = load_sites()
    link = _link_from_args(a)
    sets = build_sets(snap, {a.set: a.n})
    tles = sets[a.set]
    start = default_start(tles)
    vis = compute_visibility(tles, sites[a.site], start, a.days, link)
    st = pass_stats(vis, a.days)
    print(json.dumps(st, indent=1))
    for p in extract_passes(vis, vis.terrain_ok)[: a.limit]:
        print(
            f"{vis.time_at(p.start_idx):%Y-%m-%d %H:%M:%S}Z  {(p.end_idx - p.start_idx) * vis.step_s:5.0f} s  max el {p.max_el_deg:5.1f}  az {p.az_at_max_deg:5.1f}  sat {tles[p.sat_index].norad}"
        )
    return 0


def cmd_schedule(a) -> int:
    snap, _ = _load(a)
    sites = load_sites()
    link = _link_from_args(a)
    tles = build_sets(snap, {a.set: a.n})[a.set]
    start = default_start(tles)
    vis = compute_visibility(tles, sites[a.site], start, max(a.hours / 24.0, 1.0) + 0.1, link)
    epoch = max(t.epoch for t in tles).strftime("%Y-%m-%dT%H:%M:%SZ")
    sched = device_schedule(vis, vis.terrain_ok, [t.norad for t in tles], SchedulePolicy(), link, DeviceParams(), epoch, a.hours)
    Path(a.out).write_text(dump_schedule(sched))
    print(f"wrote {len(sched['windows'])} windows to {a.out}")
    return 0


def cmd_demo(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fig_dir = Path(a.figures) if a.figures else out
    fig_dir.mkdir(parents=True, exist_ok=True)
    snap, meta = load_snapshot()
    sites = {k: v for k, v in load_sites().items() if k in SITE_ORDER}
    link = _link_from_args(a)
    sets = {k: v for k, v in DEFAULT_SETS.items() if k in snap_classes(snap)}
    gen_days = min(a.gen_days, a.days - 1) if a.days > 1 else a.days
    res, chosen, vis = run_all(snap, sites, sets, days=a.days, gen_days=gen_days, link=link, keep_vis=True, probe_msgs=a.probes)
    res["tle_snapshot"] = meta
    res["horizon_source"] = json.loads((DATA_DIR / "horizons.json").read_text())["_meta"]
    set_key = "sso" if "sso" in chosen else next(iter(chosen))
    # sensitivity to satellite G/T (ridge vs valley)
    pair = {k: vis[(k, set_key)] for k in ("lauterbrunnen_valley", "schilthorn_ridge") if (k, set_key) in vis}
    sweep = gt_sweep(pair, link, a.days, res["sets"][set_key]["mean_altitude_km"]) if pair else []
    res["gt_sweep"] = {"set": set_key, "rows": sweep}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    labels = {k: sites[k].label.split(",")[0] for k in pair}
    md = [
        "# Measured results (simulation)\n",
        results_markdown(res, sites),
        "\n## Scheduled vs blind policy\n",
        policy_markdown(res),
    ]
    if sweep:
        md += [f"\n## Sensitivity to satellite G/T (set `{set_key}`)\n", gt_markdown(sweep, labels)]
    (out / "results.md").write_text("\n".join(md) + "\n")
    sdir = out / "site_reports"
    sdir.mkdir(exist_ok=True)
    for k in sites:
        (sdir / f"{k}.md").write_text(site_report(k, res, sites))
    sched_key = "schilthorn_ridge" if "schilthorn_ridge" in sites else next(iter(sites))
    v0 = vis[(sched_key, set_key)]
    epoch = max(t.epoch for t in chosen[set_key]).strftime("%Y-%m-%dT%H:%M:%SZ")
    sched = device_schedule(
        v0, v0.terrain_ok, [t.norad for t in chosen[set_key]], SchedulePolicy(), link, DeviceParams(), epoch, 48.0
    )
    (out / f"schedule_{sched_key}.json").write_text(dump_schedule(sched))
    timeline_figure(v0, fig_dir / f"timeline_{sched_key}.png")
    sky_figure(v0, fig_dir / f"sky_{sched_key}.png")
    sub = f"Simulated from public orbital elements ({meta.get('newest_epoch_utc', '?')[:10]}) and swisstopo terrain; 24 satellites, {set_key} orbit class"
    order = [k for k in SITE_ORDER if k in sites]
    if {"lauterbrunnen_valley", "schilthorn_ridge"} <= set(sites):
        post_figure(
            vis[("lauterbrunnen_valley", set_key)],
            vis[("schilthorn_ridge", set_key)],
            res["sites"]["lauterbrunnen_valley"]["sets"][set_key]["passes"],
            res["sites"]["schilthorn_ridge"]["sets"][set_key]["passes"],
            fig_dir / "post-figure.png",
            "Simulated: public orbital elements + swisstopo terrain, 24 LEO satellites, 24 h",
        )
        main_figure(vis, res, set_key, fig_dir / "figure.png", sub, order)
    print(md[1][:3000])
    print(f"wrote results to {out}")
    return 0


def snap_classes(snap):
    from .tle import in_class

    return {c for c in ORBIT_CLASSES if any(in_class(t, c) for t in snap)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sat-iot-planner", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check propagation against the published SGP4 verification set").set_defaults(fn=cmd_validate)
    p = sub.add_parser("fetch-tle", help="download a CelesTrak group and store a dated, name-free snapshot")
    p.add_argument("--group", default="active")
    p.set_defaults(fn=cmd_fetch_tle)
    sub.add_parser("fetch-terrain", help="rebuild horizon masks from swisstopo").set_defaults(fn=cmd_fetch_terrain)
    p = sub.add_parser("passes", help="list usable passes for one site")
    p.add_argument("--site", required=True)
    p.add_argument("--set", default="sso", choices=sorted(ORBIT_CLASSES))
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--days", type=float, default=1.0)
    p.add_argument("--limit", type=int, default=20)
    _add_link_args(p)
    p.set_defaults(fn=cmd_passes)
    p = sub.add_parser("schedule", help="write a JSON wake schedule for a device")
    p.add_argument("--site", required=True)
    p.add_argument("--set", default="sso", choices=sorted(ORBIT_CLASSES))
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--hours", type=float, default=48.0)
    p.add_argument("--out", default="schedule.json")
    _add_link_args(p)
    p.set_defaults(fn=cmd_schedule)
    p = sub.add_parser("demo", help="run every site x orbit set and write results and figures")
    p.add_argument("--days", type=float, default=7.0)
    p.add_argument("--gen-days", type=float, default=5.0)
    p.add_argument("--probes", type=int, default=1500)
    p.add_argument("--out", default="results")
    p.add_argument("--figures", default=None, help="directory for figures (default: same as --out)")
    _add_link_args(p)
    p.set_defaults(fn=cmd_demo)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
