"""Main pipeline orchestration for morphology pattern analysis."""

import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List

from ..utils.config import PipelineConfig
from ..data.db_loader import (
    get_db_connection, validate_database_schema,
    load_villages, get_total_village_count
)
from ..preprocessing.morphology_extractor import extract_morphology_features
from ..analysis.morphology_frequency import (
    compute_pattern_frequency_global,
    compute_pattern_frequency_by_region,
    calculate_pattern_lift
)
from ..analysis.regional_analysis import compute_regional_tendency

logger = logging.getLogger(__name__)


class MorphologyPipeline:
    """Pipeline for morphology pattern analysis (suffix/prefix)."""

    def __init__(
        self,
        config: PipelineConfig,
        suffix_lengths: List[int] = None,
        prefix_lengths: List[int] = None
    ):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
            suffix_lengths: List of suffix n-gram lengths (default: [1, 2, 3])
            prefix_lengths: List of prefix n-gram lengths (default: [2, 3])
        """
        self.config = config
        self.suffix_lengths = suffix_lengths or [1, 2, 3]
        self.prefix_lengths = prefix_lengths or [2, 3]
        self.output_dir = Path(config.output_dir) / config.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized morphology pipeline with run_id: {config.run_id}")
        logger.info(f"Suffix lengths: {self.suffix_lengths}")
        logger.info(f"Prefix lengths: {self.prefix_lengths}")
        logger.info(f"Output directory: {self.output_dir}")

    def run(self):
        """Execute the full pipeline."""
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting Morphology Pattern Analysis Pipeline")
        logger.info("=" * 80)

        try:
            # Save configuration
            self.config.save(str(self.output_dir / "config.json"))

            # Step 1: Load and extract morphology features
            logger.info("\n[Step 1/5] Loading and extracting morphology features...")
            villages_df = self._load_and_extract_morphology()

            # Step 2: Analyze all pattern types
            logger.info("\n[Step 2/5] Analyzing all pattern types...")
            self._analyze_all_patterns(villages_df)

            # Step 3: Generate summary report
            logger.info("\n[Step 3/5] Generating summary report...")
            self._generate_summary_report(villages_df)

            # Step 4: Persist results to database
            logger.info("\n[Step 4/5] Persisting results to database...")
            from ..data.db_writer import persist_morphology_results_to_db
            persist_morphology_results_to_db(
                db_path=self.config.db_path,
                results_dir=self.output_dir,
                suffix_lengths=self.suffix_lengths,
                prefix_lengths=self.prefix_lengths,
                region_levels=self.config.frequency.region_levels,
                batch_size=10000
            )

            # Done
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("\n" + "=" * 80)
            logger.info(f"Pipeline completed successfully in {elapsed:.1f}s")
            logger.info(f"Results saved to: {self.output_dir}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise

    def _load_and_extract_morphology(self) -> pd.DataFrame:
        """Load villages from database and extract morphology features."""
        # Connect to database
        conn = get_db_connection(self.config.db_path)

        # Validate schema
        if not validate_database_schema(conn):
            raise ValueError("Database schema validation failed")

        # Get total count
        total_count = get_total_village_count(conn)
        logger.info(f"Total villages in database: {total_count:,}")

        # Load and process in chunks
        all_chunks = []
        chunk_num = 0

        for chunk in load_villages(conn, chunk_size=self.config.frequency.chunk_size):
            chunk_num += 1
            logger.info(f"Processing chunk {chunk_num} ({len(chunk)} villages)...")

            # Extract morphology features
            processed = extract_morphology_features(
                chunk,
                suffix_lengths=self.suffix_lengths,
                prefix_lengths=self.prefix_lengths,
                bracket_mode=self.config.cleaning.bracket_mode,
                keep_rare_chars=self.config.cleaning.keep_rare_chars,
                min_name_length=self.config.cleaning.min_name_length
            )

            all_chunks.append(processed)

        conn.close()

        # Combine all chunks
        villages_df = pd.concat(all_chunks, ignore_index=True)

        logger.info(f"Loaded {len(villages_df):,} villages total")

        # Save morphology features
        output_path = self.output_dir / "village_morphology.csv"
        villages_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved morphology features to {output_path}")

        return villages_df

    def _analyze_all_patterns(self, villages_df: pd.DataFrame):
        """Analyze all pattern types (suffix_1, suffix_2, etc.)."""
        # Build list of pattern columns
        pattern_cols = []
        for n in self.suffix_lengths:
            pattern_cols.append(f'suffix_{n}')
        for n in self.prefix_lengths:
            pattern_cols.append(f'prefix_{n}')

        logger.info(f"Analyzing {len(pattern_cols)} pattern types: {pattern_cols}")

        for pattern_col in pattern_cols:
            logger.info(f"\n--- Analyzing {pattern_col} ---")
            self._analyze_single_pattern(villages_df, pattern_col)

    def _analyze_single_pattern(self, villages_df: pd.DataFrame, pattern_col: str):
        """Analyze a single pattern type."""
        # Compute global frequency
        logger.info(f"Computing global frequencies for {pattern_col}...")
        global_freq = compute_pattern_frequency_global(villages_df, pattern_col)

        # Save
        output_path = self.output_dir / f"{pattern_col}_frequency_global.csv"
        global_freq.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved to {output_path}")

        # Compute regional frequencies and tendencies
        for level in self.config.frequency.region_levels:
            logger.info(f"Computing {level}-level frequencies for {pattern_col}...")

            # Regional frequency
            regional_freq = compute_pattern_frequency_by_region(
                villages_df, level, pattern_col
            )

            # Save regional frequency
            output_path = self.output_dir / f"{pattern_col}_frequency_{level}.csv"
            regional_freq.to_csv(output_path, index=False, encoding='utf-8-sig')

            # Add global stats and compute lift
            freq_with_lift = calculate_pattern_lift(regional_freq, global_freq)

            # Compute tendency metrics
            tendency_df = compute_regional_tendency(
                freq_with_lift,
                smoothing_alpha=self.config.tendency.smoothing_alpha,
                min_global_support=self.config.tendency.min_global_support,
                min_regional_support=self.config.tendency.min_regional_support,
                compute_z=self.config.tendency.compute_z_score
            )

            # Save tendency
            output_path = self.output_dir / f"{pattern_col}_tendency_{level}.csv"
            tendency_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {level} tendencies to {output_path}")

    def _generate_summary_report(self, villages_df: pd.DataFrame):
        """Generate summary statistics report."""
        output_path = self.output_dir / "morphology_summary.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Morphology Pattern Analysis Summary\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Run ID: {self.config.run_id}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Village statistics
            total = len(villages_df)
            valid = villages_df['is_valid'].sum()
            f.write(f"Total villages: {total:,}\n")
            f.write(f"Valid villages: {valid:,}\n\n")

            # Pattern type statistics
            f.write("Pattern Types Analyzed:\n")
            f.write(f"  Suffix lengths: {self.suffix_lengths}\n")
            f.write(f"  Prefix lengths: {self.prefix_lengths}\n\n")

            # Sample patterns for each type
            valid_df = villages_df[villages_df['is_valid']]

            for n in self.suffix_lengths:
                col = f'suffix_{n}'
                if col in valid_df.columns:
                    unique_count = valid_df[col].nunique()
                    top_patterns = valid_df[col].value_counts().head(10)
                    f.write(f"\n{col} - {unique_count:,} unique patterns:\n")
                    f.write("-" * 60 + "\n")
                    for pattern, count in top_patterns.items():
                        freq = count / len(valid_df)
                        f.write(f"  {pattern:<10} {count:>8,} ({freq:>6.2%})\n")

            for n in self.prefix_lengths:
                col = f'prefix_{n}'
                if col in valid_df.columns:
                    unique_count = valid_df[col].nunique()
                    top_patterns = valid_df[col].value_counts().head(10)
                    f.write(f"\n{col} - {unique_count:,} unique patterns:\n")
                    f.write("-" * 60 + "\n")
                    for pattern, count in top_patterns.items():
                        freq = count / len(valid_df)
                        f.write(f"  {pattern:<10} {count:>8,} ({freq:>6.2%})\n")

        logger.info(f"Saved summary report to {output_path}")
