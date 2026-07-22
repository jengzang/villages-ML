import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from run_all_phases import PHASES, build_phase_command
from src.pipeline_config import (
    DEFAULT_PIPELINE_CONFIG_PATH,
    load_pipeline_config,
    merge_phase_definitions,
    resolve_pipeline_config_path,
)


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


def test_default_pipeline_config_is_guangdong_profile_with_phase12_thresholds():
    config_path = resolve_pipeline_config_path(None)
    config = load_pipeline_config(config_path)
    phases = merge_phase_definitions(PHASES, config)
    phase12_args = phases[12]["args"]

    assert config_path == DEFAULT_PIPELINE_CONFIG_PATH
    assert "--min-regional-count-by-n" in phase12_args
    assert phase12_args[phase12_args.index("--min-regional-count-by-n") + 1] == "2:3,3:2"
    assert "--min-global-count-by-n" in phase12_args
    assert phase12_args[phase12_args.index("--min-global-count-by-n") + 1] == "2:10,3:5"


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
        sys.executable,
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


def test_national_profile_defines_args_for_every_pipeline_phase():
    config = load_pipeline_config("config/pipeline.national.json")

    configured_phase_ids = {int(phase_id) for phase_id in config["phases"]}

    assert config["dataset"]["key"] == "national"
    assert config["dataset"]["schema"] == "national"
    assert configured_phase_ids == set(PHASES)
    for phase_id in PHASES:
        assert "args" in config["phases"][str(phase_id)]
        assert isinstance(config["phases"][str(phase_id)]["args"], dict)


def test_national_profile_is_conservative_for_large_dataset():
    config = load_pipeline_config("config/pipeline.national.json")

    assert config["dataset"] == {
        "key": "national",
        "db_path": "data/villages_national.db",
        "schema": "national",
    }
    assert config["run"]["run_id_prefix"] == "national"

    phase1 = config["phases"]["1"]["args"]
    assert phase1["precompute_similarities"] is True
    assert phase1["top_k"] == 20

    phase3 = config["phases"]["3"]["args"]
    assert phase3["lexicon_path"] == "data/semantic_lexicon_national_v1.json"

    phase5 = config["phases"]["5"]["args"]
    assert phase5["lexicon_path"] == "data/semantic_lexicon_national_v1.json"

    phase6 = config["phases"]["6"]["args"]
    assert phase6["semantic_lexicon_path"] == "data/semantic_lexicon_national_v1.json"
    assert phase6["use_semantic"] is True
    assert phase6["use_morphology"] is True
    assert phase6["use_diversity"] is True

    phase12 = config["phases"]["12"]["args"]
    assert phase12["n_values"] == [2]
    assert phase12["regional_levels"] == ["city", "county"]
    assert phase12["positions"] == ["all", "suffix"]
    assert phase12["min_global_count_by_n"] == "2:200"

    phase14 = config["phases"]["14"]["args"]
    assert phase14["lexicon_path"] == "data/semantic_lexicon_national_v4.json"
    assert phase14["basic_lexicon_path"] == "data/semantic_lexicon_national_v1.json"
    assert phase14["detailed_lexicon_path"] == "data/semantic_lexicon_national_v4.json"
    assert phase14["conflict_threshold"] == 20
    assert phase14["structure_progress_interval"] == 50000
    assert phase14["region_levels"] == ["city", "county"]

    phase17 = config["phases"]["17"]["args"]
    assert phase17["lexicon_path"] == "data/semantic_lexicon_national_v4.json"


def test_national_profile_lexicon_files_exist():
    config = load_pipeline_config("config/pipeline.national.json")
    lexicon_paths = set()

    for phase_config in config["phases"].values():
        args = phase_config["args"]
        for key in ("lexicon_path", "semantic_lexicon_path", "basic_lexicon_path", "detailed_lexicon_path"):
            if key in args:
                lexicon_paths.add(args[key])

    national_lexicons = sorted(path for path in lexicon_paths if "national" in path)
    assert national_lexicons
    for lexicon_path in national_lexicons:
        assert Path(lexicon_path).exists(), f"Missing configured national lexicon: {lexicon_path}"


def test_national_profile_emits_schema_to_schema_sensitive_phases():
    config = load_pipeline_config("config/pipeline.national.json")
    phases = merge_phase_definitions(PHASES, config)

    schema_phase_ids = {0, 1, 2, 3, 4, 5, 12, 13, 14, 17, 18}
    for phase_id in schema_phase_ids:
        args = phases[phase_id]["args"]
        assert "--schema" in args, f"Phase {phase_id} should receive schema from national profile"
        assert args[args.index("--schema") + 1] == "national"
