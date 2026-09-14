"""Experiment configuration shared by the acquisition controller, GUI, and I/O layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExperimentConfig:
    """All operator-set parameters for a run, including instrument metadata for K0/CCS."""

    # Timing / acquisition parameters.
    pulse_width_ms: float = 0.2
    exp_length_ms: float = 50.0
    num_points: int = 4000
    averages: int = 10
    iterations: int = 20

    # DAQ device/channel identifiers (user-configurable, not hardcoded).
    device_name: str = "Dev1"
    ai_channel: str = "ai0"
    co_channel: str = "ctr0"

    # Instrument metadata used for reduced mobility (K0) and CCS calculations.
    drift_length_cm: float = 10.0
    drift_voltage_v: float = 1000.0
    pressure_torr: float = 760.0
    temperature_k: float = 298.0
    gas_type: str = "N2"

    # Analyte metadata used for CCS (Mason-Schamp) calculations.
    ion_mz: float = 0.0
    ion_charge: int = 1

    created_at: datetime = field(default_factory=datetime.now)

    @property
    def sample_rate_hz(self) -> float:
        """Sample rate implied by the number of points spread across the experiment length."""
        return self.num_points / (self.exp_length_ms / 1000.0)

    def validate(self) -> None:
        """Raise ValueError if any parameter is out of a sane operating range."""
        if self.pulse_width_ms <= 0:
            raise ValueError("Pulse width must be positive.")
        if self.exp_length_ms <= 0:
            raise ValueError("Experiment length must be positive.")
        if self.num_points < 2:
            raise ValueError("Number of data points must be at least 2.")
        if self.averages < 1:
            raise ValueError("Averages must be at least 1.")
        if self.iterations < 1:
            raise ValueError("Iterations must be at least 1.")
        if self.pulse_width_ms >= self.exp_length_ms:
            raise ValueError("Pulse width must be shorter than the experiment length.")
