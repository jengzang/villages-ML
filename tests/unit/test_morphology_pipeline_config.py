import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.pipelines.morphology_pipeline import MorphologyPipeline
from src.utils.config import PipelineConfig


def test_morphology_pipeline_accepts_configured_lengths_and_persist_batch_size(tmp_path):
    config = PipelineConfig.create_default(
        db_path=str(tmp_path / "villages.db"),
        output_dir=str(tmp_path / "results"),
        run_id="morph_test",
    )

    pipeline = MorphologyPipeline(
        config,
        suffix_lengths=[2],
        prefix_lengths=[],
        persist_batch_size=250,
    )

    assert pipeline.suffix_lengths == [2]
    assert pipeline.prefix_lengths == []
    assert pipeline.persist_batch_size == 250
