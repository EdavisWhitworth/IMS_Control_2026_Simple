"""2D colormapped heatmap of all iterations (drift time x iteration, intensity as color)."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class HeatmapPanel(QWidget):
    """ImageItem + right-side HistogramLUTWidget, rainbow colormap over all iterations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.plot_item = self.graphics_widget.addPlot()
        self.plot_item.setLabel("bottom", "Drift time", units="ms")
        self.plot_item.setLabel("left", "Iteration")

        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        self.histogram = pg.HistogramLUTItem()
        self.histogram.setImageItem(self.image_item)
        self.histogram.gradient.loadPreset("spectrum")
        self.graphics_widget.addItem(self.histogram)

        layout.addWidget(self.graphics_widget)

    def update_image(self, data_2d: np.ndarray, time_ms: np.ndarray) -> None:
        """`data_2d` has shape (n_iterations, num_points)."""
        if data_2d.size == 0:
            return
        self.image_item.setImage(data_2d.T, autoLevels=True)
        n_iterations, num_points = data_2d.shape
        x_scale = (time_ms[-1] - time_ms[0]) / max(num_points - 1, 1)
        self.image_item.setRect(0, 0, time_ms[-1] - time_ms[0], n_iterations)
        self.image_item.setPos(time_ms[0], 0)
        _ = x_scale  # setRect already encodes the scaling via width/height
