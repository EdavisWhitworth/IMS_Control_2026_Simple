import numpy as np

from ims_control.processing.baseline import estimate_baseline


def test_estimate_baseline_follows_flat_offset():
    t_ms = np.linspace(0, 25, 2000)
    peak = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2)
    offset = 0.5
    intensity = peak + offset

    baseline = estimate_baseline(t_ms, intensity, window_ms=2.0)

    # Far from the peak, the baseline should track the flat offset closely.
    far_from_peak = np.abs(t_ms - 10.0) > 3.0
    np.testing.assert_allclose(baseline[far_from_peak], offset, atol=0.05)


def test_estimate_baseline_does_not_exceed_signal():
    t_ms = np.linspace(0, 25, 2000)
    intensity = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2) + 0.2
    baseline = estimate_baseline(t_ms, intensity, window_ms=2.0)
    assert np.all(baseline <= intensity + 1e-9)
