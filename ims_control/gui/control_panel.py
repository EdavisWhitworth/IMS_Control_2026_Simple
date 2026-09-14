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
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ims_control.acquisition.experiment import ExperimentConfig


class ControlPanel(QWidget):
    """Emits `start_requested` with a populated ExperimentConfig when the operator clicks Start."""

    start_requested = Signal(ExperimentConfig, bool)  # (config, use_simulator)
    stop_requested = Signal()
    pause_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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

        daq_box = QGroupBox("DAQ Configuration")
        daq_form = QFormLayout(daq_box)
        self.simulator_checkbox = QCheckBox("Use simulated DAQ (no hardware)")
        self.simulator_checkbox.setChecked(True)
        daq_form.addRow(self.simulator_checkbox)

        self.device_name_edit = QLineEdit("Dev1")
        daq_form.addRow("Device name", self.device_name_edit)
        self.ai_channel_edit = QLineEdit("ai0")
        daq_form.addRow("AI channel (detector)", self.ai_channel_edit)
        self.co_channel_edit = QLineEdit("ctr0")
        daq_form.addRow("CO channel (gate pulse)", self.co_channel_edit)
        layout.addWidget(daq_box)

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

    def build_config(self) -> ExperimentConfig:
        return ExperimentConfig(
            pulse_width_ms=self.pulse_width_spin.value(),
            exp_length_ms=self.exp_length_spin.value(),
            num_points=self.num_points_spin.value(),
            averages=self.averages_spin.value(),
            iterations=self.iterations_spin.value(),
            device_name=self.device_name_edit.text(),
            ai_channel=self.ai_channel_edit.text(),
            co_channel=self.co_channel_edit.text(),
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
