"""In-memory store for acquired iterations and their derived peak-picking results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig


@dataclass
class IterationRecord:
    """One averaged iteration: the drift spectrum plus its acquisition timestamp."""

    index: int
    intensity: np.ndarray
    timestamp: datetime = field(default_factory=datetime.now)
    peaks: list[dict] = field(default_factory=list)


class DataStore:
    """Holds the config and all iterations collected during (or loaded for) a run."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.iterations: list[IterationRecord] = []

    @property
    def time_axis_ms(self) -> np.ndarray:
        return np.arange(self.config.num_points) / self.config.sample_rate_hz * 1000.0

    def add_iteration(self, index: int, intensity: np.ndarray) -> IterationRecord:
        record = IterationRecord(index=index, intensity=intensity)
        self.iterations.append(record)
        return record

    def get_iteration(self, index: int) -> IterationRecord:
        return self.iterations[index]

    def as_2d_array(self) -> np.ndarray:
        """Return shape (n_iterations, num_points) intensity matrix for the heatmap."""
        if not self.iterations:
            return np.zeros((0, self.config.num_points))
        return np.vstack([rec.intensity for rec in self.iterations])

    def set_peaks(self, index: int, peaks: list[dict]) -> None:
        self.iterations[index].peaks = peaks

    def __len__(self) -> int:
        return len(self.iterations)
