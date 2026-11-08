"""End-to-end measured analysis: every site x orbit set, flat horizon vs terrain mask, latency and energy."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import numpy as np

from .link import LinkParams, max_doppler_khz, min_link_elevation_deg
from .passes import Site, Visibility, compute_visibility, pass_stats
from .sched import (
    DeviceParams,
    SchedulePolicy,
    energy_mah_per_day,
    gateway_contact_index,
    latency_stats,
    simulate_blind,
    simulate_scheduled,
)
from .tle import ORBIT_CLASSES, Tle, select_set

DEFAULT_SETS = {"sso": 24, "mid": 24, "polar": 24}


def default_start(tles: list[Tle]) -> datetime:
    """Newest element-set epoch rounded down to the full hour (UTC)."""
    newest = max(t.epoch for t in tles)
    return newest.replace(minute=0, second=0, microsecond=0).astimezone(UTC)


def build_sets(snapshot: list[Tle], sets: dict[str, int], seed: int = 2026) -> dict[str, list[Tle]]:
    out = {}
    for cls, n in sets.items():
        chosen = select_set(snapshot, cls, n, seed=seed, max_epoch_age_days=2.0)
        if not chosen:
            raise ValueError(f"no satellites of class {cls!r} in this snapshot")
        out[cls] = chosen
    return out


def analyse_site_set(
    tles: list[Tle],
    site: Site,
    start: datetime,
    days: float,
    gen_days: float,
    link: LinkParams,
    dev: DeviceParams,
    pol: SchedulePolicy,
    msgs_per_day: float = 24.0,
    probe_msgs: int = 1500,
    seed: int = 7,
    next_gw: np.ndarray | None = None,
    vis: Visibility | None = None,
) -> tuple[dict, Visibility]:
    vis = vis or compute_visibility(tles, site, start, days, link)
    if next_gw is None:
        next_gw = gateway_contact_index(tles, start, days, vis.step_s)
    ps = pass_stats(vis, days)
    rng = np.random.default_rng(seed)
    out: dict = {"passes": ps, "satellites": len(tles)}
    for tag, usable in (("terrain", vis.terrain_ok), ("flat", vis.link_ok)):
        probe = np.sort(rng.uniform(0, gen_days * 86400, probe_msgs))
        sched = simulate_scheduled(vis, usable, probe, next_gw, pol, np.random.default_rng(seed + 1))
        blind = simulate_blind(vis, usable, probe, next_gw, pol, np.random.default_rng(seed + 2))
        gen = np.sort(rng.uniform(0, gen_days * 86400, int(round(msgs_per_day * gen_days))))
        e_s = simulate_scheduled(vis, usable, gen, next_gw, pol, np.random.default_rng(seed + 3))
        e_b = simulate_blind(vis, usable, gen, next_gw, pol, np.random.default_rng(seed + 4))
        # energy: all bursts of the run divided by the generation days (tail windows only serve leftovers)
        out[tag] = {
            "scheduled": {**latency_stats(sched), **energy_mah_per_day(e_s, gen_days, dev, link)},
            "blind": {**latency_stats(blind), **energy_mah_per_day(e_b, gen_days, dev, link)},
        }
    return out, vis


def run_all(
    snapshot: list[Tle],
    sites: dict[str, Site],
    sets: dict[str, int] | None = None,
    days: float = 7.0,
    gen_days: float = 5.0,
    link: LinkParams | None = None,
    dev: DeviceParams | None = None,
    pol: SchedulePolicy | None = None,
    start: datetime | None = None,
    keep_vis: bool = False,
    msgs_per_day: float = 24.0,
    probe_msgs: int = 1500,
):
    link, dev, pol = link or LinkParams(), dev or DeviceParams(), pol or SchedulePolicy()
    sets = sets or DEFAULT_SETS
    chosen = build_sets(snapshot, sets)
    start = start or default_start([t for v in chosen.values() for t in v])
    results: dict = {
        "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": days,
        "generation_days": gen_days,
        "link": asdict(link),
        "device": asdict(dev),
        "policy": asdict(pol),
        "sets": {},
        "sites": {},
    }
    vis_store: dict = {}
    for cls, tles in chosen.items():
        alts = [t.altitude_km for t in tles]
        mean_alt = float(np.mean(alts))
        results["sets"][cls] = {
            "label": ORBIT_CLASSES[cls]["label"],
            "count": len(tles),
            "norad": [t.norad for t in tles],
            "mean_altitude_km": round(mean_alt, 1),
            "min_link_elevation_deg": min_link_elevation_deg(mean_alt, link),
            "max_doppler_khz": round(max_doppler_khz(mean_alt, link.freq_mhz), 1),
        }
        next_gw = gateway_contact_index(tles, start, days, 10.0)
        for key, site in sites.items():
            r, vis = analyse_site_set(
                tles,
                site,
                start,
                days,
                gen_days,
                link,
                dev,
                pol,
                msgs_per_day=msgs_per_day,
                probe_msgs=probe_msgs,
                next_gw=next_gw,
            )
            results["sites"].setdefault(key, {"label": site.label, "kind": site.kind, "ground_m": site.ground_m, "sets": {}})
            results["sites"][key]["sets"][cls] = r
            if keep_vis:
                vis_store[(key, cls)] = vis
    return (results, chosen, vis_store) if keep_vis else (results, chosen)


def end_of_tail(start: datetime, days: float) -> datetime:
    return start + timedelta(days=days)
