"""Baseline noise estimation over a user-selectable window of the drift spectrum."""

from __future__ import annotations

import numpy as np


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
