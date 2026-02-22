"""
03_load_ospi_enrollment.py — Add OSPI demographic subgroup data to the spine.

PURPOSE: Add FRL, ELL, SPED, Section 504, foster care, homeless, and migrant
         counts from OSPI Enrollment data. These demographics come from OSPI
         because CCD does not carry FRL data.
INPUTS: WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv,
        data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with demographics section
JOIN KEYS: DistrictCode + SchoolCode → metadata.ospi_district_code + metadata.ospi_school_code
SUPPRESSION HANDLING: OSPI N<10 → null + suppressed. "No Students" → null. Blank → null.
                      DAT column contains suppression reasons.
RECEIPT: phases/phase-2/receipt.md — demographics section
FAILURE MODES: 6 schools with 9xx district codes won't match — log, don't fail
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, build_ospi_lookup,
    parse_ospi_value, safe_int, FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_ospi_enrollment(logger):
    """Read OSPI Enrollment and add demographics to each school document."""

    schools = load_schools()
    lookup = build_ospi_lookup(schools)

    source_path = os.path.join(
        config.RAW_DIR, "ospi",
        "Report_Card_Enrollment_2023-24_School_Year.csv"
    )

    if not os.path.exists(source_path):
        logger.error(
            f"OSPI enrollment file not found at {source_path}. "
            "Check that WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv exists."
        )
        return False

    matched = 0
    unmatched = 0

    # SOURCE: WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # RULE: Filter to school-level, all-grades aggregate rows only
            org_level = (row.get("OrganizationLevel") or "").strip()
            grade_level = (row.get("GradeLevel") or "").strip()

            if org_level != "School" or grade_level != "All Grades":
                continue

            district_code = (row.get("DistrictCode") or "").strip()
            school_code = (row.get("SchoolCode") or "").strip()

            key = (district_code, school_code)
            ncessch = lookup.get(key)

            if ncessch is None:
                unmatched += 1
                continue

            # The DAT column contains suppression info for the entire row
            dat_field = row.get("DAT", "")

            # LINEAGE: OSPI enrollment columns → demographics section
            # Parse 'All Students' for the total, then each subgroup
            all_students_val, _ = parse_ospi_value(row.get("All Students"), dat_field)
            frl_val, frl_flag = parse_ospi_value(row.get("Low Income"), dat_field)
            ell_val, ell_flag = parse_ospi_value(row.get("English Language Learners"), dat_field)
            sped_val, sped_flag = parse_ospi_value(row.get("Students with Disabilities"), dat_field)
            sec504_val, sec504_flag = parse_ospi_value(row.get("Section 504"), dat_field)
            foster_val, foster_flag = parse_ospi_value(row.get("Foster Care"), dat_field)
            homeless_val, homeless_flag = parse_ospi_value(row.get("Homeless"), dat_field)
            migrant_val, migrant_flag = parse_ospi_value(row.get("Migrant"), dat_field)

            demographics = {
                "year": "2023-24",
                "ospi_total": safe_int(all_students_val) if all_students_val is not None else None,
            }

            # FRL count and derived percentage
            if frl_val is not None:
                demographics["frl_count"] = safe_int(frl_val)
                # Derive FRL percentage from count / All Students
                if all_students_val and all_students_val > 0:
                    demographics["frl_pct"] = round(frl_val / all_students_val, 4)
            elif frl_flag:
                demographics["frl_count"] = None
                demographics["frl_suppressed"] = True

            # ELL
            if ell_val is not None:
                demographics["ell_count"] = safe_int(ell_val)
            elif ell_flag:
                demographics["ell_count"] = None
                demographics["ell_suppressed"] = True

            # SPED
            if sped_val is not None:
                demographics["sped_count"] = safe_int(sped_val)
            elif sped_flag:
                demographics["sped_count"] = None
                demographics["sped_suppressed"] = True

            # Section 504
            if sec504_val is not None:
                demographics["section_504_count"] = safe_int(sec504_val)
            elif sec504_flag:
                demographics["section_504_count"] = None
                demographics["section_504_suppressed"] = True

            # Foster care
            if foster_val is not None:
                demographics["foster_care_count"] = safe_int(foster_val)
            elif foster_flag:
                demographics["foster_care_count"] = None
                demographics["foster_care_suppressed"] = True

            # Homeless
            if homeless_val is not None:
                demographics["homeless_count"] = safe_int(homeless_val)
            elif homeless_flag:
                demographics["homeless_count"] = None
                demographics["homeless_suppressed"] = True

            # Migrant
            if migrant_val is not None:
                demographics["migrant_count"] = safe_int(migrant_val)
            elif migrant_flag:
                demographics["migrant_count"] = None
                demographics["migrant_suppressed"] = True

            schools[ncessch]["demographics"] = demographics
            matched += 1

    save_schools(schools)

    # Count schools missing demographics
    missing = sum(1 for doc in schools.values() if "demographics" not in doc)

    logger.info(f"{matched} schools matched OSPI enrollment data.")
    if unmatched > 0:
        logger.info(
            f"{unmatched} OSPI enrollment rows did not match any school in the spine "
            "(likely ESDs or special entities with 9xx district codes)."
        )
    if missing > 0:
        logger.info(f"{missing} schools in the spine have no OSPI demographics data.")

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools and "demographics" in schools[FAIRHAVEN_NCESSCH]:
        dem = schools[FAIRHAVEN_NCESSCH]["demographics"]
        logger.info(
            f"Fairhaven demographics: FRL={dem.get('frl_count')}, "
            f"ELL={dem.get('ell_count')}, SPED={dem.get('sped_count')}, "
            f"Section 504={dem.get('section_504_count')}, "
            f"Homeless={dem.get('homeless_count')}."
        )
    else:
        logger.warning("Fairhaven demographics not found. Check crosswalk join.")

    return True


def main():
    logger = setup_logging("03_load_ospi_enrollment")
    logger.info("Step 03: Loading OSPI enrollment demographics.")

    success = load_ospi_enrollment(logger)

    if success:
        logger.info("Step 03 complete.")
    else:
        logger.error("Step 03 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
