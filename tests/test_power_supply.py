import pytest

from ims_control.acquisition.experiment import SystemParameters
from ims_control.daq.power_supply import SimulatedPowerSupplyBackend, kv_to_volts


def test_kv_to_volts_scaling():
    assert kv_to_volts(0.0, 15.0) == 0.0
    assert kv_to_volts(15.0, 15.0) == 10.0
    assert kv_to_volts(7.5, 15.0) == 5.0


def test_kv_to_volts_clips_to_range():
    assert kv_to_volts(-5.0, 15.0) == 0.0
    assert kv_to_volts(30.0, 15.0) == 10.0


def test_kv_to_volts_zero_max_is_safe():
    assert kv_to_volts(5.0, 0.0) == 0.0


def test_kv_to_volts_custom_full_scale():
    assert kv_to_volts(15.0, 15.0, full_scale_v=5.0) == 5.0
    assert kv_to_volts(7.5, 15.0, full_scale_v=5.0) == 2.5
    assert kv_to_volts(30.0, 15.0, full_scale_v=5.0) == 5.0  # clipped


def test_simulated_power_supply_backend_tracks_state():
    backend = SimulatedPowerSupplyBackend()
    backend.configure(
        device_name="Dev1",
        ims_cell_ao_channel="ao0",
        ionization_ao_channel="ao1",
        power_do_channel="port0/line0",
    )
    assert backend.enabled is False

    backend.set_ims_cell_kv(10.0, max_kv=15.0)
    backend.set_ionization_output_kv(13.0, max_kv=20.0)  # 10 kV cell + 3 kV bias
    assert backend.ims_cell_kv == pytest.approx(10.0)
    assert backend.ionization_kv == pytest.approx(13.0)

    backend.set_enabled(True)
    assert backend.enabled is True
    backend.set_enabled(False)
    assert backend.enabled is False


def test_system_parameters_validate():
    params = SystemParameters(ims_cell_max_kv=15.0, ionization_max_kv=5.0)
    params.validate()  # should not raise

    with pytest.raises(ValueError):
        SystemParameters(ims_cell_max_kv=0.0).validate()
    with pytest.raises(ValueError):
        SystemParameters(ionization_max_kv=-1.0).validate()
    with pytest.raises(ValueError):
        SystemParameters(ims_cell_ao_full_scale_v=0.0).validate()
    with pytest.raises(ValueError):
        SystemParameters(ionization_ao_full_scale_v=-1.0).validate()
