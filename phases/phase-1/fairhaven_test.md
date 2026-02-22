# Fairhaven Middle School — Cross-Source Join Test

**Date:** 2026-02-21
**Purpose:** Prove that Fairhaven Middle School can be found in ALL data sources and that the join chain works. This is the golden school — if Fairhaven fails, nothing ships.

---

## School Identity

| Field | Value |
|-------|-------|
| School Name | Fairhaven Middle School |
| District | Bellingham School District |
| City | Bellingham, WA 98225 |
| NCES ID | 530042000104 |
| OSPI SchoolCode | 2066 |
| OSPI DistrictCode | 37501 |
| CCD ST_SCHID | WA-37501-2066 |
| CRDC COMBOKEY | 530042000104 |
| School Type | Regular School |
| Level | Middle |
| Grade Span | 06–08 |
| Charter | No |

---

## Join Verification

| Source | ID Used | Found? | Status |
|--------|---------|--------|--------|
| CCD Directory (2024-25) | NCESSCH = 530042000104 | YES | Open |
| CCD Membership (2024-25) | NCESSCH = 530042000104 | YES | 588 total enrollment |
| CRDC Enrollment (2021-22) | COMBOKEY = 530042000104 | YES | Found in all 13 CRDC files |
| OSPI Enrollment (2023-24) | DistrictCode=37501, SchoolCode=2066 | YES | 585 total |
| OSPI Assessment (2023-24) | DistrictCode=37501, SchoolCode=2066 | YES | Proficiency data present |
| OSPI Discipline (2023-24) | DistrictCode=37501, SchoolCode=2066 | YES | After comma-stripping |
| OSPI Growth (2023-24) | DistrictCode=37501, SchoolCode=2066 | YES | SGP data present |
| OSPI SQSS (2024-25) | DistrictCode=37501, SchoolCode=2066 | YES | Regular attendance data |
| OSPI PPE (2023-24) | SchoolCode=2066 | YES | PPE data present |

**Join chain verified:**
- CCD NCESSCH `530042000104` == CRDC COMBOKEY `530042000104` ✓
- CCD ST_SCHID `WA-37501-2066` → parsed DistrictCode `37501`, SchoolCode `2066` == OSPI codes ✓

---

## Sample Values Cross-Check

These values were read directly from the raw source files and mapped to schema fields.

### Enrollment

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| enrollment.total | CCD Membership 2024-25 | **588** | NCESSCH=530042000104, TOTAL_INDICATOR='Education Unit Total' |
| enrollment.by_race.white | CCD Membership 2024-25 | **393** | Sum of M=206 + F=187 from race subtotal |
| enrollment.by_race.hispanic | CCD Membership 2024-25 | **91** | Sum of M=47 + F=44 |
| enrollment.by_race.two_or_more | CCD Membership 2024-25 | **55** | Sum of M=33 + F=22 |
| enrollment.by_race.asian | CCD Membership 2024-25 | **33** | Sum of M=15 + F=18 |
| enrollment.by_race.black | CCD Membership 2024-25 | **8** | Sum of M=6 + F=2 |
| enrollment.by_race.american_indian | CCD Membership 2024-25 | **5** | Sum of M=4 + F=1 |
| enrollment.by_race.pacific_islander | CCD Membership 2024-25 | **2** | Sum of M=2 + F=0 |
| enrollment.by_sex.female | CCD Membership 2024-25 | **274** | Sum of female counts across races |
| enrollment.by_sex.male | CCD Membership 2024-25 | **313** | Sum of male counts across races |

### Demographics (from OSPI)

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| demographics.frl_count | OSPI Enrollment 2023-24 | **257** | SchoolCode=2066, column 'Low Income' |
| demographics.frl_pct | Derived | **0.439** | 257 / 585 = 0.4393 |
| demographics.ell_count | OSPI Enrollment 2023-24 | **35** | column 'English Language Learners' |
| demographics.sped_count | OSPI Enrollment 2023-24 | **98** | column 'Students with Disabilities' |
| demographics.section_504_count | OSPI Enrollment 2023-24 | **49** | column 'Section 504' |
| demographics.homeless_count | OSPI Enrollment 2023-24 | **40** | column 'Homeless' |

### Academics

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| academics.assessment.ela_proficiency_pct | OSPI Assessment 2023-24 | **0.649** | TestSubject='ELA', StudentGroupType='All', GradeLevel='All Grades', value='64.90%' |
| academics.assessment.math_proficiency_pct | OSPI Assessment 2023-24 | **0.549** | TestSubject='Math', value='54.90%' |
| academics.assessment.science_proficiency_pct | OSPI Assessment 2023-24 | **0.655** | TestSubject='Science', value='65.50%' |
| academics.growth.ela_median_sgp | OSPI Growth 2023-24 | **61.0** | Subject='English Language Arts', GradeLevel='All Grades' |
| academics.growth.math_median_sgp | OSPI Growth 2023-24 | **68.0** | Subject='Math', GradeLevel='All Grades' |
| academics.attendance.regular_attendance_pct | OSPI SQSS 2024-25 | **0.6003** | Measure='Regular Attendance', GradeLevel='All Grades' |

### Discipline

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| discipline.ospi.rate | OSPI Discipline 2023-24 | **0.0455** | Student Group='All Students', GradeLevel='All', value='4.55%' |
| discipline.ospi.numerator | OSPI Discipline 2023-24 | **28** | Same row |
| discipline.ospi.denominator | OSPI Discipline 2023-24 | **615** | Same row |
| discipline.crdc.iss (sample) | CRDC Suspensions 2021-22 | **WH_M=5, BL_M=1, HI_M=1** | COMBOKEY=530042000104, SCH_DISCWODIS_ISS_* columns |

### Staffing (from CRDC 2021-22)

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| staffing.teacher_fte_total | CRDC School Support | **33.6** | SCH_FTETEACH_TOT |
| staffing.teacher_fte_certified | CRDC School Support | **33.6** | SCH_FTETEACH_CERT (all certified) |
| staffing.counselor_fte | CRDC School Support | **2.0** | SCH_FTECOUNSELORS |
| staffing.psychologist_fte | CRDC School Support | **0.79** | SCH_FTESERVICES_PSY |
| staffing.sro_fte | CRDC School Support | **0.0** | SCH_FTESECURITY_LEO |

### Finance

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| finance.per_pupil_total | OSPI PPE 2023-24 | **17,778.96** | SchoolCode=2066, Total_PPE |
| finance.per_pupil_local | OSPI PPE 2023-24 | **4,399.50** | Local PPE |
| finance.per_pupil_state | OSPI PPE 2023-24 | **13,065.69** | State PPE |
| finance.per_pupil_federal | OSPI PPE 2023-24 | **313.78** | Federal PPE |

### Safety (from CRDC 2021-22)

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| safety.restraint_seclusion.physical_idea | CRDC R&S | **17** | SCH_RSINSTANCES_PHYS_IDEA |
| safety.restraint_seclusion.seclusion_idea | CRDC R&S | **14** | SCH_RSINSTANCES_SECL_IDEA |
| safety.harassment_bullying.allegations_sex | CRDC Harassment | **2** | SCH_HBALLEGATIONS_SEX |
| safety.harassment_bullying.allegations_race | CRDC Harassment | **2** | SCH_HBALLEGATIONS_RAC |
| safety.harassment_bullying.allegations_disability | CRDC Harassment | **3** | SCH_HBALLEGATIONS_DIS |

### Course Access (from CRDC 2021-22)

| Schema Field | Source | Source Value | Raw Location |
|-------------|--------|-------------|--------------|
| course_access.gifted_talented.indicator | CRDC Gifted | **true** | SCH_GT_IND = 'Yes' |
| course_access.ap.indicator | CRDC AP | **false** | All AP columns = -9 (not applicable for middle school) |

---

## Enrollment Cross-Check Across Sources

| Source | Year | Enrollment | Notes |
|--------|------|-----------|-------|
| CCD Membership | 2024-25 | 588 | Newest, most authoritative |
| OSPI Enrollment | 2023-24 | 585 | One year older, slightly lower |
| OSPI PPE | 2023-24 | 574.38 | FTE-weighted, not headcount |
| CRDC Enrollment | 2021-22 | Sum of race columns | Oldest, 3+ years old |

The 3-student difference between CCD (588) and OSPI (585) is expected — different school years. The PPE enrollment (574.38) uses a different calculation method (FTE-weighted). These are not errors.

---

## Verdict

**Fairhaven Middle School joins successfully across ALL data sources.**

- CCD Directory: ✓ Found
- CCD Membership: ✓ Found (588 enrollment)
- CRDC (all 13 files): ✓ Found
- OSPI Enrollment: ✓ Found (585 enrollment, FRL=257)
- OSPI Assessment: ✓ Found (ELA 64.9%, Math 54.9%)
- OSPI Discipline: ✓ Found (4.55% rate, after comma-stripping)
- OSPI Growth: ✓ Found (ELA SGP=61, Math SGP=68)
- OSPI SQSS: ✓ Found (Regular attendance 60.03%)
- OSPI PPE: ✓ Found ($17,778.96 total)

**25+ field values cross-checked from raw source files to schema fields. All match.**
