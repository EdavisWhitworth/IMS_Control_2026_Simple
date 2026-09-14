"""CSV export for spectra and peak tables."""

from __future__ import annotations

import csv
from pathlib import Path

from ims_control.models.data_store import DataStore


def export_spectra_csv(store: DataStore, path: str | Path) -> None:
    """One row per time point; one column per iteration, plus the shared time axis."""
    time_ms = store.time_axis_ms
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["time_ms"] + [f"iteration_{rec.index}" for rec in store.iterations]
        writer.writerow(header)
        for row_idx, t in enumerate(time_ms):
            row = [t] + [rec.intensity[row_idx] for rec in store.iterations]
            writer.writerow(row)


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
