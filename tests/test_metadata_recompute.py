import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from ims_control.gui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_metadata_change_recomputes_peaks_without_active_run():
    window = MainWindow()
    config = window.control_panel.build_config()
    config.num_points = 2000
    config.exp_length_ms = 25.0

    from ims_control.models.data_store import DataStore

    window.store = DataStore(config)
    t_ms = window.store.time_axis_ms
    intensity = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2)
    record = window.store.add_iteration(0, intensity)
    record.peaks = []

    window.control_panel.ion_mz_spin.setValue(500.0)

    assert len(record.peaks) == 1
    assert record.peaks[0]["ccs_a2"] is not None
    assert window.store.config.ion_mz == 500.0
