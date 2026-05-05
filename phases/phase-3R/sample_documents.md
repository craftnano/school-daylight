# Phase 3R — Step 4: Edge-Case Sample Documents

Full pretty-printed MongoDB documents for one real school per pattern.
If a pattern has no real match, it is marked **NOT FOUND**.

## 4.1 — K-8 school

**Almira Elementary School** (NCESSCH `530009000179`)

```json
{
  "_id": "530009000179",
  "name": "Almira Elementary School",
  "district": {
    "name": "Almira School District",
    "nces_id": "5300090"
  },
  "address": {
    "street": "310 S 3RD ST",
    "city": "ALMIRA",
    "state": "WA",
    "zip": "99103"
  },
  "school_type": "Regular School",
  "level": "Elementary",
  "grade_span": {
    "low": "KG",
    "high": "08"
  },
  "is_charter": false,
  "website": "http://www.almirasd.org",
  "phone": "(509)639-2414",
  "metadata": {
    "ospi_district_code": "22017",
    "ospi_school_code": "2860",
    "crdc_combokey": "530009000179",
    "dataset_version": "2026-02-v1",
    "load_timestamp": "2026-02-22T04:02:32.125750+00:00",
    "data_vintage": {
      "ccd_directory": "2023-24",
      "ccd_membership": "2023-24",
      "ospi_enrollment": "2023-24",
      "ospi_assessment": "2023-24",
      "ospi_growth": "2024-25",
      "ospi_sqss": "2024-25",
      "ospi_discipline": "2023-24",
      "ospi_ppe": "2023-24",
      "crdc": "2021-22"
    },
    "join_status": "all_sources"
  },
  "enrollment": {
    "year": "2023-24",
    "total": 129,
    "by_race": {
      "american_indian": 0,
      "asian": 1,
      "black": 1,
      "hispanic": 10,
      "pacific_islander": 0,
      "two_or_more": 6,
      "white": 111
    },
    "by_sex": {
      "male": 66,
      "female": 63
    },
    "crdc_by_race": {
      "hispanic": 11,
      "american_indian": 0,
      "asian": 1,
      "pacific_islander": 0,
      "black": 0,
      "white": 108,
      "two_or_more": 13
    },
    "crdc_total": 133
  },
  "demographics": {
    "year": "2023-24",
    "ospi_total": 133,
    "frl_count": 55,
    "frl_pct": 0.4135,
    "ell_count": 0,
    "sped_count": 19,
    "section_504_count": 8,
    "foster_care_count": 0,
    "homeless_count": 0,
    "migrant_count": 0
  },
  "academics": {
    "assessment": {
      "year": "2023-24",
      "ela_proficiency_pct": null,
      "ela_students_tested": 109,
      "math_proficiency_pct": null,
      "math_students_tested": 109,
      "science_proficiency_pct": 0.539,
      "science_students_tested": 39
    },
    "growth": {
      "year": "2024-25",
      "ela_median_sgp": 52.0,
      "ela_low_growth_count": 29,
      "ela_typical_growth_count": 34,
      "ela_high_growth_count": 35,
      "math_median_sgp": 66.0,
      "math_low_growth_count": 12,
      "math_typical_growth_count": 38,
      "math_high_growth_count": 49
    },
    "ninth_grade_on_track": {
      "year": "2024-25"
    },
    "attendance": {
      "year": "2024-25",
      "regular_attendance_pct": 0.7557,
      "numerator": 99,
      "denominator": 131
    },
    "dual_credit": {
      "year": "2024-25"
    }
  },
  "discipline": {
    "ospi": {
      "year": "2023-24",
      "rate": null,
      "suppressed": true
    },
    "crdc": {
      "year": "2021-22",
      "iss": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "iss_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oos_instances_wodis": 0,
      "oos_instances_idea": 0,
      "oos_instances_504": 0,
      "expulsion_with_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_without_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_zero_tolerance": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "corporal_punishment_indicator": false
    }
  },
  "finance": {
    "year": "2023-24",
    "per_pupil_total": 31405.84,
    "per_pupil_local": 4849.22,
    "per_pupil_state": 25521.84,
    "per_pupil_federal": 1034.77
  },
  "safety": {
    "restraint_seclusion": {
      "mechanical_wodis": 0,
      "mechanical_idea": 0,
      "mechanical_504": 0,
      "physical_wodis": 0,
      "physical_idea": 0,
      "physical_504": 0,
      "seclusion_wodis": 0,
      "seclusion_idea": 0,
      "seclusion_504": 0
    },
    "referrals_arrests": {
      "referrals": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "arrests": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      }
    },
    "harassment_bullying": {
      "allegations_sex": 0,
      "allegations_race": 0,
      "allegations_disability": 0,
      "allegations_religion": 0,
      "allegations_orientation": 0
    },
    "offenses": {
      "firearm_indicator": false,
      "homicide_indicator": false
    }
  },
  "staffing": {
    "year": "2021-22",
    "teacher_fte_total": 11.0,
    "teacher_fte_certified": 8.0,
    "teacher_fte_not_certified": 3.0,
    "counselor_fte": 0.0,
    "nurse_fte": 0.0,
    "psychologist_fte": 0.0,
    "social_worker_fte": 0.0,
    "sro_fte": 0.0,
    "security_guard_fte": 0.0
  },
  "course_access": {
    "ap": {
      "indicator": false
    },
    "dual_enrollment": {
      "indicator": false
    },
    "gifted_talented": {
      "indicator": false
    }
  },
  "derived": {
    "student_teacher_ratio": 11.7,
    "counselor_student_ratio": null,
    "no_counselor": true,
    "chronic_absenteeism_pct": 0.2443,
    "proficiency_composite": null,
    "discipline_disparity": null,
    "discipline_disparity_max": null,
    "discipline_disparity_max_race": null,
    "discipline_disparity_no_white_baseline": true,
    "level_group": "Elementary",
    "enrollment_band": "Small",
    "frl_band": "MidFRL",
    "peer_cohort": "Elementary_Small_MidFRL",
    "percentiles": {
      "ela_proficiency_pct": {
        "state": null,
        "district": null,
        "peer": null
      },
      "math_proficiency_pct": {
        "state": null,
        "district": null,
        "peer": null
      },
      "regular_attendance_pct": {
        "state": 50,
        "district": null,
        "peer": 54
      },
      "student_teacher_ratio": {
        "state": 85,
        "district": null,
        "peer": 58
      },
      "counselor_student_ratio": {
        "state": null,
        "district": null,
        "peer": null
      },
      "per_pupil_total": {
        "state": 94,
        "district": null,
        "peer": 81
      },
      "chronic_absenteeism_pct": {
        "state": 50,
        "district": null,
        "peer": 54
      },
      "discipline_rate": {
        "state": null,
        "district": null,
        "peer": null
      }
    },
    "performance_flag": null,
    "regression_predicted": null,
    "regression_residual": null,
    "regression_zscore": null,
    "regression_group": null,
    "regression_r_squared": null,
    "flags": {
      "chronic_absenteeism": {
        "color": "yellow",
        "raw_value": 0.2443,
        "threshold": 0.2,
        "threshold_source": "USED chronic absenteeism benchmarks (20% yellow, 30% red); aligned with federal Every Student Succeeds Act reporting thresholds and foundation document v0.2.",
        "what_it_means": "More than 20% of students at this school are chronically absent, meaning they miss 10% or more of school days. This is above the threshold researchers identify as a warning sign for academic outcomes.",
        "what_it_might_not_mean": "Chronic absenteeism reflects many factors beyond school quality, including family health crises, transportation barriers, housing instability, and community-wide events. A high rate does not necessarily indicate a school climate problem.",
        "parent_question": "What programs does the school have to support students with attendance challenges, and how has the trend changed over the past two years?"
      },
      "counselor_ratio": {
        "color": null,
        "flag_absent_reason": "data_not_available"
      },
      "discipline_disparity": {
        "color": null,
        "flag_absent_reason": "data_not_available"
      },
      "no_counselor": {
        "color": "red",
        "raw_value": 0.0,
        "threshold_source": "CRDC staffing data reports 0.0 counselor FTE for this school.",
        "what_it_means": "This school reports zero counselor staff. Students at this school do not have access to a dedicated school counselor for academic, social-emotional, or college/career guidance.",
        "what_it_might_not_mean": "Some schools share counselors with other buildings or contract counseling services that may not appear in staffing reports. The school may also use other support models (social workers, community partnerships) not captured in this data.",
        "parent_question": "How does the school provide counseling and social-emotional support to students without a dedicated counselor on staff?"
      }
    },
    "performance_flag_absent_reason": "data_not_available"
  },
  "district_context": {
    "status": "enriched",
    "prompt_version": "v1",
    "validation_prompt_version": "v1",
    "generated_at": "2026-02-23T04:27:31.423894+00:00",
    "model": "claude-haiku-4-5-20251001",
    "cost": {
      "enrichment_input_tokens": 13727,
      "enrichment_output_tokens": 897,
      "validation_input_tokens": 12869,
      "validation_output_tokens": 849,
      "web_search_requests": 2,
      "total_input_tokens": 26596,
      "total_output_tokens": 1746,
      "actual_model": "claude-haiku-4-5-20251001"
    },
    "findings": [
      {
        "category": "investigations_ocr",
        "subcategory": null,
        "summary": "The Washington State Auditor's Office issued a finding against Almira School District for placing a levy request on the February 11, 2020 ballot without creating a required levy expenditure plan. The district sought $215,000 per year for collection in 2021 and 2022.",
        "source_url": "https://www.omakchronicle.com/news/auditor-issues-finding-against-almira-district/article_54e12796-ee67-11eb-a5f0-63327352e387.html",
        "source_name": "Omak Chronicle",
        "source_content_summary": "The Omak Chronicle reported on the Washington State Auditor's Office findings against Almira School District regarding the February 2020 levy request. The article details that the district failed to create a levy expenditure plan, preventing public assurance that proceeds would be spent on allowable enrichment activities. The measure passed with 76.14% voter approval.",
        "date": "2021-07-28",
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Omak Chronicle article confirms the auditor's finding against Almira School District for levy placed on Feb. 11, 2020 ballot without required expenditure plan. District correctly identified as Almira School District in Washington state. Credible news source."
      },
      {
        "category": "leadership",
        "subcategory": null,
        "summary": "Almira School District announced Tim Payne as the new superintendent for the 2024-25 school year, bringing a strong background in education.",
        "source_url": "https://www.almirasd.org/news",
        "source_name": "Almira School District Official Website",
        "source_content_summary": "The district's news page announced the arrival of Tim Payne as the new superintendent for the 2024-25 school year, welcoming him to the district with mention of his educational background.",
        "date": "2024-08-01",
        "confidence": "medium",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Source is official district website (credible), but unable to independently verify the Tim Payne superintendent announcement. Claim is plausible for district-level leadership change, but verification incomplete."
      },
      {
        "category": "programs",
        "subcategory": null,
        "summary": "Almira School District was awarded a Farm-to-School grant that enabled the district to purchase locally sourced food items including beef, flour, and cheese.",
        "source_url": "https://www.almirasd.org/news",
        "source_name": "Almira School District Official Website",
        "source_content_summary": "The district news page announced receipt of a Farm-to-School grant that has been used to purchase locally sourced food products for the school.",
        "date": null,
        "confidence": "low",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Source is official district website (credible), but unable to independently verify the Farm-to-School grant claim. No date provided. Plausible program type but requires verification."
      }
    ],
    "validation_summary": {
      "findings_submitted": 3,
      "findings_confirmed": 1,
      "findings_rejected": 0,
      "findings_downgraded": 2,
      "wrong_school_detected": 0
    },
    "error": null,
    "district_name": "Almira School District"
  },
  "layer3_narrative": {
    "text": "In 2021, the Washington State Auditor's Office issued a finding against the district for placing a levy request on the ballot without creating a required levy expenditure plan. At the district level, the levy had sought $215,000 per year for collection in 2021 and 2022. The cited records do not reflect a resolution. [Sources: https://www.omakchronicle.com/news/auditor-issues-finding-against-almira-district/article_54e12796-ee67-11eb-a5f0-63327352e387.html]",
    "model": "claude-sonnet-4-6",
    "source_findings_count": 3,
    "stage0_dropped_count": 0,
    "stage1_included_count": 1,
    "stage1_excluded_count": 2,
    "status": "ok",
    "error": null,
    "generated_at": "2026-05-02T01:40:37.147378+00:00",
    "prompt_version": "layer3_v3"
  }
}
```

## 4.2 — Small school in peer cohort with < 5 members

**NOT FOUND** — no school in MongoDB matches this pattern.

(Selected from any cohort with < 5 members; preference given to schools with Rural locale labeling but the dataset's locale field varies. School below is a real cohort-<5 case.)

**Query attempted**:
```python
schools.find({"derived.peer_cohort":{"$in":[<small cohorts>]}})
```

## 4.3 — 'Other' level school with non-null regression output

**Catalyst Public Schools** (NCESSCH `530034703723`)

```json
{
  "_id": "530034703723",
  "name": "Catalyst Public Schools",
  "district": {
    "name": "Catalyst Public Schools",
    "nces_id": "5300347"
  },
  "address": {
    "street": "1305 Ironsides Ave",
    "city": "Bremerton",
    "state": "WA",
    "zip": "98310"
  },
  "school_type": "Regular School",
  "level": "Other",
  "grade_span": {
    "low": "KG",
    "high": "09"
  },
  "is_charter": true,
  "website": "",
  "phone": "(360)207-0229",
  "metadata": {
    "ospi_district_code": "18901",
    "ospi_school_code": "5607",
    "crdc_combokey": "530034703723",
    "dataset_version": "2026-02-v1",
    "load_timestamp": "2026-02-22T04:02:32.125750+00:00",
    "data_vintage": {
      "ccd_directory": "2023-24",
      "ccd_membership": "2023-24",
      "ospi_enrollment": "2023-24",
      "ospi_assessment": "2023-24",
      "ospi_growth": "2024-25",
      "ospi_sqss": "2024-25",
      "ospi_discipline": "2023-24",
      "ospi_ppe": "2023-24",
      "crdc": "2021-22"
    },
    "join_status": "all_sources"
  },
  "enrollment": {
    "year": "2023-24",
    "total": 504,
    "by_race": {
      "american_indian": 4,
      "asian": 20,
      "black": 43,
      "hispanic": 94,
      "pacific_islander": 1,
      "two_or_more": 58,
      "white": 280,
      "not_specified": 4
    },
    "by_sex": {
      "male": 276,
      "female": 224
    },
    "crdc_by_race": {
      "hispanic": 36,
      "american_indian": 1,
      "asian": 9,
      "pacific_islander": 1,
      "black": 27,
      "white": 188,
      "two_or_more": 39
    },
    "crdc_total": 301
  },
  "demographics": {
    "year": "2023-24",
    "ospi_total": 485,
    "frl_count": 228,
    "frl_pct": 0.4701,
    "ell_count": 0,
    "sped_count": 75,
    "section_504_count": 10,
    "foster_care_count": 0,
    "homeless_count": 0,
    "migrant_count": 0
  },
  "academics": {
    "assessment": {
      "year": "2023-24",
      "ela_proficiency_pct": 0.513,
      "ela_students_tested": 310,
      "math_proficiency_pct": 0.46,
      "math_students_tested": 309,
      "science_proficiency_pct": 0.526,
      "science_students_tested": 95
    },
    "growth": {
      "year": "2024-25",
      "ela_median_sgp": 48.0,
      "ela_low_growth_count": 66,
      "ela_typical_growth_count": 80,
      "ela_high_growth_count": 68,
      "math_median_sgp": 49.0,
      "math_low_growth_count": 73,
      "math_typical_growth_count": 69,
      "math_high_growth_count": 69
    },
    "ninth_grade_on_track": {
      "year": "2024-25"
    },
    "attendance": {
      "year": "2024-25",
      "regular_attendance_pct": 0.7644,
      "numerator": 331,
      "denominator": 433
    },
    "dual_credit": {
      "year": "2024-25"
    }
  },
  "discipline": {
    "ospi": {
      "year": "2023-24",
      "rate": 0.061900000000000004,
      "numerator": 32,
      "denominator": 517
    },
    "crdc": {
      "year": "2021-22",
      "iss": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 2,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "iss_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single": {
        "hispanic_male": 1,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 1,
        "white_male": 1,
        "white_female": 3,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 1,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple": {
        "hispanic_male": 1,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 2,
        "black_female": 0,
        "white_male": 0,
        "white_female": 1,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 1,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oos_instances_wodis": 14,
      "oos_instances_idea": 3,
      "oos_instances_504": 0,
      "expulsion_with_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_without_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_zero_tolerance": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "corporal_punishment_indicator": false
    }
  },
  "finance": {
    "year": "2023-24",
    "per_pupil_total": 16633.25,
    "per_pupil_local": 0.0,
    "per_pupil_state": 16145.3,
    "per_pupil_federal": 487.96
  },
  "safety": {
    "restraint_seclusion": {
      "mechanical_wodis": 0,
      "mechanical_idea": 0,
      "mechanical_504": 0,
      "physical_wodis": 1,
      "physical_idea": 0,
      "physical_504": 0,
      "seclusion_wodis": 0,
      "seclusion_idea": 0,
      "seclusion_504": 0
    },
    "referrals_arrests": {
      "referrals": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "arrests": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      }
    },
    "harassment_bullying": {
      "allegations_sex": 0,
      "allegations_race": 0,
      "allegations_disability": 0,
      "allegations_religion": 0,
      "allegations_orientation": 0
    },
    "offenses": {
      "firearm_indicator": false,
      "homicide_indicator": false
    }
  },
  "staffing": {
    "year": "2021-22",
    "teacher_fte_total": 24.0,
    "teacher_fte_certified": 14.0,
    "teacher_fte_not_certified": 10.0,
    "counselor_fte": 0.0,
    "nurse_fte": 0.0,
    "psychologist_fte": 0.0,
    "social_worker_fte": 0.0,
    "sro_fte": 0.0,
    "security_guard_fte": 0.0
  },
  "course_access": {
    "ap": {
      "indicator": false
    },
    "dual_enrollment": {
      "indicator": false
    },
    "gifted_talented": {
      "indicator": false
    }
  },
  "derived": {
    "student_teacher_ratio": 21.0,
    "counselor_student_ratio": null,
    "no_counselor": true,
    "chronic_absenteeism_pct": 0.2356,
    "proficiency_composite": 0.4865,
    "discipline_disparity": {
      "hispanic": 1.49,
      "black": 2.98,
      "two_or_more": 0.0
    },
    "discipline_disparity_max": 2.98,
    "discipline_disparity_max_race": "black",
    "level_group": "Other",
    "enrollment_band": "Large",
    "frl_band": "MidFRL",
    "peer_cohort": "Other_Large_MidFRL",
    "percentiles": {
      "ela_proficiency_pct": {
        "state": 55,
        "district": null,
        "peer": null
      },
      "math_proficiency_pct": {
        "state": 61,
        "district": null,
        "peer": 90
      },
      "regular_attendance_pct": {
        "state": 53,
        "district": null,
        "peer": 42
      },
      "student_teacher_ratio": {
        "state": 15,
        "district": null,
        "peer": 83
      },
      "counselor_student_ratio": {
        "state": null,
        "district": null,
        "peer": null
      },
      "per_pupil_total": {
        "state": 23,
        "district": null,
        "peer": 64
      },
      "chronic_absenteeism_pct": {
        "state": 53,
        "district": null,
        "peer": 42
      },
      "discipline_rate": {
        "state": 22,
        "district": null,
        "peer": null
      }
    },
    "performance_flag": "as_expected",
    "regression_predicted": 0.4888,
    "regression_residual": -0.0023,
    "regression_zscore": -0.02,
    "regression_group": "statewide",
    "regression_r_squared": 0.685,
    "flags": {
      "chronic_absenteeism": {
        "color": "yellow",
        "raw_value": 0.2356,
        "threshold": 0.2,
        "threshold_source": "USED chronic absenteeism benchmarks (20% yellow, 30% red); aligned with federal Every Student Succeeds Act reporting thresholds and foundation document v0.2.",
        "what_it_means": "More than 20% of students at this school are chronically absent, meaning they miss 10% or more of school days. This is above the threshold researchers identify as a warning sign for academic outcomes.",
        "what_it_might_not_mean": "Chronic absenteeism reflects many factors beyond school quality, including family health crises, transportation barriers, housing instability, and community-wide events. A high rate does not necessarily indicate a school climate problem.",
        "parent_question": "What programs does the school have to support students with attendance challenges, and how has the trend changed over the past two years?"
      },
      "counselor_ratio": {
        "color": null,
        "flag_absent_reason": "data_not_available"
      },
      "discipline_disparity": {
        "color": "yellow",
        "raw_value": 2.98,
        "threshold": 2.0,
        "threshold_source": "Discipline disparity ratio compares suspension rates of each racial group to white students. A ratio of 2.0 means a group is suspended at twice the rate. Thresholds aligned with OCR enforcement guidance and ProPublica Miseducation methodology; foundation document v0.2.",
        "what_it_means": "At least one racial group at this school is suspended at more than twice the rate of white students. This pattern is common nationwide but warrants attention as a potential equity concern.",
        "what_it_might_not_mean": "Disparity ratios do not prove discrimination. Differences may reflect referral patterns, policy implementation, community factors, or small sample sizes that amplify individual incidents. The ratio identifies a pattern worth investigating, not a conclusion.",
        "parent_question": "Is the school aware of differences in discipline rates across student groups, and what steps are being taken to ensure equitable discipline practices?"
      },
      "no_counselor": {
        "color": "red",
        "raw_value": 0.0,
        "threshold_source": "CRDC staffing data reports 0.0 counselor FTE for this school.",
        "what_it_means": "This school reports zero counselor staff. Students at this school do not have access to a dedicated school counselor for academic, social-emotional, or college/career guidance.",
        "what_it_might_not_mean": "Some schools share counselors with other buildings or contract counseling services that may not appear in staffing reports. The school may also use other support models (social workers, community partnerships) not captured in this data.",
        "parent_question": "How does the school provide counseling and social-emotional support to students without a dedicated counselor on staff?"
      }
    }
  },
  "district_context": {
    "status": "enriched",
    "prompt_version": "v1",
    "validation_prompt_version": "v1",
    "generated_at": "2026-02-23T04:37:03.308715+00:00",
    "model": "claude-haiku-4-5-20251001",
    "cost": {
      "enrichment_input_tokens": 40185,
      "enrichment_output_tokens": 1268,
      "validation_input_tokens": 17526,
      "validation_output_tokens": 1295,
      "web_search_requests": 3,
      "total_input_tokens": 57711,
      "total_output_tokens": 2563,
      "actual_model": "claude-haiku-4-5-20251001"
    },
    "findings": [
      {
        "category": "awards_recognition",
        "subcategory": null,
        "summary": "Catalyst Public Schools achieved a U.S. News Best Middle Schools award badge eligibility based on high rankings for educational excellence across 2021-2024 school years.",
        "source_url": "https://www.usnews.com/education/k12/washington/catalyst-public-schools-432916",
        "source_name": "U.S. News Education",
        "source_content_summary": "School profile showing Catalyst's eligibility for the U.S. News Best Middle Schools award badge based on high rankings and educational excellence metrics from recent school years.",
        "date": null,
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "U.S. News source confirms Catalyst Public Schools (Bremerton, WA) earned eligibility for Best Middle Schools award badge based on 2021-2024 school year data. Correct district and state."
      },
      {
        "category": "programs",
        "subcategory": null,
        "summary": "Catalyst Public Schools expanded its high school program, with 9th grade launching in fall 2024 and plans to add grades sequentially through 12th grade.",
        "source_url": "https://www.catalystpublicschools.org/",
        "source_name": "Catalyst Public Schools Official Website",
        "source_content_summary": "School website indicating that the high school program launched 9th grade in fall 2024, with plans to age grades through K-12 expansion over subsequent years.",
        "date": "2024-09-01",
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Official Catalyst website confirms 9th grade launched fall 2024 with plans to add grades sequentially through K-12. Correct district and state."
      },
      {
        "category": "awards_recognition",
        "subcategory": null,
        "summary": "Washington statewide standardized test scores from 2023-2024 show Catalyst Public Schools is among the best public schools in the state, particularly for serving historically underserved students including low-income students, students with special needs, and students of color.",
        "source_url": "https://nwasianweekly.com/2025/02/this-high-performing-public-school-delivers-big-gains-for-underserved-students/",
        "source_name": "Northwest Asian Weekly",
        "source_content_summary": "Article highlighting Catalyst's 2023-24 SBAC test performance showing superior results for economically disadvantaged students (outperforming district peers by 13-16 points in ELA and math), special needs students (9.2 points higher), Black students (5.3 points higher), and Latino students (28.1 points higher in proficiency).",
        "date": "2025-02-11",
        "confidence": "medium",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Source (Northwest Asian Weekly, Feb 2025) is credible, and SBAC test scores for 2023-24 are confirmed for Catalyst. However, specific performance comparisons cited (13-16 points for economically disadvantaged, 9.2 points for special needs, etc.) cannot be verified from available search results. The article exists and appears legitimate but specific claims are unconfirmed."
      },
      {
        "category": "other",
        "subcategory": "staff_retention_concerns",
        "summary": "Community reviews on Niche report consistently high staff turnover since the school's early years, with staff concerns about limited support documented as early as year two of operation. In the 2024-25 school year, four out of five teachers in some classrooms left mid-year.",
        "source_url": "https://www.niche.com/k12/catalyst-public-schools-bremerton-wa/",
        "source_name": "Niche",
        "source_content_summary": "Parent and staff review noting persistent high staff turnover patterns, documented concerns by staff to the Board about limited support, classroom disruptions from chronic absences and resignations, and specific account of four of five teachers leaving mid-year during 2024-25.",
        "date": "2024-25",
        "confidence": "medium",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Niche source directly confirms high staff turnover since early years, staff concerns by year two, and specific account of four out of five teachers leaving mid-year in 2024-25. Accurate and well-sourced."
      },
      {
        "category": "other",
        "subcategory": "equity_and_inclusion_concerns",
        "summary": "Former BIPOC staff members reported concerns about whether the school's diversity, equity, and inclusion commitments are fully reflected in day-to-day practices, including equity in pay, hiring practices, and student academic support.",
        "source_url": "https://www.niche.com/k12/catalyst-public-schools-bremerton-wa/",
        "source_name": "Niche",
        "source_content_summary": "Staff review noting that while Catalyst publicly emphasizes equity and inclusion, several former BIPOC staff members reported that their concerns were minimized and questioned whether DEIB commitments are reflected in practices around pay equity, hiring, and student support.",
        "date": null,
        "confidence": "medium",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Niche source directly confirms former BIPOC staff concerns about whether DEIB commitments are reflected in pay equity, hiring, and student support practices. Accurate quote and sourcing."
      }
    ],
    "validation_summary": {
      "findings_submitted": 5,
      "findings_confirmed": 4,
      "findings_rejected": 0,
      "findings_downgraded": 1,
      "wrong_school_detected": 0
    },
    "error": null,
    "district_name": "Catalyst Public Schools"
  },
  "layer3_narrative": {
    "text": "In the 2024\u201325 school year, community reviews documented a pattern of staff turnover at Catalyst Public Schools, with reports indicating that four out of five teachers in some classrooms left mid-year. Concerns about limited staff support were noted in available records as early as the school's second year of operation. [Sources: https://www.niche.com/k12/catalyst-public-schools-bremerton-wa/]\n\nIn an undated report, former staff members raised concerns about whether the school's stated commitments to diversity, equity, and inclusion were fully reflected in day-to-day practices, including equity in pay, hiring practices, and student academic support. The cited records do not reflect a resolution of these concerns. [Sources: https://www.niche.com/k12/catalyst-public-schools-bremerton-wa/]",
    "model": "claude-sonnet-4-6",
    "source_findings_count": 5,
    "stage0_dropped_count": 0,
    "stage1_included_count": 2,
    "stage1_excluded_count": 3,
    "status": "ok",
    "error": null,
    "generated_at": "2026-05-02T01:41:58.779398+00:00",
    "prompt_version": "layer3_v3"
  }
}
```

## 4.4 — School with all four climate/equity flags at red

**Windsor Elementary** (NCESSCH `530123000228`)

**NOTE — no school can carry all four flags at red simultaneously.** `no_counselor` requires `staffing.counselor_fte == 0`; `counselor_ratio` requires `counselor_fte > 0` to compute the ratio. These two flags are mutually exclusive by definition. Showing the closest match: all three threshold flags red, no_counselor not applicable.

```json
{
  "_id": "530123000228",
  "name": "Windsor Elementary",
  "district": {
    "name": "Cheney School District",
    "nces_id": "5301230"
  },
  "address": {
    "street": "5504 W HALLETT RD",
    "city": "SPOKANE",
    "state": "WA",
    "zip": "99224"
  },
  "school_type": "Regular School",
  "level": "Elementary",
  "grade_span": {
    "low": "PK",
    "high": "05"
  },
  "is_charter": false,
  "website": "",
  "phone": "(509)559-4200",
  "metadata": {
    "ospi_district_code": "32360",
    "ospi_school_code": "3309",
    "crdc_combokey": "530123000228",
    "dataset_version": "2026-02-v1",
    "load_timestamp": "2026-02-22T04:02:32.125750+00:00",
    "data_vintage": {
      "ccd_directory": "2023-24",
      "ccd_membership": "2023-24",
      "ospi_enrollment": "2023-24",
      "ospi_assessment": "2023-24",
      "ospi_growth": "2024-25",
      "ospi_sqss": "2024-25",
      "ospi_discipline": "2023-24",
      "ospi_ppe": "2023-24",
      "crdc": "2021-22"
    },
    "join_status": "all_sources"
  },
  "enrollment": {
    "year": "2023-24",
    "total": 549,
    "by_race": {
      "american_indian": 3,
      "asian": 5,
      "black": 4,
      "hispanic": 76,
      "pacific_islander": 4,
      "two_or_more": 44,
      "white": 413
    },
    "by_sex": {
      "male": 303,
      "female": 246
    },
    "crdc_by_race": {
      "hispanic": 61,
      "american_indian": 6,
      "asian": 6,
      "pacific_islander": 3,
      "black": 4,
      "white": 408,
      "two_or_more": 37
    },
    "crdc_total": 525
  },
  "demographics": {
    "year": "2023-24",
    "ospi_total": 585,
    "frl_count": 273,
    "frl_pct": 0.4667,
    "ell_count": 54,
    "sped_count": 124,
    "section_504_count": 10,
    "foster_care_count": 0,
    "homeless_count": 11,
    "migrant_count": 0
  },
  "academics": {
    "assessment": {
      "year": "2023-24",
      "ela_proficiency_pct": 0.574,
      "math_proficiency_pct": 0.534,
      "science_proficiency_pct": 0.645,
      "ela_students_tested": 279,
      "math_students_tested": 279,
      "science_students_tested": 93
    },
    "growth": {
      "year": "2024-25",
      "ela_median_sgp": 43.0,
      "ela_low_growth_count": 70,
      "ela_typical_growth_count": 68,
      "ela_high_growth_count": 42,
      "math_median_sgp": 50.0,
      "math_low_growth_count": 56,
      "math_typical_growth_count": 58,
      "math_high_growth_count": 57
    },
    "ninth_grade_on_track": {
      "year": "2024-25"
    },
    "attendance": {
      "year": "2024-25",
      "regular_attendance_pct": 0.6423,
      "numerator": 343,
      "denominator": 534
    },
    "dual_credit": {
      "year": "2024-25"
    }
  },
  "discipline": {
    "ospi": {
      "year": "2023-24",
      "rate": 0.0141,
      "numerator": 8,
      "denominator": 567
    },
    "crdc": {
      "year": "2021-22",
      "iss": {
        "hispanic_male": 3,
        "hispanic_female": 1,
        "american_indian_male": 1,
        "american_indian_female": 1,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 6,
        "white_female": 2,
        "two_or_more_male": 0,
        "two_or_more_female": 1
      },
      "iss_idea": {
        "hispanic_male": 3,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single": {
        "hispanic_male": 2,
        "hispanic_female": 1,
        "american_indian_male": 1,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 1,
        "white_female": 2,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 3,
        "white_female": 0,
        "two_or_more_male": 1,
        "two_or_more_female": 0
      },
      "oss_multiple": {
        "hispanic_male": 1,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 2,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 1,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oos_instances_wodis": 13,
      "oos_instances_idea": 4,
      "oos_instances_504": 0,
      "expulsion_with_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_without_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_zero_tolerance": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "corporal_punishment_indicator": false
    }
  },
  "finance": {
    "year": "2023-24",
    "per_pupil_total": 16806.09,
    "per_pupil_local": 1188.59,
    "per_pupil_state": 14573.4,
    "per_pupil_federal": 1044.1
  },
  "safety": {
    "restraint_seclusion": {
      "mechanical_wodis": 0,
      "mechanical_idea": 16,
      "mechanical_504": 0,
      "physical_wodis": 0,
      "physical_idea": 12,
      "physical_504": 0,
      "seclusion_wodis": 0,
      "seclusion_idea": 50,
      "seclusion_504": 0
    },
    "referrals_arrests": {
      "referrals": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "arrests": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      }
    },
    "harassment_bullying": {
      "allegations_sex": 0,
      "allegations_race": 0,
      "allegations_disability": 0,
      "allegations_religion": 0,
      "allegations_orientation": 1
    },
    "offenses": {
      "firearm_indicator": false,
      "homicide_indicator": false
    }
  },
  "staffing": {
    "year": "2021-22",
    "teacher_fte_total": 37.779999,
    "teacher_fte_certified": 37.779999,
    "teacher_fte_not_certified": 0.0,
    "counselor_fte": 1.0,
    "nurse_fte": 1.0,
    "psychologist_fte": 1.0,
    "social_worker_fte": 0.0,
    "sro_fte": 0.0,
    "security_guard_fte": 0.0
  },
  "course_access": {
    "ap": {
      "indicator": false
    },
    "dual_enrollment": {
      "indicator": false
    },
    "gifted_talented": {
      "indicator": true,
      "enrollment_by_race": {
        "hispanic_male": 2,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 1,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 8,
        "white_female": 12,
        "two_or_more_male": 2,
        "two_or_more_female": 0
      }
    }
  },
  "derived": {
    "student_teacher_ratio": 14.5,
    "counselor_student_ratio": 549.0,
    "no_counselor": false,
    "chronic_absenteeism_pct": 0.3577,
    "proficiency_composite": 0.554,
    "discipline_disparity": {
      "hispanic": 4.12,
      "two_or_more": 0.85
    },
    "discipline_disparity_max": 4.12,
    "discipline_disparity_max_race": "hispanic",
    "level_group": "Elementary",
    "enrollment_band": "Large",
    "frl_band": "MidFRL",
    "peer_cohort": "Elementary_Large_MidFRL",
    "percentiles": {
      "ela_proficiency_pct": {
        "state": 66,
        "district": 94,
        "peer": 82
      },
      "math_proficiency_pct": {
        "state": 72,
        "district": 94,
        "peer": 69
      },
      "regular_attendance_pct": {
        "state": 19,
        "district": 38,
        "peer": 6
      },
      "student_teacher_ratio": {
        "state": 64,
        "district": 95,
        "peer": 74
      },
      "counselor_student_ratio": {
        "state": 13,
        "district": 17,
        "peer": 43
      },
      "per_pupil_total": {
        "state": 25,
        "district": 79,
        "peer": 18
      },
      "chronic_absenteeism_pct": {
        "state": 19,
        "district": 38,
        "peer": 6
      },
      "discipline_rate": {
        "state": 79,
        "district": 95,
        "peer": 64
      }
    },
    "performance_flag": "as_expected",
    "regression_predicted": 0.5129,
    "regression_residual": 0.0411,
    "regression_zscore": 0.45,
    "regression_group": "Elementary",
    "regression_r_squared": 0.747,
    "flags": {
      "chronic_absenteeism": {
        "color": "red",
        "raw_value": 0.3577,
        "threshold": 0.3,
        "threshold_source": "USED chronic absenteeism benchmarks (20% yellow, 30% red); aligned with federal Every Student Succeeds Act reporting thresholds and foundation document v0.2.",
        "what_it_means": "More than 30% of students at this school are chronically absent. At this level, a significant share of students are missing enough school to meaningfully affect their learning outcomes.",
        "what_it_might_not_mean": "Chronic absenteeism reflects many factors beyond school quality, including family health crises, transportation barriers, housing instability, and community-wide events. A high rate does not necessarily indicate a school climate problem.",
        "parent_question": "What is the school doing to address chronic absenteeism, and are there specific supports available for families facing attendance barriers?"
      },
      "counselor_ratio": {
        "color": "red",
        "raw_value": 549.0,
        "threshold": 500,
        "threshold_source": "American School Counselor Association (ASCA) recommends a maximum ratio of 1:250. Thresholds of 1:400 (yellow) and 1:500 (red) are set conservatively above the recommendation; foundation document v0.2.",
        "what_it_means": "This school has more than 500 students per counselor. At this level, meaningful individual counseling is very difficult to provide. Research links high counselor caseloads to lower college enrollment rates and reduced social-emotional support.",
        "what_it_might_not_mean": "Some schools supplement counselor roles with other support staff (social workers, psychologists, community partners) not captured in this ratio. The ratio alone does not tell you whether students feel supported.",
        "parent_question": "Does the school have plans to add counseling capacity, and what alternative support resources are available to students?"
      },
      "discipline_disparity": {
        "color": "red",
        "raw_value": 4.12,
        "threshold": 3.0,
        "threshold_source": "Discipline disparity ratio compares suspension rates of each racial group to white students. A ratio of 2.0 means a group is suspended at twice the rate. Thresholds aligned with OCR enforcement guidance and ProPublica Miseducation methodology; foundation document v0.2.",
        "what_it_means": "At least one racial group at this school is suspended at more than three times the rate of white students. This level of disparity is a significant equity concern that federal civil rights guidance identifies as warranting investigation.",
        "what_it_might_not_mean": "Disparity ratios do not prove discrimination. Differences may reflect referral patterns, policy implementation, community factors, or small sample sizes that amplify individual incidents. The CRDC data is from 2021-22 and may not reflect current practices.",
        "parent_question": "Has the school conducted a discipline equity audit, and what specific changes have been made to address disparities in suspension rates?"
      }
    }
  },
  "district_context": {
    "status": "enriched",
    "prompt_version": "v1",
    "validation_prompt_version": "v1",
    "generated_at": "2026-02-23T04:39:45.692809+00:00",
    "model": "claude-haiku-4-5-20251001",
    "cost": {
      "enrichment_input_tokens": 15674,
      "enrichment_output_tokens": 588,
      "validation_input_tokens": 14220,
      "validation_output_tokens": 791,
      "web_search_requests": 2,
      "total_input_tokens": 29894,
      "total_output_tokens": 1379,
      "actual_model": "claude-haiku-4-5-20251001"
    },
    "findings": [
      {
        "category": "investigations_ocr",
        "subcategory": null,
        "summary": "The U.S. Department of Education's Office for Civil Rights launched a federal Title IX investigation into Cheney Public Schools in January 2026, alleging discrimination over the district's policy allowing transgender students to compete in sports based on gender identity. The investigation was triggered by complaints regarding a transgender student athlete competing on the girls' track team.",
        "source_url": "https://www.spokesman.com/stories/2026/jan/15/feds-investigate-cheney-public-schools-4-other-wa-/",
        "source_name": "Spokesman Review",
        "source_content_summary": "Reports on the federal Department of Education investigation into Cheney Public Schools and three other Washington districts over transgender student athlete policies, noting the district allows trans students to participate in sports aligned with their gender identity under state law.",
        "date": "2026-01-15",
        "confidence": "high",
        "sensitivity": "high",
        "validated": true,
        "validation_notes": "Multiple credible sources (Spokesman Review, KREM, Fox 13, KUOW, OPB) confirm the Department of Education's Office for Civil Rights investigation into Cheney Public Schools. Investigation concerns a transgender student athlete on the girls' track team. Date (January 2026) is accurate. Correct district and state. This is a district-level policy matter."
      },
      {
        "category": "investigations_ocr",
        "subcategory": null,
        "summary": "In July 2024, a court awarded $3 million to a former student who was sexually abused by Michael Alstad, former Cheney High School band director. Alstad allegedly groomed and sexually abused the teenage student for two years.",
        "source_url": "https://www.levylaw.com/washington-schools-sexual-abuse-lawsuits/",
        "source_name": "Levy Konigsberg LLP",
        "source_content_summary": "Legal page documenting Washington school sexual abuse lawsuits, including a case against Cheney School District where a court awarded $3 million to a former student in July 2024 for sexual abuse by music director Michael Alstad.",
        "date": "2024-07-01",
        "confidence": "medium",
        "sensitivity": "high",
        "validated": true,
        "validation_notes": "Unable to fully verify this claim due to search limitations. The source (Levy Konigsberg LLP law firm) is credible for legal matters, but the specific details about Michael Alstad, the $3 million award, the July 2024 date, and the circumstances cannot be confirmed at this time. The claim involves a single school's band director, which is school-level rather than district-level, though it may still be relevant to district oversight. Recommend verifying through news archives or official district records."
      }
    ],
    "validation_summary": {
      "findings_submitted": 2,
      "findings_confirmed": 1,
      "findings_rejected": 0,
      "findings_downgraded": 1,
      "wrong_school_detected": 0
    },
    "error": null,
    "district_name": "Cheney School District"
  },
  "context": {
    "status": "no_findings",
    "prompt_version": "v1",
    "validation_prompt_version": "v1",
    "generated_at": "2026-04-30T07:37:31.447514+00:00",
    "model": "claude-haiku-4-5-20251001",
    "cost": {
      "enrichment_input_tokens": 30667,
      "enrichment_output_tokens": 390,
      "validation_input_tokens": 0,
      "validation_output_tokens": 0,
      "web_search_requests": 2,
      "total_input_tokens": 30667,
      "total_output_tokens": 390,
      "actual_model": "claude-haiku-4-5-20251001"
    },
    "findings": [],
    "validation_summary": null,
    "error": null
  },
  "layer3_narrative": {
    "text": "In 2024, a court awarded $3 million to a former student following a finding that the student had been sexually abused by a former band director at a district high school. According to available records, the abuse allegedly occurred over a two-year period during the student's enrollment. This matter arose at the district level and is relevant to all schools within the Cheney School District. [Sources: https://www.levylaw.com/washington-schools-sexual-abuse-lawsuits/]\n\nSeparately, in 2026, the U.S. Department of Education's Office for Civil Rights opened a federal Title IX investigation into the Cheney School District concerning the district's policy allowing students to compete in sports based on gender identity. The investigation was initiated following complaints related to a student athlete participating on a sports team. As reported in January 2026, the investigation was underway; the cited records do not reflect a resolution. [Sources: https://www.spokesman.com/stories/2026/jan/15/feds-investigate-cheney-public-schools-4-other-wa-/]",
    "model": "claude-sonnet-4-6",
    "source_findings_count": 2,
    "stage0_dropped_count": 0,
    "stage1_included_count": 2,
    "stage1_excluded_count": 0,
    "status": "ok",
    "error": null,
    "generated_at": "2026-05-02T01:41:50.583057+00:00",
    "prompt_version": "layer3_v3"
  }
}
```

## 4.5 — performance_flag null because suppressed_n_lt_10

**NOT FOUND** — no school in MongoDB matches this pattern.

**Query attempted**:
```python
schools.find_one({"derived.performance_flag":None,"derived.performance_flag_absent_reason":"suppressed_n_lt_10"})
```

## 4.6 — performance_flag null because grade_span_not_tested

**JJ Smith Elementary** (NCESSCH `530000103598`)

```json
{
  "_id": "530000103598",
  "name": "JJ Smith Elementary",
  "district": {
    "name": "Enumclaw School District",
    "nces_id": "5300001"
  },
  "address": {
    "street": "1640 Fell Street",
    "city": "Enumclaw",
    "state": "WA",
    "zip": "98022"
  },
  "school_type": "Regular School",
  "level": "Elementary",
  "grade_span": {
    "low": "PK",
    "high": "KG"
  },
  "is_charter": false,
  "website": "",
  "phone": "(360)272-5709",
  "metadata": {
    "ospi_district_code": "17216",
    "ospi_school_code": "5491",
    "crdc_combokey": "530000103598",
    "dataset_version": "2026-02-v1",
    "load_timestamp": "2026-02-22T04:02:32.125750+00:00",
    "data_vintage": {
      "ccd_directory": "2023-24",
      "ccd_membership": "2023-24",
      "ospi_enrollment": "2023-24",
      "ospi_assessment": "2023-24",
      "ospi_growth": "2024-25",
      "ospi_sqss": "2024-25",
      "ospi_discipline": "2023-24",
      "ospi_ppe": "2023-24",
      "crdc": "2021-22"
    },
    "join_status": "all_sources"
  },
  "enrollment": {
    "year": "2023-24",
    "total": 176,
    "by_race": {
      "american_indian": 1,
      "asian": 20,
      "black": 2,
      "hispanic": 37,
      "pacific_islander": 0,
      "two_or_more": 10,
      "white": 106
    },
    "by_sex": {
      "male": 106,
      "female": 70
    },
    "crdc_by_race": {
      "hispanic": 1,
      "american_indian": 0,
      "asian": 7,
      "pacific_islander": 0,
      "black": 0,
      "white": 8,
      "two_or_more": 2
    },
    "crdc_total": 18
  },
  "demographics": {
    "year": "2023-24",
    "ospi_total": 175,
    "frl_count": 131,
    "frl_pct": 0.7486,
    "ell_count": 8,
    "sped_count": 99,
    "section_504_count": 0,
    "foster_care_count": 0,
    "homeless_count": 11,
    "migrant_count": 0
  },
  "academics": {
    "attendance": {
      "year": "2024-25",
      "regular_attendance_pct": 0.923,
      "numerator": null,
      "denominator": null
    },
    "ninth_grade_on_track": {
      "year": "2024-25"
    },
    "dual_credit": {
      "year": "2024-25"
    }
  },
  "discipline": {
    "ospi": {
      "year": "2023-24",
      "rate": null,
      "suppressed": true
    },
    "crdc": {
      "year": "2021-22",
      "iss": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "iss_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_single_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oss_multiple_idea": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "oos_instances_wodis": 0,
      "oos_instances_idea": 0,
      "oos_instances_504": 0,
      "expulsion_with_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_without_ed": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "expulsion_zero_tolerance": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "corporal_punishment_indicator": false
    }
  },
  "finance": {
    "year": "2023-24",
    "per_pupil_total": 26002.51,
    "per_pupil_local": 11618.99,
    "per_pupil_state": 13911.4,
    "per_pupil_federal": 472.12
  },
  "safety": {
    "restraint_seclusion": {
      "mechanical_wodis": 0,
      "mechanical_idea": 0,
      "mechanical_504": 0,
      "physical_wodis": 0,
      "physical_idea": 0,
      "physical_504": 0,
      "seclusion_wodis": 0,
      "seclusion_idea": 0,
      "seclusion_504": 0
    },
    "referrals_arrests": {
      "referrals": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      },
      "arrests": {
        "hispanic_male": 0,
        "hispanic_female": 0,
        "american_indian_male": 0,
        "american_indian_female": 0,
        "asian_male": 0,
        "asian_female": 0,
        "pacific_islander_male": 0,
        "pacific_islander_female": 0,
        "black_male": 0,
        "black_female": 0,
        "white_male": 0,
        "white_female": 0,
        "two_or_more_male": 0,
        "two_or_more_female": 0
      }
    },
    "harassment_bullying": {
      "allegations_sex": 0,
      "allegations_race": 0,
      "allegations_disability": 0,
      "allegations_religion": 0,
      "allegations_orientation": 0
    },
    "offenses": {
      "firearm_indicator": false,
      "homicide_indicator": false
    }
  },
  "staffing": {
    "year": "2021-22",
    "teacher_fte_total": 6.0,
    "teacher_fte_certified": 6.0,
    "teacher_fte_not_certified": 0.0,
    "counselor_fte": 0.0,
    "nurse_fte": 0.0,
    "psychologist_fte": 0.5,
    "social_worker_fte": 0.0,
    "sro_fte": 0.0,
    "security_guard_fte": 0.0
  },
  "course_access": {
    "ap": {
      "indicator": false
    },
    "dual_enrollment": {
      "indicator": false
    },
    "gifted_talented": {
      "indicator": false
    }
  },
  "derived": {
    "student_teacher_ratio": 29.3,
    "counselor_student_ratio": null,
    "no_counselor": true,
    "chronic_absenteeism_pct": 0.077,
    "proficiency_composite": null,
    "discipline_disparity": null,
    "discipline_disparity_max": null,
    "discipline_disparity_max_race": null,
    "discipline_disparity_no_white_baseline": true,
    "level_group": "Elementary",
    "enrollment_band": "Small",
    "frl_band": "HighFRL",
    "peer_cohort": "Elementary_Small_HighFRL",
    "percentiles": {
      "ela_proficiency_pct": {
        "state": null,
        "district": null,
        "peer": null
      },
      "math_proficiency_pct": {
        "state": null,
        "district": null,
        "peer": null
      },
      "regular_attendance_pct": {
        "state": 90,
        "district": 94,
        "peer": 86
      },
      "student_teacher_ratio": {
        "state": 5,
        "district": 6,
        "peer": 1
      },
      "counselor_student_ratio": {
        "state": null,
        "district": null,
        "peer": null
      },
      "per_pupil_total": {
        "state": 91,
        "district": 94,
        "peer": 61
      },
      "chronic_absenteeism_pct": {
        "state": 90,
        "district": 94,
        "peer": 86
      },
      "discipline_rate": {
        "state": null,
        "district": null,
        "peer": null
      }
    },
    "performance_flag": null,
    "regression_predicted": null,
    "regression_residual": null,
    "regression_zscore": null,
    "regression_group": null,
    "regression_r_squared": null,
    "flags": {
      "chronic_absenteeism": {
        "color": "green",
        "raw_value": 0.077
      },
      "counselor_ratio": {
        "color": null,
        "flag_absent_reason": "data_not_available"
      },
      "discipline_disparity": {
        "color": null,
        "flag_absent_reason": "data_not_available"
      },
      "no_counselor": {
        "color": "red",
        "raw_value": 0.0,
        "threshold_source": "CRDC staffing data reports 0.0 counselor FTE for this school.",
        "what_it_means": "This school reports zero counselor staff. Students at this school do not have access to a dedicated school counselor for academic, social-emotional, or college/career guidance.",
        "what_it_might_not_mean": "Some schools share counselors with other buildings or contract counseling services that may not appear in staffing reports. The school may also use other support models (social workers, community partnerships) not captured in this data.",
        "parent_question": "How does the school provide counseling and social-emotional support to students without a dedicated counselor on staff?"
      }
    },
    "performance_flag_absent_reason": "grade_span_not_tested"
  },
  "district_context": {
    "status": "enriched",
    "prompt_version": "v1",
    "validation_prompt_version": "v1",
    "generated_at": "2026-02-23T04:54:47.472597+00:00",
    "model": "claude-haiku-4-5-20251001",
    "cost": {
      "enrichment_input_tokens": 22581,
      "enrichment_output_tokens": 1599,
      "validation_input_tokens": 12865,
      "validation_output_tokens": 1238,
      "web_search_requests": 3,
      "total_input_tokens": 35446,
      "total_output_tokens": 2837,
      "actual_model": "claude-haiku-4-5-20251001"
    },
    "findings": [
      {
        "category": "leadership",
        "subcategory": null,
        "summary": "Superintendent Dr. Shaun Carey suddenly resigned from his position after five years of service on January 12, 2026. No explanation was given for his departure. Interim Superintendent Jill Burnes, previously the deputy superintendent, has assumed the role while the district searches for a permanent replacement.",
        "source_url": "https://www.courierherald.com/news/esd-superintendent-dr-carey-suddenly-resigns/",
        "source_name": "Courier-Herald",
        "source_content_summary": "Announces Carey's sudden resignation, the brief board meeting to accept it, board president's statement thanking Carey for his service, and Carey's own statement about his tenure. Also mentions the district's plan to announce a search process.",
        "date": "2026-01-13",
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Enumclaw School District correctly identified. Courier-Herald is credible source. Facts verified: Carey resigned Jan. 12, 2026 after five years; Jill Burnes is interim superintendent. Claim fully supported by sources."
      },
      {
        "category": "community_investment",
        "subcategory": null,
        "summary": "The Enumclaw School District is partnering with developer Oakpointe to fund a new school in the Ten Trails development in Black Diamond. The district will sell 40 acres of land for $40 million and Oakpointe is loaning $25 million to be repaid through mitigation fees, plus an additional $3 million gift for sports field development.",
        "source_url": "https://www.courierherald.com/2026/02/05/esd-updates-board-on-superintendent-search-new-school-design/",
        "source_name": "Courier-Herald",
        "source_content_summary": "Updates on the superintendent search and new school design in the Ten Trails development. Details the funding arrangement with Oakpointe, architectural contracts, design advisory committee meetings, and hiring plans for a planning principal.",
        "date": "2026-02-05",
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Enumclaw School District correctly identified. Courier-Herald is credible source. District-level scope: major land sale and development partnership. Summary aligns with source content about funding arrangement with Oakpointe."
      },
      {
        "category": "leadership",
        "subcategory": null,
        "summary": "Superintendent Shaun Carey was elected president of the Washington Association of School Administrators (WASA) in July 2025, while serving as superintendent of Enumclaw School District. He has since resigned from his superintendent position in January 2026.",
        "source_url": "https://www.courierherald.com/news/esds-superintendent-communications-director-begin-year-as-association-presidents/",
        "source_name": "Courier-Herald",
        "source_content_summary": "Announces Carey's election as WASA president and notes his tenure as Enumclaw superintendent characterized by commitment to educational equity. Also mentions district communications director Jessica McCartney became president of the Washington School Public Relations Association.",
        "date": "2025-07-16",
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Enumclaw School District superintendent correctly identified. Credible source (WASA official announcement). Carey was elected WASA President-Elect for 2024-25 and assumed presidency in July 2025, consistent with claim. District-level leadership information."
      },
      {
        "category": "other",
        "subcategory": "regulatory_complaint",
        "summary": "The Washington State Public Disclosure Commission received an allegation against Enumclaw School District Officials for violations of RCW 42.17A.555 regarding misuse of public facilities by promoting and supporting a levy election through Facebook, the district website, and videos.",
        "source_url": "https://www.pdc.wa.gov/rules-enforcement/enforcement/enforcement-cases/103325",
        "source_name": "Washington State Public Disclosure Commission",
        "source_content_summary": "PDC enforcement case page documenting an allegation that Enumclaw School District officials misused public facilities to promote a levy up for election in 2022.",
        "date": null,
        "confidence": "high",
        "sensitivity": "normal",
        "validated": true,
        "validation_notes": "Enumclaw School District correctly identified. Washington State Public Disclosure Commission is official government source and highly credible. District-level regulatory matter. Source is verifiable official enforcement case record."
      }
    ],
    "validation_summary": {
      "findings_submitted": 6,
      "findings_confirmed": 4,
      "findings_rejected": 2,
      "findings_downgraded": 0,
      "wrong_school_detected": 0
    },
    "error": null,
    "district_name": "Enumclaw School District"
  },
  "layer3_narrative": {
    "text": "In an undated report, the Washington State Public Disclosure Commission received an allegation that district officials violated RCW 42.17A.555 by using public facilities \u2014 including a Facebook presence, the district website, and videos \u2014 to promote and support a levy election. The cited records do not reflect a resolution of this matter. [Sources: https://www.pdc.wa.gov/rules-enforcement/enforcement/enforcement-cases/103325]",
    "model": "claude-sonnet-4-6",
    "source_findings_count": 4,
    "stage0_dropped_count": 0,
    "stage1_included_count": 1,
    "stage1_excluded_count": 3,
    "status": "ok",
    "error": null,
    "generated_at": "2026-05-02T01:40:37.772761+00:00",
    "prompt_version": "layer3_v3"
  }
}
```
