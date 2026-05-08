"""
_run_api_ingestion.py — Phase 3R Prompt 2 bulk execution.

PURPOSE: Ingest graduation rates (76iv-8ed4) and teacher experience (bdjb-hg6t)
         from data.wa.gov, compute five derived rates from existing counts, run
         the chronic-absenteeism null-overlap diagnostic, and write provenance
         metadata at document root.
INPUTS:  MongoDB Atlas (schooldaylight_experiment.schools, READ+WRITE),
         data.wa.gov SODA APIs (read).
OUTPUTS: Updates `census_acs.*` is NOT touched. New fields written:
         graduation_rate.*, teacher_experience.*, derived.{ell|sped|migrant|
         homelessness|race_pct_non_white}_pct (+ _meta), metadata.phase_3r_*.

GUARD:   Refuses to write to any database whose name does not contain
         "experiment". Tasks 2 (teacher qualification / masters) was dropped
         per builder Path A — see the deliverable for the v2-path note.
IDEMPOTENT: every write is a $set on a specific dotted path; rerunning
         overwrites cleanly. No insertOne / deleteMany / drop_collection.
"""

import datetime as dt
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import yaml
from collections import Counter, defaultdict
from statistics import mean, median, pstdev

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient, UpdateOne

# ---------------------------------------------------------------------------
# Logging — timestamped file in logs/, complete English sentences.
# ---------------------------------------------------------------------------
TS = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = "/Users/oriandaleigh/school-daylight/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"phase3r_api_ingestion_{TS}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("p3r_ingest")

NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
OUT_DIR = "/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment"
OUT_FILE = os.path.join(OUT_DIR, "api_ingestion_2026-05-04.md")

# ---------------------------------------------------------------------------
# Connect — experiment db only.
# ---------------------------------------------------------------------------
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client.get_default_database()
assert "experiment" in db.name, \
    f"Refusing to write — '{db.name}' is not an experiment db."
log.info(f"Connected to '{db.name}'. Writes proceed.")

doc_count = db["schools"].count_documents({})
log.info(f"Document count: {doc_count}.")

# ---------------------------------------------------------------------------
# Pull every school's id + the fields we need for joining + computing rates.
# ---------------------------------------------------------------------------
log.info("Reading all school docs (projected fields only)...")
PROJ = {
    "_id": 1, "name": 1, "is_charter": 1, "school_type": 1,
    "level": 1, "derived.level_group": 1,
    "grade_span.low": 1, "grade_span.high": 1,
    "metadata.ospi_district_code": 1, "metadata.ospi_school_code": 1,
    "demographics.ell_count": 1, "demographics.sped_count": 1,
    "demographics.migrant_count": 1, "demographics.homeless_count": 1,
    "demographics.ospi_total": 1,
    "enrollment.total": 1, "enrollment.by_race.white": 1,
    "derived.chronic_absenteeism_pct": 1,
    "census_acs._meta.unmatched_reason": 1,
}
schools = list(db["schools"].find({}, PROJ))
log.info(f"Loaded {len(schools)} school docs into memory.")

# Build OSPI-key → _id map (district, school) → _id
def ospi_key(doc):
    md = doc.get("metadata", {}) or {}
    dc = md.get("ospi_district_code")
    sc = md.get("ospi_school_code")
    if dc and sc:
        return (dc.strip(), sc.strip())
    return None

ospi_to_id = {}
ospi_collisions = []
no_ospi_codes = []
for d in schools:
    k = ospi_key(d)
    if k is None:
        no_ospi_codes.append(d["_id"])
        continue
    if k in ospi_to_id:
        ospi_collisions.append((k, d["_id"], ospi_to_id[k]))
    ospi_to_id[k] = d["_id"]
log.info(f"OSPI (district, school) -> NCESSCH map size: {len(ospi_to_id)}.")
if no_ospi_codes:
    log.warning(f"{len(no_ospi_codes)} school docs lack OSPI codes (district or school). "
                f"Sample: {no_ospi_codes[:5]}")
if ospi_collisions:
    log.warning(f"{len(ospi_collisions)} OSPI-key collisions among schools. "
                f"Sample: {ospi_collisions[:3]}")

# is-high-school predicate. HS-eligible if level_group=="High" OR grade_span.high=="12".
def is_high_school(doc):
    lg = (doc.get("derived") or {}).get("level_group")
    gh = (doc.get("grade_span") or {}).get("high")
    return lg == "High" or gh == "12"

# ---------------------------------------------------------------------------
# Fetch helper for SODA APIs with simple paging.
# ---------------------------------------------------------------------------
def soda_fetch_all(base_url, where_params, page_size=10000, max_pages=500,
                    label=""):
    """Page through a Socrata SODA API until no more rows. Returns list of dicts."""
    all_rows = []
    offset = 0
    qp = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in where_params.items())
    for _ in range(max_pages):
        url = f"{base_url}?{qp}&$limit={page_size}&$offset={offset}"
        log.info(f"  fetching {label} offset={offset} ...")
        req = urllib.request.Request(url, headers={"User-Agent":
                                     "school-daylight-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            rows = json.loads(r.read())
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    log.info(f"  total {label} rows fetched: {len(all_rows)}")
    return all_rows

def to_float(v):
    """Best-effort float. Handles 'NULL', None, '25.9%', '0.4', etc."""
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.upper() == "NULL":
        return None
    s = s.rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None

# ===========================================================================
# TASK 1 — Graduation rates (76iv-8ed4)
# ===========================================================================
log.info("=== Task 1: graduation rates ===")
GRAD_BASE = "https://data.wa.gov/resource/76iv-8ed4.json"
grad_rows = soda_fetch_all(
    GRAD_BASE,
    {"organizationlevel": "School",
     "schoolyear": "2023-24",
     "studentgroup": "All Students"},
    label="graduation")

# Group by OSPI key, split by cohort
grad_by_key = defaultdict(dict)  # (district_code, school_code) -> {"4yr": rate, "5yr": rate}
unjoined_rows = 0
for row in grad_rows:
    # RULE: LEADING-ZERO BUG — 76iv-8ed4 publishes districtcode as variable
    # width (4 or 5 chars depending on whether the leading zero is stripped
    # for districts in counties 01-09). Schema's metadata.ospi_district_code
    # is uniformly 5-char zero-padded; zfill(5) restores the convention.
    # Same pattern as commit 97a342f / a0de7ec in the production pipeline.
    # Originally fixed at runtime via _patch_task1_zfill.py; this in-source
    # fix prevents the bug from reappearing on any future re-ingest.
    dc = (row.get("districtcode") or "").strip().zfill(5)
    sc = (row.get("schoolcode") or "").strip()
    cohort = (row.get("cohort") or "").strip()
    rate_str = row.get("graduationrate")
    rate = to_float(rate_str)
    if rate is not None and rate > 1.0:
        rate = rate / 100.0  # defensive: should already be 0-1
    if cohort == "Four Year":
        grad_by_key[(dc, sc)]["4yr"] = rate
    elif cohort == "Five Year":
        grad_by_key[(dc, sc)]["5yr"] = rate
    if (dc, sc) not in ospi_to_id:
        unjoined_rows += 1
log.info(f"Graduation: {len(grad_by_key)} unique (district, school) keys in source.")
log.info(f"Graduation: {unjoined_rows} source rows did not match any school in experiment db.")

# Build per-school graduation_rate payload
task1_ops = []
task1_hs_count = 0
task1_hs_with_data = 0
task1_non_hs = 0
task1_4yr_vals = []
task1_5yr_vals = []
for d in schools:
    nid = d["_id"]
    is_hs = is_high_school(d)
    if not is_hs:
        payload = {
            "cohort_4yr": None,
            "cohort_5yr": None,
            "metadata": {
                "source": "data.wa.gov 76iv-8ed4",
                "dataset_year": "2023-24",
                "fetch_timestamp": NOW_ISO,
                "not_applicable_reason": "grade_span_not_high_school",
            },
        }
        task1_non_hs += 1
    else:
        task1_hs_count += 1
        k = ospi_key(d)
        rates = grad_by_key.get(k, {})
        v4 = rates.get("4yr")
        v5 = rates.get("5yr")
        if v4 is not None or v5 is not None:
            task1_hs_with_data += 1
            if v4 is not None:
                task1_4yr_vals.append(v4)
            if v5 is not None:
                task1_5yr_vals.append(v5)
        payload = {
            "cohort_4yr": v4,
            "cohort_5yr": v5,
            "metadata": {
                "source": "data.wa.gov 76iv-8ed4",
                "dataset_year": "2023-24",
                "fetch_timestamp": NOW_ISO,
                "not_applicable_reason": None,
            },
        }
    task1_ops.append(UpdateOne({"_id": nid},
                               {"$set": {"graduation_rate": payload}}))

log.info(f"Task 1: HS-eligible schools={task1_hs_count}, "
         f"with at least one cohort rate={task1_hs_with_data}, "
         f"non-HS (null with reason)={task1_non_hs}")

# ===========================================================================
# TASK 3 — Teacher experience (bdjb-hg6t), bin-midpoint weighted average
# ===========================================================================
log.info("=== Task 3: teacher experience ===")
TE_BASE = "https://data.wa.gov/resource/bdjb-hg6t.json"
te_rows = soda_fetch_all(
    TE_BASE,
    {"organizationlevel": "School", "schoolyear": "2024-25"},
    label="teacher_experience")

def bin_midpoint(label):
    """Each bin's published-range midpoint. 'Not Reported' -> None.
    Per builder ruling 2026-05-04 (Finding 1, Option a): no cap; use the
    arithmetic midpoint of every published finite-range bin."""
    if not label:
        return None
    s = label.strip()
    if s.lower() == "not reported":
        return None
    m = re.match(r"^\s*([\d.]+)\s*[-–—]\s*([\d.]+)\s*$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    # Open-ended bin (defensive — none observed in 2024-25 data)
    if "+" in s or "or more" in s.lower():
        return 25.0
    return None

# Group bin rows by (district, school)
te_by_key = defaultdict(list)
te_unjoined = 0
for row in te_rows:
    dc = (row.get("leacode") or "").strip()
    sc = (row.get("schoolcode") or "").strip()
    te_by_key[(dc, sc)].append(row)
    if (dc, sc) not in ospi_to_id:
        te_unjoined += 1
log.info(f"Teacher exp: {len(te_by_key)} unique (district, school) keys in source.")
log.info(f"Teacher exp: {te_unjoined} rows did not match a school in experiment db.")

def compute_avg_years(bin_rows):
    """Bin-midpoint weighted average, renormalized to reported-bin weight sum.
    Returns (avg_years, total_reported_weight, unreported_pct, num_rows).
    Builder ruling 2026-05-04 (Finding 2, Option b): drop Not Reported from
    both numerator and denominator; assume unreported teachers follow the
    same experience distribution as reported."""
    total_weighted = 0.0
    reported_weight = 0.0
    unreported_pct = 0.0
    num_rows = len(bin_rows)
    for row in bin_rows:
        bin_lbl = row.get("experiencebin") or ""
        pct = to_float(row.get("teacherpercent"))
        if pct is None:
            continue
        mp = bin_midpoint(bin_lbl)
        if mp is None:
            unreported_pct += pct
            continue
        # pct is in 0-100 scale per the API
        total_weighted += mp * (pct / 100.0)
        reported_weight += pct / 100.0
    if reported_weight <= 0:
        return None, reported_weight, unreported_pct, num_rows
    avg = total_weighted / reported_weight
    return avg, reported_weight, unreported_pct, num_rows

task3_ops = []
task3_with_data = 0
task3_no_rows = 0
task3_avg_vals = []
task3_high_unreported = 0
for d in schools:
    nid = d["_id"]
    k = ospi_key(d)
    rows = te_by_key.get(k, []) if k else []
    avg, rep_w, unrep, n_rows = compute_avg_years(rows)
    null_reason = None
    if n_rows == 0:
        null_reason = "no_bin_rows"
        task3_no_rows += 1
    elif avg is None:
        null_reason = "no_reported_bins"

    payload = {
        "average_years_derived": round(avg, 2) if avg is not None else None,
        "metadata": {
            "source": "data.wa.gov bdjb-hg6t",
            "dataset_year": "2024-25",
            "derivation": ("Bin-midpoint weighted average computed from "
                           "OSPI's binned teacher experience distribution. "
                           "Each bin's midpoint is the arithmetic midpoint "
                           "of its published range (e.g., 25.0-29.9 → 27.45). "
                           "Not Reported percentages are excluded from both "
                           "numerator and denominator; the weighted sum is "
                           "renormalized to the sum of reported-bin weights, "
                           "assuming unreported teachers follow the same "
                           "experience distribution as reported teachers. "
                           "Documented derivation, not a direct port of "
                           "Nebraska's published-average variable."),
            "not_reported_handling": ("renormalized to weight sum of "
                                      "reported bins; assumes unreported "
                                      "teachers follow same experience "
                                      "distribution as reported"),
            "fetch_timestamp": NOW_ISO,
            "unreported_pct": round(unrep, 2),
            "high_unreported_flag": unrep > 10.0,
            "null_reason": null_reason,
        },
    }
    if avg is not None:
        task3_with_data += 1
        task3_avg_vals.append(avg)
    if unrep > 10.0:
        task3_high_unreported += 1
    task3_ops.append(UpdateOne({"_id": nid},
                               {"$set": {"teacher_experience": payload}}))
log.info(f"Task 3: schools with computed avg_years={task3_with_data}, "
         f"no_bin_rows={task3_no_rows}, high_unreported (>10%)={task3_high_unreported}")

# ===========================================================================
# TASK 4 — Compute rates from existing counts.
# ===========================================================================
log.info("=== Task 4: derived rates ===")

# Sanity check: confirm enrollment.total is fall membership (not annual avg).
# The pipeline source for enrollment.total is CCD ccd_wa_membership.csv
# (column 'total_enrollment'), per pipeline/02_load_enrollment.py. CCD
# membership is the federal fall point-in-time count (around Oct 1).
log.info("Denominator confirmed: enrollment.total is CCD fall membership "
         "(point-in-time, ~Oct 1) per pipeline/02_load_enrollment.py. "
         "demographics.ospi_total is OSPI 'all students' (same year vintage). "
         "Both meet the 'October 1' criterion in the prompt; neither is annual avg.")

def safe_ratio(numerator, denominator):
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator

task4_ops = []
task4_stats = defaultdict(list)
task4_outliers = defaultdict(list)  # rates outside [0,1]
for d in schools:
    nid = d["_id"]
    demo = d.get("demographics") or {}
    enr = d.get("enrollment") or {}
    ospi_total = demo.get("ospi_total")
    enr_total = enr.get("total")
    white = (enr.get("by_race") or {}).get("white")

    # OSPI-vintage rates
    ell_pct = safe_ratio(demo.get("ell_count"), ospi_total)
    sped_pct = safe_ratio(demo.get("sped_count"), ospi_total)
    migrant_pct = safe_ratio(demo.get("migrant_count"), ospi_total)
    homeless_pct = safe_ratio(demo.get("homeless_count"), ospi_total)
    # CCD-vintage race rate
    if white is None or enr_total is None or enr_total == 0:
        race_pct = None
    else:
        race_pct = 1.0 - (white / enr_total)

    fields = {
        "ell_pct": ell_pct,
        "sped_pct": sped_pct,
        "migrant_pct": migrant_pct,
        "homelessness_pct": homeless_pct,
        "race_pct_non_white": race_pct,
    }
    for fname, val in fields.items():
        if val is not None:
            task4_stats[fname].append(val)
            if val < 0 or val > 1:
                task4_outliers[fname].append((nid, round(val, 4)))

    set_doc = {
        "derived.ell_pct": ell_pct,
        "derived.ell_pct_meta": {
            "source": "demographics.ell_count / demographics.ospi_total (OSPI 2023-24)",
            "compute_timestamp": NOW_ISO,
            "null_handling": "if either field is null, derived rate is null",
        },
        "derived.sped_pct": sped_pct,
        "derived.sped_pct_meta": {
            "source": "demographics.sped_count / demographics.ospi_total (OSPI 2023-24)",
            "compute_timestamp": NOW_ISO,
            "null_handling": "if either field is null, derived rate is null",
        },
        "derived.migrant_pct": migrant_pct,
        "derived.migrant_pct_meta": {
            "source": "demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)",
            "compute_timestamp": NOW_ISO,
            "null_handling": "if either field is null, derived rate is null",
        },
        "derived.homelessness_pct": homeless_pct,
        "derived.homelessness_pct_meta": {
            "source": "demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)",
            "compute_timestamp": NOW_ISO,
            "null_handling": "if either field is null, derived rate is null",
        },
        "derived.race_pct_non_white": race_pct,
        "derived.race_pct_non_white_meta": {
            "source": "1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)",
            "compute_timestamp": NOW_ISO,
            "null_handling": "if either field is null, derived rate is null",
        },
    }
    task4_ops.append(UpdateOne({"_id": nid}, {"$set": set_doc}))

log.info(f"Task 4 stats:")
for fname, vals in task4_stats.items():
    log.info(f"  {fname}: n={len(vals)}, "
             f"min={min(vals):.4f}, max={max(vals):.4f}, "
             f"mean={sum(vals)/len(vals):.4f}, "
             f"outside[0,1]={len(task4_outliers[fname])}")

# ===========================================================================
# TASK 6 — Document-root provenance metadata.
# ===========================================================================
DATASET_VERSIONS = {
    "graduation_rate": {"source": "data.wa.gov 76iv-8ed4", "year": "2023-24"},
    "teacher_experience": {"source": "data.wa.gov bdjb-hg6t", "year": "2024-25"},
    "derived.ell_pct": {"source": "OSPI demographics 2023-24", "year": "2023-24"},
    "derived.sped_pct": {"source": "OSPI demographics 2023-24", "year": "2023-24"},
    "derived.migrant_pct": {"source": "OSPI demographics 2023-24", "year": "2023-24"},
    "derived.homelessness_pct": {"source": "OSPI demographics 2023-24", "year": "2023-24"},
    "derived.race_pct_non_white": {"source": "CCD enrollment 2023-24", "year": "2023-24"},
}
task6_ops = [
    UpdateOne(
        {"_id": d["_id"]},
        {"$set": {
            "metadata.phase_3r_ingestion_timestamp": NOW_ISO,
            "metadata.phase_3r_dataset_versions": DATASET_VERSIONS,
        }})
    for d in schools
]

# ---------------------------------------------------------------------------
# WRITE — one big bulk_write per task, in chunks of 500.
# ---------------------------------------------------------------------------
def bulk(ops, label):
    assert "experiment" in db.name
    log.info(f"Writing {label}: {len(ops)} ops in chunks of 500 ...")
    total = 0
    chunk = 500
    for i in range(0, len(ops), chunk):
        res = db["schools"].bulk_write(ops[i:i+chunk], ordered=False)
        total += res.modified_count
        log.info(f"  {label} batch {i//chunk+1}: modified={res.modified_count}")
    log.info(f"  {label} total modified: {total}")
    return total

t1_mod = bulk(task1_ops, "Task 1 graduation_rate")
t3_mod = bulk(task3_ops, "Task 3 teacher_experience")
t4_mod = bulk(task4_ops, "Task 4 derived rates")
t6_mod = bulk(task6_ops, "Task 6 document metadata")

# ===========================================================================
# TASK 5 — Chronic-absenteeism null overlap diagnostic (READ ONLY).
# ===========================================================================
log.info("=== Task 5: chronic absenteeism null overlap ===")
# Build the exclusion union: school_exclusions.yaml ∪ Phase 3R SKIP
with open("/Users/oriandaleigh/school-daylight/school_exclusions.yaml") as f:
    yaml_excl = yaml.safe_load(f)
yaml_set = {e["ncessch"] for e in yaml_excl.get("excluded_schools", [])}
skip_set = set()
skip_reasons_per_doc = {}
for d in schools:
    r = (((d.get("census_acs") or {}).get("_meta") or {}).get("unmatched_reason"))
    if r:
        skip_set.add(d["_id"])
        skip_reasons_per_doc[d["_id"]] = r
union_set = yaml_set | skip_set

# Identify chronic-absenteeism null schools
null_chronic = [d for d in schools
                if (d.get("derived") or {}).get("chronic_absenteeism_pct") is None]
log.info(f"chronic_absenteeism_pct null count: {len(null_chronic)}")

null_chronic_ids = {d["_id"] for d in null_chronic}
# Of the null-chronic schools, how many in union?
in_union = null_chronic_ids & union_set
not_in_union = null_chronic_ids - union_set
log.info(f"  Of null-chronic, in exclusion union: {len(in_union)}")
log.info(f"  Of null-chronic, NOT in exclusion union (additional gap): {len(not_in_union)}")

# Distribution analysis on the additional-gap schools
gap_docs = [d for d in null_chronic if d["_id"] in not_in_union]
gap_by_level = Counter()
gap_by_type = Counter()
gap_by_district_size = Counter()
district_size_count = Counter()  # district -> # schools (any) in experiment db
for d in schools:
    md = d.get("metadata", {}) or {}
    dc = md.get("ospi_district_code")
    if dc:
        district_size_count[dc] += 1
def district_size_bucket(n):
    if n is None: return "unknown"
    if n < 5: return "1-4"
    if n < 10: return "5-9"
    if n < 20: return "10-19"
    if n < 50: return "20-49"
    return "50+"
for d in gap_docs:
    lg = (d.get("derived") or {}).get("level_group", "(unknown)")
    gap_by_level[lg or "(null)"] += 1
    if d.get("is_charter"):
        gap_by_type["charter"] += 1
    else:
        gap_by_type[d.get("school_type") or "(unknown)"] += 1
    md = d.get("metadata", {}) or {}
    dc = md.get("ospi_district_code")
    n = district_size_count.get(dc) if dc else None
    gap_by_district_size[district_size_bucket(n)] += 1

log.info(f"  gap by level_group: {dict(gap_by_level)}")
log.info(f"  gap by school_type: {dict(gap_by_type)}")
log.info(f"  gap by district size: {dict(gap_by_district_size)}")

# ---------------------------------------------------------------------------
# DELIVERABLE — write the markdown report.
# ---------------------------------------------------------------------------
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("—" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)

def fmt(v, places=4):
    if v is None: return "—"
    if isinstance(v, float): return f"{v:,.{places}f}"
    if isinstance(v, int): return f"{v:,}"
    return str(v)

def stats_row(name, vals, expected_range=None):
    if not vals:
        return [name, 0, "—", "—", "—", "—", "—"]
    return [name, len(vals),
            fmt(min(vals)), fmt(max(vals)),
            fmt(mean(vals)), fmt(median(vals)),
            f"{doc_count - len(vals)}"]

out = []
out.append("# Phase 3R Prompt 2 — API Ingestion Results")
out.append("")
out.append(f"Run timestamp (UTC): **{NOW_ISO}**")
out.append(f"Database written: **`{db.name}`** (production untouched)")
out.append(f"Document count: **{doc_count}**")
out.append(f"Log file: `{LOG_PATH}`")
out.append("")
out.append("Task 2 (teacher qualification — masters degree percentage) was "
           "DROPPED per builder ruling. See \"Task 2 — Investigation evidence "
           "and v2 path\" section below for the full evidence trail.")
out.append("")

# Methodology decisions
out.append("## Methodology decisions applied")
out.append("")
out.append("**Blocker 1 / Finding 1 — bin midpoints.** Each bin's published "
           "range is used (e.g. `25.0-29.9` → `27.45`). The original \"cap at 25\" "
           "rule was dropped because all observed bins are finite-range; no "
           "open-ended top bin exists in the 2024-25 data. Bins observed: "
           "`0.0 - 4.9` through `55.0 - 59.9`, plus `Not Reported`.")
out.append("")
out.append("**Blocker 1 / Finding 2 — `Not Reported` handling.** Renormalized "
           "to reported-bin weight sum (drop from both numerator and denominator). "
           "Schools with >10% Not Reported get `high_unreported_flag: true`.")
out.append("")
out.append("**Concern 4 — Task 4 denominators.** OSPI-sourced counts (ELL, SPED, "
           "migrant, homeless) divided by `demographics.ospi_total`; CCD-sourced "
           "white count divided by `enrollment.total`. Vintage-matched within each "
           "rate (OSPI 2023-24 / OSPI 2023-24 and CCD 2023-24 / CCD 2023-24).")
out.append("")
out.append("**Concern 5 — join key.** Composite `(metadata.ospi_district_code, "
           "metadata.ospi_school_code)` to source `(leacode, schoolcode)` or "
           "`(districtcode, schoolcode)` depending on dataset.")
out.append("")
out.append("**Concern 6 — charters ingested.** All 2,532 schools eligible for "
           "data, including 17 charter schools.")
out.append("")

# Task 1 — graduation
out.append("## Task 1 — Graduation rates (76iv-8ed4)")
out.append("")
out.append(f"- API endpoint: `https://data.wa.gov/resource/76iv-8ed4.json`")
out.append(f"- Filter: `organizationlevel=School`, `schoolyear=2023-24`, `studentgroup=All Students`")
out.append(f"- Source rows fetched: **{len(grad_rows)}**")
out.append(f"- Source rows whose (district, school) didn't match any school in the experiment db: **{unjoined_rows}**")
out.append(f"- Schools updated: **{t1_mod}**")
out.append("")
out.append(md_table(
    ["Outcome", "Count", "% of total"],
    [["HS-eligible (level_group=High OR grade_span.high=12)", task1_hs_count,
      f"{task1_hs_count/doc_count*100:.1f}%"],
     ["HS with at least one cohort rate", task1_hs_with_data,
      f"{task1_hs_with_data/doc_count*100:.1f}%"],
     ["HS with NO graduation data (rate fields null)",
      task1_hs_count - task1_hs_with_data,
      f"{(task1_hs_count - task1_hs_with_data)/doc_count*100:.1f}%"],
     ["Non-HS (rate fields null with not_applicable_reason)", task1_non_hs,
      f"{task1_non_hs/doc_count*100:.1f}%"]]
))
out.append("")
out.append("Distribution of populated graduation rates:")
out.append("")
out.append(md_table(
    ["field", "n_non_null", "min", "max", "mean", "median", "null_count_in_collection"],
    [stats_row("graduation_rate.cohort_4yr", task1_4yr_vals),
     stats_row("graduation_rate.cohort_5yr", task1_5yr_vals)]
))
out.append("")

# Task 2 — investigation evidence (DROPPED)
out.append("## Task 2 — Teacher qualification (DROPPED per builder Path A)")
out.append("")
out.append("Per builder ruling, Task 2 was dropped from v1 to avoid creating a "
           "redundant tenure variable alongside Task 3's experience derivation. "
           "No write to `teacher_qualification.*` was performed. Two-step "
           "investigation evidence is preserved here for the v2-path note.")
out.append("")
out.append("### Step 1: Personnel Summary XLSX (`table_15-40_school_district_personnel_summary_profiles_2025-26.xlsx`)")
out.append("")
out.append("All 39 sheets (Tables 15 through 40) were inspected. Every sheet "
           "uses the same 10-column template focused on FTE counts and salary:")
out.append("")
out.append("```")
out.append("District code | District Name | Individuals | Avg Add'l Salary per Indiv. |")
out.append("Total FTE | Base Salary | Total Salary | Insur. Ben. | Mand. Ben. |")
out.append("Days in 1.0 FTE")
out.append("```")
out.append("")
out.append("Definitive workbook-wide substring scan for "
           "`master|doctor|degree|baccal|bachelor|highest-degree|education-level`: "
           "**zero matches anywhere in the workbook.** The Personnel Summary "
           "tables aggregate S-275 raw data by FTE/headcount/salary only; they "
           "do not surface the credential-level dimension that exists in the "
           "underlying S-275 personnel records.")
out.append("")
out.append("### Step 2: data.wa.gov catalog probe")
out.append("")
out.append(md_table(
    ["dataset_id", "name", "resource status", "metadata status"],
    [["t9ya-d7ak", "Educator Characteristics", "HTTP 404", "HTTP 404"],
     ["3543-y5sg", "Educator Educational Level", "HTTP 404", "HTTP 404"],
     ["wsha-faww", "Educational Attainment Level", "(not probed)", "HTTP 404"],
     ["wc8d-kv9u", "Report Card Teacher Qualification Summary 2021-22 to 2024-25",
      "alive", "alive — but only 'Inexperienced Status' / 'Experienced Status' values"],
     ["e28j-uhwn", "Report Card Teacher Qualification Summary 2017-18 to 2020-21",
      "alive", "alive — same schema as wc8d-kv9u"]]
))
out.append("")
out.append("Catalog searches for `certification`, `credential`, `S-275`, "
           "`highest degree teacher`, `educator master`, `OSPI educator` "
           "surfaced no live data.wa.gov dataset carrying school-level "
           "educator credential / education-level data. The three datasets "
           "whose names match what we want are all withdrawn at the resource level.")
out.append("")
out.append("### v2 path note")
out.append("")
out.append("OSPI publishes annual S-275 raw extracts (CSV/XLSX) outside data.wa.gov, "
           "and those rows include a Highest_Degree column at the personnel level. "
           "Aggregating Highest_Degree to school level is the v2 candidate path "
           "for restoring the credential dimension. v1 ships without it.")
out.append("")

# Task 3 — teacher experience
out.append("## Task 3 — Teacher experience (bdjb-hg6t)")
out.append("")
out.append(f"- API endpoint: `https://data.wa.gov/resource/bdjb-hg6t.json`")
out.append(f"- Filter: `organizationlevel=School`, `schoolyear=2024-25`")
out.append(f"- Source rows fetched: **{len(te_rows)}**")
out.append(f"- Source rows that didn't match any school in experiment db: **{te_unjoined}**")
out.append(f"- Schools updated: **{t3_mod}**")
out.append("")
out.append("Distinct bins observed in source data (for transparency):")
out.append("")
distinct_bins = sorted({r.get("experiencebin") for r in te_rows
                        if r.get("experiencebin")})
for b in distinct_bins:
    out.append(f"- `{b}` → midpoint = {bin_midpoint(b)}")
out.append("")
out.append(md_table(
    ["Outcome", "Count"],
    [["Schools with computed `average_years_derived`", task3_with_data],
     ["Schools with no bin rows in source (null + null_reason='no_bin_rows')",
      task3_no_rows],
     ["Schools with `high_unreported_flag: true` (>10% Not Reported)",
      task3_high_unreported]]
))
out.append("")
out.append("### Validation table (5 sample schools, run during validation gate)")
out.append("")
out.append(md_table(
    ["School", "District", "bin rows", "weight sum", "average_years_derived"],
    [["Fairhaven Middle", "Bellingham", 13, "0.977", "13.68"],
     ["Washington Elementary", "Mead", 13, "0.971", "10.46"],
     ["Franklin Elementary", "Pullman", 13, "0.998", "14.92"],
     ["Delong Elementary", "Spokane", 13, "1.000", "16.45"],
     ["Lewis and Clark High", "Spokane", 13, "0.941", "8.39 (after renormalization)"],
     ["Clark Co Juvenile Detention", "ESD 112", 0, "0.000", "null (no bin rows)"]]
))
out.append("")
out.append("Renormalization makes the Lewis and Clark figure (originally 7.90 "
           "before renormalization) consistent with the rest of the cohort.")
out.append("")
out.append(md_table(
    ["field", "n_non_null", "min", "max", "mean", "median", "null_count"],
    [stats_row("teacher_experience.average_years_derived", task3_avg_vals)]
))
out.append("")

# Task 4 — derived rates
out.append("## Task 4 — Derived rates from existing counts")
out.append("")
out.append(f"- Schools updated (rates set on every doc, with null where input is null): **{t4_mod}**")
out.append("")
out.append("**Denominator confirmation.** `enrollment.total` is CCD fall membership "
           "(point-in-time, ~Oct 1) per `pipeline/02_load_enrollment.py`. "
           "`demographics.ospi_total` is OSPI All Students (same year vintage). "
           "Both are point-in-time counts; neither is annual average. "
           "STOP-and-report condition NOT triggered.")
out.append("")
out.append("Distribution summaries:")
out.append("")
rate_rows = []
for fname in ["ell_pct", "sped_pct", "migrant_pct", "homelessness_pct",
              "race_pct_non_white"]:
    vals = task4_stats[fname]
    rate_rows.append([f"derived.{fname}", len(vals),
                      fmt(min(vals)) if vals else "—",
                      fmt(max(vals)) if vals else "—",
                      fmt(mean(vals)) if vals else "—",
                      fmt(median(vals)) if vals else "—",
                      doc_count - len(vals)])
out.append(md_table(
    ["field", "n_non_null", "min", "max", "mean", "median", "null_count"],
    rate_rows))
out.append("")
out.append("**[0, 1] range validation.**")
out.append("")
total_rates_computed = sum(len(v) for v in task4_stats.values())
total_outliers = sum(len(v) for v in task4_outliers.values())
in_range_pct = (total_rates_computed - total_outliers) / total_rates_computed * 100 \
                if total_rates_computed else 0
out.append(f"- Total non-null computed rates across all 5 fields: **{total_rates_computed}**")
out.append(f"- Rates outside [0, 1]: **{total_outliers}** "
           f"({total_outliers/total_rates_computed*100:.2f}% of non-null)")
out.append(f"- In-range fraction: **{in_range_pct:.2f}%** "
           f"(target ≥ 99%; {'PASS' if in_range_pct >= 99 else 'FAIL'})")
out.append("")
if total_outliers:
    out.append("**Schools with rates outside [0, 1] (stored as-computed; no clipping):**")
    out.append("")
    for fname, outs in task4_outliers.items():
        if not outs:
            continue
        out.append(f"### `derived.{fname}`")
        out.append("")
        out.append(md_table(
            ["_id", "computed value"],
            [[nid, val] for nid, val in outs[:50]]))
        if len(outs) > 50:
            out.append(f"... and {len(outs) - 50} more.")
        out.append("")

# Task 5 — chronic absenteeism null overlap
out.append("## Task 5 — Chronic absenteeism null overlap diagnostic")
out.append("")
out.append("READ-ONLY analysis. No writes performed for this task.")
out.append("")
out.append(md_table(
    ["bucket", "count"],
    [["`derived.chronic_absenteeism_pct` null total", len(null_chronic_ids)],
     ["Already in exclusion union (school_exclusions.yaml ∪ Phase 3R SKIP)", len(in_union)],
     ["NOT in exclusion union (additional coverage gap)", len(not_in_union)],
     ["", ""],
     ["Reference: school_exclusions.yaml", len(yaml_set)],
     ["Reference: Phase 3R SKIP", len(skip_set)],
     ["Reference: union", len(union_set)]]
))
out.append("")
out.append(f"**Additional coverage gap = {len(not_in_union)} schools.** Distribution:")
out.append("")
out.append("### By `derived.level_group`")
out.append("")
out.append(md_table(
    ["level_group", "count"],
    [[k, v] for k, v in sorted(gap_by_level.items(), key=lambda x: -x[1])]))
out.append("")
out.append("### By school type / charter status")
out.append("")
out.append(md_table(
    ["school_type", "count"],
    [[k, v] for k, v in sorted(gap_by_type.items(), key=lambda x: -x[1])]))
out.append("")
out.append("### By district size (count of schools per district within experiment db)")
out.append("")
out.append(md_table(
    ["district size bucket", "count"],
    [[k, gap_by_district_size[k]]
     for k in ["1-4", "5-9", "10-19", "20-49", "50+", "unknown"]]))
out.append("")

# Task 6 — document metadata
out.append("## Task 6 — Document-root provenance metadata")
out.append("")
out.append(f"- Schools updated: **{t6_mod}**")
out.append("")
out.append("Each touched document now carries:")
out.append("")
out.append("- `metadata.phase_3r_ingestion_timestamp` = ISO 8601 of this run")
out.append("- `metadata.phase_3r_dataset_versions` = mapping of new field name → "
           "{source, year}")
out.append("")
out.append("```json")
out.append(json.dumps(DATASET_VERSIONS, indent=2))
out.append("```")
out.append("")

# Anomalies / Issues
out.append("## Issues for builder review")
out.append("")
issues = []
if no_ospi_codes:
    issues.append(f"- **{len(no_ospi_codes)} schools lack OSPI codes** "
                  f"(`metadata.ospi_district_code` or `metadata.ospi_school_code` "
                  f"missing). They received null graduation and teacher_experience "
                  f"data. Sample: `{no_ospi_codes[:5]}`.")
if ospi_collisions:
    issues.append(f"- **{len(ospi_collisions)} OSPI-key collisions** in the "
                  f"`(district, school)`→`_id` map — multiple NCESSCH share "
                  f"the same OSPI composite. Last-write-wins in this run; "
                  f"may need disambiguation. Sample: `{ospi_collisions[:3]}`.")
te_high_pct_pct = task3_high_unreported / max(task3_with_data, 1) * 100
issues.append(f"- **`high_unreported_flag` triggered on {task3_high_unreported} "
              f"schools** ({te_high_pct_pct:.1f}% of those with computed averages). "
              f"Renormalization assumption may be weaker for these; downstream "
              f"methodology should review.")
gap_count = len(not_in_union)
issues.append(f"- **Chronic-absenteeism additional coverage gap: {gap_count} schools.** "
              f"These are schools with `chronic_absenteeism_pct=null` that are NOT "
              f"on either exclusion list. The dominant grade_level_category and "
              f"school-type buckets are listed in Task 5; many appear to be schools "
              f"without tested grades (the null pattern from Phase 3R diagnostics).")
hs_no_grad = task1_hs_count - task1_hs_with_data
if hs_no_grad:
    issues.append(f"- **{hs_no_grad} HS-eligible schools have no graduation data** "
                  f"in the source. Likely small / new / closed schools or alternative "
                  f"programs. Stored as null with metadata.not_applicable_reason=null "
                  f"(reason is null because they ARE HS-eligible — the null is a "
                  f"coverage gap, not an inapplicability).")
issues.append(f"- **No 5-year cohort rates for some schools that have a 4-year rate "
              f"(or vice versa).** 4yr non-null = {len(task1_4yr_vals)}, "
              f"5yr non-null = {len(task1_5yr_vals)}. Asymmetric coverage is "
              f"expected because the 5-year cohort lags by one academic year.")
issues.append(f"- **Task 2 was dropped.** Methodology now has zero teacher-credential "
              f"variables; only one teacher-tenure variable. `methodology_revisions_pending.md` "
              f"R1 documents the v2 path (S-275 raw extracts).")
out.extend(issues)
out.append("")

# Production untouched
out.append("## Production untouched")
out.append("")
out.append(f"- Database written: `{db.name}` (contains substring \"experiment\")")
out.append(f"- Pre-write isolation guard: PASSED (asserted before each `bulk_write`)")
out.append(f"- Production database (`{config.DB_NAME}`): NOT opened, NOT queried, NOT written.")
out.append("")
out.append("Idempotency: every write was a `$set` on a specific dotted path. "
           "Rerunning this script will overwrite the same paths cleanly. No "
           "documents were created (`upsert=False` is the pymongo default; "
           "all UpdateOne ops match by `_id` against existing docs).")
out.append("")

with open(OUT_FILE, "w") as f:
    f.write("\n".join(out))
log.info(f"Wrote deliverable: {OUT_FILE}")
log.info(f"Phase 3R Prompt 2 ingestion COMPLETE.")

client.close()
print(f"\nDONE. Deliverable: {OUT_FILE}")
print(f"Log: {LOG_PATH}")
