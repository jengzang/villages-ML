#!/usr/bin/env python3
"""
⚠️ DEPRECATED - DO NOT USE ⚠️

This script is deprecated as of 2026-03-02.

REASON:
Backend API uses dynamic aggregation for City/County level queries.
Only Township level data needs to be stored in the database.

WHAT THIS SCRIPT DID:
- Generated City and County level n-gram data
- Created 5.4M+ additional records
- Increased database size by 1.8 GB

WHY IT'S DEPRECATED:
- Backend API already supports dynamic aggregation from Township data
- City/County queries can be computed on-the-fly with acceptable latency (100-500ms)
- Storing pre-computed City/County data wastes 1.6 GB of space

CURRENT APPROACH:
- Only Township level data is stored
- City/County queries aggregate from Township data at runtime
- Database size: 2.5 GB (down from 4.1 GB)

IF YOU NEED TO REGENERATE DATA:
- Use phase12_ngram_analysis.py for Township level data
- Backend API will handle City/County aggregation automatically

CONTACT:
If you believe City/County pre-computed data is needed, please:
1. Discuss with backend team first
2. Measure actual query performance impact
3. Consider the 1.6 GB storage cost

Last updated: 2026-03-02
"""

import sys

def main():
    print("=" * 80)
    print("⚠️  ERROR: This script is DEPRECATED")
    print("=" * 80)
    print()
    print(__doc__)
    print()
    print("=" * 80)
    sys.exit(1)

if __name__ == '__main__':
    main()
