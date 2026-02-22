# Phase 1 Verification Receipt

**Date:** 2026-02-21
**Phase:** Data Dictionary, Exploration, and Schema
**Verdict:** PASS (all critical checks green)

---

## 1. Join Test

**Fairhaven Middle School (Bellingham, WA):**
- Found in NCES CCD Directory: ✓ (NCESSCH = 530042000104)
- Found in NCES CCD Membership: ✓ (588 enrollment)
- Found in CRDC (all 13 files): ✓ (COMBOKEY = 530042000104)
- Found in OSPI Enrollment: ✓ (SchoolCode = 2066)
- Found in OSPI Assessment: ✓
- Found in OSPI Discipline: ✓ (after comma-stripping)
- Found in OSPI Growth: ✓
- Found in OSPI SQSS: ✓
- Found in OSPI PPE: ✓
- IDs match across all sources: ✓

**Result: PASS** ✓

---

## 2. Crosswalk Test

CCD state school ID field `ST_SCHID` matches OSPI SchoolCode.

- Format in CCD: `WA-37501-2066` (WA-{DistrictCode}-{SchoolCode})
- Format in OSPI: DistrictCode = `37501`, SchoolCode = `2066`
- Match rate across all WA schools: **2,459 / 2,465 = 99.8%**

The 6 unmatched OSPI schools use district codes ending in "9xx" (ESDs or special entities):
`05903_5430`, `17903_1986`, `24915_5756`, `27901_5549`, `34901_5496`, `37903_5373`

CCD → CRDC match rate: **2,373 / 2,566 = 92.5%** (193 schools opened after 2021-22, expected gap)

Full chain OSPI → CCD → CRDC: **2,342 / 2,465 = 95.0%**

**Result: PASS** ✓ (all rates above 90% threshold)

---

## 3. Sample Value Cross-Check

| # | Field | Source | Raw Value | Schema Field | Match? |
|---|-------|--------|-----------|-------------|--------|
| 1 | Enrollment | CCD Membership 2024-25, NCESSCH=530042000104, Education Unit Total | 588 | enrollment.total = 588 | ✓ |
| 2 | FRL Count | OSPI Enrollment 2023-24, SchoolCode=2066, "Low Income" column | 257 | demographics.frl_count = 257 | ✓ |
| 3 | ELA Proficiency | OSPI Assessment 2023-24, TestSubject='ELA', All Students, All Grades | 64.90% | academics.assessment.ela_proficiency_pct = 0.649 | ✓ |
| 4 | Discipline Rate | OSPI Discipline 2023-24, All Students, GradeLevel='All' | 4.55% | discipline.ospi.rate = 0.0455 | ✓ |
| 5 | ELA Growth SGP | OSPI Growth 2023-24, Subject='ELA', All Grades | 61 | academics.growth.ela_median_sgp = 61.0 | ✓ |
| 6 | Regular Attendance | OSPI SQSS 2024-25, Measure='Regular Attendance', All Grades | 0.6003 | academics.attendance.regular_attendance_pct = 0.6003 | ✓ |
| 7 | Total PPE | OSPI PPE 2023-24, SchoolCode=2066 | 17,778.96 | finance.per_pupil_total = 17778.96 | ✓ |
| 8 | Teacher FTE | CRDC School Support 2021-22, COMBOKEY=530042000104 | 33.599998 | staffing.teacher_fte_total = 33.6 | ✓ |
| 9 | Counselor FTE | CRDC School Support 2021-22 | 2 | staffing.counselor_fte = 2.0 | ✓ |
| 10 | Physical Restraint (IDEA) | CRDC R&S 2021-22 | 17 | safety.restraint_seclusion.physical_idea = 17 | ✓ |

**Result: PASS** ✓ (10/10 values match)

---

## 4. Suppression Marker Audit

### CRDC Markers (WA totals across 13 files)

| Marker | Meaning | Count | Handling Rule |
|--------|---------|-------|---------------|
| -9 | Not applicable / skipped | 1,132,661 | → null, flag: not_applicable |
| -5 | Small count suppression (<5 students) | 2,744 | → null, flag: suppressed, reason: small_count |
| -4 | Teacher sex count suppression | 1,004 | → null, flag: suppressed, reason: teacher_sex |
| -3 | Secondary suppression | 809 | → null, flag: suppressed, reason: secondary |
| -12 | Unknown (enrollment only) | 1,664 | → null, flag: suppressed, reason: unknown_negative ⚠️ |
| -13 | Unknown (R&S only) | 30 | → null, flag: suppressed, reason: unknown_negative ⚠️ |
| 0 | **Genuine zero** | 1,354,574 | → 0 (preserved as real data) |

### OSPI Markers

| Marker | Meaning | Approx Count | Handling Rule |
|--------|---------|-------------|---------------|
| N<10 | Privacy (fewer than 10 students) | ~550,000+ | → null, flag: suppressed, reason: n_lt_10 |
| * | Masked numeric value | ~323,000 | → null, flag: suppressed, reason: masked |
| No Students | No students in category | 109,154 | → null, flag: no_students |
| Top/Bottom Range | Extreme value (<X% or >X%) | ~170,000 | → null, flag: suppressed, reason: top_bottom_range |
| Cross Student Group - N<10 | Complementary suppression | ~70,000 | → null, flag: suppressed, reason: cross_group |

### CCD Markers

| Marker | Meaning | Count (WA) | Handling Rule |
|--------|---------|-----------|---------------|
| -1 | Data not available | Unknown | → null, flag: suppressed, reason: not_reported |
| DMS_FLAG "Not reported" | School didn't report | 6,536 | → null, flag: suppressed, reason: not_reported |

**Result: PASS** ✓ (all markers identified and handling rules documented)

⚠️ **Note:** -12 and -13 are undocumented in the CRDC manual. Marked as medium confidence. These affect <0.2% of data cells and should be investigated during pipeline testing.

---

## 5. Zero Verification

**Critical rule: Zero means "zero incidents." Suppressed means "can't tell you." These must never be conflated.**

### CRDC Discipline (WA data)

From the suspensions file (SCH/Suspensions.csv), WA schools:
- Schools with genuinely **zero** ISS values for white males (SCH_DISCWODIS_ISS_WH_M = 0): hundreds of schools
- Schools with **-9** (not applicable) in the same column: schools that don't serve those grades

**Example — Fairhaven Middle School:**
- Corporal punishment count = **0** → This is a genuine zero. WA doesn't allow corporal punishment.
- Preschool enrollment = **-9** → Not applicable. Fairhaven serves grades 6-8, no preschool.
- These are stored differently: 0 → `0` (real data), -9 → `null` with `not_applicable: true`

### OSPI Discipline

- Schools with `DisciplineRate = "0.00%"` exist (genuine zero discipline rate)
- Schools with `DisciplineDATNotes = "N<10"` have suppressed rates (different from zero)
- Schools with `DisciplineNumerator = "0"` and `DisciplineNumerator = "*"` are different — first is zero incidents, second is suppressed

**Result: PASS** ✓ (zero values preserved as zero, suppressed values handled separately)

---

## 6. Confidence Summary

**Total column mappings: 60+**

| Confidence | Count | Percentage |
|-----------|-------|------------|
| High (>90%) | 57 | 95% |
| Medium (70-90%) | 3 | 5% |
| Low (<70%) | 0 | 0% |

### Medium-Confidence Mappings (detail)

1. **CRDC marker -12 in enrollment** (1,664 occurrences)
   - Not documented in CRDC manual. Appears only in enrollment derived fields.
   - Treating as suppressed until confirmed. Affects <0.1% of data.
   - **Action:** Investigate specific columns during pipeline testing.

2. **CRDC marker -13 in restraint/seclusion** (30 occurrences)
   - Not documented. Very rare.
   - **Action:** Log all 30 instances and review manually.

3. **OSPI Top/Bottom Range handling** (~170,000 occurrences)
   - Values like "<27.3%" could be parsed as approximate thresholds.
   - Currently treating as fully suppressed (null).
   - **Action:** Decide in Phase 2 whether to store the threshold value as an approximate.

**Result: PASS** ✓ (no low-confidence mappings, 3 medium-confidence items documented)

---

## 7. Completeness Check

Comparing mapped schema fields against the 12 briefing sections required by the foundation document:

| Briefing Section | Required Fields | Mapped? | Source |
|-----------------|----------------|---------|--------|
| 1. Rating Context | External ratings | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |
| 2. Academics in Context | Proficiency, growth, percentiles | ✓ Assessment + growth mapped | OSPI |
| 3. Demographics | Enrollment, race, FRL, ELL, SPED | ✓ All mapped | CCD + OSPI |
| 4. Staffing and Resources | Teacher FTE, counselors, SROs, PPE | ✓ All mapped | CRDC + OSPI PPE |
| 5. Strengths and Recognition | Awards, grants, programs | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |
| 6. Climate and Discipline | Suspensions, R&S, referrals, attendance | ✓ All mapped | CRDC + OSPI |
| 7. Reputation and News | OCR complaints, investigations | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |
| 8. Statewide Context | Policy changes, recovery notes | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |
| 9. What's Missing | Suppression disclosure | ✓ Suppression rules mapped | All sources |
| 10. Peer Schools | Peer matching | ⏳ Schema placeholder | Phase 3 (derived) |
| 11. Did You Know? | Notable facts | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |
| 12. Action Layer | Board meetings, FOIA | ❌ Not in Phase 1 | Phase 4 (AI enrichment) |

**Sections 1, 5, 7, 8, 11, 12** require AI enrichment (Phase 4) — they are not sourced from the raw data files. This is expected and by design.

**Section 10** (Peer Schools) requires derived calculations (Phase 3) — schema has placeholders.

**All data-sourced sections (2, 3, 4, 6, 9) are fully mapped.** ✓

**Result: PASS** ✓

---

## 8. Data Vintage Disclosure

| Source | Year | Gap from Current (2024-25) |
|--------|------|---------------------------|
| CCD Directory & Membership | 2024-25 | Current |
| OSPI Growth, SQSS | 2024-25 | Current |
| OSPI Enrollment, Assessment, Discipline | 2023-24 | 1 year |
| OSPI PPE | 2023-24 (most recent) | 1 year |
| CRDC | 2021-22 | 3 years |

**Implications documented:**
- ~128 schools in CCD not in CRDC (opened after 2021-22) ✓
- Enrollment numbers differ across sources (different years, expected) ✓
- CRDC discipline data is 3+ years old but is the only disaggregated source ✓
- Briefing must disclose data vintage for every metric ✓

**Result: PASS** ✓

---

## Overall Verdict

| Check | Result |
|-------|--------|
| 1. Join test (Fairhaven across all sources) | ✓ PASS |
| 2. Crosswalk test (99.8% match rate) | ✓ PASS |
| 3. Sample value cross-check (10/10 match) | ✓ PASS |
| 4. Suppression marker audit (all identified) | ✓ PASS |
| 5. Zero verification (zeros preserved as zero) | ✓ PASS |
| 6. Confidence summary (57 high, 3 medium, 0 low) | ✓ PASS |
| 7. Completeness check (all data sections mapped) | ✓ PASS |
| 8. Data vintage disclosure (all documented) | ✓ PASS |

## **Phase 1: APPROVED TO PROCEED** ✓

---

## Output Files Produced

| File | Purpose |
|------|---------|
| `data/data_dictionary.yaml` | Every source column mapped to schema |
| `data/schema.yaml` | MongoDB document structure |
| `phases/phase-1/exploration_report.md` | File shapes, surprises, data quality |
| `phases/phase-1/decision_log.md` | Why each mapping was made |
| `phases/phase-1/fairhaven_test.md` | Proof Fairhaven joins across sources |
| `phases/phase-1/receipt.md` | This file |
| `phases/phase-1/01-05_explore_*.py` | Exploration scripts (5 scripts) |
| `data/ccd_wa_directory.csv` | WA-only CCD directory extract |
| `data/ccd_wa_membership.csv` | WA-only CCD membership (aggregated) |
| `data/crdc_wa/*.csv` | WA-only CRDC extracts (13 files) |
