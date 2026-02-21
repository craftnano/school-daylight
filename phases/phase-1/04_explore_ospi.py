"""
04_explore_ospi.py — Read all OSPI Report Card CSVs and document structure.

OSPI provides WA-specific data: enrollment (with FRL), assessment, discipline,
growth, SQSS (attendance/dual credit), and per-pupil expenditure.

OSPI uses SchoolCode and DistrictCode to identify schools. These map to
CCD's ST_SCHID field: WA-{DistrictCode}-{SchoolCode}.

KNOWN BUG: The discipline file has commas in numeric ID fields ("2,066" not "2066").
This script documents it. The cleaning rule will strip commas before joining.

Input:  WA-raw/ospi/*.csv
Output: Console + log with structure, suppression markers, Fairhaven values
Logs:   logs/04_explore_ospi_YYYY-MM-DD.log
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

log_filename = f"04_explore_ospi_{datetime.now().strftime('%Y-%m-%d')}.log"
log_path = os.path.join(log_dir, log_filename)

logger = logging.getLogger("ospi")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
logger.addHandler(file_handler)


# OSPI SchoolCode for Fairhaven Middle School
FAIRHAVEN_SCHOOL_CODE = "2066"
FAIRHAVEN_DISTRICT_CODE = "37501"

# Known suppression markers in OSPI data
OSPI_MARKERS = ["N<10", "*", "No Students", "NULL", "N/A", ""]


def clean_ospi_code(value):
    """Strip commas from OSPI ID fields. The discipline file has '2,066' not '2066'."""
    if value:
        return value.replace(",", "")
    return value


def explore_enrollment():
    """Read OSPI enrollment — source of FRL, demographic breakdowns."""

    path = os.path.join(config.RAW_DIR, "ospi", "Report_Card_Enrollment_2023-24_School_Year.csv")
    logger.info(f"\n{'='*60}")
    logger.info(f"OSPI ENROLLMENT (2023-24)")
    logger.info(f"File: {path}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"Total rows: {len(rows):,}")

    # Filter to school-level, All Grades
    school_all = [r for r in rows if r["OrganizationLevel"] == "School" and r["GradeLevel"] == "All Grades"]
    logger.info(f"School-level, All Grades rows: {len(school_all):,}")

    # Organization levels
    org_levels = defaultdict(int)
    for r in rows:
        org_levels[r["OrganizationLevel"]] += 1
    logger.info("Organization levels:")
    for level, count in sorted(org_levels.items()):
        logger.info(f"  {level}: {count:,}")

    # Grade levels
    grade_levels = defaultdict(int)
    for r in rows:
        grade_levels[r["GradeLevel"]] += 1
    logger.info(f"Unique grade levels: {len(grade_levels)}")

    # DAT (Data Adjustment Treatment) values
    dat_values = defaultdict(int)
    for r in school_all:
        dat = r.get("DAT", "").strip()
        if dat:
            dat_values[dat] += 1
    if dat_values:
        logger.info("DAT (Data Adjustment Treatment) values:")
        for dat, count in sorted(dat_values.items(), key=lambda x: -x[1]):
            logger.info(f"  {count:>5,}: {dat}")

    # Suppression scan: look for non-numeric values in count columns
    count_columns = [
        "All Students", "Female", "Gender X", "Male",
        "American Indian/Alaskan Native", "Asian", "Black/African American",
        "Hispanic/Latino of any race(s)", "Native Hawaiian/Other Pacific Islander",
        "Two or More Races", "White", "English Language Learners",
        "Low Income", "Non-Low Income", "Students with Disabilities",
        "Foster Care", "Homeless", "Migrant", "Section 504",
    ]

    suppression_counts = defaultdict(int)
    for r in school_all:
        for col in count_columns:
            val = r.get(col, "").strip()
            if val and not val.replace(",", "").lstrip("-").isdigit():
                suppression_counts[val] += 1

    logger.info("Suppression markers in count columns (school-level, All Grades):")
    for marker, count in sorted(suppression_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {count:>5,}: '{marker}'")

    # Find Fairhaven
    logger.info("--- Fairhaven Middle School ---")
    for r in school_all:
        if r["SchoolCode"] == FAIRHAVEN_SCHOOL_CODE and r["DistrictCode"] == FAIRHAVEN_DISTRICT_CODE:
            logger.info(f"  FOUND: {r['SchoolName']}, {r['DistrictName']}")
            logger.info(f"  SchoolCode={r['SchoolCode']}, DistrictCode={r['DistrictCode']}")
            logger.info(f"  All Students: {r['All Students']}")
            logger.info(f"  Female: {r['Female']}, Male: {r['Male']}, Gender X: {r['Gender X']}")
            logger.info(f"  Low Income (FRL): {r['Low Income']}")
            logger.info(f"  Non-Low Income: {r['Non-Low Income']}")
            logger.info(f"  English Language Learners: {r['English Language Learners']}")
            logger.info(f"  Students with Disabilities: {r['Students with Disabilities']}")
            logger.info(f"  Foster Care: {r['Foster Care']}")
            logger.info(f"  Homeless: {r['Homeless']}")
            logger.info(f"  Migrant: {r['Migrant']}")
            logger.info(f"  Section 504: {r['Section 504']}")
            logger.info(f"  Hispanic/Latino: {r['Hispanic/Latino of any race(s)']}")
            logger.info(f"  White: {r['White']}")
            logger.info(f"  Asian: {r['Asian']}")
            logger.info(f"  Two or More Races: {r['Two or More Races']}")
            logger.info(f"  Black/African American: {r['Black/African American']}")
            logger.info(f"  American Indian: {r['American Indian/Alaskan Native']}")
            logger.info(f"  Pacific Islander: {r['Native Hawaiian/Other Pacific Islander']}")
            break
    else:
        logger.error("  Fairhaven NOT FOUND in OSPI enrollment")

    return len(school_all)


def explore_discipline():
    """Read OSPI discipline — has the comma-in-IDs bug."""

    path = os.path.join(config.RAW_DIR, "ospi", "Report_Card_Discipline_for_2023-24.csv")
    logger.info(f"\n{'='*60}")
    logger.info(f"OSPI DISCIPLINE (2023-24)")
    logger.info(f"File: {path}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"Total rows: {len(rows):,}")

    # Check for comma-in-IDs bug
    sample_codes = set()
    has_commas = 0
    for r in rows[:1000]:
        sc = r.get("SchoolCode", "")
        dc = r.get("DistrictCode", "")
        if "," in sc or "," in dc:
            has_commas += 1
        sample_codes.add(sc)

    if has_commas > 0:
        logger.warning(
            f"  COMMA-IN-IDS BUG CONFIRMED: {has_commas} of first 1000 rows have commas in ID fields. "
            "SchoolCode shows '2,066' instead of '2066'. "
            "Cleaning rule: strip commas from DistrictCode and SchoolCode before joining."
        )
        logger.info(f"  Sample SchoolCode values: {list(sample_codes)[:10]}")

    # Filter to school-level, All Grades, All Students
    school_rows = [r for r in rows if r["OrganizationLevel"] == "School"]
    logger.info(f"School-level rows: {len(school_rows):,}")

    # Suppression markers in DisciplineDATNotes
    dat_notes = defaultdict(int)
    for r in school_rows:
        dat = r.get("DisciplineDATNotes", "").strip()
        if dat:
            dat_notes[dat] += 1
    logger.info("DisciplineDATNotes values (school-level):")
    for note, count in sorted(dat_notes.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  {count:>8,}: '{note}'")

    # Suppression in numeric columns
    numeric_cols = [
        "DisciplineRate", "DisciplineNumerator", "DisciplineDenominator",
        "Excluded1DayOrLess", "Excluded10DaysOrMore",
    ]
    for col in numeric_cols:
        markers = defaultdict(int)
        for r in school_rows:
            val = r.get(col, "").strip()
            if val and not val.replace(",", "").replace(".", "").replace("%", "").lstrip("-").isdigit():
                markers[val] += 1
        if markers:
            logger.info(f"  Non-numeric in {col}:")
            for m, c in sorted(markers.items(), key=lambda x: -x[1])[:5]:
                logger.info(f"    {c:>6,}: '{m}'")

    # Find Fairhaven (must clean commas first)
    logger.info("--- Fairhaven Middle School ---")
    for r in school_rows:
        sc = clean_ospi_code(r.get("SchoolCode", ""))
        dc = clean_ospi_code(r.get("DistrictCode", ""))
        if sc == FAIRHAVEN_SCHOOL_CODE and dc == FAIRHAVEN_DISTRICT_CODE:
            sg = r.get("Student Group", "")
            gl = r.get("GradeLevel", "")
            if sg == "All Students" and gl == "All Grades":
                logger.info(f"  FOUND: {r['SchoolName']} (All Students, All Grades)")
                logger.info(f"  DisciplineRate: {r['DisciplineRate']}")
                logger.info(f"  DisciplineNumerator: {r['DisciplineNumerator']}")
                logger.info(f"  DisciplineDenominator: {r['DisciplineDenominator']}")
                logger.info(f"  Excluded1DayOrLess: {r['Excluded1DayOrLess']}")
                logger.info(f"  Excluded10DaysOrMore: {r['Excluded10DaysOrMore']}")
                logger.info(f"  DisciplineDATNotes: {r['DisciplineDATNotes']}")
                break
    else:
        logger.error("  Fairhaven NOT FOUND in OSPI discipline (All Students, All Grades)")


def explore_assessment():
    """Read OSPI assessment — proficiency rates."""

    path = os.path.join(config.RAW_DIR, "ospi", "Report_Card_Assessment_Data_2023-24.csv")
    logger.info(f"\n{'='*60}")
    logger.info(f"OSPI ASSESSMENT (2023-24)")
    logger.info(f"File: {path}")

    # This file is 229 MB. Read and count rows, find Fairhaven, audit suppression.
    total = 0
    school_rows = 0
    dat_values = defaultdict(int)
    subjects = defaultdict(int)
    fairhaven_found = False

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            if r["OrganizationLevel"] == "School":
                school_rows += 1
                dat = r.get("DAT", "").strip()
                if dat:
                    dat_values[dat] += 1
                subjects[r.get("TestSubject", "")] += 1

                # Find Fairhaven
                sc = r.get("SchoolCode", "")
                dc = r.get("DistrictCode", "")
                sg = r.get("StudentGroupType", "")
                gl = r.get("GradeLevel", "")
                subj = r.get("TestSubject", "")
                if (sc == FAIRHAVEN_SCHOOL_CODE and dc == FAIRHAVEN_DISTRICT_CODE
                        and sg == "All" and gl == "All Grades"):
                    if not fairhaven_found:
                        logger.info("--- Fairhaven Middle School (All Students, All Grades) ---")
                        fairhaven_found = True
                    logger.info(
                        f"  {subj}: Proficiency={r.get('Percent Consistent Grade Level Knowledge And Above', 'N/A')}"
                        f"  Students={r.get('Count of Students Expected to Test', 'N/A')}"
                        f"  DAT={r.get('DAT', '')}"
                    )

    logger.info(f"Total rows: {total:,}")
    logger.info(f"School-level rows: {school_rows:,}")

    logger.info("DAT values (school-level):")
    for dat, count in sorted(dat_values.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  {count:>8,}: '{dat}'")

    logger.info("Subjects:")
    for subj, count in sorted(subjects.items(), key=lambda x: -x[1]):
        logger.info(f"  {count:>8,}: {subj}")

    if not fairhaven_found:
        logger.error("  Fairhaven NOT FOUND in assessment data")


def explore_growth():
    """Read OSPI growth — median SGP by subject."""

    for year_label, filename in [("2023-24", "Report_Card_Growth_for_2023-24.csv"),
                                  ("2024-25", "Report_Card_Growth_for_2024-25.csv")]:
        path = os.path.join(config.RAW_DIR, "ospi", filename)
        logger.info(f"\n{'='*60}")
        logger.info(f"OSPI GROWTH ({year_label})")
        logger.info(f"File: {path}")

        total = 0
        school_rows = 0
        dat_reasons = defaultdict(int)
        fairhaven_found = False

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                total += 1
                if r["OrganizationLevel"] == "School":
                    school_rows += 1
                    dat = r.get("DATReason", "").strip()
                    dat_reasons[dat] += 1

                    sc = r.get("SchoolCode", "")
                    dc = r.get("DistrictCode", "")
                    sg = r.get("StudentGroupType", "")
                    gl = r.get("GradeLevel", "")
                    if (sc == FAIRHAVEN_SCHOOL_CODE and dc == FAIRHAVEN_DISTRICT_CODE
                            and sg == "All" and gl == "All Grades"):
                        if not fairhaven_found:
                            logger.info(f"--- Fairhaven Middle School (All Students, All Grades) ---")
                            fairhaven_found = True
                        logger.info(
                            f"  {r.get('Subject', '')}: MedianSGP={r.get('MedianSGP', 'N/A')}"
                            f"  Students={r.get('StudentCount', 'N/A')}"
                            f"  Low={r.get('PercentLowGrowth', '')}"
                            f"  Typical={r.get('PercentTypicalGrowth', '')}"
                            f"  High={r.get('PercentHighGrowth', '')}"
                        )

        logger.info(f"Total rows: {total:,}")
        logger.info(f"School-level rows: {school_rows:,}")
        logger.info("DATReason values (school-level):")
        for dat, count in sorted(dat_reasons.items(), key=lambda x: -x[1])[:10]:
            display = dat if dat else "(empty)"
            logger.info(f"  {count:>8,}: '{display}'")

        if not fairhaven_found:
            logger.error(f"  Fairhaven NOT FOUND in growth data ({year_label})")


def explore_sqss():
    """Read OSPI SQSS — regular attendance, dual credit, 9th grade on track."""

    path = os.path.join(config.RAW_DIR, "ospi", "Report_Card_SQSS_for_2024-25.csv")
    logger.info(f"\n{'='*60}")
    logger.info(f"OSPI SQSS (2024-25)")
    logger.info(f"File: {path}")

    total = 0
    school_rows = 0
    measures = defaultdict(int)
    dat_reasons = defaultdict(int)
    labels = defaultdict(int)
    fairhaven_found = False

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            if r["OrganizationLevel"] == "School":
                school_rows += 1
                measure = r.get("Measure", "")
                measures[measure] += 1
                dat = r.get("DAT_Reason", "").strip()
                if dat:
                    dat_reasons[dat] += 1
                label = r.get("Label", "").strip()
                if label:
                    labels[label] += 1

                sc = r.get("SchoolCode", "")
                dc = r.get("DistrictCode", "")
                sg = r.get("StudentGroupType", "")
                gl = r.get("GradeLevel", "")
                if (sc == FAIRHAVEN_SCHOOL_CODE and dc == FAIRHAVEN_DISTRICT_CODE
                        and sg == "All" and gl == "All Grades"):
                    if not fairhaven_found:
                        logger.info(f"--- Fairhaven Middle School (All Students, All Grades) ---")
                        fairhaven_found = True
                    logger.info(
                        f"  Measure={measure}, Label={label}, "
                        f"Percent={r.get('Percent', '')}, "
                        f"Num={r.get('Numerator', '')}, Den={r.get('Denominator', '')}"
                    )

    logger.info(f"Total rows: {total:,}")
    logger.info(f"School-level rows: {school_rows:,}")

    logger.info("Measures:")
    for m, count in sorted(measures.items(), key=lambda x: -x[1]):
        logger.info(f"  {count:>8,}: {m}")

    logger.info("Labels (top 15):")
    for l, count in sorted(labels.items(), key=lambda x: -x[1])[:15]:
        logger.info(f"  {count:>8,}: {l}")

    logger.info("DAT_Reason values:")
    for dat, count in sorted(dat_reasons.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  {count:>8,}: '{dat}'")

    if not fairhaven_found:
        logger.error("  Fairhaven NOT FOUND in SQSS data")


def explore_ppe():
    """Read OSPI Per Pupil Expenditure data."""

    path = os.path.join(config.RAW_DIR, "ospi", "Per_Pupil_Expenditure_AllYears.csv")
    logger.info(f"\n{'='*60}")
    logger.info(f"OSPI PER PUPIL EXPENDITURE (Multi-Year)")
    logger.info(f"File: {path}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"Total rows: {len(rows):,}")

    # School years available
    years = defaultdict(int)
    for r in rows:
        years[r.get("School Year Code", "")] += 1
    logger.info("School years:")
    for y, count in sorted(years.items()):
        logger.info(f"  {y}: {count:,} rows")

    # Organization levels
    org_levels = defaultdict(int)
    for r in rows:
        org_levels[r.get("Organization Level", "")] += 1
    logger.info("Organization levels:")
    for level, count in sorted(org_levels.items()):
        logger.info(f"  {level}: {count:,}")

    # Find Fairhaven in most recent year
    logger.info("--- Fairhaven Middle School ---")
    for r in rows:
        sc = r.get("SchoolCode", "").strip()
        year = r.get("School Year Code", "")
        if sc == FAIRHAVEN_SCHOOL_CODE and "2023" in year:
            logger.info(f"  FOUND: {r.get('School Name', '')} ({year})")
            logger.info(f"  Enrollment: {r.get('Enrollment', '')}")
            logger.info(f"  Total PPE: {r.get('Total_PPE', '')}")
            logger.info(f"  Local PPE: {r.get('Local PPE', '')}")
            logger.info(f"  State PPE: {r.get('State PPE', '')}")
            logger.info(f"  Federal PPE: {r.get('Federal PPE', '')}")
            break
    else:
        logger.warning("  Fairhaven not found in PPE for 2023-24. Checking other years...")
        for r in rows:
            sc = r.get("SchoolCode", "").strip()
            if sc == FAIRHAVEN_SCHOOL_CODE:
                logger.info(f"  Found in year {r.get('School Year Code', '')}: {r.get('School Name', '')}")
                logger.info(f"  Total PPE: {r.get('Total_PPE', '')}")
                break


def explore_attendance_sqss_overlap():
    """Check if there's an Attendance file separate from SQSS."""

    logger.info(f"\n{'='*60}")
    logger.info("ATTENDANCE vs SQSS OVERLAP CHECK")

    # Check if a separate attendance CSV exists
    ospi_dir = os.path.join(config.RAW_DIR, "ospi")
    files = os.listdir(ospi_dir)
    attendance_files = [f for f in files if "attendance" in f.lower() and f.endswith(".csv")]

    if attendance_files:
        logger.info(f"Separate attendance files found: {attendance_files}")
        logger.info("Need to compare with SQSS Regular Attendance measure.")
    else:
        logger.info(
            "No separate attendance CSV found in WA-raw/ospi/. "
            "Regular attendance data comes from SQSS file only. "
            "The file listed in the prompt as 'Attendance 2023-24 (~118 MB)' "
            "is NOT present — attendance data is in the SQSS file "
            "under Measure='Regular Attendance'."
        )


def main():
    logger.info("=" * 70)
    logger.info("OSPI DATA EXPLORATION")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    explore_enrollment()
    explore_discipline()
    explore_assessment()
    explore_growth()
    explore_sqss()
    explore_ppe()
    explore_attendance_sqss_overlap()

    logger.info("\n" + "=" * 70)
    logger.info("OSPI EXPLORATION COMPLETE")
    logger.info(f"Log saved to {log_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
