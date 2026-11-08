"""Sites, terrain-masked visibility and pass extraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from .link import LinkParams, margin_db
from .propagate import sky_track, time_grid
from .terrain import mask_at
from .tle import DATA_DIR, Tle

STEP_S = 10.0


@dataclass(frozen=True)
class Site:
    key: str
    label: str
    kind: str
    lat: float
    lon: float
    ground_m: float
    step_deg: float
    horizon_deg: tuple[float, ...]
    antenna_height_m: float = 2.0

    @property
    def alt_m(self) -> float:
        return self.ground_m + self.antenna_height_m

    def mask(self, az_deg):
        """Terrain horizon elevation (deg) at the given azimuth(s); a flat site returns zeros."""
        if not self.horizon_deg:
            return np.zeros_like(np.asarray(az_deg, dtype=float))
        return mask_at(az_deg, self.horizon_deg, self.step_deg)


def flat_site(lat: float, lon: float, alt_m: float = 0.0, key: str = "flat", label: str = "Flat horizon") -> Site:
    return Site(key, label, "flat horizon", lat, lon, alt_m, 2.0, ())


def load_sites(sites_path: Path | None = None, horizons_path: Path | None = None) -> dict[str, Site]:
    sites = json.loads((sites_path or DATA_DIR / "sites.json").read_text())
    hz = json.loads((horizons_path or DATA_DIR / "horizons.json").read_text())
    out = {}
    for k, s in sites.items():
        h = hz[k]
        out[k] = Site(
            k, s["label"], s["kind"], s["lat"], s["lon"], h["ground_elevation_m"], h["step_deg"], tuple(h["horizon_deg"])
        )
    return out


@dataclass
class Visibility:
    """Everything the later stages need for one site and one satellite set."""

    site: Site
    start: datetime
    step_s: float
    az: np.ndarray  # (n_sat, n_t)
    el: np.ndarray
    rng: np.ndarray
    margin: np.ndarray
    link_ok: np.ndarray  # margin >= design margin and above the geometric horizon
    terrain_ok: np.ndarray  # link_ok and above the terrain mask
    horizon_ok: np.ndarray  # above the geometric horizon only

    @property
    def n_t(self) -> int:
        return self.az.shape[1]

    @property
    def n_sat(self) -> int:
        return self.az.shape[0]

    def time_at(self, idx: int) -> datetime:
        return self.start + timedelta(seconds=float(idx) * self.step_s)


def compute_visibility(
    tles: list[Tle], site: Site, start: datetime, days: float, link: LinkParams, step_s: float = STEP_S
) -> Visibility:
    jd, fr = time_grid(start, days, step_s)
    az, el, rng = sky_track(tles, jd, fr, site.lat, site.lon, site.alt_m)
    margin = margin_db(rng, el, link)
    finite = np.isfinite(el)
    above = finite & (el > 0.0)
    link_ok = above & (margin >= link.design_margin_db)
    mask = site.mask(np.nan_to_num(az))
    terrain_ok = link_ok & (el > mask)
    return Visibility(site, start, step_s, az, el, rng, margin, link_ok, terrain_ok, above)


def runs(b: np.ndarray) -> list[tuple[int, int]]:
    """Maximal True runs of a 1-D boolean array as (start, end_exclusive)."""
    b = np.asarray(b, dtype=bool)
    if b.size == 0:
        return []
    d = np.diff(np.concatenate(([0], b.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist(), strict=True))


@dataclass(frozen=True)
class Pass:
    sat_index: int
    start_idx: int
    end_idx: int  # exclusive
    max_el_deg: float
    az_at_max_deg: float


def extract_passes(vis: Visibility, usable: np.ndarray) -> list[Pass]:
    out = []
    for s in range(vis.n_sat):
        for a, b in runs(usable[s]):
            seg = np.nan_to_num(vis.el[s, a:b], nan=-90.0)
            j = int(np.argmax(seg))
            out.append(Pass(s, a, b, float(seg[j]), float(vis.az[s, a + j])))
    out.sort(key=lambda p: p.start_idx)
    return out


def union_windows(usable: np.ndarray) -> list[tuple[int, int]]:
    """Time windows in which at least one satellite is usable."""
    return runs(usable.any(axis=0))


def pass_stats(vis: Visibility, days: float, min_window_s: float = 40.0) -> dict:
    """Passes/day and usable minutes/day for three horizons: geometric, link-limited flat, link-limited with terrain.

    A *usable pass* is one satellite pass whose link-closing part lasts at least ``min_window_s`` (enough for two bursts).
    Terrain is applied inside each link-limited pass, so a pass cut in two by a ridge is still one pass and the
    terrain count can never exceed the flat count.
    """
    out = {}
    for name, m in (("geometric", vis.horizon_ok), ("link_flat", vis.link_ok), ("link_terrain", vis.terrain_ok)):
        out[name] = {
            "sat_minutes_per_day": float(m.sum()) * vis.step_s / 60.0 / days,
            "coverage_minutes_per_day": float(m.any(axis=0).sum()) * vis.step_s / 60.0 / days,
        }
    out["geometric"]["passes_per_day"] = len(extract_passes(vis, vis.horizon_ok)) / days
    flat = terr = 0
    for s in range(vis.n_sat):
        for a, b in runs(vis.link_ok[s]):
            flat += (b - a) * vis.step_s >= min_window_s
            terr += float(vis.terrain_ok[s, a:b].sum()) * vis.step_s >= min_window_s
    out["link_flat"]["passes_per_day"] = flat / days
    out["link_terrain"]["passes_per_day"] = terr / days
    out["passes_lost_to_terrain_pct"] = 100.0 * (1 - terr / flat) if flat > 0 else 0.0
    return out
