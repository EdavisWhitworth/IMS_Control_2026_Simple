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


def test_positive_mode_inverts_spectrum_and_recomputes_peaks():
    window = MainWindow()
    config = window.control_panel.build_config()
    config.num_points = 2000
    config.exp_length_ms = 25.0

    from ims_control.models.data_store import DataStore

    window.store = DataStore(config)
    t_ms = window.store.time_axis_ms
    intensity = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2)
    record = window.store.add_iteration(0, intensity.copy())
    record.peaks = []

    window.control_panel.positive_mode_checkbox.setChecked(True)

    np.testing.assert_allclose(record.intensity, -intensity)
    # The Gaussian peak is now a dip (local minimum), so find_peaks should no longer detect it.
    assert len(record.peaks) == 0

    window.control_panel.positive_mode_checkbox.setChecked(False)

    np.testing.assert_allclose(record.intensity, intensity)
    assert len(record.peaks) == 1  # flipped back to positive-going, peak is found again


def test_baseline_subtraction_is_reversible_and_shows_overlay():
    window = MainWindow()
    config = window.control_panel.build_config()
    config.num_points = 2000
    config.exp_length_ms = 25.0

    from ims_control.models.data_store import DataStore

    window.store = DataStore(config)
    t_ms = window.store.time_axis_ms
    offset = 0.2
    peak = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2)
    intensity = peak + offset
    record = window.store.add_iteration(0, intensity.copy())
    record.peaks = []
    assert record.baseline is None

    window.control_panel.subtract_baseline_checkbox.setChecked(True)

    assert record.baseline is not None
    # After subtracting a ~flat baseline, the far-from-peak samples should sit near 0.
    assert abs(float(record.intensity[0])) < 0.05
    np.testing.assert_allclose(record.raw_intensity, intensity)  # raw copy untouched

    window.control_panel.subtract_baseline_checkbox.setChecked(False)

    assert record.baseline is None
    np.testing.assert_allclose(record.intensity, intensity)  # exactly restored


def test_normalize_scales_to_requested_range():
    window = MainWindow()
    config = window.control_panel.build_config()
    config.num_points = 2000
    config.exp_length_ms = 25.0

    from ims_control.models.data_store import DataStore

    window.store = DataStore(config)
    t_ms = window.store.time_axis_ms
    intensity = 5.0 * np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2)
    record = window.store.add_iteration(0, intensity.copy())
    record.peaks = []

    window.control_panel.normalize_checkbox.setChecked(True)
    assert abs(float(np.max(record.intensity)) - 1.0) < 1e-9  # default scale is "0-1"

    window.control_panel.normalize_scale_combo.setCurrentText("0-100%")
    assert abs(float(np.max(record.intensity)) - 100.0) < 1e-9

    window.control_panel.normalize_checkbox.setChecked(False)
    np.testing.assert_allclose(record.intensity, intensity)  # exactly restored


def test_positive_mode_and_baseline_and_normalize_compose_and_reverse_independently():
    window = MainWindow()
    config = window.control_panel.build_config()
    config.num_points = 2000
    config.exp_length_ms = 25.0

    from ims_control.models.data_store import DataStore

    window.store = DataStore(config)
    t_ms = window.store.time_axis_ms
    intensity = np.exp(-0.5 * ((t_ms - 10.0) / 0.3) ** 2) + 0.1
    record = window.store.add_iteration(0, intensity.copy())
    record.peaks = []

    window.control_panel.positive_mode_checkbox.setChecked(True)
    window.control_panel.subtract_baseline_checkbox.setChecked(True)
    window.control_panel.normalize_checkbox.setChecked(True)

    # Turn each back off in a different order than they were enabled; since intensity is
    # always re-derived from raw_intensity, order must not matter for correctness.
    window.control_panel.subtract_baseline_checkbox.setChecked(False)
    window.control_panel.positive_mode_checkbox.setChecked(False)
    window.control_panel.normalize_checkbox.setChecked(False)

    np.testing.assert_allclose(record.intensity, intensity, atol=1e-9)
    np.testing.assert_allclose(record.raw_intensity, intensity)
