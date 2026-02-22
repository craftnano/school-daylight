# Phase 3 — Fairhaven Field-by-Field Test (Live MongoDB)

**Generated:** 2026-02-22T05:20:23.312913+00:00
**Source:** MongoDB Atlas, collection 'schools', _id='530042000104'

## Identity

- **_id:** 530042000104
- **name:** Fairhaven Middle School
- **district:** Bellingham School District
- **level:** Middle

## Derived Ratios

- **student_teacher_ratio:** 17.5
- **counselor_student_ratio:** 294.0
- **chronic_absenteeism_pct:** 0.3997
- **proficiency_composite:** 0.599
- **no_counselor:** False

## Discipline Disparity

- **disparity_max:** 3.05
- **disparity_max_race:** black
- **asian:** 0.0
- **black:** 3.05
- **hispanic:** 1.11
- **two_or_more:** 2.0

## Peer Group

- **level_group:** Middle
- **enrollment_band:** Large
- **frl_band:** MidFRL
- **peer_cohort:** Middle_Large_MidFRL

## Performance Regression

- **performance_flag:** outperforming
- **regression_zscore:** 1.37
- **regression_predicted:** 0.4664
- **regression_residual:** 0.1326
- **regression_group:** Middle
- **regression_r_squared:** 0.663

## Percentiles

- **chronic_absenteeism_pct:** state=13, district=6, peer=6
- **counselor_student_ratio:** state=69, district=64, peer=73
- **discipline_rate:** state=35, district=26, peer=85
- **ela_proficiency_pct:** state=77, district=81, peer=95
- **math_proficiency_pct:** state=74, district=89, peer=94
- **per_pupil_total:** state=36, district=34, peer=58
- **regular_attendance_pct:** state=13, district=6, peer=6
- **student_teacher_ratio:** state=35, district=27, peer=62

## Climate & Equity Flags

### chronic_absenteeism
- **color:** red
- **raw_value:** 0.3997
- **threshold:** 0.3

### counselor_ratio
- **color:** green
- **raw_value:** 294.0

### discipline_disparity
- **color:** red
- **raw_value:** 3.05
- **threshold:** 3.0

## CRDC Enrollment by Race

- **american_indian:** 3
- **asian:** 31
- **black:** 14
- **hispanic:** 77
- **pacific_islander:** 3
- **two_or_more:** 64
- **white:** 427
- **total:** 619
