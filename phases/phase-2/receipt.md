# Phase 2 — Verification Receipt

**Generated:** 2026-02-22T04:02:59.035280+00:00
**Dataset version:** 2026-02-v1
**Document count:** 2532

---

## Fairhaven Field-by-Field Verification

| Check | Result | Details |
|-------|--------|---------|
| Fairhaven exists in MongoDB | PASS | _id=530042000104 |
| Fairhaven enrollment.total | PASS | 588 |
| Fairhaven demographics.frl_count | PASS | 257 |
| Fairhaven academics.assessment.ela_proficiency_pct | PASS | 0.649 (expected 0.649) |
| Fairhaven academics.assessment.math_proficiency_pct | PASS | 0.5489999999999999 (expected 0.549) |
| Fairhaven academics.growth.ela_median_sgp | PASS | 56.0 |
| Fairhaven academics.growth.math_median_sgp | PASS | 60.0 |
| Fairhaven academics.attendance.regular_attendance_pct | PASS | 0.6003 (expected 0.6003) |
| Fairhaven discipline.ospi.rate | PASS | 0.0455 (expected 0.0455) |
| Fairhaven finance.per_pupil_total | PASS | 17778.96 (expected 17778.96) |
| Fairhaven staffing.teacher_fte_total | PASS | 33.599998 (expected 33.6) |
| Fairhaven staffing.counselor_fte | PASS | 2.0 |
| Fairhaven safety.restraint_seclusion.physical_idea | PASS | 17 |

---

## Integrity Checks

| Check | Result | Details |
|-------|--------|---------|
| Document count | PASS | 2532 documents |
| NCES IDs are 12-char strings | PASS | All 2532 valid |
| Percentages in 0.0-1.0 range | PASS | No violations |
| All docs have dataset_version | PASS | All 2532 present |
| Unique _id count | PASS | 2532 unique = 2532 total |
| Join failure rate < 5% | PASS | 57/2532 = 2.3% |

---

## Join Status Summary

| Status | Count |
|--------|-------|
| all_sources | 2344 |
| ccd_only | 41 |
| missing_crdc | 131 |
| missing_ospi | 16 |

---

## Source File SHA256 Hashes

| File | SHA256 |
|------|--------|
| ccd_wa_directory.csv | `b4ac943d31e34506...` |
| ccd_wa_membership.csv | `f3e277edfb1edd80...` |
| crdc_wa/advanced_placement.csv | `2cf40424a7a4c1fc...` |
| crdc_wa/corporal_punishment.csv | `63f66a506ef745db...` |
| crdc_wa/dual_enrollment.csv | `35659c154e9c3001...` |
| crdc_wa/enrollment.csv | `02cef887ec5d87dc...` |
| crdc_wa/expulsions.csv | `1a92881c4a056f0e...` |
| crdc_wa/gifted_and_talented.csv | `5d4d153942f8d1a7...` |
| crdc_wa/harassment_and_bullying.csv | `473a48f031775948...` |
| crdc_wa/offenses.csv | `b6c2294f6f508ee3...` |
| crdc_wa/referrals_and_arrests.csv | `35ff50ce64b5cb43...` |
| crdc_wa/restraint_and_seclusion.csv | `5d96152a8f0644f9...` |
| crdc_wa/school_characteristics.csv | `05d328f87e610572...` |
| crdc_wa/school_support.csv | `5e9429e2a7743a1f...` |
| crdc_wa/suspensions.csv | `f0447dd72e11c1f2...` |
| ospi/Per_Pupil_Expenditure_AllYears.csv | `0e1d43f804017477...` |
| ospi/Report_Card_Assessment_Data_2023-24.csv | `d893c586fc9a5a11...` |
| ospi/Report_Card_Discipline_for_2023-24.csv | `6cd5c475491290e1...` |
| ospi/Report_Card_Enrollment_2023-24_School_Year.csv | `568c7bfb52e95f12...` |
| ospi/Report_Card_Growth_for_2023-24.csv | `e3255c62e5d03905...` |
| ospi/Report_Card_Growth_for_2024-25.csv | `364b0663eaded845...` |
| ospi/Report_Card_SQSS_for_2024-25.csv | `54d4754b4450ddd0...` |

---

## Growth Data Year Note

Fairhaven growth SGP values use 2024-25 data (ELA=56, Math=60), 
not the 2023-24 values verified in Phase 1 (ELA=61, Math=68). 
This is correct behavior: the pipeline uses 2024-25 as primary and 
only falls back to 2023-24 when a school has zero rows in the 2024-25 file. 
Fairhaven IS present in the 2024-25 file with updated data.
