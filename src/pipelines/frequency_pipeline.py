"""Main pipeline orchestration for character frequency analysis."""

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
from ..preprocessing.char_extractor import process_village_batch
from ..analysis.char_frequency import (
    compute_char_frequency_global,
    compute_char_frequency_by_region,
    calculate_lift
)
from ..analysis.regional_analysis import compute_regional_tendency
from ..analysis.diagnostic_reports import create_comprehensive_report

logger = logging.getLogger(__name__)


class CharacterFrequencyPipeline:
    """Pipeline for character frequency analysis."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.output_dir = Path(config.output_dir) / config.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized pipeline with run_id: {config.run_id}")
        logger.info(f"Output directory: {self.output_dir}")

    def run(self):
        """Execute the full pipeline."""
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting Character Frequency Analysis Pipeline")
        logger.info("=" * 80)

        try:
            # Save configuration
            self.config.save(str(self.output_dir / "config.json"))

            # Step 1: Load and preprocess data
            logger.info("\n[Step 1/6] Loading and preprocessing villages...")
            villages_df = self._load_and_preprocess()

            # Step 2: Compute global frequencies
            logger.info("\n[Step 2/6] Computing global character frequencies...")
            global_freq = self._compute_global_frequency(villages_df)

            # Step 3: Compute regional frequencies
            logger.info("\n[Step 3/6] Computing regional character frequencies...")
            regional_freqs = self._compute_regional_frequencies(villages_df)

            # Step 4: Compute regional tendencies
            logger.info("\n[Step 4/6] Computing regional tendency metrics...")
            self._compute_regional_tendencies(regional_freqs, global_freq)

            # Step 5: Generate summary report
            logger.info("\n[Step 5/6] Generating summary report...")
            self._generate_summary_report(villages_df, global_freq)

            # Step 6: Persist results to database
            logger.info("\n[Step 6/6] Persisting results to database...")
            from ..data.db_writer import persist_results_to_db
            persist_results_to_db(
                db_path=self.config.db_path,
                run_id=self.config.run_id,
                results_dir=self.output_dir,
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

    def _load_and_preprocess(self) -> pd.DataFrame:
        """Load villages from database and preprocess."""
        # Connect to database
        conn = get_db_connection(self.config.db_path)

        # Validate schema
        if not validate_database_schema(conn):
            raise ValueError("Database schema validation failed")

        # Get total count
        total_count = get_total_village_count(conn)

        # Load and process in chunks
        all_chunks = []
        chunk_num = 0

        for chunk in load_villages(conn, chunk_size=self.config.frequency.chunk_size):
            chunk_num += 1
            logger.info(f"Processing chunk {chunk_num} ({len(chunk)} villages)...")

            # Process chunk
            processed = process_village_batch(
                chunk,
                bracket_mode=self.config.cleaning.bracket_mode,
                keep_rare_chars=self.config.cleaning.keep_rare_chars,
                min_name_length=self.config.cleaning.min_name_length
            )

            all_chunks.append(processed)

        conn.close()

        # Combine all chunks
        villages_df = pd.concat(all_chunks, ignore_index=True)

        logger.info(f"Loaded {len(villages_df):,} villages total")

        # Save cleaned villages
        self._save_cleaned_villages(villages_df)

        # Generate cleaning report
        self._generate_cleaning_report(villages_df)

        return villages_df

    def _compute_global_frequency(self, villages_df: pd.DataFrame) -> pd.DataFrame:
        """Compute global character frequencies."""
        global_freq = compute_char_frequency_global(villages_df)

        # Save
        output_path = self.output_dir / "char_frequency_global.csv"
        global_freq.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved global frequencies to {output_path}")

        return global_freq

    def _compute_regional_frequencies(
        self,
        villages_df: pd.DataFrame
    ) -> dict:
        """Compute regional frequencies for all configured levels."""
        regional_freqs = {}

        for level in self.config.frequency.region_levels:
            logger.info(f"Computing {level}-level frequencies...")

            freq_df = compute_char_frequency_by_region(villages_df, level)
            regional_freqs[level] = freq_df

            # Save
            output_path = self.output_dir / f"char_frequency_{level}.csv"
            freq_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {level} frequencies to {output_path}")

        return regional_freqs

    def _compute_regional_tendencies(
        self,
        regional_freqs: dict,
        global_freq: pd.DataFrame
    ):
        """Compute regional tendency metrics for all levels."""
        for level, freq_df in regional_freqs.items():
            logger.info(f"Computing {level}-level tendencies...")

            # Add global stats and compute lift
            freq_with_lift = calculate_lift(freq_df, global_freq)

            # Compute tendency metrics
            tendency_df = compute_regional_tendency(
                freq_with_lift,
                smoothing_alpha=self.config.tendency.smoothing_alpha,
                min_global_support=self.config.tendency.min_global_support,
                min_regional_support=self.config.tendency.min_regional_support,
                compute_z=self.config.tendency.compute_z_score
            )

            # Add run_id
            tendency_df.insert(0, 'run_id', self.config.run_id)

            # Save
            output_path = self.output_dir / f"regional_tendency_{level}.csv"
            tendency_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {level} tendencies to {output_path}")

            # Generate diagnostic report
            report_path = self.output_dir / f"diagnostic_report_{level}.txt"
            create_comprehensive_report(tendency_df, report_path, level)


    def _save_cleaned_villages(self, villages_df: pd.DataFrame):
        """Save cleaned villages to CSV."""
        output_path = self.output_dir / "village_cleaned.csv"
        villages_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved cleaned villages to {output_path}")

    def _generate_cleaning_report(self, villages_df: pd.DataFrame):
        """Generate preprocessing diagnostics report."""
        output_path = self.output_dir / "cleaning_report.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Village Name Cleaning Report\n")
            f.write("=" * 80 + "\n\n")

            total = len(villages_df)
            valid = villages_df['is_valid'].sum()
            invalid = total - valid

            f.write(f"Total villages: {total:,}\n")
            f.write(f"Valid villages: {valid:,} ({valid/total*100:.2f}%)\n")
            f.write(f"Invalid villages: {invalid:,} ({invalid/total*100:.2f}%)\n\n")

            # Bracket statistics
            had_brackets = villages_df['had_brackets'].sum()
            f.write(f"Villages with brackets: {had_brackets:,} ({had_brackets/total*100:.2f}%)\n")

            # Noise statistics
            had_noise = villages_df['had_noise'].sum()
            f.write(f"Villages with noise: {had_noise:,} ({had_noise/total*100:.2f}%)\n\n")

            # Invalid reasons
            if invalid > 0:
                f.write("Invalid reasons:\n")
                reason_counts = villages_df[~villages_df['is_valid']]['invalid_reason'].value_counts()
                for reason, count in reason_counts.items():
                    f.write(f"  - {reason}: {count:,}\n")
                f.write("\n")

            # Name length statistics
            valid_df = villages_df[villages_df['is_valid']]
            if len(valid_df) > 0:
                f.write("Name length statistics (valid villages):\n")
                f.write(f"  - Mean: {valid_df['name_len'].mean():.2f}\n")
                f.write(f"  - Median: {valid_df['name_len'].median():.0f}\n")
                f.write(f"  - Min: {valid_df['name_len'].min()}\n")
                f.write(f"  - Max: {valid_df['name_len'].max()}\n\n")

                # Length distribution
                f.write("Length distribution:\n")
                len_dist = valid_df['name_len'].value_counts().sort_index()
                for length, count in len_dist.head(10).items():
                    f.write(f"  - {length} chars: {count:,} ({count/len(valid_df)*100:.2f}%)\n")

        logger.info(f"Saved cleaning report to {output_path}")

    def _generate_summary_report(
        self,
        villages_df: pd.DataFrame,
        global_freq: pd.DataFrame
    ):
        """Generate summary statistics report."""
        output_path = self.output_dir / "frequency_summary.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Character Frequency Analysis Summary\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Run ID: {self.config.run_id}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Village statistics
            total = len(villages_df)
            valid = villages_df['is_valid'].sum()
            f.write(f"Total villages: {total:,}\n")
            f.write(f"Valid villages: {valid:,}\n\n")

            # Character statistics
            f.write(f"Unique characters: {len(global_freq):,}\n\n")

            # Top characters
            f.write("Top 20 most common characters:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Rank':<6} {'Char':<6} {'Villages':<12} {'Frequency':<12}\n")
            f.write("-" * 80 + "\n")

            for _, row in global_freq.head(20).iterrows():
                f.write(f"{row['rank']:<6} {row['char']:<6} {row['village_count']:<12,} {row['frequency']:<12.4f}\n")

            f.write("\n")

            # Regional statistics
            for level in self.config.frequency.region_levels:
                level_map = {'city': '市级', 'county': '区县级', 'township': '乡镇级'}
                col = level_map[level]
                n_regions = villages_df[col].nunique()
                f.write(f"Number of {level} regions: {n_regions:,}\n")

        logger.info(f"Saved summary report to {output_path}")

