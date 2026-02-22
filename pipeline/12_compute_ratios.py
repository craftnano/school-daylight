"""
12_compute_ratios.py — Compute all derived ratios from base data fields.

PURPOSE: Calculate student-teacher ratio, counselor-student ratio, chronic
         absenteeism rate, proficiency composite, and discipline disparity
         ratios. These are the building blocks for flags and percentiles.
INPUTS:  data/schools_pipeline.json
OUTPUTS: Adds derived.* fields to each school document.

DISCIPLINE DISPARITY: For each racial group, compute
  (suspension rate for that group) / (suspension rate for white students).
  Only compute when both groups have 10+ students enrolled (CRDC data).
  Suspension = ISS + OSS_single + OSS_multiple (non-IDEA).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    FAIRHAVEN_NCESSCH
)


def sum_race_from_crdc_obj(obj, race):
    """Sum male + female counts for a race from a crdc_race_object dict.

    The crdc_race_object stores values like {"hispanic_male": 5, "hispanic_female": 3}.
    This function returns the total for a given race (e.g., "hispanic" → 8).
    Returns 0 if neither key is present (not None — 0 is a valid count).
    """
    if obj is None:
        return 0
    male = obj.get(f"{race}_male", 0) or 0
    female = obj.get(f"{race}_female", 0) or 0
    return male + female


def compute_disparity(doc, logger):
    """Compute discipline disparity ratios for one school.

    Returns a dict with per-race ratios, max ratio, and max race.
    Returns None if we can't compute (no CRDC, no white baseline, etc.).
    """
    crdc = doc.get("discipline", {}).get("crdc", {})
    crdc_by_race = doc.get("enrollment", {}).get("crdc_by_race", {})

    if not crdc or not crdc_by_race:
        return None

    # Get the three non-IDEA suspension types
    iss = crdc.get("iss")
    oss_single = crdc.get("oss_single")
    oss_multiple = crdc.get("oss_multiple")

    # Need at least one suspension data source
    if iss is None and oss_single is None and oss_multiple is None:
        return None

    # Compute suspension count per race by summing ISS + OSS_single + OSS_multiple
    races = ["hispanic", "american_indian", "asian", "pacific_islander",
             "black", "white", "two_or_more"]

    suspension_counts = {}
    for race in races:
        count = 0
        count += sum_race_from_crdc_obj(iss, race)
        count += sum_race_from_crdc_obj(oss_single, race)
        count += sum_race_from_crdc_obj(oss_multiple, race)
        suspension_counts[race] = count

    # Compute suspension rates (suspensions / enrolled students for that race)
    suspension_rates = {}
    for race in races:
        enrolled = crdc_by_race.get(race, 0)
        if enrolled >= 10:
            suspension_rates[race] = suspension_counts[race] / enrolled
        # If enrolled < 10, don't compute — single incidents create misleading ratios

    # Need a white baseline to compute ratios
    white_rate = suspension_rates.get("white")
    if white_rate is None:
        # White enrollment < 10 or no white students
        return {"no_white_baseline": True}

    if white_rate == 0:
        # Can't divide by zero — white students have zero suspensions
        # Still useful to note which races have suspensions when white doesn't
        return {"no_white_baseline": True, "white_rate_zero": True}

    # Compute disparity ratios: rate_for_race / rate_for_white
    ratios = {}
    for race in races:
        if race == "white":
            continue
        if race in suspension_rates:
            if suspension_rates[race] == 0:
                ratios[race] = 0.0
            else:
                ratios[race] = round(suspension_rates[race] / white_rate, 2)

    if not ratios:
        return None

    # Find the maximum disparity
    max_race = max(ratios, key=ratios.get)
    max_ratio = ratios[max_race]

    return {
        "ratios": ratios,
        "max_ratio": max_ratio,
        "max_race": max_race,
    }


def main():
    logger = setup_logging("12_compute_ratios")
    logger.info("Computing derived ratios for all schools.")

    schools = load_schools()
    logger.info(f"Loaded {len(schools)} schools.")

    # Counters for summary logging
    st_count = 0        # schools with student-teacher ratio
    counselor_count = 0  # schools with counselor ratio
    no_counselor_count = 0
    absent_count = 0    # schools with chronic absenteeism
    composite_count = 0 # schools with proficiency composite
    disparity_count = 0 # schools with discipline disparity
    no_baseline_count = 0

    for ncessch, doc in schools.items():
        if "derived" not in doc:
            doc["derived"] = {}

        derived = doc["derived"]

        # --- Student-teacher ratio ---
        enrollment_total = doc.get("enrollment", {}).get("total")
        teacher_fte = doc.get("staffing", {}).get("teacher_fte_total")

        if enrollment_total and teacher_fte and teacher_fte > 0:
            derived["student_teacher_ratio"] = round(enrollment_total / teacher_fte, 1)
            st_count += 1
        else:
            derived["student_teacher_ratio"] = None

        # --- Counselor-student ratio ---
        counselor_fte = doc.get("staffing", {}).get("counselor_fte")

        if counselor_fte is not None and counselor_fte > 0 and enrollment_total:
            derived["counselor_student_ratio"] = round(enrollment_total / counselor_fte, 1)
            derived["no_counselor"] = False
            counselor_count += 1
        elif counselor_fte is not None and counselor_fte == 0:
            # Explicitly zero counselors — flag this
            derived["counselor_student_ratio"] = None
            derived["no_counselor"] = True
            no_counselor_count += 1
        else:
            derived["counselor_student_ratio"] = None
            derived["no_counselor"] = None

        # --- Chronic absenteeism (inverse of regular attendance) ---
        attendance = doc.get("academics", {}).get("attendance", {}).get("regular_attendance_pct")

        if attendance is not None:
            derived["chronic_absenteeism_pct"] = round(1.0 - attendance, 4)
            absent_count += 1
        else:
            derived["chronic_absenteeism_pct"] = None

        # --- Proficiency composite (average of ELA + Math) ---
        assessment = doc.get("academics", {}).get("assessment", {})
        ela = assessment.get("ela_proficiency_pct")
        math = assessment.get("math_proficiency_pct")

        if ela is not None and math is not None:
            derived["proficiency_composite"] = round((ela + math) / 2, 4)
            composite_count += 1
        else:
            derived["proficiency_composite"] = None

        # --- Discipline disparity ---
        result = compute_disparity(doc, logger)
        if result is None:
            derived["discipline_disparity"] = None
            derived["discipline_disparity_max"] = None
            derived["discipline_disparity_max_race"] = None
        elif result.get("no_white_baseline"):
            derived["discipline_disparity"] = None
            derived["discipline_disparity_max"] = None
            derived["discipline_disparity_max_race"] = None
            derived["discipline_disparity_no_white_baseline"] = True
            no_baseline_count += 1
        else:
            derived["discipline_disparity"] = result["ratios"]
            derived["discipline_disparity_max"] = result["max_ratio"]
            derived["discipline_disparity_max_race"] = result["max_race"]
            disparity_count += 1

    logger.info(f"Student-teacher ratio computed for {st_count} schools.")
    logger.info(f"Counselor-student ratio computed for {counselor_count} schools. "
                f"{no_counselor_count} schools have zero counselor FTE.")
    logger.info(f"Chronic absenteeism computed for {absent_count} schools.")
    logger.info(f"Proficiency composite computed for {composite_count} schools.")
    logger.info(f"Discipline disparity computed for {disparity_count} schools. "
                f"{no_baseline_count} have no white baseline.")

    # Fairhaven verification
    if FAIRHAVEN_NCESSCH in schools:
        fh = schools[FAIRHAVEN_NCESSCH]["derived"]
        logger.info(f"Fairhaven student-teacher ratio: {fh.get('student_teacher_ratio')}")
        logger.info(f"Fairhaven counselor-student ratio: {fh.get('counselor_student_ratio')}")
        logger.info(f"Fairhaven chronic absenteeism: {fh.get('chronic_absenteeism_pct')}")
        logger.info(f"Fairhaven proficiency composite: {fh.get('proficiency_composite')}")
        logger.info(f"Fairhaven disparity max: {fh.get('discipline_disparity_max')} "
                     f"(race: {fh.get('discipline_disparity_max_race')})")
        logger.info(f"Fairhaven disparity ratios: {fh.get('discipline_disparity')}")

    save_schools(schools)
    logger.info("Step 12 complete. All derived ratios computed.")


if __name__ == "__main__":
    main()
