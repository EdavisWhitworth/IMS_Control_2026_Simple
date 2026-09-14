import numpy as np
import pytest

from ims_control.acquisition.controller import AcquisitionWorker
from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.daq.simulator import SimulatedDAQBackend

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    # Use QApplication (not QCoreApplication) so it's compatible with any test in the same
    # process that also needs to create widgets (e.g. tests/test_metadata_recompute.py).
    app = QApplication.instance() or QApplication([])
    yield app


def test_worker_runs_all_iterations():
    config = ExperimentConfig(
        pulse_width_ms=0.2, exp_length_ms=5.0, num_points=100, averages=2, iterations=3
    )
    backend = SimulatedDAQBackend(seed=2)
    worker = AcquisitionWorker(backend, config)

    received = []
    worker.iteration_ready.connect(
        lambda idx, data: received.append((idx, data)), Qt.ConnectionType.DirectConnection
    )
    worker.start()
    worker.wait(10_000)

    assert len(received) == 3
    for idx, data in received:
        assert data.shape == (100,)


def test_worker_stops_early():
    config = ExperimentConfig(
        pulse_width_ms=0.2, exp_length_ms=5.0, num_points=50, averages=1, iterations=1000
    )
    backend = SimulatedDAQBackend(seed=3)
    worker = AcquisitionWorker(backend, config)

    received = []

    def on_iteration(idx, data):
        received.append(idx)
        if idx >= 2:
            worker.stop()

    worker.iteration_ready.connect(on_iteration, Qt.ConnectionType.DirectConnection)
    worker.start()
    worker.wait(10_000)

    assert len(received) < 1000
