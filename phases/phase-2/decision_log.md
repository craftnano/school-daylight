# Phase 2 — Decision Log

Deviations from the implementation plan, with reasoning.

---

## 1. Growth SGP values differ from Phase 1 fairhaven_test.md

**Date:** 2026-02-21
**Context:** Phase 1 verified Fairhaven growth against the 2023-24 file (ELA SGP=61, Math SGP=68). The pipeline uses 2024-25 as the primary growth year.

**Decision:** Fairhaven IS present in the 2024-25 growth file with updated values (ELA SGP=56, Math SGP=60). Per the approved fallback rule (clarification #2), the pipeline only falls back to 2023-24 when a school has zero rows in the 2024-25 file. Since Fairhaven has data in 2024-25, we use those values.

**Impact:** Step 10 verification uses the 2024-25 values (56, 60) rather than the Phase 1 values (61, 68). This is correct behavior — the pipeline is working as designed.

---

## 2. Growth "PercentLowGrowth" columns are counts, not percentages

**Date:** 2026-02-21
**Context:** Phase 1 noted these columns might be counts despite the "Percent" naming (Known Issue #6).

**Decision:** Confirmed during implementation — the 2024-25 growth file has columns named `NumberLowGrowth`, `NumberTypicalGrowth`, `NumberHighGrowth` (integer counts). There are also `PercentLowGrowth`, `PercentTypicalGrowth`, `PercentHighGrowth` columns. The pipeline stores the Number columns as counts, not the Percent columns, since the Number values are more directly useful and avoid percentage naming confusion.

**Impact:** Schema fields are named `*_growth_count` (e.g., `ela_low_growth_count`).

---

## 3. PPE SchoolCode confirmed unique statewide

**Date:** 2026-02-21
**Context:** Clarification #1 asked to verify whether SchoolCode is unique statewide or if DistrictCode is needed.

**Decision:** Verified 0 collisions across all 2,457 SchoolCodes in the 2023-24 PPE data. SchoolCode alone is sufficient for the join. No DistrictCode needed.

**Impact:** None — the simple SchoolCode join works correctly.

---

## 4. CRDC -12/-13 count lower than Phase 1 estimate

**Date:** 2026-02-21
**Context:** Phase 1 estimated 1,694 instances of -12/-13. The pipeline logged 998.

**Decision:** The discrepancy is due to Phase 1 counting across ALL columns (including non-school-level and non-data columns like COMBOKEY, LEA_STATE, etc.), while the pipeline only counts school-level data columns (those starting with `SCH_`). The 998 count is the correct number of instances in actual data fields. All are logged to `logs/crdc_unknown_markers.csv`.

**Impact:** None — all real data instances are captured.

---

## 5. CRDC FTE values have float precision from raw data

**Date:** 2026-02-21
**Context:** Fairhaven's teacher_fte shows as 33.599998 instead of 33.6.

**Decision:** This is the raw CRDC value (CRDC stores FTE as single-precision floats). The pipeline preserves the raw value rather than rounding, as rounding could introduce errors for other schools where the raw precision matters. The verification uses appropriate tolerance (0.1) for float comparisons.

**Impact:** Display formatting should round to 1 decimal place in the frontend (Phase 3+).
