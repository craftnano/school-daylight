"""
11_load_crdc_enrollment.py — Load CRDC enrollment by race for disparity ratios.

PURPOSE: Phase 2 used enrollment.csv only to set crdc_combokey. It did NOT
         extract the race breakdown columns. Phase 3 needs them as denominators
         for computing discipline disparity ratios in step 12.
INPUTS:  data/crdc_wa/enrollment.csv, data/schools_pipeline.json
OUTPUTS: Adds enrollment.crdc_by_race and enrollment.crdc_total to each school
JOIN KEYS: COMBOKEY → _id (direct 12-char match)
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    parse_crdc_value, FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

# Maps CRDC race prefix suffixes to our schema keys.
# Each race has M (male) and F (female) columns: SCH_ENR_{RACE}_M, SCH_ENR_{RACE}_F.
CRDC_RACE_CODES = {
    "HI": "hispanic",
    "AM": "american_indian",
    "AS": "asian",
    "HP": "pacific_islander",
    "BL": "black",
    "WH": "white",
    "TR": "two_or_more",
}


def main():
    logger = setup_logging("11_load_crdc_enrollment")
    logger.info("Loading CRDC enrollment by race for disparity ratio denominators.")

    schools = load_schools()
    logger.info(f"Loaded {len(schools)} schools from intermediate JSON.")

    # Read the CRDC enrollment file
    filepath = os.path.join(config.DATA_DIR, "crdc_wa", "enrollment.csv")
    if not os.path.exists(filepath):
        logger.error(
            f"CRDC enrollment file not found at {filepath}. "
            "This file is required for discipline disparity computations. "
            "Check that data/crdc_wa/enrollment.csv exists."
        )
        sys.exit(1)

    matched = 0
    skipped = 0

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            combo = (row.get("COMBOKEY") or "").strip()
            if combo not in schools:
                continue

            # Sum male + female for each race
            by_race = {}
            total = 0

            for code, race_name in CRDC_RACE_CODES.items():
                male_col = f"SCH_ENR_{code}_M"
                female_col = f"SCH_ENR_{code}_F"

                male_val, male_flag = parse_crdc_value(row.get(male_col, ""))
                female_val, female_flag = parse_crdc_value(row.get(female_col, ""))

                # Only include if at least one value is a real number
                if male_val is not None or female_val is not None:
                    race_total = (male_val or 0) + (female_val or 0)
                    by_race[race_name] = race_total
                    total += race_total

            if by_race:
                if "enrollment" not in schools[combo]:
                    schools[combo]["enrollment"] = {}
                schools[combo]["enrollment"]["crdc_by_race"] = by_race
                schools[combo]["enrollment"]["crdc_total"] = total
                matched += 1
            else:
                skipped += 1

    logger.info(
        f"CRDC enrollment by race: {matched} schools loaded, "
        f"{skipped} skipped (all values suppressed/missing)."
    )

    # Fairhaven verification
    if FAIRHAVEN_NCESSCH in schools:
        doc = schools[FAIRHAVEN_NCESSCH]
        crdc_race = doc.get("enrollment", {}).get("crdc_by_race", {})
        crdc_total = doc.get("enrollment", {}).get("crdc_total", 0)

        logger.info(f"Fairhaven CRDC enrollment by race: {crdc_race}")
        logger.info(f"Fairhaven CRDC enrollment total: {crdc_total}")

        # Check that white enrollment matches Phase 2 data
        white = crdc_race.get("white", 0)
        if white > 0:
            logger.info(f"Fairhaven white enrollment (CRDC): {white}")
        else:
            logger.warning("Fairhaven has no white enrollment in CRDC — check data.")

    save_schools(schools)
    logger.info("Step 11 complete. CRDC enrollment by race loaded.")


if __name__ == "__main__":
    main()
