"""Record of the processing and peak-detection settings applied to a run.

Exporters write this (alongside the instrument/ion metadata in `ExperimentConfig`) so a
reader can see exactly which operations produced the processed spectra and peak table.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import ims_control

BASELINE_METHOD = "rolling minimum filter followed by uniform smoothing (same window), scipy.ndimage"
NOISE_METHOD = "mean/std of intensity within the noise window (default: last 10 ms of the trace)"
SNR_DEFINITION = "peak height / noise-window standard deviation"
WIDTH_DEFINITION = "width at half prominence (scipy.signal.peak_widths, rel_height=0.5)"
PEAK_PROMINENCE_AUTO = "5 x noise-window standard deviation"


@dataclass
class ProcessingSettings:
    """Spectrum-processing and peak-detection parameters in effect for a DataStore.

    Processing is always derived from `raw_intensity` in this fixed order:
    positive mode -> baseline subtraction -> normalization.
    """

    positive_mode: bool = False
    subtract_baseline: bool = False
    baseline_window_ms: float = 2.0
    normalize: bool = False
    normalize_scale: str = "0-1"

    # None means "Auto" in the GUI (pick_peaks falls back to its own threshold).
    peak_min_height: float | None = None
    peak_min_prominence: float | None = None
    noise_window_start_ms: float | None = None
    noise_window_end_ms: float | None = None

    def operations(self) -> list[str]:
        """Ordered, human-readable list of the processing operations that were applied."""
        ops: list[str] = []
        if self.positive_mode:
            ops.append("1. positive mode: intensity multiplied by -1")
        if self.subtract_baseline:
            ops.append(
                f"2. baseline subtraction: {BASELINE_METHOD}; window = {self.baseline_window_ms:g} ms"
            )
        if self.normalize:
            ops.append(f"3. normalization: divide by max(abs(intensity)), scale {self.normalize_scale}")
        return ops or ["none (processed == raw)"]

    def to_rows(self) -> list[tuple[str, object, str]]:
        """Flat (parameter, value, description) rows, in a stable order, for tables/sheets."""
        auto_h = "auto (no minimum)" if self.peak_min_height is None else self.peak_min_height
        auto_p = f"auto ({PEAK_PROMINENCE_AUTO})" if self.peak_min_prominence is None else self.peak_min_prominence
        return [
            ("software_version", ims_control.__version__, "IMS Control version that wrote this file"),
            ("positive_mode", self.positive_mode, "step 1: multiply intensity by -1"),
            ("subtract_baseline", self.subtract_baseline, "step 2: subtract estimated baseline"),
            ("baseline_window_ms", self.baseline_window_ms, f"baseline method: {BASELINE_METHOD}"),
            ("normalize", self.normalize, "step 3: divide by max(abs(intensity))"),
            ("normalize_scale", self.normalize_scale, "0-1 or 0-100%"),
            ("peak_min_height", auto_h, "find_peaks minimum height (processed units)"),
            ("peak_min_prominence", auto_p, "find_peaks minimum prominence (processed units)"),
            ("noise_window_start_ms", self.noise_window_start_ms, NOISE_METHOD),
            ("noise_window_end_ms", self.noise_window_end_ms, NOISE_METHOD),
            ("snr_definition", SNR_DEFINITION, "how the SNR column is computed"),
            ("width_definition", WIDTH_DEFINITION, "how the FWHM column is computed"),
            ("operations", "; ".join(self.operations()), "ordered processing steps applied"),
        ]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["software_version"] = ims_control.__version__
        data["operations"] = self.operations()
        data["snr_definition"] = SNR_DEFINITION
        data["width_definition"] = WIDTH_DEFINITION
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessingSettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_rows(cls, rows: dict[str, object]) -> "ProcessingSettings":
        """Inverse of `to_rows` for a {parameter: value} mapping read back from a sheet."""

        def optional_float(value):
            return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

        return cls(
            positive_mode=bool(rows.get("positive_mode", False)),
            subtract_baseline=bool(rows.get("subtract_baseline", False)),
            baseline_window_ms=float(rows.get("baseline_window_ms", 2.0)),
            normalize=bool(rows.get("normalize", False)),
            normalize_scale=str(rows.get("normalize_scale", "0-1")),
            peak_min_height=optional_float(rows.get("peak_min_height")),
            peak_min_prominence=optional_float(rows.get("peak_min_prominence")),
            noise_window_start_ms=optional_float(rows.get("noise_window_start_ms")),
            noise_window_end_ms=optional_float(rows.get("noise_window_end_ms")),
        )
