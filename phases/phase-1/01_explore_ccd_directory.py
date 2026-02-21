"""
01_explore_ccd_directory.py — Read the NCES CCD School Directory and extract WA schools.

The CCD directory is the "spine" of the dataset: it provides the canonical list of
WA schools, their NCES IDs (the universal primary key), and — critically — the
ST_SCHID field that maps NCES IDs to OSPI's SchoolCode/DistrictCode.

Input:  WA-raw/federal/ccd_sch_029_2425_w_1a_073025.zip (2024-25 school year)
Output: data/ccd_wa_directory.csv (WA schools only)
Logs:   logs/01_explore_ccd_directory_YYYY-MM-DD.log
"""

import os
import sys
import csv
import logging
from datetime import datetime
import zipfile
import io

# Add project root to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

# ---------------------------------------------------------------------------
# Logging setup — console AND file, as CLAUDE.md requires
# ---------------------------------------------------------------------------
log_dir = config.LOGS_DIR
os.makedirs(log_dir, exist_ok=True)

log_filename = f"01_explore_ccd_directory_{datetime.now().strftime('%Y-%m-%d')}.log"
log_path = os.path.join(log_dir, log_filename)

logger = logging.getLogger("ccd_directory")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
logger.addHandler(file_handler)


def read_ccd_directory():
    """Read the CCD directory CSV from its ZIP file and filter to WA schools."""

    zip_path = os.path.join(
        config.RAW_DIR, "federal", "ccd_sch_029_2425_w_1a_073025.zip"
    )
    csv_name = "ccd_sch_029_2425_w_1a_073025.csv"

    if not os.path.exists(zip_path):
        logger.error(
            f"CCD directory ZIP not found at {zip_path}. "
            "This file should have been downloaded in Phase 0. "
            "Re-download from https://nces.ed.gov/ccd/files.asp"
        )
        sys.exit(1)

    logger.info(f"Reading CCD directory from {zip_path}")

    # Read CSV from ZIP. All ID columns read as strings to preserve leading zeros.
    # NCES IDs are 12-char strings like "530042000104" — if read as int, the
    # leading zero gets stripped and the ID becomes 11 digits. This breaks joins.
    wa_rows = []
    total_national = 0

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(csv_name) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            header = reader.fieldnames

            for row in reader:
                total_national += 1
                if row["ST"] == "WA":
                    wa_rows.append(row)

    logger.info(f"Total schools nationally: {total_national:,}")
    logger.info(f"WA schools found: {len(wa_rows):,}")

    return header, wa_rows


def analyze_wa_schools(header, wa_rows):
    """Log summary statistics about WA schools."""

    # Count by status
    status_counts = {}
    for row in wa_rows:
        status = row["SY_STATUS_TEXT"]
        status_counts[status] = status_counts.get(status, 0) + 1

    logger.info("--- School Status Distribution ---")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  {status}: {count}")

    # Count by type
    type_counts = {}
    for row in wa_rows:
        sch_type = row["SCH_TYPE_TEXT"]
        type_counts[sch_type] = type_counts.get(sch_type, 0) + 1

    logger.info("--- School Type Distribution ---")
    for sch_type, count in sorted(type_counts.items()):
        logger.info(f"  {sch_type}: {count}")

    # Count by level
    level_counts = {}
    for row in wa_rows:
        level = row["LEVEL"]
        level_counts[level] = level_counts.get(level, 0) + 1

    logger.info("--- School Level Distribution ---")
    for level, count in sorted(level_counts.items()):
        logger.info(f"  {level}: {count}")

    # Charter status
    charter_counts = {}
    for row in wa_rows:
        charter = row["CHARTER_TEXT"]
        charter_counts[charter] = charter_counts.get(charter, 0) + 1

    logger.info("--- Charter Status ---")
    for charter, count in sorted(charter_counts.items()):
        logger.info(f"  {charter}: {count}")

    # Verify NCESSCH format: all should be 12 characters
    ncessch_lengths = {}
    for row in wa_rows:
        length = len(row["NCESSCH"])
        ncessch_lengths[length] = ncessch_lengths.get(length, 0) + 1

    logger.info("--- NCESSCH Length Distribution ---")
    for length, count in sorted(ncessch_lengths.items()):
        logger.info(f"  {length} chars: {count}")
        if length != 12:
            logger.warning(
                f"  WARNING: Found {count} NCESSCH values with {length} chars "
                f"instead of expected 12. This may indicate data quality issues."
            )


def test_crosswalk_pattern(wa_rows):
    """Parse ST_SCHID to extract OSPI DistrictCode and SchoolCode."""

    logger.info("--- Crosswalk Pattern Test (ST_SCHID → OSPI codes) ---")

    # ST_SCHID format should be WA-{DistrictCode}-{SchoolCode}
    parse_success = 0
    parse_fail = 0
    sample_mappings = []

    for row in wa_rows:
        st_schid = row["ST_SCHID"]
        ncessch = row["NCESSCH"]

        # Try to parse the WA-XXXXX-YYYY pattern
        parts = st_schid.split("-")
        if len(parts) == 3 and parts[0] == "WA":
            district_code = parts[1]
            school_code = parts[2]
            parse_success += 1

            # Save first 5 for logging
            if len(sample_mappings) < 5:
                sample_mappings.append({
                    "ncessch": ncessch,
                    "st_schid": st_schid,
                    "district_code": district_code,
                    "school_code": school_code,
                    "school_name": row["SCH_NAME"],
                })
        else:
            parse_fail += 1
            if parse_fail <= 5:
                logger.warning(
                    f"  Could not parse ST_SCHID '{st_schid}' for {row['SCH_NAME']}. "
                    f"Expected format: WA-XXXXX-YYYY"
                )

    logger.info(f"  Successfully parsed: {parse_success:,} ({100*parse_success/len(wa_rows):.1f}%)")
    logger.info(f"  Failed to parse: {parse_fail:,}")

    logger.info("  Sample crosswalk mappings:")
    for m in sample_mappings:
        logger.info(
            f"    {m['school_name']:40s} NCESSCH={m['ncessch']}  "
            f"ST_SCHID={m['st_schid']}  → DistrictCode={m['district_code']}, "
            f"SchoolCode={m['school_code']}"
        )

    # Find Fairhaven Middle School specifically
    logger.info("--- Fairhaven Middle School Lookup ---")
    fairhaven_found = False
    for row in wa_rows:
        if "fairhaven" in row["SCH_NAME"].lower() and "middle" in row["SCH_NAME"].lower():
            fairhaven_found = True
            parts = row["ST_SCHID"].split("-")
            logger.info(f"  School Name:    {row['SCH_NAME']}")
            logger.info(f"  District:       {row['LEA_NAME']}")
            logger.info(f"  NCESSCH:        {row['NCESSCH']}")
            logger.info(f"  ST_SCHID:       {row['ST_SCHID']}")
            logger.info(f"  LEAID:          {row['LEAID']}")
            logger.info(f"  City:           {row['LCITY']}")
            logger.info(f"  ZIP:            {row['LZIP']}")
            logger.info(f"  School Type:    {row['SCH_TYPE_TEXT']}")
            logger.info(f"  Level:          {row['LEVEL']}")
            logger.info(f"  Grade Span:     {row['GSLO']}–{row['GSHI']}")
            logger.info(f"  Charter:        {row['CHARTER_TEXT']}")
            logger.info(f"  Status:         {row['SY_STATUS_TEXT']}")
            if len(parts) == 3:
                logger.info(f"  Parsed DistrictCode: {parts[1]}")
                logger.info(f"  Parsed SchoolCode:   {parts[2]}")

    if not fairhaven_found:
        logger.error(
            "Fairhaven Middle School NOT FOUND in CCD directory. "
            "This is unexpected — check that the file is the 2024-25 CCD "
            "and that WA filtering is correct."
        )


def save_wa_extract(header, wa_rows):
    """Save WA-only directory data to a CSV for use by later scripts."""

    output_path = os.path.join(config.DATA_DIR, "ccd_wa_directory.csv")
    os.makedirs(config.DATA_DIR, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(wa_rows)

    logger.info(f"Saved {len(wa_rows):,} WA schools to {output_path}")


def main():
    logger.info("=" * 70)
    logger.info("CCD SCHOOL DIRECTORY EXPLORATION")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    header, wa_rows = read_ccd_directory()
    analyze_wa_schools(header, wa_rows)
    test_crosswalk_pattern(wa_rows)
    save_wa_extract(header, wa_rows)

    logger.info("=" * 70)
    logger.info("CCD Directory exploration complete.")
    logger.info(f"Log saved to {log_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
