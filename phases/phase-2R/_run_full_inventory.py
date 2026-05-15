"""
_run_full_inventory.py — Phase 2R audit diagnostic; main audit deliverable.

PURPOSE: Read-only side-by-side inventory across both MongoDB databases
         for the 16 remaining v1 similarity variables (teacher_experience
         covered separately by _run_teacher_exp_inventory.py). For each
         variable, pulls the literal stored value, every in-block vintage
         stamp, and upstream count/denominator context where the variable
         is a derived ratio. Automated uniformity check flags any variable
         whose vintage stamps disagree across the 5 sampled schools within
         a database.
INPUTS:  config.MONGO_URI, config.MONGO_URI_EXPERIMENT (read).
OUTPUTS: phases/phase-2R/inventory_remaining_16.md (markdown report).
READ-ONLY: Yes against MongoDB. Single filesystem write to the markdown
           report.
RECEIPT: phases/phase-2R/inventory_remaining_16.md (1,498 lines) — the
         consolidated audit deliverable referenced in the 2026-05-13
         build_log entry.
SAMPLE SCHOOLS: same five as _run_teacher_exp_inventory.py.
VARIABLES COVERED: 16 of the v1 17-variable set — variables 1, 2, 3, 4,
                   5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17. (Variable
                   9 = teacher_experience, covered separately.)
"""

import json
import os
import sys

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

sys.path.insert(0, "/Users/oriandaleigh/school-daylight")
import config
from pymongo import MongoClient

SAMPLE = [
    ("530042000104", "Fairhaven Middle"),
    ("530423000670", "Juanita HS"),
    ("530927001579", "Lewis and Clark HS"),
    ("530393000610", "Washington Elementary"),
    ("530000102795", "Thunder Mountain Middle"),
]

OUT_PATH = "/Users/oriandaleigh/school-daylight/phases/phase-2R/inventory_remaining_16.md"

PROJ = {
    "_id": 1, "name": 1,
    "metadata.dataset_version": 1,
    "metadata.load_timestamp": 1,
    "metadata.phase_3r_dataset_versions": 1,
    "metadata.phase_3r_ingestion_timestamp": 1,
    "metadata.ospi_district_code": 1,
    "metadata.ospi_school_code": 1,
    "level": 1,
    "derived.level_group": 1,
    "district.nces_id": 1,
    "district.name": 1,
    # enrollment (CCD)
    "enrollment": 1,
    # OSPI demographics
    "demographics": 1,
    # SQSS attendance
    "academics.attendance": 1,
    "academics.growth.year": 1,
    "academics.assessment.year": 1,
    # derived rates
    "derived.chronic_absenteeism_pct": 1,
    "derived.ell_pct": 1, "derived.ell_pct_meta": 1,
    "derived.sped_pct": 1, "derived.sped_pct_meta": 1,
    "derived.homelessness_pct": 1, "derived.homelessness_pct_meta": 1,
    "derived.migrant_pct": 1, "derived.migrant_pct_meta": 1,
    "derived.race_pct_non_white": 1, "derived.race_pct_non_white_meta": 1,
    # graduation
    "graduation_rate": 1,
    # teacher salary
    "teacher_salary": 1,
    # census ACS
    "census_acs": 1,
}


def deep_get(d, dotted):
    if d is None:
        return ("absent", None)
    cur = d
    for p in dotted.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return ("absent", None)
    return ("present", cur)


def status_repr(status, val):
    if status == "absent":
        return "FIELD ABSENT"
    if val is None:
        return "null"
    if isinstance(val, (dict, list)):
        return "```json\n" + json.dumps(val, indent=2, default=str, sort_keys=True) + "\n```"
    return f"`{val!r}`"


def short_repr(status, val):
    if status == "absent":
        return "ABSENT"
    if val is None:
        return "null"
    if isinstance(val, dict):
        return f"<dict, keys={sorted(val.keys())}>"
    if isinstance(val, list):
        return f"<list, len={len(val)}>"
    return repr(val)


def compare(a_status, a_val, b_status, b_val):
    if a_status == "absent" and b_status == "absent":
        return "both absent"
    if a_status == "absent":
        return "absent in schooldaylight, present in schooldaylight_experiment"
    if b_status == "absent":
        return "present in schooldaylight, absent in schooldaylight_experiment"
    if a_val == b_val:
        return "same"
    return "different"


def open_db(uri, name):
    return MongoClient(uri, serverSelectionTimeoutMS=15000)[name]


db_hist = open_db(config.MONGO_URI, config.DB_NAME)
db_exp = open_db(config.MONGO_URI_EXPERIMENT, config.DB_NAME_EXPERIMENT)

# Pull all five schools from both databases up front.
docs = {"hist": {}, "exp": {}}
for nid, _ in SAMPLE:
    docs["hist"][nid] = db_hist["schools"].find_one({"_id": nid}, PROJ)
    docs["exp"][nid] = db_exp["schools"].find_one({"_id": nid}, PROJ)


def emit(line=""):
    out.append(line)


out = []


def header(title, level=2):
    emit(("#" * level) + " " + title)
    emit("")


def render_variable(num, name, schema_path, prov_pattern, section_b, section_c,
                    doc_vintage, in_block_vintage_paths, extra_context_paths=None):
    """Emit one variable's audit block.

    schema_path: dotted path of the stored value
    in_block_vintage_paths: list of dotted paths to vintage stamps to report alongside
    extra_context_paths: optional list of dotted paths to also dump (e.g. upstream counts)
    """
    header(f"Variable {num}: {name}", 2)
    emit(f"- **Schema location:** `{schema_path}`")
    emit(f"- **Provenance pattern:** {prov_pattern}")
    emit("")

    # ----- Section A: MongoDB sample values side-by-side -----
    header("Section A — MongoDB sample values (both databases)", 3)
    for nid, sname in SAMPLE:
        emit(f"**{nid} — {sname}**")
        a = docs["hist"].get(nid)
        b = docs["exp"].get(nid)
        a_status, a_val = deep_get(a, schema_path)
        b_status, b_val = deep_get(b, schema_path)

        emit("")
        emit(f"- `schooldaylight`: {short_repr(a_status, a_val)}")
        if isinstance(a_val, (dict, list)):
            emit(status_repr(a_status, a_val))
        emit(f"- `schooldaylight_experiment`: {short_repr(b_status, b_val)}")
        if isinstance(b_val, (dict, list)):
            emit(status_repr(b_status, b_val))
        emit(f"- **Comparison:** {compare(a_status, a_val, b_status, b_val)}")

        if extra_context_paths:
            emit("")
            emit("  Upstream / supporting context:")
            for p in extra_context_paths:
                as2, av2 = deep_get(a, p)
                bs2, bv2 = deep_get(b, p)
                emit(f"  - `{p}` — hist: {short_repr(as2, av2)} | exp: {short_repr(bs2, bv2)}")

        emit("")

    # ----- In-block vintage stamps per school per db -----
    header("Vintage stamps in or near the variable block (per school, both DBs)", 3)
    rows = []
    rows.append(["School", "Path", "schooldaylight", "schooldaylight_experiment"])
    rows.append(["---"] * 4)
    for nid, sname in SAMPLE:
        a = docs["hist"].get(nid)
        b = docs["exp"].get(nid)
        for vp in in_block_vintage_paths:
            as_, av = deep_get(a, vp)
            bs_, bv = deep_get(b, vp)
            rows.append([f"{nid}", f"`{vp}`",
                         f"`{av!r}`" if as_ == "present" else "ABSENT",
                         f"`{bv!r}`" if bs_ == "present" else "ABSENT"])
    for r in rows:
        emit("| " + " | ".join(str(c) for c in r) + " |")
    emit("")

    # Check uniformity: same in-block vintage across all 5 schools per db
    flag = []
    for db_label, db_key in [("schooldaylight", "hist"), ("schooldaylight_experiment", "exp")]:
        for vp in in_block_vintage_paths:
            vals = []
            for nid, _ in SAMPLE:
                d = docs[db_key].get(nid)
                s, v = deep_get(d, vp)
                vals.append((s, v))
            distinct = set()
            for s, v in vals:
                if s == "absent":
                    distinct.add(("ABSENT",))
                else:
                    try:
                        distinct.add(("present", json.dumps(v, default=str, sort_keys=True)))
                    except Exception:
                        distinct.add(("present", repr(v)))
            if len(distinct) > 1:
                flag.append(f"⚠ NON-UNIFORM `{vp}` in `{db_label}` across the 5 sampled schools: distinct values = {distinct}")
    if flag:
        for f in flag:
            emit(f)
        emit("")
    else:
        emit("Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.")
        emit("")

    # ----- Section B: source -----
    header("Section B — Source file or API endpoint", 3)
    for line in section_b:
        emit(line)
    emit("")

    # ----- Section C: pipeline filter -----
    header("Section C — Pipeline filter / ingestion logic", 3)
    for line in section_c:
        emit(line)
    emit("")

    # ----- Vintage triangulation -----
    header("Vintage triangulation", 3)
    emit("| Source | Vintage |")
    emit("|---|---|")
    # Empirical from MongoDB: collapse from in_block_vintage_paths per db
    def empirical_summary(db_key, db_label):
        summary_parts = []
        for vp in in_block_vintage_paths:
            distinct = set()
            any_present = False
            for nid, _ in SAMPLE:
                d = docs[db_key].get(nid)
                s, v = deep_get(d, vp)
                if s == "present":
                    any_present = True
                    try:
                        distinct.add(json.dumps(v, default=str, sort_keys=True))
                    except Exception:
                        distinct.add(repr(v))
            if not any_present:
                summary_parts.append(f"`{vp}` ABSENT in all 5")
            elif len(distinct) == 1:
                summary_parts.append(f"`{vp}` = {next(iter(distinct))}")
            else:
                summary_parts.append(f"`{vp}` NON-UNIFORM: {distinct}")
        return "; ".join(summary_parts) or "—"

    emit(f"| Empirical (`schooldaylight`) | {empirical_summary('hist', 'hist')} |")
    emit(f"| Empirical (`schooldaylight_experiment`) | {empirical_summary('exp', 'exp')} |")
    emit(f"| Encoded by pipeline / ingestion script | {section_c[0] if section_c else '—'} |")
    emit(f"| Inferred from documentation | {doc_vintage} |")
    emit("")


# ============================================================================
# PER-VARIABLE BLOCKS
# ============================================================================

emit("# Phase 2R — Vintage inventory: remaining 16 variables")
emit("")
emit("Read-only side-by-side inventory across `schooldaylight` (historical) and "
     "`schooldaylight_experiment` (operating Phase 3R artifacts) for the 16 v1 "
     "similarity variables not covered in the teacher_experience round.")
emit("")
emit("Sample schools (same 5 used for teacher_experience):")
for nid, name in SAMPLE:
    emit(f"- `{nid}` — {name}")
emit("")
emit("Format per variable: Section A (literal sample values, side-by-side), "
     "vintage stamp table, Section B (source), Section C (pipeline filter), "
     "vintage triangulation (empirical / pipeline-encoded / documentation-inferred). "
     "Non-uniform vintage stamps within the 5-school sample are flagged in place.")
emit("")

# ----------------------------------------------------------------------------
# 1. Enrollment (membership)
# ----------------------------------------------------------------------------
render_variable(
    num=1,
    name="Enrollment (membership)",
    schema_path="enrollment.total",
    prov_pattern="File-sourced (CCD WA Membership CSV on disk).",
    section_b=[
        "- File: `data/ccd_wa_membership.csv` (file size 180 KB, mtime 2026-02-21 15:40).",
        "- Header: `ncessch,school_name,total_enrollment,american_indian,asian,"
        "black,hispanic,pacific_islander,two_or_more,white,not_specified,male,female`.",
        "- The CSV is the Phase 1 pre-aggregated school-level CCD membership "
        "extract (one row per NCESSCH).",
        "- No SchoolYear column in the file; vintage is documented only in the "
        "pipeline script and ingestion metadata.",
        "- Underlying federal file on disk: `WA-raw/federal/ccd_sch_052_2425_l_1a_073025.csv` "
        "(2.3 GB, December 2025 mtime). This is the 2024-25 CCD Membership "
        "national release — but the pre-aggregated `data/ccd_wa_membership.csv` "
        "consumed by the pipeline was produced earlier (Feb 2026 mtime) and is "
        "stamped 2023-24 by the loader. The 2024-25 national release is present "
        "on disk but not yet wired into the pipeline.",
    ],
    section_c=[
        "Pipeline 02 hard-codes `\"year\": \"2023-24\"` in the enrollment block "
        "(`pipeline/02_load_enrollment.py` line 61). No year filter on the file "
        "itself — the file has only one school-level enrollment per NCESSCH.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 1: \"OSPI Report Card 2023-24 "
                "(already ingested)\". `build_log.md` discusses CCD 2023-24 for "
                "enrollment. Note: matrix row 1 says OSPI but pipeline uses CCD.",
    in_block_vintage_paths=["enrollment.year"],
    extra_context_paths=None,
)

# ----------------------------------------------------------------------------
# 2. Chronic absenteeism rate (attendance substitute)
# ----------------------------------------------------------------------------
render_variable(
    num=2,
    name="Chronic absenteeism rate (substituted for attendance rate)",
    schema_path="derived.chronic_absenteeism_pct",
    prov_pattern="Derived (= 1 - academics.attendance.regular_attendance_pct, "
                 "which is itself file-sourced from OSPI SQSS CSV on disk).",
    section_b=[
        "- File: `WA-raw/ospi/Report_Card_SQSS_for_2024-25.csv` (244 MB, mtime "
        "2026-02-21 14:13).",
        "- File's `SchoolYear` column has a single distinct value: `\"2025\"` "
        "(not `\"2024-25\"`).",
        "- File's `DataAsOf` column sample value: `\"2026 Jan 06 12:00:00 AM\"`.",
        "- Filter applied at read: `OrganizationLevel == \"School\"`, "
        "`StudentGroupType == \"AllStudents\"` (note: SQSS uses \"All Students\" "
        "with space; see `pipeline/04_load_ospi_academics.py:255`), "
        "`GradeLevel == \"All Grades\"`.",
    ],
    section_c=[
        "`pipeline/04_load_ospi_academics.py:load_sqss` loads SQSS rows and "
        "stamps `attendance[\"year\"] = \"2024-25\"` (line 281). "
        "`pipeline/12_compute_ratios.py:169` derives "
        "`derived.chronic_absenteeism_pct = 1.0 - academics.attendance.regular_attendance_pct`. "
        "No standalone year filter on the chronic absenteeism field — it "
        "inherits the SQSS file's vintage.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 2: \"OSPI Report Card 2023-24, "
                "school-level\". Note: pipeline uses SQSS 2024-25 file; the matrix "
                "row claim of \"2023-24\" is documentation drift.",
    in_block_vintage_paths=[
        "academics.attendance.year",
        # there's no per-doc vintage stamp on derived.chronic_absenteeism_pct itself
    ],
    extra_context_paths=[
        "academics.attendance.regular_attendance_pct",
        "academics.attendance.numerator",
        "academics.attendance.denominator",
    ],
)

# ----------------------------------------------------------------------------
# 3. Graduation rate (4-year)
# ----------------------------------------------------------------------------
render_variable(
    num=3,
    name="Graduation rate, 4-year (HS-only)",
    schema_path="graduation_rate.cohort_4yr",
    prov_pattern="API-sourced with no cache (data.wa.gov SODA endpoint "
                 "76iv-8ed4; raw API rows never persisted).",
    section_b=[
        "- API endpoint: `https://data.wa.gov/resource/76iv-8ed4.json`.",
        "- No cached source file exists on disk. Grep for `76iv-8ed4` outside "
        "logs/docs returns no JSON/CSV/parquet/pickle.",
        "- The fetch occurred 2026-05-05 00:19 UTC per "
        "`logs/phase3r_api_ingestion_2026-05-04_17-19-03.log`: 3,007 rows pulled.",
        "- No DataAsOf-equivalent metadata is preserved from the SODA response.",
    ],
    section_c=[
        "Filter encoded in `phases/phase-3R/experiment/_run_api_ingestion.py` "
        "lines 165-169: `organizationlevel=School`, `schoolyear=2023-24`, "
        "`studentgroup=All Students`. There is no production-pipeline loader "
        "for graduation rate; the Phase 3R sandbox script is the only loader. "
        "The leading-zero zfill bug was patched in-source per commit "
        "`97a342f` / `a0de7ec`-class fix; runtime patch via "
        "`_patch_task1_zfill.py` applied to existing experiment data.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 3: \"data.wa.gov Report Card "
                "Graduation 2023-24, school-level all-students\".",
    in_block_vintage_paths=[
        "graduation_rate.metadata.dataset_year",
        "graduation_rate.metadata.source",
        "graduation_rate.metadata.fetch_timestamp",
    ],
    extra_context_paths=[
        "graduation_rate.cohort_4yr",
        "graduation_rate.cohort_5yr",
        "graduation_rate.metadata.not_applicable_reason",
    ],
)

# ----------------------------------------------------------------------------
# 4. FRL rate
# ----------------------------------------------------------------------------
render_variable(
    num=4,
    name="FRL (Low Income) rate",
    schema_path="demographics.frl_pct",
    prov_pattern="File-sourced (OSPI Report Card Enrollment CSV on disk); "
                 "ratio computed in-loader as Low_Income / All_Students.",
    section_b=[
        "- File: `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` "
        "(7.0 MB, mtime 2026-02-21 13:36).",
        "- File's `SchoolYear` column has a single distinct value: `\"2023-24\"`.",
        "- File's `DataAsOf` column has a single distinct value: "
        "`\"2024 Jun 18 12:00:00 AM\"`.",
        "- This single file is the source for variables 4, 6, 7, 8, and 16 "
        "(FRL, Homeless, ELL, Migrant, SPED) — confirmed by `pipeline/03_load_ospi_enrollment.py`.",
    ],
    section_c=[
        "`pipeline/03_load_ospi_enrollment.py` hard-codes the filename and "
        "stamps `demographics[\"year\"] = \"2023-24\"` (line 89). Filter: "
        "`OrganizationLevel == \"School\"` AND `GradeLevel == \"All Grades\"` "
        "(line 61). FRL ratio is computed in-loader as "
        "`frl_count / all_students_val` (line 98).",
    ],
    doc_vintage="`variable_decision_matrix.md` row 4: \"OSPI 2023-24 (already "
                "ingested)\".",
    in_block_vintage_paths=["demographics.year"],
    extra_context_paths=[
        "demographics.frl_count",
        "demographics.ospi_total",
    ],
)

# ----------------------------------------------------------------------------
# 5. Race composition (% non-white)
# ----------------------------------------------------------------------------
render_variable(
    num=5,
    name="Minority rate (% non-white)",
    schema_path="derived.race_pct_non_white",
    prov_pattern="Derived (computed in Phase 3R sandbox = 1 − "
                 "enrollment.by_race.white / enrollment.total; upstream is "
                 "the CCD-sourced enrollment block from variable 1).",
    section_b=[
        "- Upstream values come from `data/ccd_wa_membership.csv` "
        "(see Variable 1 Section B).",
        "- No standalone source file for this derived rate.",
    ],
    section_c=[
        "Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` "
        "Task 4 (lines 405-409): "
        "`race_pct = 1.0 - (enrollment.by_race.white / enrollment.total)`. "
        "Vintage stamp on the `_meta` block stamps "
        "`\"source\": \"1 - (enrollment.by_race.white / enrollment.total) "
        "(CCD 2023-24)\"`. No year filter; inherits enrollment vintage.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 5: \"OSPI 2023-24 (already "
                "ingested), single percent non-white\". Note: matrix says OSPI "
                "but the actual upstream is CCD enrollment (build log clarified).",
    in_block_vintage_paths=[
        "derived.race_pct_non_white_meta.source",
        "derived.race_pct_non_white_meta.compute_timestamp",
    ],
    extra_context_paths=[
        "enrollment.by_race.white",
        "enrollment.total",
        "enrollment.year",
    ],
)

# ----------------------------------------------------------------------------
# 6. Homeless rate
# ----------------------------------------------------------------------------
render_variable(
    num=6,
    name="Homeless rate",
    schema_path="derived.homelessness_pct",
    prov_pattern="Derived (computed in Phase 3R sandbox = homeless_count / "
                 "ospi_total; upstream is the OSPI Enrollment CSV used for "
                 "variable 4).",
    section_b=[
        "- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` "
        "(see Variable 4 Section B).",
        "- No standalone source file for this derived rate.",
    ],
    section_c=[
        "Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 "
        "(line 404): `homeless_pct = safe_ratio(demo.get('homeless_count'), "
        "ospi_total)`. `_meta` stamp identifies upstream as "
        "`demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)`.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 6: \"OSPI Report Card "
                "2023-24, school-level\".",
    in_block_vintage_paths=[
        "derived.homelessness_pct_meta.source",
        "derived.homelessness_pct_meta.compute_timestamp",
    ],
    extra_context_paths=[
        "demographics.homeless_count",
        "demographics.ospi_total",
    ],
)

# ----------------------------------------------------------------------------
# 7. EL (LEP) rate
# ----------------------------------------------------------------------------
render_variable(
    num=7,
    name="EL / LEP rate",
    schema_path="derived.ell_pct",
    prov_pattern="Derived (ell_count / ospi_total); upstream is OSPI "
                 "Enrollment CSV used for variable 4.",
    section_b=[
        "- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` "
        "(see Variable 4 Section B).",
        "- No standalone source file for this derived rate.",
    ],
    section_c=[
        "Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` "
        "Task 4 (line 401): `ell_pct = safe_ratio(demo.get('ell_count'), "
        "ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 7: \"OSPI 2023-24 "
                "(already ingested); WA term is EL/ML\".",
    in_block_vintage_paths=[
        "derived.ell_pct_meta.source",
        "derived.ell_pct_meta.compute_timestamp",
    ],
    extra_context_paths=[
        "demographics.ell_count",
        "demographics.ospi_total",
    ],
)

# ----------------------------------------------------------------------------
# 8. Migrant rate
# ----------------------------------------------------------------------------
render_variable(
    num=8,
    name="Migrant rate",
    schema_path="derived.migrant_pct",
    prov_pattern="Derived (migrant_count / ospi_total); upstream is OSPI "
                 "Enrollment CSV used for variable 4.",
    section_b=[
        "- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` "
        "(see Variable 4 Section B).",
        "- No standalone source file for this derived rate.",
    ],
    section_c=[
        "Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` "
        "Task 4 (line 403): `migrant_pct = safe_ratio(demo.get('migrant_count'), "
        "ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 8: \"OSPI 2023-24 "
                "(already ingested)\".",
    in_block_vintage_paths=[
        "derived.migrant_pct_meta.source",
        "derived.migrant_pct_meta.compute_timestamp",
    ],
    extra_context_paths=[
        "demographics.migrant_count",
        "demographics.ospi_total",
    ],
)

# ----------------------------------------------------------------------------
# 10. Median household income (Census ACS)
# ----------------------------------------------------------------------------
render_variable(
    num=10,
    name="Median household income (Census ACS B19013_001E)",
    schema_path="census_acs.median_household_income.value",
    prov_pattern="API-sourced with no cache (Census ACS 5-year API endpoint; "
                 "raw API rows never persisted).",
    section_b=[
        "- API endpoint: `https://api.census.gov/data/2023/acs/acs5?get=NAME,"
        "B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,"
        "B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53`.",
        "- This single fetch supplies B19013 (median household income), B19301 "
        "(per capita income), B19083 (Gini), and B01003 (total population) for "
        "every WA unified school district.",
        "- No on-disk cache of the API response. `VINTAGE` constant in the "
        "loader is the string `\"acs5_2019_2023\"` — i.e. the ACS 5-year "
        "release covering 2019-2023, accessed via the `/data/2023/...` URL.",
    ],
    section_c=[
        "`phases/phase-3R/experiment/_run_acs_ingestion.py` line 57: "
        "`VINTAGE = \"acs5_2019_2023\"`. Endpoint URL fetched once at run start "
        "(line 165). Filter is geographic only (`state:53`, all WA unified school "
        "districts). No year filter beyond the API path itself.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 19: \"Census ACS B19013_001E "
                "at district geography (already ingested)\". No vintage year "
                "stated in the matrix.",
    in_block_vintage_paths=[
        "census_acs._meta.vintage",
        "census_acs._meta.acs_base_api_url",
        "census_acs._meta.fetched_at",
        "census_acs.median_household_income.census_code",
    ],
    extra_context_paths=[
        "census_acs.median_household_income.moe",
        "census_acs._meta.district_geoid",
        "census_acs._meta.unmatched_reason",
    ],
)

# ----------------------------------------------------------------------------
# 11. Gini index
# ----------------------------------------------------------------------------
render_variable(
    num=11,
    name="Gini index (Census ACS B19083_001E)",
    schema_path="census_acs.gini_index.value",
    prov_pattern="API-sourced with no cache (same Census ACS endpoint as "
                 "variable 10).",
    section_b=[
        "- Same endpoint as variable 10 (`B19083_001E` is one of the base "
        "table fields in the single ACS fetch).",
    ],
    section_c=[
        "Same script as variable 10 (`_run_acs_ingestion.py`). Geographic-only "
        "filter (`state:53`). VINTAGE = `acs5_2019_2023`.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 21: \"Census ACS B19083_001E "
                "(already ingested)\".",
    in_block_vintage_paths=[
        "census_acs._meta.vintage",
        "census_acs.gini_index.census_code",
    ],
    extra_context_paths=[
        "census_acs.gini_index.moe",
    ],
)

# ----------------------------------------------------------------------------
# 12. Labor force participation rate
# ----------------------------------------------------------------------------
render_variable(
    num=12,
    name="Labor force participation rate, 16+ (Census ACS S2301_C02_001E)",
    schema_path="census_acs.labor_force_participation_rate_16plus.value",
    prov_pattern="API-sourced with no cache (Census ACS subject-table endpoint).",
    section_b=[
        "- API endpoint (subject tables): `https://api.census.gov/data/2023/"
        "acs/acs5/subject?get=NAME,S1501_C02_015E,S1501_C02_015M,"
        "S2301_C02_001E,S2301_C02_001M,S2301_C04_001E,S2301_C04_001M"
        "&for=school+district+(unified):*&in=state:53`.",
        "- This subject-table fetch supplies S1501 (bachelor's pct), S2301 LFP, "
        "and S2301 unemployment.",
    ],
    section_c=[
        "Same script as variable 10. VINTAGE = `acs5_2019_2023`.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 23: \"Census ACS S2301 "
                "(already ingested)\".",
    in_block_vintage_paths=[
        "census_acs._meta.vintage",
        "census_acs.labor_force_participation_rate_16plus.census_code",
    ],
    extra_context_paths=[
        "census_acs.labor_force_participation_rate_16plus.moe",
    ],
)

# ----------------------------------------------------------------------------
# 13. Unemployment rate
# ----------------------------------------------------------------------------
render_variable(
    num=13,
    name="Unemployment rate, 16+ (Census ACS S2301_C04_001E)",
    schema_path="census_acs.unemployment_rate_16plus.value",
    prov_pattern="API-sourced with no cache (same Census ACS subject endpoint "
                 "as variable 12).",
    section_b=[
        "- Same endpoint as variable 12.",
    ],
    section_c=[
        "Same script as variable 10. VINTAGE = `acs5_2019_2023`.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 24: \"Census ACS S2301 "
                "(already ingested)\".",
    in_block_vintage_paths=[
        "census_acs._meta.vintage",
        "census_acs.unemployment_rate_16plus.census_code",
    ],
    extra_context_paths=[
        "census_acs.unemployment_rate_16plus.moe",
    ],
)

# ----------------------------------------------------------------------------
# 14. Land area
# ----------------------------------------------------------------------------
render_variable(
    num=14,
    name="Land area, sq miles (TIGER 2023 Gazetteer ALAND_SQMI)",
    schema_path="census_acs.land_area_sq_miles.value",
    prov_pattern="API-sourced with no cache (TIGER 2023 Gazetteer ZIP — "
                 "the loader downloads the ZIP, extracts the TXT in memory, "
                 "and discards both).",
    section_b=[
        "- File URL: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
        "2023_Gazetteer/2023_Gaz_unsd_national.zip`.",
        "- Downloaded into memory at run time (`_run_acs_ingestion.py` lines "
        "195-201). Neither the ZIP nor the extracted `.txt` is persisted to disk.",
        "- Inside the ZIP: tab-delimited national Unified School District file; "
        "filtered to `USPS == \"WA\"` in-memory.",
    ],
    section_c=[
        "Same script as variable 10. The land_area field is stored under "
        "`census_acs.land_area_sq_miles` with `source = \"TIGER 2023 Unified "
        "Gazetteer ALAND_SQMI\"`. No year filter at fetch — the URL is "
        "year-specific (`2023_Gazetteer`).",
    ],
    doc_vintage="`variable_decision_matrix.md` row 26: \"TIGER Gazetteer "
                "ALAND (already ingested)\". No vintage year stated in the matrix.",
    in_block_vintage_paths=[
        "census_acs._meta.tiger_gazetteer_url",
        "census_acs.land_area_sq_miles.source",
    ],
    extra_context_paths=None,
)

# ----------------------------------------------------------------------------
# 15. Population density
# ----------------------------------------------------------------------------
render_variable(
    num=15,
    name="Population density, per sq mile (B01003 / ALAND_SQMI)",
    schema_path="census_acs.population_density_per_sq_mile.value",
    prov_pattern="Derived (computed in-loader as B01003_001E / "
                 "TIGER ALAND_SQMI; both upstream values are API-sourced "
                 "without cache).",
    section_b=[
        "- Upstream: B01003_001E from ACS base fetch (variable 10); "
        "ALAND_SQMI from TIGER 2023 Gazetteer (variable 14).",
    ],
    section_c=[
        "Same script as variable 10. Computed at lines 254-256 of "
        "`_run_acs_ingestion.py`: "
        "`pop_density = pop_var['value'] / aland`. Stored with field "
        "`computed_from = \"total_population / land_area_sq_miles\"`.",
    ],
    doc_vintage="`variable_decision_matrix.md` row 27: \"Computed B01003 / "
                "ALAND (already ingested)\". Note: relies on ACS 2019-2023 "
                "numerator and TIGER 2023 denominator — mixed-year derivation.",
    in_block_vintage_paths=[
        "census_acs.population_density_per_sq_mile.computed_from",
        "census_acs._meta.vintage",
    ],
    extra_context_paths=None,
)

# ----------------------------------------------------------------------------
# 16. SPED percentage
# ----------------------------------------------------------------------------
render_variable(
    num=16,
    name="SPED percentage (addition from Texas)",
    schema_path="derived.sped_pct",
    prov_pattern="Derived (sped_count / ospi_total); upstream is OSPI "
                 "Enrollment CSV used for variable 4.",
    section_b=[
        "- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` "
        "(see Variable 4 Section B).",
    ],
    section_c=[
        "Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` "
        "Task 4 (line 402): `sped_pct = safe_ratio(demo.get('sped_count'), "
        "ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.",
    ],
    doc_vintage="`variable_decision_matrix.md` row A1: \"OSPI 2023-24 "
                "(already ingested)\".",
    in_block_vintage_paths=[
        "derived.sped_pct_meta.source",
        "derived.sped_pct_meta.compute_timestamp",
    ],
    extra_context_paths=[
        "demographics.sped_count",
        "demographics.ospi_total",
    ],
)

# ----------------------------------------------------------------------------
# 17. Average teacher salary
# ----------------------------------------------------------------------------
render_variable(
    num=17,
    name="Average teacher salary, base per 1.0 FTE (S-275-derived)",
    schema_path="teacher_salary.average_base_per_fte",
    prov_pattern="File-sourced (OSPI Personnel Summary XLSX on disk).",
    section_b=[
        "- File: `phases/phase-3R/ingestion_data/table_15-40_school_district_"
        "personnel_summary_profiles_2023-24.xlsx` (note: also exists alongside "
        "the 2025-26 preliminary file in the same directory).",
        "- Two candidate files on disk: the 2023-24 final and the 2025-26 "
        "preliminary. Phase 3R's salary loader was rerun on 2026-05-05 "
        "(`_run_salary_reingestion_2023-24.py`) to vintage-align downward to "
        "2023-24 final per the May 5 R10 decision.",
        "- Sheet: `Table19` (no space in 2023-24 file; with space in 2025-26 "
        "file).",
        "- No SchoolYear column in the workbook; vintage is the filename and "
        "the loader's `YEAR_STR` constant.",
    ],
    section_c=[
        "`phases/phase-3R/experiment/_run_salary_reingestion_2023-24.py` line 217: "
        "`YEAR_STR = \"2023-24 final\"`. Reads `Table19` sheet (line 105-107) "
        "and parses base salary (col index 5). Each school inherits its "
        "district's average via `metadata.ospi_district_code`. "
        "Note: an earlier loader `_run_salary_ingestion.py` used the 2025-26 "
        "preliminary file and stamped `dataset_year = \"2025-26 preliminary\"`; "
        "the May 5 re-ingestion replaced that with 2023-24 final values across "
        "all docs.",
    ],
    doc_vintage="`variable_decision_matrix.md` rows 16-18 and A2: \"OSPI "
                "Personnel Summary Reports 2023-24, Table 19 (Average Base "
                "Salary per 1.0 FTE), district-level\".",
    in_block_vintage_paths=[
        "teacher_salary.metadata.dataset_year",
        "teacher_salary.metadata.source",
        "teacher_salary.metadata.sheet",
    ],
    extra_context_paths=[
        "teacher_salary.average_base_per_fte",
        "teacher_salary.district_code",
    ],
)

# ----------------------------------------------------------------------------
# Final summary
# ----------------------------------------------------------------------------
emit("---")
emit("")
emit("Sanity check: 16 variables emitted above; teacher_experience (variable 9) "
     "was covered in the prior round. Total = 17, matching `variable_decision_matrix.md` "
     "v1 set.")
emit("")

with open(OUT_PATH, "w") as f:
    f.write("\n".join(out))

print(f"Wrote {OUT_PATH}")
print(f"{len(out)} lines.")
