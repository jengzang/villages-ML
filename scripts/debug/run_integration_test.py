#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to run spatial_tendency_integration with detailed logging.
"""
import sys
import subprocess
import time

print("Starting spatial_tendency_integration test...")
print("=" * 60)

cmd = [
    sys.executable,
    "scripts/experimental/spatial_tendency_integration.py",
    "--chars", "村",
    "--tendency-run-id", "freq_final_001",
    "--spatial-run-id", "final_03_20260219_225259",
    "--output-run-id", "integration_test_003"
]

print(f"Command: {' '.join(cmd)}")
print("=" * 60)

start_time = time.time()

try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )

    elapsed = time.time() - start_time

    print(f"\nExit code: {result.returncode}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print("\n" + "=" * 60)
    print("STDOUT:")
    print("=" * 60)
    print(result.stdout)

    if result.stderr:
        print("\n" + "=" * 60)
        print("STDERR:")
        print("=" * 60)
        print(result.stderr)

except subprocess.TimeoutExpired:
    elapsed = time.time() - start_time
    print(f"\n[ERROR] Script timed out after {elapsed:.2f}s")
except Exception as e:
    print(f"\n[ERROR] {e}")
