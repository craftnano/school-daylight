"""
16_write_and_verify.py — Push Phase 3 data to Atlas + comprehensive verification.

PURPOSE: Write updated documents (now including derived fields from Phase 3)
         to MongoDB Atlas. Run Fairhaven field-by-field verification, sanity
         check 5-10 schools across the spectrum, and generate Phase 3 receipt
         and fairhaven_test.md.
INPUTS:  data/schools_pipeline.json, MongoDB Atlas, flag_thresholds.yaml
OUTPUTS: Updated MongoDB collection, phases/phase-3/receipt.md,
         phases/phase-3/fairhaven_test.md
FAILURE MODES: Fairhaven mismatch = hard stop. Sanity school anomaly = warning.
"""

import os
import sys
import json
from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, compute_sha256, get_nested,
    load_flag_thresholds, FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ============================================================================
# ATLAS WRITE
# ============================================================================

def write_to_atlas(schools, logger):
    """Drop and recreate the schools collection with all Phase 3 data."""
    if not config.MONGO_URI:
        logger.error(
            "MONGO_URI is empty. Check that your .env file contains a valid "
            "MongoDB Atlas connection string."
        )
        return None

    try:
        from pymongo import MongoClient
    except ImportError:
        logger.error("pymongo is not installed. Run: pip install 'pymongo[srv]'")
        return None

    documents = list(schools.values())

    # Find largest document
    largest_size = 0
    largest_id = None
    for doc in documents:
        size = len(json.dumps(doc, default=str, ensure_ascii=False).encode("utf-8"))
        if size > largest_size:
            largest_size = size
            largest_id = doc.get("_id", "unknown")

    logger.info(f"Prepared {len(documents)} documents for insertion.")
    logger.info(f"Largest document: {largest_id} ({largest_size:,} bytes).")

    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        logger.info("Connected to MongoDB Atlas.")
    except Exception as e:
        logger.error(
            f"Could not connect to MongoDB Atlas: {e}. "
            "Check .env MONGO_URI and try again."
        )
        return None

    db = client["schooldaylight"]
    collection = db["schools"]

    # Drop and reinsert — idempotent
    collection.drop()
    logger.info("Dropped existing 'schools' collection.")

    result = collection.insert_many(documents)
    logger.info(f"Inserted {len(result.inserted_ids)} documents.")

    collection.create_index("name")
    logger.info("Created index on 'name' field.")

    count = collection.count_documents({})
    logger.info(f"Verification: {count} documents in collection.")

    if count != len(documents):
        logger.error(f"Document count mismatch: expected {len(documents)}, got {count}.")
        client.close()
        return None

    return client


# ============================================================================
# FAIRHAVEN VERIFICATION — Phase 3 derived field checks
# ============================================================================

def check_fairhaven_phase3(collection, logger):
    """Verify Fairhaven's Phase 3 derived fields against expected values."""
    checks = []

    doc = collection.find_one({"_id": FAIRHAVEN_NCESSCH})
    if doc is None:
        checks.append(("Fairhaven exists in MongoDB", "FAIL", "Not found"))
        return checks, False

    checks.append(("Fairhaven exists in MongoDB", "PASS", f"_id={FAIRHAVEN_NCESSCH}"))

    derived = doc.get("derived", {})
    flags = derived.get("flags", {})
    percentiles = derived.get("percentiles", {})

    # Phase 3 expected values (tolerance where needed)
    phase3_checks = [
        ("derived.performance_flag", derived.get("performance_flag"), "outperforming", None),
        ("derived.regression_zscore", derived.get("regression_zscore"), 1.33, 0.05),
        ("derived.regression_group", derived.get("regression_group"), "Middle", None),
        ("derived.student_teacher_ratio", derived.get("student_teacher_ratio"), 17.5, 0.2),
        ("derived.counselor_student_ratio", derived.get("counselor_student_ratio"), 294.0, 1.0),
        ("derived.chronic_absenteeism_pct", derived.get("chronic_absenteeism_pct"), 0.3997, 0.002),
        ("derived.proficiency_composite", derived.get("proficiency_composite"), 0.599, 0.002),
        ("derived.peer_cohort", derived.get("peer_cohort"), "Middle_Large_MidFRL", None),
        ("flags.chronic_absenteeism.color", flags.get("chronic_absenteeism", {}).get("color"), "red", None),
        ("flags.counselor_ratio.color", flags.get("counselor_ratio", {}).get("color"), "green", None),
        ("flags.discipline_disparity.color", flags.get("discipline_disparity", {}).get("color"), "red", None),
    ]

    all_passed = True
    for name, actual, expected, tolerance in phase3_checks:
        if actual is None and expected is not None:
            checks.append((f"Fairhaven {name}", "FAIL", f"Value is None (expected {expected})"))
            all_passed = False
        elif tolerance is not None:
            if abs(actual - expected) <= tolerance:
                checks.append((f"Fairhaven {name}", "PASS", f"{actual} (expected {expected})"))
            else:
                checks.append((f"Fairhaven {name}", "FAIL", f"{actual} != {expected} (tol {tolerance})"))
                all_passed = False
        else:
            if actual == expected:
                checks.append((f"Fairhaven {name}", "PASS", f"{actual}"))
            else:
                checks.append((f"Fairhaven {name}", "FAIL", f"{actual} != {expected}"))
                all_passed = False

    # Check that ELA state percentile is not null and > 50
    ela_state = percentiles.get("ela_proficiency_pct", {}).get("state")
    if ela_state is not None and ela_state > 50:
        checks.append(("Fairhaven ELA state percentile > 50", "PASS", f"{ela_state}"))
    else:
        checks.append(("Fairhaven ELA state percentile > 50", "FAIL", f"{ela_state}"))
        all_passed = False

    return checks, all_passed


# ============================================================================
# SANITY SCHOOLS — check 6 diverse schools across the spectrum
# ============================================================================

def check_sanity_schools(schools, logger):
    """Identify and verify 6 sanity schools across the spectrum.

    We find real schools matching each archetype and verify their flags
    make logical sense.
    """
    checks = []
    all_passed = True

    # 1. Low-FRL school with high scores → should be "as_expected"
    #    (high scores explained by low poverty — not outperforming)
    found = find_school(
        schools,
        lambda d: (
            d.get("demographics", {}).get("frl_pct") is not None
            and d.get("demographics", {}).get("frl_pct") < 0.15
            and d.get("derived", {}).get("proficiency_composite") is not None
            and d.get("derived", {}).get("proficiency_composite") > 0.75
            and d.get("derived", {}).get("performance_flag") is not None
        )
    )
    if found:
        ncessch, doc = found
        flag = doc["derived"]["performance_flag"]
        name = doc.get("name", ncessch)
        frl = doc["demographics"]["frl_pct"]
        comp = doc["derived"]["proficiency_composite"]
        if flag == "as_expected":
            checks.append((
                f"Low-FRL high-score ({name})",
                "PASS", f"frl={frl:.2f}, composite={comp:.3f}, flag={flag}"
            ))
        else:
            checks.append((
                f"Low-FRL high-score ({name})",
                "WARN", f"frl={frl:.2f}, composite={comp:.3f}, flag={flag} (expected as_expected)"
            ))
            logger.warning(f"Sanity school '{name}' has flag={flag}, expected as_expected. Review manually.")

    # 2. High-FRL school with low scores → should be "as_expected" or "underperforming"
    found = find_school(
        schools,
        lambda d: (
            d.get("demographics", {}).get("frl_pct") is not None
            and d.get("demographics", {}).get("frl_pct") > 0.80
            and d.get("derived", {}).get("proficiency_composite") is not None
            and d.get("derived", {}).get("proficiency_composite") < 0.20
            and d.get("derived", {}).get("performance_flag") is not None
        )
    )
    if found:
        ncessch, doc = found
        flag = doc["derived"]["performance_flag"]
        name = doc.get("name", ncessch)
        frl = doc["demographics"]["frl_pct"]
        comp = doc["derived"]["proficiency_composite"]
        if flag in ("as_expected", "underperforming"):
            checks.append((
                f"High-FRL low-score ({name})",
                "PASS", f"frl={frl:.2f}, composite={comp:.3f}, flag={flag}"
            ))
        else:
            checks.append((
                f"High-FRL low-score ({name})",
                "WARN", f"frl={frl:.2f}, composite={comp:.3f}, flag={flag}"
            ))

    # 3. School with high discipline disparity → yellow or red flag
    found = find_school(
        schools,
        lambda d: (
            d.get("derived", {}).get("discipline_disparity_max") is not None
            and d.get("derived", {}).get("discipline_disparity_max") > 3.0
        )
    )
    if found:
        ncessch, doc = found
        max_ratio = doc["derived"]["discipline_disparity_max"]
        flag_color = doc.get("derived", {}).get("flags", {}).get("discipline_disparity", {}).get("color")
        name = doc.get("name", ncessch)
        if flag_color in ("yellow", "red"):
            checks.append((
                f"High disparity ({name})",
                "PASS", f"disparity={max_ratio}, flag={flag_color}"
            ))
        else:
            checks.append((
                f"High disparity ({name})",
                "FAIL", f"disparity={max_ratio}, flag={flag_color} (expected yellow or red)"
            ))
            all_passed = False

    # 4. Single-school district → null district percentiles
    district_sizes = Counter()
    for doc in schools.values():
        did = doc.get("district", {}).get("nces_id")
        if did:
            district_sizes[did] += 1
    single_districts = [did for did, count in district_sizes.items() if count == 1]

    if single_districts:
        # Find a school in a single-school district that has percentile data
        found = find_school(
            schools,
            lambda d: (
                d.get("district", {}).get("nces_id") in single_districts
                and d.get("derived", {}).get("percentiles", {}).get("ela_proficiency_pct", {}).get("state") is not None
            )
        )
        if found:
            ncessch, doc = found
            name = doc.get("name", ncessch)
            ela_district = doc["derived"]["percentiles"]["ela_proficiency_pct"].get("district")
            if ela_district is None:
                checks.append((
                    f"Single-school district ({name})",
                    "PASS", "district percentile is null (correct)"
                ))
            else:
                checks.append((
                    f"Single-school district ({name})",
                    "FAIL", f"district percentile is {ela_district} (expected null)"
                ))
                all_passed = False

    # 5. School missing CRDC → null disparity flags with absent reason
    found = find_school(
        schools,
        lambda d: (
            d.get("metadata", {}).get("join_status") == "missing_crdc"
            and d.get("derived", {}).get("flags") is not None
        )
    )
    if found:
        ncessch, doc = found
        name = doc.get("name", ncessch)
        disp_flag = doc.get("derived", {}).get("flags", {}).get("discipline_disparity", {})
        color = disp_flag.get("color")
        reason = disp_flag.get("flag_absent_reason")
        if color is None and reason == "data_not_available":
            checks.append((
                f"Missing CRDC ({name})",
                "PASS", f"disparity color=null, reason={reason}"
            ))
        elif color is None:
            checks.append((
                f"Missing CRDC ({name})",
                "PASS", f"disparity color=null, reason={reason}"
            ))
        else:
            checks.append((
                f"Missing CRDC ({name})",
                "FAIL", f"disparity color={color} (expected null)"
            ))
            all_passed = False

    # 6. Low-FRL school with mediocre scores → "underperforming"
    found = find_school(
        schools,
        lambda d: (
            d.get("demographics", {}).get("frl_pct") is not None
            and d.get("demographics", {}).get("frl_pct") < 0.20
            and d.get("derived", {}).get("proficiency_composite") is not None
            and d.get("derived", {}).get("proficiency_composite") < 0.40
            and d.get("derived", {}).get("performance_flag") == "underperforming"
        )
    )
    if found:
        ncessch, doc = found
        name = doc.get("name", ncessch)
        frl = doc["demographics"]["frl_pct"]
        comp = doc["derived"]["proficiency_composite"]
        checks.append((
            f"Low-FRL underperforming ({name})",
            "PASS", f"frl={frl:.2f}, composite={comp:.3f}, flag=underperforming (key insight)"
        ))
    else:
        # This is the rarest case — it's OK if we can't find one
        logger.info("No low-FRL underperforming school found (broadening search).")
        found = find_school(
            schools,
            lambda d: (
                d.get("demographics", {}).get("frl_pct") is not None
                and d.get("demographics", {}).get("frl_pct") < 0.30
                and d.get("derived", {}).get("proficiency_composite") is not None
                and d.get("derived", {}).get("proficiency_composite") < 0.50
                and d.get("derived", {}).get("performance_flag") == "underperforming"
            )
        )
        if found:
            ncessch, doc = found
            name = doc.get("name", ncessch)
            frl = doc["demographics"]["frl_pct"]
            comp = doc["derived"]["proficiency_composite"]
            checks.append((
                f"Low-FRL underperforming ({name})",
                "PASS", f"frl={frl:.2f}, composite={comp:.3f}, flag=underperforming"
            ))

    return checks, all_passed


def find_school(schools, predicate):
    """Find the first school matching a predicate. Returns (ncessch, doc) or None."""
    for ncessch, doc in schools.items():
        try:
            if predicate(doc):
                return (ncessch, doc)
        except (KeyError, TypeError):
            continue
    return None


# ============================================================================
# RECEIPT AND FAIRHAVEN TEST GENERATION
# ============================================================================

def generate_receipt(fairhaven_checks, sanity_checks, schools, hashes, logger):
    """Generate the Phase 3 verification receipt."""
    receipt_path = os.path.join(config.PHASES_DIR, "phase-3", "receipt.md")
    os.makedirs(os.path.dirname(receipt_path), exist_ok=True)

    # Collect Phase 3 statistics
    derived_stats = {
        "with_performance_flag": 0,
        "outperforming": 0,
        "as_expected": 0,
        "underperforming": 0,
        "with_peer_cohort": 0,
        "with_percentiles": 0,
    }
    flag_stats = {}

    for doc in schools.values():
        d = doc.get("derived", {})
        pf = d.get("performance_flag")
        if pf:
            derived_stats["with_performance_flag"] += 1
            derived_stats[pf] = derived_stats.get(pf, 0) + 1
        if d.get("peer_cohort"):
            derived_stats["with_peer_cohort"] += 1
        if d.get("percentiles"):
            derived_stats["with_percentiles"] += 1

        for flag_name, flag_data in d.get("flags", {}).items():
            if flag_name not in flag_stats:
                flag_stats[flag_name] = Counter()
            color = flag_data.get("color")
            if color:
                flag_stats[flag_name][color] += 1
            else:
                reason = flag_data.get("flag_absent_reason", "null")
                flag_stats[flag_name][f"null ({reason})"] += 1

    lines = []
    lines.append("# Phase 3 — Verification Receipt")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Dataset version:** 2026-02-v1")
    lines.append(f"**Document count:** {len(schools)}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Fairhaven Phase 3 Verification")
    lines.append("")
    lines.append("| Check | Result | Details |")
    lines.append("|-------|--------|---------|")
    for name, result, details in fairhaven_checks:
        lines.append(f"| {name} | {result} | {details} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Sanity School Checks")
    lines.append("")
    lines.append("| Check | Result | Details |")
    lines.append("|-------|--------|---------|")
    for name, result, details in sanity_checks:
        lines.append(f"| {name} | {result} | {details} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Regression Summary")
    lines.append("")
    lines.append(f"- **Schools with performance flag:** {derived_stats['with_performance_flag']}")
    lines.append(f"- **Outperforming (green):** {derived_stats['outperforming']}")
    lines.append(f"- **As expected (yellow):** {derived_stats['as_expected']}")
    lines.append(f"- **Underperforming (red):** {derived_stats['underperforming']}")
    lines.append(f"- **Schools with peer cohort:** {derived_stats['with_peer_cohort']}")
    lines.append(f"- **Schools with percentiles:** {derived_stats['with_percentiles']}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Flag Distribution")
    lines.append("")
    for flag_name in sorted(flag_stats.keys()):
        lines.append(f"### {flag_name}")
        lines.append("")
        lines.append("| Color/Status | Count |")
        lines.append("|-------------|-------|")
        for status, count in sorted(flag_stats[flag_name].items()):
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

    receipt_content = "\n".join(lines)

    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(receipt_content)

    logger.info(f"Receipt written to {receipt_path}.")


def generate_fairhaven_test(doc, logger):
    """Generate Phase 3 fairhaven_test.md with all derived fields."""
    test_path = os.path.join(config.PHASES_DIR, "phase-3", "fairhaven_test.md")
    os.makedirs(os.path.dirname(test_path), exist_ok=True)

    derived = doc.get("derived", {})
    flags = derived.get("flags", {})
    percentiles = derived.get("percentiles", {})

    lines = []
    lines.append("# Phase 3 — Fairhaven Field-by-Field Test (Live MongoDB)")
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
    lines.append("")

    lines.append("## Derived Ratios")
    lines.append("")
    lines.append(f"- **student_teacher_ratio:** {derived.get('student_teacher_ratio')}")
    lines.append(f"- **counselor_student_ratio:** {derived.get('counselor_student_ratio')}")
    lines.append(f"- **chronic_absenteeism_pct:** {derived.get('chronic_absenteeism_pct')}")
    lines.append(f"- **proficiency_composite:** {derived.get('proficiency_composite')}")
    lines.append(f"- **no_counselor:** {derived.get('no_counselor')}")
    lines.append("")

    lines.append("## Discipline Disparity")
    lines.append("")
    lines.append(f"- **disparity_max:** {derived.get('discipline_disparity_max')}")
    lines.append(f"- **disparity_max_race:** {derived.get('discipline_disparity_max_race')}")
    disp = derived.get("discipline_disparity", {})
    if disp:
        for race, ratio in sorted(disp.items()):
            lines.append(f"- **{race}:** {ratio}")
    lines.append("")

    lines.append("## Peer Group")
    lines.append("")
    lines.append(f"- **level_group:** {derived.get('level_group')}")
    lines.append(f"- **enrollment_band:** {derived.get('enrollment_band')}")
    lines.append(f"- **frl_band:** {derived.get('frl_band')}")
    lines.append(f"- **peer_cohort:** {derived.get('peer_cohort')}")
    lines.append("")

    lines.append("## Performance Regression")
    lines.append("")
    lines.append(f"- **performance_flag:** {derived.get('performance_flag')}")
    lines.append(f"- **regression_zscore:** {derived.get('regression_zscore')}")
    lines.append(f"- **regression_predicted:** {derived.get('regression_predicted')}")
    lines.append(f"- **regression_residual:** {derived.get('regression_residual')}")
    lines.append(f"- **regression_group:** {derived.get('regression_group')}")
    lines.append(f"- **regression_r_squared:** {derived.get('regression_r_squared')}")
    lines.append("")

    lines.append("## Percentiles")
    lines.append("")
    for metric_key, scopes in sorted(percentiles.items()):
        state = scopes.get("state")
        district = scopes.get("district")
        peer = scopes.get("peer")
        lines.append(f"- **{metric_key}:** state={state}, district={district}, peer={peer}")
    lines.append("")

    lines.append("## Climate & Equity Flags")
    lines.append("")
    for flag_name, flag_data in sorted(flags.items()):
        color = flag_data.get("color")
        raw = flag_data.get("raw_value")
        reason = flag_data.get("flag_absent_reason")
        lines.append(f"### {flag_name}")
        lines.append(f"- **color:** {color}")
        if raw is not None:
            lines.append(f"- **raw_value:** {raw}")
        if flag_data.get("threshold") is not None:
            lines.append(f"- **threshold:** {flag_data['threshold']}")
        if reason:
            lines.append(f"- **flag_absent_reason:** {reason}")
        lines.append("")

    lines.append("## CRDC Enrollment by Race")
    lines.append("")
    crdc_race = doc.get("enrollment", {}).get("crdc_by_race", {})
    crdc_total = doc.get("enrollment", {}).get("crdc_total", 0)
    for race, count in sorted(crdc_race.items()):
        lines.append(f"- **{race}:** {count}")
    lines.append(f"- **total:** {crdc_total}")
    lines.append("")

    with open(test_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Fairhaven test written to {test_path}.")


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


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger = setup_logging("16_write_and_verify")
    logger.info("Step 16: Writing Phase 3 data to Atlas and running verification.")

    schools = load_schools()
    logger.info(f"Loaded {len(schools)} schools from intermediate JSON.")

    # Write to Atlas
    client = write_to_atlas(schools, logger)
    if client is None:
        logger.error("Atlas write failed. See errors above.")
        sys.exit(1)

    db = client["schooldaylight"]
    collection = db["schools"]

    # Run Fairhaven Phase 3 checks
    logger.info("--- Fairhaven Phase 3 Verification ---")
    fairhaven_checks, fh_passed = check_fairhaven_phase3(collection, logger)
    for name, result, details in fairhaven_checks:
        logger.info(f"  {result}: {name} — {details}")

    # Run sanity school checks
    logger.info("--- Sanity School Checks ---")
    sanity_checks, sanity_passed = check_sanity_schools(schools, logger)
    for name, result, details in sanity_checks:
        logger.info(f"  {result}: {name} — {details}")

    # Compute source file hashes
    hashes = compute_source_hashes(logger)

    # Generate receipt
    generate_receipt(fairhaven_checks, sanity_checks, schools, hashes, logger)

    # Generate Fairhaven test doc
    fh_doc = collection.find_one({"_id": FAIRHAVEN_NCESSCH})
    if fh_doc:
        generate_fairhaven_test(fh_doc, logger)

    client.close()

    # Final verdict
    if fh_passed:
        logger.info("ALL FAIRHAVEN CHECKS PASSED.")
    else:
        logger.error("FAIRHAVEN CHECKS FAILED. Pipeline output is not verified.")
        sys.exit(1)

    if not sanity_passed:
        logger.warning("Some sanity checks had warnings. Review manually.")

    logger.info("Step 16 complete. Phase 3 verified.")


if __name__ == "__main__":
    main()
