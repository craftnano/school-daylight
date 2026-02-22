"""
01_build_spine.py — Create one document per WA school from the CCD Directory.

PURPOSE: Build the pipeline's starting point: a base document for every open
         WA school, with identity fields and the crosswalk codes needed to
         join OSPI data in later steps.
INPUTS: data/ccd_wa_directory.csv
OUTPUTS: Creates data/schools_pipeline.json with ~2,532 base documents
JOIN KEYS: NCESSCH (12-char string, primary key for all downstream joins)
SUPPRESSION HANDLING: None needed for directory fields
RECEIPT: phases/phase-2/receipt.md — spine section
FAILURE MODES: Missing NCESSCH, non-WA schools leaking in
"""

import os
import sys
import csv

# Add pipeline dir to path for helpers import
sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, save_schools, INTERMEDIATE_PATH, FAIRHAVEN_NCESSCH
)

# Add project root for config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def parse_st_schid(st_schid):
    """Parse ST_SCHID (format 'WA-{DistrictCode}-{SchoolCode}') into its parts.

    Returns (district_code, school_code) as strings, or (None, None) if
    the format doesn't match. These codes are used by OSPI files, which
    don't use NCES IDs — this is how we join OSPI data to the CCD spine.
    """
    # LINEAGE: ST_SCHID → metadata.ospi_district_code, metadata.ospi_school_code
    if not st_schid or not st_schid.startswith("WA-"):
        return (None, None)

    parts = st_schid.split("-")
    if len(parts) != 3:
        return (None, None)

    return (parts[1], parts[2])


def build_spine(logger):
    """Read CCD Directory and create one base document per open WA school."""

    source_path = os.path.join(config.DATA_DIR, "ccd_wa_directory.csv")

    if not os.path.exists(source_path):
        logger.error(
            f"CCD directory file not found at {source_path}. "
            "This file should have been created in Phase 1. "
            "Check that data/ccd_wa_directory.csv exists."
        )
        return False

    # Delete any existing intermediate file for a clean start.
    # This guarantees idempotency — every full run starts fresh.
    if os.path.exists(INTERMEDIATE_PATH):
        os.remove(INTERMEDIATE_PATH)
        logger.info(f"Deleted existing intermediate file at {INTERMEDIATE_PATH}.")

    schools = {}
    skipped_status = 0
    skipped_no_ncessch = 0

    # SOURCE: data/ccd_wa_directory.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # RULE: Only include open schools. Closed/Inactive/Future/New are excluded.
            status = (row.get("SY_STATUS_TEXT") or "").strip()
            if status != "Open":
                skipped_status += 1
                continue

            ncessch = (row.get("NCESSCH") or "").strip()
            if not ncessch:
                skipped_no_ncessch += 1
                continue

            # Parse ST_SCHID to get OSPI district and school codes for crosswalk
            district_code, school_code = parse_st_schid(
                (row.get("ST_SCHID") or "").strip()
            )

            # RULE: CHARTER_TEXT → boolean
            charter_text = (row.get("CHARTER_TEXT") or "").strip()
            is_charter = charter_text == "Yes"

            # Build the base document — identity, location, and crosswalk codes
            doc = {
                "_id": ncessch,
                "name": (row.get("SCH_NAME") or "").strip(),
                "district": {
                    "name": (row.get("LEA_NAME") or "").strip(),
                    "nces_id": (row.get("LEAID") or "").strip(),
                },
                "address": {
                    "street": (row.get("LSTREET1") or "").strip(),
                    "city": (row.get("LCITY") or "").strip(),
                    "state": (row.get("LSTATE") or "").strip(),
                    "zip": (row.get("LZIP") or "").strip(),
                },
                "school_type": (row.get("SCH_TYPE_TEXT") or "").strip(),
                "level": (row.get("LEVEL") or "").strip(),
                "grade_span": {
                    "low": (row.get("GSLO") or "").strip(),
                    "high": (row.get("GSHI") or "").strip(),
                },
                "is_charter": is_charter,
                "website": (row.get("WEBSITE") or "").strip(),
                "phone": (row.get("PHONE") or "").strip(),
                "metadata": {
                    "ospi_district_code": district_code,
                    "ospi_school_code": school_code,
                },
            }

            schools[ncessch] = doc

    # Save the intermediate file
    save_schools(schools)

    # Log results
    logger.info(f"Created {len(schools)} base documents from CCD Directory.")
    if skipped_status > 0:
        logger.info(f"Skipped {skipped_status} non-open schools (Closed, Inactive, Future, or New).")
    if skipped_no_ncessch > 0:
        logger.warning(f"Skipped {skipped_no_ncessch} rows with missing NCESSCH.")

    # Fairhaven check — our golden reference school must be present
    if FAIRHAVEN_NCESSCH in schools:
        fh = schools[FAIRHAVEN_NCESSCH]
        logger.info(
            f"Fairhaven Middle School ({FAIRHAVEN_NCESSCH}): found. "
            f"Name='{fh['name']}', District='{fh['district']['name']}', "
            f"OSPI codes=({fh['metadata']['ospi_district_code']}, {fh['metadata']['ospi_school_code']})."
        )
    else:
        logger.error(
            f"Fairhaven Middle School ({FAIRHAVEN_NCESSCH}) NOT FOUND in spine. "
            "This is a critical error — Fairhaven is the golden reference school. "
            "Check that ccd_wa_directory.csv contains this NCESSCH and that the "
            "school's SY_STATUS_TEXT is 'Open'."
        )
        return False

    return True


def main():
    logger = setup_logging("01_build_spine")
    logger.info("Step 01: Building CCD spine from directory data.")

    success = build_spine(logger)

    if success:
        logger.info("Step 01 complete.")
    else:
        logger.error("Step 01 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
