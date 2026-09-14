"""Threaded acquisition worker: runs the DAQ loop off the GUI thread with start/stop/pause."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.daq.base import DAQBackend


class AcquisitionWorker(QThread):
    """Runs `config.iterations` averaged acquisitions using the given DAQ backend.

    Emits signals so the GUI can update plots/tables as each iteration completes.
    Stop is cooperative: checked between replicate acquisitions, not mid-replicate.
    Pause blocks the loop between iterations until resumed, calling `backend.pause()`/
    `resume()` so hardware backends can halt a free-running pulse train instead of
    overflowing the AI buffer while nothing is reading it.
    """

    iteration_ready = Signal(int, np.ndarray)
    progress = Signal(int, int)  # (current_iteration, total_iterations)
    finished_ok = Signal()
    error = Signal(str)

    def __init__(self, backend: DAQBackend, config: ExperimentConfig) -> None:
        super().__init__()
        self._backend = backend
        self._config = config
        self._mutex = QMutex()
        self._paused = False

    def set_paused(self, paused: bool) -> None:
        with QMutexLocker(self._mutex):
            self._paused = paused

    def _is_paused(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._paused

    def stop(self) -> None:
        self.requestInterruption()

    def run(self) -> None:
        cfg = self._config
        try:
            cfg.validate()
            self._backend.configure(
                device_name=cfg.device_name,
                ai_channel=cfg.ai_channel,
                co_channel=cfg.co_channel,
                sample_rate_hz=cfg.sample_rate_hz,
                num_points=cfg.num_points,
                pulse_width_ms=cfg.pulse_width_ms,
            )
            for iteration_index in range(cfg.iterations):
                if self.isInterruptionRequested():
                    break
                if self._is_paused():
                    self._backend.pause()
                    while self._is_paused():
                        if self.isInterruptionRequested():
                            break
                        self.msleep(50)
                    if not self.isInterruptionRequested():
                        self._backend.resume()
                if self.isInterruptionRequested():
                    break

                accumulator = np.zeros(cfg.num_points)
                for _ in range(cfg.averages):
                    if self.isInterruptionRequested():
                        break
                    accumulator += self._backend.acquire_one()
                else:
                    averaged = accumulator / cfg.averages
                    self.iteration_ready.emit(iteration_index, averaged)
                    self.progress.emit(iteration_index + 1, cfg.iterations)
                    continue
                break
            self.finished_ok.emit()
        except Exception as exc:  # surface hardware/config errors to the GUI
            self.error.emit(str(exc))
        finally:
            self._backend.close()
