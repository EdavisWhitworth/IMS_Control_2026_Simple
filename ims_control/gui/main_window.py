"""Top-level main window wiring the control panel, plots, peak table, and export controls."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from ims_control.acquisition.controller import AcquisitionWorker
from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.daq.simulator import SimulatedDAQBackend
from ims_control.gui.control_panel import ControlPanel
from ims_control.gui.heatmap_panel import HeatmapPanel
from ims_control.gui.peak_table import PeakTablePanel
from ims_control.gui.plot_panel import PlotPanel
from ims_control.io.csv_io import export_peaks_csv, export_spectra_csv
from ims_control.io.hdf5_io import export_hdf5
from ims_control.io.mzml_io import export_mzml
from ims_control.models.data_store import DataStore
from ims_control.processing.peak_picking import pick_peaks


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMS Control")
        self.resize(1400, 900)

        self.store: DataStore | None = None
        self.worker: AcquisitionWorker | None = None

        self.control_panel = ControlPanel()
        self.plot_panel = PlotPanel()
        self.heatmap_panel = HeatmapPanel()
        self.peak_table = PeakTablePanel()

        self._build_layout()
        self._wire_signals()

    def _build_layout(self) -> None:
        export_row = QHBoxLayout()
        self.export_csv_button = QPushButton("Export CSV")
        self.export_hdf5_button = QPushButton("Export HDF5")
        self.export_mzml_button = QPushButton("Export mzML")
        for button in (self.export_csv_button, self.export_hdf5_button, self.export_mzml_button):
            button.setMinimumHeight(56)
            export_row.addWidget(button)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        plots_splitter = QSplitter(Qt.Orientation.Vertical)
        plots_splitter.addWidget(self.plot_panel)
        plots_splitter.addWidget(self.heatmap_panel)
        plots_splitter.addWidget(self.peak_table)
        right_layout.addWidget(plots_splitter)
        right_layout.addLayout(export_row)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.control_panel)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(main_splitter)

    def _wire_signals(self) -> None:
        self.control_panel.start_requested.connect(self._on_start_requested)
        self.control_panel.stop_requested.connect(self._on_stop_requested)
        self.control_panel.pause_toggled.connect(self._on_pause_toggled)
        self.plot_panel.iteration_selection_changed.connect(self._refresh_current_view)

        self.export_csv_button.clicked.connect(self._on_export_csv)
        self.export_hdf5_button.clicked.connect(self._on_export_hdf5)
        self.export_mzml_button.clicked.connect(self._on_export_mzml)

    def _on_start_requested(self, config: ExperimentConfig, use_simulator: bool) -> None:
        try:
            config.validate()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid parameters", str(exc))
            return

        if not use_simulator:
            from ims_control.daq.ni_daq import NIDAQBackend

            try:
                backend = NIDAQBackend()
            except RuntimeError as exc:
                QMessageBox.critical(self, "DAQ unavailable", str(exc))
                return
        else:
            backend = SimulatedDAQBackend()

        self.store = DataStore(config)
        self.plot_panel.set_available_iterations(0)
        self.heatmap_panel.update_image(self.store.as_2d_array(), self.store.time_axis_ms)
        self.peak_table.set_peaks([])

        self.worker = AcquisitionWorker(backend, config)
        self.worker.iteration_ready.connect(self._on_iteration_ready)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.control_panel.set_running_state(True)
        self.worker.start()

    def _on_stop_requested(self) -> None:
        if self.worker is not None:
            self.worker.stop()

    def _on_pause_toggled(self, paused: bool) -> None:
        if self.worker is not None:
            self.worker.set_paused(paused)

    def _on_iteration_ready(self, index: int, intensity) -> None:
        if self.store is None:
            return
        record = self.store.add_iteration(index, intensity)
        peaks = pick_peaks(
            self.store.time_axis_ms,
            intensity,
            drift_length_cm=self.store.config.drift_length_cm,
            drift_voltage_v=self.store.config.drift_voltage_v,
            pressure_torr=self.store.config.pressure_torr,
            temperature_k=self.store.config.temperature_k,
            gas_type=self.store.config.gas_type,
            ion_mz=self.store.config.ion_mz,
            ion_charge=self.store.config.ion_charge,
        )
        self.store.set_peaks(index, [p.__dict__ for p in peaks])
        record.peaks = [p.__dict__ for p in peaks]

        self.plot_panel.set_available_iterations(len(self.store))
        self.heatmap_panel.update_image(self.store.as_2d_array(), self.store.time_axis_ms)
        if self.plot_panel.selected_iteration() == self.plot_panel.CURRENT_SENTINEL:
            self.plot_panel.update_curve(self.store.time_axis_ms, intensity)
            self.peak_table.set_peaks(peaks)

    def _on_progress(self, current: int, total: int) -> None:
        self.control_panel.progress_bar.setMaximum(total)
        self.control_panel.progress_bar.setValue(current)

    def _on_finished(self) -> None:
        self.control_panel.set_running_state(False)

    def _on_error(self, message: str) -> None:
        self.control_panel.set_running_state(False)
        QMessageBox.critical(self, "Acquisition error", message)

    def _refresh_current_view(self, iteration_index: int) -> None:
        if self.store is None or len(self.store) == 0:
            return
        if iteration_index == self.plot_panel.CURRENT_SENTINEL:
            iteration_index = len(self.store) - 1
        record = self.store.get_iteration(iteration_index)
        self.plot_panel.update_curve(self.store.time_axis_ms, record.intensity)
        self.peak_table.set_peaks(record.peaks)

    def _on_export_csv(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export spectra CSV", filter="CSV (*.csv)")
        if not path:
            return
        export_spectra_csv(self.store, path)
        peaks_path = path.rsplit(".", 1)[0] + "_peaks.csv"
        export_peaks_csv(self.store, peaks_path)

    def _on_export_hdf5(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export HDF5", filter="HDF5 (*.h5)")
        if path:
            export_hdf5(self.store, path)

    def _on_export_mzml(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export mzML", filter="mzML (*.mzml)")
        if path:
            export_mzml(self.store, path)

    def _require_data(self) -> bool:
        if self.store is None or len(self.store) == 0:
            QMessageBox.information(self, "No data", "Run an experiment before exporting.")
            return False
        return True
