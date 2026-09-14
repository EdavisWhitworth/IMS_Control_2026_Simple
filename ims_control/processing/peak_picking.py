"""Peak picking and derived IMS parameters: FWHM, resolving power, SNR, K0, and CCS.

Reduced mobility (K0) uses the standard temperature/pressure correction:
    K0 = (L^2 / (V * t_d)) * (P / 760) * (273.15 / T)
with L in cm, V in volts, t_d in seconds, P in torr, T in kelvin -> K0 in cm^2 V^-1 s^-1.

Collision cross section (CCS) uses the Mason-Schamp equation:
    CCS = (3 / 16) * sqrt(2*pi / (mu * kB * T)) * (z * e) / (N0 * K0)
with mu the ion-neutral reduced mass (kg), N0 the neutral gas number density at STP.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks, peak_widths

from ims_control.processing.baseline import default_noise_window, noise_stats

# Physical constants (SI unless noted).
BOLTZMANN_J_PER_K = 1.380649e-23
ELEMENTARY_CHARGE_C = 1.602176634e-19
AMU_TO_KG = 1.66053906660e-27
LOSCHMIDT_NUMBER_PER_M3 = 2.6867811e25  # neutral gas number density at 273.15 K, 760 torr

# Monoisotopic-ish average molar masses (amu) of common IMS buffer gases.
GAS_MASSES_AMU = {
    "N2": 28.0134,
    "HE": 4.0026,
    "AIR": 28.96,
    "CO2": 44.01,
    "AR": 39.948,
}


@dataclass
class PeakResult:
    index: int
    time_ms: float
    height: float
    fwhm_ms: float
    resolving_power: float
    snr: float
    k0: float
    ccs_a2: float | None


def reduced_mobility(
    drift_time_ms: float,
    drift_length_cm: float,
    drift_voltage_v: float,
    pressure_torr: float,
    temperature_k: float,
) -> float:
    """K0 in cm^2 V^-1 s^-1."""
    t_d_s = drift_time_ms / 1000.0
    k = (drift_length_cm**2) / (drift_voltage_v * t_d_s)
    return k * (pressure_torr / 760.0) * (273.15 / temperature_k)


def collision_cross_section(
    k0_cm2_v_s: float,
    ion_mz: float,
    ion_charge: int,
    temperature_k: float,
    gas_type: str,
) -> float | None:
    """CCS in square angstroms, or None if inputs are insufficient (e.g. ion_mz not set)."""
    if k0_cm2_v_s <= 0 or ion_mz <= 0 or ion_charge <= 0:
        return None
    gas_mass_amu = GAS_MASSES_AMU.get(gas_type.upper())
    if gas_mass_amu is None:
        return None

    ion_mass_amu = ion_mz * ion_charge  # neutral mass estimate, ignoring electron mass
    reduced_mass_kg = (ion_mass_amu * gas_mass_amu) / (ion_mass_amu + gas_mass_amu) * AMU_TO_KG
    k0_m2_v_s = k0_cm2_v_s * 1e-4  # cm^2 -> m^2

    ze = ion_charge * ELEMENTARY_CHARGE_C
    prefactor = (3.0 / 16.0) * np.sqrt(2.0 * np.pi / (reduced_mass_kg * BOLTZMANN_J_PER_K * temperature_k))
    ccs_m2 = prefactor * ze / (LOSCHMIDT_NUMBER_PER_M3 * k0_m2_v_s)
    return float(ccs_m2 * 1e20)  # m^2 -> angstrom^2


def pick_peaks(
    time_ms: np.ndarray,
    intensity: np.ndarray,
    *,
    drift_length_cm: float,
    drift_voltage_v: float,
    pressure_torr: float,
    temperature_k: float,
    gas_type: str,
    ion_mz: float = 0.0,
    ion_charge: int = 1,
    noise_window_ms: tuple[float, float] | None = None,
    height: float | None = None,
    prominence: float | None = None,
) -> list[PeakResult]:
    """Find peaks in a drift spectrum and compute time/FWHM/resolving power/SNR/K0/CCS for each."""
    if noise_window_ms is None:
        noise_window_ms = default_noise_window(time_ms)
    _, baseline_std = noise_stats(time_ms, intensity, *noise_window_ms)
    baseline_std = baseline_std if baseline_std > 0 else 1e-12

    # Default prominence filters out noise-induced local maxima (low prominence relative
    # to the noise floor) while still catching genuine, isolated peaks.
    if prominence is None:
        prominence = 5.0 * baseline_std

    peak_indices, _ = find_peaks(intensity, height=height, prominence=prominence)
    if len(peak_indices) == 0:
        return []

    widths_samples, width_heights, left_ips, right_ips = peak_widths(
        intensity, peak_indices, rel_height=0.5
    )
    dt_ms = float(time_ms[1] - time_ms[0])

    results: list[PeakResult] = []
    for i, peak_idx in enumerate(peak_indices):
        t_peak_ms = float(time_ms[peak_idx])
        fwhm_ms = float(widths_samples[i] * dt_ms)
        peak_height = float(intensity[peak_idx])
        resolving_power = t_peak_ms / fwhm_ms if fwhm_ms > 0 else float("inf")
        snr = peak_height / baseline_std
        k0 = reduced_mobility(t_peak_ms, drift_length_cm, drift_voltage_v, pressure_torr, temperature_k)
        ccs = collision_cross_section(k0, ion_mz, ion_charge, temperature_k, gas_type)
        results.append(
            PeakResult(
                index=int(peak_idx),
                time_ms=t_peak_ms,
                height=peak_height,
                fwhm_ms=fwhm_ms,
                resolving_power=resolving_power,
                snr=snr,
                k0=k0,
                ccs_a2=ccs,
            )
        )
    return results
