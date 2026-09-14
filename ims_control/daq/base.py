"""Abstract DAQ backend interface shared by real hardware and simulator implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class DAQBackend(ABC):
    """Common interface for anything that can pulse an ion gate and acquire a drift spectrum."""

    @abstractmethod
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
        """Prepare the backend for repeated single-replicate acquisitions with the given timing."""

    @abstractmethod
    def acquire_one(self) -> np.ndarray:
        """Trigger one gate pulse and return one replicate of `num_points` intensity samples."""

    def pause(self) -> None:
        """Halt hardware acquisition (e.g. stop the gate pulse train) so the AI buffer doesn't
        overflow while nothing is reading it. Default no-op; override if acquire_one() runs
        against a free-running, continuously triggered hardware task."""

    def resume(self) -> None:
        """Resume hardware acquisition after `pause()`. Default no-op."""

    @abstractmethod
    def close(self) -> None:
        """Release any underlying hardware/task resources."""

    def __enter__(self) -> "DAQBackend":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
