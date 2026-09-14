"""Power-supply control backends: IMS cell and Ionization supplies via 0-10 V analog
outputs (scaled from kV setpoints), plus a single shared enable/LED digital output line.

Unlike the acquisition DAQBackend, these are simple software-timed writes (no sample
clock/triggering), so each write opens and closes its own short-lived task rather than
keeping persistent tasks armed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

try:
    import nidaqmx
except ImportError:  # pragma: no cover - exercised only on machines without NI-DAQmx
    nidaqmx = None


def kv_to_volts(kv: float, max_kv: float, full_scale_v: float = 10.0) -> float:
    """Scale a kV setpoint to the 0-full_scale_v range the supply's analog input expects.

    full_scale_v is the AO voltage that corresponds to max_kv (commonly 10 V, but not all
    supplies use a 10 V full-scale control input).
    """
    if max_kv <= 0:
        return 0.0
    return max(0.0, min(full_scale_v, (kv / max_kv) * full_scale_v))


class PowerSupplyBackend(ABC):
    """Common interface for controlling the IMS cell and Ionization power supplies."""

    @abstractmethod
    def configure(
        self,
        *,
        device_name: str,
        ims_cell_ao_channel: str,
        ionization_ao_channel: str,
        power_do_channel: str,
    ) -> None:
        """Record channel assignments for subsequent writes."""

    @abstractmethod
    def set_ims_cell_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        """Write the IMS cell setpoint (kV, scaled to 0-full_scale_v by max_kv)."""

    @abstractmethod
    def set_ionization_output_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        """Write the Ionization supply's absolute output setpoint (kV, scaled to 0-full_scale_v
        by max_kv). The caller is responsible for adding the IMS cell kV to the desired bias
        before calling this, since the ionization AO input expects the supply's true output,
        not just the bias amount."""

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable both supplies together; the same line also drives the external LED."""

    @abstractmethod
    def close(self) -> None:
        """Release any underlying hardware resources."""


class NIPowerSupplyBackend(PowerSupplyBackend):
    """Writes AO/DO channels on real NI-DAQmx hardware."""

    def __init__(self) -> None:
        if nidaqmx is None:
            raise RuntimeError(
                "nidaqmx package / NI-DAQmx driver not available; install NI-DAQmx "
                "and the 'nidaqmx' Python package, or use SimulatedPowerSupplyBackend instead."
            )
        self._device_name = ""
        self._ims_cell_ao_channel = ""
        self._ionization_ao_channel = ""
        self._power_do_channel = ""

    def configure(
        self,
        *,
        device_name: str,
        ims_cell_ao_channel: str,
        ionization_ao_channel: str,
        power_do_channel: str,
    ) -> None:
        self._device_name = device_name
        self._ims_cell_ao_channel = ims_cell_ao_channel
        self._ionization_ao_channel = ionization_ao_channel
        self._power_do_channel = power_do_channel

    def _write_ao(self, channel: str, volts: float) -> None:
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(f"{self._device_name}/{channel}")
            task.write(volts)

    def _write_do(self, channel: str, value: bool) -> None:
        with nidaqmx.Task() as task:
            task.do_channels.add_do_chan(f"{self._device_name}/{channel}")
            task.write(bool(value), auto_start=True)

    def set_ims_cell_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        self._write_ao(self._ims_cell_ao_channel, kv_to_volts(kv, max_kv, full_scale_v))

    def set_ionization_output_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        self._write_ao(self._ionization_ao_channel, kv_to_volts(kv, max_kv, full_scale_v))

    def set_enabled(self, enabled: bool) -> None:
        self._write_do(self._power_do_channel, enabled)

    def close(self) -> None:
        pass  # each write uses a short-lived task; nothing persistent to release


class SimulatedPowerSupplyBackend(PowerSupplyBackend):
    """No-hardware stand-in; records the last commanded state for inspection/tests."""

    def __init__(self) -> None:
        self.ims_cell_kv = 0.0
        self.ionization_kv = 0.0
        self.enabled = False

    def configure(
        self,
        *,
        device_name: str,
        ims_cell_ao_channel: str,
        ionization_ao_channel: str,
        power_do_channel: str,
    ) -> None:
        pass

    def set_ims_cell_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        self.ims_cell_kv = kv_to_volts(kv, max_kv, full_scale_v) / full_scale_v * max_kv

    def set_ionization_output_kv(self, kv: float, max_kv: float, full_scale_v: float = 10.0) -> None:
        self.ionization_kv = kv_to_volts(kv, max_kv, full_scale_v) / full_scale_v * max_kv

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def close(self) -> None:
        pass
