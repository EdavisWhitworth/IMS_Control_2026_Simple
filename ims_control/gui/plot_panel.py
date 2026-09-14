"""X/Y line plot of a single iteration, selectable as live-updating current or any past run."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PlotPanel(QWidget):
    """Shows the drift spectrum for the iteration chosen in the selector combo box."""

    iteration_selection_changed = Signal(int)  # -1 means "current/live"
    CURRENT_SENTINEL = -1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Iteration:"))
        self.iteration_combo = QComboBox()
        self.iteration_combo.addItem("Current (live)", self.CURRENT_SENTINEL)
        selector_row.addWidget(self.iteration_combo)
        selector_row.addStretch(1)
        layout.addLayout(selector_row)

        self.plot_widget = pg.PlotWidget()
        # pyqtgraph defaults to a black background; without this the black trace is invisible.
        self.plot_widget.setBackground("w")
        self.plot_widget.setLabel("bottom", "Drift time", units="ms")
        self.plot_widget.setLabel("left", "Intensity")
        self.plot_widget.getAxis("bottom").setPen("k")
        self.plot_widget.getAxis("left").setPen("k")
        self.plot_widget.getAxis("bottom").setTextPen("k")
        self.plot_widget.getAxis("left").setTextPen("k")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color="k", width=1.5))
        layout.addWidget(self.plot_widget)

        self.iteration_combo.currentIndexChanged.connect(self._on_combo_changed)

    def selected_iteration(self) -> int:
        return self.iteration_combo.currentData()

    def set_available_iterations(self, count: int) -> None:
        """Repopulate the combo box, preserving "Current (live)" plus one entry per iteration."""
        previous = self.selected_iteration()
        self.iteration_combo.blockSignals(True)
        self.iteration_combo.clear()
        self.iteration_combo.addItem("Current (live)", self.CURRENT_SENTINEL)
        for i in range(count):
            self.iteration_combo.addItem(f"Iteration {i}", i)
        restore_index = self.iteration_combo.findData(previous)
        self.iteration_combo.setCurrentIndex(restore_index if restore_index >= 0 else 0)
        self.iteration_combo.blockSignals(False)

    def update_curve(self, time_ms: np.ndarray, intensity: np.ndarray) -> None:
        self.curve.setData(time_ms, intensity)

    def _on_combo_changed(self, _index: int) -> None:
        self.iteration_selection_changed.emit(self.selected_iteration())
