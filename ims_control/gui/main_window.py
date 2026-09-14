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
from ims_control.acquisition.experiment import ExperimentConfig, SystemParameters
from ims_control.daq.power_supply import PowerSupplyBackend, SimulatedPowerSupplyBackend
from ims_control.daq.simulator import SimulatedDAQBackend
from ims_control.gui.control_panel import ControlPanel
from ims_control.gui.heatmap_panel import HeatmapPanel
from ims_control.gui.peak_table import PeakTablePanel
from ims_control.gui.plot_panel import PlotPanel
from ims_control.gui.system_parameters_dialog import SystemParametersDialog
from ims_control.io.csv_io import export_peaks_csv, export_spectra_csv
from ims_control.io.hdf5_io import export_hdf5
from ims_control.io.mzml_io import export_mzml
from ims_control.io.settings_io import load_defaults, save_defaults
from ims_control.models.data_store import DataStore
from ims_control.processing.peak_picking import pick_peaks


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMS Control")
        self.resize(1400, 900)

        self.store: DataStore | None = None
        self.worker: AcquisitionWorker | None = None
        self.system_parameters = SystemParameters()
        self.power_backend: PowerSupplyBackend | None = None

        self.control_panel = ControlPanel()
        self.control_panel.apply_system_parameters(self.system_parameters)
        self.plot_panel = PlotPanel()
        self.heatmap_panel = HeatmapPanel()
        self.peak_table = PeakTablePanel()

        self._build_layout()
        self._wire_signals()
        self._set_power_indicator(False)
        self._load_saved_defaults()

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
        self.control_panel.system_parameters_requested.connect(self._on_system_parameters_requested)
        self.control_panel.power_kv_changed.connect(self._on_power_kv_changed)
        self.control_panel.power_toggle_requested.connect(self._on_power_toggle_requested)
        self.control_panel.save_defaults_requested.connect(self._on_save_defaults_requested)
        self.control_panel.power_simulator_checkbox.toggled.connect(self._on_power_mode_toggled)
        self.control_panel.metadata_changed.connect(self._on_metadata_changed)
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

        if not self.control_panel.is_power_enabled():
            proceed = QMessageBox.warning(
                self,
                "Power supplies are off",
                "The IMS cell and Ionization power supplies are currently OFF.\n\n"
                "Start the analysis anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
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

    def _on_metadata_changed(self) -> None:
        """Recompute K0/CCS for every stored iteration using the latest metadata field values."""
        if self.store is None:
            return
        metadata = self.control_panel.metadata_values()
        for key, value in metadata.items():
            setattr(self.store.config, key, value)

        for record in self.store.iterations:
            peaks = pick_peaks(self.store.time_axis_ms, record.intensity, **metadata)
            record.peaks = [p.__dict__ for p in peaks]

        if len(self.store) > 0:
            self._refresh_current_view(self.plot_panel.selected_iteration())

    def _on_system_parameters_requested(self) -> None:
        if self.control_panel.is_power_enabled():
            QMessageBox.warning(
                self,
                "Power supplies are on",
                "Turn off the power supplies before editing system parameters.",
            )
            return
        dialog = SystemParametersDialog(self.system_parameters, self)
        if dialog.exec() == SystemParametersDialog.DialogCode.Accepted:
            self.system_parameters = dialog.result_parameters()
            self.control_panel.apply_system_parameters(self.system_parameters)
            self.power_backend = None  # force reconfiguration with the new channel assignments

    def _load_saved_defaults(self) -> None:
        saved = load_defaults()
        if saved is None:
            return
        self.system_parameters = saved["system_parameters"]
        self.control_panel.apply_system_parameters(self.system_parameters)
        self.control_panel.apply_experiment_defaults(
            saved["experiment"],
            saved["use_simulator"],
            saved["use_simulated_power"],
            saved["ims_cell_kv"],
            saved["ionization_kv"],
        )

    def _on_save_defaults_requested(self) -> None:
        ims_kv, ionization_kv = self.control_panel.power_kv_values()
        save_defaults(
            self.control_panel.build_config(),
            self.system_parameters,
            self.control_panel.simulator_checkbox.isChecked(),
            self.control_panel.power_simulator_checkbox.isChecked(),
            ims_kv,
            ionization_kv,
        )
        QMessageBox.information(self, "Defaults saved", "Current settings saved as the new defaults.")

    def _get_power_backend(self) -> PowerSupplyBackend | None:
        if self.power_backend is not None:
            return self.power_backend
        if self.control_panel.power_simulator_checkbox.isChecked():
            backend: PowerSupplyBackend = SimulatedPowerSupplyBackend()
        else:
            from ims_control.daq.power_supply import NIPowerSupplyBackend

            try:
                backend = NIPowerSupplyBackend()
            except RuntimeError as exc:
                QMessageBox.critical(self, "Power supply DAQ unavailable", str(exc))
                return None
        backend.configure(
            device_name=self.system_parameters.device_name,
            ims_cell_ao_channel=self.system_parameters.ims_cell_ao_channel,
            ionization_ao_channel=self.system_parameters.ionization_ao_channel,
            power_do_channel=self.system_parameters.power_do_channel,
        )
        self.power_backend = backend
        return backend

    def _on_power_kv_changed(self, ims_cell_kv: float, ionization_kv: float) -> None:
        backend = self._get_power_backend()
        if backend is None:
            return
        backend.set_ims_cell_kv(ims_cell_kv, self.system_parameters.ims_cell_max_kv)
        # Ionization is a bias on top of the IMS cell output, so the supply's true output
        # setpoint is their sum (e.g. 5 kV cell + 3 kV bias = 8 kV written to the ionization AO).
        backend.set_ionization_output_kv(
            ims_cell_kv + ionization_kv, self.system_parameters.ionization_max_kv
        )

    def _on_power_toggle_requested(self, enabled: bool) -> None:
        backend = self._get_power_backend()
        if backend is None:
            self.control_panel.set_power_indicator(False)
            return
        backend.set_enabled(enabled)
        if enabled:
            ims_kv, ionization_kv = self.control_panel.power_kv_values()
            backend.set_ims_cell_kv(ims_kv, self.system_parameters.ims_cell_max_kv)
            backend.set_ionization_output_kv(
                ims_kv + ionization_kv, self.system_parameters.ionization_max_kv
            )
        self._set_power_indicator(enabled)

    def _on_power_mode_toggled(self, _checked: bool) -> None:
        if self.control_panel.is_power_enabled():
            return  # avoid swapping backends out from under an active supply
        self.power_backend = None  # force reconfiguration against the newly selected backend

    def _set_power_indicator(self, enabled: bool) -> None:
        self.control_panel.set_power_indicator(enabled)

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
