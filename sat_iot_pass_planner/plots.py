"""Figures: sky plots with terrain horizon and pass tracks, valley vs ridge, timelines, summary figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from .passes import Visibility, union_windows  # noqa: E402

BG, GRID, TEXT, MUTED = "#16213A", "#2A3750", "#F8FAFC", "#A9B6CB"
ACCENT, GREEN, AMBER, RED, GREY, VIOLET = "#38BDF8", "#34D399", "#FBBF24", "#F87171", "#64748B", "#A78BFA"


def _font() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    return "Segoe UI" if "Segoe UI" in names else "DejaVu Sans"


def style():
    plt.rcParams.update(
        {
            "font.family": _font(),
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": TEXT,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": GRID,
            "grid.color": GRID,
        }
    )


def sky_axes(ax, labels=True, fs=11):
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    ax.set_yticks([30, 60])
    ax.set_yticklabels([])
    ax.set_xticks(np.radians([0, 90, 180, 270]))
    ax.set_xticklabels(["N", "E", "S", "W"] if labels else [], fontsize=fs, color=MUTED)
    ax.tick_params(axis="x", pad=-1)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.spines["polar"].set_color(GRID)
    ax.set_facecolor(BG)


def draw_sky(ax, vis: Visibility, hours: float = 24.0, lw: float = 1.6, labels=True, fs=11, show_flat=False):
    """Polar sky plot: terrain horizon (blocked region), pass tracks green where usable, red where terrain/link blocks them."""
    sky_axes(ax, labels, fs)
    site = vis.site
    az = np.arange(0, 361, 1.0)
    hz = np.clip(site.mask(az), 0, 90)
    ax.fill_between(np.radians(az), 90 - hz, 90, color=GREY, alpha=0.75, linewidth=0, zorder=2)
    ax.plot(np.radians(az), 90 - hz, color=AMBER, linewidth=1.4, zorder=3)
    n = int(hours * 3600 / vis.step_s)
    link_el = float(np.nanmin(vis.el[vis.link_ok])) if vis.link_ok.any() else 0.0
    ax.plot(
        np.radians(np.linspace(0, 360, 361)),
        np.full(361, 90 - link_el),
        color=MUTED,
        linewidth=1.0,
        linestyle=(0, (4, 4)),
        zorder=3,
    )
    for s in range(vis.n_sat):
        a = vis.az[s, :n]
        up = vis.link_ok[s, :n]
        if not up.any():
            continue
        ok = vis.terrain_ok[s, :n]
        r = 90 - vis.el[s, :n]
        th = np.radians(a)
        wrap = np.r_[False, np.abs(np.diff(a)) > 180]  # no spokes where azimuth wraps
        for sel, col, z in ((up & ~ok, RED, 4), (ok, GREEN, 5)):
            ax.plot(th, np.where(sel & ~wrap, r, np.nan), color=col, linewidth=lw, alpha=0.95, zorder=z, solid_capstyle="round")
    ax.set_ylim(0, 90)


def timeline(ax, vis: Visibility, hours: float = 24.0):
    """Coverage bars over time: geometric passes (grey), link-limited flat (violet), with terrain (green)."""
    n = int(hours * 3600 / vis.step_s)
    t = np.arange(n) * vis.step_s / 3600.0
    for row, (m, col, lab) in enumerate(
        ((vis.horizon_ok, GREY, "geometric"), (vis.link_ok, VIOLET, "link, flat"), (vis.terrain_ok, GREEN, "link + terrain"))
    ):
        u = m[:, :n].any(axis=0)
        for a, b in union_windows(m[:, :n]):
            ax.barh(row, (b - a) * vis.step_s / 3600.0, left=t[a], height=0.7, color=col)
        ax.text(hours + 0.2, row, lab, va="center", color=MUTED, fontsize=11)
        del u
    ax.set_yticks([])
    ax.set_xlim(0, hours)
    ax.set_xlabel("hours since start (UTC)")
    ax.grid(True, axis="x")


def save_fig(fig, path: Path, w_px: int, h_px: int):
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
    _check_size(path, w_px, h_px)


def _check_size(path: Path, w: int, h: int):
    from matplotlib.image import imread

    im = imread(path)
    if im.shape[0] != h or im.shape[1] != w:
        raise RuntimeError(f"{path} is {im.shape[1]}x{im.shape[0]}, expected {w}x{h}")


def post_figure(vis_valley: Visibility, vis_ridge: Visibility, stats_valley: dict, stats_ridge: dict, path: Path, subtitle: str):
    """960x700 phone-sized hook: sky plots of a valley floor and a ridge top with terrain horizon and pass tracks."""
    style()
    fig = plt.figure(figsize=(9.6, 7.0), dpi=100, facecolor=BG)
    fig.text(0.04, 0.945, "Same sky, different terrain: valley vs ridge", fontsize=19, fontweight="bold", color=TEXT, va="center")
    fig.text(0.04, 0.895, subtitle, fontsize=12, color=MUTED, va="center")
    for i, (vis, st, title) in enumerate(
        ((vis_valley, stats_valley, vis_valley.site.label), (vis_ridge, stats_ridge, vis_ridge.site.label))
    ):
        ax = fig.add_axes([0.04 + i * 0.49, 0.20, 0.43, 0.54], projection="polar")
        draw_sky(ax, vis, hours=24, lw=2.2, fs=14)
        fig.text(0.255 + i * 0.49, 0.80, title, ha="center", fontsize=15, fontweight="bold", color=TEXT)
        fig.text(
            0.255 + i * 0.49,
            0.145,
            f"{st['link_terrain']['passes_per_day']:.1f} usable passes/day",
            ha="center",
            fontsize=17,
            fontweight="bold",
            color=GREEN if i == 1 else AMBER,
        )
        fig.text(
            0.255 + i * 0.49,
            0.095,
            f"flat horizon: {st['link_flat']['passes_per_day']:.1f}",
            ha="center",
            fontsize=15,
            color=MUTED,
        )
    fig.text(0.04, 0.035, "green: usable   red: hidden behind terrain   dashed ring: link limit", fontsize=13, color=MUTED)
    save_fig(fig, path, 960, 700)


def main_figure(visibility: dict, results: dict, set_key: str, path: Path, subtitle: str, order: list[str]):
    """1600x900: row of sky plots, passes/day flat vs terrain, latency p50/p95."""
    style()
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
    fig.text(
        0.03,
        0.955,
        "Direct-to-satellite IoT uplink: what terrain does to pass opportunities",
        fontsize=22,
        fontweight="bold",
        color=TEXT,
        va="center",
    )
    fig.text(0.03, 0.915, subtitle, fontsize=13, color=MUTED, va="center")
    n = len(order)
    for i, key in enumerate(order):
        vis = visibility[(key, set_key)]
        ax = fig.add_axes([0.02 + i * (0.96 / n), 0.50, 0.96 / n - 0.01, 0.34], projection="polar")
        draw_sky(ax, vis, hours=24, lw=1.4, fs=10, labels=False)
        st = results["sites"][key]["sets"][set_key]["passes"]
        fig.text(
            0.02 + (i + 0.5) * (0.96 / n) - 0.005,
            0.875,
            vis.site.label.split(",")[0],
            ha="center",
            fontsize=14,
            fontweight="bold",
            color=TEXT,
        )
        fig.text(
            0.02 + (i + 0.5) * (0.96 / n) - 0.005,
            0.47,
            f"{vis.site.ground_m:.0f} m, {vis.site.kind}",
            ha="center",
            fontsize=11,
            color=MUTED,
        )
        del st
    names = [visibility[(k, set_key)].site.label.split(",")[0] for k in order]
    x = np.arange(n)
    ax1 = fig.add_axes([0.06, 0.09, 0.40, 0.31])
    flat = [results["sites"][k]["sets"][set_key]["passes"]["link_flat"]["passes_per_day"] for k in order]
    terr = [results["sites"][k]["sets"][set_key]["passes"]["link_terrain"]["passes_per_day"] for k in order]
    ax1.bar(x - 0.2, flat, 0.38, color=VIOLET, label="flat horizon")
    ax1.bar(x + 0.2, terr, 0.38, color=GREEN, label="with terrain mask")
    for xi, v in zip(x, terr, strict=True):
        ax1.text(xi + 0.2, v + 0.15, f"{v:.1f}", ha="center", color=TEXT, fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels([n_.replace(" ", "\n", 1) for n_ in names], fontsize=10)
    ax1.set_ylabel("usable passes per day", fontsize=12)
    ax1.set_ylim(0, max(flat) * 1.3)
    ax1.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=11, loc="upper left", ncol=2)
    ax1.grid(True, axis="y")
    ax1.set_axisbelow(True)
    ax2 = fig.add_axes([0.56, 0.09, 0.41, 0.31])
    p50 = [results["sites"][k]["sets"][set_key]["terrain"]["scheduled"]["e2e_p50_min"] for k in order]
    p95 = [results["sites"][k]["sets"][set_key]["terrain"]["scheduled"]["e2e_p95_min"] for k in order]
    ax2.bar(x - 0.2, p50, 0.38, color=ACCENT, label="p50")
    ax2.bar(x + 0.2, p95, 0.38, color=AMBER, label="p95")
    ax2.set_xticks(x)
    ax2.set_xticklabels([n_.replace(" ", "\n", 1) for n_ in names], fontsize=10)
    ax2.set_ylabel("message latency, minutes", fontsize=12)
    ax2.set_ylim(0, max(p95) * 1.3)
    ax2.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=11, loc="upper left", ncol=2)
    ax2.grid(True, axis="y")
    ax2.set_axisbelow(True)
    for a in (ax1, ax2):
        for sp in a.spines.values():
            sp.set_color(GRID)
    fig.text(
        0.03,
        0.025,
        "Sky plots: first 24 h. Green = usable track, red = hidden behind terrain, grey = terrain, dashed = link limit. End-to-end latency incl. store-and-forward to a gateway.",
        fontsize=11,
        color=MUTED,
    )
    save_fig(fig, path, 1600, 900)


def timeline_figure(vis: Visibility, path: Path, hours: float = 24.0):
    style()
    fig, ax = plt.subplots(figsize=(10, 2.6), dpi=100, facecolor=BG)
    timeline(ax, vis, hours)
    ax.set_title(f"{vis.site.label}: contact windows", loc="left", color=TEXT, fontsize=14, fontweight="bold")
    fig.subplots_adjust(left=0.03, right=0.84, bottom=0.25, top=0.85)
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)


def sky_figure(vis: Visibility, path: Path, hours: float = 24.0):
    style()
    fig = plt.figure(figsize=(6, 6), dpi=100, facecolor=BG)
    ax = fig.add_axes([0.08, 0.06, 0.84, 0.80], projection="polar")
    draw_sky(ax, vis, hours=hours, lw=1.8, fs=13)
    fig.text(0.05, 0.94, vis.site.label, fontsize=15, fontweight="bold", color=TEXT)
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
