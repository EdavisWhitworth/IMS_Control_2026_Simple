from ims_control.acquisition.experiment import ExperimentConfig, SystemParameters
from ims_control.io.settings_io import load_defaults, save_defaults


def test_save_and_load_defaults_round_trip(tmp_path):
    path = tmp_path / "defaults.json"
    config = ExperimentConfig(pulse_width_ms=0.5, exp_length_ms=40.0, num_points=2000, ion_mz=500.0)
    system_parameters = SystemParameters(device_name="Dev2", ims_cell_max_kv=20.0)

    save_defaults(
        config,
        system_parameters,
        use_simulator=False,
        use_simulated_power=True,
        ims_cell_kv=12.0,
        ionization_kv=2.5,
        path=path,
    )
    loaded = load_defaults(path=path)

    assert loaded is not None
    assert loaded["experiment"].pulse_width_ms == 0.5
    assert loaded["experiment"].exp_length_ms == 40.0
    assert loaded["experiment"].ion_mz == 500.0
    assert loaded["system_parameters"].device_name == "Dev2"
    assert loaded["system_parameters"].ims_cell_max_kv == 20.0
    assert loaded["use_simulator"] is False
    assert loaded["use_simulated_power"] is True
    assert loaded["ims_cell_kv"] == 12.0
    assert loaded["ionization_kv"] == 2.5


def test_load_defaults_missing_file_returns_none(tmp_path):
    path = tmp_path / "does_not_exist.json"
    assert load_defaults(path=path) is None


def test_load_defaults_ignores_unknown_saved_fields(tmp_path):
    """Older saved defaults referencing renamed/removed fields must not crash on load."""
    import json

    path = tmp_path / "defaults.json"
    payload = {
        "experiment": {"pulse_width_ms": 0.3},
        "system_parameters": {
            "device_name": "Dev3",
            "power_enable_do_channel": "port0/line0",  # removed field from an older schema
            "power_led_do_channel": "port0/line1",  # removed field from an older schema
        },
        "use_simulator": True,
        "ims_cell_kv": 1.0,
        "ionization_kv": 0.5,
    }
    path.write_text(json.dumps(payload))

    loaded = load_defaults(path=path)

    assert loaded is not None
    assert loaded["experiment"].pulse_width_ms == 0.3
    assert loaded["system_parameters"].device_name == "Dev3"
    assert loaded["use_simulated_power"] is True  # default applied for the missing key
