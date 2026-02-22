"""
04_load_ospi_academics.py — Add assessment proficiency, growth, and attendance data.

PURPOSE: Add ELA/Math/Science proficiency rates from Assessment, student growth
         percentiles from Growth (2024-25 primary, 2023-24 fallback), and
         regular attendance / 9th grade on track / dual credit from SQSS.
INPUTS: WA-raw/ospi/Report_Card_Assessment_Data_2023-24.csv,
        WA-raw/ospi/Report_Card_Growth_for_2024-25.csv,
        WA-raw/ospi/Report_Card_Growth_for_2023-24.csv,
        WA-raw/ospi/Report_Card_SQSS_for_2024-25.csv,
        data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with academics section
JOIN KEYS: DistrictCode + SchoolCode → crosswalk
SUPPRESSION HANDLING: N<10 → null + suppressed. "*" → null + masked.
                      DATReason='NULL' is NOT suppression — data is valid.
                      "No Students" → null + no_students.
RECEIPT: phases/phase-2/receipt.md — academics section
FAILURE MODES: Growth uses "AllStudents" (no space), SQSS uses "All Students" (with space).
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, build_ospi_lookup,
    parse_ospi_value, parse_percentage, safe_int, safe_float,
    FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_assessment(schools, lookup, logger):
    """Load OSPI Assessment proficiency rates (ELA, Math, Science)."""

    source_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_Assessment_Data_2023-24.csv"
    )

    if not os.path.exists(source_path):
        logger.error(f"OSPI assessment file not found at {source_path}.")
        return 0

    matched = 0

    # Map OSPI TestSubject names to our schema field names
    subject_map = {
        "ELA": "ela",
        "Math": "math",
        "Science": "science",
    }

    # SOURCE: WA-raw/ospi/Report_Card_Assessment_Data_2023-24.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # RULE: Filter to school-level, all students, all grades
            org_level = (row.get("OrganizationLevel") or "").strip()
            group_type = (row.get("StudentGroupType") or "").strip()
            grade_level = (row.get("GradeLevel") or "").strip()

            if org_level != "School" or group_type != "All" or grade_level != "All Grades":
                continue

            district_code = (row.get("DistrictCode") or "").strip()
            school_code = (row.get("SchoolCode") or "").strip()
            ncessch = lookup.get((district_code, school_code))

            if ncessch is None:
                continue

            test_subject = (row.get("TestSubject") or "").strip()
            schema_subject = subject_map.get(test_subject)
            if schema_subject is None:
                continue

            # Initialize academics.assessment if not yet present
            if "academics" not in schools[ncessch]:
                schools[ncessch]["academics"] = {}
            if "assessment" not in schools[ncessch]["academics"]:
                schools[ncessch]["academics"]["assessment"] = {"year": "2023-24"}

            assessment = schools[ncessch]["academics"]["assessment"]

            # LINEAGE: "Percent Consistent Grade Level Knowledge And Above" → proficiency_pct
            dat = row.get("DAT", "")
            proficiency_raw = row.get("Percent Consistent Grade Level Knowledge And Above", "")
            prof_val, prof_flag = parse_ospi_value(proficiency_raw, dat)

            if prof_val is not None:
                # RULE: Convert percentage string to 0.0-1.0 decimal
                assessment[f"{schema_subject}_proficiency_pct"] = parse_percentage(proficiency_raw)
            elif prof_flag:
                assessment[f"{schema_subject}_proficiency_pct"] = None

            # Also capture student count
            students_raw = row.get("Count of Students Expected to Test", "")
            students_val, _ = parse_ospi_value(students_raw)
            if students_val is not None:
                assessment[f"{schema_subject}_students_tested"] = safe_int(students_val)

            matched += 1

    logger.info(f"Assessment: {matched} subject-school rows loaded.")
    return matched


def load_growth(schools, lookup, logger):
    """Load OSPI Growth SGP data (2024-25 primary, 2023-24 fallback).

    RULE (clarification #2): Fall back to 2023-24 ONLY when the school
    has zero rows in the 2024-25 file. If the school is present in
    2024-25 but suppressed, keep the suppressed null — do NOT fall back.
    """

    primary_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_Growth_for_2024-25.csv"
    )
    fallback_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_Growth_for_2023-24.csv"
    )

    # Subject names differ between Growth and Assessment files
    subject_map = {
        "English Language Arts": "ela",
        "Math": "math",
    }

    def read_growth_file(filepath, year_label):
        """Read a growth file and return {ncessch: {subject: row_data}}."""
        data = {}
        if not os.path.exists(filepath):
            logger.warning(f"Growth file not found: {filepath}")
            return data

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # RULE: Growth uses "AllStudents" (no space), not "All Students"
                org_level = (row.get("OrganizationLevel") or "").strip()
                group_type = (row.get("StudentGroupType") or "").strip()
                grade_level = (row.get("GradeLevel") or "").strip()

                if org_level != "School" or group_type != "AllStudents" or grade_level != "All Grades":
                    continue

                district_code = (row.get("DistrictCode") or "").strip()
                school_code = (row.get("SchoolCode") or "").strip()
                ncessch = lookup.get((district_code, school_code))
                if ncessch is None:
                    continue

                subject = (row.get("Subject") or "").strip()
                schema_subject = subject_map.get(subject)
                if schema_subject is None:
                    continue

                if ncessch not in data:
                    data[ncessch] = {}
                data[ncessch][schema_subject] = row

        return data

    # Read both years
    primary_data = read_growth_file(primary_path, "2024-25")
    fallback_data = read_growth_file(fallback_path, "2023-24")

    # Track which schools are present in primary (even if suppressed)
    schools_in_primary = set(primary_data.keys())

    matched = 0
    fell_back = 0

    for ncessch in schools:
        # Determine which year's data to use
        if ncessch in primary_data:
            growth_rows = primary_data[ncessch]
            year_used = "2024-25"
        elif ncessch in fallback_data:
            # RULE: Only fall back when school has zero rows in primary
            growth_rows = fallback_data[ncessch]
            year_used = "2023-24"
            fell_back += 1
        else:
            continue

        if "academics" not in schools[ncessch]:
            schools[ncessch]["academics"] = {}

        growth = {"year": year_used}

        for schema_subject in ["ela", "math"]:
            row = growth_rows.get(schema_subject)
            if row is None:
                continue

            # RULE: DATReason='NULL' means data is valid, not suppressed
            dat_reason = (row.get("DATReason") or "").strip()
            is_suppressed = dat_reason and dat_reason != "NULL" and (
                "N<10" in dat_reason or "Cross" in dat_reason
            )

            if is_suppressed:
                growth[f"{schema_subject}_median_sgp"] = None
            else:
                # LINEAGE: MedianSGP → academics.growth.{subject}_median_sgp
                median_sgp = safe_float(row.get("MedianSGP"))
                growth[f"{schema_subject}_median_sgp"] = median_sgp

                # Growth counts — these columns are named "Percent" but are actually counts
                # RULE: NumberLowGrowth etc. are integer counts
                growth[f"{schema_subject}_low_growth_count"] = safe_int(row.get("NumberLowGrowth"))
                growth[f"{schema_subject}_typical_growth_count"] = safe_int(row.get("NumberTypicalGrowth"))
                growth[f"{schema_subject}_high_growth_count"] = safe_int(row.get("NumberHighGrowth"))

        schools[ncessch]["academics"]["growth"] = growth
        matched += 1

    logger.info(
        f"Growth: {matched} schools loaded. "
        f"{len(schools_in_primary)} found in 2024-25 primary. "
        f"{fell_back} fell back to 2023-24."
    )
    return matched


def load_sqss(schools, lookup, logger):
    """Load OSPI SQSS data: attendance, 9th grade on track, dual credit."""

    source_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_SQSS_for_2024-25.csv"
    )

    if not os.path.exists(source_path):
        logger.error(f"OSPI SQSS file not found at {source_path}.")
        return 0

    attendance_matched = 0
    ninth_grade_matched = 0
    dual_credit_matched = 0

    # SOURCE: WA-raw/ospi/Report_Card_SQSS_for_2024-25.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # RULE: SQSS uses "All Students" (with space), not "AllStudents"
            org_level = (row.get("OrganizationLevel") or "").strip()
            group_type = (row.get("StudentGroupType") or "").strip()
            grade_level = (row.get("GradeLevel") or "").strip()

            if org_level != "School" or group_type != "All Students" or grade_level != "All Grades":
                continue

            district_code = (row.get("DistrictCode") or "").strip()
            school_code = (row.get("SchoolCode") or "").strip()
            ncessch = lookup.get((district_code, school_code))
            if ncessch is None:
                continue

            measure = (row.get("Measure") or "").strip()
            dat_reason = row.get("DAT_Reason", "")

            if "academics" not in schools[ncessch]:
                schools[ncessch]["academics"] = {}

            if measure == "Regular Attendance":
                # LINEAGE: SQSS Percent → academics.attendance.regular_attendance_pct
                pct_val, pct_flag = parse_ospi_value(row.get("Percent"), dat_reason)
                num_val, _ = parse_ospi_value(row.get("Numerator"), dat_reason)
                den_val, _ = parse_ospi_value(row.get("Denominator"), dat_reason)

                attendance = {"year": "2024-25"}
                if pct_val is not None:
                    attendance["regular_attendance_pct"] = safe_float(pct_val)
                    attendance["numerator"] = safe_int(num_val)
                    attendance["denominator"] = safe_int(den_val)
                elif pct_flag:
                    attendance["regular_attendance_pct"] = None
                    attendance["suppressed"] = True

                schools[ncessch]["academics"]["attendance"] = attendance
                attendance_matched += 1

            elif measure == "Ninth Grade on Track":
                pct_val, pct_flag = parse_ospi_value(row.get("Percent"), dat_reason)
                ninth = {"year": "2024-25"}
                if pct_val is not None:
                    ninth["pct"] = safe_float(pct_val)
                    ninth["numerator"] = safe_int(parse_ospi_value(row.get("Numerator"), dat_reason)[0])
                    ninth["denominator"] = safe_int(parse_ospi_value(row.get("Denominator"), dat_reason)[0])
                elif pct_flag:
                    if pct_flag.get("no_students"):
                        ninth["no_students"] = True
                    else:
                        ninth["pct"] = None
                        ninth["suppressed"] = True

                schools[ncessch]["academics"]["ninth_grade_on_track"] = ninth
                ninth_grade_matched += 1

            elif measure == "Dual Credit":
                pct_val, pct_flag = parse_ospi_value(row.get("Percent"), dat_reason)
                dual = {"year": "2024-25"}
                if pct_val is not None:
                    dual["pct"] = safe_float(pct_val)
                    dual["numerator"] = safe_int(parse_ospi_value(row.get("Numerator"), dat_reason)[0])
                    dual["denominator"] = safe_int(parse_ospi_value(row.get("Denominator"), dat_reason)[0])
                elif pct_flag:
                    if pct_flag.get("no_students"):
                        dual["no_students"] = True
                    else:
                        dual["pct"] = None
                        dual["suppressed"] = True

                schools[ncessch]["academics"]["dual_credit"] = dual
                dual_credit_matched += 1

    logger.info(
        f"SQSS: {attendance_matched} schools with attendance, "
        f"{ninth_grade_matched} with 9th grade on track, "
        f"{dual_credit_matched} with dual credit."
    )
    return attendance_matched


def main():
    logger = setup_logging("04_load_ospi_academics")
    logger.info("Step 04: Loading OSPI academics (assessment, growth, attendance).")

    schools = load_schools()
    lookup = build_ospi_lookup(schools)

    load_assessment(schools, lookup, logger)
    load_growth(schools, lookup, logger)
    load_sqss(schools, lookup, logger)

    save_schools(schools)

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools and "academics" in schools[FAIRHAVEN_NCESSCH]:
        acad = schools[FAIRHAVEN_NCESSCH]["academics"]
        assess = acad.get("assessment", {})
        growth = acad.get("growth", {})
        attend = acad.get("attendance", {})
        logger.info(
            f"Fairhaven academics: "
            f"ELA proficiency={assess.get('ela_proficiency_pct')}, "
            f"Math proficiency={assess.get('math_proficiency_pct')}, "
            f"Science proficiency={assess.get('science_proficiency_pct')}, "
            f"Growth year={growth.get('year')}, "
            f"ELA SGP={growth.get('ela_median_sgp')}, "
            f"Math SGP={growth.get('math_median_sgp')}, "
            f"Attendance={attend.get('regular_attendance_pct')}."
        )
    else:
        logger.warning("Fairhaven academics not found. Check crosswalk join.")

    logger.info("Step 04 complete.")


if __name__ == "__main__":
    main()
