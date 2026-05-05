# Phase 3R — Data Element Inventory

**Purpose:** Complete inventory of every data element the Phase 3 comparison engine currently touches. Reference document for Phase 3R formalization and Layer 2 narrative design.

**Scope:** What the code actually computes today. Not what `foundation.md` aspires to.

**Generated:** 2026-05-02 from a read-only scan of `pipeline/12_compute_ratios.py`, `pipeline/13_assign_peer_groups.py`, `pipeline/14_compute_percentiles.py`, `pipeline/15_regression_and_flags.py`, `flag_thresholds.yaml`, `school_exclusions.yaml`, and a sample MongoDB document (Fairhaven Middle School, NCES 530042000104). Coverage percentages are non-null counts across the 2,532-school production collection.

**Notation conventions:**
- "Coverage" is `db.schools.count_documents({field: {$ne: null, $exists: true}}) / 2532`.
- "Currently compared against" reflects what the comparison engine does *today*, not what's possible.
- "Used as flag input" answers whether the field directly feeds a flag computation, not whether it's mentioned in any prose.

---

## 1. Academic performance metrics

### ELA proficiency percent
- **MongoDB field path:** `academics.assessment.ela_proficiency_pct`
- **Source dataset:** OSPI Report Card 2023-24
- **Source column(s):** ELA proficiency rate (`Percent met standard`-class metric)
- **Data type:** percentage (0.0–1.0 decimal)
- **Suppression handling:** null when source suppressed (N<10); separate `{field}_suppressed: true` flag handled by `is_suppressed()` helper at `pipeline/15_regression_and_flags.py:481`
- **Currently compared against:** state percentile / district percentile / peer-cohort percentile (via `derived.percentiles.ela_proficiency_pct`); also feeds `proficiency_composite` as the X-input to the FRL regression
- **Flag output:** no flag of its own; contributes to `performance_flag` via composite
- **Threshold values:** none (percentile-based)
- **Coverage:** 1,477 schools (58.3%)
- **Used in regression as:** dependent variable (component of `proficiency_composite`)
- **Used as flag input:** indirectly via composite

### Math proficiency percent
- **MongoDB field path:** `academics.assessment.math_proficiency_pct`
- **Source dataset:** OSPI Report Card 2023-24
- **Source column(s):** Math proficiency rate
- **Data type:** percentage (0.0–1.0)
- **Suppression handling:** same as ELA — null + separate suppressed flag
- **Currently compared against:** state / district / peer percentile; component of regression composite
- **Flag output:** no flag of its own
- **Threshold values:** none
- **Coverage:** 1,445 schools (57.1%)
- **Used in regression as:** dependent variable (component of composite)
- **Used as flag input:** indirectly via composite

### Science proficiency percent
- **MongoDB field path:** `academics.assessment.science_proficiency_pct`
- **Source dataset:** OSPI Report Card 2023-24
- **Source column(s):** Science (WCAS) proficiency rate
- **Data type:** percentage (0.0–1.0)
- **Suppression handling:** null + separate suppressed flag
- **Currently compared against:** **not compared** — no percentile, no flag, no inclusion in composite
- **Flag output:** none
- **Threshold values:** n/a
- **Coverage:** 1,447 schools (57.1%)
- **Used in regression as:** not used
- **Used as flag input:** no

### Students tested counts (ELA / Math / Science)
- **MongoDB field path:** `academics.assessment.{ela,math,science}_students_tested`
- **Source dataset:** OSPI Report Card 2023-24
- **Source column(s):** Students tested by subject
- **Data type:** count (integer)
- **Suppression handling:** null when subject was suppressed
- **Currently compared against:** descriptive only (used to filter out tiny tested cohorts implicitly when proficiency is suppressed)
- **Flag output:** none
- **Threshold values:** none
- **Coverage:** ~57% (parallels proficiency)
- **Used in regression as:** not used
- **Used as flag input:** no

### ELA median Student Growth Percentile (SGP)
- **MongoDB field path:** `academics.growth.ela_median_sgp`
- **Source dataset:** OSPI Growth (SGP) 2024-25
- **Source column(s):** Median Student Growth Percentile, ELA
- **Data type:** percentile (0–100 integer)
- **Suppression handling:** null when source suppressed
- **Currently compared against:** **not compared** — not in the `percentile_metrics` list at `flag_thresholds.yaml:83-122`; no flag
- **Flag output:** none
- **Threshold values:** n/a
- **Coverage:** 1,443 schools (57.0%)
- **Used in regression as:** not used
- **Used as flag input:** no

### Math median Student Growth Percentile
- **MongoDB field path:** `academics.growth.math_median_sgp`
- **Source dataset:** OSPI Growth (SGP) 2024-25
- **Source column(s):** Median Student Growth Percentile, Math
- **Data type:** percentile (0–100)
- **Suppression handling:** null when suppressed
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Threshold values:** n/a
- **Coverage:** 1,444 schools (57.0%)
- **Used in regression as:** not used
- **Used as flag input:** no

### Growth-tier counts (ELA + Math low / typical / high)
- **MongoDB field paths:** `academics.growth.{ela,math}_{low,typical,high}_growth_count`
- **Source dataset:** OSPI Growth 2024-25
- **Data type:** count (integer)
- **Suppression handling:** null when suppressed
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** ~57% (parallels SGP)
- **Used in regression as:** not used
- **Used as flag input:** no

### Regular attendance percent
- **MongoDB field path:** `academics.attendance.regular_attendance_pct`
- **Source dataset:** OSPI SQSS 2024-25 (attendance data lives in the SQSS file, not a separate attendance file)
- **Source column(s):** Regular Attendance rate (1 − chronic absenteeism)
- **Data type:** percentage (0.0–1.0)
- **Suppression handling:** null when suppressed
- **Currently compared against:** state / district / peer percentile; serves as the BASIS for `derived.chronic_absenteeism_pct` (1 − this value)
- **Flag output:** no flag of its own; chronic-absenteeism flag uses the inverse
- **Threshold values:** none directly
- **Coverage:** 1,961 schools (77.4%)
- **Used in regression as:** not used
- **Used as flag input:** indirectly via chronic-absenteeism inverse

### Attendance numerator and denominator
- **MongoDB field paths:** `academics.attendance.numerator`, `academics.attendance.denominator`
- **Data type:** count
- **Suppression handling:** null when suppressed
- **Currently compared against:** descriptive only
- **Flag output:** none
- **Coverage:** ~77%
- **Used as flag input:** no

### Ninth-grade-on-track (placeholder)
- **MongoDB field path:** `academics.ninth_grade_on_track`
- **Source dataset:** OSPI Report Card (planned)
- **Data type:** placeholder dict containing only `{year: "2024-25"}` on most schools
- **Suppression handling:** the data is effectively absent — no actual rate stored
- **Currently compared against:** **not compared** — empty container
- **Flag output:** none
- **Coverage:** structurally present on most schools but no rate values populated
- **Used as flag input:** no

### Dual-credit (placeholder)
- **MongoDB field path:** `academics.dual_credit`
- **Source dataset:** OSPI Report Card (planned)
- **Data type:** placeholder dict containing only `{year: "2024-25"}`
- **Currently compared against:** **not compared** — empty container
- **Coverage:** 2,019 schools have the `year` key; no rate values populated
- **Used as flag input:** no

### Comparison engine treatment summary — Academic performance metrics

| Treatment | Metrics |
|---|---|
| **Produces a flag** | None directly. `performance_flag` (outperforming / as_expected / underperforming) derives from the composite of ELA + Math proficiency vs. FRL regression. |
| **Has percentiles** | ELA proficiency, Math proficiency, regular attendance |
| **Computed but not surfaced** | Science proficiency, ELA median SGP, math median SGP, growth-tier counts |
| **Placeholder only** | Ninth-grade-on-track, dual-credit (year tag with no values) |

---

## 2. Climate and discipline metrics

### OSPI discipline rate
- **MongoDB field path:** `discipline.ospi.rate`
- **Source dataset:** OSPI Discipline 2023-24
- **Source column(s):** State-reported discipline rate (Discipline Rate column)
- **Data type:** percentage (0.0–1.0)
- **Suppression handling:** null when N<10, "*", or "No Students" (per `cleaning_rules.yaml`)
- **Currently compared against:** state / district / peer percentile (lower-is-better polarity at `flag_thresholds.yaml:119-122`)
- **Flag output:** no dedicated flag (the disparity flag uses CRDC, not this rate)
- **Threshold values:** none directly; appears in percentile output
- **Coverage:** 1,202 schools (47.5%)
- **Used in regression as:** not used
- **Used as flag input:** no — but produces percentile

### OSPI discipline numerator / denominator
- **MongoDB field paths:** `discipline.ospi.numerator`, `discipline.ospi.denominator`
- **Data type:** count (integer)
- **Suppression handling:** null when suppressed
- **Currently compared against:** descriptive only
- **Flag output:** none
- **Coverage:** parallels rate (~47%)

### CRDC in-school suspensions (ISS) by race × sex
- **MongoDB field path:** `discipline.crdc.iss` (object keyed `{race}_{male|female}`)
- **Source dataset:** CRDC 2021-22
- **Source column(s):** ISS counts by race × sex (e.g., `SCH_DISCWODIS_ISS_HI_M`)
- **Data type:** count (integer per race-sex cell)
- **Suppression handling:** -9 (N/A), -5 (small count), -4 (teacher sex), -3 (secondary) → null per the project's `RULE: SUPPRESSION_CRDC_*` handlers
- **Currently compared against:** not directly — feeds the discipline disparity ratio computation at `pipeline/12_compute_ratios.py:62-78`
- **Flag output:** indirectly via `discipline_disparity` flag
- **Threshold values:** disparity flag thresholds: yellow 2.0, red 3.0 (`flag_thresholds.yaml:213-216`)
- **Coverage:** 2,275 schools (89.8%)
- **Used as flag input:** yes (component of disparity ratio numerator)

### CRDC ISS for IDEA students by race × sex
- **MongoDB field path:** `discipline.crdc.iss_idea`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** ISS for students with disabilities served under IDEA, by race × sex
- **Data type:** count
- **Suppression handling:** same CRDC suppression treatment
- **Currently compared against:** **not compared** — separately tracked, not included in disparity ratio
- **Flag output:** none
- **Coverage:** parallels ISS (~89%)
- **Used as flag input:** no

### CRDC out-of-school suspensions, single-instance, by race × sex
- **MongoDB field path:** `discipline.crdc.oss_single`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** OSS single-instance counts by race × sex
- **Data type:** count
- **Suppression handling:** standard CRDC
- **Currently compared against:** feeds disparity ratio (sum of ISS + OSS_single + OSS_multiple at `12_compute_ratios.py:65-71`)
- **Flag output:** indirectly via `discipline_disparity` flag
- **Coverage:** ~89% (parallels iss)
- **Used as flag input:** yes

### CRDC OSS single-instance for IDEA students
- **MongoDB field path:** `discipline.crdc.oss_single_idea`
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Used as flag input:** no

### CRDC OSS multiple-instances by race × sex
- **MongoDB field path:** `discipline.crdc.oss_multiple`
- **Source dataset:** CRDC 2021-22
- **Currently compared against:** feeds disparity ratio
- **Flag output:** indirectly via disparity flag
- **Used as flag input:** yes

### CRDC OSS multiple-instances for IDEA students
- **MongoDB field path:** `discipline.crdc.oss_multiple_idea`
- **Currently compared against:** **not compared**
- **Used as flag input:** no

### CRDC out-of-school instances totals (non-disability / IDEA / 504)
- **MongoDB field paths:** `discipline.crdc.oos_instances_wodis`, `oos_instances_idea`, `oos_instances_504`
- **Source dataset:** CRDC 2021-22
- **Data type:** count (single integer, not race-broken-out)
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Used as flag input:** no

### CRDC expulsions (with educational services / without / zero-tolerance) by race × sex
- **MongoDB field paths:** `discipline.crdc.expulsion_with_ed`, `expulsion_without_ed`, `expulsion_zero_tolerance`
- **Source dataset:** CRDC 2021-22
- **Data type:** count by race × sex
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Used as flag input:** no

### CRDC corporal-punishment indicator
- **MongoDB field path:** `discipline.crdc.corporal_punishment_indicator`
- **Data type:** boolean
- **Currently compared against:** **not compared**
- **Coverage:** ~89%

### Restraint/seclusion (mechanical / physical / seclusion × no-disability / IDEA / 504)
- **MongoDB field path:** `safety.restraint_seclusion.{mechanical,physical,seclusion}_{wodis,idea,504}`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** Mechanical/physical restraint and seclusion incident counts
- **Data type:** count (integer)
- **Suppression handling:** standard CRDC
- **Currently compared against:** **not compared** — no flag, no percentile
- **Flag output:** none
- **Threshold values:** n/a
- **Coverage:** 2,247 schools (88.7%)
- **Used in regression as:** not used
- **Used as flag input:** no

### Law-enforcement referrals and arrests (by race × sex)
- **MongoDB field paths:** `safety.referrals_arrests.referrals`, `safety.referrals_arrests.arrests`
- **Source dataset:** CRDC 2021-22
- **Data type:** count by race × sex
- **Suppression handling:** standard CRDC
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** 2,260 schools (89.3%)
- **Used as flag input:** no

### Harassment / bullying allegations by basis
- **MongoDB field path:** `safety.harassment_bullying.allegations_{sex,race,disability,religion,orientation}`
- **Source dataset:** CRDC 2021-22
- **Data type:** count (integer per category)
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** 2,299 schools (90.8%)
- **Used as flag input:** no

### Firearm / homicide indicators
- **MongoDB field paths:** `safety.offenses.firearm_indicator`, `safety.offenses.homicide_indicator`
- **Source dataset:** CRDC 2021-22
- **Data type:** boolean
- **Currently compared against:** **not compared**
- **Coverage:** ~89%

### Comparison engine treatment summary — Climate and discipline

| Treatment | Metrics |
|---|---|
| **Produces a flag** | `discipline_disparity` (max ratio across non-white groups vs. white baseline) |
| **Produces a percentile** | OSPI discipline rate, chronic absenteeism (derived) |
| **Computed but not surfaced** | IDEA-specific discipline tracks (ISS_IDEA, OSS_IDEA), 504 OSS, expulsions, restraint/seclusion (all categories), referrals/arrests, harassment/bullying allegations, firearm/homicide indicators, corporal-punishment indicator |
| **Placeholder / unused** | none in this section |

The asymmetric coverage is striking: the engine ingests the full CRDC discipline & safety surface (88-90% coverage on most fields) but actively surfaces only the disparity ratio. Restraint/seclusion data — explicitly named in foundation.md Risk 3 as "needing extra caveat language" — is in the database with no flag wired up.

---

## 3. Staffing metrics

### Total teacher FTE
- **MongoDB field path:** `staffing.teacher_fte_total`
- **Source dataset:** CRDC 2021-22 (note: the CRDC vintage is older than the OSPI fields)
- **Source column(s):** Total teacher FTE
- **Data type:** decimal (FTE count)
- **Suppression handling:** null when CRDC suppressed
- **Currently compared against:** denominator of `derived.student_teacher_ratio`
- **Flag output:** no flag of its own
- **Coverage:** 2,359 schools (93.2%)
- **Used in regression as:** not used
- **Used as flag input:** indirectly (denominator of ratio)

### Certified vs. not-certified teacher FTE
- **MongoDB field paths:** `staffing.teacher_fte_certified`, `staffing.teacher_fte_not_certified`
- **Source dataset:** CRDC 2021-22
- **Data type:** decimal FTE
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** ~93%

### Counselor FTE
- **MongoDB field path:** `staffing.counselor_fte`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** School counselor FTE
- **Data type:** decimal FTE
- **Suppression handling:** null when suppressed; explicit zero is preserved (zero counselors = 0.0, not null) — this distinction drives the `no_counselor` binary flag
- **Currently compared against:** denominator of `derived.counselor_student_ratio`; basis of `no_counselor` flag
- **Flag output:** `no_counselor` flag (binary red when FTE = 0)
- **Threshold values:** `condition: equals_zero` at `flag_thresholds.yaml:256`
- **Coverage:** 2,359 schools (93.2%)
- **Used as flag input:** yes (no_counselor + counselor ratio)

### Nurse / psychologist / social worker FTE
- **MongoDB field paths:** `staffing.nurse_fte`, `staffing.psychologist_fte`, `staffing.social_worker_fte`
- **Source dataset:** CRDC 2021-22
- **Data type:** decimal FTE
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** 2,360 schools (93.2%)
- **Used as flag input:** no

### School resource officer (SRO) and security guard FTE
- **MongoDB field paths:** `staffing.sro_fte`, `staffing.security_guard_fte`
- **Source dataset:** CRDC 2021-22
- **Data type:** decimal FTE
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** 2,337 schools (92.3%)
- **Used as flag input:** no

### Comparison engine treatment summary — Staffing

| Treatment | Metrics |
|---|---|
| **Produces a flag** | `counselor_ratio` (yellow 400:1, red 500:1), `no_counselor` (binary red on zero FTE) |
| **Produces a percentile** | `student_teacher_ratio`, `counselor_student_ratio` |
| **Computed but not surfaced** | Certified vs. uncertified teacher split, nurse FTE, psychologist FTE, social worker FTE, SRO FTE, security guard FTE |

Foundation.md "Counselor-to-student ratio > 1:400 = yellow, > 1:500 = red" is implemented faithfully. Foundation also names "teacher certification" as a quality signal — the data is in MongoDB but no rule derives anything from it.

---

## 4. Resource and access metrics

### Per-pupil expenditure (total / local / state / federal)
- **MongoDB field paths:** `finance.per_pupil_total`, `finance.per_pupil_local`, `finance.per_pupil_state`, `finance.per_pupil_federal`
- **Source dataset:** OSPI School Apportionment & Finance Services (SAFS / Per-Pupil Expenditure 2023-24)
- **Source column(s):** Per-pupil expenditure totals; FTE-weighted decimal enrollment is the denominator
- **Data type:** dollar amount (decimal)
- **Suppression handling:** null when source unavailable
- **Currently compared against:** state / district / peer percentile (`per_pupil_total` only; sub-components are descriptive)
- **Flag output:** none — no PPE flag exists
- **Threshold values:** none
- **Coverage:** 2,433 schools (96.1%)
- **Used in regression as:** not used
- **Used as flag input:** no

### AP indicator
- **MongoDB field path:** `course_access.ap.indicator`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** School offers AP courses (yes/no)
- **Data type:** boolean
- **Currently compared against:** **not compared**
- **Flag output:** none
- **Coverage:** 2,360 schools (93.2%)
- **Used as flag input:** no

### AP enrollment by race × sex
- **MongoDB field path:** `course_access.ap.enrollment_by_race`
- **Source dataset:** CRDC 2021-22
- **Data type:** count by race × sex
- **Currently compared against:** **not compared** — no AP-access disparity ratio computed despite the data being present
- **Flag output:** none
- **Coverage:** populated where indicator=true
- **Used as flag input:** no

### Dual-enrollment indicator
- **MongoDB field path:** `course_access.dual_enrollment.indicator`
- **Source dataset:** CRDC 2021-22
- **Data type:** boolean
- **Currently compared against:** **not compared**
- **Coverage:** 2,360 schools (93.2%)

### Dual-enrollment by race × sex
- **MongoDB field path:** `course_access.dual_enrollment.enrollment_by_race`
- **Source dataset:** CRDC 2021-22
- **Data type:** count by race × sex
- **Currently compared against:** **not compared**

### Gifted-and-talented indicator
- **MongoDB field path:** `course_access.gifted_talented.indicator`
- **Source dataset:** CRDC 2021-22
- **Data type:** boolean
- **Currently compared against:** **not compared**
- **Coverage:** 2,360 schools (93.2%)

### Gifted-and-talented enrollment by race × sex
- **MongoDB field path:** `course_access.gifted_talented.enrollment_by_race`
- **Source dataset:** CRDC 2021-22
- **Data type:** count by race × sex
- **Currently compared against:** **not compared**

### Comparison engine treatment summary — Resource and access

| Treatment | Metrics |
|---|---|
| **Produces a flag** | None |
| **Produces a percentile** | per-pupil-total only |
| **Computed but not surfaced** | per-pupil sub-components (local / state / federal); AP indicator and enrollment-by-race; dual-enrollment indicator and enrollment-by-race; gifted-and-talented indicator and enrollment-by-race |

This section is the largest gap between data ingested and rules computed. Foundation.md names "AP/IB access and enrollment gaps" as a CRDC value-add and "SPED inclusion rates" as another — neither is touched by any rule. The AP enrollment-by-race data could in principle drive an access-disparity ratio analogous to the discipline disparity ratio; it currently doesn't.

---

## 5. Demographic and contextual fields

### Total enrollment
- **MongoDB field path:** `enrollment.total`
- **Source dataset:** NCES CCD Membership 2023-24 (primary)
- **Source column(s):** Total student count
- **Data type:** count (integer)
- **Suppression handling:** null when CCD suppressed; some schools show zero, treated as closed/dormant per `school_exclusions.yaml:347-369`
- **Currently compared against:** descriptive (used as numerator of student-teacher and counselor-student ratios; used to assign `enrollment_band`)
- **Flag output:** no direct flag
- **Threshold values:** Small ≤200, Medium 201–500, Large 501+ (`flag_thresholds.yaml:14-23`)
- **Coverage:** 2,532 schools (100%)
- **Used in regression as:** not used directly
- **Used as flag input:** indirectly (peer cohort assignment, ratio denominators)

### Enrollment by race
- **MongoDB field paths:** `enrollment.by_race.{american_indian,asian,black,hispanic,pacific_islander,two_or_more,white,not_specified}`
- **Source dataset:** NCES CCD Membership 2023-24
- **Data type:** count
- **Currently compared against:** descriptive only
- **Flag output:** none
- **Coverage:** ~100%
- **Used as flag input:** no

### Enrollment by sex
- **MongoDB field paths:** `enrollment.by_sex.{male,female}`
- **Source dataset:** NCES CCD Membership 2023-24
- **Data type:** count
- **Currently compared against:** descriptive only

### CRDC enrollment by race
- **MongoDB field path:** `enrollment.crdc_by_race`
- **Source dataset:** CRDC 2021-22
- **Source column(s):** SCH_ENR_HI_M, SCH_ENR_AM_M, etc.
- **Data type:** count
- **Currently compared against:** denominator in disparity ratio (suspension count / enrolled count); minimum 10 students per race required at `pipeline/12_compute_ratios.py:77`
- **Flag output:** indirectly via disparity flag
- **Coverage:** 2,275 schools (89.8%)
- **Used as flag input:** yes (disparity ratio denominator)

### CRDC total enrollment
- **MongoDB field path:** `enrollment.crdc_total`
- **Source dataset:** CRDC 2021-22
- **Data type:** count
- **Currently compared against:** descriptive only

### FRL count and percentage
- **MongoDB field paths:** `demographics.frl_count`, `demographics.frl_pct`
- **Source dataset:** OSPI Enrollment 2023-24 ("Low Income" — note: NOT from CCD, per builder's data decisions)
- **Source column(s):** Low Income count and rate
- **Data type:** count + percentage (decimal 0.0–1.0)
- **Suppression handling:** null when N<10 or "*"
- **Currently compared against:** **independent variable in the FRL regression**; assigns `frl_band`; documented limitation re: CEP-inflated percentages (harm register)
- **Flag output:** drives `performance_flag` via regression
- **Threshold values:** band edges LowFRL ≤0.35, MidFRL 0.36–0.65, HighFRL 0.66–1.00 (`flag_thresholds.yaml:25-34`)
- **Coverage:** 2,380 schools (94.0%)
- **Used in regression as:** **independent variable** (the predictor)
- **Used as flag input:** yes (performance flag, peer cohort)

### ELL count
- **MongoDB field path:** `demographics.ell_count`
- **Source dataset:** OSPI Enrollment 2023-24
- **Data type:** count
- **Currently compared against:** **not compared**
- **Coverage:** 2,445 schools (96.6%)
- **Used as flag input:** no

### SPED count
- **MongoDB field path:** `demographics.sped_count`
- **Source dataset:** OSPI Enrollment 2023-24
- **Data type:** count
- **Currently compared against:** **not compared**
- **Coverage:** 2,445 schools (96.6%)
- **Used as flag input:** no

### Section 504 count
- **MongoDB field path:** `demographics.section_504_count`
- **Source dataset:** OSPI Enrollment 2023-24
- **Data type:** count
- **Currently compared against:** **not compared**
- **Coverage:** 2,445 schools (96.6%)
- **Used as flag input:** no

### Foster care, homeless, migrant counts
- **MongoDB field paths:** `demographics.foster_care_count`, `demographics.homeless_count`, `demographics.migrant_count`
- **Source dataset:** OSPI Enrollment 2023-24
- **Data type:** count
- **Currently compared against:** **not compared**
- **Coverage:** ~96%
- **Used as flag input:** no

### School level (CCD-derived)
- **MongoDB field path:** `level`
- **Source dataset:** NCES CCD Directory 2023-24
- **Source column(s):** LEVEL
- **Data type:** categorical (Elementary / Middle / High / Secondary / Other / Prekindergarten)
- **Currently compared against:** mapped to `level_group` for regression and peer cohort
- **Flag output:** drives regression group assignment and peer cohort
- **Threshold values:** mapping at `flag_thresholds.yaml:39-45` (Secondary→High; Other and Prekindergarten→Other)
- **Coverage:** 100%
- **Used in regression as:** grouping variable (per-level model when n≥30)
- **Used as flag input:** yes

### Grade span (low / high)
- **MongoDB field paths:** `grade_span.low`, `grade_span.high`
- **Source dataset:** NCES CCD Directory 2023-24
- **Source column(s):** GSLO, GSHI
- **Data type:** categorical (string grade codes "PK", "KG", "01"–"12")
- **Currently compared against:** descriptive only — but `grade_span_includes_tested()` at `pipeline/15_regression_and_flags.py` uses these to assign the `grade_span_not_tested` flag-absent reason
- **Flag output:** none directly; produces flag-absent reason codes
- **Coverage:** ~100%

### School type
- **MongoDB field path:** `school_type`
- **Source dataset:** NCES CCD Directory 2023-24
- **Source column(s):** SCH_TYPE
- **Data type:** categorical (Regular School / Alternative School / Special Education School / Career and Technical School)
- **Currently compared against:** drives regression-eligibility filter; non-Regular types excluded
- **Threshold values:** excluded set at `flag_thresholds.yaml:71-74` ("Alternative School", "Special Education School", "Career and Technical School")
- **Coverage:** 100%
- **Used as flag input:** yes (regression-eligibility gate; produces `school_type_not_comparable` absent reason)

### Is-charter flag
- **MongoDB field path:** `is_charter`
- **Source dataset:** NCES CCD Directory 2023-24
- **Data type:** boolean
- **Currently compared against:** **not compared** — no charter-specific rule
- **Coverage:** 100% (17 schools = true)

### District identity
- **MongoDB field paths:** `district.name`, `district.nces_id`
- **Source dataset:** NCES CCD
- **Currently compared against:** scope for district percentile (min district size 2 at `flag_thresholds.yaml:125`)
- **Used as flag input:** scope variable

### Address (street, city, state, zip)
- **MongoDB field path:** `address.{street,city,state,zip}`
- **Source dataset:** NCES CCD Directory 2023-24
- **Currently compared against:** descriptive only (no locale-based comparison)
- **Coverage:** 100%

### Comparison engine treatment summary — Demographic and contextual

| Treatment | Metrics |
|---|---|
| **Drives flags** | FRL % (regression independent variable + FRL band), school level (regression grouping + level group), school type (regression exclusion gate), enrollment total (peer cohort band), grade span (flag-absent reason) |
| **Used in peer cohort** | Level + enrollment band + FRL band — three-axis composite |
| **Computed but not surfaced** | Enrollment by race / by sex, ELL count, SPED count, Section 504 count, foster care / homeless / migrant counts, is-charter flag |

Demographic context drives the regression and the peer cohort but the *substantive* demographic counts (ELL, SPED, 504, homeless, foster, migrant) are ingested without ever being compared against anything. Foundation.md mentions "SPED inclusion rates" specifically as a CRDC value-add — no rule derives or compares it.

---

## 6. Recognition and community signals

**This entire section is a documentation-vs-implementation gap.** Foundation.md names DonorsChoose, US DOE Recognition Programs (Blue Ribbon, Green Ribbon, NBCT counts), local election data (levy/bond passage), Teacher of the Year nominees, and grant wins as project-defining strength signals. **None of these fields exist in the production MongoDB schema.** Confirmed empty:

| Foundation reference | MongoDB field | Coverage |
|---|---|---:|
| DonorsChoose projects | (none) | 0 |
| Blue Ribbon / Green Ribbon | (none) | 0 |
| NBCT counts | (none) | 0 |
| Levy / bond passage rates | (none) | 0 |
| Teacher of the Year recognitions | (none) | 0 |
| Other grants (Title IV-A, ESSER, etc.) | (none) | 0 |

What does exist as recognition-adjacent: the Phase 4 web-search enrichment surfaces these signals as text findings on `context.findings` and `district_context.findings` (see Phase 4 `prompts/context_enrichment_v1.txt:16` "awards_recognition" category). Phase 5 Layer 3 narrative writes them into prose. Neither output is a structured data field the comparison engine can compute over.

### Comparison engine treatment summary — Recognition and community signals

| Treatment | Metrics |
|---|---|
| **Produces a flag** | None |
| **Produces a percentile** | None |
| **Structured field present** | None — see Known Gaps |
| **Surfaced via narrative only** | Awards / recognitions / programs / community investment via Phase 4 Haiku enrichment + Phase 5 Sonnet narrative |

---

## 7. Computed/derived fields

### `derived.student_teacher_ratio`
- Computed: `enrollment.total / staffing.teacher_fte_total` at `pipeline/12_compute_ratios.py:144`
- Coverage: 2,266 (89.5%)
- Used: percentile metric (lower-is-better)

### `derived.counselor_student_ratio`
- Computed: `enrollment.total / staffing.counselor_fte` at `12_compute_ratios.py:153`
- Coverage: 1,785 (70.5%)
- Used: percentile metric (lower-is-better); flag input

### `derived.no_counselor`
- Computed: `staffing.counselor_fte == 0` at `12_compute_ratios.py:159`
- Type: boolean (true when zero, false when non-zero, null when source null)
- Coverage: 2,532 has the field; 567 schools (22.4%) are true
- Used: drives `no_counselor` red flag

### `derived.chronic_absenteeism_pct`
- Computed: `1.0 - academics.attendance.regular_attendance_pct` at `12_compute_ratios.py:169`
- Coverage: 1,961 (77.4%)
- Used: percentile metric; chronic_absenteeism flag input

### `derived.proficiency_composite`
- Computed: `(ela_proficiency_pct + math_proficiency_pct) / 2` at `12_compute_ratios.py:180`
- Coverage: 1,249 (49.3%)
- Used: dependent variable in FRL regression

### `derived.discipline_disparity` (object)
- Computed: per-race ratios `rate_for_race / rate_for_white` at `12_compute_ratios.py:101`
- Stored as `{race: ratio, ...}` for non-white races where enrollment ≥ 10
- Coverage: 1,300 (51.3%)
- Used: source for `discipline_disparity_max`

### `derived.discipline_disparity_max`
- Computed: max of the per-race ratio dict at `12_compute_ratios.py:108`
- Type: ratio (decimal)
- Coverage: 1,300 (51.3%)
- Used: drives `discipline_disparity` flag (yellow ≥2.0, red ≥3.0)

### `derived.discipline_disparity_max_race`
- Computed: argmax race name at `12_compute_ratios.py:108`
- Used: descriptive metadata on the disparity flag

### `derived.discipline_disparity_no_white_baseline`
- Computed: true when no white students enrolled or white suspension rate is zero at `12_compute_ratios.py:90`
- Type: boolean
- Used: explains why disparity is null

### `derived.level_group`
- Computed: lookup `level_groups[level]` at `13_assign_peer_groups.py:71`
- Maps Secondary→High, Prekindergarten→Other, Other→Other
- Used: regression grouping + peer cohort axis

### `derived.enrollment_band`
- Computed: `assign_band(enrollment.total, enrollment_bands)` at `13_assign_peer_groups.py:84`
- Values: Small / Medium / Large / null
- Used: peer cohort axis

### `derived.frl_band`
- Computed: `assign_band(demographics.frl_pct, frl_bands)` at `13_assign_peer_groups.py:90`
- Values: LowFRL / MidFRL / HighFRL / null
- Used: peer cohort axis

### `derived.peer_cohort`
- Computed: `f"{level_group}_{enrollment_band}_{frl_band}"` at `13_assign_peer_groups.py:96`
- Type: string concatenation; null when any axis is null
- Coverage: 2,323 (91.7%)
- Used: scope for peer-percentile computation (only when cohort has ≥5 schools with data per metric)

### `derived.percentiles.{metric_key}.{state,district,peer}`
- Computed at `pipeline/14_compute_percentiles.py:30` via `(count_below + 0.5*count_equal) / total * 100`, flipped for lower-is-better metrics
- Type: integer 0-100
- Eight metric_keys: ela_proficiency_pct, math_proficiency_pct, regular_attendance_pct, student_teacher_ratio, counselor_student_ratio, per_pupil_total, chronic_absenteeism_pct, discipline_rate
- District scope requires district size ≥ 2; peer scope requires cohort size ≥ 5
- Coverage varies by metric

### `derived.performance_flag`
- Values: outperforming / as_expected / underperforming / null
- Computed at `15_regression_and_flags.py:233-239`: zscore > 1.0 → outperforming; zscore < −1.0 → underperforming; otherwise as_expected
- Coverage: 1,145 (45.2%)
- Distribution: 152 outperforming, 831 as_expected, 162 underperforming, 1,387 null

### `derived.regression_predicted` / `regression_residual` / `regression_zscore` / `regression_group` / `regression_r_squared`
- Predicted: model.predict([[frl]]); residual: composite − predicted; zscore: residual / SD of residuals
- regression_group: which level model was used ("Elementary", "Middle", "High", or "statewide" fallback when level group has < 30 schools)
- Stored at `15_regression_and_flags.py:243-248`
- Coverage: 1,145 (parallels performance_flag)

### `derived.performance_flag_absent_reason`
- Values: school_type_not_comparable / grade_span_not_tested / suppressed_n_lt_10 / data_not_available
- Assigned at `15_regression_and_flags.py:411`
- Coverage: 1,387 (the schools with null performance_flag)

### `derived.flags.{flag_name}.color`
- Values: green / yellow / red / null
- Four flags: chronic_absenteeism, counselor_ratio, discipline_disparity, no_counselor
- Coverage varies; all four computed at `15_regression_and_flags.py:273-369`

### `derived.flags.{flag_name}.flag_absent_reason`
- Values: same four as performance_flag_absent_reason
- Assigned at `15_regression_and_flags.py:418`

### `derived.flags.{flag_name}.{raw_value, threshold, threshold_source, what_it_means, what_it_might_not_mean, parent_question}`
- Stored on red and yellow flags only; green flags get only color + raw_value
- Source: yaml metadata at `flag_thresholds.yaml:137-271`
- Same metadata text for every school at the same flag color (structured, not AI-generated)

### Comparison engine treatment summary — Computed/derived

| Treatment | Field |
|---|---|
| **Surfaced flag** | performance_flag, flags.chronic_absenteeism, flags.counselor_ratio, flags.discipline_disparity, flags.no_counselor |
| **Surfaced percentile** | derived.percentiles.* (8 metric keys × 3 scopes) |
| **Internal scaffolding** | level_group, enrollment_band, frl_band, peer_cohort, regression_group, regression_predicted, regression_residual, regression_zscore, regression_r_squared, discipline_disparity object, discipline_disparity_max_race, no_counselor boolean |

---

## A. Flag inventory

| Flag name | Input field(s) | Threshold or model | Output values | Reason codes for absent | File path |
|---|---|---|---|---|---|
| `performance_flag` | `demographics.frl_pct` (X), `derived.proficiency_composite` (Y) | Linear regression per `level_group` (n≥30) or statewide fallback; ±1.0 SD on residual zscore | outperforming / as_expected / underperforming / null | school_type_not_comparable / grade_span_not_tested / suppressed_n_lt_10 / data_not_available | `pipeline/15_regression_and_flags.py:91-266` |
| `chronic_absenteeism` | `derived.chronic_absenteeism_pct` | yellow >0.20, red >0.30 | green / yellow / red / null | grade_span_not_tested / suppressed_n_lt_10 / data_not_available | `pipeline/15_regression_and_flags.py:273-341` (config at `flag_thresholds.yaml:138-173`) |
| `counselor_ratio` | `derived.counselor_student_ratio` | yellow >400, red >500 | green / yellow / red / null | data_not_available (most common) | same script (config at `flag_thresholds.yaml:175-210`) |
| `discipline_disparity` | `derived.discipline_disparity_max` | yellow ≥2.0, red ≥3.0 | green / yellow / red / null | data_not_available / suppressed_n_lt_10 | same script (config at `flag_thresholds.yaml:212-250`) |
| `no_counselor` | `staffing.counselor_fte` | binary: equals zero → red | red / null (no green; absence of flag means non-zero counselor) | n/a (binary) | `pipeline/15_regression_and_flags.py:344-369` (config at `flag_thresholds.yaml:254-271`) |

Per-flag color distribution across the 2,532-school production set:

| Flag | green | yellow | red | null |
|---|---:|---:|---:|---:|
| performance_flag | 152 (outperforming) | 831 (as_expected) | 162 (underperforming) | 1,387 |
| chronic_absenteeism | 708 | 613 | 640 | 571 |
| counselor_ratio | 1,074 | 372 | 339 | 747 |
| discipline_disparity | 647 | 236 | 417 | 1,232 |
| no_counselor | n/a | n/a | 567 | 1,965 |

The chronic_absenteeism distribution (640 red, 613 yellow, 708 green) reflects the post-COVID baseline shift documented in `docs/harm_register.md` Phase 4 entry. The harm register flagged these thresholds for upward revision (candidate 30%/45%) before Phase 5 production; that revision was deferred.

---

## B. Regression model details

**Type:** scikit-learn `LinearRegression` per `flag_thresholds.yaml:61` (only this method supported).

**Dependent variable:** `derived.proficiency_composite` = `(ela_proficiency_pct + math_proficiency_pct) / 2`.

**Independent variable:** `demographics.frl_pct` (a single feature; this is a univariate regression).

**Per-level split:**
- Schools are bucketed by `derived.level_group` which is the result of `level_groups[ccd_level]` mapping at `flag_thresholds.yaml:39-45`.
- Mapping: Elementary→Elementary, Middle→Middle, High→High, **Secondary→High**, Other→Other, Prekindergarten→Other.
- The mapping puts comprehensive 6-12 / 7-12 / 9-12 secondary schools into the High group. **K-8 schools are mapped according to their CCD `LEVEL` value (most are coded as Elementary or Middle by CCD; the engine inherits whatever CCD assigns).** No special handling of K-8 or 6-12 grade spans beyond CCD's classification.
- Per-level model is fit only when level group has ≥30 schools (`min_group_size` at `flag_thresholds.yaml:58`). Smaller groups fall back to the statewide all-levels model.
- The "Other" level group (Prekindergarten + CCD-Other) is included in the statewide model when individual schools have FRL + composite data, but the Other group's per-level model is rarely fit (it's typically the smallest).

**Regression-readiness gate:** a school enters the regression IFF `frl_pct` is non-null AND `proficiency_composite` is non-null AND `level_group` is non-null AND `school_type` is NOT in {"Alternative School", "Special Education School", "Career and Technical School"} AND `_id` is NOT in `school_exclusions.yaml`. Non-ready schools are stripped of any prior regression output and assigned a flag-absent reason.

**Residual SD:** computed per level model (or statewide), as `np.std(actual − predicted)`.

**Z-score → flag mapping (at `15_regression_and_flags.py:234`):**
- `zscore > 1.0` → outperforming (foundation calls this 🟢)
- `zscore < -1.0` → underperforming (🔴)
- otherwise → as_expected (🟡)
- The 1.0 SD threshold is set at `flag_thresholds.yaml:54` and the comment notes "±1.0 gives roughly 15%/70%/15% distribution."

**Exclusion list size and categories:** `school_exclusions.yaml` contains 78 manually excluded schools across these documented categories:
- Virtual / online schools coded as "Regular School" in CCD: 26
- Jails and juvenile detention centers: 17
- Group homes and residential treatment facilities: 6
- Preschool and early-childhood programs: 10
- Homeschool partnerships: 3
- Community-based / youth services programs: 4
- Alternative / re-engagement programs miscoded as "Regular School": 6
- Special education programs miscoded as "Regular School": 3
- Tribal language immersion / culturally significant programs: 1
- Zero-enrollment / closed schools: 5

The list is appended to the auto-exclusions from CCD `school_type` ("Alternative School" 341, "Special Education School" 82, "Career and Technical School" 20). Together: ~520 schools never enter the regression.

**R² values:** stored per-school in `derived.regression_r_squared`. Per-level R² typically lands in the 0.55–0.70 range based on Fairhaven's stored value (0.663 for the Middle-school model).

---

## C. Peer cohort definition

**Construction:** `peer_cohort = f"{level_group}_{enrollment_band}_{frl_band}"` at `pipeline/13_assign_peer_groups.py:96`. Three-axis Cartesian product:
- **level_group:** Elementary / Middle / High / Other (Secondary collapses to High; Prekindergarten and CCD-Other collapse to Other).
- **enrollment_band:** Small (1–200) / Medium (201–500) / Large (501+).
- **frl_band:** LowFRL (0.00–0.35) / MidFRL (0.36–0.65) / HighFRL (0.66–1.00).

**Distance metric:** none. This is hard-bin assignment, not nearest-neighbor matching. Two schools are "peers" iff they share all three categorical bins.

**Cohort size:** A peer cohort can be as small as 1 (a school alone in its bin). Schools whose cohort has < 5 members with non-null data on a given metric receive null peer percentile for that metric (`flag_thresholds.yaml:126`).

**Coverage:** 2,323 schools (91.7%) have a non-null `peer_cohort`. The remaining 209 are missing because at least one axis is null (typically `frl_band` when FRL is suppressed, or `enrollment_band` when enrollment is zero/null).

**Use:** peer cohort is *only* used as a scope for percentile computation in `pipeline/14_compute_percentiles.py`. It is not used in regression, not used in flag thresholds, and not used to produce the "peer schools shown to parent" output the foundation document describes.

**"Peer schools shown to parent" output:** per the inventory above, **this output does not exist in the current data layer.** Foundation.md "Output: The Briefing" item 10 names "Peer schools: 3-5 schools serving similar populations, with the same metrics, for meaningful comparison" — there is no `derived.peer_schools` field, no nearest-neighbor matching, and no curated 3-5-school sibling list anywhere in the schema. The 3-axis hard-bin cohort serves percentile computation only.

**National benchmark:** foundation.md's "Comparison Engine" lists four benchmarks (district / state / national / demographic peers). The current engine implements three (state / district / peer cohort). **There is no national benchmark.** This is a known constraint of the WA-only Phase 1 launch — national CRDC ingestion is Phase 3 in the foundation roadmap.

---

## D. Known gaps

### Ingested-but-unused (data in MongoDB, no rule consumes it)

1. **Restraint and seclusion (CRDC).** `safety.restraint_seclusion.{mechanical,physical,seclusion}_{wodis,idea,504}` — 88.7% coverage. Foundation.md Risk 3 specifically calls these out as "needing extra caveat language and lower confidence presentation"; no flag, no percentile, no rule.
2. **Law-enforcement referrals and arrests (CRDC).** `safety.referrals_arrests.{referrals,arrests}` — 89.3% coverage by race × sex. Foundation references "school resource officer" as a CRDC value-add. No rule.
3. **Harassment / bullying allegations (CRDC).** `safety.harassment_bullying.allegations_{sex,race,disability,religion,orientation}` — 90.8% coverage. No rule.
4. **Expulsion counts (CRDC).** `discipline.crdc.expulsion_{with_ed,without_ed,zero_tolerance}` by race × sex — ~89% coverage. Foundation.md "Climate and discipline" surfaces "suspension rates by race and disability" but no expulsion-specific rule exists.
5. **IDEA-specific discipline tracks.** `discipline.crdc.{iss_idea,oss_single_idea,oss_multiple_idea}` — present but excluded from the disparity ratio (which uses only non-IDEA suspensions). No separate disability-disparity ratio.
6. **AP, dual-enrollment, gifted-and-talented access by race × sex.** `course_access.ap.enrollment_by_race`, `course_access.dual_enrollment.enrollment_by_race`, `course_access.gifted_talented.enrollment_by_race`. Foundation explicitly names "AP/IB access and enrollment gaps" as a CRDC value-add. No access-disparity rule analogous to the discipline-disparity one.
7. **AP / dual-enrollment / gifted indicators.** Booleans available; no flag fires on absence (no "AP not offered at this high school" flag, for instance).
8. **Growth (Student Growth Percentile) data.** `academics.growth.{ela,math}_median_sgp` and growth-tier counts — 57% coverage. Foundation.md "Output: The Briefing" item 2 says "Academics in context: Proficiency and growth scores benchmarked against district, state, and demographic peers." Growth is in the database but is not in the `percentile_metrics` list and feeds no flag.
9. **Science proficiency.** `academics.assessment.science_proficiency_pct` — 57% coverage. Not in regression composite (which is ELA + Math only); not in percentile metrics; not in any flag.
10. **Demographic counts.** `demographics.{ell_count,sped_count,section_504_count,foster_care_count,homeless_count,migrant_count}` — 96.6% coverage. None feeds any flag or percentile. Foundation specifically calls out "SPED inclusion rates" as a CRDC value-add.
11. **Staffing FTEs beyond teacher and counselor.** `staffing.{nurse,psychologist,social_worker,sro,security_guard}_fte` — 92-93% coverage. None used. Foundation describes the "counselor or only a police officer" choice as parent-relevant but no rule operationalizes the SRO-vs-counselor comparison.
12. **Per-pupil sub-components.** `finance.per_pupil_{local,state,federal}` — surfaced descriptively but no percentile or flag (only `per_pupil_total` is in `percentile_metrics`).
13. **Teacher certification split.** `staffing.teacher_fte_{certified,not_certified}`. Foundation lists "teacher certification" as a quality signal. No rule.
14. **Charter-school flag.** `is_charter` — 17 schools. No charter-specific rule or comparison.
15. **Corporal-punishment, firearm, homicide indicators.** Booleans on `discipline.crdc.corporal_punishment_indicator`, `safety.offenses.firearm_indicator`, `safety.offenses.homicide_indicator`. None used by any rule.

### Referenced-in-foundation-but-not-in-database

The foundation document's data layer description references several signals that have **no MongoDB field at all**:

16. **DonorsChoose data.** Foundation Architecture / "Strength signals" names DonorsChoose as a primary engagement signal. Confirmed empty: 0 documents have any donorschoose-related field.
17. **US DOE Recognition Programs.** Foundation references Blue Ribbon, Green Ribbon, NBCT counts as a structured data source. None of these has a MongoDB field; confirmed empty. (These signals do surface in Phase 4 narrative findings but as unstructured text, not comparable data.)
18. **Local election / levy / bond passage rates.** Foundation lists this as a "community investment signal" with county-auditor records as the source. No MongoDB field.
19. **Teacher of the Year / Milken Award / Presidential Award recognitions.** Foundation lists these as educator-recognition signals. No MongoDB field.
20. **Grant wins (Title IV-A, ESSER, 21st Century, Magnet School Assistance, etc.).** Foundation lists these as resource signals. No MongoDB field.
21. **Locale code (urban / suburban / rural).** Foundation describes "schools serving similar populations" and lists "locale" as a peer-matching dimension. The CCD locale code is **not stored** — `address` has street/city/state/zip but no locale classification. The peer cohort axes are level + enrollment + FRL only; locale is not used.
22. **Title I status.** Foundation references Title I as a peer-matching dimension. No `is_title_i` field exists.
23. **Suppression flags as separate field.** Foundation and CLAUDE.md require `null + suppressed: true` distinction. The codebase uses `is_suppressed()` reading `{field}_suppressed: true` as a separate adjacent field; this is implemented for OSPI assessment fields but **whether every suppressible field actually carries a parallel `_suppressed` boolean is not uniformly verified**. The diagnostic above showed flag-absent reason `suppressed_n_lt_10` is the assignment, but absence of the `_suppressed` adjacent field doesn't currently cause a different absent reason — `data_not_available` is the catch-all. Worth a dedicated audit.

### Code-vs-documentation discrepancies

24. **National benchmark.** Foundation.md "Comparison Engine" line "the system calculates where a school sits relative to four benchmarks: 1. Its own district 2. Its state 3. The national average 4. Schools with similar demographics." The code computes three: state, district, peer cohort. **The "national average" benchmark is not implemented.** This is consistent with the WA-only Phase 1 scope but the foundation language reads as if all four are computed today.
25. **"Peer schools" output.** Foundation.md "Output: The Briefing" item 10 — "Peer schools: 3-5 schools serving similar populations, with the same metrics, for meaningful comparison." The peer cohort exists as a scope for percentile computation; **a curated 3-5-school sibling list does not exist** in the schema. No nearest-neighbor matching is implemented.
26. **Chronic absenteeism thresholds.** Foundation.md and `flag_thresholds.yaml:140-141` use 20% / 30% (yellow/red). Harm register entry "Chronic absenteeism thresholds miscalibrated for post-COVID era" recommends 30% / 45% as the candidate replacement. **The replacement is not implemented in production** — production used 20%/30%, producing 640 red and 613 yellow on the current data.
27. **Discipline-disparity minimum-N.** `pipeline/12_compute_ratios.py:77` uses minimum 10 students per race subgroup. Harm register entry "Discipline disparity ratios unreliable at small subgroup sizes" recommends raising the minimum-N from 10 to 30. **Not implemented.** Production disparity ratios are computed at the 10-student threshold.
28. **`oos_instances_504`.** Field name in MongoDB is `oos_instances_504` (note: oos vs oss elsewhere). The disparity ratio code at `12_compute_ratios.py:55` ignores this field; only ISS, OSS_single, OSS_multiple feed the disparity. May be intentional (504 students get separate framework) but undocumented.

### Rule-level gaps from the editorial-rule audit (2026-05-02) that intersect Phase 3R

29. **Non-traditional school narrative framing.** The harm register Phase 5 entry calls for school-type branching in narrative. The Phase 3 engine *excludes* non-traditional types from the regression (good, structural), but does not produce flags-with-narrative-modifier metadata indicating "this school is excluded for reason X — the parent should expect a different briefing structure." The narrative layer currently inherits this gap.
30. **Three-layer trust model.** The harm register Phase 5 entry "Three-layer trust model" calls for clear distinction between (1) verified data presented visually, (2) narrative interpretation of verified data only, (3) web-sourced findings clearly labeled with LLM/web disclaimer. Layer 3 (web-sourced) implements per-paragraph citations as part of this. Layer 2 (narrative interpretation of verified data — i.e., narrative around the comparison engine's outputs) **has not begun**; the Phase 3 engine produces the structured flags but no "Layer 2" narrative is generated from them. Phase 3R formalization should specify the Layer 2 contract before that work begins.

---

*Read-only investigation. No code modified. No prompts modified. No data modified. Future Phase 3R artifacts (product spec, methodology review brief, threshold-revision plan) will live in this same `phases/phase-3R/` directory.*
