# Phase 3R — Schema Check & Homelessness Verification

Run date (UTC): **2026-05-04T18:20:36.032489Z**
Database: **`schooldaylight_experiment`** (read-only this session)
Document count: **2532**
Sample size for schema enumeration (Task 2): **50**
Log file: `/Users/oriandaleigh/school-daylight/logs/schema_check_2026-05-04_11-20-26.log`

This is a read-only inspection. No documents were modified. The isolation guard `assert "experiment" in db.name` passed at the top of the run.

## 1. Schema enumeration (Task 2)

Random sample of 50 documents walked recursively. Numeric stats below are computed from the sample only; full-collection stats for v1 variables are in the next section.

Top-level field paths in the sample, with type distribution, presence count (out of 50), and null count:

| path | present (of 50) | null (of 50) | types seen |
|---|---|---|---|
| _id | 50 | 0 | str×50 |
| academics | 41 | 0 | dict×41 |
| address | 50 | 0 | dict×50 |
| census_acs | 50 | 0 | dict×50 |
| context | 32 | 0 | dict×32 |
| course_access | 48 | 0 | dict×48 |
| demographics | 48 | 0 | dict×48 |
| derived | 50 | 0 | dict×50 |
| discipline | 50 | 0 | dict×50 |
| district | 50 | 0 | dict×50 |
| district_context | 50 | 0 | dict×50 |
| enrollment | 50 | 0 | dict×50 |
| finance | 49 | 0 | dict×49 |
| grade_span | 50 | 0 | dict×50 |
| is_charter | 50 | 0 | bool×50 |
| layer3_narrative | 50 | 0 | dict×50 |
| level | 50 | 0 | str×50 |
| metadata | 50 | 0 | dict×50 |
| name | 50 | 0 | str×50 |
| phone | 50 | 0 | str×50 |
| safety | 48 | 0 | dict×48 |
| school_type | 50 | 0 | str×50 |
| staffing | 48 | 0 | dict×48 |
| website | 50 | 0 | str×50 |

Numeric-typed paths discovered in the sample, with sample-only stats:

| path | n_in_sample | min | max | mean | median |
|---|---|---|---|---|---|
| academics.assessment.ela_proficiency_pct | 38 | 0.1250 | 0.9100 | 0.5048 | 0.5010 |
| academics.assessment.ela_students_tested | 41 | 34.0000 | 1,108.0000 | 294.8537 | 219.0000 |
| academics.assessment.math_proficiency_pct | 33 | 0.0820 | 0.8830 | 0.4383 | 0.4170 |
| academics.assessment.math_students_tested | 41 | 35.0000 | 1,109.0000 | 295.1951 | 220.0000 |
| academics.assessment.science_proficiency_pct | 26 | 0.0680 | 0.8700 | 0.5104 | 0.5530 |
| academics.assessment.science_students_tested | 36 | 25.0000 | 425.0000 | 119.4722 | 85.0000 |
| academics.attendance.denominator | 41 | 29.0000 | 1,364.0000 | 488.9756 | 483.0000 |
| academics.attendance.numerator | 41 | 17.0000 | 1,009.0000 | 387.5610 | 370.0000 |
| academics.attendance.regular_attendance_pct | 41 | 0.4545 | 0.9492 | 0.7631 | 0.7884 |
| academics.dual_credit.denominator | 6 | 95.0000 | 1,365.0000 | 370.0000 | 168.0000 |
| academics.dual_credit.numerator | 6 | 11.0000 | 1,233.0000 | 300.3333 | 126.0000 |
| academics.dual_credit.pct | 6 | 0.0692 | 0.9127 | 0.6700 | 0.7848 |
| academics.growth.ela_high_growth_count | 37 | 4.0000 | 371.0000 | 75.7027 | 40.0000 |
| academics.growth.ela_low_growth_count | 37 | 4.0000 | 370.0000 | 84.3243 | 45.0000 |
| academics.growth.ela_median_sgp | 37 | 28.0000 | 67.0000 | 49.0541 | 49.0000 |
| academics.growth.ela_typical_growth_count | 37 | 11.0000 | 369.0000 | 80.8378 | 48.0000 |
| academics.growth.math_high_growth_count | 37 | 12.0000 | 417.0000 | 79.5405 | 46.0000 |
| academics.growth.math_low_growth_count | 37 | 5.0000 | 412.0000 | 82.1081 | 42.0000 |
| academics.growth.math_median_sgp | 37 | 26.0000 | 69.0000 | 50.2432 | 50.0000 |
| academics.growth.math_typical_growth_count | 37 | 9.0000 | 340.0000 | 78.7297 | 44.0000 |
| academics.ninth_grade_on_track.denominator | 5 | 24.0000 | 82.0000 | 46.0000 | 44.0000 |
| academics.ninth_grade_on_track.numerator | 5 | 21.0000 | 61.0000 | 34.8000 | 32.0000 |
| academics.ninth_grade_on_track.pct | 5 | 0.7143 | 0.8750 | 0.7734 | 0.7439 |
| census_acs.bachelors_or_higher_pct_25plus.moe | 50 | 0.6000 | 8.3000 | 2.7300 | 2.2000 |
| census_acs.bachelors_or_higher_pct_25plus.value | 50 | 4.7000 | 78.8000 | 36.5040 | 34.2000 |
| census_acs.gini_index.moe | 50 | 0.0046 | 0.1235 | 0.0277 | 0.0213 |
| census_acs.gini_index.value | 50 | 0.3669 | 0.5151 | 0.4319 | 0.4301 |
| census_acs.labor_force_participation_rate_16plus.moe | 50 | 0.4000 | 8.3000 | 2.6740 | 1.8000 |
| census_acs.labor_force_participation_rate_16plus.value | 50 | 42.1000 | 76.8000 | 63.1280 | 66.0000 |
| census_acs.land_area_sq_miles.value | 50 | 5.0690 | 594.7610 | 136.7711 | 102.9820 |
| census_acs.median_household_income.moe | 50 | 1,441.0000 | 21,934.0000 | 6,617.1000 | 5,262.0000 |
| census_acs.median_household_income.value | 50 | 42,773.0000 | 202,359.0000 | 99,359.3400 | 93,611.0000 |
| census_acs.per_capita_income.moe | 50 | 912.0000 | 13,421.0000 | 3,251.2000 | 2,471.0000 |
| census_acs.per_capita_income.value | 50 | 20,445.0000 | 120,120.0000 | 50,642.8600 | 46,639.0000 |
| census_acs.population_density_per_sq_mile.value | 50 | 2.9019 | 8,676.8741 | 1,882.6234 | 644.0222 |
| census_acs.total_population.moe | 50 | 27.0000 | 3,388.0000 | 1,415.4800 | 1,249.0000 |
| census_acs.total_population.value | 50 | 1,159.0000 | 741,812.0000 | 100,307.7200 | 49,293.0000 |
| census_acs.unemployment_rate_16plus.moe | 50 | 0.3000 | 8.1000 | 1.7120 | 1.1000 |
| census_acs.unemployment_rate_16plus.value | 50 | 1.8000 | 21.1000 | 5.1720 | 4.7000 |
| context.cost.enrichment_input_tokens | 32 | 12,458.0000 | 38,315.0000 | 30,785.5625 | 32,318.0000 |
| context.cost.enrichment_output_tokens | 32 | 194.0000 | 1,538.0000 | 541.7500 | 423.0000 |
| context.cost.total_input_tokens | 32 | 12,458.0000 | 56,214.0000 | 38,857.8750 | 37,442.0000 |
| context.cost.total_output_tokens | 32 | 194.0000 | 2,831.0000 | 921.8750 | 889.0000 |
| context.cost.validation_input_tokens | 32 | 0.0000 | 18,605.0000 | 8,072.3125 | 12,328.0000 |
| context.cost.validation_output_tokens | 32 | 0.0000 | 1,320.0000 | 380.1250 | 474.0000 |
| context.cost.web_search_requests | 32 | 1.0000 | 3.0000 | 2.4375 | 3.0000 |
| context.validation_summary.findings_confirmed | 17 | 0.0000 | 7.0000 | 1.4706 | 1.0000 |
| context.validation_summary.findings_downgraded | 17 | 0.0000 | 4.0000 | 0.6471 | 0.0000 |
| context.validation_summary.findings_rejected | 17 | 0.0000 | 1.0000 | 0.1176 | 0.0000 |
| context.validation_summary.findings_submitted | 17 | 1.0000 | 7.0000 | 2.2353 | 1.0000 |
| context.validation_summary.wrong_school_detected | 17 | 0.0000 | 1.0000 | 0.0588 | 0.0000 |
| course_access.ap.enrollment_by_race.american_indian_female | 3 | 0.0000 | 1.0000 | 0.6667 | 1.0000 |
| course_access.ap.enrollment_by_race.american_indian_male | 3 | 0.0000 | 2.0000 | 1.0000 | 1.0000 |
| course_access.ap.enrollment_by_race.asian_female | 3 | 0.0000 | 71.0000 | 33.6667 | 30.0000 |
| course_access.ap.enrollment_by_race.asian_male | 3 | 0.0000 | 69.0000 | 31.3333 | 25.0000 |
| course_access.ap.enrollment_by_race.black_female | 3 | 0.0000 | 15.0000 | 5.6667 | 2.0000 |
| course_access.ap.enrollment_by_race.black_male | 3 | 0.0000 | 12.0000 | 5.0000 | 3.0000 |
| course_access.ap.enrollment_by_race.hispanic_female | 3 | 0.0000 | 29.0000 | 18.0000 | 25.0000 |
| course_access.ap.enrollment_by_race.hispanic_male | 3 | 0.0000 | 21.0000 | 13.0000 | 18.0000 |
| course_access.ap.enrollment_by_race.pacific_islander_female | 3 | 0.0000 | 1.0000 | 0.6667 | 1.0000 |
| course_access.ap.enrollment_by_race.pacific_islander_male | 3 | 0.0000 | 3.0000 | 1.3333 | 1.0000 |
| course_access.ap.enrollment_by_race.two_or_more_female | 3 | 0.0000 | 29.0000 | 15.6667 | 18.0000 |
| course_access.ap.enrollment_by_race.two_or_more_male | 3 | 0.0000 | 26.0000 | 15.0000 | 19.0000 |
| course_access.ap.enrollment_by_race.white_female | 3 | 1.0000 | 213.0000 | 95.0000 | 71.0000 |
| course_access.ap.enrollment_by_race.white_male | 3 | 5.0000 | 168.0000 | 80.6667 | 69.0000 |
| course_access.dual_enrollment.enrollment_by_race.american_indian_female | 5 | 0.0000 | 3.0000 | 0.8000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.american_indian_male | 5 | 1.0000 | 3.0000 | 1.8000 | 2.0000 |
| course_access.dual_enrollment.enrollment_by_race.asian_female | 5 | 0.0000 | 66.0000 | 17.4000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.asian_male | 5 | 0.0000 | 71.0000 | 18.4000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.black_female | 5 | 0.0000 | 56.0000 | 11.6000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.black_male | 5 | 0.0000 | 57.0000 | 12.2000 | 1.0000 |
| course_access.dual_enrollment.enrollment_by_race.hispanic_female | 5 | 0.0000 | 116.0000 | 34.6000 | 18.0000 |
| course_access.dual_enrollment.enrollment_by_race.hispanic_male | 5 | 0.0000 | 98.0000 | 28.6000 | 17.0000 |
| course_access.dual_enrollment.enrollment_by_race.pacific_islander_female | 5 | 0.0000 | 11.0000 | 2.2000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.pacific_islander_male | 5 | 0.0000 | 10.0000 | 2.0000 | 0.0000 |
| course_access.dual_enrollment.enrollment_by_race.two_or_more_female | 5 | 0.0000 | 66.0000 | 21.0000 | 5.0000 |
| course_access.dual_enrollment.enrollment_by_race.two_or_more_male | 5 | 0.0000 | 82.0000 | 20.4000 | 6.0000 |
| course_access.dual_enrollment.enrollment_by_race.white_female | 5 | 2.0000 | 238.0000 | 107.6000 | 102.0000 |
| course_access.dual_enrollment.enrollment_by_race.white_male | 5 | 4.0000 | 279.0000 | 106.0000 | 100.0000 |
| course_access.gifted_talented.enrollment_by_race.american_indian_female | 32 | 0.0000 | 1.0000 | 0.0625 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.american_indian_male | 32 | 0.0000 | 2.0000 | 0.1250 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.asian_female | 32 | 0.0000 | 40.0000 | 3.7188 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.asian_male | 32 | 0.0000 | 42.0000 | 4.2812 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.black_female | 32 | 0.0000 | 2.0000 | 0.4062 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.black_male | 32 | 0.0000 | 6.0000 | 0.6250 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.hispanic_female | 32 | 0.0000 | 49.0000 | 3.3750 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.hispanic_male | 32 | 0.0000 | 61.0000 | 4.4062 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.pacific_islander_female | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.pacific_islander_male | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| course_access.gifted_talented.enrollment_by_race.two_or_more_female | 32 | 0.0000 | 13.0000 | 2.3750 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.two_or_more_male | 32 | 0.0000 | 19.0000 | 3.4062 | 1.0000 |
| course_access.gifted_talented.enrollment_by_race.white_female | 32 | 0.0000 | 85.0000 | 13.5625 | 8.0000 |
| course_access.gifted_talented.enrollment_by_race.white_male | 32 | 0.0000 | 109.0000 | 17.8438 | 11.0000 |
| demographics.ell_count | 48 | 0.0000 | 290.0000 | 54.8125 | 35.0000 |
| demographics.foster_care_count | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| demographics.frl_count | 48 | 0.0000 | 697.0000 | 195.9583 | 175.0000 |
| demographics.frl_pct | 47 | 0.0194 | 0.9516 | 0.4771 | 0.4345 |
| demographics.homeless_count | 48 | 0.0000 | 73.0000 | 12.2292 | 10.0000 |
| demographics.migrant_count | 48 | 0.0000 | 82.0000 | 6.1042 | 0.0000 |
| demographics.ospi_total | 48 | 0.0000 | 1,997.0000 | 479.3542 | 437.0000 |
| demographics.section_504_count | 48 | 0.0000 | 191.0000 | 28.7083 | 14.0000 |
| demographics.sped_count | 48 | 0.0000 | 202.0000 | 81.0000 | 79.0000 |
| derived.chronic_absenteeism_pct | 41 | 0.0508 | 0.5455 | 0.2369 | 0.2116 |
| derived.counselor_student_ratio | 37 | 75.5000 | 1,116.0000 | 381.8730 | 352.0000 |
| derived.discipline_disparity.american_indian | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| derived.discipline_disparity.asian | 18 | 0.0000 | 1.3700 | 0.2556 | 0.0000 |
| derived.discipline_disparity.black | 17 | 0.0000 | 33.2600 | 3.1829 | 1.2100 |
| derived.discipline_disparity.hispanic | 29 | 0.0000 | 8.4700 | 1.8776 | 1.1400 |
| derived.discipline_disparity.pacific_islander | 6 | 0.0000 | 7.8500 | 2.4833 | 1.5000 |
| derived.discipline_disparity.two_or_more | 26 | 0.0000 | 16.4100 | 2.1165 | 1.1100 |
| derived.discipline_disparity_max | 31 | 0.0000 | 33.2600 | 4.0000 | 2.1600 |
| derived.flags.chronic_absenteeism.raw_value | 41 | 0.0508 | 0.5455 | 0.2369 | 0.2116 |
| derived.flags.chronic_absenteeism.threshold | 22 | 0.2000 | 0.3000 | 0.2545 | 0.3000 |
| derived.flags.counselor_ratio.raw_value | 37 | 75.5000 | 1,116.0000 | 381.8730 | 352.0000 |
| derived.flags.counselor_ratio.threshold | 14 | 400.0000 | 500.0000 | 457.1429 | 500.0000 |
| derived.flags.discipline_disparity.raw_value | 31 | 0.0000 | 33.2600 | 4.0000 | 2.1600 |
| derived.flags.discipline_disparity.threshold | 16 | 2.0000 | 3.0000 | 2.7500 | 3.0000 |
| derived.flags.no_counselor.raw_value | 11 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| derived.percentiles.chronic_absenteeism_pct.district | 40 | 6.0000 | 95.0000 | 51.7000 | 52.0000 |
| derived.percentiles.chronic_absenteeism_pct.peer | 40 | 2.0000 | 98.0000 | 56.7000 | 59.0000 |
| derived.percentiles.chronic_absenteeism_pct.state | 41 | 3.0000 | 93.0000 | 53.3902 | 60.0000 |
| derived.percentiles.counselor_student_ratio.district | 35 | 9.0000 | 97.0000 | 55.0286 | 62.0000 |
| derived.percentiles.counselor_student_ratio.peer | 36 | 2.0000 | 96.0000 | 53.9722 | 53.0000 |
| derived.percentiles.counselor_student_ratio.state | 37 | 1.0000 | 98.0000 | 51.7027 | 52.0000 |
| derived.percentiles.discipline_rate.district | 30 | 11.0000 | 93.0000 | 56.8667 | 70.0000 |
| derived.percentiles.discipline_rate.peer | 31 | 7.0000 | 97.0000 | 55.1935 | 55.0000 |
| derived.percentiles.discipline_rate.state | 32 | 4.0000 | 98.0000 | 59.4375 | 69.0000 |
| derived.percentiles.ela_proficiency_pct.district | 35 | 3.0000 | 93.0000 | 43.7143 | 36.0000 |
| derived.percentiles.ela_proficiency_pct.peer | 37 | 5.0000 | 99.0000 | 49.2973 | 49.0000 |
| derived.percentiles.ela_proficiency_pct.state | 38 | 1.0000 | 99.0000 | 51.6053 | 54.0000 |
| derived.percentiles.math_proficiency_pct.district | 32 | 6.0000 | 99.0000 | 53.9688 | 54.0000 |
| derived.percentiles.math_proficiency_pct.peer | 32 | 3.0000 | 94.0000 | 48.8438 | 51.0000 |
| derived.percentiles.math_proficiency_pct.state | 33 | 3.0000 | 99.0000 | 53.2121 | 55.0000 |
| derived.percentiles.per_pupil_total.district | 48 | 1.0000 | 97.0000 | 50.3542 | 50.0000 |
| derived.percentiles.per_pupil_total.peer | 47 | 6.0000 | 99.0000 | 53.0426 | 48.0000 |
| derived.percentiles.per_pupil_total.state | 49 | 3.0000 | 96.0000 | 52.2653 | 49.0000 |
| derived.percentiles.regular_attendance_pct.district | 40 | 6.0000 | 95.0000 | 51.7000 | 52.0000 |
| derived.percentiles.regular_attendance_pct.peer | 40 | 2.0000 | 98.0000 | 56.7000 | 59.0000 |
| derived.percentiles.regular_attendance_pct.state | 41 | 3.0000 | 93.0000 | 53.3902 | 60.0000 |
| derived.percentiles.student_teacher_ratio.district | 46 | 4.0000 | 97.0000 | 56.4783 | 61.0000 |
| derived.percentiles.student_teacher_ratio.peer | 46 | 8.0000 | 100.0000 | 52.2826 | 51.0000 |
| derived.percentiles.student_teacher_ratio.state | 47 | 8.0000 | 100.0000 | 53.5319 | 55.0000 |
| derived.proficiency_composite | 31 | 0.1340 | 0.8965 | 0.4618 | 0.4200 |
| derived.regression_predicted | 31 | 0.1876 | 0.8129 | 0.4720 | 0.4802 |
| derived.regression_r_squared | 31 | 0.5430 | 0.7470 | 0.7036 | 0.7470 |
| derived.regression_residual | 31 | -0.1737 | 0.1429 | -0.0103 | -0.0010 |
| derived.regression_zscore | 31 | -1.7900 | 1.5600 | -0.0994 | -0.0100 |
| derived.student_teacher_ratio | 47 | 0.8000 | 24.5000 | 15.1830 | 15.3000 |
| discipline.crdc.expulsion_with_ed.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.asian_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_with_ed.black_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_with_ed.black_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_with_ed.hispanic_female | 46 | 0.0000 | 2.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_with_ed.hispanic_male | 46 | 0.0000 | 4.0000 | 0.1739 | 0.0000 |
| discipline.crdc.expulsion_with_ed.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.two_or_more_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_with_ed.two_or_more_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_with_ed.white_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_with_ed.white_male | 46 | 0.0000 | 2.0000 | 0.0870 | 0.0000 |
| discipline.crdc.expulsion_without_ed.american_indian_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_without_ed.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.asian_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_without_ed.black_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.black_male | 46 | 0.0000 | 2.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_without_ed.hispanic_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.expulsion_without_ed.hispanic_male | 46 | 0.0000 | 2.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_without_ed.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.two_or_more_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.two_or_more_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_without_ed.white_female | 46 | 0.0000 | 3.0000 | 0.0870 | 0.0000 |
| discipline.crdc.expulsion_without_ed.white_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.asian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.black_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.black_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.hispanic_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.hispanic_male | 46 | 0.0000 | 2.0000 | 0.0652 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.two_or_more_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.two_or_more_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.white_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.expulsion_zero_tolerance.white_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss.american_indian_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.iss.asian_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.iss.asian_male | 46 | 0.0000 | 2.0000 | 0.0870 | 0.0000 |
| discipline.crdc.iss.black_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.iss.black_male | 46 | 0.0000 | 1.0000 | 0.0652 | 0.0000 |
| discipline.crdc.iss.hispanic_female | 46 | 0.0000 | 19.0000 | 0.5435 | 0.0000 |
| discipline.crdc.iss.hispanic_male | 46 | 0.0000 | 9.0000 | 0.9565 | 0.0000 |
| discipline.crdc.iss.pacific_islander_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.iss.pacific_islander_male | 46 | 0.0000 | 2.0000 | 0.0652 | 0.0000 |
| discipline.crdc.iss.two_or_more_female | 46 | 0.0000 | 3.0000 | 0.2174 | 0.0000 |
| discipline.crdc.iss.two_or_more_male | 46 | 0.0000 | 5.0000 | 0.2391 | 0.0000 |
| discipline.crdc.iss.white_female | 46 | 0.0000 | 7.0000 | 0.6087 | 0.0000 |
| discipline.crdc.iss.white_male | 46 | 0.0000 | 14.0000 | 1.4348 | 0.0000 |
| discipline.crdc.iss_idea.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.asian_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.iss_idea.black_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.black_male | 46 | 0.0000 | 3.0000 | 0.1304 | 0.0000 |
| discipline.crdc.iss_idea.hispanic_female | 46 | 0.0000 | 1.0000 | 0.0652 | 0.0000 |
| discipline.crdc.iss_idea.hispanic_male | 46 | 0.0000 | 3.0000 | 0.1957 | 0.0000 |
| discipline.crdc.iss_idea.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.two_or_more_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.iss_idea.two_or_more_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.iss_idea.white_female | 46 | 0.0000 | 1.0000 | 0.1087 | 0.0000 |
| discipline.crdc.iss_idea.white_male | 46 | 0.0000 | 5.0000 | 0.6739 | 0.0000 |
| discipline.crdc.oos_instances_504 | 46 | 0.0000 | 13.0000 | 1.0000 | 0.0000 |
| discipline.crdc.oos_instances_idea | 46 | 0.0000 | 53.0000 | 6.1522 | 2.0000 |
| discipline.crdc.oos_instances_wodis | 46 | 0.0000 | 102.0000 | 12.1304 | 3.0000 |
| discipline.crdc.oss_multiple.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple.asian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple.black_female | 46 | 0.0000 | 2.0000 | 0.1087 | 0.0000 |
| discipline.crdc.oss_multiple.black_male | 46 | 0.0000 | 3.0000 | 0.1087 | 0.0000 |
| discipline.crdc.oss_multiple.hispanic_female | 46 | 0.0000 | 5.0000 | 0.1739 | 0.0000 |
| discipline.crdc.oss_multiple.hispanic_male | 46 | 0.0000 | 11.0000 | 0.7174 | 0.0000 |
| discipline.crdc.oss_multiple.pacific_islander_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_multiple.pacific_islander_male | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_multiple.two_or_more_female | 46 | 0.0000 | 2.0000 | 0.1087 | 0.0000 |
| discipline.crdc.oss_multiple.two_or_more_male | 46 | 0.0000 | 3.0000 | 0.1957 | 0.0000 |
| discipline.crdc.oss_multiple.white_female | 46 | 0.0000 | 4.0000 | 0.1522 | 0.0000 |
| discipline.crdc.oss_multiple.white_male | 46 | 0.0000 | 4.0000 | 0.5870 | 0.0000 |
| discipline.crdc.oss_multiple_idea.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple_idea.american_indian_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.oss_multiple_idea.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple_idea.asian_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.oss_multiple_idea.black_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.oss_multiple_idea.black_male | 46 | 0.0000 | 1.0000 | 0.0652 | 0.0000 |
| discipline.crdc.oss_multiple_idea.hispanic_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple_idea.hispanic_male | 46 | 0.0000 | 3.0000 | 0.2391 | 0.0000 |
| discipline.crdc.oss_multiple_idea.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple_idea.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_multiple_idea.two_or_more_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_multiple_idea.two_or_more_male | 46 | 0.0000 | 3.0000 | 0.1522 | 0.0000 |
| discipline.crdc.oss_multiple_idea.white_female | 46 | 0.0000 | 2.0000 | 0.1304 | 0.0000 |
| discipline.crdc.oss_multiple_idea.white_male | 46 | 0.0000 | 6.0000 | 0.5652 | 0.0000 |
| discipline.crdc.oss_single.american_indian_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_single.american_indian_male | 46 | 0.0000 | 2.0000 | 0.0870 | 0.0000 |
| discipline.crdc.oss_single.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single.asian_male | 46 | 0.0000 | 2.0000 | 0.0652 | 0.0000 |
| discipline.crdc.oss_single.black_female | 46 | 0.0000 | 2.0000 | 0.0652 | 0.0000 |
| discipline.crdc.oss_single.black_male | 46 | 0.0000 | 5.0000 | 0.2826 | 0.0000 |
| discipline.crdc.oss_single.hispanic_female | 46 | 0.0000 | 13.0000 | 0.8043 | 0.0000 |
| discipline.crdc.oss_single.hispanic_male | 46 | 0.0000 | 27.0000 | 1.6304 | 0.0000 |
| discipline.crdc.oss_single.pacific_islander_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_single.pacific_islander_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.oss_single.two_or_more_female | 46 | 0.0000 | 2.0000 | 0.2391 | 0.0000 |
| discipline.crdc.oss_single.two_or_more_male | 46 | 0.0000 | 4.0000 | 0.4348 | 0.0000 |
| discipline.crdc.oss_single.white_female | 46 | 0.0000 | 5.0000 | 0.6522 | 0.0000 |
| discipline.crdc.oss_single.white_male | 46 | 0.0000 | 10.0000 | 1.9783 | 1.0000 |
| discipline.crdc.oss_single_idea.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single_idea.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single_idea.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single_idea.asian_male | 46 | 0.0000 | 1.0000 | 0.0652 | 0.0000 |
| discipline.crdc.oss_single_idea.black_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| discipline.crdc.oss_single_idea.black_male | 46 | 0.0000 | 1.0000 | 0.0870 | 0.0000 |
| discipline.crdc.oss_single_idea.hispanic_female | 46 | 0.0000 | 2.0000 | 0.1087 | 0.0000 |
| discipline.crdc.oss_single_idea.hispanic_male | 46 | 0.0000 | 7.0000 | 0.3261 | 0.0000 |
| discipline.crdc.oss_single_idea.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single_idea.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| discipline.crdc.oss_single_idea.two_or_more_female | 46 | 0.0000 | 1.0000 | 0.0435 | 0.0000 |
| discipline.crdc.oss_single_idea.two_or_more_male | 46 | 0.0000 | 2.0000 | 0.1739 | 0.0000 |
| discipline.crdc.oss_single_idea.white_female | 46 | 0.0000 | 4.0000 | 0.3261 | 0.0000 |
| discipline.crdc.oss_single_idea.white_male | 46 | 0.0000 | 5.0000 | 0.9565 | 0.0000 |
| discipline.ospi.denominator | 32 | 50.0000 | 1,488.0000 | 553.1875 | 527.0000 |
| discipline.ospi.numerator | 32 | 3.0000 | 115.0000 | 16.5312 | 10.0000 |
| discipline.ospi.rate | 32 | 0.0054 | 0.1400 | 0.0344 | 0.0228 |
| district_context.cost.enrichment_input_tokens | 50 | 13,920.0000 | 49,572.0000 | 31,061.1800 | 36,220.0000 |
| district_context.cost.enrichment_output_tokens | 50 | 265.0000 | 2,388.0000 | 1,376.1800 | 1,378.0000 |
| district_context.cost.total_input_tokens | 50 | 13,920.0000 | 68,028.0000 | 47,013.2200 | 49,777.0000 |
| district_context.cost.total_output_tokens | 50 | 265.0000 | 3,712.0000 | 2,433.3200 | 2,571.0000 |
| district_context.cost.validation_input_tokens | 50 | 0.0000 | 22,442.0000 | 15,952.0400 | 17,500.0000 |
| district_context.cost.validation_output_tokens | 50 | 0.0000 | 1,478.0000 | 1,057.1400 | 1,137.0000 |
| district_context.cost.web_search_requests | 50 | 1.0000 | 3.0000 | 2.7600 | 3.0000 |
| district_context.validation_summary.findings_confirmed | 47 | 0.0000 | 8.0000 | 4.1277 | 4.0000 |
| district_context.validation_summary.findings_downgraded | 47 | 0.0000 | 4.0000 | 0.7872 | 1.0000 |
| district_context.validation_summary.findings_rejected | 47 | 0.0000 | 3.0000 | 0.3617 | 0.0000 |
| district_context.validation_summary.findings_submitted | 47 | 1.0000 | 10.0000 | 5.2766 | 5.0000 |
| district_context.validation_summary.wrong_school_detected | 47 | 0.0000 | 1.0000 | 0.0213 | 0.0000 |
| enrollment.by_race.american_indian | 50 | 0.0000 | 40.0000 | 3.5400 | 2.0000 |
| enrollment.by_race.asian | 50 | 0.0000 | 290.0000 | 43.2000 | 12.0000 |
| enrollment.by_race.black | 50 | 0.0000 | 154.0000 | 18.4000 | 7.0000 |
| enrollment.by_race.hispanic | 50 | 0.0000 | 701.0000 | 104.6800 | 63.0000 |
| enrollment.by_race.not_specified | 18 | 1.0000 | 14.0000 | 4.1111 | 3.0000 |
| enrollment.by_race.pacific_islander | 50 | 0.0000 | 46.0000 | 3.8200 | 1.0000 |
| enrollment.by_race.two_or_more | 50 | 0.0000 | 213.0000 | 45.5800 | 38.0000 |
| enrollment.by_race.white | 50 | 0.0000 | 1,275.0000 | 244.0400 | 230.0000 |
| enrollment.by_sex.female | 50 | 0.0000 | 970.0000 | 223.0800 | 200.0000 |
| enrollment.by_sex.male | 50 | 0.0000 | 1,043.0000 | 240.1800 | 219.0000 |
| enrollment.crdc_by_race.american_indian | 46 | 0.0000 | 38.0000 | 4.4130 | 3.0000 |
| enrollment.crdc_by_race.asian | 46 | 0.0000 | 226.0000 | 43.1739 | 12.0000 |
| enrollment.crdc_by_race.black | 46 | 0.0000 | 135.0000 | 17.6739 | 9.0000 |
| enrollment.crdc_by_race.hispanic | 46 | 0.0000 | 656.0000 | 109.7609 | 67.0000 |
| enrollment.crdc_by_race.pacific_islander | 46 | 0.0000 | 29.0000 | 4.3478 | 2.0000 |
| enrollment.crdc_by_race.two_or_more | 46 | 0.0000 | 176.0000 | 46.6087 | 43.0000 |
| enrollment.crdc_by_race.white | 46 | 3.0000 | 1,387.0000 | 268.3696 | 238.0000 |
| enrollment.crdc_total | 46 | 47.0000 | 2,031.0000 | 494.3478 | 435.0000 |
| enrollment.total | 50 | 0.0000 | 2,026.0000 | 464.7400 | 427.0000 |
| finance.per_pupil_federal | 49 | 35.4400 | 5,229.6600 | 1,049.0424 | 695.5100 |
| finance.per_pupil_local | 49 | 159.3100 | 11,446.9700 | 3,542.6414 | 3,270.3400 |
| finance.per_pupil_state | 49 | 3,830.3700 | 27,013.3800 | 14,932.2067 | 14,878.2200 |
| finance.per_pupil_total | 49 | 5,410.7500 | 37,745.0700 | 19,523.8892 | 18,725.9100 |
| layer3_narrative.dedup_collisions_count | 10 | 0.0000 | 1.0000 | 0.1000 | 0.0000 |
| layer3_narrative.source_findings_count | 50 | 0.0000 | 13.0000 | 5.2600 | 5.0000 |
| layer3_narrative.stage0_dropped_count | 50 | 0.0000 | 11.0000 | 0.7800 | 0.0000 |
| layer3_narrative.stage1_excluded_count | 50 | 0.0000 | 8.0000 | 3.0000 | 3.0000 |
| layer3_narrative.stage1_included_count | 50 | 0.0000 | 7.0000 | 2.2200 | 2.0000 |
| safety.harassment_bullying.allegations_disability | 46 | 0.0000 | 5.0000 | 0.2174 | 0.0000 |
| safety.harassment_bullying.allegations_orientation | 46 | 0.0000 | 6.0000 | 0.3261 | 0.0000 |
| safety.harassment_bullying.allegations_race | 46 | 0.0000 | 18.0000 | 0.7609 | 0.0000 |
| safety.harassment_bullying.allegations_religion | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.harassment_bullying.allegations_sex | 46 | 0.0000 | 8.0000 | 0.6087 | 0.0000 |
| safety.referrals_arrests.arrests.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.asian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.black_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.black_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.hispanic_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.hispanic_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.pacific_islander_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.two_or_more_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.two_or_more_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.white_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.arrests.white_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.american_indian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.american_indian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.asian_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.asian_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.black_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.black_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| safety.referrals_arrests.referrals.hispanic_female | 46 | 0.0000 | 2.0000 | 0.0435 | 0.0000 |
| safety.referrals_arrests.referrals.hispanic_male | 46 | 0.0000 | 3.0000 | 0.1087 | 0.0000 |
| safety.referrals_arrests.referrals.pacific_islander_female | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.pacific_islander_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| safety.referrals_arrests.referrals.two_or_more_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| safety.referrals_arrests.referrals.two_or_more_male | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.referrals_arrests.referrals.white_female | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| safety.referrals_arrests.referrals.white_male | 46 | 0.0000 | 1.0000 | 0.0217 | 0.0000 |
| safety.restraint_seclusion.mechanical_504 | 45 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.restraint_seclusion.mechanical_idea | 45 | 0.0000 | 5.0000 | 0.1111 | 0.0000 |
| safety.restraint_seclusion.mechanical_wodis | 45 | 0.0000 | 9.0000 | 0.2000 | 0.0000 |
| safety.restraint_seclusion.physical_504 | 45 | 0.0000 | 2.0000 | 0.0667 | 0.0000 |
| safety.restraint_seclusion.physical_idea | 45 | 0.0000 | 52.0000 | 2.8889 | 0.0000 |
| safety.restraint_seclusion.physical_wodis | 45 | 0.0000 | 19.0000 | 0.8222 | 0.0000 |
| safety.restraint_seclusion.seclusion_504 | 45 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| safety.restraint_seclusion.seclusion_idea | 45 | 0.0000 | 98.0000 | 4.0889 | 0.0000 |
| safety.restraint_seclusion.seclusion_wodis | 45 | 0.0000 | 18.0000 | 0.5778 | 0.0000 |
| staffing.counselor_fte | 48 | 0.0000 | 7.0000 | 1.2358 | 1.0000 |
| staffing.nurse_fte | 48 | 0.0000 | 1.6500 | 0.4725 | 0.4000 |
| staffing.psychologist_fte | 48 | 0.0000 | 4.0000 | 0.5604 | 0.5000 |
| staffing.security_guard_fte | 48 | 0.0000 | 2.0000 | 0.1942 | 0.0000 |
| staffing.social_worker_fte | 48 | 0.0000 | 2.0000 | 0.1646 | 0.0000 |
| staffing.sro_fte | 48 | 0.0000 | 1.0000 | 0.0394 | 0.0000 |
| staffing.teacher_fte_certified | 48 | 0.7700 | 74.0800 | 28.8167 | 28.0000 |
| staffing.teacher_fte_not_certified | 48 | 0.0000 | 21.5500 | 1.0550 | 0.0000 |
| staffing.teacher_fte_total | 48 | 0.7700 | 94.4300 | 29.8717 | 29.0000 |

Total distinct field paths walked: **594**.

## 2. V1 variable verification (Task 3)

For each v1 variable, the actual MongoDB path, full-collection null count (out of 2532), and basic distribution. **null_pct** is computed against the full collection, not against "non-excluded" schools — that filter is not yet defined; flagging anything ≥ 10%.

### Identity

| v1 variable | actual MongoDB path | non-null | null % | notes |
|---|---|---|---|---|
| nces_id | `_id` | 2532 | 0.0% | — |
| district_nces_id | `district.nces_id` | 2532 | 0.0% | — |
| school_name | `name` | 2532 | 0.0% | — |
| grade_level_category | `derived.level_group` | 2532 | 0.0% | — |

### Demographics

| v1 variable | actual MongoDB path | non-null | null % | notes |
|---|---|---|---|---|
| enrollment_total | `enrollment.total` | 2532 | 0.0% | — |
| frl_rate | `demographics.frl_pct` | 2380 | 0.0% | prompt assumed `frl_rate` — actual differs |
| ell_rate | **MISSING** | — | — | no path returned non-null |
| sped_rate | **MISSING** | — | — | no path returned non-null |
| migrant_rate | **MISSING** | — | — | no path returned non-null |
| race_pct_non_white | **MISSING** | — | — | no path returned non-null |
| chronic_absenteeism_rate | `derived.chronic_absenteeism_pct` | 1961 | 22.6% | prompt assumed `chronic_absenteeism_rate` — actual differs; high null pct (22.6%) |

Numeric distribution (full-collection, non-null only):

| v1 variable | n | min | median | mean | max |
|---|---|---|---|---|---|
| enrollment_total | 2532 | 0.0000 | 381.0000 | 431.6647 | 3,127.0000 |
| frl_rate | 2380 | 0.0000 | 0.5337 | 0.5131 | 0.9910 |
| chronic_absenteeism_rate | 1961 | 0.0013 | 0.2460 | 0.2541 | 0.9762 |

### Census

| v1 variable | actual MongoDB path | non-null | null % | notes |
|---|---|---|---|---|
| median_household_income | `census_acs.median_household_income.value` | 2481 | 0.1% | — |
| per_capita_income | `census_acs.per_capita_income.value` | 2484 | 0.0% | — |
| gini_index | `census_acs.gini_index.value` | 2484 | 0.0% | — |
| bachelors_pct_25_plus | `census_acs.bachelors_or_higher_pct_25plus.value` | 2484 | 0.0% | prompt assumed `census_acs.bachelors_pct_25_plus.value` — actual differs |
| labor_force_participation_rate | `census_acs.labor_force_participation_rate_16plus.value` | 2484 | 0.0% | prompt assumed `census_acs.labor_force_participation_rate.value` — actual differs |
| unemployment_rate | `census_acs.unemployment_rate_16plus.value` | 2484 | 0.0% | prompt assumed `census_acs.unemployment_rate.value` — actual differs |
| total_population | `census_acs.total_population.value` | 2484 | 0.0% | — |
| land_area_sq_mi | `census_acs.land_area_sq_miles.value` | 2484 | 0.0% | prompt assumed `census_acs.land_area_sq_mi.value` — actual differs |
| population_density | `census_acs.population_density_per_sq_mile.value` | 2484 | 0.0% | prompt assumed `census_acs.population_density.value` — actual differs |

Numeric distribution (full-collection, non-null only):

| v1 variable | n | min | median | mean | max |
|---|---|---|---|---|---|
| median_household_income | 2481 | 26,875.0000 | 87,196.0000 | 93,435.2660 | 202,359.0000 |
| per_capita_income | 2484 | 16,077.0000 | 43,363.0000 | 47,036.2303 | 120,120.0000 |
| gini_index | 2484 | 0.3016 | 0.4306 | 0.4300 | 0.7500 |
| bachelors_pct_25_plus | 2484 | 2.8000 | 31.2000 | 33.7728 | 78.8000 |
| labor_force_participation_rate | 2484 | 13.3000 | 64.4000 | 62.6756 | 79.4000 |
| unemployment_rate | 2484 | 0.0000 | 5.0000 | 5.2026 | 21.1000 |
| total_population | 2484 | 30.0000 | 56,036.0000 | 105,762.0866 | 741,812.0000 |
| land_area_sq_mi | 2484 | 5.0690 | 85.4930 | 163.2396 | 1,879.4890 |
| population_density | 2484 | 0.0697 | 619.5141 | 1,717.5770 | 8,676.8741 |

### Exclusions

| v1 variable | actual MongoDB path | non-null | null % | notes |
|---|---|---|---|---|
| exclusion_status | `census_acs._meta.unmatched_reason` | 48 | 98.1% | prompt assumed `exclusion_status` — actual differs; high null pct (98.1%) |
| exclusion_reason_code | `census_acs._meta.unmatched_reason` | 48 | 98.1% | prompt assumed `exclusion_reason_code` — actual differs; high null pct (98.1%) |

## 3. Homelessness availability (Task 4)

**Found in schema.** Paths containing 'homeless':

- `demographics.homeless_count`

## 4. Exclusions union (Task 5)

| List | count |
|---|---|
| school_exclusions.yaml | 78 |
| Phase 3R SKIP (census_acs._meta.unmatched_reason ≠ null) | 48 |
| Overlap (in both) | 6 |
| **Union** | 120 |

Phase 3R SKIP breakdown by reason code (post-patch):

| unmatched_reason | count |
|---|---|
| charter_pending_district_assignment | 17 |
| regional_alternative_program_not_comparable | 12 |
| institutional_facility_not_comparable | 10 |
| statewide_specialty_school_not_comparable | 8 |
| tribal_community_context_not_capturable_v1 | 1 |

**One or more counts outside expected ranges:** yaml expected 70-90 got 78 (OK); skip expected 40-60 got 48 (OK); union expected 80-100 got 120 (OUT).

## 5. Issues for builder review

### Missing v1 variables

These v1 variables had **no candidate path returning a non-null value**. Either they need to be ingested in subsequent prompts or the candidate paths in this verifier are wrong.

- **ell_rate**
- **sped_rate**
- **migrant_rate**
- **race_pct_non_white**

### Path discrepancies (prompt assumed vs. actual)

Variables found, but at a different MongoDB path than the prompt assumed. Either the prompt should adopt the actual path, or the data should be re-stored at the assumed path. Recommendation: use the actual path going forward.

| v1 variable | prompt assumed | actual |
|---|---|---|
| frl_rate | `frl_rate` | `demographics.frl_pct` |
| chronic_absenteeism_rate | `chronic_absenteeism_rate` | `derived.chronic_absenteeism_pct` |
| bachelors_pct_25_plus | `census_acs.bachelors_pct_25_plus.value` | `census_acs.bachelors_or_higher_pct_25plus.value` |
| labor_force_participation_rate | `census_acs.labor_force_participation_rate.value` | `census_acs.labor_force_participation_rate_16plus.value` |
| unemployment_rate | `census_acs.unemployment_rate.value` | `census_acs.unemployment_rate_16plus.value` |
| land_area_sq_mi | `census_acs.land_area_sq_mi.value` | `census_acs.land_area_sq_miles.value` |
| population_density | `census_acs.population_density.value` | `census_acs.population_density_per_sq_mile.value` |
| exclusion_status | `exclusion_status` | `census_acs._meta.unmatched_reason` |
| exclusion_reason_code | `exclusion_reason_code` | `census_acs._meta.unmatched_reason` |

### High-null fields (≥ 10% null in full collection)

These fields are populated for fewer than 90% of schools. Review whether the null pattern is expected (e.g. high schools only, non-comparable schools excluded) or a coverage gap.

| v1 variable | actual path | null % |
|---|---|---|
| chronic_absenteeism_rate | `derived.chronic_absenteeism_pct` | 22.6% |
| exclusion_status | `census_acs._meta.unmatched_reason` | 98.1% |
| exclusion_reason_code | `census_acs._meta.unmatched_reason` | 98.1% |

### Homelessness path decision

- Homelessness field already present in schema at: demographics.homeless_count. No data.wa.gov probe needed.

### Other anomalies

- `nces_id` is the MongoDB primary key `_id` (12-char string), not a separate `nces_id` field. Confirmed: there is no `nces_id` field on these documents. All experimental scripts must use `_id` for the school identifier (this caught us in the prior session — see `_run_acs_ingestion.py`).
- Exclusion status lives at `census_acs._meta.unmatched_reason`, not at a top-level `exclusion_status`/`exclusion_reason_code`. Phase 3R Census ingestion stored both the reason code and the flag-of-being-skipped in one field. If the v1 methodology needs a separate `exclusion_status` enum (in/out), it has to be derived or written in a future prompt.
