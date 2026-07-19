import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from run_all_phases import PHASES, build_phase_command
from src.pipeline_config import load_pipeline_config, merge_phase_definitions


@pytest.mark.parametrize(
    "script",
    [
        "scripts/preprocessing/create_preprocessed_table.py",
        "scripts/core/create_missing_tables.py",
        "scripts/core/phase14_semantic_composition.py",
        "scripts/core/phase15_region_similarity.py",
        "scripts/core/phase17_semantic_subcategory.py",
        "scripts/core/fill_aggregates_tables.py",
        "scripts/core/phase16_semantic_centrality.py",
        "scripts/core/run_morphology.py",
    ],
)
def test_phase_entrypoint_exposes_help(script):
    result = subprocess.run(
        [str(PROJECT_ROOT / ".venv/bin/python"), script, "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "--help" in result.stdout


def _extract_options(args):
    return {arg for arg in args if arg.startswith("--")}


@pytest.mark.parametrize(
    "config_path",
    [
        "config/pipeline.guangdong.json",
        "config/pipeline.national.json",
    ],
)
def test_profile_only_emits_supported_phase_options(config_path):
    config = load_pipeline_config(config_path)
    phases = merge_phase_definitions(PHASES, config)

    for phase_id, phase in phases.items():
        if phase_id in {3, 6}:
            command = [sys.executable, phase["script"]]
            if phase_id == 3:
                command.extend(["--char-run-id", "char_test", "--output-run-id", "semantic_test"])
            else:
                command.extend([
                    "--semantic-run-id",
                    "semantic_test",
                    "--morphology-run-id",
                    "morph_test",
                    "--output-run-id",
                    "cluster_test",
                ])
            command.extend(phase["args"])
        else:
            command, _, _ = build_phase_command(
                phase_id,
                phases=phases,
                run_id_prefix="test",
                db_path="data/villages.db",
                now_str="20260716_120000",
            )

        help_result = subprocess.run(
            [str(PROJECT_ROOT / ".venv/bin/python"), phase["script"], "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert help_result.returncode == 0, help_result.stderr
        help_text = help_result.stdout

        unsupported_options = [
            option for option in _extract_options(command[2:])
            if option != "--help" and option not in help_text
        ]
        assert unsupported_options == [], f"Phase {phase_id} unsupported options: {unsupported_options}"


def test_national_profile_emits_phase6_and_phase14_deep_config_options():
    config = load_pipeline_config("config/pipeline.national.json")
    phases = merge_phase_definitions(PHASES, config)

    phase6_cmd = [
        sys.executable,
        phases[6]["script"],
        "--semantic-run-id",
        "semantic_test",
        "--morphology-run-id",
        "morph_test",
        "--output-run-id",
        "cluster_test",
    ]
    phase6_cmd.extend(phases[6]["args"])

    assert "--semantic-lexicon-path" in phase6_cmd
    assert phase6_cmd[phase6_cmd.index("--semantic-lexicon-path") + 1] == "data/semantic_lexicon_national_v1.json"
    assert "--use-semantic" in phase6_cmd
    assert "--use-morphology" in phase6_cmd
    assert "--use-diversity" in phase6_cmd

    phase14_cmd, _, _ = build_phase_command(
        14,
        phases=phases,
        run_id_prefix="national",
        db_path="data/villages_national.db",
        now_str="20260716_120000",
    )

    assert "--basic-lexicon-path" in phase14_cmd
    assert phase14_cmd[phase14_cmd.index("--basic-lexicon-path") + 1] == "data/semantic_lexicon_national_v1.json"
    assert "--detailed-lexicon-path" in phase14_cmd
    assert phase14_cmd[phase14_cmd.index("--detailed-lexicon-path") + 1] == "data/semantic_lexicon_national_v4.json"
    assert "--conflict-threshold" in phase14_cmd
    assert phase14_cmd[phase14_cmd.index("--conflict-threshold") + 1] == "20"
    assert "--structure-progress-interval" in phase14_cmd
    assert phase14_cmd[phase14_cmd.index("--structure-progress-interval") + 1] == "50000"


def test_national_profile_emits_phase4_schema_and_china_bounds():
    config = load_pipeline_config("config/pipeline.national.json")
    phases = merge_phase_definitions(PHASES, config)
    phase4_cmd, _, _ = build_phase_command(
        4,
        phases=phases,
        run_id_prefix="national",
        db_path="data/villages_national.db",
        now_str="20260716_120000",
    )

    assert "--schema" in phase4_cmd
    assert phase4_cmd[phase4_cmd.index("--schema") + 1] == "national"
    assert "--coordinate-bounds" in phase4_cmd
    assert phase4_cmd[phase4_cmd.index("--coordinate-bounds") + 1] == "china"
