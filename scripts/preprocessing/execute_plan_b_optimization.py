"""Execute Plan B Database Optimization.

This script executes the complete Plan B optimization:
1. Regenerate preprocessed table with:
   - village_id column
   - longitude/latitude as REAL type
   - Column name: 村委会 (not 行政村)
2. Add village_id to main table
3. Regenerate village_ngrams table
4. Regenerate village_semantic_structure table
5. Verify all changes

Total estimated time: 2-3 hours
"""

import subprocess
import sys
import time
from pathlib import Path

def run_script(script_path: str, description: str):
    """Run a Python script and report results."""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*80}\n")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True
        )

        elapsed = time.time() - start_time
        print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        print(f"\n✅ Completed in {elapsed:.1f} seconds")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED after {elapsed:.1f} seconds")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Execute all optimization steps."""
    base_dir = Path(__file__).parent.parent.parent

    steps = [
        {
            'script': base_dir / 'scripts' / 'preprocessing' / 'create_preprocessed_table.py',
            'description': 'Step 1: Regenerate preprocessed table (village_id + REAL coords + 村委会)',
            'estimated_time': '15-20 min'
        },
        {
            'script': base_dir / 'scripts' / 'preprocessing' / 'add_village_id_to_main_table.py',
            'description': 'Step 2: Add village_id to main table',
            'estimated_time': '5 min'
        },
        {
            'script': base_dir / 'scripts' / 'core' / 'populate_village_ngrams.py',
            'description': 'Step 3: Regenerate village_ngrams table',
            'estimated_time': '20-25 min'
        },
        {
            'script': base_dir / 'scripts' / 'core' / 'phase14_semantic_composition.py',
            'description': 'Step 4: Regenerate village_semantic_structure table',
            'estimated_time': '40-50 min'
        },
        {
            'script': base_dir / 'scripts' / 'verification' / 'verify_village_id.py',
            'description': 'Step 5: Verify all changes',
            'estimated_time': '2 min'
        }
    ]

    print("="*80)
    print("PLAN B DATABASE OPTIMIZATION")
    print("="*80)
    print("\nChanges to be applied:")
    print("  ✅ Add village_id to all analysis tables")
    print("  ✅ Change longitude/latitude to REAL type")
    print("  ✅ Rename column: 行政村 → 村委会")
    print("  ❌ Skip run_id (not needed)")
    print("\nTotal estimated time: 2-3 hours")
    print("\nSteps:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step['description']} ({step['estimated_time']})")

    response = input("\nProceed with optimization? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        return

    # Execute steps
    start_time = time.time()
    failed_steps = []

    for i, step in enumerate(steps, 1):
        success = run_script(str(step['script']), f"{i}. {step['description']}")

        if not success:
            failed_steps.append(i)
            print(f"\n⚠️  Step {i} failed. Do you want to continue? (yes/no): ", end='')
            response = input()
            if response.lower() not in ['yes', 'y']:
                print("Optimization aborted.")
                break

    # Summary
    total_time = time.time() - start_time
    print(f"\n{'='*80}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"Steps completed: {len(steps) - len(failed_steps)}/{len(steps)}")

    if failed_steps:
        print(f"Failed steps: {', '.join(map(str, failed_steps))}")
        print("\n⚠️  Optimization completed with errors")
    else:
        print("\n✅ All steps completed successfully!")
        print("\nNext steps:")
        print("  1. Test API endpoints")
        print("  2. Run benchmark tests")
        print("  3. Update documentation")


if __name__ == '__main__':
    main()
