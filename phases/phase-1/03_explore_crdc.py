"""
03_explore_crdc.py — Read CRDC school-level CSVs and extract WA data.

The CRDC ZIP contains 35 CSVs covering ~98,000 schools nationally.
We read the 13 school-level CSVs we need, filter to WA, audit suppression
markers (-9, -2, etc.), and save WA-only extracts.

CRDC join key: COMBOKEY = LEAID + SCHID (12 chars) = CCD's NCESSCH.

Input:  WA-raw/federal/2021-22-crdc-data.zip
Output: data/crdc_wa/*.csv (one per CRDC category)
Logs:   logs/03_explore_crdc_YYYY-MM-DD.log
"""

import os
import sys
import csv
import logging
from datetime import datetime
from collections import defaultdict
import zipfile
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
log_dir = config.LOGS_DIR
os.makedirs(log_dir, exist_ok=True)

log_filename = f"03_explore_crdc_{datetime.now().strftime('%Y-%m-%d')}.log"
log_path = os.path.join(log_dir, log_filename)

logger = logging.getLogger("crdc")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
logger.addHandler(file_handler)


# The 13 CRDC school-level CSVs we need for the briefing
CRDC_FILES = [
    "SCH/Enrollment.csv",
    "SCH/Suspensions.csv",
    "SCH/Expulsions.csv",
    "SCH/Restraint and Seclusion.csv",
    "SCH/Referrals and Arrests.csv",
    "SCH/Harassment and Bullying.csv",
    "SCH/School Support.csv",
    "SCH/Advanced Placement.csv",
    "SCH/Dual Enrollment.csv",
    "SCH/Gifted and Talented.csv",
    "SCH/Offenses.csv",
    "SCH/Corporal Punishment.csv",
    "SCH/School Characteristics.csv",
]

# CRDC suppression markers and their meanings
SUPPRESSION_MARKERS = {
    "-9": "Not applicable / skipped",
    "-2": "Data not available",
    "-4": "Suppressed (teacher sex counts)",
    "-5": "Suppressed (small count)",
    "-6": "Suppressed (related to small count)",
}

FAIRHAVEN_COMBOKEY = "530042000104"


def find_state_column(header):
    """Find the column that identifies the state in a CRDC CSV.

    CRDC files use LEA_STATE for the state code. Some files may use
    different column names — this function handles that.
    """
    for col in ["LEA_STATE", "LEA_ST"]:
        if col in header:
            return col
    return None


def find_combokey_column(header):
    """Find the COMBOKEY column (the join key to CCD NCESSCH)."""
    for col in ["COMBOKEY", "Combo Key", "combo_key"]:
        if col in header:
            return col
    return None


def scan_suppression_markers(rows, header, csv_name):
    """Scan all numeric columns for suppression markers and zero values.

    Returns a dict of {marker: count} and a count of genuine zeros.
    """
    marker_counts = defaultdict(int)
    zero_counts = 0
    negative_other = defaultdict(int)

    # Identify likely-numeric columns (skip known string ID/name columns)
    id_columns = {
        "COMBOKEY", "LEA_STATE", "LEA_NAME", "LEAID", "SCHID",
        "SCH_NAME", "NCESSCH", "JJ",
    }

    for row in rows:
        for col in header:
            if col in id_columns:
                continue
            val = row.get(col, "").strip()
            if val in SUPPRESSION_MARKERS:
                marker_counts[val] += 1
            elif val == "0":
                zero_counts += 1
            elif val.startswith("-") and val not in ("", "-"):
                # Any other negative value — might be a suppression code we missed
                try:
                    num = int(val)
                    if num < -1:
                        negative_other[val] += 1
                except ValueError:
                    try:
                        num = float(val)
                        if num < -1:
                            negative_other[val] += 1
                    except ValueError:
                        pass

    return marker_counts, zero_counts, negative_other


def explore_crdc_file(zf, csv_name):
    """Read one CRDC CSV from the ZIP, filter to WA, and analyze it."""

    logger.info(f"\n{'='*60}")
    logger.info(f"Reading: {csv_name}")

    with zf.open(csv_name) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        header = list(reader.fieldnames)

        state_col = find_state_column(header)
        combokey_col = find_combokey_column(header)

        if not state_col:
            logger.warning(f"  Could not find state column in {csv_name}. Columns: {header[:10]}")
            return None, None

        if not combokey_col:
            logger.warning(f"  Could not find COMBOKEY column in {csv_name}. Columns: {header[:10]}")

        all_rows = list(reader)

    total_national = len(all_rows)
    wa_rows = [r for r in all_rows if r.get(state_col) == "WA"]

    logger.info(f"  National rows: {total_national:,}")
    logger.info(f"  WA rows: {len(wa_rows):,}")
    logger.info(f"  Columns ({len(header)}): {', '.join(header[:15])}{'...' if len(header) > 15 else ''}")

    # Find Fairhaven
    if combokey_col:
        fairhaven_rows = [r for r in wa_rows if r.get(combokey_col) == FAIRHAVEN_COMBOKEY]
        if fairhaven_rows:
            logger.info(f"  Fairhaven (COMBOKEY={FAIRHAVEN_COMBOKEY}): FOUND ({len(fairhaven_rows)} rows)")
            # Log a few key values from Fairhaven
            fh = fairhaven_rows[0]
            # Show up to 10 non-ID columns
            shown = 0
            for col in header:
                if col not in ("COMBOKEY", "LEA_STATE", "LEA_NAME", "LEAID", "SCHID", "SCH_NAME", "NCESSCH", "JJ"):
                    val = fh.get(col, "")
                    if val and val not in ("-9", ""):
                        logger.info(f"    {col}: {val}")
                        shown += 1
                        if shown >= 12:
                            break
        else:
            logger.warning(f"  Fairhaven (COMBOKEY={FAIRHAVEN_COMBOKEY}): NOT FOUND")

    # Suppression audit
    marker_counts, zero_counts, negative_other = scan_suppression_markers(wa_rows, header, csv_name)

    logger.info("  --- Suppression Markers (WA) ---")
    for marker, count in sorted(marker_counts.items(), key=lambda x: -x[1]):
        meaning = SUPPRESSION_MARKERS.get(marker, "Unknown")
        logger.info(f"    {marker:>5s}: {count:>6,} occurrences ({meaning})")
    logger.info(f"    Zero values (genuine): {zero_counts:,}")
    if negative_other:
        logger.info("    Other negative values found:")
        for val, count in sorted(negative_other.items(), key=lambda x: -x[1])[:5]:
            logger.info(f"      {val}: {count:,}")

    return header, wa_rows


def save_wa_extract(csv_name, header, wa_rows):
    """Save WA-only extract to data/crdc_wa/ directory."""

    output_dir = os.path.join(config.DATA_DIR, "crdc_wa")
    os.makedirs(output_dir, exist_ok=True)

    # Use the filename from the ZIP path, e.g. "SCH/Enrollment.csv" → "enrollment.csv"
    base_name = csv_name.split("/")[-1].lower().replace(" ", "_")
    output_path = os.path.join(output_dir, base_name)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(wa_rows)

    logger.info(f"  Saved {len(wa_rows):,} WA rows to {output_path}")


def main():
    logger.info("=" * 70)
    logger.info("CRDC DATA EXPLORATION (2021-22)")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    zip_path = os.path.join(config.RAW_DIR, "federal", "2021-22-crdc-data.zip")
    if not os.path.exists(zip_path):
        logger.error(
            f"CRDC ZIP not found at {zip_path}. "
            "Download from https://ocrdata.ed.gov/resources/downloaddatafile"
        )
        sys.exit(1)

    # Track overall suppression markers across all files
    total_markers = defaultdict(int)
    total_zeros = 0
    total_wa_schools = set()

    with zipfile.ZipFile(zip_path) as zf:
        # First, list all files in the ZIP for documentation
        logger.info("Files in CRDC ZIP:")
        for info in zf.infolist():
            size_mb = info.file_size / (1024 * 1024)
            logger.info(f"  {info.filename:45s} {size_mb:8.1f} MB")

        for csv_name in CRDC_FILES:
            header, wa_rows = explore_crdc_file(zf, csv_name)
            if header and wa_rows:
                save_wa_extract(csv_name, header, wa_rows)

                # Aggregate school IDs
                combokey_col = find_combokey_column(header)
                if combokey_col:
                    for row in wa_rows:
                        total_wa_schools.add(row.get(combokey_col, ""))

                # Aggregate suppression counts
                markers, zeros, _ = scan_suppression_markers(wa_rows, header, csv_name)
                for marker, count in markers.items():
                    total_markers[marker] += count
                total_zeros += zeros

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CRDC EXPLORATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total unique WA schools across all CRDC files: {len(total_wa_schools):,}")
    logger.info("Overall suppression marker counts (all 13 files, WA only):")
    for marker, count in sorted(total_markers.items(), key=lambda x: -x[1]):
        meaning = SUPPRESSION_MARKERS.get(marker, "Unknown")
        logger.info(f"  {marker:>5s}: {count:>8,} ({meaning})")
    logger.info(f"  Genuine zero values: {total_zeros:>8,}")
    logger.info(
        "\nCRITICAL: Zero values represent 'zero incidents reported.' "
        "Suppression markers (-9, -2) represent 'data not available or not applicable.' "
        "These MUST be handled differently in the pipeline."
    )
    logger.info(f"\nLog saved to {log_path}")


if __name__ == "__main__":
    main()
