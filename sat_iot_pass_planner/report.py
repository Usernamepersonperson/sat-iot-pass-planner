"""Markdown reports and sensitivity sweeps built from the measured results."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .link import LinkParams, margin_db, min_link_elevation_deg
from .passes import Site, Visibility, pass_stats


def horizon_summary(site: Site, min_el_deg: float) -> dict:
    hz = np.asarray(site.horizon_deg, dtype=float)
    return {
        "mean_horizon_deg": float(hz.mean()),
        "max_horizon_deg": float(hz.max()),
        "azimuth_share_blocked_pct": float(100.0 * (hz > min_el_deg).mean()),
    }


def relink(vis: Visibility, link: LinkParams) -> Visibility:
    """The same sky tracks evaluated with other link parameters (no re-propagation)."""
    margin = margin_db(vis.rng, vis.el, link)
    link_ok = vis.horizon_ok & (margin >= link.design_margin_db)
    mask = vis.site.mask(np.nan_to_num(vis.az))
    terrain_ok = link_ok & (vis.el > mask)
    return replace(vis, margin=margin, link_ok=link_ok, terrain_ok=terrain_ok)


def gt_sweep(
    vis_by_site: dict[str, Visibility], base: LinkParams, days: float, alt_km: float, gts=(-24.0, -22.0, -20.0, -18.0, -16.0)
):
    """Passes/day (flat vs terrain) as the satellite G/T, hence the minimum link elevation, changes."""
    rows = []
    for gt in gts:
        lp = replace(base, sat_gt_dbk=gt)
        row = {"sat_gt_dbk": gt, "min_link_elevation_deg": min_link_elevation_deg(alt_km, lp), "sites": {}}
        for key, vis in vis_by_site.items():
            st = pass_stats(relink(vis, lp), days)
            row["sites"][key] = {
                "flat": st["link_flat"]["passes_per_day"],
                "terrain": st["link_terrain"]["passes_per_day"],
                "lost_pct": st["passes_lost_to_terrain_pct"],
            }
        rows.append(row)
    return rows


def _f(x, nd=1):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def results_markdown(results: dict, sites: dict[str, Site]) -> str:
    out = []
    out.append(
        f"Simulation start {results['start_utc']}, {results['days']:g} days propagated, messages generated over the first "
        f"{results['generation_days']:g} days. All numbers are simulated from the stated assumptions.\n"
    )
    for cls, meta in results["sets"].items():
        e = meta["min_link_elevation_deg"]
        out.append(f"### Orbit set `{cls}`: {meta['label']}\n")
        out.append(
            f"{meta['count']} satellites, mean altitude {meta['mean_altitude_km']} km, link closes above "
            f"{_f(e)} deg elevation, max Doppler about {meta['max_doppler_khz']} kHz.\n"
        )
        out.append(
            "| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | "
            "Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |"
        )
        out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for key, srec in results["sites"].items():
            r = srec["sets"][cls]
            hs = horizon_summary(sites[key], e or 0.0)
            s = r["terrain"]["scheduled"]
            out.append(
                f"| {srec['label']} | {srec['ground_m']:.0f} | {hs['mean_horizon_deg']:.1f} / {hs['max_horizon_deg']:.1f} | "
                f"{r['passes']['link_flat']['passes_per_day']:.1f} | {r['passes']['link_terrain']['passes_per_day']:.1f} | "
                f"{r['passes']['passes_lost_to_terrain_pct']:.0f} | {r['passes']['link_terrain']['coverage_minutes_per_day']:.0f} | "
                f"{_f(s['uplink_p50_min'], 0)} / {_f(s['uplink_p95_min'], 0)} | {_f(s['e2e_p50_min'], 0)} / {_f(s['e2e_p95_min'], 0)} | "
                f"{100 * s['delivery_ratio']:.0f} | {s['total_mah_per_day']:.2f} | {s['battery_years']:.1f} |"
            )
        out.append("")
    return "\n".join(out)


def policy_markdown(results: dict) -> str:
    out = [
        "| Orbit set | Site | Policy | Uplink p50/p95 min | Delivered % | mAh/day | Battery years |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for cls in results["sets"]:
        for srec in results["sites"].values():
            for pol in ("scheduled", "blind"):
                s = srec["sets"][cls]["terrain"][pol]
                out.append(
                    f"| {cls} | {srec['label']} | {pol} | {_f(s['uplink_p50_min'], 0)} / {_f(s['uplink_p95_min'], 0)} | "
                    f"{100 * s['delivery_ratio']:.0f} | {s['total_mah_per_day']:.2f} | {s['battery_years']:.1f} |"
                )
    return "\n".join(out)


def site_report(key: str, results: dict, sites: dict[str, Site]) -> str:
    srec = results["sites"][key]
    site = sites[key]
    out = [
        f"# Site report: {srec['label']}\n",
        f"Type: {srec['kind']}. Ground {srec['ground_m']:.0f} m (swissALTI3D), antenna +{site.antenna_height_m:g} m. "
        f"Position {site.lat:.4f} N, {site.lon:.4f} E. Source: swisstopo.\n",
        f"Simulated {results['days']:g} days from {results['start_utc']}. Simulated results, not field measurements.\n",
    ]
    for cls, r in srec["sets"].items():
        e = results["sets"][cls]["min_link_elevation_deg"]
        hs = horizon_summary(site, e or 0.0)
        s = r["terrain"]["scheduled"]
        b = r["terrain"]["blind"]
        out.append(f"## Orbit set `{cls}` ({results['sets'][cls]['count']} satellites)\n")
        out.append(
            f"- Horizon: mean {hs['mean_horizon_deg']:.1f} deg, max {hs['max_horizon_deg']:.1f} deg; {hs['azimuth_share_blocked_pct']:.0f}% of "
            f"azimuths are above the {_f(e)} deg link limit."
        )
        out.append(
            f"- Usable passes/day: {r['passes']['link_flat']['passes_per_day']:.1f} flat horizon, "
            f"{r['passes']['link_terrain']['passes_per_day']:.1f} with terrain ({r['passes']['passes_lost_to_terrain_pct']:.0f}% lost)."
        )
        out.append(
            f"- Message latency (scheduled): uplink p50 {_f(s['uplink_p50_min'], 0)} min, p95 {_f(s['uplink_p95_min'], 0)} min; "
            f"end-to-end p50 {_f(s['e2e_p50_min'], 0)} min, p95 {_f(s['e2e_p95_min'], 0)} min; delivered {100 * s['delivery_ratio']:.0f}%."
        )
        out.append(
            f"- Energy: {s['total_mah_per_day']:.2f} mAh/day, battery about {s['battery_years']:.1f} years "
            f"(blind periodic baseline: {b['total_mah_per_day']:.2f} mAh/day, uplink p50 {_f(b['uplink_p50_min'], 0)} min).\n"
        )
    return "\n".join(out)


def gt_markdown(rows: list[dict], labels: dict[str, str]) -> str:
    keys = list(rows[0]["sites"].keys())
    head = "| G/T dB/K | Link min elevation deg | " + " | ".join(f"{labels[k]} flat / terrain (lost %)" for k in keys) + " |"
    out = [head, "|---:|---:|" + "---:|" * len(keys)]
    for r in rows:
        cells = [f"{r['sites'][k]['flat']:.1f} / {r['sites'][k]['terrain']:.1f} ({r['sites'][k]['lost_pct']:.0f}%)" for k in keys]
        out.append(f"| {r['sat_gt_dbk']:.0f} | {_f(r['min_link_elevation_deg'])} | " + " | ".join(cells) + " |")
    return "\n".join(out)
