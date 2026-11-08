"""Link budget for a generic direct-to-satellite IoT uplink (low-rate, sub-GHz, small omni-directional device antenna).

All defaults are *typical* values for this class of link and are assumptions, not the specification of any service:

* device EIRP 16 dBm (14 dBm conducted + 2 dBi antenna), the usual order of magnitude for battery sub-GHz radios
* satellite receive G/T -20 dB/K, a small-satellite UHF/ISM antenna with a low-noise front end
* 868 MHz carrier, 300 bit/s coded uplink, required Eb/N0 5 dB (typical for strongly coded low-rate modulation)
* 2 dB implementation loss, 3 dB polarisation / pointing loss, 0.2 dB zenith atmospheric loss (scaled by 1/sin(el))
* 3 dB design margin that the link must keep to count as usable

Change them with ``LinkParams`` or on the command line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

BOLTZMANN_DBW = -228.6  # 10 log10(k), dBW/Hz/K
C_KM_S = 299792.458
R_EQ_KM = 6378.137


@dataclass(frozen=True)
class LinkParams:
    freq_mhz: float = 868.0
    eirp_dbm: float = 16.0
    sat_gt_dbk: float = -20.0
    data_rate_bps: float = 300.0
    req_ebn0_db: float = 5.0
    impl_loss_db: float = 2.0
    pol_pointing_loss_db: float = 3.0
    atmos_zenith_db: float = 0.2
    design_margin_db: float = 3.0

    def __post_init__(self):
        if self.freq_mhz <= 0 or self.data_rate_bps <= 0:
            raise ValueError("frequency and data rate must be positive")


def fspl_db(range_km: np.ndarray | float, freq_mhz: float) -> np.ndarray | float:
    """Free-space path loss: 32.44 + 20 log10(f/MHz) + 20 log10(d/km)."""
    return 32.44 + 20 * np.log10(freq_mhz) + 20 * np.log10(range_km)


def slant_range_km(elevation_deg: np.ndarray | float, altitude_km: float) -> np.ndarray | float:
    """Slant range to a satellite on a circular orbit seen at the given elevation (spherical Earth)."""
    el = np.radians(elevation_deg)
    r = R_EQ_KM
    return np.sqrt((r + altitude_km) ** 2 - (r * np.cos(el)) ** 2) - r * np.sin(el)


def margin_db(range_km, elevation_deg, p: LinkParams = LinkParams()):
    """Link margin (dB) over the required C/N0. Works on scalars or arrays."""
    eirp_dbw = p.eirp_dbm - 30.0
    el = np.maximum(np.asarray(elevation_deg, dtype=float), 0.5)
    atmos = p.atmos_zenith_db / np.sin(np.radians(el))
    cn0 = eirp_dbw + p.sat_gt_dbk - fspl_db(range_km, p.freq_mhz) - p.pol_pointing_loss_db - atmos - BOLTZMANN_DBW
    req = p.req_ebn0_db + 10 * np.log10(p.data_rate_bps) + p.impl_loss_db
    return cn0 - req


def min_link_elevation_deg(altitude_km: float, p: LinkParams = LinkParams()) -> float | None:
    """Lowest elevation at which margin >= design margin for a circular orbit of the given altitude.

    Returns None when the link never closes, even at zenith.
    """
    els = np.linspace(0.5, 90.0, 1800)
    ok = margin_db(slant_range_km(els, altitude_km), els, p) >= p.design_margin_db
    if not ok.any():
        return None
    return float(els[np.argmax(ok)])


def max_doppler_khz(altitude_km: float, freq_mhz: float) -> float:
    """Upper bound on the Doppler shift: circular-orbit speed times carrier / c (reached near the horizon)."""
    mu = 398600.4418
    v = math.sqrt(mu / (R_EQ_KM + altitude_km))
    return v / C_KM_S * freq_mhz * 1000.0


def airtime_s(payload_bytes: int, overhead_bytes: int, p: LinkParams) -> float:
    return (payload_bytes + overhead_bytes) * 8 / p.data_rate_bps
