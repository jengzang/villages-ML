# Villages-ML Analysis Results Showcase

**Generated:** 2026-02-19
**Purpose:** Comprehensive review of all analysis results to inform rerun decision

---

## Executive Summary

This document showcases all analysis results across 15 implementation phases (Phase 0-14) of the villages-ML project. The goal is to help decide whether to:

- **Option A:** Rerun all analyses with new preprocessed data (current algorithms)
- **Option B:** Improve algorithms first, then rerun
- **Option C:** Selective rerun (only certain phases)

### Dataset Overview

- **Total villages:** 285,860
- **Valid villages:** 284,764
- **Database size:** 1.7GB
- **Total tables:** 26
- **Unique characters:** 3,876
- **Geographic coverage:** 12 cities, 100+ counties, 1,500+ townships

---

## Phase 0: Data Preprocessing

### Status: ✅ Complete (Just Regenerated - 2026-02-19)

### Implementation Details

**Table:** `广东省自然村_预处理`

**Processing Time:** ~47 seconds for full dataset

**Algorithm:** 5-rule priority system
1. Rule 1: Greedy delimiter-based removal (村/社区/寨/片)
2. Rule 2: Admin village comparison (with homophone support)
3. Rule 3: Modifier handling (大/小/新/老/东/西/南/北/上/下)
4. Rule 4: Minimum length validation (≥2 characters)
5. Rule 5: Identical names early exit

### Results Summary

**Overall Statistics:**
- Prefixes removed: 5,704 villages (2.00%)
- Numbered villages: 4,808 villages (1.7%)
- Processing throughput: ~21,900 villages/second

**Removal by Rule Type:**
- Rule 2 (Admin comparison): 4,041 (70.8%)
- Rule 3 (Modifier handling): 835 (14.6%)
- Rule 1 (Delimiter-based): 828 (14.5%)

**Top 5 Cities by Removal Rate:**
1. 汕头市: 790/4,586 (17.23%)
2. 揭阳市: 241/2,863 (8.42%)
3. 汕尾市: 510/6,379 (7.99%)
4. 潮州市: 607/8,253 (7.35%)
5. 河源市: 65/1,059 (6.14%)

### Sample Results

**Example 1 - Rule 1 (Delimiter):**
- Original: `霞露村尾厝`
- Removed: `霞露村`
- Result: `尾厝`

**Example 2 - Rule 2 (Admin comparison):**
- Admin: `凤北村`
- Original: `凤北超苟村`
- Removed: `凤北`
- Result: `超苟村`

**Example 3 - Rule 2 (Homophone):**
- Admin: `湖下村`
- Original: `湖厦村祠堂前片`
- Removed: `湖厦村`
- Result: `祠堂前片`

**Example 4 - Rule 3 (Modifier):**
- Admin: `松水村`
- Original: `大松水路头`
- Removed: `大松水`
- Result: `路头`

### Quality Assessment

**Completeness:** ✅ Excellent (100% of villages processed)
**Accuracy:** ✅ Excellent (40 unit tests passing, all user examples verified)
**Coverage:** ✅ Good (2.0% removal rate, varies by region)
**Usefulness:** ✅ Excellent (cleaner names for downstream analysis)

### Impact on Downstream Analyses

**Affected Villages:** 5,704 (2.0%) now have different cleaned names

**Potentially Affected Phases:**
- Phase 12: N-gram Analysis (if uses preprocessed table)
- Phase 14: Semantic Composition (if uses preprocessed table)
- All other phases: NOT affected (use raw table)

---

