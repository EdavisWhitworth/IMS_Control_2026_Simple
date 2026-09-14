"""Operator control panel: experiment parameters, DAQ channel config, and run controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ims_control.acquisition.experiment import ExperimentConfig, SystemParameters


class ControlPanel(QWidget):
    """Emits `start_requested` with a populated ExperimentConfig when the operator clicks Start."""

    start_requested = Signal(ExperimentConfig, bool)  # (config, use_simulator)
    stop_requested = Signal()
    pause_toggled = Signal(bool)
    system_parameters_requested = Signal()
    power_kv_changed = Signal(float, float)  # (ims_cell_kv, ionization_kv)
    power_toggle_requested = Signal(bool)  # requested enabled state
    save_defaults_requested = Signal()
    metadata_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._system_parameters = SystemParameters()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        timing_box = QGroupBox("Experiment Parameters")
        timing_form = QFormLayout(timing_box)
        self.pulse_width_spin = QDoubleSpinBox()
        self.pulse_width_spin.setRange(0.01, 1000.0)
        self.pulse_width_spin.setDecimals(3)
        self.pulse_width_spin.setValue(0.2)
        self.pulse_width_spin.setSuffix(" ms")
        timing_form.addRow("Gate pulse width", self.pulse_width_spin)

        self.exp_length_spin = QDoubleSpinBox()
        self.exp_length_spin.setRange(1.0, 100000.0)
        self.exp_length_spin.setValue(50.0)
        self.exp_length_spin.setSuffix(" ms")
        timing_form.addRow("Experiment length", self.exp_length_spin)

        self.num_points_spin = QSpinBox()
        self.num_points_spin.setRange(2, 1_000_000)
        self.num_points_spin.setValue(4000)
        timing_form.addRow("Data points", self.num_points_spin)

        self.averages_spin = QSpinBox()
        self.averages_spin.setRange(1, 100_000)
        self.averages_spin.setValue(10)
        timing_form.addRow("Averages per iteration", self.averages_spin)

        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(1, 1_000_000)
        self.iterations_spin.setValue(20)
        timing_form.addRow("Total iterations", self.iterations_spin)
        layout.addWidget(timing_box)

        daq_box = QGroupBox("Acquisition Mode")
        daq_form = QFormLayout(daq_box)
        self.simulator_checkbox = QCheckBox("Use simulated DAQ (no hardware)")
        self.simulator_checkbox.setChecked(True)
        daq_form.addRow(self.simulator_checkbox)
        self.system_parameters_button = QPushButton("System Parameters...")
        daq_form.addRow(self.system_parameters_button)
        self.save_defaults_button = QPushButton("Save Current as Defaults")
        daq_form.addRow(self.save_defaults_button)
        layout.addWidget(daq_box)

        power_box = QGroupBox("Power Supplies")
        power_form = QFormLayout(power_box)
        self.power_simulator_checkbox = QCheckBox("Use simulated power supplies (no hardware)")
        self.power_simulator_checkbox.setChecked(True)
        power_form.addRow(self.power_simulator_checkbox)

        self.ims_cell_kv_spin = QDoubleSpinBox()
        self.ims_cell_kv_spin.setRange(0.0, self._system_parameters.ims_cell_max_kv)
        self.ims_cell_kv_spin.setSuffix(" kV")
        power_form.addRow("IMS cell", self.ims_cell_kv_spin)

        self.ionization_kv_spin = QDoubleSpinBox()
        self.ionization_kv_spin.setRange(0.0, self._system_parameters.ionization_max_kv)
        self.ionization_kv_spin.setSuffix(" kV bias")
        power_form.addRow("Ionization", self.ionization_kv_spin)

        self.power_toggle_button = QPushButton("Power OFF")
        self.power_toggle_button.setCheckable(True)
        self._style_power_button(False)
        power_form.addRow(self.power_toggle_button)
        layout.addWidget(power_box)

        metadata_box = QGroupBox("Instrument / Ion Metadata (for K0 and CCS)")
        metadata_form = QFormLayout(metadata_box)
        self.drift_length_spin = QDoubleSpinBox()
        self.drift_length_spin.setRange(0.1, 1000.0)
        self.drift_length_spin.setValue(10.0)
        self.drift_length_spin.setSuffix(" cm")
        metadata_form.addRow("Drift length", self.drift_length_spin)

        self.drift_voltage_spin = QDoubleSpinBox()
        self.drift_voltage_spin.setRange(1.0, 100000.0)
        self.drift_voltage_spin.setValue(1000.0)
        self.drift_voltage_spin.setSuffix(" V")
        metadata_form.addRow("Drift voltage", self.drift_voltage_spin)

        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(1.0, 2000.0)
        self.pressure_spin.setValue(760.0)
        self.pressure_spin.setSuffix(" torr")
        metadata_form.addRow("Pressure", self.pressure_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(1.0, 1000.0)
        self.temperature_spin.setValue(298.0)
        self.temperature_spin.setSuffix(" K")
        metadata_form.addRow("Temperature", self.temperature_spin)

        self.gas_type_combo = QComboBox()
        self.gas_type_combo.addItems(["N2", "HE", "AIR", "CO2", "AR"])
        metadata_form.addRow("Buffer gas", self.gas_type_combo)

        self.ion_mz_spin = QDoubleSpinBox()
        self.ion_mz_spin.setRange(0.0, 1_000_000.0)
        self.ion_mz_spin.setDecimals(4)
        self.ion_mz_spin.setValue(0.0)
        metadata_form.addRow("Ion m/z (0 = skip CCS)", self.ion_mz_spin)

        self.ion_charge_spin = QSpinBox()
        self.ion_charge_spin.setRange(1, 20)
        self.ion_charge_spin.setValue(1)
        metadata_form.addRow("Ion charge", self.ion_charge_spin)
        layout.addWidget(metadata_box)

        controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCheckable(True)
        self.stop_button = QPushButton("Stop")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)
        layout.addLayout(controls_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("Iteration %v / %m")
        layout.addWidget(self.progress_bar)
        layout.addStretch(1)

        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.pause_button.toggled.connect(self._on_pause_toggled)
        self.system_parameters_button.clicked.connect(lambda: self.system_parameters_requested.emit())
        self.save_defaults_button.clicked.connect(lambda: self.save_defaults_requested.emit())
        self.ims_cell_kv_spin.valueChanged.connect(self._on_power_kv_changed)
        self.ionization_kv_spin.valueChanged.connect(self._on_power_kv_changed)
        self.power_toggle_button.toggled.connect(self._on_power_toggled)
        self.drift_length_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())
        self.drift_voltage_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())
        self.pressure_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())
        self.temperature_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())
        self.gas_type_combo.currentTextChanged.connect(lambda _text: self.metadata_changed.emit())
        self.ion_mz_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())
        self.ion_charge_spin.valueChanged.connect(lambda _value: self.metadata_changed.emit())

    def build_config(self) -> ExperimentConfig:
        return ExperimentConfig(
            pulse_width_ms=self.pulse_width_spin.value(),
            exp_length_ms=self.exp_length_spin.value(),
            num_points=self.num_points_spin.value(),
            averages=self.averages_spin.value(),
            iterations=self.iterations_spin.value(),
            device_name=self._system_parameters.device_name,
            ai_channel=self._system_parameters.ai_channel,
            co_channel=self._system_parameters.co_channel,
            drift_length_cm=self.drift_length_spin.value(),
            drift_voltage_v=self.drift_voltage_spin.value(),
            pressure_torr=self.pressure_spin.value(),
            temperature_k=self.temperature_spin.value(),
            gas_type=self.gas_type_combo.currentText(),
            ion_mz=self.ion_mz_spin.value(),
            ion_charge=self.ion_charge_spin.value(),
        )

    def set_running_state(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.stop_button.setEnabled(running)
        if not running:
            self.pause_button.setChecked(False)

    def _on_start_clicked(self) -> None:
        self.start_requested.emit(self.build_config(), self.simulator_checkbox.isChecked())

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()

    def _on_pause_toggled(self, checked: bool) -> None:
        self.pause_button.setText("Resume" if checked else "Pause")
        self.pause_toggled.emit(checked)

    def apply_system_parameters(self, parameters: SystemParameters) -> None:
        """Update the stored parameters and the kV spinbox ranges they imply."""
        self._system_parameters = parameters
        self.ims_cell_kv_spin.setMaximum(parameters.ims_cell_max_kv)
        self.ionization_kv_spin.setMaximum(parameters.ionization_max_kv)

    def apply_experiment_defaults(
        self,
        config: ExperimentConfig,
        use_simulator: bool,
        use_simulated_power: bool,
        ims_cell_kv: float,
        ionization_kv: float,
    ) -> None:
        """Populate every operator-facing field from a previously saved default set."""
        self.pulse_width_spin.setValue(config.pulse_width_ms)
        self.exp_length_spin.setValue(config.exp_length_ms)
        self.num_points_spin.setValue(config.num_points)
        self.averages_spin.setValue(config.averages)
        self.iterations_spin.setValue(config.iterations)
        self.drift_length_spin.setValue(config.drift_length_cm)
        self.drift_voltage_spin.setValue(config.drift_voltage_v)
        self.pressure_spin.setValue(config.pressure_torr)
        self.temperature_spin.setValue(config.temperature_k)
        gas_index = self.gas_type_combo.findText(config.gas_type)
        if gas_index >= 0:
            self.gas_type_combo.setCurrentIndex(gas_index)
        self.ion_mz_spin.setValue(config.ion_mz)
        self.ion_charge_spin.setValue(config.ion_charge)
        self.simulator_checkbox.setChecked(use_simulator)
        self.power_simulator_checkbox.setChecked(use_simulated_power)
        # Block signals: populating saved kV setpoints must not write to hardware on its own.
        self.ims_cell_kv_spin.blockSignals(True)
        self.ims_cell_kv_spin.setValue(ims_cell_kv)
        self.ims_cell_kv_spin.blockSignals(False)
        self.ionization_kv_spin.blockSignals(True)
        self.ionization_kv_spin.setValue(ionization_kv)
        self.ionization_kv_spin.blockSignals(False)

    def is_power_enabled(self) -> bool:
        return self.power_toggle_button.isChecked()

    def power_kv_values(self) -> tuple[float, float]:
        return self.ims_cell_kv_spin.value(), self.ionization_kv_spin.value()

    def metadata_values(self) -> dict:
        """Current K0/CCS instrument+ion metadata, for recomputing peaks on the fly."""
        return {
            "drift_length_cm": self.drift_length_spin.value(),
            "drift_voltage_v": self.drift_voltage_spin.value(),
            "pressure_torr": self.pressure_spin.value(),
            "temperature_k": self.temperature_spin.value(),
            "gas_type": self.gas_type_combo.currentText(),
            "ion_mz": self.ion_mz_spin.value(),
            "ion_charge": self.ion_charge_spin.value(),
        }

    def set_power_indicator(self, enabled: bool) -> None:
        """Sync the toggle button's visual state without re-emitting power_toggle_requested."""
        self.power_toggle_button.blockSignals(True)
        self.power_toggle_button.setChecked(enabled)
        self._style_power_button(enabled)
        self.power_toggle_button.blockSignals(False)

    def _on_power_kv_changed(self, _value: float) -> None:
        ims_kv, ionization_kv = self.power_kv_values()
        self.power_kv_changed.emit(ims_kv, ionization_kv)

    def _on_power_toggled(self, checked: bool) -> None:
        self._style_power_button(checked)
        self.power_toggle_requested.emit(checked)

    def _style_power_button(self, enabled: bool) -> None:
        self.power_toggle_button.setText("Power ON" if enabled else "Power OFF")
        color = "#c62828" if enabled else "#2e7d32"  # red = on, green = off
        self.power_toggle_button.setStyleSheet(
            f"background-color: {color}; color: white; font-weight: bold;"
        )
