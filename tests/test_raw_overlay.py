"""Raw-overlay checkboxes: off by default, one per processing step, only effective with that step on."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.gui.main_window import MainWindow
from ims_control.models.data_store import DataStore


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.store = DataStore(ExperimentConfig(num_points=100, exp_length_ms=50.0))
    w.store.add_iteration(0, np.random.default_rng(0).random(100))
    yield w
    w.close()


def _shown(w) -> bool:
    w._refresh_current_view(0)
    x = w.plot_panel.raw_curve.getData()[0]
    return x is not None and len(x) > 0


def test_defaults_off(window):
    cp = window.control_panel
    assert not cp.baseline_raw_overlay_checkbox.isChecked()
    assert not cp.normalize_raw_overlay_checkbox.isChecked()
    cp.subtract_baseline_checkbox.setChecked(True)
    cp.normalize_checkbox.setChecked(True)
    assert not _shown(window)


def test_each_overlay_is_independent(window):
    cp = window.control_panel
    cp.baseline_raw_overlay_checkbox.setChecked(True)
    assert not _shown(window)  # baseline subtraction not active
    cp.subtract_baseline_checkbox.setChecked(True)
    assert _shown(window)
    cp.baseline_raw_overlay_checkbox.setChecked(False)
    cp.normalize_raw_overlay_checkbox.setChecked(True)
    assert not _shown(window)  # normalization not active
    cp.normalize_checkbox.setChecked(True)
    assert _shown(window)
