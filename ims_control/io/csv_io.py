"""CSV export/import for spectra and peak tables."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.io.variants import DEFAULT_EXPORT, split_variant, validate_export_data, variant_path
from ims_control.models.data_store import DataStore


def export_spectra_csv(
    store: DataStore, path: str | Path, data: str = DEFAULT_EXPORT
) -> list[Path]:
    """One row per time point; one column per iteration, plus the shared time axis.

    `data` is "both" (default), "raw" or "processed". Each selected variant is written to its
    own clearly named file, `<base>_raw.csv` / `<base>_processed.csv`. Returns the paths written.
    """
    time_ms = store.time_axis_ms
    written: list[Path] = []
    for variant in validate_export_data(data):
        out_path = variant_path(path, variant)
        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["time_ms"] + [f"iteration_{rec.index}" for rec in store.iterations]
            writer.writerow(header)
            for row_idx, t in enumerate(time_ms):
                row = [t] + [
                    (rec.raw_intensity if variant == "raw" else rec.intensity)[row_idx]
                    for rec in store.iterations
                ]
                writer.writerow(row)
        written.append(out_path)
    return written


def export_peaks_csv(store: DataStore, path: str | Path) -> None:
    """One row per detected peak, across all iterations."""
    fieldnames = [
        "iteration",
        "index",
        "time_ms",
        "height",
        "fwhm_ms",
        "resolving_power",
        "snr",
        "k0",
        "ccs_a2",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in store.iterations:
            for peak in rec.peaks:
                writer.writerow({"iteration": rec.index, **peak})


def peaks_csv_path(path: str | Path) -> Path:
    """Sibling peaks file `<base>_peaks.csv` for a spectra CSV (variant suffix ignored)."""
    base, _ = split_variant(path)
    return base.with_name(base.stem + "_peaks.csv")


def _read_spectra_columns(path: Path) -> tuple[np.ndarray, list[str], np.ndarray]:
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    header, data_rows = rows[0], rows[1:]
    time_ms = np.array([float(row[0]) for row in data_rows])
    columns = np.array([[float(v) for v in row[1:]] for row in data_rows])  # (num_points, n_iter)
    return time_ms, header[1:], columns


def import_spectra_csv(path: str | Path) -> DataStore:
    """Rebuild a DataStore from a spectra CSV. Instrument/ion metadata is not stored in
    CSV, so the resulting ExperimentConfig uses default metadata values -- edit the
    metadata fields in the GUI afterward to get correct K0/CCS on any recomputation.

    If `path` is a `_raw`/`_processed` file and its sibling variant exists, both are loaded,
    so the pristine raw data is restored as `raw_intensity`. A lone processed file (or an
    unlabelled legacy file) has no independent raw data, so raw is set equal to it."""
    path = Path(path)
    base, variant = split_variant(path)
    time_ms, iteration_labels, columns = _read_spectra_columns(path)
    raw_columns = None
    if variant is not None:
        sibling = variant_path(base, "processed" if variant == "raw" else "raw")
        if sibling.exists():
            _, sibling_labels, sibling_columns = _read_spectra_columns(sibling)
            if sibling_labels != iteration_labels or sibling_columns.shape != columns.shape:
                raise ValueError(f"{path.name} and {sibling.name} do not describe the same iterations")
            if variant == "raw":
                raw_columns, columns = columns, sibling_columns
            else:
                raw_columns = sibling_columns
        elif variant == "raw":
            raw_columns = columns  # raw-only: processing is re-derived from raw by the GUI

    num_points = len(time_ms)
    # DataStore.time_axis_ms = arange(num_points)/sample_rate*1000 with sample_rate =
    # num_points/(exp_length_ms/1000), i.e. dt = exp_length_ms/num_points -- so recover
    # exp_length_ms from the sample spacing, not from (last - first) time.
    dt_ms = float(time_ms[1] - time_ms[0]) if num_points > 1 else 1.0
    exp_length_ms = dt_ms * num_points
    config = ExperimentConfig(exp_length_ms=exp_length_ms, num_points=num_points)
    store = DataStore(config)
    for col_idx, label in enumerate(iteration_labels):
        index = int(label.rsplit("_", 1)[-1])
        raw = None if raw_columns is None else raw_columns[:, col_idx]
        store.add_iteration(index, columns[:, col_idx], raw)
    return store


def import_peaks_csv(store: DataStore, path: str | Path) -> None:
    """Merge previously exported peak rows into an existing DataStore's iterations."""
    iteration_by_index = {rec.index: rec for rec in store.iterations}
    peaks_by_iteration: dict[int, list[dict]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            iteration = int(row.pop("iteration"))
            peak = {
                "index": int(row["index"]),
                "time_ms": float(row["time_ms"]),
                "height": float(row["height"]),
                "fwhm_ms": float(row["fwhm_ms"]),
                "resolving_power": float(row["resolving_power"]),
                "snr": float(row["snr"]),
                "k0": float(row["k0"]),
                "ccs_a2": None if row["ccs_a2"] in ("", "None") else float(row["ccs_a2"]),
            }
            peaks_by_iteration.setdefault(iteration, []).append(peak)
    for index, peaks in peaks_by_iteration.items():
        if index in iteration_by_index:
            iteration_by_index[index].peaks = peaks

