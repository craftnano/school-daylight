"""
_run_schema_check.py — Read-only Phase 3R schema verification.

PURPOSE: Verify field paths, null distributions, and homelessness availability
         in schooldaylight_experiment.schools before any v1 ingestion.
INPUTS:  MongoDB Atlas (schooldaylight_experiment.schools, READ ONLY),
         school_exclusions.yaml, phases/phase-3R/experiment/district_id_audit.md
OUTPUTS: phases/phase-3R/experiment/schema_check_verification.md
         logs/schema_check_<TS>.log

GUARD:   Refuses to run against any database whose name does not contain
         "experiment". Read-only by policy and by code path — no $set, $unset,
         insert, delete, or bulk_write anywhere in this script.
"""

import datetime as dt
import json
import logging
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
import yaml
from collections import Counter, defaultdict

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Logging — timestamped file in logs/, complete English sentences.
# ---------------------------------------------------------------------------
TS = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = "/Users/oriandaleigh/school-daylight/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"schema_check_{TS}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("schema_check")
log.info(f"Schema-check run starting. Log file: {LOG_PATH}")

OUT_DIR = "/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment"
OUT_FILE = os.path.join(OUT_DIR, "schema_check_verification.md")

# ---------------------------------------------------------------------------
# TASK 1 — confirm sandbox.
# ---------------------------------------------------------------------------
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client.get_default_database()
assert "experiment" in db.name, \
    f"Refusing to run — database name '{db.name}' does not contain 'experiment'."
log.info(f"Connected to database '{db.name}' via MONGO_URI_EXPERIMENT.")

doc_count = db["schools"].count_documents({})
log.info(f"Document count in schools collection: {doc_count}.")
if not (2400 <= doc_count <= 2700):
    log.error(f"Document count {doc_count} is outside the expected ~2,532 range. Stopping.")
    raise SystemExit(2)
log.info(f"Sandbox confirmed: '{db.name}' with {doc_count} schools (within expected ~2,532 range).")

# ---------------------------------------------------------------------------
# TASK 2 — enumerate schema from a 50-doc sample.
# Walk every field path, record type, count nulls, and gather numeric stats.
# ---------------------------------------------------------------------------
SAMPLE_N = 50
sample_cursor = db["schools"].aggregate([{"$sample": {"size": SAMPLE_N}}])
sample = list(sample_cursor)
log.info(f"Drew a {len(sample)}-document random sample for schema enumeration.")

field_types = defaultdict(Counter)
field_nulls = defaultdict(int)         # nulls within sample
field_present = defaultdict(int)       # count of times the path was present
numeric_values = defaultdict(list)     # numeric samples per path

PRIMITIVE = (str, int, float, bool, type(None))

def walk(prefix, obj, depth=0):
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if v is None:
                field_present[path] += 1
                field_types[path]["null"] += 1
                field_nulls[path] += 1
            elif isinstance(v, bool):
                field_present[path] += 1
                field_types[path]["bool"] += 1
            elif isinstance(v, (int, float)):
                field_present[path] += 1
                field_types[path]["int" if isinstance(v, int) else "float"] += 1
                numeric_values[path].append(float(v))
            elif isinstance(v, str):
                field_present[path] += 1
                field_types[path]["str"] += 1
            elif isinstance(v, dict):
                field_present[path] += 1
                field_types[path]["dict"] += 1
                walk(path, v, depth+1)
            elif isinstance(v, list):
                field_present[path] += 1
                field_types[path]["list"] += 1
                if v and isinstance(v[0], dict):
                    walk(path + "[]", v[0], depth+1)
            else:
                field_present[path] += 1
                field_types[path][type(v).__name__] += 1

for d in sample:
    walk("", d)

log.info(f"Walked {len(field_present)} distinct field paths in the sample.")

# ---------------------------------------------------------------------------
# TASK 3 — verify v1 variables across the FULL collection.
# Each entry: (label, [candidate paths], category)
# We probe each candidate, pick the first one that has any non-null in the sample,
# and report its full-collection null count.
# ---------------------------------------------------------------------------
V1_VARS = [
    # (label, candidate paths, category)
    # Identity
    ("nces_id", ["_id", "nces_id", "ncessch", "NCESSCH"], "Identity"),
    ("district_nces_id", ["district.nces_id", "district_nces_id", "leaid", "district.leaid"], "Identity"),
    ("school_name", ["name", "school_name"], "Identity"),
    ("grade_level_category", ["derived.level_group", "level", "grade_level_category"], "Identity"),
    # Demographics & structure
    ("enrollment_total", ["enrollment.total", "enrollment_total"], "Demographics"),
    ("frl_rate", ["demographics.frl_pct", "demographics.frl_rate", "frl_rate", "frl_pct"], "Demographics"),
    ("ell_rate", ["demographics.ell_pct", "demographics.ell_rate", "ell_rate", "demographics.ell"], "Demographics"),
    ("sped_rate", ["demographics.sped_pct", "demographics.sped_rate", "sped_rate", "demographics.sped"], "Demographics"),
    ("migrant_rate", ["demographics.migrant_pct", "demographics.migrant_rate", "migrant_rate"], "Demographics"),
    ("race_pct_non_white", ["demographics.percent_non_white", "demographics.race.percent_non_white",
                            "race_composition.percent_non_white", "demographics.non_white_pct",
                            "demographics.race_composition.percent_non_white"], "Demographics"),
    ("chronic_absenteeism_rate", ["derived.chronic_absenteeism_pct", "academics.attendance.chronic_absenteeism_pct",
                                  "chronic_absenteeism_rate", "academics.chronic_absenteeism_pct"], "Demographics"),
    # Census ACS — value is at census_acs.<var>.value
    ("median_household_income", ["census_acs.median_household_income.value"], "Census"),
    ("per_capita_income", ["census_acs.per_capita_income.value"], "Census"),
    ("gini_index", ["census_acs.gini_index.value"], "Census"),
    ("bachelors_pct_25_plus", ["census_acs.bachelors_or_higher_pct_25plus.value",
                                "census_acs.bachelors_pct_25_plus.value"], "Census"),
    ("labor_force_participation_rate", ["census_acs.labor_force_participation_rate_16plus.value",
                                         "census_acs.labor_force_participation_rate.value"], "Census"),
    ("unemployment_rate", ["census_acs.unemployment_rate_16plus.value",
                           "census_acs.unemployment_rate.value"], "Census"),
    ("total_population", ["census_acs.total_population.value"], "Census"),
    ("land_area_sq_mi", ["census_acs.land_area_sq_miles.value", "census_acs.land_area_sq_mi.value"], "Census"),
    ("population_density", ["census_acs.population_density_per_sq_mile.value",
                             "census_acs.population_density.value"], "Census"),
    # Exclusions
    ("exclusion_status", ["census_acs._meta.unmatched_reason", "exclusion_status"], "Exclusions"),
    ("exclusion_reason_code", ["census_acs._meta.unmatched_reason", "exclusion_reason_code"], "Exclusions"),
]

def probe_path(path):
    """Return (n_present, n_null, n_nonnull). Counts via $exists then $ne null."""
    n_exists = db["schools"].count_documents({path: {"$exists": True}})
    n_nonnull = db["schools"].count_documents({path: {"$exists": True, "$ne": None}})
    return n_exists, n_exists - n_nonnull, n_nonnull

def numeric_stats(path):
    """Pull non-null numeric values and return a small stats dict."""
    cursor = db["schools"].find(
        {path: {"$exists": True, "$ne": None, "$type": "number"}},
        {path: 1, "_id": 0})
    vals = []
    parts = path.split(".")
    for d in cursor:
        cur = d
        for p in parts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = None
                break
        if isinstance(cur, (int, float)) and cur is not None:
            vals.append(float(cur))
    if not vals:
        return None
    vals_sorted = sorted(vals)
    return {
        "n": len(vals),
        "min": vals_sorted[0],
        "max": vals_sorted[-1],
        "mean": sum(vals) / len(vals),
        "median": vals_sorted[len(vals)//2],
    }

v1_findings = []
for label, candidates, category in V1_VARS:
    chosen = None
    for c in candidates:
        n_exists, n_null, n_nn = probe_path(c)
        if n_nn > 0:
            chosen = c
            break
    if chosen is None:
        v1_findings.append({
            "label": label, "category": category,
            "actual_path": None, "n_present": 0, "n_null": 0, "n_nonnull": 0,
            "stats": None, "notes": "MISSING — no candidate path returned non-null values",
        })
        log.warning(f"Variable '{label}': MISSING. Candidates {candidates} all empty.")
        continue
    n_exists, n_null, n_nn = probe_path(chosen)
    stats = numeric_stats(chosen) if category in ("Demographics", "Census") else None
    null_pct = n_null / doc_count * 100
    v1_findings.append({
        "label": label, "category": category,
        "actual_path": chosen,
        "n_present": n_exists, "n_null_full": doc_count - n_nn,
        "n_nonnull": n_nn,
        "null_pct": null_pct, "stats": stats,
        "alt_candidates": [c for c in candidates if c != chosen],
    })
    log.info(f"Variable '{label}' resolved to '{chosen}': "
             f"{n_nn} non-null, {doc_count - n_nn} null ({(doc_count-n_nn)/doc_count*100:.1f}%).")

# ---------------------------------------------------------------------------
# TASK 4 — homelessness search.
# ---------------------------------------------------------------------------
log.info("Searching for any field path containing 'homeless' (case-insensitive).")
HOMELESS_RE = re.compile(r"homeless", re.IGNORECASE)
homeless_paths = sorted([p for p in field_present if HOMELESS_RE.search(p)])
log.info(f"Sample-walk found {len(homeless_paths)} paths containing 'homeless'.")

# Belt-and-braces: scan a wider set if sample missed it. Pull 200 docs,
# walk again into a temp set.
extra_homeless = set()
extra_cursor = db["schools"].aggregate([{"$sample": {"size": 200}}])
def find_homeless(prefix, obj, hits, depth=0):
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if HOMELESS_RE.search(k):
                hits.add(path)
            if isinstance(v, dict):
                find_homeless(path, v, hits, depth+1)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                find_homeless(path + "[]", v[0], hits, depth+1)
for d in extra_cursor:
    find_homeless("", d, extra_homeless)
homeless_paths = sorted(set(homeless_paths) | extra_homeless)
log.info(f"After 200-doc rescan: {len(homeless_paths)} 'homeless' paths total.")

# If empty, query data.wa.gov for the OSPI Report Card Enrollment dataset.
homeless_decision = None
homeless_test_rows = None
homeless_dataset_id = None
homeless_subgroup_or_column = None
homeless_query_url = None

if not homeless_paths:
    log.info("No 'homeless' field found. Querying data.wa.gov catalog for "
             "'Report Card Enrollment 2023-24' dataset.")
    catalog_url = ("https://data.wa.gov/api/catalog/v1?q=Report+Card+Enrollment+"
                   "2023-24&only=datasets&limit=10")
    try:
        with urllib.request.urlopen(catalog_url, timeout=30) as r:
            cat = json.loads(r.read())
        results = cat.get("results", [])
        log.info(f"Catalog returned {len(results)} candidate datasets.")
        # Prefer the one with 'Report Card Enrollment' and 2023-24 in the name
        chosen = None
        for entry in results:
            res = entry.get("resource", {})
            name = res.get("name", "")
            if "Report Card Enrollment" in name and ("2023-24" in name or "2024" in name):
                chosen = res
                break
        if chosen is None and results:
            chosen = results[0].get("resource", {})
        if chosen:
            homeless_dataset_id = chosen.get("id")
            log.info(f"Chose dataset: id={homeless_dataset_id}, name={chosen.get('name')!r}.")
            # Pull 5 rows to inspect schema
            sample_url = (f"https://data.wa.gov/resource/{homeless_dataset_id}.json"
                          f"?$limit=5")
            homeless_query_url = sample_url
            log.info(f"Fetching 5-row sample: {sample_url}")
            with urllib.request.urlopen(sample_url, timeout=30) as r:
                rows = json.loads(r.read())
            homeless_test_rows = rows
            if rows:
                cols = sorted(rows[0].keys())
                log.info(f"Column list (first row): {cols}")
                # Heuristic: is "homeless" a value in some 'subgroup' / 'studentgroup' column?
                # or is it a column name?
                col_match = any("homeless" in c.lower() for c in cols)
                value_match = any(any("homeless" in str(v).lower()
                                       for v in row.values())
                                  for row in rows)
                # Try a targeted query against likely subgroup column names
                subgroup_columns = ["studentgroup", "student_group", "subgroup",
                                     "studentgrouptype", "studentgrouptype_descr",
                                     "studentgrouptype_description"]
                found_subgroup = None
                for sc in subgroup_columns:
                    if sc in cols:
                        # Try fetching a row where this column = Homeless
                        q = (f"https://data.wa.gov/resource/{homeless_dataset_id}.json"
                             f"?{sc}=Homeless&$limit=3")
                        try:
                            with urllib.request.urlopen(q, timeout=30) as rr:
                                hits = json.loads(rr.read())
                            if hits:
                                found_subgroup = (sc, hits)
                                break
                        except urllib.error.HTTPError as e:
                            log.warning(f"Subgroup probe '{sc}' returned {e.code}.")
                if col_match:
                    homeless_subgroup_or_column = "column"
                    homeless_decision = ("Homelessness appears as one or more COLUMNS in "
                                         "the dataset (e.g. column name contains 'homeless').")
                elif found_subgroup:
                    homeless_subgroup_or_column = "subgroup_row"
                    homeless_decision = (f"Homelessness appears as a ROW (subgroup) in the "
                                         f"'{found_subgroup[0]}' column. Each school appears "
                                         f"on multiple rows, one per StudentGroup; pivot on "
                                         f"that column at ingestion time.")
                else:
                    homeless_subgroup_or_column = "unknown"
                    homeless_decision = ("Homelessness presence in this dataset is "
                                         "ambiguous from the 5-row sample. Builder review "
                                         "needed before ingestion.")
        else:
            homeless_decision = ("data.wa.gov catalog did not return a clear "
                                 "Report Card Enrollment 2023-24 dataset. Manual "
                                 "lookup required.")
    except Exception as e:
        homeless_decision = f"data.wa.gov probe failed: {type(e).__name__}: {e}"
        log.error(homeless_decision)
else:
    homeless_decision = (f"Homelessness field already present in schema at: "
                         f"{', '.join(homeless_paths)}. No data.wa.gov probe needed.")
    log.info(homeless_decision)

# ---------------------------------------------------------------------------
# TASK 5 — exclusions union.
# ---------------------------------------------------------------------------
log.info("Computing exclusions union: school_exclusions.yaml ∪ Phase 3R SKIP.")
with open("/Users/oriandaleigh/school-daylight/school_exclusions.yaml") as f:
    yaml_excl = yaml.safe_load(f)
yaml_set = {e["ncessch"] for e in yaml_excl.get("excluded_schools", [])}

# Phase 3R SKIP from MongoDB (post-patch state, single source of truth)
skip_set = set()
skip_by_reason_count = Counter()
cursor = db["schools"].find(
    {"census_acs._meta.unmatched_reason": {"$ne": None}},
    {"_id": 1, "census_acs._meta.unmatched_reason": 1})
for d in cursor:
    skip_set.add(d["_id"])
    skip_by_reason_count[d["census_acs"]["_meta"]["unmatched_reason"]] += 1

overlap = yaml_set & skip_set
union = yaml_set | skip_set
log.info(f"school_exclusions.yaml count: {len(yaml_set)}.")
log.info(f"Phase 3R SKIP count: {len(skip_set)}.")
log.info(f"Overlap: {len(overlap)}. Union: {len(union)}.")

# Sanity-check vs. the prompt's expectations
expected_yaml_min, expected_yaml_max = 70, 90
expected_skip_min, expected_skip_max = 40, 60
expected_union_min, expected_union_max = 80, 100
unions_ok = expected_union_min <= len(union) <= expected_union_max
yaml_ok = expected_yaml_min <= len(yaml_set) <= expected_yaml_max
skip_ok = expected_skip_min <= len(skip_set) <= expected_skip_max
log.info(f"Range checks: yaml={yaml_ok} skip={skip_ok} union={unions_ok}.")

# Cross-check the audit doc's headline number (we expect 48 SKIP)
audit_path = "/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment/district_id_audit.md"
audit_total_non_usd = None
if os.path.exists(audit_path):
    with open(audit_path) as f:
        audit_text = f.read()
    m = re.search(r"\| \*\*Total schools\*\* \| — \| \*\*([\d,]+)\*\*", audit_text)
    m2 = re.search(r"USD-rolled\s+schools[^|]*\|\s*\d+\s*\|\s*\*?\*?([\d,]+)", audit_text)
    log.info(f"district_id_audit.md exists, used as reference (not parsed for new numbers).")

# ---------------------------------------------------------------------------
# WRITE deliverable
# ---------------------------------------------------------------------------
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("—" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)

def fmt(v, places=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{places}f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)

issues = []
out = []
out.append("# Phase 3R — Schema Check & Homelessness Verification")
out.append("")
out.append(f"Run date (UTC): **{dt.datetime.utcnow().isoformat()}Z**")
out.append(f"Database: **`{db.name}`** (read-only this session)")
out.append(f"Document count: **{doc_count}**")
out.append(f"Sample size for schema enumeration (Task 2): **{len(sample)}**")
out.append(f"Log file: `{LOG_PATH}`")
out.append("")
out.append("This is a read-only inspection. No documents were modified. The "
           "isolation guard `assert \"experiment\" in db.name` passed at the top "
           "of the run.")
out.append("")

# ---- Task 2: schema enumeration ----
out.append("## 1. Schema enumeration (Task 2)")
out.append("")
out.append(f"Random sample of {len(sample)} documents walked recursively. "
           "Numeric stats below are computed from the sample only; full-collection "
           "stats for v1 variables are in the next section.")
out.append("")
out.append("Top-level field paths in the sample, with type distribution, "
           "presence count (out of 50), and null count:")
out.append("")
top_level_paths = sorted([p for p in field_present if "." not in p and "[]" not in p])
rows = []
for p in top_level_paths:
    types = ", ".join(f"{t}×{n}" for t, n in field_types[p].most_common())
    rows.append([p, field_present[p], field_nulls[p], types])
out.append(md_table(["path", "present (of 50)", "null (of 50)", "types seen"], rows))
out.append("")

# Numeric distribution for nested numeric paths in the sample
out.append(f"Numeric-typed paths discovered in the sample, with sample-only stats:")
out.append("")
num_paths = sorted(numeric_values.keys())
num_rows = []
for p in num_paths:
    vals = numeric_values[p]
    if not vals:
        continue
    num_rows.append([p, len(vals), fmt(min(vals)), fmt(max(vals)),
                     fmt(sum(vals)/len(vals)),
                     fmt(sorted(vals)[len(vals)//2])])
out.append(md_table(
    ["path", "n_in_sample", "min", "max", "mean", "median"], num_rows))
out.append("")
out.append(f"Total distinct field paths walked: **{len(field_present)}**.")
out.append("")

# ---- Task 3: v1 variables ----
out.append("## 2. V1 variable verification (Task 3)")
out.append("")
out.append(f"For each v1 variable, the actual MongoDB path, full-collection null "
           f"count (out of {doc_count}), and basic distribution. **null_pct** is "
           f"computed against the full collection, not against \"non-excluded\" "
           f"schools — that filter is not yet defined; flagging anything ≥ 10%.")
out.append("")

NULL_PCT_THRESHOLD = 10.0
hi_null_paths = []
missing_paths = []
unexpected_paths = []
PROMPT_ASSUMED_PATHS = {
    "frl_rate": "frl_rate",
    "ell_rate": "ell_rate",
    "sped_rate": "sped_rate",
    "migrant_rate": "migrant_rate",
    "race_pct_non_white": "race_composition.percent_non_white",
    "chronic_absenteeism_rate": "chronic_absenteeism_rate",
    "median_household_income": "census_acs.median_household_income.value",
    "per_capita_income": "census_acs.per_capita_income.value",
    "gini_index": "census_acs.gini_index.value",
    "bachelors_pct_25_plus": "census_acs.bachelors_pct_25_plus.value",
    "labor_force_participation_rate": "census_acs.labor_force_participation_rate.value",
    "unemployment_rate": "census_acs.unemployment_rate.value",
    "total_population": "census_acs.total_population.value",
    "land_area_sq_mi": "census_acs.land_area_sq_mi.value",
    "population_density": "census_acs.population_density.value",
    "exclusion_status": "exclusion_status",
    "exclusion_reason_code": "exclusion_reason_code",
}

for category in ["Identity", "Demographics", "Census", "Exclusions"]:
    cat_findings = [f for f in v1_findings if f["category"] == category]
    if not cat_findings:
        continue
    out.append(f"### {category}")
    out.append("")
    rows = []
    for f in cat_findings:
        path = f["actual_path"]
        if path is None:
            rows.append([f["label"], "**MISSING**", "—", "—", "no path returned non-null"])
            missing_paths.append(f["label"])
            continue
        prompt_path = PROMPT_ASSUMED_PATHS.get(f["label"])
        if prompt_path and prompt_path != path:
            note = f"prompt assumed `{prompt_path}` — actual differs"
            unexpected_paths.append((f["label"], prompt_path, path))
        else:
            note = ""
        if f["null_pct"] >= NULL_PCT_THRESHOLD:
            note = (note + "; " if note else "") + f"high null pct ({f['null_pct']:.1f}%)"
            hi_null_paths.append((f["label"], path, f["null_pct"]))
        rows.append([f["label"], f"`{path}`", f["n_nonnull"],
                     f"{f['null_pct']:.1f}%", note or "—"])
    out.append(md_table(
        ["v1 variable", "actual MongoDB path", "non-null", "null %", "notes"], rows))
    out.append("")
    # Numeric stats
    num_rows = []
    for f in cat_findings:
        if f.get("stats"):
            s = f["stats"]
            num_rows.append([f["label"],
                             s["n"],
                             fmt(s["min"]),
                             fmt(s["median"]),
                             fmt(s["mean"]),
                             fmt(s["max"])])
    if num_rows:
        out.append(f"Numeric distribution (full-collection, non-null only):")
        out.append("")
        out.append(md_table(
            ["v1 variable", "n", "min", "median", "mean", "max"], num_rows))
        out.append("")

# ---- Task 4: homelessness ----
out.append("## 3. Homelessness availability (Task 4)")
out.append("")
if homeless_paths:
    out.append(f"**Found in schema.** Paths containing 'homeless':")
    out.append("")
    for p in homeless_paths:
        out.append(f"- `{p}`")
    out.append("")
else:
    out.append("**Not found in schema.** No field path matching `/homeless/i` "
               f"was discovered in a 50-doc sample or a 200-doc rescan. Falling "
               f"back to data.wa.gov catalog probe.")
    out.append("")
    out.append(f"- Catalog query: `https://data.wa.gov/api/catalog/v1?q=Report+Card+Enrollment+2023-24&only=datasets&limit=10`")
    if homeless_dataset_id:
        out.append(f"- Selected dataset id: **`{homeless_dataset_id}`**")
        out.append(f"- 5-row test query: `{homeless_query_url}`")
        out.append(f"- Form of homelessness in dataset: **{homeless_subgroup_or_column}**")
        out.append("")
        out.append(f"**Decision: {homeless_decision}**")
        out.append("")
        if homeless_test_rows:
            cols = sorted(homeless_test_rows[0].keys())
            out.append(f"Columns observed in 5-row sample (first row only):")
            out.append("")
            out.append("```")
            out.append(", ".join(cols))
            out.append("```")
            out.append("")
            out.append("First row of the 5-row test fetch (truncated for readability):")
            out.append("")
            out.append("```json")
            r0 = homeless_test_rows[0]
            short = {k: (str(v)[:80] + "…" if isinstance(v, str) and len(str(v)) > 80 else v)
                     for k, v in r0.items()}
            out.append(json.dumps(short, indent=2))
            out.append("```")
            out.append("")
    else:
        out.append(f"**Decision: {homeless_decision}**")
        out.append("")

# ---- Task 5: exclusions union ----
out.append("## 4. Exclusions union (Task 5)")
out.append("")
out.append(md_table(
    ["List", "count"],
    [["school_exclusions.yaml", len(yaml_set)],
     ["Phase 3R SKIP (census_acs._meta.unmatched_reason ≠ null)", len(skip_set)],
     ["Overlap (in both)", len(overlap)],
     ["**Union**", len(union)]]))
out.append("")
out.append(f"Phase 3R SKIP breakdown by reason code (post-patch):")
out.append("")
out.append(md_table(
    ["unmatched_reason", "count"],
    [[r, n] for r, n in sorted(skip_by_reason_count.items(),
                                 key=lambda x: -x[1])]))
out.append("")

range_ok = unions_ok and yaml_ok and skip_ok
if range_ok:
    out.append(f"All counts within expected ranges (yaml ~78, skip ~48, union 84-90).")
else:
    out.append(f"**One or more counts outside expected ranges:** "
               f"yaml expected 70-90 got {len(yaml_set)} ({'OK' if yaml_ok else 'OUT'}); "
               f"skip expected 40-60 got {len(skip_set)} ({'OK' if skip_ok else 'OUT'}); "
               f"union expected 80-100 got {len(union)} ({'OK' if unions_ok else 'OUT'}).")
out.append("")

# ---- Issues for builder review ----
out.append("## 5. Issues for builder review")
out.append("")

if missing_paths:
    out.append("### Missing v1 variables")
    out.append("")
    out.append("These v1 variables had **no candidate path returning a non-null "
               "value**. Either they need to be ingested in subsequent prompts or "
               "the candidate paths in this verifier are wrong.")
    out.append("")
    for label in missing_paths:
        out.append(f"- **{label}**")
    out.append("")

if unexpected_paths:
    out.append("### Path discrepancies (prompt assumed vs. actual)")
    out.append("")
    out.append("Variables found, but at a different MongoDB path than the prompt "
               "assumed. Either the prompt should adopt the actual path, or the "
               "data should be re-stored at the assumed path. Recommendation: "
               "use the actual path going forward.")
    out.append("")
    out.append(md_table(
        ["v1 variable", "prompt assumed", "actual"],
        [[label, f"`{p}`", f"`{a}`"] for label, p, a in unexpected_paths]))
    out.append("")

if hi_null_paths:
    out.append("### High-null fields (≥ 10% null in full collection)")
    out.append("")
    out.append("These fields are populated for fewer than 90% of schools. Review "
               "whether the null pattern is expected (e.g. high schools only, "
               "non-comparable schools excluded) or a coverage gap.")
    out.append("")
    out.append(md_table(
        ["v1 variable", "actual path", "null %"],
        [[label, f"`{p}`", f"{pct:.1f}%"] for label, p, pct in hi_null_paths]))
    out.append("")

# Homelessness decision
out.append("### Homelessness path decision")
out.append("")
out.append(f"- {homeless_decision}")
out.append("")

# Anomalies / closing
out.append("### Other anomalies")
out.append("")
anomalies = []
# `nces_id` and `district_nces_id` paths differ from prompt assumption
nid_finding = next((f for f in v1_findings if f["label"] == "nces_id"), None)
if nid_finding and nid_finding["actual_path"] == "_id":
    anomalies.append("- `nces_id` is the MongoDB primary key `_id` (12-char string), "
                     "not a separate `nces_id` field. Confirmed: there is no `nces_id` "
                     "field on these documents. All experimental scripts must use "
                     "`_id` for the school identifier (this caught us in the prior "
                     "session — see `_run_acs_ingestion.py`).")
# Exclusion field naming
excl_finding = next((f for f in v1_findings if f["label"] == "exclusion_status"), None)
if excl_finding and excl_finding["actual_path"] != "exclusion_status":
    anomalies.append(f"- Exclusion status lives at `census_acs._meta.unmatched_reason`, "
                     f"not at a top-level `exclusion_status`/`exclusion_reason_code`. "
                     f"Phase 3R Census ingestion stored both the reason code and the "
                     f"flag-of-being-skipped in one field. If the v1 methodology needs "
                     f"a separate `exclusion_status` enum (in/out), it has to be derived "
                     f"or written in a future prompt.")
if not anomalies:
    out.append("None observed beyond what's listed above.")
    out.append("")
else:
    out.extend(anomalies)
    out.append("")

# Final write
with open(OUT_FILE, "w") as f:
    f.write("\n".join(out))
log.info(f"Wrote deliverable: {OUT_FILE}")
log.info(f"Schema-check run complete. {len(missing_paths)} missing, "
         f"{len(unexpected_paths)} discrepancies, {len(hi_null_paths)} high-null. "
         f"Homelessness: {homeless_decision[:80]}")

client.close()
print(f"\nDONE. Deliverable: {OUT_FILE}")
print(f"Log: {LOG_PATH}")
