# Phase 2 — Phase Exit Document

**Date:** 2026-02-21
**Reviewed by:** Orianda Leigh (builder/project owner)
**Phase:** ETL Pipeline + MongoDB Load
**Verdict:** APPROVED TO PROCEED TO PHASE 3

---

## Human Review Log

- **Receipt reviewed:** All 19 checks PASS (13 Fairhaven field checks + 6 integrity checks). Accepted.
- **Fairhaven verified:** All fields match expected values. Growth SGP values use 2024-25 data (ELA=56, Math=60), not the 2023-24 values verified in Phase 1 (ELA=61, Math=68). This is correct behavior — the pipeline uses 2024-25 as primary and Fairhaven is present in that file. Accepted.
- **Decision log reviewed:** 5 deviations from the implementation plan, all accepted:
  1. Growth SGP year change (2024-25 vs 2023-24) — correct per fallback rule
  2. Growth count columns named `*_growth_count` instead of percentages — confirmed as counts
  3. PPE SchoolCode unique statewide (0 collisions) — simple join works
  4. CRDC -12/-13 count 998 vs Phase 1 estimate of 1,694 — difference is non-data columns
  5. CRDC FTE float precision from raw data — preserve raw, round in frontend

---

## Verification Summary

- **All 19 checks PASSED** (13 Fairhaven field checks + 6 integrity checks)
- **2,532 documents** loaded to MongoDB Atlas
- **2,344 schools** have all data sources (CCD + OSPI + CRDC)
- **131 schools** missing CRDC (opened after 2021-22)
- **16 schools** missing OSPI (ESDs/special entities)
- **41 schools** CCD only (no OSPI or CRDC match)
- **Join failure rate: 2.3%** (target was < 5%)
- **998 instances** of CRDC -12/-13 logged to CSV

---

## Known Issues Carried Forward to Phase 3

1. **CRDC -12/-13 manual review:** 998 instances logged to `logs/crdc_unknown_markers.csv`. These are undocumented suppression codes treated as suppressed. Manual review should confirm no real data is being discarded. Briefings must disclose the caveat.
2. **FTE display rounding:** CRDC FTE values have single-precision float artifacts (e.g., 33.599998 instead of 33.6). Frontend display should round to 1 decimal place. Math proficiency similarly needs rounding to 3 decimals (0.5489999999999999 → 0.549).
3. **schema.yaml updates from deviation #2:** Growth fields are stored as `*_growth_count` (integer counts), not `*_growth_pct` (percentages). The `data/schema.yaml` should be updated to reflect the actual field names used in the pipeline.

---

## Go/No-Go

Phase 2: GO. Proceed to Phase 3.
