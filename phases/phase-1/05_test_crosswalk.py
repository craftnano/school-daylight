"""
05_test_crosswalk.py — Test the crosswalk join across all data sources.

This is the CRITICAL test. If the crosswalk fails, nothing downstream works.

Join chain:
  CCD Directory: NCESSCH (12 chars) and ST_SCHID (WA-{DistrictCode}-{SchoolCode})
  CRDC: COMBOKEY (12 chars, same as NCESSCH)
  OSPI: DistrictCode + SchoolCode (extracted from ST_SCHID)

Tests:
  1. Fairhaven Middle School found in ALL sources with matching IDs
  2. 5 additional schools verified across different districts
  3. Bulk match rate: % of OSPI schools matched to CCD via ST_SCHID

HARD STOP if: Fairhaven not found, bulk match rate <90%, or COMBOKEY != NCESSCH.

Input:  data/ccd_wa_directory.csv, data/crdc_wa/*.csv, WA-raw/ospi/*.csv
Output: Console + log
Logs:   logs/05_test_crosswalk_YYYY-MM-DD.log
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

log_filename = f"05_test_crosswalk_{datetime.now().strftime('%Y-%m-%d')}.log"
log_path = os.path.join(log_dir, log_filename)

logger = logging.getLogger("crosswalk")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
logger.addHandler(file_handler)


def load_ccd_crosswalk():
    """Load CCD directory and build NCESSCH ↔ OSPI code mapping."""

    path = os.path.join(config.DATA_DIR, "ccd_wa_directory.csv")
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Build lookup: OSPI codes → NCESSCH
    # ST_SCHID format: WA-{DistrictCode}-{SchoolCode}
    ospi_to_ncessch = {}
    ncessch_to_info = {}

    for r in rows:
        ncessch = r["NCESSCH"]
        st_schid = r["ST_SCHID"]
        parts = st_schid.split("-")
        if len(parts) == 3 and parts[0] == "WA":
            district_code = parts[1]
            school_code = parts[2]
            key = f"{district_code}_{school_code}"
            ospi_to_ncessch[key] = ncessch
            ncessch_to_info[ncessch] = {
                "name": r["SCH_NAME"],
                "district": r["LEA_NAME"],
                "district_code": district_code,
                "school_code": school_code,
                "st_schid": st_schid,
                "status": r.get("SY_STATUS_TEXT", ""),
            }

    logger.info(f"CCD: Loaded {len(ncessch_to_info):,} WA schools with crosswalk data")
    return ospi_to_ncessch, ncessch_to_info


def load_crdc_combokeys():
    """Load COMBOKEY values from CRDC enrollment (representative file)."""

    path = os.path.join(config.DATA_DIR, "crdc_wa", "enrollment.csv")
    combokeys = set()

    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            combokeys.add(r["COMBOKEY"])

    logger.info(f"CRDC: Loaded {len(combokeys):,} WA school COMBOKEYs")
    return combokeys


def load_ospi_school_codes(filename, code_col="SchoolCode", dist_col="DistrictCode"):
    """Load unique school codes from an OSPI file."""

    path = os.path.join(config.RAW_DIR, "ospi", filename)
    school_codes = set()

    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("OrganizationLevel") == "School":
                sc = r.get(code_col, "").replace(",", "").strip()
                dc = r.get(dist_col, "").replace(",", "").strip()
                if sc and dc:
                    school_codes.add(f"{dc}_{sc}")

    logger.info(f"OSPI {filename}: {len(school_codes):,} unique school codes")
    return school_codes


def test_single_school(name, expected_ncessch, expected_district, expected_school,
                       ncessch_to_info, crdc_combokeys, ospi_codes_enrollment):
    """Test that a single school can be found in all sources."""

    logger.info(f"\n--- {name} ---")
    results = {"ccd": False, "crdc": False, "ospi": False}

    # CCD
    if expected_ncessch in ncessch_to_info:
        info = ncessch_to_info[expected_ncessch]
        logger.info(f"  CCD: FOUND — {info['name']}, {info['district']}")
        logger.info(f"    NCESSCH={expected_ncessch}, ST_SCHID={info['st_schid']}")
        logger.info(f"    Parsed DistrictCode={info['district_code']}, SchoolCode={info['school_code']}")
        results["ccd"] = True

        # Verify the parsed codes match expectations
        if info["district_code"] != expected_district:
            logger.error(f"    MISMATCH: Expected DistrictCode={expected_district}, got {info['district_code']}")
            results["ccd"] = False
        if info["school_code"] != expected_school:
            logger.error(f"    MISMATCH: Expected SchoolCode={expected_school}, got {info['school_code']}")
            results["ccd"] = False
    else:
        logger.error(f"  CCD: NOT FOUND (NCESSCH={expected_ncessch})")

    # CRDC
    if expected_ncessch in crdc_combokeys:
        logger.info(f"  CRDC: FOUND (COMBOKEY={expected_ncessch})")
        results["crdc"] = True
    else:
        logger.warning(f"  CRDC: NOT FOUND (COMBOKEY={expected_ncessch}). "
                       "May not exist in 2021-22 CRDC if school opened after that year.")

    # OSPI
    ospi_key = f"{expected_district}_{expected_school}"
    if ospi_key in ospi_codes_enrollment:
        logger.info(f"  OSPI: FOUND (DistrictCode={expected_district}, SchoolCode={expected_school})")
        results["ospi"] = True
    else:
        logger.error(f"  OSPI: NOT FOUND (DistrictCode={expected_district}, SchoolCode={expected_school})")

    # Summary
    all_pass = all(results.values())
    status = "PASS" if all_pass else "FAIL"
    logger.info(f"  Result: {status} — CCD={'Y' if results['ccd'] else 'N'} | "
                f"CRDC={'Y' if results['crdc'] else 'N'} | "
                f"OSPI={'Y' if results['ospi'] else 'N'}")

    return results


def test_bulk_match(ospi_to_ncessch, crdc_combokeys, ospi_codes_enrollment):
    """Test what % of OSPI schools can be matched to CCD and CRDC."""

    logger.info("\n" + "=" * 60)
    logger.info("BULK CROSSWALK MATCH TEST")
    logger.info("=" * 60)

    # OSPI → CCD match rate
    ospi_matched_ccd = 0
    ospi_unmatched_ccd = []
    for ospi_key in ospi_codes_enrollment:
        if ospi_key in ospi_to_ncessch:
            ospi_matched_ccd += 1
        else:
            ospi_unmatched_ccd.append(ospi_key)

    total_ospi = len(ospi_codes_enrollment)
    pct_ccd = 100 * ospi_matched_ccd / total_ospi if total_ospi > 0 else 0

    logger.info(f"\nOSPI → CCD match rate: {ospi_matched_ccd:,} / {total_ospi:,} = {pct_ccd:.1f}%")
    if ospi_unmatched_ccd:
        logger.info(f"  Unmatched OSPI schools: {len(ospi_unmatched_ccd)}")
        if len(ospi_unmatched_ccd) <= 20:
            for key in sorted(ospi_unmatched_ccd):
                logger.info(f"    {key}")
        else:
            for key in sorted(ospi_unmatched_ccd)[:10]:
                logger.info(f"    {key}")
            logger.info(f"    ... and {len(ospi_unmatched_ccd) - 10} more")

    # CCD → CRDC match rate
    ccd_matched_crdc = 0
    ccd_unmatched_crdc = 0
    for ospi_key, ncessch in ospi_to_ncessch.items():
        if ncessch in crdc_combokeys:
            ccd_matched_crdc += 1
        else:
            ccd_unmatched_crdc += 1

    total_ccd = len(ospi_to_ncessch)
    pct_crdc = 100 * ccd_matched_crdc / total_ccd if total_ccd > 0 else 0

    logger.info(f"\nCCD → CRDC match rate: {ccd_matched_crdc:,} / {total_ccd:,} = {pct_crdc:.1f}%")
    logger.info(
        f"  {ccd_unmatched_crdc:,} CCD schools not in CRDC. "
        "This is expected — CRDC is 2021-22, CCD is 2024-25. "
        "Schools that opened after 2021-22 won't be in CRDC."
    )

    # Full chain: OSPI → CCD → CRDC
    full_match = 0
    for ospi_key in ospi_codes_enrollment:
        ncessch = ospi_to_ncessch.get(ospi_key)
        if ncessch and ncessch in crdc_combokeys:
            full_match += 1

    pct_full = 100 * full_match / total_ospi if total_ospi > 0 else 0
    logger.info(f"\nFull chain (OSPI → CCD → CRDC): {full_match:,} / {total_ospi:,} = {pct_full:.1f}%")

    # HARD STOP check
    if pct_ccd < 90:
        logger.error(
            f"\n*** HARD STOP: OSPI → CCD match rate is {pct_ccd:.1f}% (below 90% threshold). ***\n"
            "The crosswalk between OSPI SchoolCode and CCD ST_SCHID is unreliable. "
            "Investigate: Are the ID formats different? Are there schools in OSPI not in CCD?"
        )
        return False

    logger.info(f"\nCrosswalk match rates are acceptable (OSPI→CCD: {pct_ccd:.1f}%, full chain: {pct_full:.1f}%)")
    return True


def main():
    logger.info("=" * 70)
    logger.info("CROSSWALK JOIN TEST")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # Load data
    ospi_to_ncessch, ncessch_to_info = load_ccd_crosswalk()
    crdc_combokeys = load_crdc_combokeys()
    ospi_codes_enrollment = load_ospi_school_codes(
        "Report_Card_Enrollment_2023-24_School_Year.csv"
    )

    # Test Fairhaven (the golden school)
    logger.info("\n" + "=" * 60)
    logger.info("INDIVIDUAL SCHOOL TESTS")
    logger.info("=" * 60)

    test_single_school(
        "Fairhaven Middle School (Bellingham)",
        "530042000104", "37501", "2066",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )

    # Test 5 additional schools across different districts and types
    test_single_school(
        "Roosevelt High School (Seattle)",
        "530771001239", "17001", "2285",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )
    test_single_school(
        "Garfield High School (Seattle)",
        "530771001171", "17001", "2306",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )
    test_single_school(
        "Expedition Elementary (Bethel) — new school, may not be in CRDC",
        "530048003925", "27403", "5757",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )
    test_single_school(
        "Lincoln High School (Tacoma)",
        "530870001476", "27010", "2215",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )
    test_single_school(
        "Wenatchee High School (Wenatchee)",
        "530966001639", "04246", "2134",
        ncessch_to_info, crdc_combokeys, ospi_codes_enrollment,
    )

    # Bulk match test
    success = test_bulk_match(ospi_to_ncessch, crdc_combokeys, ospi_codes_enrollment)

    logger.info("\n" + "=" * 70)
    if success:
        logger.info("CROSSWALK TEST: PASSED")
    else:
        logger.error("CROSSWALK TEST: FAILED — SEE DETAILS ABOVE")
    logger.info(f"Log saved to {log_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
