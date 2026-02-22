"""
05_load_ospi_discipline.py — Add OSPI aggregate discipline rates.

PURPOSE: Add overall discipline rate and counts from OSPI Discipline data.
INPUTS: WA-raw/ospi/Report_Card_Discipline_for_2023-24.csv,
        data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with discipline.ospi section
JOIN KEYS: DistrictCode + SchoolCode → crosswalk (STRIP COMMAS FIRST)
SUPPRESSION HANDLING: N<10 → null + suppressed. "*" → null + masked.
                      Top/Bottom Range (< or >) → null + suppressed.
RECEIPT: phases/phase-2/receipt.md — discipline section
FAILURE MODES: COMMA-IN-IDS BUG — DistrictCode and SchoolCode have commas
               (e.g., "2,066" instead of "2066"). Must strip before joining.
               GradeLevel filter is "All" not "All Grades".
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, build_ospi_lookup,
    parse_ospi_value, parse_percentage, safe_int,
    FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_ospi_discipline(logger):
    """Read OSPI Discipline and add discipline rates to each school."""

    schools = load_schools()
    lookup = build_ospi_lookup(schools)

    source_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_Discipline_for_2023-24.csv"
    )

    if not os.path.exists(source_path):
        logger.error(f"OSPI discipline file not found at {source_path}.")
        return False

    matched = 0
    unmatched = 0

    # SOURCE: WA-raw/ospi/Report_Card_Discipline_for_2023-24.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            org_level = (row.get("OrganizationLevel") or "").strip()
            student_group = (row.get("Student Group") or "").strip()
            # RULE: Discipline file uses "All" for grade level, not "All Grades"
            grade_level = (row.get("GradeLevel") or "").strip()

            if org_level != "School" or student_group != "All Students" or grade_level != "All":
                continue

            # RULE: COMMA-IN-IDS BUG — strip commas from codes before joining
            district_code = (row.get("DistrictCode") or "").strip().replace(",", "")
            school_code = (row.get("SchoolCode") or "").strip().replace(",", "")

            ncessch = lookup.get((district_code, school_code))
            if ncessch is None:
                unmatched += 1
                continue

            dat_notes = row.get("DisciplineDATNotes", "")

            # LINEAGE: DisciplineRate → discipline.ospi.rate (percentage → 0.0-1.0)
            rate_raw = (row.get("DisciplineRate") or "").strip()
            rate_val, rate_flag = parse_ospi_value(rate_raw, dat_notes)

            discipline_ospi = {"year": "2023-24"}

            if rate_val is not None:
                discipline_ospi["rate"] = parse_percentage(rate_raw)
                discipline_ospi["numerator"] = safe_int(
                    parse_ospi_value(row.get("DisciplineNumerator"), dat_notes)[0]
                )
                discipline_ospi["denominator"] = safe_int(
                    parse_ospi_value(row.get("DisciplineDenominator"), dat_notes)[0]
                )
            elif rate_flag:
                discipline_ospi["rate"] = None
                discipline_ospi["suppressed"] = True

            # Nest under discipline.ospi
            if "discipline" not in schools[ncessch]:
                schools[ncessch]["discipline"] = {}
            schools[ncessch]["discipline"]["ospi"] = discipline_ospi
            matched += 1

    save_schools(schools)

    missing = sum(
        1 for doc in schools.values()
        if "discipline" not in doc or "ospi" not in doc.get("discipline", {})
    )

    logger.info(f"{matched} schools matched OSPI discipline data.")
    if unmatched > 0:
        logger.info(f"{unmatched} discipline rows did not match (after comma stripping).")
    if missing > 0:
        logger.info(f"{missing} schools have no OSPI discipline data.")

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools:
        disc = schools[FAIRHAVEN_NCESSCH].get("discipline", {}).get("ospi", {})
        logger.info(
            f"Fairhaven discipline: rate={disc.get('rate')}, "
            f"numerator={disc.get('numerator')}, "
            f"denominator={disc.get('denominator')}."
        )
    else:
        logger.warning("Fairhaven discipline data not found.")

    return True


def main():
    logger = setup_logging("05_load_ospi_discipline")
    logger.info("Step 05: Loading OSPI discipline rates.")

    success = load_ospi_discipline(logger)

    if success:
        logger.info("Step 05 complete.")
    else:
        logger.error("Step 05 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
