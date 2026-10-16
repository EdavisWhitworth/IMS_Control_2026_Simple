r"""Tutorial: verify that raw data survives export and import unchanged.

Builds a synthetic run, applies a (deliberately aggressive) processing step so that
`intensity` differs from `raw_intensity`, exports to HDF5/CSV/mzML with the default
"both" option, re-imports each file, and checks bit-for-bit that `raw_intensity` equals
the original acquired data and was not replaced by processed data.

Run from the repository root:
    $env:PYTHONPATH='.'; .venv\Scripts\python.exe scripts\verify_raw_roundtrip.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.io.xlsx_io import export_xlsx, import_xlsx
from ims_control.io.hdf5_io import export_hdf5, import_hdf5
from ims_control.io.mzml_io import export_mzml, import_mzml
from ims_control.models.data_store import DataStore


def build_store() -> DataStore:
    store = DataStore(ExperimentConfig(exp_length_ms=25.0, num_points=500, iterations=3))
    t = store.time_axis_ms
    rng = np.random.default_rng(1)
    for i in range(3):
        rec = store.add_iteration(i, 2.0 + np.exp(-0.5 * ((t - 10) / 0.3) ** 2) + rng.normal(0, 0.01, t.size))
        rec.intensity = (rec.raw_intensity - 2.0) / np.max(rec.raw_intensity - 2.0)  # "processed"
    return store


def check(label: str, loaded: DataStore, original: DataStore, exact: bool = True) -> bool:
    # Excel stores ~15 significant digits, so XLSX is compared to 1e-14 relative, not bit-for-bit.
    raw_ok = all(
        np.array_equal(a.raw_intensity, b.raw_intensity)
        if exact
        else np.allclose(a.raw_intensity, b.raw_intensity, rtol=1e-14, atol=0)
        for a, b in zip(loaded.iterations, original.iterations)
    )
    processed_distinct = not np.allclose(loaded.iterations[0].raw_intensity, loaded.iterations[0].intensity)
    print(f"{label:6s} raw identical: {raw_ok}   raw distinct from processed: {processed_distinct}")
    return raw_ok and processed_distinct


def main() -> int:
    original = build_store()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        export_hdf5(original, tmp_path / "run.h5")
        export_xlsx(original, tmp_path / "run.xlsx")
        export_mzml(original, tmp_path / "run.mzml")
        print("Files written:", ", ".join(sorted(p.name for p in tmp_path.iterdir())))
        results = [
            check("HDF5", import_hdf5(tmp_path / "run.h5"), original),
            check("XLSX", import_xlsx(tmp_path / "run.xlsx"), original, exact=False),
            check("mzML", import_mzml(tmp_path / "run_processed.mzml"), original),
        ]
    print("ALL CHECKS PASSED" if all(results) else "CHECK FAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
