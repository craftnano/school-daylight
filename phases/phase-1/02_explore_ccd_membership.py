"""
02_explore_ccd_membership.py — Read CCD Membership and extract WA enrollment data.

The CCD membership file is 2.3 GB in long format (one row per school/grade/race/sex).
We stream it in chunks, filter to WA, and aggregate to one row per school with:
  - Total enrollment (Education Unit Total)
  - Enrollment by race/ethnicity (summing male + female for each race)
  - Enrollment by grade
  - Enrollment by sex

NOTE: CCD Membership does NOT contain FRL data. FRL comes from OSPI enrollment.

Input:  WA-raw/federal/ccd_sch_052_2425_l_1a_073025.csv (extracted from ZIP)
Output: data/ccd_wa_membership.csv (one row per school)
Logs:   logs/02_explore_ccd_membership_YYYY-MM-DD.log
"""

import os
import sys
import csv
import logging
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
log_dir = config.LOGS_DIR
os.makedirs(log_dir, exist_ok=True)

log_filename = f"02_explore_ccd_membership_{datetime.now().strftime('%Y-%m-%d')}.log"
log_path = os.path.join(log_dir, log_filename)

logger = logging.getLogger("ccd_membership")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
logger.addHandler(file_handler)


# The CCD uses these race/ethnicity category names
RACE_CATEGORIES = [
    "American Indian or Alaska Native",
    "Asian",
    "Black or African American",
    "Hispanic/Latino",
    "Native Hawaiian or Other Pacific Islander",
    "Two or more races",
    "White",
    "Not Specified",
]

# Short names for output columns
RACE_SHORT = {
    "American Indian or Alaska Native": "american_indian",
    "Asian": "asian",
    "Black or African American": "black",
    "Hispanic/Latino": "hispanic",
    "Native Hawaiian or Other Pacific Islander": "pacific_islander",
    "Two or more races": "two_or_more",
    "White": "white",
    "Not Specified": "not_specified",
}


def read_wa_membership():
    """Stream the 2.3 GB membership CSV and extract WA school data."""

    csv_path = os.path.join(
        config.RAW_DIR, "federal", "ccd_sch_052_2425_l_1a_073025.csv"
    )

    if not os.path.exists(csv_path):
        logger.error(
            f"CCD membership CSV not found at {csv_path}. "
            "Extract it from the ZIP first: "
            "unzip WA-raw/federal/ccd_sch_052_2425_l_1a_073025.zip -d WA-raw/federal/"
        )
        sys.exit(1)

    logger.info(f"Reading CCD membership from {csv_path}")
    logger.info("This file is 2.3 GB — streaming and filtering to WA only...")

    # We'll collect per-school data in dictionaries keyed by NCESSCH
    # Total enrollment from "Education Unit Total" rows
    school_totals = {}
    # Race/ethnicity enrollment (sum male+female) from "Derived - Subtotal by Race..."
    school_race = defaultdict(lambda: defaultdict(int))
    # Grade enrollment from "Subtotal 4 - By Grade"
    school_grade = defaultdict(lambda: defaultdict(int))
    # Sex enrollment (sum across races) — we'll derive from race subtotals
    school_sex = defaultdict(lambda: defaultdict(int))
    # School names for output
    school_names = {}

    # DMS_FLAG tracking for suppression audit
    dms_counts = defaultdict(int)
    wa_rows = 0
    total_rows = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            if total_rows % 5_000_000 == 0:
                logger.info(f"  ...processed {total_rows:,} rows so far")

            if row["ST"] != "WA":
                continue

            wa_rows += 1
            ncessch = row["NCESSCH"]
            ti = row["TOTAL_INDICATOR"]
            count_str = row["STUDENT_COUNT"]
            dms = row["DMS_FLAG"]
            dms_counts[dms] += 1

            # Store school name
            if ncessch not in school_names:
                school_names[ncessch] = row["SCH_NAME"]

            # Parse count — some may be blank or missing
            try:
                count = int(count_str)
            except (ValueError, TypeError):
                count = None

            # Education Unit Total → total enrollment
            if ti == "Education Unit Total" and count is not None:
                school_totals[ncessch] = count

            # Race/ethnicity subtotals (summing male+female gives race total)
            elif "Subtotal by Race/Ethnicity" in ti and count is not None:
                race = row["RACE_ETHNICITY"]
                sex = row["SEX"]
                if race in RACE_SHORT:
                    school_race[ncessch][RACE_SHORT[race]] += count
                if sex in ("Male", "Female"):
                    school_sex[ncessch][sex.lower()] += count

            # Grade-level subtotals
            elif ti == "Subtotal 4 - By Grade" and count is not None:
                grade = row["GRADE"]
                if grade not in ("Not Specified", "No Category Codes"):
                    school_grade[ncessch][grade] += count

    logger.info(f"Total rows in file: {total_rows:,}")
    logger.info(f"WA rows: {wa_rows:,}")
    logger.info(f"Unique WA schools with enrollment total: {len(school_totals):,}")
    logger.info(f"Unique WA schools with race data: {len(school_race):,}")

    return school_totals, school_race, school_grade, school_sex, school_names, dms_counts


def analyze_results(school_totals, school_race, school_grade, school_sex, school_names, dms_counts):
    """Log summary statistics about WA enrollment data."""

    # DMS_FLAG distribution (suppression audit)
    logger.info("--- DMS_FLAG Distribution (WA only) ---")
    for flag, count in sorted(dms_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {count:>8,}  {flag}")

    not_reported = dms_counts.get("Not reported", 0)
    if not_reported > 0:
        logger.info(
            f"  Note: {not_reported:,} WA rows have DMS_FLAG='Not reported'. "
            "These are schools that did not report enrollment for that "
            "grade/race/sex combination. The STUDENT_COUNT may be blank or 0."
        )

    # Enrollment range
    if school_totals:
        enrollments = sorted(school_totals.values())
        logger.info("--- Enrollment Distribution ---")
        logger.info(f"  Min: {enrollments[0]}")
        logger.info(f"  Max: {enrollments[-1]:,}")
        logger.info(f"  Median: {enrollments[len(enrollments)//2]:,}")

        # Count schools with zero enrollment (may be closed or reporting issue)
        zero_enrollment = sum(1 for e in enrollments if e == 0)
        logger.info(f"  Schools with 0 enrollment: {zero_enrollment}")

    # Fairhaven check
    fairhaven_id = "530042000104"
    logger.info("--- Fairhaven Middle School Enrollment (CCD 2024-25) ---")
    if fairhaven_id in school_totals:
        logger.info(f"  Total enrollment: {school_totals[fairhaven_id]}")
        if fairhaven_id in school_race:
            logger.info("  By race/ethnicity:")
            for race, count in sorted(school_race[fairhaven_id].items()):
                logger.info(f"    {race:25s}: {count}")
        if fairhaven_id in school_grade:
            logger.info("  By grade:")
            for grade, count in sorted(school_grade[fairhaven_id].items()):
                logger.info(f"    {grade:15s}: {count}")
        if fairhaven_id in school_sex:
            logger.info("  By sex:")
            for sex, count in sorted(school_sex[fairhaven_id].items()):
                logger.info(f"    {sex:15s}: {count}")
    else:
        logger.error(
            "Fairhaven Middle School (530042000104) NOT FOUND in CCD membership. "
            "This is unexpected. Check that NCESSCH filtering is correct."
        )


def save_aggregated(school_totals, school_race, school_grade, school_sex, school_names):
    """Save one-row-per-school aggregated enrollment to CSV."""

    output_path = os.path.join(config.DATA_DIR, "ccd_wa_membership.csv")

    # Build output rows
    fieldnames = [
        "ncessch", "school_name", "total_enrollment",
        "american_indian", "asian", "black", "hispanic",
        "pacific_islander", "two_or_more", "white", "not_specified",
        "male", "female",
    ]

    rows = []
    for ncessch in sorted(school_totals.keys()):
        row = {
            "ncessch": ncessch,
            "school_name": school_names.get(ncessch, ""),
            "total_enrollment": school_totals[ncessch],
        }
        # Race data
        race_data = school_race.get(ncessch, {})
        for race_key in RACE_SHORT.values():
            row[race_key] = race_data.get(race_key, "")

        # Sex data
        sex_data = school_sex.get(ncessch, {})
        row["male"] = sex_data.get("male", "")
        row["female"] = sex_data.get("female", "")

        rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Saved {len(rows):,} schools to {output_path}")


def main():
    logger.info("=" * 70)
    logger.info("CCD SCHOOL MEMBERSHIP EXPLORATION")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    school_totals, school_race, school_grade, school_sex, school_names, dms_counts = (
        read_wa_membership()
    )
    analyze_results(
        school_totals, school_race, school_grade, school_sex, school_names, dms_counts
    )
    save_aggregated(school_totals, school_race, school_grade, school_sex, school_names)

    logger.info("=" * 70)
    logger.info("CCD Membership exploration complete.")
    logger.info(f"Log saved to {log_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
