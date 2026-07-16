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


def test_guangdong_profile_only_emits_supported_phase_options():
    config = load_pipeline_config("config/pipeline.guangdong.json")
    phases = merge_phase_definitions(PHASES, config)

    for phase_id, phase in phases.items():
        if phase_id in {3, 6}:
            command = ["python", phase["script"]]
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
