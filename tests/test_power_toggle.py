from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from ims_control.daq.power_supply import PowerSupplyBackend  # noqa: E402
from ims_control.gui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


class RecordingPowerBackend(PowerSupplyBackend):
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[tuple] = []
        self.fail_on = fail_on

    def configure(
        self,
        *,
        device_name: str,
        ims_cell_ao_channel: str,
        ionization_ao_channel: str,
        power_do_channel: str,
    ) -> None:
        pass

    def close(self) -> None:
        pass

    def _record(self, operation: tuple) -> None:
        self.calls.append(operation)
        if operation[0] == self.fail_on:
            raise RuntimeError(f"{self.fail_on} failed")

    def set_ims_cell_kv(self, kv: float, max_kv: float, full_scale_v: float) -> None:
        self._record(("ims_cell", kv, max_kv, full_scale_v))

    def set_ionization_output_kv(self, kv: float, max_kv: float, full_scale_v: float) -> None:
        self._record(("ionization", kv, max_kv, full_scale_v))

    def set_enabled(self, enabled: bool) -> None:
        self._record(("enabled", enabled))


def _window_with_backend(backend: RecordingPowerBackend) -> MainWindow:
    window = MainWindow()
    window.power_backend = backend
    window.control_panel.ims_cell_kv_spin.setValue(10.0)
    window.control_panel.ionization_kv_spin.setValue(3.0)
    return window


def test_power_off_zeros_both_ao_outputs_before_disabling(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    backend = RecordingPowerBackend()
    window = _window_with_backend(backend)

    window._on_power_toggle_requested(False)

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert backend.calls[0][1] == 0.0
    assert backend.calls[1][1] == 0.0
    assert backend.calls[2] == ("enabled", False)
    assert not window.control_panel.is_power_enabled()


def test_power_on_sets_outputs_before_enabling(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    backend = RecordingPowerBackend()
    window = _window_with_backend(backend)

    window._on_power_toggle_requested(True)

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert backend.calls[0][1] == 10.0
    assert backend.calls[1][1] == 13.0
    assert backend.calls[2] == ("enabled", True)
    assert window.control_panel.is_power_enabled()


def test_power_off_attempts_all_commands_and_reports_failure(monkeypatch):
    messages = Mock()
    monkeypatch.setattr(QMessageBox, "critical", messages)
    backend = RecordingPowerBackend(fail_on="ims_cell")
    window = _window_with_backend(backend)
    window.control_panel.set_power_indicator(True)

    window._on_power_toggle_requested(False)

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert backend.calls[2] == ("enabled", False)
    assert window.control_panel.is_power_enabled()
    messages.assert_called_once()
    assert "may still be energized" in messages.call_args.args[2]
    assert "IMS cell AO: ims_cell failed" in messages.call_args.args[2]


def test_power_setpoint_changes_do_not_write_ao_while_power_is_off(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    backend = RecordingPowerBackend()
    window = _window_with_backend(backend)

    window.control_panel.ims_cell_kv_spin.setValue(12.0)

    assert backend.calls == []


def test_unavailable_backend_does_not_indicate_power_is_off(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    window = MainWindow()
    monkeypatch.setattr(window, "_get_power_backend", lambda: None)

    window._on_power_toggle_requested(False)

    assert window.control_panel.is_power_enabled()


def test_startup_zeros_both_ao_outputs_and_disables_power(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    backend = RecordingPowerBackend()
    monkeypatch.setattr(MainWindow, "_get_power_backend", lambda self: backend)

    window = MainWindow()

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert backend.calls[0][1] == 0.0
    assert backend.calls[1][1] == 0.0
    assert backend.calls[2] == ("enabled", False)
    assert not window.control_panel.is_power_enabled()


def test_close_zeros_both_ao_outputs_and_disables_power(monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    backend = RecordingPowerBackend()
    monkeypatch.setattr(MainWindow, "_get_power_backend", lambda self: backend)
    window = MainWindow()
    backend.calls.clear()
    event = QCloseEvent()

    window.closeEvent(event)

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert backend.calls[0][1] == 0.0
    assert backend.calls[1][1] == 0.0
    assert backend.calls[2] == ("enabled", False)
    assert event.isAccepted()


def test_close_reports_failed_power_off_attempt(monkeypatch):
    messages = Mock()
    monkeypatch.setattr(QMessageBox, "critical", messages)
    backend = RecordingPowerBackend(fail_on="ionization")
    monkeypatch.setattr(MainWindow, "_get_power_backend", lambda self: backend)
    window = MainWindow()
    backend.calls.clear()
    messages.reset_mock()
    event = QCloseEvent()

    window.closeEvent(event)

    assert [call[0] for call in backend.calls] == ["ims_cell", "ionization", "enabled"]
    assert messages.call_count == 1
    assert "Shutdown power-off failed" in messages.call_args.args[1]
    assert "Ionization AO: ionization failed" in messages.call_args.args[2]
    assert event.isAccepted()
