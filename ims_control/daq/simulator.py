"""Simulated DAQ backend: generates synthetic IMS drift-time traces without hardware.

Used for development and unit tests when no NI-DAQmx device/driver is available.
"""

from __future__ import annotations

import numpy as np

from ims_control.daq.base import DAQBackend


class SimulatedDAQBackend(DAQBackend):
    """Produces Gaussian-peak drift spectra plus noise, matching the DAQBackend interface."""

    def __init__(self, *, seed: int | None = None, peak_times_ms: list[float] | None = None) -> None:
        self._rng = np.random.default_rng(seed)
        # Default synthetic peaks (drift time in ms, relative height, width in ms).
        self._peak_times_ms = peak_times_ms if peak_times_ms is not None else [12.0, 22.0, 31.0]
        self._sample_rate_hz = 0.0
        self._num_points = 0
        self._noise_std = 0.02

    def configure(
        self,
        *,
        device_name: str,
        ai_channel: str,
        co_channel: str,
        sample_rate_hz: float,
        num_points: int,
        pulse_width_ms: float,
    ) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._num_points = num_points

    def acquire_one(self) -> np.ndarray:
        if self._num_points == 0 or self._sample_rate_hz == 0:
            raise RuntimeError("configure() must be called before acquire_one().")
        t_ms = np.arange(self._num_points) / self._sample_rate_hz * 1000.0
        signal = np.zeros(self._num_points)
        for center_ms in self._peak_times_ms:
            width_ms = 0.6 + 0.05 * center_ms
            height = 1.0 + 0.3 * self._rng.standard_normal()
            signal += height * np.exp(-0.5 * ((t_ms - center_ms) / width_ms) ** 2)
        noise = self._rng.normal(0.0, self._noise_std, size=self._num_points)
        return signal + noise

    def close(self) -> None:
        pass
