"""Baseline noise estimation and full-trace baseline curve estimation."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import minimum_filter1d, uniform_filter1d


def noise_stats(
    time_ms: np.ndarray, intensity: np.ndarray, window_start_ms: float, window_end_ms: float
) -> tuple[float, float]:
    """Return (mean, std) of intensity within [window_start_ms, window_end_ms].

    Defaults to the last 10 ms of the trace when called with the default window
    computed by `default_noise_window`.
    """
    mask = (time_ms >= window_start_ms) & (time_ms <= window_end_ms)
    if not np.any(mask):
        raise ValueError("Noise window does not overlap the acquired time axis.")
    window = intensity[mask]
    return float(np.mean(window)), float(np.std(window))


def default_noise_window(time_ms: np.ndarray) -> tuple[float, float]:
    """Last 10 ms of the trace, matching the analysis-suite convention."""
    end = float(time_ms[-1])
    start = max(float(time_ms[0]), end - 10.0)
    return start, end


def estimate_baseline(time_ms: np.ndarray, intensity: np.ndarray, window_ms: float) -> np.ndarray:
    """Rolling-minimum + smoothing envelope that follows a slowly varying noise floor.

    `window_ms` sets the width of both the minimum filter and the smoothing pass; wider
    windows follow slower baseline drift but risk absorbing genuine (wide) peaks.
    """
    if len(time_ms) < 2:
        return np.zeros_like(intensity)
    dt_ms = float(time_ms[1] - time_ms[0])
    window_samples = max(1, int(round(window_ms / dt_ms)))
    envelope = minimum_filter1d(intensity, size=window_samples, mode="nearest")
    return uniform_filter1d(envelope, size=window_samples, mode="nearest")
