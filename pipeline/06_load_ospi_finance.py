"""
06_load_ospi_finance.py — Add per-pupil expenditure from OSPI PPE data.

PURPOSE: Add per-pupil expenditure (total, local, state, federal) from OSPI PPE.
INPUTS: WA-raw/ospi/Per_Pupil_Expenditure_AllYears.csv,
        data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with finance section
JOIN KEYS: SchoolCode (PPE) → metadata.ospi_school_code (spine).
           No DistrictCode needed — SchoolCode is unique statewide (verified: 0 collisions).
SUPPRESSION HANDLING: None expected (financial data, not student counts)
RECEIPT: phases/phase-2/receipt.md — finance section
FAILURE MODES: Multi-year file — filter to 2023-24. Dollar values have commas.
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, safe_float,
    FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_ospi_finance(logger):
    """Read OSPI PPE and add per-pupil expenditure to each school."""

    schools = load_schools()

    source_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Per_Pupil_Expenditure_AllYears.csv"
    )

    if not os.path.exists(source_path):
        logger.error(f"OSPI PPE file not found at {source_path}.")
        return False

    # Build lookup: ospi_school_code → ncessch
    # SchoolCode is unique statewide in PPE (verified: 0 collisions), so no
    # DistrictCode is needed to disambiguate.
    school_code_lookup = {}
    for ncessch, doc in schools.items():
        meta = doc.get("metadata", {})
        sch_code = meta.get("ospi_school_code")
        if sch_code:
            school_code_lookup[str(sch_code)] = ncessch

    logger.info(f"SchoolCode lookup: {len(school_code_lookup)} entries. No collisions found.")

    matched = 0
    unmatched = 0

    # SOURCE: WA-raw/ospi/Per_Pupil_Expenditure_AllYears.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # RULE: Filter to school-level, 2023-24 year only
            org_level = (row.get("Organization Level") or "").strip()
            year_code = (row.get("School Year Code") or "").strip()

            if org_level != "School" or year_code != "2023-24":
                continue

            school_code = (row.get("SchoolCode") or "").strip()
            ncessch = school_code_lookup.get(school_code)

            if ncessch is None:
                unmatched += 1
                continue

            # LINEAGE: Total_PPE → finance.per_pupil_total
            # Dollar values have commas (e.g., "17,778.96") — safe_float strips them
            finance = {
                "year": "2023-24",
                "per_pupil_total": safe_float(row.get("Total_PPE")),
                "per_pupil_local": safe_float(row.get("Local PPE")),
                "per_pupil_state": safe_float(row.get("State PPE")),
                "per_pupil_federal": safe_float(row.get("Federal PPE")),
            }

            schools[ncessch]["finance"] = finance
            matched += 1

    save_schools(schools)

    missing = sum(1 for doc in schools.values() if "finance" not in doc)

    logger.info(f"{matched} schools matched OSPI PPE data.")
    if unmatched > 0:
        logger.info(f"{unmatched} PPE rows did not match any school in the spine.")
    if missing > 0:
        logger.info(f"{missing} schools have no PPE data.")

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools and "finance" in schools[FAIRHAVEN_NCESSCH]:
        fin = schools[FAIRHAVEN_NCESSCH]["finance"]
        logger.info(
            f"Fairhaven finance: total=${fin.get('per_pupil_total')}, "
            f"local=${fin.get('per_pupil_local')}, "
            f"state=${fin.get('per_pupil_state')}, "
            f"federal=${fin.get('per_pupil_federal')}."
        )
    else:
        logger.warning("Fairhaven PPE data not found.")

    return True


def main():
    logger = setup_logging("06_load_ospi_finance")
    logger.info("Step 06: Loading OSPI per-pupil expenditure.")

    success = load_ospi_finance(logger)

    if success:
        logger.info("Step 06 complete.")
    else:
        logger.error("Step 06 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
