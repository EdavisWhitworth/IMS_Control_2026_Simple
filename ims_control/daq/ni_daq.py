"""Real hardware backend for an NI USB-6351 (or similar X-Series NI-DAQmx device).

The ion-gate pulse is generated as a free-running, continuous pulse train on a
counter-output (CO) channel at the experiment repetition rate; the AI task uses that
pulse's internal output terminal as a *retriggerable* start trigger, so it automatically
re-arms after each replicate without any per-replicate task start/stop. Both tasks are
started once in `configure()` and read from repeatedly in `acquire_one()` -- restarting
NI-DAQmx tasks for every replicate adds tens of milliseconds of USB/driver overhead per
call, which would otherwise inflate the pulse period well beyond `exp_length_ms`.

Requires the NI-DAQmx driver and the `nidaqmx` Python package. Import of `nidaqmx` is
deferred/optional so the rest of the application still runs (in simulator mode) on
machines without the driver installed.
"""

from __future__ import annotations

import numpy as np

from ims_control.daq.base import DAQBackend

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, Edge
except ImportError:  # pragma: no cover - exercised only on machines without NI-DAQmx
    nidaqmx = None
    AcquisitionType = None
    Edge = None


class NIDAQBackend(DAQBackend):
    """DAQBackend implementation talking to real NI-DAQmx hardware."""

    def __init__(self) -> None:
        if nidaqmx is None:
            raise RuntimeError(
                "nidaqmx package / NI-DAQmx driver not available; install NI-DAQmx "
                "and the 'nidaqmx' Python package, or use SimulatedDAQBackend instead."
            )
        self._ai_task: "nidaqmx.Task | None" = None
        self._co_task: "nidaqmx.Task | None" = None
        self._num_points = 0

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
        self.close()
        self._num_points = num_points
        exp_length_s = num_points / sample_rate_hz

        self._co_task = nidaqmx.Task()
        # Continuous pulse train at the experiment repetition rate: high_time is the gate
        # pulse width, low_time is the remainder of the experiment window. This way the CO
        # task free-runs in hardware and never needs restarting between replicates.
        high_time_s = pulse_width_ms / 1000.0
        low_time_s = exp_length_s - high_time_s
        co_chan = self._co_task.co_channels.add_co_pulse_chan_time(
            f"{device_name}/{co_channel}",
            low_time=low_time_s,
            high_time=high_time_s,
        )
        self._co_task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        counter_terminal = co_chan.co_pulse_term if hasattr(co_chan, "co_pulse_term") else None

        self._ai_task = nidaqmx.Task()
        self._ai_task.ai_channels.add_ai_voltage_chan(f"{device_name}/{ai_channel}")
        self._ai_task.timing.cfg_samp_clk_timing(
            rate=sample_rate_hz,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=num_points,
        )
        trigger_source = counter_terminal or f"/{device_name}/{co_channel}InternalOutput"
        self._ai_task.triggers.start_trigger.cfg_dig_edge_start_trig(
            trigger_source=trigger_source, trigger_edge=Edge.RISING
        )
        # Auto-rearm after each replicate so the AI task keeps pace with the free-running
        # CO pulse train without any per-replicate start()/stop() round trip.
        self._ai_task.triggers.start_trigger.retriggerable = True

        # Arm the AI task first so it is ready to catch the CO task's first pulse edge.
        self._ai_task.start()
        self._co_task.start()

    def acquire_one(self) -> np.ndarray:
        if self._ai_task is None or self._co_task is None:
            raise RuntimeError("configure() must be called before acquire_one().")
        data = self._ai_task.read(number_of_samples_per_channel=self._num_points, timeout=10.0)
        return np.asarray(data, dtype=float)

    def close(self) -> None:
        for task in (self._ai_task, self._co_task):
            if task is not None:
                try:
                    task.stop()
                except Exception:
                    pass
                try:
                    task.close()
                except Exception:
                    pass
        self._ai_task = None
        self._co_task = None
