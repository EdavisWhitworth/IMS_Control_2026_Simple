"""Persistence of operator defaults (experiment + system parameters) between sessions."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

from ims_control.acquisition.experiment import ExperimentConfig, SystemParameters

DEFAULT_SETTINGS_PATH = Path.home() / ".ims_control" / "defaults.json"


def save_defaults(
    experiment_config: ExperimentConfig,
    system_parameters: SystemParameters,
    use_simulator: bool,
    use_simulated_power: bool,
    ims_cell_kv: float,
    ionization_kv: float,
    path: Path = DEFAULT_SETTINGS_PATH,
) -> None:
    experiment_dict = asdict(experiment_config)
    experiment_dict.pop("created_at", None)  # per-run timestamp, not a saved preference
    payload = {
        "experiment": experiment_dict,
        "system_parameters": asdict(system_parameters),
        "use_simulator": use_simulator,
        "use_simulated_power": use_simulated_power,
        "ims_cell_kv": ims_cell_kv,
        "ionization_kv": ionization_kv,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _filter_known_fields(data: dict, cls) -> dict:
    """Drop keys that no longer exist on `cls`, so older saved defaults don't crash on load."""
    known = {f.name for f in fields(cls)}
    return {key: value for key, value in data.items() if key in known}


def load_defaults(path: Path = DEFAULT_SETTINGS_PATH) -> dict | None:
    """Returns None if no saved defaults exist yet."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    payload.setdefault("use_simulated_power", True)
    payload["experiment"] = ExperimentConfig(**_filter_known_fields(payload["experiment"], ExperimentConfig))
    payload["system_parameters"] = SystemParameters(
        **_filter_known_fields(payload["system_parameters"], SystemParameters)
    )
    return payload
