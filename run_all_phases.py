#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Villages-ML Analysis Pipeline Runner

This script orchestrates all analysis phases for the Guangdong villages dataset.
You can run specific phases or all phases at once.

Usage:
    # Run all phases
    python run_all_phases.py --all

    # Run specific phases
    python run_all_phases.py --phases 0,1,2,3

    # Run with custom run ID prefix
    python run_all_phases.py --all --run-id-prefix final

    # Dry run (show what would be executed)
    python run_all_phases.py --all --dry-run

Available Phases:
    0  - Data Preprocessing (prefix cleaning)
    1  - Character Embeddings (Word2Vec)
    2  - Frequency Analysis
    3  - Spatial Analysis
    4  - Clustering Analysis (KMeans, DBSCAN, GMM)
    5  - N-gram Analysis
    6  - Semantic Composition Analysis
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Phase definitions
PHASES = {
    0: {
        "name": "Data Preprocessing",
        "script": "scripts/create_preprocessed_table.py",
        "args": [],
        "description": "Clean village names and remove administrative prefixes"
    },
    1: {
        "name": "Character Embeddings",
        "script": "scripts/train_char_embeddings.py",
        "args": [
            "--db-path", "data/villages.db",
            "--vector-size", "100",
            "--window", "3",
            "--min-count", "2",
            "--epochs", "15",
            "--model-type", "skipgram",
            "--precompute-similarities",
            "--top-k", "50"
        ],
        "description": "Train Word2Vec embeddings on character sequences"
    },
    2: {
        "name": "Frequency & Tendency Analysis",
        "script": "scripts/run_frequency_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Compute character frequencies and regional tendencies"
    },
    3: {
        "name": "Spatial Analysis",
        "script": "scripts/run_spatial_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Analyze spatial distribution patterns"
    },
    4: {
        "name": "Clustering Analysis",
        "script": "scripts/run_clustering_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Cluster villages based on naming features"
    },
    5: {
        "name": "N-gram Analysis",
        "script": "scripts/phase12_ngram_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Extract and analyze character n-gram patterns"
    },
    6: {
        "name": "Semantic Composition",
        "script": "scripts/phase14_semantic_composition.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Analyze semantic composition patterns"
    }
}


def run_phase(phase_id, run_id_prefix="run", dry_run=False):
    """Run a single analysis phase."""
    if phase_id not in PHASES:
        print(f"❌ Error: Phase {phase_id} not found")
        return False

    phase = PHASES[phase_id]
    print(f"\n{'='*80}")
    print(f"Phase {phase_id}: {phase['name']}")
    print(f"{'='*80}")
    print(f"Description: {phase['description']}")
    print(f"Script: {phase['script']}")

    # Build command
    cmd = ["python", phase['script']]

    # Add run-id if the script supports it
    if phase_id > 0:  # Phase 0 doesn't use run-id
        run_id = f"{run_id_prefix}_{phase_id:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cmd.extend(["--run-id", run_id])

    # Add phase-specific arguments
    cmd.extend(phase['args'])

    print(f"Command: {' '.join(cmd)}")

    if dry_run:
        print("[DRY RUN] Command not executed")
        return True

    # Execute
    print(f"\n[START] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )

        elapsed = time.time() - start_time
        print(f"\n[OK] Phase {phase_id} completed successfully in {elapsed:.1f}s")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n[FAIL] Phase {phase_id} failed after {elapsed:.1f}s")
        print(f"Error: {e}")
        return False

    except KeyboardInterrupt:
        print(f"\n[STOP] Phase {phase_id} interrupted by user")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run Villages-ML analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all phases sequentially"
    )

    parser.add_argument(
        "--phases",
        type=str,
        help="Comma-separated list of phase IDs to run (e.g., '1,2,3')"
    )

    parser.add_argument(
        "--run-id-prefix",
        type=str,
        default="run",
        help="Prefix for run IDs (default: 'run')"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available phases"
    )

    args = parser.parse_args()

    # List phases
    if args.list:
        print("\nAvailable Phases:")
        print("="*80)
        for phase_id, phase in sorted(PHASES.items()):
            print(f"  {phase_id} - {phase['name']}")
            print(f"      {phase['description']}")
        print()
        return 0

    # Determine which phases to run
    if args.all:
        phases_to_run = sorted(PHASES.keys())
    elif args.phases:
        try:
            phases_to_run = [int(p.strip()) for p in args.phases.split(',')]
            # Validate phase IDs
            invalid = [p for p in phases_to_run if p not in PHASES]
            if invalid:
                print(f"❌ Error: Invalid phase IDs: {invalid}")
                print(f"Valid phases: {sorted(PHASES.keys())}")
                return 1
        except ValueError:
            print("❌ Error: Invalid phase format. Use comma-separated integers (e.g., '1,2,3')")
            return 1
    else:
        parser.print_help()
        return 1

    # Run phases
    print("\n" + "="*80)
    print("Villages-ML Analysis Pipeline")
    print("="*80)
    print(f"Phases to run: {phases_to_run}")
    print(f"Run ID prefix: {args.run_id_prefix}")
    print(f"Dry run: {args.dry_run}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    overall_start = time.time()
    results = {}

    for phase_id in phases_to_run:
        success = run_phase(phase_id, args.run_id_prefix, args.dry_run)
        results[phase_id] = success

        if not success and not args.dry_run:
            print(f"\n[STOP] Phase {phase_id} failed. Stop execution.")
            break

    # Summary
    overall_elapsed = time.time() - overall_start
    print("\n" + "="*80)
    print("Pipeline Summary")
    print("="*80)

    for phase_id in phases_to_run:
        status = "[OK]" if results.get(phase_id) else "[FAIL]"
        phase_name = PHASES[phase_id]['name']
        print(f"  Phase {phase_id} ({phase_name}): {status}")

    print(f"\nTotal time: {overall_elapsed:.1f}s")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Return exit code
    all_success = all(results.values())
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
