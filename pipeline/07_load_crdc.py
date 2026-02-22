"""
07_load_crdc.py — Load all 13 CRDC files into the intermediate JSON.

PURPOSE: Add CRDC data covering discipline by race/sex/disability, safety
         incidents, staffing levels, and course access (AP, dual enrollment,
         gifted). This is the largest pipeline step — it reads 13 files and
         populates four top-level sections.
INPUTS: data/crdc_wa/*.csv (13 files), data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with discipline.crdc, safety, staffing,
         course_access sections
JOIN KEYS: COMBOKEY (12-char) → _id (NCESSCH, direct 12-char match)
SUPPRESSION HANDLING: -9 → not_applicable. -5 → suppressed (small_count).
                      -4 → suppressed (teacher_sex). -3 → suppressed (secondary).
                      -2 → suppressed (not_reported).
                      -12/-13 → suppressed (unknown_negative) — LOG ALL INSTANCES.
                      0 → 0 (genuine zero — real data, not suppressed).
RECEIPT: phases/phase-2/receipt.md — CRDC section
FAILURE MODES: ~128 schools in spine won't have CRDC data (opened after 2021-22).
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    parse_crdc_value, crdc_race_object, safe_float,
    FAIRHAVEN_NCESSCH, RACE_SUFFIXES
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

CRDC_DIR = os.path.join(config.DATA_DIR, "crdc_wa")


def read_crdc_file(filename, logger):
    """Read a CRDC CSV and return rows as a dict keyed by COMBOKEY.

    Returns {combokey: row_dict} for schools in the spine.
    """
    filepath = os.path.join(CRDC_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"CRDC file not found: {filepath}")
        return {}

    rows = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            combo = (row.get("COMBOKEY") or "").strip()
            if combo:
                rows[combo] = row
    return rows


def log_unknown_markers(marker_log, schools, logger):
    """Write all -12/-13 instances to a CSV file for manual review.

    RULE: Per Phase 1 exit, every instance of -12 or -13 must be logged.
    """
    if not marker_log:
        logger.info("No -12/-13 instances found.")
        return

    log_path = os.path.join(config.LOGS_DIR, "crdc_unknown_markers.csv")
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    with open(log_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ncessch", "school_name", "file", "column", "value"])
        for entry in marker_log:
            school_name = schools.get(entry["ncessch"], {}).get("name", "Unknown")
            writer.writerow([
                entry["ncessch"], school_name,
                entry["file"], entry["column"], entry["value"]
            ])

    logger.info(
        f"Logged {len(marker_log)} instances of -12/-13 to {log_path}. "
        "These are undocumented CRDC codes treated as suppressed."
    )


def process_suspensions(schools, logger, marker_log):
    """Process suspensions.csv → discipline.crdc section."""
    rows = read_crdc_file("suspensions.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        # Track -12/-13 instances
        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "suspensions.csv",
                    "column": col, "value": str(val).strip()
                })

        if "discipline" not in schools[ncessch]:
            schools[ncessch]["discipline"] = {}
        if "crdc" not in schools[ncessch]["discipline"]:
            schools[ncessch]["discipline"]["crdc"] = {"year": "2021-22"}

        crdc = schools[ncessch]["discipline"]["crdc"]

        # LINEAGE: SCH_DISCWODIS_ISS_{race}_{sex} → discipline.crdc.iss
        crdc["iss"] = crdc_race_object(row, "SCH_DISCWODIS_ISS_")
        crdc["iss_idea"] = crdc_race_object(row, "SCH_DISCWDIS_ISS_IDEA_")

        # LINEAGE: SCH_DISCWODIS_SINGOOS_ → oss_single, SCH_DISCWODIS_MULTOOS_ → oss_multiple
        crdc["oss_single"] = crdc_race_object(row, "SCH_DISCWODIS_SINGOOS_")
        crdc["oss_single_idea"] = crdc_race_object(row, "SCH_DISCWDIS_SINGOOS_IDEA_")
        crdc["oss_multiple"] = crdc_race_object(row, "SCH_DISCWODIS_MULTOOS_")
        crdc["oss_multiple_idea"] = crdc_race_object(row, "SCH_DISCWDIS_MULTOOS_IDEA_")

        # OOS instance totals
        oos_wodis_val, _ = parse_crdc_value(row.get("SCH_OOSINSTANCES_WODIS"))
        oos_idea_val, _ = parse_crdc_value(row.get("SCH_OOSINSTANCES_IDEA"))
        oos_504_val, _ = parse_crdc_value(row.get("SCH_OOSINSTANCES_504"))
        if oos_wodis_val is not None:
            crdc["oos_instances_wodis"] = oos_wodis_val
        if oos_idea_val is not None:
            crdc["oos_instances_idea"] = oos_idea_val
        if oos_504_val is not None:
            crdc["oos_instances_504"] = oos_504_val

        matched += 1

    logger.info(f"Suspensions: {matched} schools loaded.")
    return matched


def process_expulsions(schools, logger, marker_log):
    """Process expulsions.csv → discipline.crdc.expulsions."""
    rows = read_crdc_file("expulsions.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "expulsions.csv",
                    "column": col, "value": str(val).strip()
                })

        if "discipline" not in schools[ncessch]:
            schools[ncessch]["discipline"] = {}
        if "crdc" not in schools[ncessch]["discipline"]:
            schools[ncessch]["discipline"]["crdc"] = {"year": "2021-22"}

        crdc = schools[ncessch]["discipline"]["crdc"]

        # LINEAGE: EXPWE = with educational services, EXPWOE = without, EXPZT = zero tolerance
        crdc["expulsion_with_ed"] = crdc_race_object(row, "SCH_DISCWODIS_EXPWE_")
        crdc["expulsion_without_ed"] = crdc_race_object(row, "SCH_DISCWODIS_EXPWOE_")
        crdc["expulsion_zero_tolerance"] = crdc_race_object(row, "SCH_DISCWODIS_EXPZT_")

        matched += 1

    logger.info(f"Expulsions: {matched} schools loaded.")
    return matched


def process_corporal_punishment(schools, logger, marker_log):
    """Process corporal_punishment.csv → discipline.crdc.corporal_punishment."""
    rows = read_crdc_file("corporal_punishment.csv", logger)
    matched = 0
    wa_corporal_yes = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "corporal_punishment.csv",
                    "column": col, "value": str(val).strip()
                })

        if "discipline" not in schools[ncessch]:
            schools[ncessch]["discipline"] = {}
        if "crdc" not in schools[ncessch]["discipline"]:
            schools[ncessch]["discipline"]["crdc"] = {"year": "2021-22"}

        # Check indicator — WA doesn't use corporal punishment, so any "Yes" is an anomaly
        indicator = (row.get("SCH_CORPINSTANCES_IND") or "").strip()
        if indicator == "Yes":
            wa_corporal_yes += 1
            logger.warning(
                f"Data quality anomaly: {schools[ncessch].get('name', ncessch)} "
                f"({ncessch}) shows corporal punishment indicator = Yes. "
                "WA state law prohibits corporal punishment."
            )

        schools[ncessch]["discipline"]["crdc"]["corporal_punishment_indicator"] = (indicator == "Yes")
        matched += 1

    if wa_corporal_yes > 0:
        logger.warning(f"{wa_corporal_yes} WA schools show corporal punishment = Yes (unexpected).")
    else:
        logger.info("Corporal punishment: No WA schools show Yes (expected).")
    logger.info(f"Corporal punishment: {matched} schools loaded.")
    return matched


def process_restraint_seclusion(schools, logger, marker_log):
    """Process restraint_and_seclusion.csv → safety.restraint_seclusion."""
    rows = read_crdc_file("restraint_and_seclusion.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "restraint_and_seclusion.csv",
                    "column": col, "value": str(val).strip()
                })

        if "safety" not in schools[ncessch]:
            schools[ncessch]["safety"] = {}

        rs = {}

        # LINEAGE: SCH_RSINSTANCES_{type}_{disability} → safety.restraint_seclusion
        for measure_type, label in [("MECH", "mechanical"), ("PHYS", "physical"), ("SECL", "seclusion")]:
            for dis_type, dis_label in [("WODIS", "wodis"), ("IDEA", "idea"), ("504", "504")]:
                col = f"SCH_RSINSTANCES_{measure_type}_{dis_type}"
                val, flag = parse_crdc_value(row.get(col, ""))
                key = f"{label}_{dis_label}"
                if val is not None:
                    rs[key] = val
                # Suppressed values left as absent (not stored as null in compact object)

        if rs:
            schools[ncessch]["safety"]["restraint_seclusion"] = rs

        matched += 1

    logger.info(f"Restraint/seclusion: {matched} schools loaded.")
    return matched


def process_referrals_arrests(schools, logger, marker_log):
    """Process referrals_and_arrests.csv → safety.referrals_arrests."""
    rows = read_crdc_file("referrals_and_arrests.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "referrals_and_arrests.csv",
                    "column": col, "value": str(val).strip()
                })

        if "safety" not in schools[ncessch]:
            schools[ncessch]["safety"] = {}

        ra = {}

        # LINEAGE: SCH_DISCWODIS_REF_ → referrals, SCH_DISCWODIS_ARR_ → arrests
        referrals = crdc_race_object(row, "SCH_DISCWODIS_REF_")
        arrests = crdc_race_object(row, "SCH_DISCWODIS_ARR_")

        if referrals:
            ra["referrals"] = referrals
        if arrests:
            ra["arrests"] = arrests

        if ra:
            schools[ncessch]["safety"]["referrals_arrests"] = ra

        matched += 1

    logger.info(f"Referrals/arrests: {matched} schools loaded.")
    return matched


def process_harassment(schools, logger, marker_log):
    """Process harassment_and_bullying.csv → safety.harassment_bullying."""
    rows = read_crdc_file("harassment_and_bullying.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "harassment_and_bullying.csv",
                    "column": col, "value": str(val).strip()
                })

        if "safety" not in schools[ncessch]:
            schools[ncessch]["safety"] = {}

        hb = {}

        # LINEAGE: SCH_HBALLEGATIONS_{type} → safety.harassment_bullying
        for col_suffix, label in [
            ("SEX", "allegations_sex"),
            ("RAC", "allegations_race"),
            ("DIS", "allegations_disability"),
            ("REL", "allegations_religion"),
            ("ORI", "allegations_orientation"),
        ]:
            val, flag = parse_crdc_value(row.get(f"SCH_HBALLEGATIONS_{col_suffix}", ""))
            if val is not None:
                hb[label] = val

        if hb:
            schools[ncessch]["safety"]["harassment_bullying"] = hb

        matched += 1

    logger.info(f"Harassment/bullying: {matched} schools loaded.")
    return matched


def process_offenses(schools, logger, marker_log):
    """Process offenses.csv → safety.offenses."""
    rows = read_crdc_file("offenses.csv", logger)
    matched = 0

    # Column mappings for offense types
    offense_cols = {
        "SCH_OFFENSE_ATT": "attacks",
        "SCH_OFFENSE_WEAP": "weapons",
        "SCH_OFFENSE_ROB": "robbery",
        "SCH_OFFENSE_THREAT": "threats",
        "SCH_OFFENSE_SEX": "sexual_assault",
    }

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "offenses.csv",
                    "column": col, "value": str(val).strip()
                })

        if "safety" not in schools[ncessch]:
            schools[ncessch]["safety"] = {}

        offenses = {}

        for crdc_col, schema_key in offense_cols.items():
            val, flag = parse_crdc_value(row.get(crdc_col, ""))
            if val is not None:
                offenses[schema_key] = val

        # Indicator fields
        firearm_ind = (row.get("SCH_FIREARM_IND") or "").strip()
        homicide_ind = (row.get("SCH_HOMICIDE_IND") or "").strip()
        offenses["firearm_indicator"] = (firearm_ind == "Yes")
        offenses["homicide_indicator"] = (homicide_ind == "Yes")

        schools[ncessch]["safety"]["offenses"] = offenses
        matched += 1

    logger.info(f"Offenses: {matched} schools loaded.")
    return matched


def process_school_support(schools, logger, marker_log):
    """Process school_support.csv → staffing section."""
    rows = read_crdc_file("school_support.csv", logger)
    matched = 0

    staffing_cols = {
        "SCH_FTETEACH_TOT": "teacher_fte_total",
        "SCH_FTETEACH_CERT": "teacher_fte_certified",
        "SCH_FTETEACH_NOTCERT": "teacher_fte_not_certified",
        "SCH_FTECOUNSELORS": "counselor_fte",
        "SCH_FTESERVICES_NUR": "nurse_fte",
        "SCH_FTESERVICES_PSY": "psychologist_fte",
        "SCH_FTESERVICES_SOC": "social_worker_fte",
        "SCH_FTESECURITY_LEO": "sro_fte",
        "SCH_FTESECURITY_GUA": "security_guard_fte",
    }

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "school_support.csv",
                    "column": col, "value": str(val).strip()
                })

        staffing = {"year": "2021-22"}

        # LINEAGE: SCH_FTETEACH_TOT → staffing.teacher_fte_total, etc.
        for crdc_col, schema_key in staffing_cols.items():
            val, flag = parse_crdc_value(row.get(crdc_col, ""))
            if val is not None:
                staffing[schema_key] = safe_float(val)

        schools[ncessch]["staffing"] = staffing
        matched += 1

    logger.info(f"School support (staffing): {matched} schools loaded.")
    return matched


def process_course_access_file(schools, filename, section_key, indicator_col,
                                enrollment_prefix, logger, marker_log):
    """Generic processor for AP, dual enrollment, and gifted/talented files.

    These files all follow the same pattern: an indicator column (Yes/No)
    and enrollment columns by race/sex.
    """
    rows = read_crdc_file(filename, logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": filename,
                    "column": col, "value": str(val).strip()
                })

        if "course_access" not in schools[ncessch]:
            schools[ncessch]["course_access"] = {}

        indicator = (row.get(indicator_col) or "").strip()
        section = {
            "indicator": (indicator == "Yes"),
        }

        # Enrollment by race/sex if applicable
        enrollment = crdc_race_object(row, enrollment_prefix)
        if enrollment:
            section["enrollment_by_race"] = enrollment

        schools[ncessch]["course_access"][section_key] = section
        matched += 1

    logger.info(f"{section_key}: {matched} schools loaded.")
    return matched


def process_enrollment(schools, logger, marker_log):
    """Process enrollment.csv — set metadata.crdc_combokey for traceability."""
    rows = read_crdc_file("enrollment.csv", logger)
    matched = 0

    for ncessch in schools:
        row = rows.get(ncessch)
        if row is None:
            continue

        for col, val in row.items():
            if col.startswith("SCH_") and str(val).strip() in ("-12", "-13"):
                marker_log.append({
                    "ncessch": ncessch, "file": "enrollment.csv",
                    "column": col, "value": str(val).strip()
                })

        schools[ncessch]["metadata"]["crdc_combokey"] = ncessch
        matched += 1

    logger.info(f"CRDC enrollment: {matched} schools matched (combokey set).")
    return matched


def main():
    logger = setup_logging("07_load_crdc")
    logger.info("Step 07: Loading CRDC data from 13 files.")

    schools = load_schools()

    # Accumulates all -12/-13 instances across all files
    marker_log = []

    # Process each CRDC file
    process_enrollment(schools, logger, marker_log)
    process_suspensions(schools, logger, marker_log)
    process_expulsions(schools, logger, marker_log)
    process_corporal_punishment(schools, logger, marker_log)
    process_restraint_seclusion(schools, logger, marker_log)
    process_referrals_arrests(schools, logger, marker_log)
    process_harassment(schools, logger, marker_log)
    process_offenses(schools, logger, marker_log)
    process_school_support(schools, logger, marker_log)

    # Course access files — all follow the same indicator + enrollment pattern
    process_course_access_file(
        schools, "advanced_placement.csv", "ap",
        "SCH_APENR_IND", "SCH_APENR_", logger, marker_log
    )
    process_course_access_file(
        schools, "dual_enrollment.csv", "dual_enrollment",
        "SCH_DUAL_IND", "SCH_DUALENR_", logger, marker_log
    )
    process_course_access_file(
        schools, "gifted_and_talented.csv", "gifted_talented",
        "SCH_GT_IND", "SCH_GTENR_", logger, marker_log
    )

    # Log -12/-13 instances
    log_unknown_markers(marker_log, schools, logger)

    save_schools(schools)

    # Summary: how many schools have CRDC data?
    has_crdc = sum(1 for doc in schools.values() if "metadata" in doc and doc["metadata"].get("crdc_combokey"))
    missing_crdc = len(schools) - has_crdc

    logger.info(f"{has_crdc} schools have CRDC data. {missing_crdc} missing (likely opened after 2021-22).")

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools:
        doc = schools[FAIRHAVEN_NCESSCH]
        staffing = doc.get("staffing", {})
        safety = doc.get("safety", {})
        rs = safety.get("restraint_seclusion", {})
        hb = safety.get("harassment_bullying", {})
        ca = doc.get("course_access", {})

        logger.info(
            f"Fairhaven CRDC: "
            f"teacher_fte={staffing.get('teacher_fte_total')}, "
            f"counselor_fte={staffing.get('counselor_fte')}, "
            f"psychologist_fte={staffing.get('psychologist_fte')}, "
            f"physical_idea={rs.get('physical_idea')}, "
            f"seclusion_idea={rs.get('seclusion_idea')}, "
            f"harassment_sex={hb.get('allegations_sex')}, "
            f"harassment_race={hb.get('allegations_race')}, "
            f"harassment_disability={hb.get('allegations_disability')}, "
            f"gifted_indicator={ca.get('gifted_talented', {}).get('indicator')}, "
            f"ap_indicator={ca.get('ap', {}).get('indicator')}."
        )

    logger.info("Step 07 complete.")


if __name__ == "__main__":
    main()
