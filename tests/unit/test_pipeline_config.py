import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from run_all_phases import PHASES, build_phase_command
from src.pipeline_config import load_pipeline_config, merge_phase_definitions


def test_load_pipeline_config_reads_json_and_exposes_defaults(tmp_path):
    config_path = tmp_path / "pipeline.test.json"
    config_path.write_text(
        json.dumps(
            {
                "dataset": {"db_path": "data/national.db"},
                "run": {"run_id_prefix": "national"},
                "phases": {
                    "12": {
                        "args": {
                            "db_path": "data/national.db",
                            "n_values": [2, 3],
                            "regional_levels": ["county"],
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_pipeline_config(str(config_path))

    assert config["dataset"]["db_path"] == "data/national.db"
    assert config["run"]["run_id_prefix"] == "national"
    assert config["phases"]["12"]["args"]["regional_levels"] == ["county"]


def test_merge_phase_definitions_overrides_phase_args_without_mutating_defaults():
    config = {
        "phases": {
            "12": {
                "args": {
                    "db_path": "data/national.db",
                    "n_values": [2, 3],
                    "regional_levels": ["county"],
                    "positions": ["all", "suffix"],
                }
            }
        }
    }

    merged = merge_phase_definitions(PHASES, config)

    assert merged[12]["args"] == [
        "--db-path",
        "data/national.db",
        "--n-values",
        "2,3",
        "--regional-levels",
        "county",
        "--positions",
        "all,suffix",
    ]
    assert PHASES[12]["args"] == ["--db-path", "data/villages.db"]


def test_build_phase_command_uses_merged_phase_args_and_db_path():
    phases = merge_phase_definitions(
        PHASES,
        {
            "phases": {
                "12": {
                    "args": {
                        "db_path": "data/national.db",
                        "n_values": [2],
                    }
                }
            }
        },
    )

    cmd, run_id, output_run_id = build_phase_command(
        12,
        phases=phases,
        run_id_prefix="national",
        db_path="data/national.db",
        now_str="20260716_120000",
    )

    assert run_id == "national_12_20260716_120000"
    assert output_run_id is None
    assert cmd == [
        "python",
        "scripts/core/phase12_ngram_analysis.py",
        "--run-id",
        "national_12_20260716_120000",
        "--db-path",
        "data/national.db",
        "--n-values",
        "2",
    ]


def test_load_pipeline_config_rejects_unsupported_extension(tmp_path):
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text("dataset:\n  db_path: data/test.db\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Only JSON"):
        load_pipeline_config(str(config_path))


def test_guangdong_profile_defines_args_for_every_pipeline_phase():
    config = load_pipeline_config("config/pipeline.guangdong.json")

    configured_phase_ids = {int(phase_id) for phase_id in config["phases"]}

    assert configured_phase_ids == set(PHASES)
    for phase_id in PHASES:
        assert "args" in config["phases"][str(phase_id)]
        assert isinstance(config["phases"][str(phase_id)]["args"], dict)
