import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.io.csv_io import (
    export_peaks_csv,
    export_spectra_csv,
    import_peaks_csv,
    import_spectra_csv,
    peaks_csv_path,
)
from ims_control.io.hdf5_io import export_hdf5, import_hdf5
from ims_control.io.mzml_io import export_mzml, import_mzml
from ims_control.models.data_store import DataStore


def _make_store():
    config = ExperimentConfig(exp_length_ms=5.0, num_points=50, iterations=2)
    store = DataStore(config)
    for i in range(2):
        intensity = np.linspace(0, 1, 50) + i
        record = store.add_iteration(i, intensity)
        record.peaks = [
            {
                "index": 10,
                "time_ms": 1.0,
                "height": 0.5,
                "fwhm_ms": 0.2,
                "resolving_power": 5.0,
                "snr": 10.0,
                "k0": 1.5,
                "ccs_a2": 150.0,
            }
        ]
    return store


def test_csv_export_round_trip(tmp_path):
    store = _make_store()
    spectra_path = tmp_path / "spectra.csv"
    peaks_path = tmp_path / "peaks.csv"
    written = export_spectra_csv(store, spectra_path)
    export_peaks_csv(store, peaks_path)
    assert [p.name for p in written] == ["spectra_raw.csv", "spectra_processed.csv"]
    assert peaks_path.exists()
    assert "iteration_0" in (tmp_path / "spectra_processed.csv").read_text()


def test_csv_import_round_trip(tmp_path):
    store = _make_store()
    spectra_path = tmp_path / "spectra.csv"
    peaks_path = tmp_path / "spectra_peaks.csv"
    export_spectra_csv(store, spectra_path)
    export_peaks_csv(store, peaks_path)

    loaded = import_spectra_csv(tmp_path / "spectra_processed.csv")
    import_peaks_csv(loaded, peaks_csv_path(tmp_path / "spectra_processed.csv"))

    assert len(loaded) == len(store)
    np.testing.assert_allclose(loaded.as_2d_array(), store.as_2d_array())
    np.testing.assert_allclose(loaded.time_axis_ms, store.time_axis_ms, atol=1e-6)
    assert loaded.iterations[0].peaks[0]["k0"] == 1.5
    assert loaded.iterations[0].peaks[0]["ccs_a2"] == 150.0


def test_hdf5_export_import_round_trip(tmp_path):
    store = _make_store()
    path = tmp_path / "run.h5"
    export_hdf5(store, path)
    loaded = import_hdf5(path)
    assert len(loaded) == len(store)
    assert loaded.config.num_points == store.config.num_points
    np.testing.assert_allclose(loaded.as_2d_array(), store.as_2d_array())
    assert loaded.iterations[0].peaks[0]["k0"] == 1.5


def test_mzml_export_creates_valid_xml(tmp_path):
    store = _make_store()
    path = tmp_path / "run.mzml"
    export_mzml(store, path)
    content = (tmp_path / "run_processed.mzml").read_text(encoding="utf-8")
    assert "<mzML" in content
    assert content.count("<spectrum ") == 2
    assert (tmp_path / "run_raw.mzml").exists()


def test_mzml_import_round_trip(tmp_path):
    store = _make_store()
    path = tmp_path / "run.mzml"
    export_mzml(store, path)

    loaded = import_mzml(tmp_path / "run_processed.mzml")

    assert len(loaded) == len(store)
    np.testing.assert_allclose(loaded.as_2d_array(), store.as_2d_array())
    np.testing.assert_allclose(loaded.time_axis_ms, store.time_axis_ms, atol=1e-6)
    assert loaded.iterations[0].peaks == []  # mzML does not carry peak data
