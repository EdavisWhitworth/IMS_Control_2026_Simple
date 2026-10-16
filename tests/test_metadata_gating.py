"""Imports without instrument/ion metadata flag it and withhold K0/CCS until confirmed."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.gui.main_window import MainWindow
from ims_control.io.csv_io import export_spectra_csv, import_spectra_csv
from ims_control.io.hdf5_io import export_hdf5, import_hdf5
from ims_control.io.mzml_io import export_mzml, import_mzml
from ims_control.io.xlsx_io import export_xlsx, import_xlsx
from ims_control.models.data_store import DataStore
from ims_control.processing.peak_picking import pick_peaks

META = dict(drift_length_cm=10.0, drift_voltage_v=1000.0, pressure_torr=760.0, temperature_k=298.0, gas_type="N2")


def _store(confirmed: bool = True) -> DataStore:
    config = ExperimentConfig(num_points=500, exp_length_ms=50.0, ion_mz=200.0)
    store = DataStore(config)
    t = store.time_axis_ms
    rng = np.random.default_rng(0)
    for i in range(2):
        store.add_iteration(i, 10 * np.exp(-0.5 * ((t - 20) / 0.4) ** 2) + rng.normal(0, 0.05, t.size))
    store.metadata_confirmed = confirmed
    return store


def test_pick_peaks_withholds_mobility():
    s = _store()
    withheld = pick_peaks(s.time_axis_ms, s.iterations[0].intensity, **META, compute_mobility=False)
    shown = pick_peaks(s.time_axis_ms, s.iterations[0].intensity, **META)
    assert withheld and withheld[0].k0 is None and withheld[0].ccs_a2 is None
    assert shown[0].k0 is not None and shown[0].ccs_a2 is None  # ion_mz not given -> CCS unavailable
    assert withheld[0].time_ms == shown[0].time_ms


def test_csv_import_is_unconfirmed(tmp_path):
    written = export_spectra_csv(_store(), tmp_path / "r.csv")
    assert import_spectra_csv(written[0]).metadata_confirmed is False


def test_self_describing_formats_stay_confirmed(tmp_path):
    export_hdf5(_store(), tmp_path / "r.h5")
    export_xlsx(_store(), tmp_path / "r.xlsx")
    mz = export_mzml(_store(), tmp_path / "r.mzML")
    assert import_hdf5(tmp_path / "r.h5").metadata_confirmed is True
    assert import_xlsx(tmp_path / "r.xlsx").metadata_confirmed is True
    assert import_mzml(mz[0]).metadata_confirmed is True


def test_unconfirmed_flag_round_trips(tmp_path):
    export_hdf5(_store(False), tmp_path / "r.h5")
    export_xlsx(_store(False), tmp_path / "r.xlsx")
    mz = export_mzml(_store(False), tmp_path / "r.mzML")
    assert import_hdf5(tmp_path / "r.h5").metadata_confirmed is False
    assert import_xlsx(tmp_path / "r.xlsx").metadata_confirmed is False
    assert import_mzml(mz[0]).metadata_confirmed is False


def test_xlsx_without_settings_sheet_is_unconfirmed(tmp_path):
    from openpyxl import load_workbook

    path = tmp_path / "r.xlsx"
    export_xlsx(_store(), path)
    wb = load_workbook(path)
    del wb["Settings"]
    wb.save(path)
    assert import_xlsx(path).metadata_confirmed is False


@pytest.fixture
def window():
    QApplication.instance() or QApplication([])
    w = MainWindow()
    yield w
    w.close()


def test_gui_banner_and_confirm(window):
    window.store = _store(False)
    window._update_metadata_banner()
    window._recompute_all_peaks()
    assert not window.metadata_banner.isHidden()
    assert all(p["k0"] is None for p in window.store.iterations[0].peaks)

    window.control_panel.drift_length_spin.setValue(12.0)  # editing alone must not release K0
    assert all(p["k0"] is None for p in window.store.iterations[0].peaks)

    window._on_confirm_metadata()
    assert window.metadata_banner.isHidden()
    assert window.store.metadata_confirmed
    assert window.store.config.drift_length_cm == 12.0
    assert all(p["k0"] is not None for p in window.store.iterations[0].peaks)
