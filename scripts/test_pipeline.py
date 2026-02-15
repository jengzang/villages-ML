"""Quick test script to verify pipeline works on sample data."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PipelineConfig
from src.utils.logging_config import setup_logging
from src.pipelines.frequency_pipeline import CharacterFrequencyPipeline


def main():
    """Run pipeline on first 1000 villages as a test."""
    print("=" * 80)
    print("Testing Character Frequency Pipeline on Sample Data")
    print("=" * 80)

    # Create configuration
    config = PipelineConfig.create_default(
        db_path='data/villages.db',
        output_dir='results',
        run_id='test_sample'
    )

    # Limit to small chunk for testing
    config.frequency.chunk_size = 1000

    # Setup logging
    setup_logging(level='INFO')

    print(f"\nConfiguration:")
    print(f"  Database: {config.db_path}")
    print(f"  Output: {config.output_dir}/{config.run_id}")
    print(f"  Chunk size: {config.frequency.chunk_size}")
    print()

    # Run pipeline
    try:
        pipeline = CharacterFrequencyPipeline(config)
        pipeline.run()
        print("\n" + "=" * 80)
        print("SUCCESS: Pipeline completed!")
        print("=" * 80)
        return 0

    except Exception as e:
        print(f"\nERROR: Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
