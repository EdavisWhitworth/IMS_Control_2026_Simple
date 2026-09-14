"""Modal dialog for editing DAQ channel assignments and power-supply scaling."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from ims_control.acquisition.experiment import SystemParameters


class SystemParametersDialog(QDialog):
    """Edits a copy of SystemParameters; call `result_parameters()` after Accepted exec()."""

    def __init__(self, parameters: SystemParameters, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("System Parameters")
        self._build_ui(parameters)

    def _build_ui(self, parameters: SystemParameters) -> None:
        layout = QVBoxLayout(self)

        daq_box = QGroupBox("Acquisition DAQ Channels")
        daq_form = QFormLayout(daq_box)
        self.device_name_edit = QLineEdit(parameters.device_name)
        daq_form.addRow("Device name", self.device_name_edit)
        self.ai_channel_edit = QLineEdit(parameters.ai_channel)
        daq_form.addRow("AI channel (detector)", self.ai_channel_edit)
        self.co_channel_edit = QLineEdit(parameters.co_channel)
        daq_form.addRow("CO channel (gate pulse)", self.co_channel_edit)
        layout.addWidget(daq_box)

        power_box = QGroupBox("Power Supply Channels")
        power_form = QFormLayout(power_box)
        self.ims_cell_ao_edit = QLineEdit(parameters.ims_cell_ao_channel)
        power_form.addRow("IMS cell AO channel", self.ims_cell_ao_edit)
        self.ionization_ao_edit = QLineEdit(parameters.ionization_ao_channel)
        power_form.addRow("Ionization AO channel", self.ionization_ao_edit)
        self.power_do_edit = QLineEdit(parameters.power_do_channel)
        power_form.addRow("Power enable/LED DO channel", self.power_do_edit)

        self.ims_cell_max_kv_spin = QDoubleSpinBox()
        self.ims_cell_max_kv_spin.setRange(0.1, 100.0)
        self.ims_cell_max_kv_spin.setValue(parameters.ims_cell_max_kv)
        self.ims_cell_max_kv_spin.setSuffix(" kV")
        power_form.addRow("IMS cell max output", self.ims_cell_max_kv_spin)

        self.ims_cell_full_scale_v_spin = QDoubleSpinBox()
        self.ims_cell_full_scale_v_spin.setRange(0.1, 10.0)
        self.ims_cell_full_scale_v_spin.setValue(parameters.ims_cell_ao_full_scale_v)
        self.ims_cell_full_scale_v_spin.setSuffix(" V")
        power_form.addRow("IMS cell AO full-scale voltage", self.ims_cell_full_scale_v_spin)

        self.ionization_max_kv_spin = QDoubleSpinBox()
        self.ionization_max_kv_spin.setRange(0.1, 100.0)
        self.ionization_max_kv_spin.setValue(parameters.ionization_max_kv)
        self.ionization_max_kv_spin.setSuffix(" kV")
        power_form.addRow("Ionization max bias", self.ionization_max_kv_spin)

        self.ionization_full_scale_v_spin = QDoubleSpinBox()
        self.ionization_full_scale_v_spin.setRange(0.1, 10.0)
        self.ionization_full_scale_v_spin.setValue(parameters.ionization_ao_full_scale_v)
        self.ionization_full_scale_v_spin.setSuffix(" V")
        power_form.addRow("Ionization AO full-scale voltage", self.ionization_full_scale_v_spin)
        layout.addWidget(power_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_parameters(self) -> SystemParameters:
        return SystemParameters(
            device_name=self.device_name_edit.text(),
            ai_channel=self.ai_channel_edit.text(),
            co_channel=self.co_channel_edit.text(),
            ims_cell_ao_channel=self.ims_cell_ao_edit.text(),
            ionization_ao_channel=self.ionization_ao_edit.text(),
            power_do_channel=self.power_do_edit.text(),
            ims_cell_max_kv=self.ims_cell_max_kv_spin.value(),
            ionization_max_kv=self.ionization_max_kv_spin.value(),
            ims_cell_ao_full_scale_v=self.ims_cell_full_scale_v_spin.value(),
            ionization_ao_full_scale_v=self.ionization_full_scale_v_spin.value(),
        )
