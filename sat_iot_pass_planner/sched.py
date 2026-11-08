"""Store-and-forward scheduling, latency and battery budget for an uplink-only device.

Model (all stated assumptions, see README):

* The device has no downlink, so it never learns whether a burst was received. It repeats instead of retrying on ack.
* A burst is heard when at least one satellite is usable (link margin and terrain mask) at that moment, and then with
  probability ``p_burst`` (collisions with other devices, residual Doppler error). The strongest satellite hears it.
* The satellite stores the message and delivers it at its next contact with a ground gateway (store-and-forward).
* A burst carries every message that is pending at that moment (batching, payload limit not binding).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import timedelta

import numpy as np

from .link import LinkParams, airtime_s
from .passes import Visibility, runs, union_windows
from .propagate import sky_track, time_grid
from .tle import Tle

# Two generic gateways: a high-latitude northern station and a mid-latitude southern-hemisphere station (lat, lon, alt m). Assumption.
DEFAULT_GATEWAYS = ((78.2, 15.4, 50.0), (-33.9, 151.2, 50.0))
GATEWAY_MIN_EL_DEG = 5.0


@dataclass(frozen=True)
class DeviceParams:
    tx_current_ma: float = 45.0  # transceiver at +14 dBm, typical order of magnitude
    wake_current_ma: float = 10.0
    wake_s: float = 3.0  # MCU + radio start-up, clock check per wake
    sleep_ua: float = 8.0
    payload_bytes: int = 24
    overhead_bytes: int = 16
    battery_mah: float = 3000.0  # primary lithium cells, rail-referred
    battery_usable_fraction: float = 0.6  # cold derating + self-discharge reserve


@dataclass(frozen=True)
class SchedulePolicy:
    burst_count: int = 3  # bursts per usable window
    burst_spacing_s: float = 20.0
    windows_per_message: int = 2  # each message is offered in this many windows (no acks)
    p_burst: float = 0.7  # reception probability of one burst while a satellite is usable
    blind_interval_s: float = 900.0  # baseline: transmit every 15 min with no pass knowledge
    blind_hold_h: float = 6.0  # baseline: keep repeating a message this long


def gateway_contact_index(
    tles: list[Tle], start, days: float, step_s: float, gateways=DEFAULT_GATEWAYS, min_el: float = GATEWAY_MIN_EL_DEG
) -> np.ndarray:
    """next_idx[s, t] = first time index >= t at which satellite s sees any gateway, or n_t when it never does."""
    jd, fr = time_grid(start, days, step_s)
    n_t = jd.size
    ok = np.zeros((len(tles), n_t), dtype=bool)
    for lat, lon, alt in gateways:
        _az, el, _r = sky_track(tles, jd, fr, lat, lon, alt)
        ok |= np.nan_to_num(el, nan=-90.0) >= min_el
    idx = np.where(ok, np.arange(n_t)[None, :], n_t)
    return np.minimum.accumulate(idx[:, ::-1], axis=1)[:, ::-1]


@dataclass
class SimResult:
    delivered: np.ndarray  # bool per message
    up_latency_s: np.ndarray  # NaN when not delivered
    e2e_latency_s: np.ndarray  # NaN when not delivered or not forwarded within the simulation
    windows_used: int
    bursts: int
    wakes: int


def _result(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.zeros(n, dtype=bool), np.full(n, np.nan), np.full(n, np.nan)


def _record(i_msgs, t_burst_s, sat, idx, g, next_gw, step_s, delivered, up, e2e):
    n_t = next_gw.shape[1]
    gw_idx = next_gw[sat, idx]
    for m in i_msgs:
        delivered[m] = True
        up[m] = t_burst_s - g[m]
        if gw_idx < n_t:
            e2e[m] = max(t_burst_s, gw_idx * step_s) - g[m]


def simulate_scheduled(
    vis: Visibility, usable: np.ndarray, gen_s: np.ndarray, next_gw: np.ndarray, pol: SchedulePolicy, rng: np.random.Generator
) -> SimResult:
    """Pass-aware policy: wake only at predicted usable windows and send ``burst_count`` bursts."""
    g = np.asarray(gen_s, dtype=float)
    delivered, up, e2e = _result(g.size)
    wins_used = np.zeros(g.size, dtype=int)
    step = vis.step_s
    spacing = max(1, int(round(pol.burst_spacing_s / step)))
    n_win = n_bursts = 0
    for ws, we in union_windows(usable):
        tx_in_window = False
        attempted = np.zeros(g.size, dtype=bool)
        for k in range(pol.burst_count):
            idx = ws + k * spacing
            if idx >= we:
                break
            t_b = idx * step
            elig = np.flatnonzero(~delivered & (g <= t_b) & (wins_used < pol.windows_per_message))
            if elig.size == 0:
                continue
            tx_in_window = True
            n_bursts += 1
            attempted[elig] = True
            if rng.random() < pol.p_burst:
                active = np.flatnonzero(usable[:, idx])
                sat = int(active[np.argmax(vis.margin[active, idx])])
                _record(elig, t_b, sat, idx, g, next_gw, step, delivered, up, e2e)
        wins_used[attempted & ~delivered] += 1
        n_win += tx_in_window
    return SimResult(delivered, up, e2e, n_win, n_bursts, n_win)


def simulate_blind(
    vis: Visibility, usable: np.ndarray, gen_s: np.ndarray, next_gw: np.ndarray, pol: SchedulePolicy, rng: np.random.Generator
) -> SimResult:
    """Baseline without pass knowledge: periodic bursts while a message is pending, for at most ``blind_hold_h``."""
    g = np.asarray(gen_s, dtype=float)
    delivered, up, e2e = _result(g.size)
    step = vis.step_s
    any_usable = usable.any(axis=0)
    hold = pol.blind_hold_h * 3600.0
    n_bursts = 0
    t = float(rng.uniform(0, pol.blind_interval_s))
    end = vis.n_t * step
    while t < end:
        elig = np.flatnonzero(~delivered & (g <= t) & (t <= g + hold))
        if elig.size:
            n_bursts += 1
            idx = min(int(round(t / step)), vis.n_t - 1)
            if any_usable[idx] and rng.random() < pol.p_burst:
                active = np.flatnonzero(usable[:, idx])
                sat = int(active[np.argmax(vis.margin[active, idx])])
                _record(elig, t, sat, idx, g, next_gw, step, delivered, up, e2e)
        t += pol.blind_interval_s
    return SimResult(delivered, up, e2e, n_bursts, n_bursts, n_bursts)


def energy_mah_per_day(res: SimResult, days: float, dev: DeviceParams, link: LinkParams) -> dict:
    tx_s = airtime_s(dev.payload_bytes, dev.overhead_bytes, link)
    tx = res.bursts * tx_s * dev.tx_current_ma / 3600.0
    wake = res.wakes * dev.wake_s * dev.wake_current_ma / 3600.0
    sleep = dev.sleep_ua / 1000.0 * 24.0 * days
    total = (tx + wake + sleep) / days
    life_days = dev.battery_mah * dev.battery_usable_fraction / total if total > 0 else float("inf")
    return {
        "tx_mah_per_day": tx / days,
        "wake_mah_per_day": wake / days,
        "sleep_mah_per_day": sleep / days,
        "total_mah_per_day": total,
        "battery_years": life_days / 365.0,
        "burst_airtime_s": tx_s,
    }


def latency_stats(res: SimResult) -> dict:
    def pct(a, q):
        a = a[np.isfinite(a)]
        return float(np.percentile(a, q)) / 60.0 if a.size else float("nan")

    return {
        "delivery_ratio": float(res.delivered.mean()) if res.delivered.size else 0.0,
        "uplink_p50_min": pct(res.up_latency_s, 50),
        "uplink_p95_min": pct(res.up_latency_s, 95),
        "e2e_p50_min": pct(res.e2e_latency_s, 50),
        "e2e_p95_min": pct(res.e2e_latency_s, 95),
    }


def device_schedule(
    vis: Visibility,
    usable: np.ndarray,
    norad_ids: list[int],
    pol: SchedulePolicy,
    link: LinkParams,
    dev: DeviceParams,
    tle_epoch_utc: str,
    valid_hours: float = 48.0,
) -> dict:
    """JSON-serialisable wake schedule for one device: one entry per usable window with burst times."""
    step = vis.step_s
    spacing = max(1, int(round(pol.burst_spacing_s / step)))
    horizon_idx = int(valid_hours * 3600 / step)
    wins = []
    for ws, we in union_windows(usable):
        if ws > horizon_idx:
            break
        sats = np.flatnonzero(usable[:, ws:we].any(axis=1))
        max_el = float(np.nanmax(np.where(usable[:, ws:we], vis.el[:, ws:we], -90.0)))
        bursts = [
            vis.time_at(ws + k * spacing).strftime("%Y-%m-%dT%H:%M:%SZ") for k in range(pol.burst_count) if ws + k * spacing < we
        ]
        wins.append(
            {
                "wake_utc": vis.time_at(ws).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_utc": vis.time_at(we).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration_s": int((we - ws) * step),
                "max_elevation_deg": round(max_el, 1),
                "satellites_norad": [norad_ids[s] for s in sats],
                "burst_utc": bursts,
            }
        )
    return {
        "site": {"key": vis.site.key, "label": vis.site.label, "lat": vis.site.lat, "lon": vis.site.lon, "alt_m": vis.site.alt_m},
        "generated_for_start_utc": vis.start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_until_utc": (vis.start + timedelta(hours=valid_hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tle_newest_epoch_utc": tle_epoch_utc,
        "note": "Regenerate when element sets are older than about 3 days; times are predictions, keep a margin around each window.",
        "link": asdict(link),
        "device": asdict(dev),
        "policy": asdict(pol),
        "windows": wins,
    }


def dump_schedule(sched: dict) -> str:
    return json.dumps(sched, indent=1)


__all__ = ["runs"]
