"""HDF5 export/import of a full IMS run: raw iterations, config metadata, and peak results."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import h5py
import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.models.data_store import DataStore, IterationRecord


def export_hdf5(store: DataStore, path: str | Path) -> None:
    with h5py.File(path, "w") as f:
        config_dict = asdict(store.config)
        config_dict["created_at"] = str(config_dict["created_at"])
        f.attrs["config_json"] = json.dumps(config_dict)

        f.create_dataset("time_axis_ms", data=store.time_axis_ms)
        f.create_dataset("intensity", data=store.as_2d_array())

        peaks_group = f.create_group("peaks")
        for rec in store.iterations:
            peaks_group.create_dataset(f"iteration_{rec.index}", data=json.dumps(rec.peaks))


def import_hdf5(path: str | Path) -> DataStore:
    with h5py.File(path, "r") as f:
        config_dict = json.loads(f.attrs["config_json"])
        config_dict.pop("created_at", None)
        config = ExperimentConfig(**config_dict)

        store = DataStore(config)
        intensity = np.asarray(f["intensity"])
        for i in range(intensity.shape[0]):
            rec = IterationRecord(index=i, intensity=intensity[i])
            if "peaks" in f and f"iteration_{i}" in f["peaks"]:
                rec.peaks = json.loads(f["peaks"][f"iteration_{i}"][()])
            store.iterations.append(rec)
        return store
