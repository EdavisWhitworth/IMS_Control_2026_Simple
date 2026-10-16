"""HDF5 export/import of a full IMS run: raw iterations, config metadata, and peak results."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import h5py
import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.io.variants import DEFAULT_EXPORT, validate_export_data
from ims_control.models.data_store import DataStore, IterationRecord


def export_hdf5(store: DataStore, path: str | Path, data: str = DEFAULT_EXPORT) -> None:
    """Write the run. `data` is "both" (default), "raw" or "processed".

    Datasets: `raw_intensity` (as acquired, never processed) and `intensity` (processed:
    whatever positive-mode/baseline/normalization is active). Each carries a `label` attr.
    """
    variants = validate_export_data(data)
    with h5py.File(path, "w") as f:
        config_dict = asdict(store.config)
        config_dict["created_at"] = str(config_dict["created_at"])
        f.attrs["config_json"] = json.dumps(config_dict)

        f.create_dataset("time_axis_ms", data=store.time_axis_ms)
        f.attrs["exported_data"] = ",".join(variants)
        if "raw" in variants:
            ds = f.create_dataset("raw_intensity", data=store.as_2d_raw_array())
            ds.attrs["label"] = "raw: as acquired/imported, no processing applied"
        if "processed" in variants:
            ds = f.create_dataset("intensity", data=store.as_2d_array())
            ds.attrs["label"] = (
                "processed: positive mode / baseline subtraction / normalization as active at export"
            )

        peaks_group = f.create_group("peaks")
        for rec in store.iterations:
            peaks_group.create_dataset(f"iteration_{rec.index}", data=json.dumps(rec.peaks))


def import_hdf5(path: str | Path) -> DataStore:
    with h5py.File(path, "r") as f:
        config_dict = json.loads(f.attrs["config_json"])
        config_dict.pop("created_at", None)
        config = ExperimentConfig(**config_dict)

        store = DataStore(config)
        processed = np.asarray(f["intensity"]) if "intensity" in f else None
        raw = np.asarray(f["raw_intensity"]) if "raw_intensity" in f else None
        if processed is None and raw is None:
            raise ValueError("HDF5 file contains neither `intensity` nor `raw_intensity`")
        if processed is None:
            processed = raw  # raw-only export: processing is re-derived from raw by the GUI
        for i in range(processed.shape[0]):
            rec = IterationRecord(
                index=i,
                intensity=processed[i],
                raw_intensity=None if raw is None else raw[i].copy(),
            )
            if "peaks" in f and f"iteration_{i}" in f["peaks"]:
                rec.peaks = json.loads(f["peaks"][f"iteration_{i}"][()])
            store.iterations.append(rec)
        return store
