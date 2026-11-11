"""Synthetic element sets for tests and offline CI runs.

Every orbit here is made up: altitudes, inclinations, node angles and phases are drawn from a seeded random generator
inside the three generic orbit classes. Nothing describes a real object. The sets are labelled so they cannot be mistaken
for real data: name line ``SYNTHETIC <n>``, international designator field ``SYNTH``, catalogue numbers from 80001.
The lines follow the two-line element layout with correct mod-10 checksums, so the normal parser and SGP4 accept them.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

from .tle import MU_KM3_S2, R_EQ_KM, Tle, parse_tle_text

SYNTHETIC_EPOCH = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
FIRST_NORAD = 80001
SYNTHETIC_DESIGNATOR = "SYNTH"

# Made-up parameter ranges per class: (inclination range deg, altitude range km). They sit inside tle.ORBIT_CLASSES.
SYNTHETIC_CLASSES: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "sso": ((97.2, 97.9), (470.0, 560.0)),
    "mid": ((50.0, 54.0), (480.0, 600.0)),
    "polar": ((85.0, 88.0), (500.0, 850.0)),
}


def checksum(body: str) -> int:
    """TLE mod-10 checksum of the first 68 characters (digits count their value, '-' counts 1)."""
    return sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in body[:68]) % 10


def mean_motion_rev_day(altitude_km: float) -> float:
    a = R_EQ_KM + altitude_km
    return math.sqrt(MU_KM3_S2 / a**3) * 86400.0 / (2 * math.pi)


def _epoch_field(t: datetime) -> str:
    start = datetime(t.year, 1, 1, tzinfo=UTC)
    day = 1.0 + (t - start).total_seconds() / 86400.0
    return f"{t.year % 100:02d}{day:012.8f}"


def _exp_field(x: float) -> str:
    """Assumed-decimal exponent notation used for B* (e.g. 1.5e-4 -> ' 15000-3')."""
    if x == 0:
        return " 00000-0"
    sign = "-" if x < 0 else " "
    e = math.floor(math.log10(abs(x))) + 1
    mant = round(abs(x) / 10**e * 1e5)
    if mant >= 100000:
        mant, e = mant // 10, e + 1
    es = f"{'-' if e < 0 else '+'}{abs(e)}"
    return f"{sign}{mant:05d}{es}"


def make_tle(
    norad: int,
    epoch: datetime,
    inclination_deg: float,
    raan_deg: float,
    eccentricity: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    mean_motion: float,
    bstar: float = 1.0e-4,
    element_number: int = 999,
    rev_number: int = 1000,
) -> Tle:
    """Build one element set from orbital parameters, with valid layout and checksums."""
    if not 0 < norad < 100000:
        raise ValueError("catalogue number must have at most 5 digits")
    if not 0 <= eccentricity < 1:
        raise ValueError("eccentricity must be in [0, 1)")
    if not 0 <= inclination_deg <= 180:
        raise ValueError("inclination must be in [0, 180] deg")
    ecc = f"{round(eccentricity * 1e7):07d}"
    b1 = (
        f"1 {norad:05d}U {SYNTHETIC_DESIGNATOR:<8} {_epoch_field(epoch)}  .00000000  00000-0 {_exp_field(bstar)} 0 "
        f"{element_number % 10000:4d}"
    )
    b2 = (
        f"2 {norad:05d} {inclination_deg:8.4f} {raan_deg % 360:8.4f} {ecc} {arg_perigee_deg % 360:8.4f} "
        f"{mean_anomaly_deg % 360:8.4f} {mean_motion:11.8f}{rev_number % 100000:5d}"
    )
    assert len(b1) == 68 and len(b2) == 68, (len(b1), len(b2))
    return Tle(norad, b1 + str(checksum(b1)), b2 + str(checksum(b2)))


def synthetic_tles(per_class: int = 40, seed: int = 1, epoch: datetime = SYNTHETIC_EPOCH) -> list[Tle]:
    """Deterministic made-up constellation: ``per_class`` satellites in each generic orbit class."""
    rng = random.Random(seed)
    out: list[Tle] = []
    norad = FIRST_NORAD
    for _cls, (inc, alt) in SYNTHETIC_CLASSES.items():
        for _ in range(per_class):
            out.append(
                make_tle(
                    norad,
                    epoch - timedelta(hours=rng.uniform(0.0, 20.0)),
                    rng.uniform(*inc),
                    rng.uniform(0, 360),
                    rng.uniform(0.0001, 0.002),
                    rng.uniform(0, 360),
                    rng.uniform(0, 360),
                    mean_motion_rev_day(rng.uniform(*alt)),
                    bstar=rng.uniform(0.5e-4, 3e-4),
                    rev_number=rng.randint(1000, 40000),
                )
            )
            norad += 1
    return out


def synthetic_text(tles: list[Tle]) -> str:
    return "".join(f"SYNTHETIC {t.norad}\n{t.line1}\n{t.line2}\n" for t in tles)


def load_synthetic(per_class: int = 40, seed: int = 1) -> tuple[list[Tle], dict]:
    """Synthetic set plus metadata in the same shape as a cached snapshot."""
    tles = parse_tle_text(synthetic_text(synthetic_tles(per_class, seed)))
    newest = max(t.epoch for t in tles)
    meta = {
        "source": "SYNTHETIC element sets generated from made-up orbital parameters (not real objects)",
        "group": "synthetic",
        "fetched_utc": None,
        "newest_epoch_utc": newest.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(tles),
        "synthetic": True,
        "seed": seed,
    }
    return tles, meta
