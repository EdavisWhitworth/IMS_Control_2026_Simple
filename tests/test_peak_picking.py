import numpy as np

from ims_control.processing.peak_picking import (
    collision_cross_section,
    pick_peaks,
    reduced_mobility,
)


def _synthetic_trace(num_points=2000, sample_rate_hz=80000.0, peak_time_ms=15.0, width_ms=0.3):
    t_ms = np.arange(num_points) / sample_rate_hz * 1000.0
    signal = np.exp(-0.5 * ((t_ms - peak_time_ms) / width_ms) ** 2)
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.01, size=num_points)
    return t_ms, signal + noise


def test_pick_peaks_finds_known_peak_and_fwhm():
    t_ms, intensity = _synthetic_trace()
    peaks = pick_peaks(
        t_ms,
        intensity,
        drift_length_cm=10.0,
        drift_voltage_v=1000.0,
        pressure_torr=760.0,
        temperature_k=298.0,
        gas_type="N2",
        height=0.3,
    )
    assert len(peaks) == 1
    peak = peaks[0]
    assert abs(peak.time_ms - 15.0) < 0.2
    # FWHM of a Gaussian with sigma=width_ms is 2*sqrt(2*ln2)*sigma ~ 2.355*width_ms.
    expected_fwhm = 2.3548 * 0.3
    assert abs(peak.fwhm_ms - expected_fwhm) < 0.15
    assert peak.snr > 5
    assert peak.k0 > 0


def test_reduced_mobility_formula():
    k0 = reduced_mobility(
        drift_time_ms=15.0, drift_length_cm=10.0, drift_voltage_v=1000.0,
        pressure_torr=760.0, temperature_k=273.15,
    )
    expected = (10.0**2) / (1000.0 * 0.015)
    assert abs(k0 - expected) < 1e-9


def test_ccs_requires_ion_mz():
    ccs = collision_cross_section(
        k0_cm2_v_s=1.5, ion_mz=0.0, ion_charge=1, temperature_k=298.0, gas_type="N2"
    )
    assert ccs is None

    ccs = collision_cross_section(
        k0_cm2_v_s=1.5, ion_mz=500.0, ion_charge=1, temperature_k=298.0, gas_type="N2"
    )
    assert ccs is not None
    assert ccs > 0
