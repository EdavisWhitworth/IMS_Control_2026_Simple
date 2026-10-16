"""mzML labels: profile spectrum, drift time in a ms time array (not m/z); legacy files still import."""

from __future__ import annotations

import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.io.mzml_io import export_mzml, import_mzml
from ims_control.models.data_store import DataStore


def _store() -> DataStore:
    store = DataStore(ExperimentConfig(num_points=100, exp_length_ms=50.0))
    store.add_iteration(0, np.linspace(0, 1, 100))
    return store


def test_export_uses_profile_and_time_array(tmp_path):
    path = export_mzml(_store(), tmp_path / "r.mzML", data="processed")[0]
    text = path.read_text(encoding="utf-8")
    assert 'accession="MS:1000128"' in text and "profile spectrum" in text
    assert "centroid" not in text
    assert 'accession="MS:1000595"' in text and 'unitAccession="UO:0000028"' in text
    assert 'unitName="millisecond"' in text
    assert "MS:1000514" not in text and "m/z array" not in text
    assert 'name="ims_x_axis" value="drift time"' in text
    assert 'name="ims_x_units" value="ms"' in text


def test_round_trip_exact(tmp_path):
    s = _store()
    path = export_mzml(s, tmp_path / "r.mzML", data="processed")[0]
    back = import_mzml(path)
    assert np.array_equal(back.iterations[0].intensity, s.iterations[0].intensity)
    assert np.isclose(back.config.exp_length_ms, 50.0)


def test_legacy_mz_array_file_still_imports(tmp_path):
    path = export_mzml(_store(), tmp_path / "r.mzML", data="processed")[0]
    legacy = path.read_text(encoding="utf-8").replace("MS:1000595", "MS:1000514").replace(
        "MS:1000128", "MS:1000127"
    )
    old = tmp_path / "old.mzML"
    old.write_text(legacy, encoding="utf-8")
    back = import_mzml(old)
    assert back.config.num_points == 100 and np.isclose(back.config.exp_length_ms, 50.0)
