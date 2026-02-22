"""
helpers.py — Shared utilities for all pipeline scripts.

Every pipeline step imports from here. Contains logging setup,
suppression handlers, type parsers, and the intermediate JSON
load/save functions.
"""

import os
import sys
import csv
import json
import hashlib
import logging
import yaml
from datetime import datetime, timezone

# Add project root to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ============================================================================
# CONSTANTS
# ============================================================================

FAIRHAVEN_NCESSCH = "530042000104"

INTERMEDIATE_PATH = os.path.join(config.DATA_DIR, "schools_pipeline.json")

# CRDC race/sex column suffix → (schema_race_key, schema_sex_key)
# Used by 07_load_crdc.py and any step that reads CRDC race breakdowns.
RACE_SUFFIXES = {
    "HI_M": ("hispanic", "male"), "HI_F": ("hispanic", "female"),
    "AM_M": ("american_indian", "male"), "AM_F": ("american_indian", "female"),
    "AS_M": ("asian", "male"), "AS_F": ("asian", "female"),
    "HP_M": ("pacific_islander", "male"), "HP_F": ("pacific_islander", "female"),
    "BL_M": ("black", "male"), "BL_F": ("black", "female"),
    "WH_M": ("white", "male"), "WH_F": ("white", "female"),
    "TR_M": ("two_or_more", "male"), "TR_F": ("two_or_more", "female"),
}


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(script_name):
    """Set up dual logging: console + timestamped log file in logs/."""
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = os.path.join(config.LOGS_DIR, f"{script_name}_{timestamp}.log")

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if called twice
    if logger.handlers:
        return logger

    # Console handler — shows messages in the terminal
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    # File handler — keeps a permanent record
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    logger.addHandler(file_handler)

    logger.info(f"Logging to {log_file}")
    return logger


# ============================================================================
# INTERMEDIATE JSON — the document store that accumulates data across steps
# ============================================================================

def load_schools():
    """Load the intermediate schools JSON. Returns a dict keyed by NCESSCH."""
    if not os.path.exists(INTERMEDIATE_PATH):
        raise FileNotFoundError(
            f"Intermediate file not found at {INTERMEDIATE_PATH}. "
            "This usually means 01_build_spine.py has not been run yet. "
            "Run the pipeline from step 01 first."
        )
    with open(INTERMEDIATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schools(schools):
    """Save the schools dict back to the intermediate JSON file."""
    os.makedirs(os.path.dirname(INTERMEDIATE_PATH), exist_ok=True)
    with open(INTERMEDIATE_PATH, "w", encoding="utf-8") as f:
        json.dump(schools, f, indent=2, ensure_ascii=False)


# ============================================================================
# SUPPRESSION HANDLERS
# ============================================================================

# CRDC suppression codes — each negative number means something different.
# Zero means zero incidents. This is the project's #1 data integrity rule.
CRDC_SUPPRESSION = {
    "-9":  {"not_applicable": True},
    "-5":  {"suppressed": True, "reason": "small_count"},
    "-4":  {"suppressed": True, "reason": "teacher_sex"},
    "-3":  {"suppressed": True, "reason": "secondary"},
    "-2":  {"suppressed": True, "reason": "not_reported"},
    "-12": {"suppressed": True, "reason": "unknown_negative"},
    "-13": {"suppressed": True, "reason": "unknown_negative"},
}


def parse_crdc_value(val):
    """Convert a CRDC cell value, respecting suppression codes.

    Returns (numeric_value_or_None, flag_dict_or_None).
    Zero returns (0, None) — zero is real data, not suppressed.
    Negative suppression codes return (None, {...flag...}).
    """
    if val is None or str(val).strip() == "":
        return (None, None)

    val_str = str(val).strip()

    # RULE: SUPPRESSION_CRDC_NEGATIVE — check for suppression codes
    if val_str in CRDC_SUPPRESSION:
        return (None, CRDC_SUPPRESSION[val_str])

    try:
        f = float(val_str)
        # Preserve zero as zero (genuine zero, not suppressed)
        if f == int(f):
            return (int(f), None)
        return (f, None)
    except (ValueError, TypeError):
        return (None, None)


def parse_ospi_value(val, dat_field=None):
    """Convert an OSPI cell value, respecting suppression markers.

    Returns (numeric_value_or_None, flag_dict_or_None).

    Args:
        val: The cell value (string or number).
        dat_field: The corresponding DAT/DATReason/DATNotes field, if any.
                   Used to detect N<10 and Cross Group suppression.
    """
    if val is None:
        return (None, None)

    val_str = str(val).strip()

    if val_str == "" or val_str.lower() == "none":
        return (None, None)

    # RULE: SUPPRESSION_OSPI_N_LT_10
    if val_str == "N<10" or (dat_field and "N<10" in str(dat_field)):
        return (None, {"suppressed": True, "reason": "n_lt_10"})

    # RULE: SUPPRESSION_OSPI_MASKED — asterisk means masked value
    if val_str == "*":
        return (None, {"suppressed": True, "reason": "masked"})

    # RULE: SUPPRESSION_OSPI_NO_STUDENTS
    if val_str == "No Students":
        return (None, {"no_students": True})

    # RULE: SUPPRESSION_OSPI_CROSS_GROUP
    if dat_field and "Cross Student Group" in str(dat_field):
        return (None, {"suppressed": True, "reason": "cross_group"})

    # RULE: SUPPRESSION_OSPI_TOP_BOTTOM_RANGE — values like "<27.3%" or ">72.7%"
    if val_str.startswith("<") or val_str.startswith(">"):
        return (None, {"suppressed": True, "reason": "top_bottom_range"})

    # Not suppressed — try to parse as number
    cleaned = val_str.replace(",", "").replace("%", "")
    try:
        f = float(cleaned)
        # If original had %, convert to 0.0-1.0 scale
        if "%" in val_str:
            f = f / 100.0
        return (f, None)
    except (ValueError, TypeError):
        return (None, None)


# ============================================================================
# TYPE PARSERS
# ============================================================================

def parse_percentage(val):
    """Parse a percentage string to a 0.0-1.0 decimal.

    '64.90%' → 0.649
    '0.649'  → 0.649 (already a decimal, leave as-is)
    None     → None
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if val_str == "" or val_str.lower() == "none":
        return None

    # If it has a % sign, strip it and divide by 100
    if "%" in val_str:
        try:
            return float(val_str.replace("%", "").replace(",", "")) / 100.0
        except ValueError:
            return None

    # Otherwise try as a raw float (might already be 0.0-1.0)
    try:
        f = float(val_str.replace(",", ""))
        return f
    except ValueError:
        return None


def safe_int(val):
    """Convert to int, stripping commas. Returns None if not possible."""
    if val is None:
        return None
    val_str = str(val).strip().replace(",", "")
    if val_str == "" or val_str.lower() == "none":
        return None
    try:
        return int(float(val_str))
    except (ValueError, TypeError):
        return None


def safe_float(val):
    """Convert to float, stripping commas. Returns None if not possible."""
    if val is None:
        return None
    val_str = str(val).strip().replace(",", "")
    if val_str == "" or val_str.lower() == "none":
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


# ============================================================================
# FILE HASHING
# ============================================================================

def compute_sha256(filepath):
    """Compute SHA256 hash of a file. Returns hex string."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ============================================================================
# CRDC RACE BREAKDOWN BUILDER
# ============================================================================

def crdc_race_object(row, prefix):
    """Build a race/sex breakdown dict from CRDC columns with a given prefix.

    Example: prefix="SCH_DISCWODIS_ISS_" reads columns like
    SCH_DISCWODIS_ISS_HI_M, SCH_DISCWODIS_ISS_HI_F, etc.
    Returns a dict like {"hispanic_male": 5, "hispanic_female": 3, ...}
    or None if all values are suppressed/missing.
    """
    obj = {}
    for suffix, (race, sex) in RACE_SUFFIXES.items():
        col = f"{prefix}{suffix}"
        val, flag = parse_crdc_value(row.get(col, ""))
        key = f"{race}_{sex}"
        if val is not None:
            obj[key] = val
        elif flag is not None:
            # Store None for suppressed, but we don't embed the flag
            # in the race object to keep it compact. The flag is tracked
            # at a higher level (suppression audit).
            pass
    return obj if obj else None


# ============================================================================
# OSPI CROSSWALK LOOKUP BUILDER
# ============================================================================

def build_ospi_lookup(schools):
    """Build a lookup dict from (ospi_district_code, ospi_school_code) → NCESSCH.

    Used by OSPI loading scripts to join OSPI data to the CCD spine.
    """
    lookup = {}
    for ncessch, doc in schools.items():
        meta = doc.get("metadata", {})
        dist = meta.get("ospi_district_code")
        sch = meta.get("ospi_school_code")
        if dist and sch:
            lookup[(str(dist), str(sch))] = ncessch
    return lookup


# ============================================================================
# NESTED FIELD ACCESS — used by percentile and flag scripts to read metrics
# by config-defined dotted paths like "academics.assessment.ela_proficiency_pct"
# ============================================================================

def get_nested(doc, dotted_path):
    """Read a value from a nested dict using a dotted path string.

    get_nested(doc, "academics.assessment.ela_proficiency_pct")
    is equivalent to doc["academics"]["assessment"]["ela_proficiency_pct"]
    but returns None if any key is missing instead of raising KeyError.
    """
    current = doc
    for key in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


# ============================================================================
# FLAG THRESHOLDS CONFIG — loads flag_thresholds.yaml from the project root
# ============================================================================

FLAG_THRESHOLDS_PATH = os.path.join(config.PROJECT_ROOT, "flag_thresholds.yaml")
SCHOOL_EXCLUSIONS_PATH = os.path.join(config.PROJECT_ROOT, "school_exclusions.yaml")


def load_flag_thresholds():
    """Load the flag_thresholds.yaml config file.

    Returns the parsed YAML as a dict. Raises FileNotFoundError with
    a helpful message if the file is missing.
    """
    if not os.path.exists(FLAG_THRESHOLDS_PATH):
        raise FileNotFoundError(
            f"flag_thresholds.yaml not found at {FLAG_THRESHOLDS_PATH}. "
            "This file contains all threshold definitions for Phase 3. "
            "It should be in the project root alongside cleaning_rules.yaml."
        )
    with open(FLAG_THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_school_exclusions():
    """Load the school_exclusions.yaml manual override list.

    Returns a set of NCESSCH IDs that should be excluded from
    the performance regression. Returns an empty set if the file
    doesn't exist (the file is optional — CCD school_type filtering
    catches most cases).
    """
    if not os.path.exists(SCHOOL_EXCLUSIONS_PATH):
        return set()
    with open(SCHOOL_EXCLUSIONS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "excluded_schools" not in data:
        return set()
    return {entry["ncessch"] for entry in data["excluded_schools"]}
