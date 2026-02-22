"""
02_load_enrollment.py — Add CCD Membership enrollment data to the spine.

PURPOSE: Add total enrollment, enrollment by race (7 categories), and
         enrollment by sex (male/female) from CCD Membership data.
INPUTS: data/ccd_wa_membership.csv, data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with enrollment section
JOIN KEYS: ncessch (membership CSV) → _id (spine)
SUPPRESSION HANDLING: CCD -1 → null + not_reported. Phase 1 already
                      excluded DMS_FLAG "Not reported" rows.
RECEIPT: phases/phase-2/receipt.md — enrollment section
FAILURE MODES: Schools in spine but not in membership (some have 0 enrollment)
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, safe_int,
    FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_enrollment(logger):
    """Read CCD Membership and add enrollment data to each school document."""

    schools = load_schools()
    source_path = os.path.join(config.DATA_DIR, "ccd_wa_membership.csv")

    if not os.path.exists(source_path):
        logger.error(
            f"CCD membership file not found at {source_path}. "
            "This file should have been created in Phase 1. "
            "Check that data/ccd_wa_membership.csv exists."
        )
        return False

    matched = 0
    unmatched_ids = []

    # SOURCE: data/ccd_wa_membership.csv (Phase 1 pre-aggregated: one row per school)
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            ncessch = (row.get("ncessch") or "").strip()

            if ncessch not in schools:
                unmatched_ids.append(ncessch)
                continue

            # LINEAGE: ccd_wa_membership columns → enrollment section
            total = safe_int(row.get("total_enrollment"))

            enrollment = {
                "year": "2023-24",
                "total": total,
                "by_race": {
                    "american_indian": safe_int(row.get("american_indian")),
                    "asian": safe_int(row.get("asian")),
                    "black": safe_int(row.get("black")),
                    "hispanic": safe_int(row.get("hispanic")),
                    "pacific_islander": safe_int(row.get("pacific_islander")),
                    "two_or_more": safe_int(row.get("two_or_more")),
                    "white": safe_int(row.get("white")),
                },
                "by_sex": {
                    "male": safe_int(row.get("male")),
                    "female": safe_int(row.get("female")),
                },
            }

            # Include not_specified if present and non-zero
            not_specified = safe_int(row.get("not_specified"))
            if not_specified and not_specified > 0:
                enrollment["by_race"]["not_specified"] = not_specified

            schools[ncessch]["enrollment"] = enrollment
            matched += 1

    # Count schools in spine that have no enrollment data
    missing_enrollment = sum(
        1 for doc in schools.values() if "enrollment" not in doc
    )

    save_schools(schools)

    # Log results
    logger.info(f"{matched} schools matched CCD enrollment data.")
    if unmatched_ids:
        logger.info(
            f"{len(unmatched_ids)} membership rows did not match any school in the spine "
            "(these are likely closed/inactive schools filtered out in step 01)."
        )
    if missing_enrollment > 0:
        logger.info(
            f"{missing_enrollment} schools in the spine have no enrollment data "
            "(no matching row in CCD membership)."
        )

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools and "enrollment" in schools[FAIRHAVEN_NCESSCH]:
        fh_enroll = schools[FAIRHAVEN_NCESSCH]["enrollment"]
        logger.info(
            f"Fairhaven enrollment: total={fh_enroll['total']}, "
            f"white={fh_enroll['by_race'].get('white')}, "
            f"hispanic={fh_enroll['by_race'].get('hispanic')}, "
            f"male={fh_enroll['by_sex'].get('male')}, "
            f"female={fh_enroll['by_sex'].get('female')}."
        )
    else:
        logger.warning("Fairhaven enrollment data not found. Check join.")

    return True


def main():
    logger = setup_logging("02_load_enrollment")
    logger.info("Step 02: Loading CCD enrollment data.")

    success = load_enrollment(logger)

    if success:
        logger.info("Step 02 complete.")
    else:
        logger.error("Step 02 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
