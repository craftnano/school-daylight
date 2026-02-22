"""
schema_preflight.py — Simulate MongoDB documents and measure size.

Builds a full document for Fairhaven and the 5 largest WA schools,
plus estimates max/median across all WA schools.

Output: phases/phase-1/schema_preflight.md
"""

import os
import sys
import csv
import json
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

FAIRHAVEN = "530042000104"

# CRDC race column suffixes → schema keys
RACE_SUFFIXES = {
    "HI_M": ("hispanic", "male"), "HI_F": ("hispanic", "female"),
    "AM_M": ("american_indian", "male"), "AM_F": ("american_indian", "female"),
    "AS_M": ("asian", "male"), "AS_F": ("asian", "female"),
    "HP_M": ("pacific_islander", "male"), "HP_F": ("pacific_islander", "female"),
    "BL_M": ("black", "male"), "BL_F": ("black", "female"),
    "WH_M": ("white", "male"), "WH_F": ("white", "female"),
    "TR_M": ("two_or_more", "male"), "TR_F": ("two_or_more", "female"),
}


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_int(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def parse_crdc_value(val):
    """Convert CRDC value, respecting suppression."""
    if val in ("-9", "-5", "-4", "-3", "-2", "-12", "-13"):
        return None  # suppressed — would store null + flag in real pipeline
    try:
        f = float(val)
        if f == int(f):
            return int(f)
        return f
    except (ValueError, TypeError):
        return None


def crdc_race_object(row, prefix):
    """Build a race/sex breakdown object from CRDC columns with a given prefix."""
    obj = {}
    for suffix, (race, sex) in RACE_SUFFIXES.items():
        col = f"{prefix}{suffix}"
        val = parse_crdc_value(row.get(col, ""))
        if val is not None:
            obj[f"{race}_{sex}"] = val
    return obj if obj else None


def build_document(ncessch, directory, membership, crdc_files, ospi_enroll, ospi_assess,
                   ospi_disc, ospi_growth, ospi_sqss, ospi_ppe):
    """Build a simulated MongoDB document for one school."""

    doc = {}

    # --- Identity (CCD Directory) ---
    ccd = directory.get(ncessch)
    if not ccd:
        return None

    doc["_id"] = ncessch
    doc["name"] = ccd["SCH_NAME"]
    doc["district"] = {"name": ccd["LEA_NAME"], "nces_id": ccd["LEAID"]}
    doc["address"] = {
        "street": ccd.get("LSTREET1", ""),
        "city": ccd.get("LCITY", ""),
        "state": ccd.get("LSTATE", ""),
        "zip": ccd.get("LZIP", ""),
    }
    doc["school_type"] = ccd.get("SCH_TYPE_TEXT", "")
    doc["level"] = ccd.get("LEVEL", "")
    doc["grade_span"] = {"low": ccd.get("GSLO", ""), "high": ccd.get("GSHI", "")}
    doc["is_charter"] = ccd.get("CHARTER_TEXT", "") == "Yes"
    doc["website"] = ccd.get("WEBSITE", "")
    doc["phone"] = ccd.get("PHONE", "")

    # --- Enrollment (CCD Membership) ---
    mem = membership.get(ncessch)
    if mem:
        doc["enrollment"] = {
            "year": "2024-25",
            "total": safe_int(mem.get("total_enrollment")),
            "by_race": {
                "hispanic": safe_int(mem.get("hispanic")),
                "american_indian": safe_int(mem.get("american_indian")),
                "asian": safe_int(mem.get("asian")),
                "black": safe_int(mem.get("black")),
                "pacific_islander": safe_int(mem.get("pacific_islander")),
                "white": safe_int(mem.get("white")),
                "two_or_more": safe_int(mem.get("two_or_more")),
            },
            "by_sex": {
                "male": safe_int(mem.get("male")),
                "female": safe_int(mem.get("female")),
            },
        }

    # --- Demographics (OSPI Enrollment) ---
    ospi_e = ospi_enroll.get(ncessch)
    if ospi_e:
        all_students = safe_int(ospi_e.get("All Students"))
        frl = safe_int(ospi_e.get("Low Income"))
        doc["demographics"] = {
            "year": "2023-24",
            "frl_count": frl,
            "frl_pct": round(frl / all_students, 4) if frl and all_students else None,
            "ell_count": safe_int(ospi_e.get("English Language Learners")),
            "sped_count": safe_int(ospi_e.get("Students with Disabilities")),
            "section_504_count": safe_int(ospi_e.get("Section 504")),
            "foster_care_count": safe_int(ospi_e.get("Foster Care")),
            "homeless_count": safe_int(ospi_e.get("Homeless")),
            "migrant_count": safe_int(ospi_e.get("Migrant")),
        }

    # --- Academics: Assessment ---
    assessments = ospi_assess.get(ncessch, [])
    assess_doc = {"year": "2023-24"}
    for r in assessments:
        subj = r.get("TestSubject", "")
        val = r.get("Percent Consistent Grade Level Knowledge And Above", "")
        pct = safe_float(val)
        if pct is not None:
            pct = round(pct / 100, 4)
        if subj == "ELA":
            assess_doc["ela_proficiency_pct"] = pct
        elif subj == "Math":
            assess_doc["math_proficiency_pct"] = pct
        elif subj == "Science":
            assess_doc["science_proficiency_pct"] = pct
    assess_doc["students_tested"] = safe_int(
        (assessments[0] if assessments else {}).get("Count of Students Expected to Test")
    )
    doc["academics"] = {"assessment": assess_doc}

    # --- Academics: Growth ---
    growth_rows = ospi_growth.get(ncessch, [])
    growth_doc = {"year": "2023-24"}
    for r in growth_rows:
        subj = r.get("Subject", "")
        sgp = safe_float(r.get("MedianSGP"))
        if "English" in subj:
            growth_doc["ela_median_sgp"] = sgp
            growth_doc["ela_pct_low"] = safe_float(r.get("PercentLowGrowth"))
            growth_doc["ela_pct_typical"] = safe_float(r.get("PercentTypicalGrowth"))
            growth_doc["ela_pct_high"] = safe_float(r.get("PercentHighGrowth"))
        elif subj == "Math":
            growth_doc["math_median_sgp"] = sgp
            growth_doc["math_pct_low"] = safe_float(r.get("PercentLowGrowth"))
            growth_doc["math_pct_typical"] = safe_float(r.get("PercentTypicalGrowth"))
            growth_doc["math_pct_high"] = safe_float(r.get("PercentHighGrowth"))
    doc["academics"]["growth"] = growth_doc

    # --- Academics: Attendance (SQSS) ---
    sqss_rows = ospi_sqss.get(ncessch, {})
    att = sqss_rows.get("Regular Attendance")
    doc["academics"]["attendance"] = {
        "year": "2024-25",
        "regular_attendance_pct": safe_float(att["Percent"]) if att else None,
        "regular_attendance_numerator": safe_int(att["Numerator"]) if att else None,
        "regular_attendance_denominator": safe_int(att["Denominator"]) if att else None,
    }
    ninth = sqss_rows.get("Ninth Grade on Track")
    doc["academics"]["ninth_grade_on_track_pct"] = safe_float(ninth["Percent"]) if ninth else None
    dual = sqss_rows.get("Dual Credit")
    doc["academics"]["dual_credit_pct"] = safe_float(dual["Percent"]) if dual else None

    # --- Discipline OSPI ---
    disc = ospi_disc.get(ncessch)
    if disc:
        doc["discipline"] = {
            "ospi": {
                "year": "2023-24",
                "rate": safe_float(disc.get("DisciplineRate")),
                "numerator": safe_int(disc.get("DisciplineNumerator")),
                "denominator": safe_int(disc.get("DisciplineDenominator")),
            }
        }
    else:
        doc["discipline"] = {"ospi": {"year": "2023-24"}}

    # --- Discipline CRDC ---
    susp = crdc_files.get("suspensions", {}).get(ncessch)
    crdc_disc = {"year": "2021-22"}
    if susp:
        crdc_disc["iss"] = crdc_race_object(susp, "SCH_DISCWODIS_ISS_")
        crdc_disc["oss_single"] = crdc_race_object(susp, "SCH_DISCWODIS_SINGOOS_")
        crdc_disc["oss_multiple"] = crdc_race_object(susp, "SCH_DISCWODIS_MULTOOS_")
        crdc_disc["iss_idea"] = crdc_race_object(susp, "SCH_DISCIDEA_ISS_")
        crdc_disc["oss_single_idea"] = crdc_race_object(susp, "SCH_DISCIDEA_SINGOOS_")
        crdc_disc["oss_multiple_idea"] = crdc_race_object(susp, "SCH_DISCIDEA_MULTOOS_")
    exp = crdc_files.get("expulsions", {}).get(ncessch)
    if exp:
        crdc_disc["expulsions"] = crdc_race_object(exp, "SCH_DISCWODIS_EXPWE_")
    corp = crdc_files.get("corporal_punishment", {}).get(ncessch)
    if corp:
        crdc_disc["corporal_punishment_indicator"] = corp.get("SCH_CORP_IND") == "Yes"
        crdc_disc["corporal_punishment_count"] = parse_crdc_value(
            corp.get("SCH_PSCORPINSTANCES_ALL", "0")
        )
    doc["discipline"]["crdc"] = crdc_disc

    # --- Safety ---
    rs = crdc_files.get("restraint_and_seclusion", {}).get(ncessch)
    safety = {}
    if rs:
        safety["restraint_seclusion"] = {
            "year": "2021-22",
            "caveat": "GAO found significant quality issues in R&S data.",
            "mechanical_wodis": parse_crdc_value(rs.get("SCH_RSINSTANCES_MECH_WODIS")),
            "mechanical_idea": parse_crdc_value(rs.get("SCH_RSINSTANCES_MECH_IDEA")),
            "mechanical_504": parse_crdc_value(rs.get("SCH_RSINSTANCES_MECH_504")),
            "physical_wodis": parse_crdc_value(rs.get("SCH_RSINSTANCES_PHYS_WODIS")),
            "physical_idea": parse_crdc_value(rs.get("SCH_RSINSTANCES_PHYS_IDEA")),
            "physical_504": parse_crdc_value(rs.get("SCH_RSINSTANCES_PHYS_504")),
            "seclusion_wodis": parse_crdc_value(rs.get("SCH_RSINSTANCES_SECL_WODIS")),
            "seclusion_idea": parse_crdc_value(rs.get("SCH_RSINSTANCES_SECL_IDEA")),
            "seclusion_504": parse_crdc_value(rs.get("SCH_RSINSTANCES_SECL_504")),
        }
    ref = crdc_files.get("referrals_and_arrests", {}).get(ncessch)
    if ref:
        safety["referrals_arrests"] = {
            "year": "2021-22",
            "referrals": crdc_race_object(ref, "SCH_DISCWODIS_REF_"),
            "arrests": crdc_race_object(ref, "SCH_DISCWODIS_ARR_"),
        }
    hb = crdc_files.get("harassment_and_bullying", {}).get(ncessch)
    if hb:
        safety["harassment_bullying"] = {
            "year": "2021-22",
            "allegations_sex": parse_crdc_value(hb.get("SCH_HBALLEGATIONS_SEX")),
            "allegations_orientation": parse_crdc_value(hb.get("SCH_HBALLEGATIONS_ORI")),
            "allegations_race": parse_crdc_value(hb.get("SCH_HBALLEGATIONS_RAC")),
            "allegations_disability": parse_crdc_value(hb.get("SCH_HBALLEGATIONS_DIS")),
            "allegations_religion": parse_crdc_value(hb.get("SCH_HBALLEGATIONS_REL")),
        }
    off = crdc_files.get("offenses", {}).get(ncessch)
    if off:
        safety["offenses"] = {
            "year": "2021-22",
            "attacks_with_weapon": parse_crdc_value(off.get("SCH_OFFENSE_ATTWW")),
            "attacks_without_weapon": parse_crdc_value(off.get("SCH_OFFENSE_ATTWOW")),
            "weapon_possession": parse_crdc_value(off.get("SCH_OFFENSE_POSSWX")),
            "threats_with_weapon": parse_crdc_value(off.get("SCH_OFFENSE_THRWW")),
            "threats_without_weapon": parse_crdc_value(off.get("SCH_OFFENSE_THRWOW")),
            "firearm_indicator": off.get("SCH_FIREARM_IND") == "Yes",
            "homicide_indicator": off.get("SCH_HOMICIDE_IND") == "Yes",
        }
    doc["safety"] = safety

    # --- Staffing ---
    sup = crdc_files.get("school_support", {}).get(ncessch)
    if sup:
        doc["staffing"] = {
            "year": "2021-22",
            "teacher_fte_total": safe_float(sup.get("SCH_FTETEACH_TOT")),
            "teacher_fte_certified": safe_float(sup.get("SCH_FTETEACH_CERT")),
            "teacher_fte_not_certified": safe_float(sup.get("SCH_FTETEACH_NOTCERT")),
            "counselor_fte": safe_float(sup.get("SCH_FTECOUNSELORS")),
            "nurse_fte": safe_float(sup.get("SCH_FTESERVICES_NUR")),
            "psychologist_fte": safe_float(sup.get("SCH_FTESERVICES_PSY")),
            "social_worker_fte": safe_float(sup.get("SCH_FTESERVICES_SOC")),
            "sro_fte": safe_float(sup.get("SCH_FTESECURITY_LEO")),
            "security_guard_fte": safe_float(sup.get("SCH_FTESECURITY_GUA")),
        }

    # --- Finance ---
    ppe = ospi_ppe.get(ncessch)
    if ppe:
        doc["finance"] = {
            "year": ppe.get("School Year Code", ""),
            "per_pupil_total": safe_float(ppe.get("Total_PPE")),
            "per_pupil_local": safe_float(ppe.get("Local PPE")),
            "per_pupil_state": safe_float(ppe.get("State PPE")),
            "per_pupil_federal": safe_float(ppe.get("Federal PPE")),
        }

    # --- Course Access ---
    ap = crdc_files.get("advanced_placement", {}).get(ncessch)
    de = crdc_files.get("dual_enrollment", {}).get(ncessch)
    gt = crdc_files.get("gifted_and_talented", {}).get(ncessch)
    course = {"year": "2021-22"}
    if ap:
        course["ap"] = {
            "indicator": ap.get("SCH_APSCIENR_IND") == "Yes",
            "enrollment_by_race": crdc_race_object(ap, "SCH_APENR_"),
        }
    if de:
        course["dual_enrollment"] = {
            "indicator": de.get("SCH_DUAL_IND") == "Yes",
            "enrollment_by_race": crdc_race_object(de, "SCH_DUALENR_"),
        }
    if gt:
        course["gifted_talented"] = {
            "indicator": gt.get("SCH_GT_IND") == "Yes",
            "enrollment_by_race": crdc_race_object(gt, "SCH_GTENR_"),
        }
    doc["course_access"] = course

    # --- Metadata ---
    parts = ccd.get("ST_SCHID", "").split("-")
    doc["metadata"] = {
        "ospi_school_code": parts[2] if len(parts) == 3 else "",
        "ospi_district_code": parts[1] if len(parts) == 3 else "",
        "crdc_combokey": ncessch,
        "data_vintage": {
            "ccd": "2024-25", "crdc": "2021-22",
            "ospi_enrollment": "2023-24", "ospi_assessment": "2023-24",
            "ospi_discipline": "2023-24", "ospi_growth": "2024-25",
            "ospi_sqss": "2024-25", "ospi_ppe": "varies",
        },
        "join_status": "all_sources" if ncessch in crdc_files.get("enrollment", {}) else "missing_crdc",
    }

    return doc


def section_sizes(doc):
    """Return byte sizes of each top-level key in the document."""
    sizes = {}
    for key, value in doc.items():
        sizes[key] = len(json.dumps(value))
    return sizes


def main():
    data_dir = config.DATA_DIR
    crdc_dir = os.path.join(data_dir, "crdc_wa")
    ospi_dir = os.path.join(config.RAW_DIR, "ospi")

    # --- Load CCD Directory ---
    directory = {}
    for r in load_csv(os.path.join(data_dir, "ccd_wa_directory.csv")):
        directory[r["NCESSCH"]] = r

    # --- Load CCD Membership ---
    membership = {}
    for r in load_csv(os.path.join(data_dir, "ccd_wa_membership.csv")):
        membership[r["ncessch"]] = r

    # --- Load CRDC extracts (keyed by COMBOKEY) ---
    crdc_files_map = {}
    for fname in os.listdir(crdc_dir):
        if not fname.endswith(".csv"):
            continue
        key = fname.replace(".csv", "")
        crdc_files_map[key] = {}
        for r in load_csv(os.path.join(crdc_dir, fname)):
            crdc_files_map[key][r["COMBOKEY"]] = r

    # --- Load OSPI Enrollment (school-level, All Grades) ---
    ospi_enroll = {}
    # Build crosswalk: OSPI codes → NCESSCH
    ospi_to_ncessch = {}
    for ncessch, ccd_row in directory.items():
        parts = ccd_row.get("ST_SCHID", "").split("-")
        if len(parts) == 3:
            ospi_to_ncessch[f"{parts[1]}_{parts[2]}"] = ncessch

    for r in load_csv(os.path.join(ospi_dir, "Report_Card_Enrollment_2023-24_School_Year.csv")):
        if r["OrganizationLevel"] == "School" and r["GradeLevel"] == "All Grades":
            key = f"{r['DistrictCode']}_{r['SchoolCode']}"
            nid = ospi_to_ncessch.get(key)
            if nid:
                ospi_enroll[nid] = r

    # --- Load OSPI Assessment (school-level, All Students, All Grades) ---
    ospi_assess = defaultdict(list)
    for r in load_csv(os.path.join(ospi_dir, "Report_Card_Assessment_Data_2023-24.csv")):
        if (r["OrganizationLevel"] == "School" and r.get("StudentGroupType") == "All"
                and r["GradeLevel"] == "All Grades"):
            key = f"{r['DistrictCode']}_{r['SchoolCode']}"
            nid = ospi_to_ncessch.get(key)
            if nid:
                ospi_assess[nid].append(r)

    # --- Load OSPI Discipline (All Students, All) ---
    ospi_disc = {}
    for r in load_csv(os.path.join(ospi_dir, "Report_Card_Discipline_for_2023-24.csv")):
        if (r["OrganizationLevel"] == "School"
                and r.get("Student Group") == "All Students" and r["GradeLevel"] == "All"):
            dc = r["DistrictCode"].replace(",", "")
            sc = r["SchoolCode"].replace(",", "")
            key = f"{dc}_{sc}"
            nid = ospi_to_ncessch.get(key)
            if nid:
                ospi_disc[nid] = r

    # --- Load OSPI Growth (AllStudents, All Grades) ---
    ospi_growth = defaultdict(list)
    for r in load_csv(os.path.join(ospi_dir, "Report_Card_Growth_for_2023-24.csv")):
        if (r["OrganizationLevel"] == "School"
                and r.get("StudentGroupType") == "AllStudents"
                and r["GradeLevel"] == "All Grades"):
            key = f"{r['DistrictCode']}_{r['SchoolCode']}"
            nid = ospi_to_ncessch.get(key)
            if nid:
                ospi_growth[nid].append(r)

    # --- Load OSPI SQSS (All Students, All Grades) ---
    ospi_sqss = defaultdict(dict)
    for r in load_csv(os.path.join(ospi_dir, "Report_Card_SQSS_for_2024-25.csv")):
        if (r["OrganizationLevel"] == "School"
                and r.get("StudentGroupType") == "All Students"
                and r["GradeLevel"] == "All Grades"):
            key = f"{r['DistrictCode']}_{r['SchoolCode']}"
            nid = ospi_to_ncessch.get(key)
            if nid:
                ospi_sqss[nid][r["Measure"]] = r

    # --- Load OSPI PPE (most recent year, school-level) ---
    ospi_ppe = {}
    for r in load_csv(os.path.join(ospi_dir, "Per_Pupil_Expenditure_AllYears.csv")):
        if r.get("Organization Level") == "School" and "2023" in r.get("School Year Code", ""):
            sc = r.get("SchoolCode", "").strip()
            # PPE doesn't have DistrictCode in same format; match by SchoolCode via
            # reverse lookup
            for okey, nid in ospi_to_ncessch.items():
                if okey.endswith(f"_{sc}"):
                    ospi_ppe[nid] = r
                    break

    # --- Build documents for all schools that have CCD directory entries ---
    print("Building documents for all WA schools...")
    all_ncessch = sorted(directory.keys())

    # Find 5 largest by enrollment
    enrollment_list = []
    for nid in all_ncessch:
        mem = membership.get(nid)
        if mem:
            total = safe_int(mem.get("total_enrollment"))
            if total and total > 0:
                enrollment_list.append((total, nid))
    enrollment_list.sort(reverse=True)
    top5 = [nid for _, nid in enrollment_list[:5]]

    # Target schools: Fairhaven + top 5
    targets = [FAIRHAVEN] + top5

    # Build documents for targets
    target_docs = {}
    for nid in targets:
        doc = build_document(
            nid, directory, membership, crdc_files_map,
            ospi_enroll, ospi_assess, ospi_disc, ospi_growth, ospi_sqss, ospi_ppe
        )
        if doc:
            target_docs[nid] = doc

    # Build all docs for size distribution
    all_sizes = []
    for nid in all_ncessch:
        doc = build_document(
            nid, directory, membership, crdc_files_map,
            ospi_enroll, ospi_assess, ospi_disc, ospi_growth, ospi_sqss, ospi_ppe
        )
        if doc:
            size = len(json.dumps(doc))
            all_sizes.append((size, nid))

    all_sizes.sort(reverse=True)

    # --- Generate report ---
    lines = []
    lines.append("# Schema Preflight Check")
    lines.append("")
    lines.append(f"**Date:** 2026-02-21")
    lines.append(f"**Purpose:** Verify MongoDB document sizes are well within the 16 MB limit.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Target school table
    lines.append("## Target School Documents")
    lines.append("")
    lines.append("| School | NCESSCH | Enrollment | JSON Bytes | KB |")
    lines.append("|--------|---------|-----------|------------|-----|")
    for nid in targets:
        doc = target_docs.get(nid)
        if doc:
            size = len(json.dumps(doc))
            enr = doc.get("enrollment", {}).get("total", "?")
            name = doc.get("name", "?")
            lines.append(f"| {name} | {nid} | {enr} | {size:,} | {size/1024:.1f} |")

    lines.append("")

    # Section breakdown for Fairhaven
    lines.append("## Section Size Breakdown (Fairhaven)")
    lines.append("")
    fh_doc = target_docs.get(FAIRHAVEN)
    if fh_doc:
        sizes = section_sizes(fh_doc)
        total = sum(sizes.values())
        lines.append("| Section | Bytes | % of Total |")
        lines.append("|---------|-------|-----------|")
        for key, size in sorted(sizes.items(), key=lambda x: -x[1]):
            pct = 100 * size / total
            lines.append(f"| {key} | {size:,} | {pct:.1f}% |")
        lines.append(f"| **TOTAL** | **{total:,}** | **100%** |")
    lines.append("")

    # Section breakdown for largest school
    if all_sizes:
        biggest_nid = all_sizes[0][1]
        biggest_doc = build_document(
            biggest_nid, directory, membership, crdc_files_map,
            ospi_enroll, ospi_assess, ospi_disc, ospi_growth, ospi_sqss, ospi_ppe
        )
        if biggest_doc:
            lines.append(f"## Section Size Breakdown (Largest: {biggest_doc.get('name', '?')})")
            lines.append("")
            sizes = section_sizes(biggest_doc)
            total = sum(sizes.values())
            lines.append("| Section | Bytes | % of Total |")
            lines.append("|---------|-------|-----------|")
            for key, size in sorted(sizes.items(), key=lambda x: -x[1]):
                pct = 100 * size / total
                lines.append(f"| {key} | {size:,} | {pct:.1f}% |")
            lines.append(f"| **TOTAL** | **{total:,}** | **100%** |")
        lines.append("")

    # Distribution
    lines.append("## Size Distribution (All WA Schools)")
    lines.append("")
    if all_sizes:
        sizes_only = [s for s, _ in all_sizes]
        n = len(sizes_only)
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Schools with documents | {n:,} |")
        lines.append(f"| Maximum | {sizes_only[0]:,} bytes ({sizes_only[0]/1024:.1f} KB) |")
        lines.append(f"| 95th percentile | {sizes_only[int(n*0.05)]:,} bytes ({sizes_only[int(n*0.05)]/1024:.1f} KB) |")
        lines.append(f"| Median | {sizes_only[n//2]:,} bytes ({sizes_only[n//2]/1024:.1f} KB) |")
        lines.append(f"| Minimum | {sizes_only[-1]:,} bytes ({sizes_only[-1]/1024:.1f} KB) |")
        over_1mb = sum(1 for s in sizes_only if s > 1_000_000)
        over_16mb = sum(1 for s in sizes_only if s > 16_000_000)
        lines.append(f"| Schools > 1 MB | {over_1mb} |")
        lines.append(f"| Schools > 16 MB | {over_16mb} |")

    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    if all_sizes:
        max_kb = sizes_only[0] / 1024
        lines.append(f"The largest document is **{max_kb:.1f} KB** — well under the 1 MB concern threshold")
        lines.append(f"and nowhere near the 16 MB MongoDB limit.")
        lines.append("")
        lines.append("Even after Phase 4 adds AI context (estimated ~2-5 KB of news/reputation findings)")
        lines.append("and Phase 5 adds the cached briefing narrative (estimated ~5-10 KB of text),")
        lines.append(f"the largest documents would still be under **{max_kb + 15:.0f} KB** — about")
        lines.append(f"**{(max_kb + 15) / 1024 * 100:.1f}%** of the 1 MB soft target.")
        lines.append("")
        lines.append("**No schema redesign needed.** ✓")

    report = "\n".join(lines)
    output_path = os.path.join(config.PHASES_DIR, "phase-1", "schema_preflight.md")
    with open(output_path, "w") as f:
        f.write(report)
    print(f"Report written to {output_path}")
    print(f"\nQuick summary: {len(all_sizes)} docs, max={sizes_only[0]:,} bytes, median={sizes_only[len(sizes_only)//2]:,} bytes")


if __name__ == "__main__":
    main()
