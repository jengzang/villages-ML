"""Pipeline profile configuration helpers.

Profiles keep dataset-specific paths and phase arguments out of
``run_all_phases.py`` while preserving the current defaults when no profile is
provided.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DEFAULT_PIPELINE_CONFIG_PATH = "config/pipeline.guangdong.json"

_ARG_NAME_OVERRIDES = {
    "db_path": "db-path",
    "run_id": "run-id",
    "run_id_prefix": "run-id-prefix",
}


def resolve_pipeline_config_path(config_path: str | None) -> str:
    """Return the explicit profile path or the Guangdong default profile."""
    return config_path or DEFAULT_PIPELINE_CONFIG_PATH


def load_pipeline_config(config_path: str | None) -> dict[str, Any]:
    """Load a pipeline profile from JSON.

    ``None`` returns an empty config so tests and callers can still merge
    unconditionally. Pipeline entrypoints should call
    ``resolve_pipeline_config_path`` first when they want the default profile.
    """
    if not config_path:
        return {}

    path = Path(config_path)
    if path.suffix.lower() != ".json":
        raise ValueError("Only JSON pipeline config files are supported for now")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Pipeline config root must be a JSON object")

    return data


def phase_args_from_mapping(args_config: dict[str, Any]) -> list[str]:
    """Convert a profile args mapping into CLI arguments."""
    args: list[str] = []
    for key, value in args_config.items():
        option = _ARG_NAME_OVERRIDES.get(key, key.replace("_", "-"))
        flag = f"--{option}"

        if isinstance(value, bool):
            if value:
                args.append(flag)
            continue

        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            value = ",".join(str(item) for item in value)

        args.extend([flag, str(value)])

    return args


def merge_phase_definitions(
    default_phases: dict[int, dict[str, Any]],
    config: dict[str, Any] | None,
) -> dict[int, dict[str, Any]]:
    """Return phase definitions with profile overrides applied."""
    merged = copy.deepcopy(default_phases)
    config = config or {}
    phase_configs = config.get("phases", {})

    for phase_id_text, phase_config in phase_configs.items():
        phase_id = int(phase_id_text)
        if phase_id not in merged:
            raise ValueError(f"Pipeline config references unknown phase: {phase_id}")

        phase_config = phase_config or {}
        for key, value in phase_config.items():
            if key == "args":
                if isinstance(value, dict):
                    merged[phase_id]["args"] = phase_args_from_mapping(value)
                elif isinstance(value, list):
                    merged[phase_id]["args"] = [str(item) for item in value]
                else:
                    raise ValueError(f"Phase {phase_id} args must be an object or list")
            else:
                merged[phase_id][key] = value

    return merged
