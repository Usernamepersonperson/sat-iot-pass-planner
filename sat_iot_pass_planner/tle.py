"""Two-line element handling: parsing, orbit-class filtering, deterministic sampling, runtime fetch into a local cache.

No orbital data ships with this package. Element sets are downloaded at runtime from CelesTrak into a gitignored
``cache/`` directory (``fetch-tle`` or automatically on first use) and reused while present. Tests and CI use
synthetic element sets (``synthetic.py``) instead.

Satellites are selected by orbital geometry only (inclination, altitude, eccentricity). Object names are dropped when a
snapshot is cached; a satellite is identified by its NORAD catalogue number.
"""

from __future__ import annotations

import gzip
import json
import math
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MU_KM3_S2 = 398600.4418
R_EQ_KM = 6378.137
CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
USER_AGENT = "sat-iot-pass-planner/0.1 (open-source pass planner; +https://github.com/Usernamepersonperson/sat-iot-pass-planner)"
# CelesTrak asks clients not to download the same group more than once per update cycle (about 2 hours).
MIN_REFETCH_S = 2 * 3600
CACHE_ENV = "SAT_IOT_CACHE_DIR"

# Generic LEO orbit classes (inclination range in degrees, mean altitude range in km, max eccentricity).
ORBIT_CLASSES: dict[str, dict] = {
    "sso": {"label": "sun-synchronous class (inc 96-99.5 deg, 450-650 km)", "inc": (96.0, 99.5), "alt": (450.0, 650.0)},
    "mid": {"label": "mid-inclination class (inc 45-60 deg, 450-650 km)", "inc": (45.0, 60.0), "alt": (450.0, 650.0)},
    "polar": {"label": "near-polar class (inc 80-90 deg, 450-900 km)", "inc": (80.0, 90.0), "alt": (450.0, 900.0)},
}
MAX_ECC = 0.02


@dataclass(frozen=True)
class Tle:
    norad: int
    line1: str
    line2: str

    @property
    def inclination_deg(self) -> float:
        return float(self.line2[8:16])

    @property
    def eccentricity(self) -> float:
        return float("0." + self.line2[26:33].strip())

    @property
    def mean_motion_rev_day(self) -> float:
        return float(self.line2[52:63])

    @property
    def altitude_km(self) -> float:
        """Mean altitude from the mean motion (Kepler, equatorial radius)."""
        n = self.mean_motion_rev_day * 2 * math.pi / 86400.0
        return (MU_KM3_S2 / n**2) ** (1 / 3) - R_EQ_KM

    @property
    def epoch(self) -> datetime:
        yy = int(self.line1[18:20])
        day = float(self.line1[20:32])
        year = 2000 + yy if yy < 57 else 1900 + yy
        return datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=day - 1)


def checksum_ok(line: str) -> bool:
    if len(line) < 69 or not line[68].isdigit():
        return False
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10 == int(line[68])


def parse_tle_text(text: str) -> list[Tle]:
    """Parse 2-line or 3-line TLE text. Malformed or checksum-failing sets are skipped."""
    lines = [ln.rstrip("\r\n") for ln in text.splitlines() if ln.strip()]
    out: list[Tle] = []
    i = 0
    while i < len(lines) - 1:
        l1, l2 = lines[i], lines[i + 1]
        if l1.startswith("1 ") and l2.startswith("2 "):
            if checksum_ok(l1) and checksum_ok(l2) and l1[2:7] == l2[2:7]:
                try:
                    out.append(Tle(int(l1[2:7]), l1[:69], l2[:69]))
                except ValueError:
                    pass
            i += 2
        else:
            i += 1
    return out


def in_class(t: Tle, cls: str) -> bool:
    c = ORBIT_CLASSES[cls]
    return (
        c["inc"][0] <= t.inclination_deg <= c["inc"][1]
        and c["alt"][0] <= t.altitude_km <= c["alt"][1]
        and t.eccentricity <= MAX_ECC
    )


def select_set(tles: list[Tle], cls: str, n: int, seed: int = 2026, max_epoch_age_days: float = 5.0) -> list[Tle]:
    """Deterministic random sample of ``n`` satellites of an orbit class with a recent epoch."""
    if cls not in ORBIT_CLASSES:
        raise KeyError(f"unknown orbit class {cls!r}; choose from {sorted(ORBIT_CLASSES)}")
    members = [t for t in tles if in_class(t, cls)]
    if not members:
        return []
    # age is measured against the newest epoch inside the class: a few high orbits in public data carry forward-dated
    # epochs, and those must not push every low-orbit set out of the window
    newest = max(t.epoch for t in members)
    cand = sorted(
        (t for t in members if (newest - t.epoch).total_seconds() <= max_epoch_age_days * 86400),
        key=lambda t: t.norad,
    )
    if n >= len(cand):
        return cand
    return sorted(random.Random(seed).sample(cand, n), key=lambda t: t.norad)


def anonymise(tles: list[Tle]) -> str:
    """3-line text with a neutral name line (``SAT <norad>``)."""
    return "".join(f"SAT {t.norad}\n{t.line1}\n{t.line2}\n" for t in tles)


def cache_dir(override: str | Path | None = None) -> Path:
    """Cache location: explicit override, else ``$SAT_IOT_CACHE_DIR``, else ``./cache`` (gitignored)."""
    if override:
        return Path(override)
    env = os.environ.get(CACHE_ENV)
    return Path(env) if env else Path.cwd() / "cache"


def cache_path(group: str = "active", directory: str | Path | None = None) -> Path:
    return cache_dir(directory) / f"tle_{group}.tle.gz"


def meta_path(path: Path) -> Path:
    return path.with_name(path.name.replace(".tle.gz", ".meta.json"))


class FetchRefused(RuntimeError):
    """Raised when a download would break the source's rate rule or the source returned no element sets."""


def fetch_celestrak(group: str = "active", timeout: float = 60.0, opener=None) -> str:
    """Download one CelesTrak GP group as TLE text, with a User-Agent that names this project.

    ``opener`` is ``urllib.request.urlopen`` by default; tests pass a stub so they never touch the network.
    """
    import urllib.request

    if not group.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"invalid group name {group!r}")
    req = urllib.request.Request(CELESTRAK_URL.format(group=group), headers={"User-Agent": USER_AGENT})
    opener = opener or urllib.request.urlopen
    with opener(req, timeout=timeout) as r:  # noqa: S310 (fixed https host)
        return r.read().decode("utf-8", "replace")


def cache_age_s(path: Path, now: datetime | None = None) -> float | None:
    """Seconds since the cached snapshot was fetched, or None when there is no cache."""
    mp = meta_path(path)
    if not path.exists() or not mp.exists():
        return None
    fetched = datetime.fromisoformat(json.loads(mp.read_text())["fetched_utc"].replace("Z", "+00:00"))
    return ((now or datetime.now(UTC)) - fetched).total_seconds()


def fetch_to_cache(
    group: str = "active", directory: str | Path | None = None, opener=None, now: datetime | None = None
) -> tuple[Path, int]:
    """Download a group into the cache, unless the cached copy is younger than ``MIN_REFETCH_S``.

    Returns (path, number of element sets saved; 0 when the recent cache was kept). This is the only place that talks
    to the network, and it makes at most one request per call.
    """
    path = cache_path(group, directory)
    age = cache_age_s(path, now)
    if age is not None and age < MIN_REFETCH_S:
        return path, 0
    text = fetch_celestrak(group, opener=opener)
    tles = parse_tle_text(text)
    if not tles:
        raise FetchRefused(f"no element sets parsed from CelesTrak (rate limit or bad group?): {text[:200]!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    save_snapshot(tles, "CelesTrak GP data (celestrak.org), TLE format, fetched at runtime", group, path)
    return path, len(tles)


def load_cached(
    group: str = "active", directory: str | Path | None = None, auto_fetch: bool = True, opener=None
) -> tuple[list[Tle], dict]:
    """Load the cached snapshot; on first use (no cache) download it when ``auto_fetch`` is set."""
    path = cache_path(group, directory)
    if not path.exists():
        if not auto_fetch:
            raise FileNotFoundError(
                f"no orbital data in {path}; run `python -m sat_iot_pass_planner fetch-tle` or use --synthetic"
            )
        print(f"no cached orbital data in {path.parent}; downloading group {group!r} from CelesTrak once")
        fetch_to_cache(group, directory, opener=opener)
    return load_snapshot(path)


def save_snapshot(tles: list[Tle], source: str, group: str, path: Path) -> Path:
    """Write a gzip snapshot (names stripped) plus a metadata json next to it."""
    newest = max(t.epoch for t in tles)
    with gzip.open(path, "wt", encoding="ascii", newline="\n") as f:
        f.write(anonymise(tles))
    meta = {
        "source": source,
        "group": group,
        "fetched_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "newest_epoch_utc": newest.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(tles),
        "note": "object names removed; selection in this project uses orbital geometry only",
    }
    meta_path(path).write_text(json.dumps(meta, indent=1))
    return path


def load_snapshot(path: Path) -> tuple[list[Tle], dict]:
    with gzip.open(path, "rt", encoding="ascii") as f:
        tles = parse_tle_text(f.read())
    mp = meta_path(path)
    meta = json.loads(mp.read_text()) if mp.exists() else {}
    return tles, meta
