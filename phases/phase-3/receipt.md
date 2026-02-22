# Phase 3 — Verification Receipt

**Generated:** 2026-02-22T05:20:23.279486+00:00
**Dataset version:** 2026-02-v1
**Document count:** 2532

---

## Fairhaven Phase 3 Verification

| Check | Result | Details |
|-------|--------|---------|
| Fairhaven exists in MongoDB | PASS | _id=530042000104 |
| Fairhaven derived.performance_flag | PASS | outperforming |
| Fairhaven derived.regression_zscore | PASS | 1.37 (expected 1.33) |
| Fairhaven derived.regression_group | PASS | Middle |
| Fairhaven derived.student_teacher_ratio | PASS | 17.5 (expected 17.5) |
| Fairhaven derived.counselor_student_ratio | PASS | 294.0 (expected 294.0) |
| Fairhaven derived.chronic_absenteeism_pct | PASS | 0.3997 (expected 0.3997) |
| Fairhaven derived.proficiency_composite | PASS | 0.599 (expected 0.599) |
| Fairhaven derived.peer_cohort | PASS | Middle_Large_MidFRL |
| Fairhaven flags.chronic_absenteeism.color | PASS | red |
| Fairhaven flags.counselor_ratio.color | PASS | green |
| Fairhaven flags.discipline_disparity.color | PASS | red |
| Fairhaven ELA state percentile > 50 | PASS | 77 |

---

## Sanity School Checks

| Check | Result | Details |
|-------|--------|---------|
| Low-FRL high-score (Capt Johnston Blakely Elem Sch) | WARN | frl=0.09, composite=0.903, flag=outperforming (expected as_expected) |
| High-FRL low-score (Inchelium Middle School) | PASS | frl=0.88, composite=0.134, flag=as_expected |
| High disparity (Enumclaw Sr High School) | PASS | disparity=6.86, flag=red |
| Single-school district (Washington State School for the Deaf) | PASS | district percentile is null (correct) |
| Missing CRDC (Clallam Co Juvenile Detention) | PASS | disparity color=null, reason=data_not_available |
| Low-FRL underperforming (BOISTFORT ONLINE SCHOOL) | PASS | frl=0.01, composite=0.181, flag=underperforming (key insight) |

---

## Regression Summary

- **Schools with performance flag:** 1152
- **Outperforming (green):** 152
- **As expected (yellow):** 838
- **Underperforming (red):** 162
- **Schools with peer cohort:** 2323
- **Schools with percentiles:** 2532

---

## Flag Distribution

### chronic_absenteeism

| Color/Status | Count |
|-------------|-------|
| green | 708 |
| null (data_not_available) | 473 |
| null (grade_span_not_tested) | 98 |
| red | 640 |
| yellow | 613 |

### counselor_ratio

| Color/Status | Count |
|-------------|-------|
| green | 1074 |
| null (data_not_available) | 747 |
| red | 339 |
| yellow | 372 |

### discipline_disparity

| Color/Status | Count |
|-------------|-------|
| green | 647 |
| null (data_not_available) | 1232 |
| red | 417 |
| yellow | 236 |

### no_counselor

| Color/Status | Count |
|-------------|-------|
| red | 567 |

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
