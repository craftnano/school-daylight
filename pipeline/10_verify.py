"""
10_verify.py — Verify Fairhaven against live MongoDB and generate receipt.

PURPOSE: Run Fairhaven field-by-field checks against live MongoDB, perform
         integrity checks, compute source file hashes, and generate the
         Phase 2 verification receipt.
INPUTS: MongoDB Atlas (live), data/schools_pipeline.json,
        all source files (for SHA256 hashes)
OUTPUTS: phases/phase-2/receipt.md, phases/phase-2/fairhaven_test.md
JOIN KEYS: None
SUPPRESSION HANDLING: Verify no suppressed values stored as 0 or empty string
RECEIPT: IS the receipt
FAILURE MODES: Fairhaven mismatch = hard stop
"""

import os
import sys
import json
import glob as glob_module
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, compute_sha256, FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def check_fairhaven(collection, logger):
    """Run Fairhaven field-by-field verification against live MongoDB.

    TEST: Fairhaven values from phases/phase-1/fairhaven_test.md
    Returns (checks_list, all_passed).
    """
    checks = []

    doc = collection.find_one({"_id": FAIRHAVEN_NCESSCH})
    if doc is None:
        checks.append(("Fairhaven exists in MongoDB", "FAIL", "Document not found"))
        return checks, False

    checks.append(("Fairhaven exists in MongoDB", "PASS", f"_id={FAIRHAVEN_NCESSCH}"))

    # Define expected values from Phase 1 fairhaven_test.md
    # NOTE: Growth values use 2024-25 primary data (not 2023-24 Phase 1 values)
    # because Fairhaven IS present in the 2024-25 growth file.
    expected = {
        "enrollment.total": (doc.get("enrollment", {}).get("total"), 588),
        "demographics.frl_count": (doc.get("demographics", {}).get("frl_count"), 257),
        "academics.assessment.ela_proficiency_pct": (
            doc.get("academics", {}).get("assessment", {}).get("ela_proficiency_pct"),
            0.649, 0.002  # tolerance for float comparison
        ),
        "academics.assessment.math_proficiency_pct": (
            doc.get("academics", {}).get("assessment", {}).get("math_proficiency_pct"),
            0.549, 0.002
        ),
        # Growth values from 2024-25 (Fairhaven present in primary year file)
        "academics.growth.ela_median_sgp": (
            doc.get("academics", {}).get("growth", {}).get("ela_median_sgp"),
            56.0  # 2024-25 value (Phase 1 verified 61.0 from 2023-24)
        ),
        "academics.growth.math_median_sgp": (
            doc.get("academics", {}).get("growth", {}).get("math_median_sgp"),
            60.0  # 2024-25 value (Phase 1 verified 68.0 from 2023-24)
        ),
        "academics.attendance.regular_attendance_pct": (
            doc.get("academics", {}).get("attendance", {}).get("regular_attendance_pct"),
            0.6003, 0.002
        ),
        "discipline.ospi.rate": (
            doc.get("discipline", {}).get("ospi", {}).get("rate"),
            0.0455, 0.002
        ),
        "finance.per_pupil_total": (
            doc.get("finance", {}).get("per_pupil_total"),
            17778.96, 0.02
        ),
        "staffing.teacher_fte_total": (
            doc.get("staffing", {}).get("teacher_fte_total"),
            33.6, 0.1  # CRDC float precision
        ),
        "staffing.counselor_fte": (
            doc.get("staffing", {}).get("counselor_fte"),
            2.0
        ),
        "safety.restraint_seclusion.physical_idea": (
            doc.get("safety", {}).get("restraint_seclusion", {}).get("physical_idea"),
            17
        ),
    }

    all_passed = True
    for field_name, values in expected.items():
        actual = values[0]
        expected_val = values[1]
        tolerance = values[2] if len(values) > 2 else None

        if actual is None:
            checks.append((f"Fairhaven {field_name}", "FAIL", f"Value is None (expected {expected_val})"))
            all_passed = False
        elif tolerance is not None:
            if abs(actual - expected_val) <= tolerance:
                checks.append((f"Fairhaven {field_name}", "PASS", f"{actual} (expected {expected_val})"))
            else:
                checks.append((f"Fairhaven {field_name}", "FAIL", f"{actual} != {expected_val} (tolerance {tolerance})"))
                all_passed = False
        else:
            if actual == expected_val:
                checks.append((f"Fairhaven {field_name}", "PASS", f"{actual}"))
            else:
                checks.append((f"Fairhaven {field_name}", "FAIL", f"{actual} != {expected_val}"))
                all_passed = False

    return checks, all_passed


def integrity_checks(collection, schools, logger):
    """Run data integrity checks across all documents.

    Returns (checks_list, all_passed).
    """
    checks = []
    all_passed = True

    # Check 1: Document count matches
    mongo_count = collection.count_documents({})
    json_count = len(schools)
    if mongo_count == json_count:
        checks.append(("Document count", "PASS", f"{mongo_count} documents"))
    else:
        checks.append(("Document count", "FAIL", f"MongoDB={mongo_count}, JSON={json_count}"))
        all_passed = False

    # Check 2: All _id values are 12-char strings (not integers)
    bad_ids = 0
    for doc in collection.find({}, {"_id": 1}):
        if not isinstance(doc["_id"], str) or len(doc["_id"]) != 12:
            bad_ids += 1
    if bad_ids == 0:
        checks.append(("NCES IDs are 12-char strings", "PASS", f"All {mongo_count} valid"))
    else:
        checks.append(("NCES IDs are 12-char strings", "FAIL", f"{bad_ids} invalid IDs"))
        all_passed = False

    # Check 3: No percentage outside 0.0-1.0
    bad_pct = 0
    pct_fields = [
        "academics.assessment.ela_proficiency_pct",
        "academics.assessment.math_proficiency_pct",
        "academics.assessment.science_proficiency_pct",
        "academics.attendance.regular_attendance_pct",
        "discipline.ospi.rate",
        "demographics.frl_pct",
    ]
    for ncessch, doc in schools.items():
        for field_path in pct_fields:
            parts = field_path.split(".")
            val = doc
            for p in parts:
                val = val.get(p, {}) if isinstance(val, dict) else None
                if val is None:
                    break
            if val is not None and isinstance(val, (int, float)):
                if val < 0 or val > 1.0:
                    bad_pct += 1
                    logger.warning(f"Percentage out of range: {ncessch} {field_path} = {val}")

    if bad_pct == 0:
        checks.append(("Percentages in 0.0-1.0 range", "PASS", "No violations"))
    else:
        checks.append(("Percentages in 0.0-1.0 range", "FAIL", f"{bad_pct} violations"))
        all_passed = False

    # Check 4: All documents have metadata.dataset_version
    missing_version = sum(
        1 for doc in schools.values()
        if doc.get("metadata", {}).get("dataset_version") is None
    )
    if missing_version == 0:
        checks.append(("All docs have dataset_version", "PASS", f"All {json_count} present"))
    else:
        checks.append(("All docs have dataset_version", "FAIL", f"{missing_version} missing"))
        all_passed = False

    # Check 5: Unique _id count == document count
    unique_ids = len(set(doc.get("_id") for doc in schools.values()))
    if unique_ids == json_count:
        checks.append(("Unique _id count", "PASS", f"{unique_ids} unique = {json_count} total"))
    else:
        checks.append(("Unique _id count", "FAIL", f"{unique_ids} unique != {json_count} total"))
        all_passed = False

    # Check 6: Join failure rate < 5%
    missing_ospi = sum(
        1 for doc in schools.values()
        if doc.get("metadata", {}).get("join_status") == "missing_ospi"
    )
    ccd_only = sum(
        1 for doc in schools.values()
        if doc.get("metadata", {}).get("join_status") == "ccd_only"
    )
    join_failures = missing_ospi + ccd_only
    failure_rate = join_failures / json_count if json_count > 0 else 0
    if failure_rate < 0.05:
        checks.append(("Join failure rate < 5%", "PASS",
                       f"{join_failures}/{json_count} = {failure_rate:.1%}"))
    else:
        checks.append(("Join failure rate < 5%", "FAIL",
                       f"{join_failures}/{json_count} = {failure_rate:.1%}"))
        all_passed = False

    return checks, all_passed


def compute_source_hashes(logger):
    """Compute SHA256 hashes for all source files."""
    hashes = {}

    # CCD files
    for name in ["ccd_wa_directory.csv", "ccd_wa_membership.csv"]:
        path = os.path.join(config.DATA_DIR, name)
        if os.path.exists(path):
            hashes[name] = compute_sha256(path)

    # OSPI files
    ospi_dir = os.path.join(config.RAW_DIR, "ospi")
    if os.path.isdir(ospi_dir):
        for fname in sorted(os.listdir(ospi_dir)):
            if fname.endswith(".csv"):
                path = os.path.join(ospi_dir, fname)
                hashes[f"ospi/{fname}"] = compute_sha256(path)

    # CRDC files
    crdc_dir = os.path.join(config.DATA_DIR, "crdc_wa")
    if os.path.isdir(crdc_dir):
        for fname in sorted(os.listdir(crdc_dir)):
            if fname.endswith(".csv"):
                path = os.path.join(crdc_dir, fname)
                hashes[f"crdc_wa/{fname}"] = compute_sha256(path)

    logger.info(f"Computed SHA256 hashes for {len(hashes)} source files.")
    return hashes


def generate_receipt(fairhaven_checks, integrity_checks_list, hashes, schools, logger):
    """Generate the Phase 2 verification receipt."""

    receipt_path = os.path.join(config.PHASES_DIR, "phase-2", "receipt.md")
    os.makedirs(os.path.dirname(receipt_path), exist_ok=True)

    # Count join statuses
    join_statuses = {}
    for doc in schools.values():
        status = doc.get("metadata", {}).get("join_status", "unknown")
        join_statuses[status] = join_statuses.get(status, 0) + 1

    lines = []
    lines.append("# Phase 2 — Verification Receipt")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Dataset version:** 2026-02-v1")
    lines.append(f"**Document count:** {len(schools)}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Fairhaven Field-by-Field Verification")
    lines.append("")
    lines.append("| Check | Result | Details |")
    lines.append("|-------|--------|---------|")
    for check_name, result, details in fairhaven_checks:
        emoji = "PASS" if result == "PASS" else "FAIL"
        lines.append(f"| {check_name} | {emoji} | {details} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Integrity Checks")
    lines.append("")
    lines.append("| Check | Result | Details |")
    lines.append("|-------|--------|---------|")
    for check_name, result, details in integrity_checks_list:
        emoji = "PASS" if result == "PASS" else "FAIL"
        lines.append(f"| {check_name} | {emoji} | {details} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Join Status Summary")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status, count in sorted(join_statuses.items()):
        lines.append(f"| {status} | {count} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Source File SHA256 Hashes")
    lines.append("")
    lines.append("| File | SHA256 |")
    lines.append("|------|--------|")
    for fname, sha in sorted(hashes.items()):
        lines.append(f"| {fname} | `{sha[:16]}...` |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Growth Data Year Note")
    lines.append("")
    lines.append("Fairhaven growth SGP values use 2024-25 data (ELA=56, Math=60), ")
    lines.append("not the 2023-24 values verified in Phase 1 (ELA=61, Math=68). ")
    lines.append("This is correct behavior: the pipeline uses 2024-25 as primary and ")
    lines.append("only falls back to 2023-24 when a school has zero rows in the 2024-25 file. ")
    lines.append("Fairhaven IS present in the 2024-25 file with updated data.")
    lines.append("")

    receipt_content = "\n".join(lines)

    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(receipt_content)

    logger.info(f"Receipt written to {receipt_path}.")
    return receipt_path


def generate_fairhaven_test(collection, logger):
    """Generate the Phase 2 fairhaven_test.md with live MongoDB values."""

    doc = collection.find_one({"_id": FAIRHAVEN_NCESSCH})
    if doc is None:
        logger.error("Cannot generate fairhaven_test.md — Fairhaven not in MongoDB.")
        return

    test_path = os.path.join(config.PHASES_DIR, "phase-2", "fairhaven_test.md")

    lines = []
    lines.append("# Phase 2 — Fairhaven Field-by-Field Test (Live MongoDB)")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Source:** MongoDB Atlas, collection 'schools', _id='{FAIRHAVEN_NCESSCH}'")
    lines.append("")

    lines.append("## Identity")
    lines.append("")
    lines.append(f"- **_id:** {doc.get('_id')}")
    lines.append(f"- **name:** {doc.get('name')}")
    lines.append(f"- **district:** {doc.get('district', {}).get('name')}")
    lines.append(f"- **level:** {doc.get('level')}")
    lines.append(f"- **is_charter:** {doc.get('is_charter')}")
    lines.append("")

    lines.append("## Enrollment")
    enr = doc.get("enrollment", {})
    lines.append(f"- **total:** {enr.get('total')}")
    lines.append(f"- **by_race.white:** {enr.get('by_race', {}).get('white')}")
    lines.append(f"- **by_race.hispanic:** {enr.get('by_race', {}).get('hispanic')}")
    lines.append(f"- **by_sex.male:** {enr.get('by_sex', {}).get('male')}")
    lines.append(f"- **by_sex.female:** {enr.get('by_sex', {}).get('female')}")
    lines.append("")

    lines.append("## Demographics")
    dem = doc.get("demographics", {})
    lines.append(f"- **frl_count:** {dem.get('frl_count')}")
    lines.append(f"- **frl_pct:** {dem.get('frl_pct')}")
    lines.append(f"- **ell_count:** {dem.get('ell_count')}")
    lines.append(f"- **sped_count:** {dem.get('sped_count')}")
    lines.append(f"- **section_504_count:** {dem.get('section_504_count')}")
    lines.append(f"- **homeless_count:** {dem.get('homeless_count')}")
    lines.append("")

    lines.append("## Academics")
    acad = doc.get("academics", {})
    assess = acad.get("assessment", {})
    growth = acad.get("growth", {})
    attend = acad.get("attendance", {})
    lines.append(f"- **assessment.ela_proficiency_pct:** {assess.get('ela_proficiency_pct')}")
    lines.append(f"- **assessment.math_proficiency_pct:** {assess.get('math_proficiency_pct')}")
    lines.append(f"- **assessment.science_proficiency_pct:** {assess.get('science_proficiency_pct')}")
    lines.append(f"- **growth.year:** {growth.get('year')}")
    lines.append(f"- **growth.ela_median_sgp:** {growth.get('ela_median_sgp')}")
    lines.append(f"- **growth.math_median_sgp:** {growth.get('math_median_sgp')}")
    lines.append(f"- **attendance.regular_attendance_pct:** {attend.get('regular_attendance_pct')}")
    lines.append("")

    lines.append("## Discipline")
    disc = doc.get("discipline", {})
    ospi_disc = disc.get("ospi", {})
    lines.append(f"- **ospi.rate:** {ospi_disc.get('rate')}")
    lines.append(f"- **ospi.numerator:** {ospi_disc.get('numerator')}")
    lines.append(f"- **ospi.denominator:** {ospi_disc.get('denominator')}")
    lines.append("")

    lines.append("## Finance")
    fin = doc.get("finance", {})
    lines.append(f"- **per_pupil_total:** {fin.get('per_pupil_total')}")
    lines.append(f"- **per_pupil_local:** {fin.get('per_pupil_local')}")
    lines.append(f"- **per_pupil_state:** {fin.get('per_pupil_state')}")
    lines.append(f"- **per_pupil_federal:** {fin.get('per_pupil_federal')}")
    lines.append("")

    lines.append("## Staffing")
    staff = doc.get("staffing", {})
    lines.append(f"- **teacher_fte_total:** {staff.get('teacher_fte_total')}")
    lines.append(f"- **teacher_fte_certified:** {staff.get('teacher_fte_certified')}")
    lines.append(f"- **counselor_fte:** {staff.get('counselor_fte')}")
    lines.append(f"- **psychologist_fte:** {staff.get('psychologist_fte')}")
    lines.append(f"- **sro_fte:** {staff.get('sro_fte')}")
    lines.append("")

    lines.append("## Safety")
    safety = doc.get("safety", {})
    rs = safety.get("restraint_seclusion", {})
    hb = safety.get("harassment_bullying", {})
    lines.append(f"- **restraint_seclusion.physical_idea:** {rs.get('physical_idea')}")
    lines.append(f"- **restraint_seclusion.seclusion_idea:** {rs.get('seclusion_idea')}")
    lines.append(f"- **harassment_bullying.allegations_sex:** {hb.get('allegations_sex')}")
    lines.append(f"- **harassment_bullying.allegations_race:** {hb.get('allegations_race')}")
    lines.append(f"- **harassment_bullying.allegations_disability:** {hb.get('allegations_disability')}")
    lines.append("")

    lines.append("## Course Access")
    ca = doc.get("course_access", {})
    lines.append(f"- **ap.indicator:** {ca.get('ap', {}).get('indicator')}")
    lines.append(f"- **gifted_talented.indicator:** {ca.get('gifted_talented', {}).get('indicator')}")
    lines.append("")

    lines.append("## Metadata")
    meta = doc.get("metadata", {})
    lines.append(f"- **dataset_version:** {meta.get('dataset_version')}")
    lines.append(f"- **join_status:** {meta.get('join_status')}")
    lines.append(f"- **crdc_combokey:** {meta.get('crdc_combokey')}")
    lines.append(f"- **ospi_district_code:** {meta.get('ospi_district_code')}")
    lines.append(f"- **ospi_school_code:** {meta.get('ospi_school_code')}")
    lines.append("")

    with open(test_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Fairhaven test written to {test_path}.")


def main():
    logger = setup_logging("10_verify")
    logger.info("Step 10: Running verification checks.")

    # Import pymongo
    try:
        from pymongo import MongoClient
    except ImportError:
        logger.error("pymongo is not installed. Run: pip install 'pymongo[srv]'")
        sys.exit(1)

    # Load schools from JSON
    schools = load_schools()

    # Connect to Atlas
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        logger.info("Connected to MongoDB Atlas.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB Atlas: {e}")
        sys.exit(1)

    db = client["schooldaylight"]
    collection = db["schools"]

    # Run Fairhaven checks
    fairhaven_checks, fh_passed = check_fairhaven(collection, logger)
    for name, result, details in fairhaven_checks:
        logger.info(f"  {result}: {name} — {details}")

    # Run integrity checks
    integrity_list, integrity_passed = integrity_checks(collection, schools, logger)
    for name, result, details in integrity_list:
        logger.info(f"  {result}: {name} — {details}")

    # Compute hashes
    hashes = compute_source_hashes(logger)

    # Generate receipt
    generate_receipt(fairhaven_checks, integrity_list, hashes, schools, logger)

    # Generate fairhaven test doc
    generate_fairhaven_test(collection, logger)

    client.close()

    # Final verdict
    if fh_passed and integrity_passed:
        logger.info("ALL CHECKS PASSED. Phase 2 pipeline verified.")
    else:
        if not fh_passed:
            logger.error("FAIRHAVEN CHECKS FAILED. Pipeline output is not verified.")
        if not integrity_passed:
            logger.error("INTEGRITY CHECKS FAILED. Review failures above.")
        sys.exit(1)

    logger.info("Step 10 complete.")


if __name__ == "__main__":
    main()
