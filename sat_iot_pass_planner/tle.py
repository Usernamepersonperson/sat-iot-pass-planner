"""Two-line element handling: parsing, orbit-class filtering, deterministic sampling, dated offline snapshots.

Satellites are selected by orbital geometry only (inclination, altitude, eccentricity). Object names are dropped when a
snapshot is stored; a satellite is identified by its NORAD catalogue number.
"""

from __future__ import annotations

import gzip
import json
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MU_KM3_S2 = 398600.4418
R_EQ_KM = 6378.137
CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"

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
    if not tles:
        return []
    newest = max(t.epoch for t in tles)
    cand = sorted(
        (t for t in tles if in_class(t, cls) and (newest - t.epoch).total_seconds() <= max_epoch_age_days * 86400),
        key=lambda t: t.norad,
    )
    if n >= len(cand):
        return cand
    return sorted(random.Random(seed).sample(cand, n), key=lambda t: t.norad)


def anonymise(tles: list[Tle]) -> str:
    """3-line text with a neutral name line (``SAT <norad>``)."""
    return "".join(f"SAT {t.norad}\n{t.line1}\n{t.line2}\n" for t in tles)


def fetch_celestrak(group: str = "active", timeout: float = 60.0) -> str:
    """Download one CelesTrak GP group as TLE text (CelesTrak asks for at most one request per group per 2 hours)."""
    import urllib.request

    with urllib.request.urlopen(CELESTRAK_URL.format(group=group), timeout=timeout) as r:  # noqa: S310 (fixed https host)
        return r.read().decode("utf-8", "replace")


def save_snapshot(tles: list[Tle], source: str, group: str, path: Path | None = None) -> Path:
    """Write a gzip snapshot (names stripped) plus a metadata json next to it."""
    path = path or DATA_DIR / "tle_snapshot.tle.gz"
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
    path.with_name("tle_snapshot.meta.json").write_text(json.dumps(meta, indent=1))
    return path


def load_snapshot(path: Path | None = None) -> tuple[list[Tle], dict]:
    path = path or DATA_DIR / "tle_snapshot.tle.gz"
    with gzip.open(path, "rt", encoding="ascii") as f:
        tles = parse_tle_text(f.read())
    meta_path = path.with_name("tle_snapshot.meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    return tles, meta
