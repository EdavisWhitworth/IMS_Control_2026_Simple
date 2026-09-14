"""Peak parameter table for the currently selected iteration."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ims_control.processing.peak_picking import PeakResult

_COLUMNS = [
    ("time_ms", "Time (ms)"),
    ("height", "Height"),
    ("fwhm_ms", "FWHM (ms)"),
    ("resolving_power", "Resolving Power"),
    ("snr", "S/N"),
    ("k0", "K0 (cm2/V/s)"),
    ("ccs_a2", "CCS (A^2)"),
]


class PeakTablePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def set_peaks(self, peaks: list[PeakResult] | list[dict]) -> None:
        self.table.setRowCount(len(peaks))
        for row, peak in enumerate(peaks):
            values = peak.__dict__ if hasattr(peak, "__dict__") else peak
            for col, (key, _label) in enumerate(_COLUMNS):
                value = values.get(key)
                text = "-" if value is None else f"{value:.4g}" if isinstance(value, float) else str(value)
                self.table.setItem(row, col, QTableWidgetItem(text))
