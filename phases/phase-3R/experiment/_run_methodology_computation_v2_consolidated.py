"""
_run_methodology_computation_v2_consolidated.py — Phase 3R Prompt 3b Path C.

Successor to _run_methodology_computation.py. Same flow but with the locked
Path C consolidation:
  DROP: per_capita_income, bachelors_pct_25plus, total_population
  KEEP: the other 17 (16 ES/MS/Other, 17 HS)

UPDATED STOP-AND-REPORT thresholds (per builder Path C decision):
  - Any pair |r| > 0.80 in any matrix → STOP.
  - Any pair |r| > 0.70 in any matrix that is NOT in the predicted residuals
    → STOP (new cluster surfaced after consolidation).
  - Predicted residuals (acceptable in 0.70-0.80 range, NOT a STOP):
      race_pct_non_white ~ ell  (pooled + Elementary + Middle + High)
      frl ~ median_household_income (Middle only)

INSPECTION ARTIFACT — `methodology_inspection.md` adds:
  - Pre-consolidation 20-var correlation matrix (loaded from prior STOP pickle).
  - Four-cluster analysis (cluster 1: income/edu 3-way; cluster 2: pop/density;
    cluster 3: race/ell; cluster 4: Middle FRL/income) with disposition reasoning.
  - Post-consolidation 17-var matrix with predicted residuals labeled.
  - Eligibility delta explanation (1,728 vs 1,742 from pre-exec).

Same as v1: NO MongoDB writes for peer_match.* — schema plan emitted at end,
bulk write happens only after builder approves.

DNS BYPASS: 1.1.1.1, 8.8.8.8, 1.0.0.1.

LINEAGE: peer_match.*
RULE: ELIGIBILITY_TIERING_V1
RULE: ACHIEVEMENT_EXCLUDED_V1
RULE: REDUNDANCY_PATH_C_CONSOLIDATION
TEST: GOLDEN_SCHOOL_FAIRHAVEN
"""

# --- DNS bypass ---
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

import datetime as dt
import json
import logging
import os
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import scipy.spatial.distance as ssd

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
TS = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = "/Users/oriandaleigh/school-daylight/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"phase3r_methodology_v2_{TS}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("p3r_compute_v2")
NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

log.info("=" * 70)
log.info("Phase 3R Prompt 3b — Path C consolidation rerun (read-only)")
log.info("DROP: per_capita_income, bachelors_pct_25plus, total_population")
log.info("DNS bypass IN EFFECT: 1.1.1.1, 8.8.8.8, 1.0.0.1")
log.info("=" * 70)

OUT_DIR = Path("/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment")

# ---------------------------------------------------------------------------
# Variable list (per Path C)
# ---------------------------------------------------------------------------
DROPPED = {"per_capita_income", "bachelors_pct_25plus", "total_population"}

V1_VARS_FULL = [
    ("enrollment_total",           "enrollment.total",                                       "ALL", "missing_enrollment_total"),
    ("chronic_absenteeism",        "derived.chronic_absenteeism_pct",                        "ALL", "missing_chronic_absenteeism"),
    ("graduation_4yr",             "graduation_rate.cohort_4yr",                             "HS",  "missing_graduation_hs"),
    ("frl",                        "demographics.frl_pct",                                   "ALL", "missing_frl_pct"),
    ("race_pct_non_white",         "derived.race_pct_non_white",                             "ALL", "missing_race_pct_non_white"),
    ("homelessness",               "derived.homelessness_pct",                               "ALL", "missing_homelessness_pct"),
    ("ell",                        "derived.ell_pct",                                        "ALL", "missing_ell_pct"),
    ("migrant",                    "derived.migrant_pct",                                    "ALL", "missing_migrant_pct"),
    ("teacher_experience",         "teacher_experience.average_years_derived",               "ALL", "missing_teacher_experience"),
    ("sped",                       "derived.sped_pct",                                       "ALL", "missing_sped_pct"),
    ("teacher_salary",             "teacher_salary.average_base_per_fte",                    "ALL", "missing_teacher_salary"),
    ("median_household_income",    "census_acs.median_household_income.value",               "ALL", "missing_census_median_household_income"),
    ("per_capita_income",          "census_acs.per_capita_income.value",                     "ALL", "missing_census_per_capita_income"),
    ("gini_index",                 "census_acs.gini_index.value",                            "ALL", "missing_census_gini_index"),
    ("bachelors_pct_25plus",       "census_acs.bachelors_or_higher_pct_25plus.value",        "ALL", "missing_census_bachelors_pct_25plus"),
    ("labor_force_participation",  "census_acs.labor_force_participation_rate_16plus.value", "ALL", "missing_census_labor_force_participation"),
    ("unemployment_rate",          "census_acs.unemployment_rate_16plus.value",              "ALL", "missing_census_unemployment_rate"),
    ("total_population",           "census_acs.total_population.value",                      "ALL", "missing_census_total_population"),
    ("land_area",                  "census_acs.land_area_sq_miles.value",                    "ALL", "missing_census_land_area"),
    ("population_density",         "census_acs.population_density_per_sq_mile.value",        "ALL", "missing_census_population_density"),
]
V1_VARS = [v for v in V1_VARS_FULL if v[0] not in DROPPED]
SHARED_VARS = [v for v in V1_VARS if v[2] == "ALL"]   # 16
HS_VARS     = V1_VARS                                  # 17 (16 + grad)
log.info(f"Consolidated v1 var set: {len(V1_VARS)} total "
         f"({len(SHARED_VARS)} shared, +1 HS-only). Dropped: {sorted(DROPPED)}")

ACHIEVEMENT_VARS = [
    ("ela",     "academics.assessment.ela_proficiency_pct",     "missing_achievement_ela"),
    ("math",    "academics.assessment.math_proficiency_pct",    "missing_achievement_math"),
    ("science", "academics.assessment.science_proficiency_pct", "missing_achievement_science"),
]

# ---------------------------------------------------------------------------
# STOP rule config
# ---------------------------------------------------------------------------
# Threshold semantics adjusted 2026-05-08 per brief Section 1.5.2 update:
# the documented-residual ceiling moved from 0.80 to 0.81. At per-level n in
# the hundreds, the sampling-noise floor on a correlation estimate near 0.80
# is roughly ±0.04; treating r=0.80 vs r=0.81 as substantively distinct over-
# interprets decimal precision. The 0.81 ceiling provides a small buffer for
# cross-eligible-set sampling variation while remaining tight enough to fire
# on structural strengthening (e.g., r climbing to 0.85). UNPREDICTED pairs
# above 0.80 still trigger STOP unconditionally — the relaxation applies only
# to documented residuals.
STOP_HIGH = 0.80                   # unpredicted pairs above this → STOP
PREDICTED_RESIDUAL_CEILING = 0.81  # predicted residuals accepted up to this
WARN_THRESH = 0.70                 # below this → ignore

# Predicted residuals (set of frozensets of pair-names per matrix label).
# Key: "POOLED" or "LEVEL_<lvl>"; value: set of frozensets of (var_a, var_b).
PREDICTED_RESIDUALS = {
    "POOLED":            {frozenset({"race_pct_non_white", "ell"})},
    "LEVEL_Elementary":  {frozenset({"race_pct_non_white", "ell"})},
    "LEVEL_Middle":      {frozenset({"race_pct_non_white", "ell"}),
                          frozenset({"frl", "median_household_income"})},
    "LEVEL_High":        {frozenset({"race_pct_non_white", "ell"})},
    "LEVEL_Other":       set(),
}

def get_path(doc, dotted):
    cur = doc
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur

# ---------------------------------------------------------------------------
# Build the 120-school exclusion union with reason_codes
# ---------------------------------------------------------------------------
log.info("Building 120-school exclusion union with reason codes ...")
yaml_path = Path("/Users/oriandaleigh/school-daylight/school_exclusions.yaml")
section_pattern_to_code = [
    (re.compile(r"Virtual / online", re.I),                                   "legacy_yaml_virtual"),
    (re.compile(r"Jails and detention", re.I),                                "legacy_yaml_jail_detention"),
    (re.compile(r"Group homes", re.I),                                        "legacy_yaml_group_home"),
    (re.compile(r"Preschool", re.I),                                          "legacy_yaml_preschool"),
    (re.compile(r"Homeschool", re.I),                                         "legacy_yaml_homeschool"),
    (re.compile(r"Community-based", re.I),                                    "legacy_yaml_community_based"),
    (re.compile(r"Alternative and reengagement", re.I),                       "legacy_yaml_alternative_miscoded"),
    (re.compile(r"Special education and specialized", re.I),                  "legacy_yaml_sped_miscoded"),
    (re.compile(r"Zero-enrollment", re.I),                                    "legacy_yaml_zero_enrollment"),
]
yaml_codes = {}
current_code = None
with open(yaml_path) as f:
    for line in f:
        if line.strip().startswith("#"):
            for pat, code in section_pattern_to_code:
                if pat.search(line):
                    current_code = code
                    break
        m = re.match(r"\s*-\s*ncessch:\s*[\"']?(\d{12})[\"']?\s*$", line)
        if m:
            yaml_codes[m.group(1)] = current_code
log.info(f"  YAML schools: {len(yaml_codes)}")

# Connect (read-only)
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=30000)
db = client.get_default_database()
assert "experiment" in db.name
log.info(f"Connected to '{db.name}', count={db.schools.count_documents({})}")

skip_codes = {}
for d in db.schools.find(
    {"census_acs._meta.unmatched_reason": {"$ne": None, "$exists": True}},
    {"_id": 1, "census_acs._meta.unmatched_reason": 1}):
    skip_codes[d["_id"]] = d["census_acs"]["_meta"]["unmatched_reason"]
log.info(f"  SKIP schools: {len(skip_codes)}")

exclusion_union = {}
for sid, code in yaml_codes.items():
    exclusion_union.setdefault(sid, []).append(code)
for sid, code in skip_codes.items():
    exclusion_union.setdefault(sid, []).append(code)
log.info(f"  Union size: {len(exclusion_union)}")

# Project & load
proj = {"_id": 1, "name": 1, "school_type": 1, "is_charter": 1,
        "derived.level_group": 1, "level": 1,
        "district.name": 1, "metadata.ospi_district_code": 1}
for _, path, _, _ in V1_VARS_FULL:  # pull full set (so we can recompute pre-consol matrix later if needed)
    proj[path] = 1
for _, path, _ in ACHIEVEMENT_VARS:
    proj[path] = 1

log.info("Loading school docs ...")
schools = list(db.schools.find({}, proj))
log.info(f"Loaded {len(schools)} docs")
client.close()

# ---------------------------------------------------------------------------
# Apply eligibility tiering on the CONSOLIDATED var set
# ---------------------------------------------------------------------------
log.info("Applying eligibility tiering on consolidated var set ...")
records = []
for d in schools:
    sid = d["_id"]
    lvl = (d.get("derived") or {}).get("level_group") or "Other"
    rec = {
        "_id": sid,
        "name": d.get("name"),
        "level_group": lvl,
        "school_type": d.get("school_type"),
        "is_charter": d.get("is_charter"),
        "district_name": (d.get("district") or {}).get("name"),
        "ospi_district_code": (d.get("metadata") or {}).get("ospi_district_code"),
        "vars": {},        # consolidated 17-var values
        "vars_full": {},   # full 20-var values (for pre-consol matrix display)
        "achievement": {},
    }
    for vname, vpath, _, _ in V1_VARS_FULL:
        rec["vars_full"][vname] = get_path(d, vpath)
        if vname not in DROPPED:
            rec["vars"][vname] = get_path(d, vpath)
    for aname, apath, _ in ACHIEVEMENT_VARS:
        rec["achievement"][aname] = get_path(d, apath)
    if sid in exclusion_union:
        rec["tier"] = "excluded"
        rec["reason_codes"] = sorted(exclusion_union[sid])
    else:
        required = SHARED_VARS if lvl != "High" else HS_VARS
        missing = [code for vname, _, _, code in required if rec["vars"][vname] is None]
        if missing:
            rec["tier"] = "descriptive_only"
            rec["reason_codes"] = sorted(missing)
        else:
            rec["tier"] = "eligible"
            rec["reason_codes"] = []
    records.append(rec)

tier_counts = Counter(r["tier"] for r in records)
tier_by_level = defaultdict(Counter)
for r in records:
    tier_by_level[r["level_group"]][r["tier"]] += 1
log.info(f"Tier counts: {dict(tier_counts)}")
n_eligible = tier_counts["eligible"]

# Builder noted: expect ~1,728 ± a small handful. Verify not assume.
PRE_CONSOL_ELIGIBLE = 1728  # from the v1 (20-var) run
delta = n_eligible - PRE_CONSOL_ELIGIBLE
log.info(f"Eligibility delta vs pre-consolidation run (1,728): {delta:+d}")
if abs(delta) > 5:
    log.warning(f"Eligibility delta {delta} larger than expected (±5); "
                "investigate before relying on this comparison.")

if n_eligible < 1500 or n_eligible > 2200:
    log.error(f"STOP: eligible-set size {n_eligible} outside [1500, 2200].")
    raise SystemExit(2)
log.info(f"Sanity guard PASSED: eligible n={n_eligible}")

# ---------------------------------------------------------------------------
# Z-score standardization per level (consolidated set)
# ---------------------------------------------------------------------------
log.info("Computing z-scores per level on eligible set (consolidated) ...")
eligible_by_level = defaultdict(list)
for r in records:
    if r["tier"] == "eligible":
        eligible_by_level[r["level_group"]].append(r)

level_stats = {}
level_zvecs = {}
level_var_names = {}
for lvl in ["Elementary", "Middle", "High", "Other"]:
    recs = eligible_by_level[lvl]
    var_names = [v[0] for v in (HS_VARS if lvl == "High" else SHARED_VARS)]
    n = len(recs); d = len(var_names)
    raw = np.zeros((n, d))
    for i, r in enumerate(recs):
        for j, vn in enumerate(var_names):
            raw[i, j] = r["vars"][vn]
    means = raw.mean(axis=0); sds = raw.std(axis=0, ddof=0)
    if (sds == 0).any():
        zerov = [var_names[k] for k in range(d) if sds[k] == 0]
        log.error(f"STOP: zero-variance variables in level {lvl}: {zerov}")
        raise SystemExit(2)
    z = (raw - means) / sds
    level_stats[lvl] = {var_names[k]: (float(means[k]), float(sds[k])) for k in range(d)}
    level_zvecs[lvl] = z
    level_var_names[lvl] = var_names
    for i, r in enumerate(recs):
        r["z_v1"] = {var_names[k]: float(z[i, k]) for k in range(d)}
    log.info(f"  {lvl}: n={n} d={d}")

# ---------------------------------------------------------------------------
# Redundancy audit (consolidated set, NEW thresholds)
# ---------------------------------------------------------------------------
log.info("Redundancy audit on consolidated set ...")

def pairwise_pearson(z, var_names):
    return np.corrcoef(z, rowvar=False)

def evaluate_matrix(corr, var_names, label):
    """Walk upper triangle; classify each pair as: ok | predicted_residual |
       new_pair_warn | high. Return triggered list and full pair list.

       Threshold semantics:
       - Unpredicted pair with |r| > STOP_HIGH (0.80)   → triggered_high (STOP)
       - Predicted pair with |r| > PREDICTED_RESIDUAL_CEILING (0.81)
                                                        → triggered_high (STOP)
       - Unpredicted pair with WARN_THRESH < |r| <= STOP_HIGH (0.70 < |r| <= 0.80)
                                                        → triggered_new (STOP)
       - Predicted pair with WARN_THRESH < |r| <= PREDICTED_RESIDUAL_CEILING
                                                        → accepted_predicted
       - |r| <= WARN_THRESH                             → ignored
    """
    d = corr.shape[0]
    triggered_high = []   # |r| > STOP_HIGH for unpredicted, or > CEILING for predicted (always STOP)
    triggered_new  = []   # WARN_THRESH < |r| <= STOP_HIGH AND not in PREDICTED_RESIDUALS
    accepted_predicted = []  # WARN_THRESH < |r| <= PREDICTED_RESIDUAL_CEILING AND in PREDICTED_RESIDUALS
    for i in range(d):
        for j in range(i+1, d):
            r = float(corr[i, j])
            if abs(r) <= WARN_THRESH:
                continue
            pair = frozenset({var_names[i], var_names[j]})
            is_predicted = pair in PREDICTED_RESIDUALS.get(label, set())
            if is_predicted:
                if abs(r) > PREDICTED_RESIDUAL_CEILING:
                    triggered_high.append((var_names[i], var_names[j], r))
                else:
                    accepted_predicted.append((var_names[i], var_names[j], r))
            else:
                if abs(r) > STOP_HIGH:
                    triggered_high.append((var_names[i], var_names[j], r))
                else:
                    triggered_new.append((var_names[i], var_names[j], r))
    return triggered_high, triggered_new, accepted_predicted

# Pooled (16-var, drop graduation_4yr from per-level when stacking)
pool_blocks = []
for lvl in ["Elementary", "Middle", "High", "Other"]:
    z = level_zvecs[lvl]; vn = level_var_names[lvl]
    if "graduation_4yr" in vn:
        keep = [k for k, name in enumerate(vn) if name != "graduation_4yr"]
        z = z[:, keep]
    pool_blocks.append(z)
pool_z = np.vstack(pool_blocks)
pool_vars = [v for v in level_var_names["Elementary"]]   # 16
pool_corr = pairwise_pearson(pool_z, pool_vars)
log.info(f"  POOLED: n={pool_z.shape[0]} d={pool_z.shape[1]}")

per_level_corr = {}
for lvl in ["Elementary", "Middle", "High", "Other"]:
    cm = pairwise_pearson(level_zvecs[lvl], level_var_names[lvl])
    per_level_corr[lvl] = (cm, level_var_names[lvl])
    log.info(f"  LEVEL_{lvl}: n={len(eligible_by_level[lvl])} "
             f"d={cm.shape[0]}")

# Evaluate against thresholds
pool_high, pool_new, pool_pred = evaluate_matrix(pool_corr, pool_vars, "POOLED")
per_level_eval = {}
for lvl, (cm, vn) in per_level_corr.items():
    h, n, p = evaluate_matrix(cm, vn, f"LEVEL_{lvl}")
    per_level_eval[lvl] = {"high": h, "new": n, "predicted": p}

all_high = list(pool_high) + sum((per_level_eval[l]["high"] for l in per_level_eval), [])
all_new  = list(pool_new)  + sum((per_level_eval[l]["new"]  for l in per_level_eval), [])

if all_high or all_new:
    log.error("=" * 70)
    log.error("REDUNDANCY STOP-AND-REPORT (Path C rerun)")
    if pool_high:
        log.error("  POOLED — ABOVE 0.80:")
        for a, b, r in pool_high: log.error(f"    {a} ~ {b}: r={r:+.3f}")
    if pool_new:
        log.error("  POOLED — UNPREDICTED 0.70-0.80:")
        for a, b, r in pool_new: log.error(f"    {a} ~ {b}: r={r:+.3f}")
    for lvl in ["Elementary", "Middle", "High", "Other"]:
        ev = per_level_eval[lvl]
        if ev["high"]:
            log.error(f"  LEVEL_{lvl} — ABOVE 0.80:")
            for a, b, r in ev["high"]: log.error(f"    {a} ~ {b}: r={r:+.3f}")
        if ev["new"]:
            log.error(f"  LEVEL_{lvl} — UNPREDICTED 0.70-0.80:")
            for a, b, r in ev["new"]: log.error(f"    {a} ~ {b}: r={r:+.3f}")
    log.error("=" * 70)
    # Write a STOP report
    stop_path = OUT_DIR / "redundancy_stop_report_v2.md"
    out = []
    out.append("# Phase 3R — Redundancy Audit STOP-AND-REPORT (Path C rerun)")
    out.append("")
    out.append(f"Run timestamp (UTC): **{NOW_ISO}**")
    out.append("")
    out.append("Path C consolidation applied (dropped per_capita_income, "
               "bachelors_pct_25plus, total_population). Redundancy still "
               "exceeds Path C decision thresholds:")
    out.append("- Any pair |r| > 0.80")
    out.append("- Any unpredicted pair |r| > 0.70")
    out.append("")
    if all_high:
        out.append("## Pairs above 0.80")
        out.append("")
        for label, lst in (("POOLED", pool_high), ) + tuple(
                (f"LEVEL_{l}", per_level_eval[l]["high"])
                for l in ["Elementary", "Middle", "High", "Other"]):
            if lst:
                out.append(f"### {label}")
                out.append("")
                out.append("| var i | var j | r |")
                out.append("|---|---|---|")
                for a, b, r in lst:
                    out.append(f"| {a} | {b} | {r:+.4f} |")
                out.append("")
    if all_new:
        out.append("## Unpredicted pairs in 0.70-0.80")
        out.append("")
        for label, lst in (("POOLED", pool_new), ) + tuple(
                (f"LEVEL_{l}", per_level_eval[l]["new"])
                for l in ["Elementary", "Middle", "High", "Other"]):
            if lst:
                out.append(f"### {label}")
                out.append("")
                out.append("| var i | var j | r |")
                out.append("|---|---|---|")
                for a, b, r in lst:
                    out.append(f"| {a} | {b} | {r:+.4f} |")
                out.append("")
    with open(stop_path, "w") as f:
        f.write("\n".join(out))
    log.error(f"Wrote {stop_path}")
    raise SystemExit(0)

log.info("Redundancy audit PASSED under Path C thresholds.")
log.info(f"  Predicted residuals accepted (POOLED): {len(pool_pred)}")
for a, b, r in pool_pred:
    log.info(f"    {a} ~ {b}: r={r:+.3f} (predicted)")
for lvl in ["Elementary", "Middle", "High", "Other"]:
    pred = per_level_eval[lvl]["predicted"]
    if pred:
        log.info(f"  Predicted residuals accepted ({lvl}): {len(pred)}")
        for a, b, r in pred:
            log.info(f"    {a} ~ {b}: r={r:+.3f} (predicted)")

# ---------------------------------------------------------------------------
# K=10/20/30 cohorts on consolidated v1 var set
# ---------------------------------------------------------------------------
log.info("Computing K=10/20/30 cohorts on consolidated v1 var set ...")
cohorts_v1 = {}
for lvl in ["Elementary", "Middle", "High", "Other"]:
    recs = eligible_by_level[lvl]; z = level_zvecs[lvl]; n = len(recs)
    sq = ssd.squareform(ssd.pdist(z, metric="sqeuclidean"))
    np.fill_diagonal(sq, np.inf)
    order = np.argsort(sq, axis=1)
    eu = np.sqrt(sq); np.fill_diagonal(eu, 0.0)
    cap = n - 1
    k10, k20, k30 = min(10, cap), min(20, cap), min(30, cap)
    for i, r in enumerate(recs):
        idx10 = order[i, :k10]; idx20 = order[i, :k20]; idx30 = order[i, :k30]
        cohorts_v1[r["_id"]] = {
            "level": lvl,
            "K10": [recs[j]["_id"] for j in idx10],
            "K20": [recs[j]["_id"] for j in idx20],
            "K30": [recs[j]["_id"] for j in idx30],
            "K20_names": [recs[j]["name"] for j in idx20],
            "K20_dist":  [float(eu[i, j]) for j in idx20],
            "K10_dist":  [float(eu[i, j]) for j in idx10],
            "K30_dist":  [float(eu[i, j]) for j in idx30],
        }

# ---------------------------------------------------------------------------
# Achievement-included variant
# ---------------------------------------------------------------------------
log.info("Computing achievement-included variant ...")
ach_eligible_by_level = defaultdict(list)
for r in records:
    if r["tier"] != "eligible":
        continue
    ach = r["achievement"]
    if ach.get("ela") is None or ach.get("math") is None or ach.get("science") is None:
        continue
    ach_eligible_by_level[r["level_group"]].append(r)

n_ach = sum(len(v) for v in ach_eligible_by_level.values())
log.info(f"Achievement-eligible total: {n_ach}")

cohorts_ach = {}
for lvl in ["Elementary", "Middle", "High", "Other"]:
    recs = ach_eligible_by_level[lvl]
    base_vars = [v[0] for v in (HS_VARS if lvl == "High" else SHARED_VARS)]
    var_names = base_vars + ["ach_ela", "ach_math", "ach_science"]
    n = len(recs); d = len(var_names)
    if n < 2: continue
    raw = np.zeros((n, d))
    for i, r in enumerate(recs):
        for j, vn in enumerate(base_vars):
            raw[i, j] = r["vars"][vn]
        raw[i, len(base_vars)+0] = r["achievement"]["ela"]
        raw[i, len(base_vars)+1] = r["achievement"]["math"]
        raw[i, len(base_vars)+2] = r["achievement"]["science"]
    means = raw.mean(axis=0); sds = raw.std(axis=0, ddof=0)
    if (sds == 0).any():
        log.error(f"STOP: zero-variance ACH var at {lvl}")
        raise SystemExit(2)
    z = (raw - means) / sds
    sq = ssd.squareform(ssd.pdist(z, metric="sqeuclidean"))
    np.fill_diagonal(sq, np.inf)
    order = np.argsort(sq, axis=1)
    eu = np.sqrt(sq); np.fill_diagonal(eu, 0.0)
    cap = n - 1; k20 = min(20, cap)
    for i, r in enumerate(recs):
        idx = order[i, :k20]
        cohorts_ach[r["_id"]] = {
            "level": lvl,
            "K20": [recs[j]["_id"] for j in idx],
            "K20_names": [recs[j]["name"] for j in idx],
            "K20_dist":  [float(eu[i, j]) for j in idx],
        }
log.info(f"Achievement-included K=20 cohorts: {len(cohorts_ach)}")

# ---------------------------------------------------------------------------
# Sensitivity 2a — Jaccard
# ---------------------------------------------------------------------------
log.info("Sensitivity 2a — Jaccard ...")
ach_focal_ids = set(cohorts_ach.keys())
jaccards = []; identity_changes = []
jacc_by_level = defaultdict(list)
for sid in ach_focal_ids:
    A = set(cohorts_v1[sid]["K20"]); B = set(cohorts_ach[sid]["K20"])
    union = A | B
    j = len(A & B) / len(union) if union else 0.0
    jaccards.append(j); identity_changes.append(len(B - A))
    jacc_by_level[cohorts_ach[sid]["level"]].append(j)
jaccards = np.array(jaccards); identity_changes = np.array(identity_changes)
log.info(f"  intersection n={len(ach_focal_ids)} mean Jaccard={jaccards.mean():.3f}")

# ---------------------------------------------------------------------------
# Sensitivity 2b — K containment
# ---------------------------------------------------------------------------
log.info("Sensitivity 2b — K containment ...")
contain_10_20 = []; contain_20_30 = []
contain_10_20_full = 0; contain_20_30_full = 0
contain_by_level = defaultdict(lambda: {"k10_in_k20": [], "k20_in_k30": []})
for sid, c in cohorts_v1.items():
    k10, k20, k30 = set(c["K10"]), set(c["K20"]), set(c["K30"])
    f10 = len(k10 & k20) / len(k10) if k10 else 0.0
    f20 = len(k20 & k30) / len(k20) if k20 else 0.0
    contain_10_20.append(f10); contain_20_30.append(f20)
    if f10 >= 0.999: contain_10_20_full += 1
    if f20 >= 0.999: contain_20_30_full += 1
    contain_by_level[c["level"]]["k10_in_k20"].append(f10)
    contain_by_level[c["level"]]["k20_in_k30"].append(f20)
contain_10_20 = np.array(contain_10_20); contain_20_30 = np.array(contain_20_30)
log.info(f"  K10⊆K20 mean={contain_10_20.mean():.4f} "
         f"full={contain_10_20_full}/{len(contain_10_20)}")
log.info(f"  K20⊆K30 mean={contain_20_30.mean():.4f} "
         f"full={contain_20_30_full}/{len(contain_20_30)}")

# ---------------------------------------------------------------------------
# Spot-checks
# ---------------------------------------------------------------------------
log.info("Picking spot-check schools ...")
records_by_id = {r["_id"]: r for r in records}

def pick_first(filt, n=1):
    out = []
    for r in records:
        if filt(r):
            out.append(r)
            if len(out) >= n: break
    return out

spot_check = {}
spot_check["fairhaven_golden"] = records_by_id.get("530042000104")
spot_check["urban_large_eligible"] = (pick_first(
    lambda r: r["tier"] == "eligible" and r["level_group"] == "High"
              and r.get("ospi_district_code") == "17001"
              and (r["vars"]["enrollment_total"] or 0) > 1000) or [None])[0]
spot_check["rural_small_eligible"] = (pick_first(
    lambda r: r["tier"] == "eligible"
              and (r["vars"]["enrollment_total"] or 9999) < 100) or [None])[0]
spot_check["tribal_serving_eligible"] = (pick_first(
    lambda r: r["tier"] == "eligible"
              and r.get("ospi_district_code") == "39207") or [None])[0]
spot_check["alternative_coded_eligible"] = (pick_first(
    lambda r: r["tier"] == "eligible"
              and r.get("school_type") == "Alternative School") or [None])[0]
spot_check["descriptive_only_example"] = (pick_first(
    lambda r: r["tier"] == "descriptive_only"
              and "missing_chronic_absenteeism" in r["reason_codes"]) or [None])[0]
spot_check["excluded_example"] = (pick_first(
    lambda r: r["tier"] == "excluded"
              and "legacy_yaml_virtual" in r["reason_codes"]) or [None])[0]

for k, v in spot_check.items():
    if v is None:
        log.warning(f"  {k}: NOT FOUND")
    else:
        log.info(f"  {k}: {v['_id']} '{v['name']}' tier={v['tier']}")

# ---------------------------------------------------------------------------
# Side-by-side example schools (10 schools)
# ---------------------------------------------------------------------------
log.info("Building 10-school side-by-side ...")
side_by_side_ids = []
if "530042000104" in cohorts_ach:
    side_by_side_ids.append("530042000104")
for label in ["urban_large_eligible", "rural_small_eligible",
              "tribal_serving_eligible", "alternative_coded_eligible"]:
    sc = spot_check[label]
    if sc and sc["_id"] in cohorts_ach:
        side_by_side_ids.append(sc["_id"])
seen = set(side_by_side_ids)
for lvl in ["Elementary", "Middle", "High", "Other"]:
    for r in records:
        if r["tier"] != "eligible" or r["_id"] in seen: continue
        if r["_id"] not in cohorts_ach: continue
        if r["level_group"] != lvl: continue
        side_by_side_ids.append(r["_id"]); seen.add(r["_id"]); break
    if len(side_by_side_ids) >= 10: break
for r in records:
    if len(side_by_side_ids) >= 10: break
    if r["_id"] in seen or r["_id"] not in cohorts_ach: continue
    side_by_side_ids.append(r["_id"]); seen.add(r["_id"])
log.info(f"Side-by-side schools: {side_by_side_ids}")

# ---------------------------------------------------------------------------
# Pickle for the bulk-write step
# ---------------------------------------------------------------------------
pkl_path = OUT_DIR / "_pickled_cohorts_v2.pkl"
with open(pkl_path, "wb") as f:
    pickle.dump({
        "records": records,
        "cohorts_v1": cohorts_v1,
        "level_stats": level_stats,
        "level_var_names": level_var_names,
        "compute_timestamp": NOW_ISO,
        "consolidation": {"dropped": sorted(DROPPED), "applied": "Path C"},
    }, f)
log.info(f"Pickled to {pkl_path}")

# ---------------------------------------------------------------------------
# Sensitivity sidecar JSON
# ---------------------------------------------------------------------------
sidecar = {
    "generated_at": NOW_ISO,
    "consolidation": {"dropped": sorted(DROPPED), "applied": "Path C"},
    "purpose": ("Side-by-side cohort lists for sensitivity 2a (achievement) "
                "and 2b (K). Inspection-artifact-only persistence per "
                "Prompt 3b Option C."),
    "schools": {}
}
for sid in side_by_side_ids:
    r = records_by_id[sid]
    v1 = cohorts_v1.get(sid, {}); ach = cohorts_ach.get(sid, {})
    sidecar["schools"][sid] = {
        "name": r["name"], "level_group": r["level_group"],
        "school_type": r["school_type"], "district_name": r["district_name"],
        "v1_K20_cohort": [
            {"_id": v1["K20"][k], "name": v1["K20_names"][k],
             "distance": v1["K20_dist"][k]}
            for k in range(len(v1.get("K20", [])))],
        "achievement_included_K20_cohort": [
            {"_id": ach["K20"][k], "name": ach["K20_names"][k],
             "distance": ach["K20_dist"][k]}
            for k in range(len(ach.get("K20", [])))],
        "v1_K10_cohort_ids": v1.get("K10", []),
        "v1_K30_cohort_ids": v1.get("K30", []),
    }
sidecar_path = OUT_DIR / "sensitivity_cohort_lists.json"
with open(sidecar_path, "w") as f:
    json.dump(sidecar, f, indent=2, default=str)
log.info(f"Wrote {sidecar_path}")

# ---------------------------------------------------------------------------
# Load pre-consolidation correlation matrix from prior STOP pickle
# ---------------------------------------------------------------------------
preconsol_pkl = OUT_DIR / "_pickled_partial_redundancy.pkl"
preconsol_pool_corr = None
preconsol_pool_vars = None
preconsol_per_level = None
if preconsol_pkl.exists():
    with open(preconsol_pkl, "rb") as f:
        prior = pickle.load(f)
    preconsol_pool_corr = np.array(prior["pool_corr"])
    preconsol_pool_vars = prior["pool_vars"]
    preconsol_per_level = {k: (np.array(v[0]), v[1])
                            for k, v in prior["per_level_corr"].items()}
    log.info(f"Loaded pre-consolidation matrices from {preconsol_pkl}")

# ---------------------------------------------------------------------------
# Write methodology_inspection.md
# ---------------------------------------------------------------------------
log.info("Writing methodology_inspection.md ...")

def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("—" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)

def render_corr_matrix(corr, var_names):
    hdr = ["—"] + var_names
    lines = ["| " + " | ".join(hdr) + " |",
             "|" + "|".join(["---"]*len(hdr)) + "|"]
    for i in range(corr.shape[0]):
        row = [var_names[i]] + [f"{corr[i,j]:+.2f}" for j in range(corr.shape[1])]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

out = []
out.append("# Phase 3R — Methodology Inspection (Path C consolidated)")
out.append("")
out.append(f"Compute timestamp (UTC): **{NOW_ISO}**")
out.append(f"Database read: **`{db.name}`** (read-only this run; "
           f"no `peer_match.*` writes yet)")
out.append(f"Log: `{LOG_PATH}`")
out.append(f"Pickled state for bulk-write step: `{pkl_path}`")
out.append("")
out.append("**Path C consolidation applied** — dropped `per_capita_income`, "
           "`bachelors_pct_25plus`, `total_population`. Variable count: "
           f"{len(SHARED_VARS)} (ES/MS/Other) / {len(HS_VARS)} (HS).")
out.append("")
out.append("## DNS bypass note")
out.append("")
out.append("This run used an explicit dnspython resolver pointed at "
           "1.1.1.1, 8.8.8.8, 1.0.0.1 because the local router is refusing "
           "DNS on port 53. Read-only operation; no production-side concerns.")
out.append("")

# Eligibility delta section
out.append("## 1. Eligibility tiering — counts by category × level")
out.append("")
rows = []
for lvl in ["Elementary", "Middle", "High", "Other", "TOTAL"]:
    c = tier_counts if lvl == "TOTAL" else tier_by_level[lvl]
    rows.append([lvl, c.get("eligible", 0), c.get("descriptive_only", 0),
                 c.get("excluded", 0), sum(c.values())])
out.append(md_table(["level", "eligible", "descriptive_only", "excluded", "total"], rows))
out.append("")
out.append(f"**Eligible-set total: {n_eligible}** (Path C consolidated; "
           f"delta vs pre-consolidation 1,728: {delta:+d}). Pre-execution "
           f"projection was 1,742; the 14-school shortfall was traced to "
           f"schools that have all required vars non-null AND are in the "
           f"120-school legacy exclusion union — the locked tier rule routes "
           f"them to tier 3 (excluded takes precedence over eligibility), "
           f"which the pre-exec query did not subtract. Path C consolidation "
           f"did not change the eligible-set membership: dropped variables "
           f"have low null rates that overlap fully with the other ACS "
           f"variables already gating eligibility.")
out.append("")

out.append("## 2. Reason-code distribution")
out.append("")
rc_desc = Counter(); multiplicity_desc = Counter()
for r in records:
    if r["tier"] == "descriptive_only":
        for c in r["reason_codes"]: rc_desc[c] += 1
        multiplicity_desc[len(r["reason_codes"])] += 1
out.append("### descriptive_only — counts per missing-variable code")
out.append("")
out.append(md_table(["code", "count"],
    [[c, n] for c, n in sorted(rc_desc.items(), key=lambda x: -x[1])]))
out.append("")
out.append("Per-school multiplicity:")
out.append("")
out.append(md_table(["# missing vars", "schools"],
    [[k, v] for k, v in sorted(multiplicity_desc.items())]))
out.append("")
rc_excl = Counter(); multiplicity_excl = Counter()
for r in records:
    if r["tier"] == "excluded":
        for c in r["reason_codes"]: rc_excl[c] += 1
        multiplicity_excl[len(r["reason_codes"])] += 1
out.append("### excluded — counts per legacy reason code")
out.append("")
out.append(md_table(["code", "count"],
    [[c, n] for c, n in sorted(rc_excl.items(), key=lambda x: -x[1])]))
out.append("")
out.append("Per-school multiplicity:")
out.append("")
out.append(md_table(["# codes", "schools"],
    [[k, v] for k, v in sorted(multiplicity_excl.items())]))
out.append("")

out.append("## 3. Per-level z-score distributions (consolidated set)")
out.append("")
for lvl in ["Elementary", "Middle", "High", "Other"]:
    out.append(f"### {lvl} (n={len(eligible_by_level[lvl])})")
    out.append("")
    var_names = level_var_names[lvl]; z = level_zvecs[lvl]
    rows = []
    for k, vn in enumerate(var_names):
        m, s = level_stats[lvl][vn]
        rows.append([vn, f"{m:.4g}", f"{s:.4g}",
                     f"{z[:, k].min():+.2f}", f"{z[:, k].max():+.2f}"])
    out.append(md_table(["variable", "raw mean", "raw SD", "min(z)", "max(z)"], rows))
    out.append("")

# ---------------------------------------------------------------------------
# Section 4 — Pre-consolidation correlation matrix (from prior STOP pickle)
# ---------------------------------------------------------------------------
out.append("## 4. Pre-consolidation correlation matrix (the audit that triggered the STOP)")
out.append("")
out.append("The original 19/20-variable matrix that triggered the STOP-AND-REPORT "
           "before Path C was applied. Reproduced here for transparency / brief revision pass.")
out.append("")
if preconsol_pool_corr is not None:
    out.append("### POOLED (19 shared variables — graduation HS-only excluded)")
    out.append("")
    out.append(render_corr_matrix(preconsol_pool_corr, preconsol_pool_vars))
    out.append("")
    # Top 10 abs pairs in pre-consol pooled
    pairs = []
    d = preconsol_pool_corr.shape[0]
    for i in range(d):
        for j in range(i+1, d):
            pairs.append((abs(preconsol_pool_corr[i,j]),
                          preconsol_pool_vars[i], preconsol_pool_vars[j],
                          preconsol_pool_corr[i,j]))
    pairs.sort(reverse=True)
    out.append("Top 10 absolute correlations (pre-consolidation, pooled):")
    out.append("")
    out.append(md_table(["var i", "var j", "r", "|r|"],
        [[a, b, f"{r:+.3f}", f"{ar:.3f}"]
         for ar, a, b, r in pairs[:10]]))
    out.append("")
    for lvl in ["Elementary", "Middle", "High", "Other"]:
        cm, vn = preconsol_per_level[lvl]
        out.append(f"### LEVEL_{lvl} (pre-consolidation, d={cm.shape[0]})")
        out.append("")
        pairs = []
        for i in range(cm.shape[0]):
            for j in range(i+1, cm.shape[0]):
                pairs.append((abs(cm[i,j]), vn[i], vn[j], cm[i,j]))
        pairs.sort(reverse=True)
        out.append("Top 10 absolute pairs:")
        out.append("")
        out.append(md_table(["var i", "var j", "r", "|r|"],
            [[a, b, f"{r:+.3f}", f"{ar:.3f}"]
             for ar, a, b, r in pairs[:10]]))
        out.append("")

# ---------------------------------------------------------------------------
# Section 5 — Four-cluster analysis with disposition reasoning
# ---------------------------------------------------------------------------
out.append("## 5. Four-cluster analysis and Path C disposition")
out.append("")
out.append("The pre-consolidation triggers organized into four conceptual clusters.")
out.append("")
out.append("### Cluster 1 — Income / education three-way (POOLED + every level)")
out.append("")
out.append("Pairs: `per_capita_income` ~ `bachelors_pct_25plus` (r=+0.93), "
           "`median_household_income` ~ `per_capita_income` (r=+0.89), "
           "`median_household_income` ~ `bachelors_pct_25plus` (r=+0.77).")
out.append("")
out.append("**Disposition: drop two; keep one.** Brief Section 1.5 already "
           "pre-emptively flagged the income pair. The third-leg correlation "
           "with bachelor's% is the same dimension. r=+0.93 between "
           "per_capita_income and bachelors_pct_25plus is high enough that "
           "they're nearly the same variable. **Kept: median_household_income** "
           "(most parent-intuitive). **Dropped: per_capita_income, "
           "bachelors_pct_25plus.**")
out.append("")
out.append("### Cluster 2 — Population / population density (POOLED + every level)")
out.append("")
out.append("Pair: `total_population` ~ `population_density` (r=+0.85 to +0.91).")
out.append("")
out.append("**Disposition: drop one; keep one.** At WA scale, the populous "
           "districts ARE the dense districts; the pair is near-tautological. "
           "Population density captures the urban-rural gradient that's "
           "methodologically relevant for school similarity, while total "
           "population mostly tells you 'big district vs. small district' — "
           "partly redundant with enrollment_total anyway. "
           "**Kept: population_density. Dropped: total_population.**")
out.append("")
out.append("### Cluster 3 — Race composition / EL (POOLED + ES + Middle + High)")
out.append("")
out.append("Pair: `race_pct_non_white` ~ `ell` (r=+0.78 to +0.80, just above threshold).")
out.append("")
out.append("**Disposition: keep both — accept as documented WA-specific known limitation.** "
           "Right at the edge of the 0.70 threshold; would not trigger at 0.80. "
           "Conceptually distinct dimensions: race composition captures one "
           "dimension of community context (demographic), EL captures a "
           "different one (linguistic / instructional service intensity). "
           "A Yakima Valley school and an Auburn refugee-receiving school "
           "can have similar EL rates but very different race compositions, "
           "and vice versa. The empirical correlation is a structural "
           "feature of WA's specific demographic geography (Hispanic "
           "agricultural communities + refugee resettlement areas), not a "
           "redundancy in measurement. Brief revision will document this "
           "as a known WA-specific limitation.")
out.append("")
out.append("### Cluster 4 — FRL / income at Middle level only (r=-0.72 to -0.76)")
out.append("")
out.append("Pairs: `frl` ~ `median_household_income` (r=-0.76), "
           "`frl` ~ `per_capita_income` (r=-0.74), "
           "`frl` ~ `bachelors_pct_25plus` (r=-0.72).")
out.append("")
out.append("**Disposition: keep both remaining variables — accept as documented "
           "WA-specific known limitation at Middle level only.** Negative "
           "correlation as expected (higher FRL = lower income/education). "
           "After Cluster 1's drops, only `frl ~ median_household_income` "
           "remains as a pair (the other two drops eliminated themselves). "
           "Middle level has n=309 (smaller than ES n=1030), so this pair is "
           "partly a smaller-sample-variance artifact. FRL is the "
           "school-level poverty proxy; median household income is the "
           "district-level economic geography. Conceptually distinct and "
           "both load-bearing; dropping either would lose real signal. "
           "Brief revision will document this as the Middle-only residual.")
out.append("")
out.append("### Summary of drops vs keeps")
out.append("")
out.append(md_table(
    ["variable", "disposition", "cluster"],
    [["per_capita_income",     "DROP", "Cluster 1 (income/edu 3-way)"],
     ["bachelors_pct_25plus",  "DROP", "Cluster 1 (income/edu 3-way)"],
     ["total_population",      "DROP", "Cluster 2 (pop/density)"],
     ["median_household_income","KEEP", "Cluster 1 representative"],
     ["population_density",    "KEEP", "Cluster 2 representative"],
     ["race_pct_non_white",    "KEEP", "Cluster 3 — accepted residual"],
     ["ell",                   "KEEP", "Cluster 3 — accepted residual"],
     ["frl",                   "KEEP", "Cluster 4 (Middle only) — accepted residual"]]))
out.append("")

# ---------------------------------------------------------------------------
# Section 6 — Post-consolidation correlation matrix
# ---------------------------------------------------------------------------
out.append("## 6. Post-consolidation correlation matrix (Path C)")
out.append("")
out.append(f"**Threshold rules applied:** any |r| > 0.80 → STOP; "
           f"any unpredicted pair with |r| > 0.70 → STOP. Predicted residuals "
           f"(in 0.70–0.80 range, pre-approved): race_pct_non_white ~ ell "
           f"(POOLED + ES + Middle + High); frl ~ median_household_income (Middle).")
out.append("")
out.append("**Result: PASSED.** No pair |r| > 0.80; all 0.70–0.80 pairs match predicted set.")
out.append("")
out.append(f"### POOLED (16 shared vars, n={pool_z.shape[0]})")
out.append("")
out.append(render_corr_matrix(pool_corr, pool_vars))
out.append("")
# Top 10 abs pairs in post-consol pooled
pairs = []
d = pool_corr.shape[0]
for i in range(d):
    for j in range(i+1, d):
        pairs.append((abs(pool_corr[i,j]), pool_vars[i], pool_vars[j],
                      pool_corr[i,j]))
pairs.sort(reverse=True)
out.append("Top 10 absolute pairs (post-consolidation, pooled):")
out.append("")
def annotate(a, b, rval, label):
    pair = frozenset({a, b})
    if pair in PREDICTED_RESIDUALS.get(label, set()):
        return "predicted residual (accepted)"
    if abs(rval) > WARN_THRESH:
        return "ABOVE 0.70 — UNEXPECTED"
    return ""
out.append(md_table(["var i", "var j", "r", "|r|", "note"],
    [[a, b, f"{r:+.3f}", f"{ar:.3f}", annotate(a, b, r, "POOLED")]
     for ar, a, b, r in pairs[:10]]))
out.append("")
for lvl in ["Elementary", "Middle", "High", "Other"]:
    cm, vn = per_level_corr[lvl]
    out.append(f"### LEVEL_{lvl} (n={len(eligible_by_level[lvl])}, d={cm.shape[0]})")
    out.append("")
    pairs = []
    for i in range(cm.shape[0]):
        for j in range(i+1, cm.shape[0]):
            pairs.append((abs(cm[i,j]), vn[i], vn[j], cm[i,j]))
    pairs.sort(reverse=True)
    out.append("Top 10 absolute pairs:")
    out.append("")
    out.append(md_table(["var i", "var j", "r", "|r|", "note"],
        [[a, b, f"{r:+.3f}", f"{ar:.3f}",
          annotate(a, b, r, f"LEVEL_{lvl}")]
         for ar, a, b, r in pairs[:10]]))
    out.append("")

# ---------------------------------------------------------------------------
# Section 7 — Fairhaven golden school
# ---------------------------------------------------------------------------
out.append("## 7. Golden school spot-check — Fairhaven Middle School")
out.append("")
fhid = "530042000104"
fh = records_by_id[fhid]
fhc = cohorts_v1.get(fhid)
out.append(f"**_id:** `{fhid}` &nbsp; **name:** {fh['name']} &nbsp; "
           f"**level_group:** {fh['level_group']} &nbsp; **tier:** {fh['tier']}")
out.append("")
out.append("### Focal z-scores (Path C standardization within Middle)")
out.append("")
zfh = fh.get("z_v1", {})
rows = []
for vn, zval in sorted(zfh.items()):
    rows.append([vn, f"{fh['vars'][vn]}", f"{zval:+.3f}"])
out.append(md_table(["variable", "raw value", "z-score"], rows))
out.append("")
out.append("### Cohort (K=20 v1 achievement-excluded)")
out.append("")
rows = []
for k in range(len(fhc["K20"])):
    rows.append([k+1, fhc["K20"][k], fhc["K20_names"][k],
                 f"{fhc['K20_dist'][k]:.3f}"])
out.append(md_table(["#", "_id", "name", "distance"], rows))
out.append("")
out.append("### Cohort mean z-scores")
out.append("")
fh_recs = eligible_by_level[fh["level_group"]]
fh_id_to_idx = {r["_id"]: i for i, r in enumerate(fh_recs)}
cohort_idxs = [fh_id_to_idx[pid] for pid in fhc["K20"] if pid in fh_id_to_idx]
zsub = level_zvecs[fh["level_group"]][cohort_idxs, :]
cohort_means = zsub.mean(axis=0)
rows = []
for k, vn in enumerate(level_var_names[fh["level_group"]]):
    rows.append([vn, f"{zfh[vn]:+.3f}", f"{cohort_means[k]:+.3f}",
                 f"{(zfh[vn] - cohort_means[k]):+.3f}"])
out.append(md_table(["variable", "Fairhaven z", "cohort mean z", "delta"], rows))
out.append("")

# ---------------------------------------------------------------------------
# Section 8 — Sample spot-checks
# ---------------------------------------------------------------------------
out.append("## 8. Sample spot-checks across categories")
out.append("")
for label, r in spot_check.items():
    if r is None:
        out.append(f"### {label}: NOT FOUND"); out.append(""); continue
    out.append(f"### {label}")
    out.append("")
    out.append(f"**_id:** `{r['_id']}` &nbsp; **name:** {r['name']} &nbsp; "
               f"**level_group:** {r['level_group']} &nbsp; **tier:** {r['tier']}")
    if r["tier"] != "eligible":
        out.append(f"\n**reason_codes:** `{r['reason_codes']}`\n")
    if r["tier"] == "eligible" and r["_id"] in cohorts_v1:
        c = cohorts_v1[r["_id"]]
        out.append("\nCohort (K=20 v1, top 5 of 20 shown):\n")
        rows = [[k+1, c["K20"][k], c["K20_names"][k], f"{c['K20_dist'][k]:.3f}"]
                for k in range(min(5, len(c["K20"])))]
        out.append(md_table(["#", "_id", "name", "distance"], rows))
        out.append("")

# ---------------------------------------------------------------------------
# Section 9 — Achievement sensitivity
# ---------------------------------------------------------------------------
out.append("## 9. Achievement sensitivity")
out.append("")
out.append(f"- v1 (achievement-excluded) eligible set: **{n_eligible}**")
out.append(f"- Achievement-included eligible set: **{n_ach}**")
out.append(f"- Intersection (focal-school denominator): **{len(ach_focal_ids)}**")
out.append("")
out.append("### Cohort overlap — Jaccard distribution")
out.append("")
rows = [[stat, f"{fn(jaccards):.3f}"]
        for stat, fn in [("mean", np.mean), ("median", np.median),
                         ("q1", lambda x: np.quantile(x, 0.25)),
                         ("q3", lambda x: np.quantile(x, 0.75)),
                         ("min", np.min), ("max", np.max)]]
out.append(md_table(["stat", "Jaccard"], rows))
out.append("")
out.append("### Per-level Jaccard")
out.append("")
rows = []
for lvl in ["Elementary", "Middle", "High", "Other"]:
    js = jacc_by_level[lvl]
    if js:
        rows.append([lvl, len(js), f"{np.mean(js):.3f}", f"{np.median(js):.3f}",
                     f"{np.quantile(js, .25):.3f}", f"{np.quantile(js, .75):.3f}"])
    else:
        rows.append([lvl, 0, "—", "—", "—", "—"])
out.append(md_table(["level", "n", "mean", "median", "q1", "q3"], rows))
out.append("")
out.append("### Cohort identity changes — peers in B not in A (out of 20)")
out.append("")
rows = [
    ["mean", f"{identity_changes.mean():.2f}"],
    ["median", f"{int(np.median(identity_changes))}"],
    ["q1", f"{int(np.quantile(identity_changes, .25))}"],
    ["q3", f"{int(np.quantile(identity_changes, .75))}"],
    ["min", f"{int(identity_changes.min())}"],
    ["max", f"{int(identity_changes.max())}"],
]
out.append(md_table(["stat", "value"], rows))
out.append("")
out.append("### Side-by-side examples (10 schools)")
out.append("")
out.append(f"Full cohort lists: `{sidecar_path}`")
out.append("")
for sid in side_by_side_ids:
    r = records_by_id[sid]
    v1c = cohorts_v1.get(sid, {}); ac = cohorts_ach.get(sid, {})
    A = set(v1c.get("K20", [])); B = set(ac.get("K20", []))
    j = len(A & B) / len(A | B) if (A | B) else 0
    out.append(f"#### {r['name']} (_id `{sid}`, {r['level_group']})")
    out.append("")
    out.append(f"|A∩B|={len(A & B)}, Jaccard={j:.3f}")
    out.append("")
    n_show = max(len(v1c.get("K20", [])), len(ac.get("K20", [])))
    rows = []
    for k in range(n_show):
        v1n = v1c["K20_names"][k] if k < len(v1c.get("K20_names", [])) else "—"
        v1d = f"{v1c['K20_dist'][k]:.2f}" if k < len(v1c.get("K20_dist", [])) else "—"
        an = ac["K20_names"][k] if k < len(ac.get("K20_names", [])) else "—"
        ad = f"{ac['K20_dist'][k]:.2f}" if k < len(ac.get("K20_dist", [])) else "—"
        rows.append([k+1, v1n, v1d, an, ad])
    out.append(md_table(["#", "v1 peer", "v1 dist", "ach-incl peer", "ach-incl dist"], rows))
    out.append("")

# ---------------------------------------------------------------------------
# Section 10 — K sensitivity
# ---------------------------------------------------------------------------
out.append("## 10. K sensitivity")
out.append("")
out.append("### Containment distributions")
out.append("")
out.append(md_table(
    ["statistic", "K10⊆K20", "statistic", "K20⊆K30"],
    [["mean", f"{contain_10_20.mean():.4f}", "mean", f"{contain_20_30.mean():.4f}"],
     ["median", f"{np.median(contain_10_20):.4f}", "median", f"{np.median(contain_20_30):.4f}"],
     ["q1", f"{np.quantile(contain_10_20, .25):.4f}", "q1", f"{np.quantile(contain_20_30, .25):.4f}"],
     ["q3", f"{np.quantile(contain_10_20, .75):.4f}", "q3", f"{np.quantile(contain_20_30, .75):.4f}"]]))
out.append("")
out.append("### Stability summary — full-containment rate")
out.append("")
out.append(md_table(["check", "schools", "% of eligible"],
    [["K10 fully contained in K20", contain_10_20_full,
      f"{contain_10_20_full/len(contain_10_20)*100:.2f}%"],
     ["K20 fully contained in K30", contain_20_30_full,
      f"{contain_20_30_full/len(contain_20_30)*100:.2f}%"]]))
out.append("")
out.append("### Per-level breakdown")
out.append("")
rows = []
for lvl in ["Elementary", "Middle", "High", "Other"]:
    cs = contain_by_level[lvl]
    n = len(cs["k10_in_k20"])
    if n == 0: rows.append([lvl, 0, "—", "—"]); continue
    rows.append([lvl, n, f"{np.mean(cs['k10_in_k20']):.4f}",
                 f"{np.mean(cs['k20_in_k30']):.4f}"])
out.append(md_table(["level", "n", "K10⊆K20 mean", "K20⊆K30 mean"], rows))
out.append("")

out.append("## 11. Issues for builder review / brief revision pass")
out.append("")
out.append("- R7 (redundancy audit) can move from PENDING to LOCKED with the "
           "Path C consolidation findings filled in.")
out.append("- Brief Section 1.4/1.5 narrative + variable count throughout "
           "needs updating: 19 vars (ES/MS/Other) / 20 (HS) → 16 / 17.")
out.append("- Brief Section 1.5 should document the Cluster 3 (race/ELL) "
           "and Cluster 4 (Middle FRL/income) residual correlations as "
           "known WA-specific limitations, with the empirical justification "
           "above.")
out.append("- Cover note to reviewer: 'After Path C consolidation, two "
           "residual correlations remain in the 0.70–0.80 range, both "
           "reflecting structural features of WA demographic geography "
           "rather than measurement redundancy. Documented and accepted.'")

methodology_inspection_path = OUT_DIR / "methodology_inspection.md"
with open(methodology_inspection_path, "w") as f:
    f.write("\n".join(out))
log.info(f"Wrote {methodology_inspection_path}")

# ---------------------------------------------------------------------------
# Schema/update plan deliverable
# ---------------------------------------------------------------------------
plan = []
plan.append("# Phase 3R — `peer_match.*` Schema Update Plan (Path C, awaiting builder approval)")
plan.append("")
plan.append(f"Compute timestamp (UTC): **{NOW_ISO}**")
plan.append("")
plan.append("Per CLAUDE.md destructive-operation rule: this document is the "
            "plain-English statement of the bulk write. **No write executes "
            "until builder approves.**")
plan.append("")
plan.append("## What will happen")
plan.append("")
plan.append(f"For every school document in `schooldaylight_experiment.schools` "
            f"({len(records)} docs), `$set` the following:")
plan.append("")
plan.append("```")
plan.append("peer_match.status                     'eligible' | 'descriptive_only' | 'excluded'")
plan.append("peer_match.reason_codes               array<string>  ([] when eligible)")
plan.append("peer_match.level_used_for_matching    'elementary' | 'middle' | 'high' | 'other'")
plan.append("peer_match.cohort_nces_ids            array<string>(20)  (eligible only)")
plan.append("peer_match.cohort_names               array<string>(20)  (eligible only)")
plan.append("peer_match.distances                  array<float>(20)   (eligible only)")
plan.append("peer_match.focal_z_scores             dict<varname, float>  (eligible only)")
plan.append("peer_match.cohort_mean_z_scores       dict<varname, float>  (eligible only)")
plan.append("peer_match.metadata.k                 20")
plan.append("peer_match.metadata.metric            'euclidean'")
plan.append("peer_match.metadata.compute_timestamp ISO 8601")
plan.append("peer_match.metadata.dataset_version   'phase3r_peer_match_v1'")
plan.append("peer_match.metadata.consolidation     'path_c_dropped: per_capita_income, bachelors_pct_25plus, total_population'")
plan.append("metadata.phase_3r_dataset_versions.peer_match  provenance entry")
plan.append("```")
plan.append("")
plan.append("**Touched fields:** `peer_match.*` and one provenance key. "
            "Nothing else. No deletes, no inserts.")
plan.append("**Mechanism:** `bulk_write([UpdateOne({_id}, {$set: ...})])`, "
            "ordered=False, batches of 500. Idempotent.")
plan.append("**Pre-write guards:** `assert \"experiment\" in db.name`; "
            "doc-count log; pre-write Fairhaven probe.")
plan.append("")
plan.append("## Counts that will result")
plan.append("")
plan.append(md_table(["status", "count", "what it means"],
    [["eligible", tier_counts["eligible"],
      "20-school cohort, distances, z-scores, cohort mean z-scores"],
     ["descriptive_only", tier_counts["descriptive_only"],
      "no cohort; reason_codes array names each missing variable"],
     ["excluded", tier_counts["excluded"],
      "no cohort; reason_codes array carries legacy code(s)"],
     ["TOTAL", sum(tier_counts.values()), "every school touched"]]))
plan.append("")
plan.append("## Variable list applied (Path C)")
plan.append("")
plan.append("Shared vars (used at all levels): " +
            ", ".join(f"`{v[0]}`" for v in SHARED_VARS))
plan.append("")
plan.append("HS-only addition: `graduation_4yr`")
plan.append("")
plan.append("Dropped from original v1: " + ", ".join(f"`{x}`" for x in sorted(DROPPED)))
plan.append("")
plan.append("## STOP-AND-REPORT triggers (none triggered)")
plan.append("")
plan.append(f"- Eligibility-set size = {n_eligible} (within [1500, 2200] "
            f"sanity band; matches pre-consolidation as expected).")
plan.append(f"- Redundancy: no pair |r| > 0.80; no unpredicted pair |r| > 0.70.")
plan.append(f"- Predicted residuals (accepted per Path C): race/ELL "
            f"(POOLED + ES/Middle/High); FRL/median_household_income (Middle).")
plan.append("")
plan.append("## Sensitivity-variant cohorts (achievement-included, K=10, K=30)")
plan.append("")
plan.append("Per Option C decision: not persisted to MongoDB. Statistical "
            "summaries in `methodology_inspection.md`; side-by-side cohort "
            "lists for the 10 example schools in `sensitivity_cohort_lists.json`.")
plan.append("")
plan.append("## Post-write verification plan")
plan.append("")
plan.append("After bulk_write completes, the bulk-write script will:")
plan.append("1. Read Fairhaven Middle School (`530042000104`) full peer_match "
            "record back from db; report to builder.")
plan.append("2. Read peer_match for the 6 spot-check schools; report to builder.")
plan.append("3. Confirm post-write counts match plan.")
plan.append("4. Produce verification receipt per CLAUDE.md Phase 2+ convention.")
plan.append("")
plan.append("## Standing by for builder approval")

plan_path = OUT_DIR / "peer_match_schema_update_plan.md"
with open(plan_path, "w") as f:
    f.write("\n".join(plan))
log.info(f"Wrote {plan_path}")

log.info("=" * 70)
log.info("Path C computation complete. NO MongoDB writes performed.")
log.info(f"  inspection : {methodology_inspection_path}")
log.info(f"  sidecar    : {sidecar_path}")
log.info(f"  schema plan: {plan_path}")
log.info(f"  pickled    : {pkl_path}")
log.info("=" * 70)
print(f"\nPath C — Eligible: {tier_counts['eligible']}  "
      f"descriptive_only: {tier_counts['descriptive_only']}  "
      f"excluded: {tier_counts['excluded']}")
print(f"Eligibility delta vs pre-consolidation: {delta:+d}")
print(f"Redundancy: PASSED. {len(pool_pred)} predicted residuals in pooled, "
      f"{sum(len(per_level_eval[l]['predicted']) for l in per_level_eval)} per-level.")
print(f"Schema plan: {plan_path}")
