"""Shared helpers for exporting raw (as-acquired) and/or processed spectra with clear labels."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

ExportData = Literal["both", "raw", "processed"]
EXPORT_CHOICES: tuple[str, ...] = ("both", "raw", "processed")
DEFAULT_EXPORT: ExportData = "both"
VARIANTS: tuple[str, ...] = ("raw", "processed")


def validate_export_data(data: str) -> list[str]:
    """Return the variants ('raw'/'processed') selected by `data`."""
    if data not in EXPORT_CHOICES:
        raise ValueError(f"data must be one of {EXPORT_CHOICES}, got {data!r}")
    return list(VARIANTS) if data == "both" else [data]


def split_variant(path: str | Path) -> tuple[Path, str | None]:
    """Split `<base>_raw.ext` / `<base>_processed.ext` into (`<base>.ext`, variant).
    Paths without a variant suffix return (path, None)."""
    path = Path(path)
    for variant in VARIANTS:
        suffix = f"_{variant}"
        if path.stem.endswith(suffix):
            return path.with_name(path.stem[: -len(suffix)] + path.suffix), variant
    return path, None


def variant_path(path: str | Path, variant: str) -> Path:
    """`<base>.ext` -> `<base>_<variant>.ext`."""
    path = Path(path)
    return path.with_name(f"{path.stem}_{variant}{path.suffix}")
