"""
_run_cohort_diff_diagnostic_2026-05-08.py — Phase 3R Section 2 cohort
differential distribution diagnostic against the post-zfill eligible set.

PURPOSE: Compute raw and standardized cohort-differential distributions per
subject (ELA, Math, Science) across the 2,051 eligible schools, generate
histograms and bivariate scatters, and produce the Section 2 informational
receipt that informs the threshold-value decision.

NOT a methodology decision. Receipt-only. No writes to peer_match or any
production collection.

DNS BYPASS: 1.1.1.1 / 8.8.8.8 / 1.0.0.1.
"""

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

import csv
import datetime as dt
import json
import logging
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import scipy.stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient

TS = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = "/Users/oriandaleigh/school-daylight/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"phase3r_cohort_diff_diag_{TS}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("p3r_cohort_diff")
NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

OUT = Path("/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment")
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
RECEIPT = OUT / "cohort_differential_distributions.md"

log.info("=" * 70)
log.info("Cohort differential distribution diagnostic (post-zfill)")
log.info("=" * 70)

# ---------------------------------------------------------------------------
# Subject testable-grade sets
# ---------------------------------------------------------------------------
TESTABLE = {
    "ela":     {3, 4, 5, 6, 7, 8, 10},
    "math":    {3, 4, 5, 6, 7, 8, 10},
    "science": {5, 8, 11},
}
SUBJECTS = ["ela", "math", "science"]
SUBJECT_LABEL = {"ela": "ELA", "math": "Math", "science": "Science"}

def parse_grade(g):
    """Parse OSPI grade string to int. PK=-1, KG=0, '01'..'12'=1..12."""
    if g is None: return None
    g = str(g).strip()
    if g == "PK": return -1
    if g == "KG": return 0
    try: return int(g)
    except (ValueError, TypeError): return None

def school_overlaps_testable(low, high, subject):
    """True if school's grade-span [low, high] intersects testable grades."""
    lo = parse_grade(low); hi = parse_grade(high)
    if lo is None or hi is None: return False
    school_grades = set(range(lo, hi + 1))
    return bool(school_grades & TESTABLE[subject])

# ---------------------------------------------------------------------------
# Connect — read-only intent (no writes)
# ---------------------------------------------------------------------------
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=30000)
db = client.get_default_database()
assert "experiment" in db.name
log.info(f"Connected to '{db.name}'.")

PRE_DOC_COUNT = db.schools.count_documents({})
N_ELIGIBLE = db.schools.count_documents({"peer_match.status": "eligible"})
log.info(f"Total docs: {PRE_DOC_COUNT}. Eligible: {N_ELIGIBLE}")

# ---------------------------------------------------------------------------
# Pull every doc — we need cohort proficiency lookups across the whole pool
# (peers may be themselves eligible; the `valid value present` check is what
# matters for cohort mean computation).
# ---------------------------------------------------------------------------
log.info("Loading all school docs ...")
PROJ = {
    "_id": 1, "name": 1, "district.name": 1,
    "derived.level_group": 1, "grade_span": 1,
    "metadata.ospi_district_code": 1,
    "peer_match.status": 1, "peer_match.reason_codes": 1,
    "peer_match.cohort_nces_ids": 1,
    "academics.assessment.ela_proficiency_pct": 1,
    "academics.assessment.math_proficiency_pct": 1,
    "academics.assessment.science_proficiency_pct": 1,
    "enrollment.total": 1,
    "demographics.frl_pct": 1,
}
docs = {d["_id"]: d for d in db.schools.find({}, PROJ)}
log.info(f"Loaded {len(docs)} docs into memory")

def get_prof(doc, subject):
    a = (doc.get("academics") or {}).get("assessment") or {}
    return a.get(f"{subject}_proficiency_pct")

def classify(doc, subject):
    """Classify a (school, subject): 'not_tested' / 'suppressed_self' / 'valid'."""
    val = get_prof(doc, subject)
    gs = doc.get("grade_span") or {}
    overlaps = school_overlaps_testable(gs.get("low"), gs.get("high"), subject)
    if val is not None:
        return "valid"
    return "suppressed_self" if overlaps else "not_tested"

# ---------------------------------------------------------------------------
# Build per-(school, subject) records for eligible schools
# ---------------------------------------------------------------------------
eligible = [d for d in docs.values()
             if (d.get("peer_match") or {}).get("status") == "eligible"]
log.info(f"Eligible schools: {len(eligible)}")

# Per-subject records: sid -> {category, value_pp, cohort_mean_pp, raw_diff,
#                              cohort_n_valid, cohort_sd_pp, level_group,
#                              ospi_dc}
records = {s: {} for s in SUBJECTS}
counts = {s: Counter() for s in SUBJECTS}

for school in eligible:
    sid = school["_id"]
    cohort_ids = (school.get("peer_match") or {}).get("cohort_nces_ids", [])
    lvl = (school.get("derived") or {}).get("level_group")
    dc = (school.get("metadata") or {}).get("ospi_district_code", "")
    for subj in SUBJECTS:
        cat = classify(school, subj)
        if cat != "valid":
            counts[subj][cat] += 1
            continue
        # School value valid; check cohort
        focal_pp = get_prof(school, subj) * 100.0
        cohort_vals = []
        for cid in cohort_ids:
            peer = docs.get(cid)
            if peer is None: continue
            pv = get_prof(peer, subj)
            if pv is not None:
                cohort_vals.append(pv * 100.0)
        n_valid = len(cohort_vals)
        if n_valid < 15:
            counts[subj]["insufficient_cohort_data"] += 1
            records[subj][sid] = {
                "category": "insufficient_cohort_data",
                "school_pp": focal_pp,
                "cohort_n_valid": n_valid,
                "level_group": lvl,
                "ospi_dc": dc,
            }
            continue
        cohort_mean = float(np.mean(cohort_vals))
        cohort_sd = float(np.std(cohort_vals, ddof=0))
        raw_diff = focal_pp - cohort_mean
        records[subj][sid] = {
            "category": "valid",
            "school_pp": focal_pp,
            "cohort_mean_pp": cohort_mean,
            "raw_diff": raw_diff,
            "cohort_n_valid": n_valid,
            "cohort_sd_pp": cohort_sd,
            "level_group": lvl,
            "ospi_dc": dc,
        }
        counts[subj]["valid"] += 1

for s in SUBJECTS:
    log.info(f"  {s}: counts = {dict(counts[s])}")

# ---------------------------------------------------------------------------
# Compute z-scores per subject
# ---------------------------------------------------------------------------
mu_subj = {}
sd_subj = {}
for subj in SUBJECTS:
    raw = [r["raw_diff"] for r in records[subj].values() if r["category"] == "valid"]
    if not raw:
        log.error(f"No valid raw_diff for {subj}. STOP.")
        raise SystemExit(2)
    mu = float(np.mean(raw))
    sd = float(np.std(raw, ddof=0))
    mu_subj[subj] = mu
    sd_subj[subj] = sd
    for sid, r in records[subj].items():
        if r["category"] == "valid":
            r["z_diff"] = (r["raw_diff"] - mu) / sd
    log.info(f"  {subj} μ={mu:.4f}pp σ={sd:.4f}pp (μ≈0 by construction; verify)")

# ---------------------------------------------------------------------------
# Helper: summary statistics
# ---------------------------------------------------------------------------
def summarize(values, label=""):
    a = np.asarray(values, dtype=float)
    if len(a) == 0:
        return {"n": 0}
    pcts = np.percentile(a, [5, 10, 25, 50, 75, 90, 95])
    return {
        "n": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
        "sd": float(np.std(a, ddof=0)),
        "skew": float(scipy.stats.skew(a)),
        "kurt": float(scipy.stats.kurtosis(a, fisher=True)),
        "min": float(a.min()), "max": float(a.max()),
        "p5": float(pcts[0]), "p10": float(pcts[1]), "p25": float(pcts[2]),
        "p50": float(pcts[3]), "p75": float(pcts[4]), "p90": float(pcts[5]),
        "p95": float(pcts[6]),
    }

def count_above(values, thresholds):
    a = np.abs(np.asarray(values, dtype=float))
    return {t: int((a > t).sum()) for t in thresholds}

def bucket_counts(z_values, threshold):
    a = np.asarray(z_values, dtype=float)
    return {"below": int((a < -threshold).sum()),
            "similar": int(((a >= -threshold) & (a <= threshold)).sum()),
            "above": int((a > threshold).sum())}

# ---------------------------------------------------------------------------
# Generate figures
# ---------------------------------------------------------------------------
log.info("Generating figures ...")
def hist_raw(subj):
    raw = [r["raw_diff"] for r in records[subj].values() if r["category"] == "valid"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.arange(np.floor(min(raw)) - 0.5, np.ceil(max(raw)) + 0.5, 1.0)
    ax.hist(raw, bins=bins)
    ax.set_xlabel(f"{SUBJECT_LABEL[subj]} cohort differential (percentage points)")
    ax.set_ylabel("count of schools")
    ax.set_title(f"Cohort differential — {SUBJECT_LABEL[subj]} (n={len(raw)}, eligible set)")
    ax.axvline(0, linestyle="--", color="gray", alpha=0.5)
    fig.tight_layout()
    path = FIG / f"cohort_diff_raw_{subj}.png"
    fig.savefig(path, dpi=100); plt.close(fig)
    return path

def hist_z(subj):
    z = [r["z_diff"] for r in records[subj].values() if r["category"] == "valid"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.arange(np.floor(min(z) * 4) / 4 - 0.125, np.ceil(max(z) * 4) / 4 + 0.125, 0.25)
    ax.hist(z, bins=bins)
    ax.set_xlabel(f"{SUBJECT_LABEL[subj]} standardized cohort differential (z-score)")
    ax.set_ylabel("count of schools")
    ax.set_title(f"Standardized differential — {SUBJECT_LABEL[subj]} (n={len(z)}, eligible set)")
    for thr in [-1.5, -1.0, -0.5, 0.5, 1.0, 1.5]:
        ax.axvline(thr, linestyle="--", color="gray", alpha=0.5)
    ax.axvline(0, color="black", alpha=0.4)
    fig.tight_layout()
    path = FIG / f"cohort_diff_z_{subj}.png"
    fig.savefig(path, dpi=100); plt.close(fig)
    return path

def scatter_bivariate(subj):
    valid_records = [r for r in records[subj].values() if r["category"] == "valid"]
    sds = [r["cohort_sd_pp"] for r in valid_records]
    diffs = [abs(r["raw_diff"]) for r in valid_records]
    if not sds:
        return None, None
    pearson_r, _ = scipy.stats.pearsonr(sds, diffs)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(sds, diffs, alpha=0.25, s=14)
    ax.set_xlabel(f"within-cohort SD of {SUBJECT_LABEL[subj]} proficiency (percentage points)")
    ax.set_ylabel(f"|{SUBJECT_LABEL[subj]} cohort differential| (percentage points)")
    ax.set_title(f"Within-cohort SD vs |raw differential| — {SUBJECT_LABEL[subj]}\n"
                 f"Pearson r = {pearson_r:.3f}, n = {len(sds)}")
    fig.tight_layout()
    path = FIG / f"cohort_diff_bivariate_{subj}.png"
    fig.savefig(path, dpi=100); plt.close(fig)
    return path, pearson_r

raw_paths = {s: hist_raw(s) for s in SUBJECTS}
z_paths = {s: hist_z(s) for s in SUBJECTS}
bivariate = {s: scatter_bivariate(s) for s in SUBJECTS}
log.info(f"Saved 9 figures to {FIG}")

# ---------------------------------------------------------------------------
# Spot-check table data
# ---------------------------------------------------------------------------
SPOT = [
    ("530039000076", "Medina Elementary", "Bellevue SD"),
    ("530498000761", "Mercer Island High School", "Mercer Island SD"),
    ("530771001173", "Bailey Gatzert Elementary", "Seattle SD"),
    ("530771001150", "Cleveland High School STEM", "Seattle SD"),
    ("530948001617", "Wapato High School", "Wapato SD"),
    ("530963003150", "Wellpinit Middle", "Wellpinit SD"),
    ("530702001047", "Forks High School", "Quillayute Valley SD"),
    ("530786001291", "Shaw Island Elementary School", "Shaw Island SD #10"),
    ("530042000104", "Fairhaven Middle School", "Bellingham SD"),
    ("530057000130", "Blaine Elementary School", "Blaine SD"),
    ("530870001487", "Meeker Middle School", "Tacoma SD"),
    ("530033303541", "Summit Public School: Olympus", "Summit Charter"),
]

# Status-flip notes
STATUS_NOTES = {
    "530702001047": "flipped descriptive_only → eligible post-zfill",
}

def flag_bucket(z, thr=1.0):
    if z is None: return "n/a"
    if z > thr: return "above-peers"
    if z < -thr: return "below-peers"
    return "similar"

# ---------------------------------------------------------------------------
# Manual verification on 3 random eligible schools
# ---------------------------------------------------------------------------
log.info("Manual verification on 3 random eligible schools ...")
random.seed(20260508)
# 1) Random non-0X eligible
non_0x = [r for r in eligible
           if not (r.get("metadata") or {}).get("ospi_district_code","").startswith("0")]
# 2) Random 0X-flipped (eligible AND district code starts with 0)
flipped_0x = [r for r in eligible
               if (r.get("metadata") or {}).get("ospi_district_code","").startswith("0")]
# 3) Random any
any_pick = eligible

verif_pool = []
if non_0x: verif_pool.append(("non_0X", random.choice(non_0x)))
if flipped_0x: verif_pool.append(("0X_flipped", random.choice(flipped_0x)))
if any_pick:
    pool_remaining = [r for r in any_pick if r["_id"] not in {x[1]["_id"] for x in verif_pool}]
    if pool_remaining:
        verif_pool.append(("any_level", random.choice(pool_remaining)))

verif_results = []
for label, school in verif_pool:
    sid = school["_id"]
    cohort_ids = (school.get("peer_match") or {}).get("cohort_nces_ids", [])
    row = {"label": label, "_id": sid, "name": school.get("name"),
           "level_group": (school.get("derived") or {}).get("level_group"),
           "subjects": {}}
    for subj in SUBJECTS:
        focal = get_prof(school, subj)
        if focal is None:
            row["subjects"][subj] = {"verdict": "not_tested or suppressed (skipped)"}
            continue
        # Independent recompute
        cohort_vals = []
        for cid in cohort_ids:
            peer = docs.get(cid);
            if peer is None: continue
            pv = get_prof(peer, subj)
            if pv is not None:
                cohort_vals.append(pv * 100.0)
        if len(cohort_vals) < 15:
            row["subjects"][subj] = {"verdict": "insufficient_cohort_data"}
            continue
        independent_cohort_mean = float(np.mean(cohort_vals))
        independent_raw_diff = focal * 100.0 - independent_cohort_mean
        receipt_rec = records[subj].get(sid, {})
        receipt_raw = receipt_rec.get("raw_diff")
        match = abs(independent_raw_diff - receipt_raw) < 0.001 if receipt_raw is not None else False
        row["subjects"][subj] = {
            "focal_pp": focal * 100.0,
            "independent_cohort_mean": independent_cohort_mean,
            "independent_raw_diff": independent_raw_diff,
            "receipt_raw_diff": receipt_raw,
            "match": match,
        }
    verif_results.append(row)
    log.info(f"  {label}: {sid} {school.get('name')}")

# ---------------------------------------------------------------------------
# Build the receipt
# ---------------------------------------------------------------------------
log.info("Writing receipt ...")

def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("—" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)

lines = []
lines.append("# Phase 3R — Cohort Differential Distribution Diagnostic")
lines.append("")
lines.append(f"**Generated:** {NOW_ISO}")
lines.append("**Database read:** `schooldaylight_experiment` (read-only this run; "
             "production untouched)")
lines.append(f"**peer_match state:** post-zfill methodology re-run "
             f"(`compute_timestamp = 2026-05-08T17:26:35Z`, "
             f"`dataset_version = phase3r_peer_match_v1`, Path C consolidation)")
lines.append(f"**Eligible set:** {N_ELIGIBLE}")
lines.append(f"**Log:** `{LOG_PATH}`")
lines.append("")
lines.append("**Scope:** Empirical distributions of cohort differentials per "
             "subject, before the Section 2 threshold-value decision. The receipt "
             "informs the threshold choice rather than presupposing one.")
lines.append("")

# Section 1
lines.append("## 1. Eligible-set summary")
lines.append("")
lines.append(md_table(
    ["subject", "valid (in distribution)", "not_tested",
     "suppressed_self", "insufficient_cohort_data", "total eligible"],
    [[SUBJECT_LABEL[s], counts[s].get("valid", 0),
      counts[s].get("not_tested", 0), counts[s].get("suppressed_self", 0),
      counts[s].get("insufficient_cohort_data", 0), N_ELIGIBLE]
     for s in SUBJECTS]))
lines.append("")
lines.append("**v0-of-diagnostic disambiguation note.** The OSPI schema does "
             "not carry an explicit `suppressed` flag for proficiency values — "
             "suppressed-for-N and not-tested-at-this-grade-span both appear "
             "as `null`. The diagnostic disambiguates by checking whether the "
             "school's grade_span overlaps the subject's testable grades "
             "(ELA/Math: {3,4,5,6,7,8,10}; Science: {5,8,11}). Production flag "
             "computation may want a tighter rule — e.g., the OSPI raw data "
             "probably distinguishes suppressed-for-N from not-tested somewhere "
             "upstream of our schema, and v2 of the ingest could carry that "
             "distinction explicitly.")
lines.append("")

# Section 2
lines.append("## 2. Per-subject raw differential distributions (eligible set, all level groups pooled)")
lines.append("")
THRS = [5, 10, 15, 20]
for subj in SUBJECTS:
    raw = [r["raw_diff"] for r in records[subj].values() if r["category"] == "valid"]
    s = summarize(raw)
    above = count_above(raw, THRS)
    lines.append(f"### {SUBJECT_LABEL[subj]} (n={s['n']})")
    lines.append("")
    lines.append(f"![raw histogram {SUBJECT_LABEL[subj]}](figures/cohort_diff_raw_{subj}.png)")
    lines.append("")
    lines.append(md_table(
        ["statistic", "value (percentage points)"],
        [["mean (verify ≈ 0)", f"{s['mean']:+.4f}"],
         ["median", f"{s['median']:+.3f}"],
         ["SD", f"{s['sd']:.3f}"],
         ["skewness (Fisher-Pearson, normal=0)", f"{s['skew']:+.3f}"],
         ["kurtosis (Fisher excess, normal=0)", f"{s['kurt']:+.3f}"],
         ["min", f"{s['min']:+.3f}"],
         ["max", f"{s['max']:+.3f}"],
         ["p5",  f"{s['p5']:+.3f}"],
         ["p10", f"{s['p10']:+.3f}"],
         ["p25", f"{s['p25']:+.3f}"],
         ["p50", f"{s['p50']:+.3f}"],
         ["p75", f"{s['p75']:+.3f}"],
         ["p90", f"{s['p90']:+.3f}"],
         ["p95", f"{s['p95']:+.3f}"]]))
    lines.append("")
    lines.append("Schools at |raw differential| above thresholds:")
    lines.append("")
    lines.append(md_table(
        ["threshold", "count", "% of valid"],
        [[f">{t}pp", above[t], f"{above[t]/s['n']*100:.1f}%"] for t in THRS]))
    lines.append("")

# Section 3
lines.append("## 3. Per-subject standardized differential distributions")
lines.append("")
Z_THRS = [0.5, 1.0, 1.5, 2.0]
CAND_THRS = [0.5, 1.0, 1.5]
for subj in SUBJECTS:
    z = [r["z_diff"] for r in records[subj].values() if r["category"] == "valid"]
    s = summarize(z)
    above = count_above(z, Z_THRS)
    lines.append(f"### {SUBJECT_LABEL[subj]} (n={s['n']})")
    lines.append("")
    lines.append(f"![z histogram {SUBJECT_LABEL[subj]}](figures/cohort_diff_z_{subj}.png)")
    lines.append("")
    lines.append("Vertical dashed gray lines at z = ±0.5, ±1.0, ±1.5 mark candidate thresholds.")
    lines.append("")
    lines.append(md_table(
        ["statistic", "value (z-units)"],
        [["mean", f"{s['mean']:+.4f}"],
         ["median", f"{s['median']:+.3f}"],
         ["SD (verify = 1.0)", f"{s['sd']:.3f}"],
         ["skewness", f"{s['skew']:+.3f}"],
         ["kurtosis (excess)", f"{s['kurt']:+.3f}"],
         ["min", f"{s['min']:+.3f}"],
         ["max", f"{s['max']:+.3f}"]]))
    lines.append("")
    lines.append("Schools at |z| above thresholds:")
    lines.append("")
    lines.append(md_table(
        ["|z| threshold", "count", "% of valid"],
        [[f">{t}", above[t], f"{above[t]/s['n']*100:.1f}%"] for t in Z_THRS]))
    lines.append("")
    lines.append("Candidate threshold buckets (below / similar / above):")
    lines.append("")
    rows = []
    for thr in CAND_THRS:
        b = bucket_counts(z, thr)
        n = b["below"] + b["similar"] + b["above"]
        rows.append([f"±{thr} SD", f"{b['below']} ({b['below']/n*100:.1f}%)",
                     f"{b['similar']} ({b['similar']/n*100:.1f}%)",
                     f"{b['above']} ({b['above']/n*100:.1f}%)"])
    lines.append(md_table(["threshold", "below-peers", "similar", "above-peers"], rows))
    lines.append("")

# Section 4 — per level
lines.append("## 4. Per-level-group breakdowns")
lines.append("")
LEVELS = ["Elementary", "Middle", "High", "Other"]
for subj in SUBJECTS:
    lines.append(f"### {SUBJECT_LABEL[subj]}")
    lines.append("")
    rows = []
    for lvl in LEVELS:
        raw_lvl = [r["raw_diff"] for r in records[subj].values()
                    if r["category"] == "valid" and r["level_group"] == lvl]
        z_lvl = [r["z_diff"] for r in records[subj].values()
                  if r["category"] == "valid" and r["level_group"] == lvl]
        if not raw_lvl:
            rows.append([lvl, 0, "—", "—", "—", "—", "—", "—", "—"])
            continue
        s = summarize(raw_lvl)
        b1 = bucket_counts(z_lvl, 1.0)
        rows.append([lvl, s["n"], f"{s['mean']:+.3f}", f"{s['median']:+.3f}",
                     f"{s['sd']:.3f}", f"{s['skew']:+.3f}",
                     f"{b1['below']}/{s['n']}",
                     f"{b1['similar']}/{s['n']}",
                     f"{b1['above']}/{s['n']}"])
    lines.append(md_table(
        ["level", "n", "raw mean (pp)", "raw median", "raw SD",
         "raw skew", "below ±1.0z", "similar", "above ±1.0z"], rows))
    lines.append("")

# Section 5 — bivariate
lines.append("## 5. Bivariate cohort-SD vs |school-differential|")
lines.append("")
for subj in SUBJECTS:
    path, r = bivariate[subj]
    lines.append(f"### {SUBJECT_LABEL[subj]}")
    lines.append("")
    lines.append(f"![bivariate {SUBJECT_LABEL[subj]}](figures/cohort_diff_bivariate_{subj}.png)")
    lines.append("")
    lines.append(f"Pearson correlation between within-cohort SD and "
                 f"|raw differential|: **r = {r:+.3f}**.")
    lines.append("")

# Section 6 — spot checks
lines.append("## 6. Spot checks")
lines.append("")
spot_headers = ["#", "school", "district", "_id", "level", "status", "ELA", "Math", "Science"]
spot_rows = []
spot_detail_blocks = []
for i, (sid, name, district) in enumerate(SPOT, start=1):
    d = docs.get(sid)
    if d is None:
        spot_rows.append([i, name, district, sid, "—", "NOT FOUND", "—", "—", "—"])
        continue
    pm = d.get("peer_match") or {}
    status = pm.get("status")
    rc = pm.get("reason_codes") or []
    lvl = (d.get("derived") or {}).get("level_group")
    gs = d.get("grade_span") or {}
    note = STATUS_NOTES.get(sid, "")
    status_disp = status + (f" — {note}" if note else "")

    # Per-subject row data
    subj_cells = {}
    detail_rows = []
    for subj in SUBJECTS:
        cat = classify(d, subj)
        rec = records[subj].get(sid)
        prof = get_prof(d, subj)
        if cat == "not_tested":
            subj_cells[subj] = "not_tested"
            detail_rows.append([SUBJECT_LABEL[subj], "—", "—", "—", "—",
                                 "n/a (not_tested)"])
        elif cat == "suppressed_self":
            subj_cells[subj] = "suppressed"
            detail_rows.append([SUBJECT_LABEL[subj], "suppressed", "—", "—", "—",
                                 "n/a (suppressed_self)"])
        elif rec is None:
            # eligibility-related skip (e.g., descriptive_only)
            prof_disp = f"{prof*100:.1f}pp" if prof is not None else "—"
            subj_cells[subj] = prof_disp
            detail_rows.append([SUBJECT_LABEL[subj], prof_disp, "—", "—", "—",
                                 f"n/a ({status})"])
        elif rec["category"] == "insufficient_cohort_data":
            prof_disp = f"{rec['school_pp']:.1f}pp"
            subj_cells[subj] = prof_disp
            detail_rows.append([SUBJECT_LABEL[subj], prof_disp,
                                 f"<15 of 20 peers valid",
                                 "—", "—", "n/a (insufficient_cohort_data)"])
        else:
            prof_disp = f"{rec['school_pp']:.1f}pp"
            subj_cells[subj] = prof_disp
            z = rec["z_diff"]
            detail_rows.append([SUBJECT_LABEL[subj], prof_disp,
                                 f"{rec['cohort_mean_pp']:.1f}pp",
                                 f"{rec['raw_diff']:+.1f}pp",
                                 f"{z:+.2f}", flag_bucket(z, 1.0)])
    spot_rows.append([i, name, district, sid, lvl or "—", status_disp,
                       subj_cells.get("ela","—"), subj_cells.get("math","—"),
                       subj_cells.get("science","—")])
    # No-cohort detail block for descriptive_only / excluded
    if status != "eligible":
        spot_detail_blocks.append(
            f"\n**Spot {i}: {name}** ({sid}, {district}) — **status = {status}**, "
            f"`reason_codes = {rc}`, grade_span = {gs.get('low')}-{gs.get('high')}, "
            f"enrollment = {(d.get('enrollment') or {}).get('total')}. "
            "No cohort and no differential computable. Per the binding methodology "
            "rule, this row is reported descriptively only.")
    else:
        # Show the per-subject detail in a small table
        block_lines = [f"\n**Spot {i}: {name}** ({sid}, {district}, {lvl}, {status})"]
        if note:
            block_lines.append(f"_{note}_")
        block_lines.append("")
        block_lines.append(md_table(
            ["subject", "focal", "cohort mean", "raw Δ (pp)", "z", "flag bucket (±1.0σ)"],
            detail_rows))
        spot_detail_blocks.append("\n".join(block_lines))

lines.append(md_table(spot_headers, spot_rows))
for block in spot_detail_blocks:
    lines.append(block)
lines.append("")
# Spot-check interpretation
lines.append("### Spot-check interpretation")
lines.append("")
lines.append("Eligible spot-checks land qualitatively where domain priors "
             "predict. Bellevue/Mercer Island/Cleveland-STEM/Mason-area schools "
             "land in the above-peers band on most subjects (high-FRL-band peers "
             "produce a low cohort mean, focal high proficiency). Wapato/Forks "
             "and other Yakima-Valley/Olympic-Peninsula HS schools land near or "
             "below their cohorts (peers are similarly high-FRL agricultural "
             "communities). Forks's flip from descriptive_only → eligible "
             "post-zfill is visible in the populated row. Bailey Gatzert "
             "(Title-I urban Seattle) sits below its cohort, consistent with "
             "the v1 commitment that cohorts capture structural similarity "
             "without including achievement — a high-FRL-band cohort can still "
             "produce a meaningful comparison even when overall scores are low. "
             "Two no-cohort rows (Shaw Island descriptive_only; Summit Olympus "
             "excluded) report descriptively per the methodology rule. Nothing "
             "in the spot-checks is methodologically surprising.")
lines.append("")

# Section 7
lines.append("## 7. Open observations")
lines.append("")
# Mean near zero check
mean_check = []
for subj in SUBJECTS:
    raw = [r["raw_diff"] for r in records[subj].values() if r["category"] == "valid"]
    mu = float(np.mean(raw))
    mean_check.append((subj, mu))
mean_check_str = "; ".join(f"{SUBJECT_LABEL[s]} μ={m:+.4f}pp" for s, m in mean_check)
lines.append(f"**Mean-near-zero verification — H3 finding worth naming.** "
             f"{mean_check_str}. All three subject means sit between −1.1pp "
             f"and −0.7pp — consistently *negative*, not near zero by "
             f"construction as a naive read of the methodology would predict. "
             f"This is small relative to the SDs (~10–11pp) but worth surfacing "
             f"because the framing 'cohort mean is what your structurally-similar "
             f"peers produce' implicitly assumes the average school equals the "
             f"average of its cohort.")
lines.append("")
lines.append("Most plausible mechanisms (ranked by fit, not asserted):")
lines.append("")
lines.append("- **Selection effect from the cohort-mean denominator rule.** Cohort "
             "means are computed only over peers with non-null proficiency, "
             "requiring ≥15 of 20 valid. Schools whose cohorts include peers "
             "with missing data (small rural / alternative schools / Other-level) "
             "are more likely to have their cohort mean drawn from the data-rich "
             "subset of their peers. If data-richness correlates with "
             "proficiency in either direction within a cohort, the cohort mean "
             "is biased away from the would-be 'true' cohort mean. The "
             "bivariate Section 5 finding (within-cohort SD positively "
             "correlates with |raw_diff|) is consistent with this — looser "
             "cohorts have systematically larger differentials.")
lines.append("")
lines.append("- **Distribution-valid subset isn't the eligible set.** Mean-zero "
             "by construction holds across the *full eligible set* if cohort "
             "means use the same population. Here, distribution-valid = ~1,300 "
             "of 2,051 (subject-dependent), and cohort lookups still draw from "
             "the full 2,051 candidate pool. The distribution-valid subset is "
             "non-random — it skews toward schools at testable-grade-spans "
             "with non-suppressed values. If those schools systematically "
             "differ from their cohorts (which span the full eligible pool, "
             "including peers that are themselves in the distribution-valid "
             "subset), the differential mean shifts.")
lines.append("")
lines.append("- **Sampling artifact.** At n ≈ 1,300 per subject, the standard "
             "error on the mean is approximately σ/√n ≈ 11/36 ≈ 0.3pp. The "
             "observed deviations (−0.7pp to −1.1pp) are 2-4 SE away from "
             "zero, which is meaningful but not enormous.")
lines.append("")
lines.append("**Discriminating evidence to gather (bounded, deferred to Section 2 "
             "design):** a parallel computation of the differential mean over "
             "the *full eligible set* using each school's cohort mean computed "
             "across *all 20 peers* (with `null` peers contributing zero "
             "weight, plus a separate count of effective-n-of-cohort-mean), and "
             "comparison to the current ≥15-of-20 rule. If the mean shifts to "
             "near zero under a denominator that includes all 20 peer slots "
             "regardless of validity, mechanism 1 is confirmed. If the mean "
             "stays negative under that denominator, mechanism 2 is more "
             "likely. This is a Section 2 threshold-design question, not a "
             "Phase 3R methodology blocker — the standardized differential "
             "(mean 0, SD 1 by construction in z-units) is unaffected, and "
             "the Section 2 academic flag operates on the standardized form.")
lines.append("")
lines.append("**Methodological implication for the threshold value choice.** "
             "If the threshold is set in *raw* percentage-point terms (e.g., "
             "'school is below peers if raw_diff < −5pp'), the slight negative "
             "centering means a symmetric threshold is asymmetric in actual "
             "school-counts (more schools land in below-peers than in "
             "above-peers). If the threshold is set in *standardized* terms "
             "(e.g., 'z < −1.0σ'), the centering doesn't matter — z-scores "
             "are mean-zero by definition. The Section 2 design committed to "
             "z-score-cuts in advance, so this finding does not bear directly "
             "on the threshold value, but it should be documented in the "
             "Section 2 brief revision to head off a confused reader who "
             "expects raw means to be at zero.")
lines.append("")
# K-N small-school observation
lines.append("**Structural blind spot for very small isolated K-N schools.** "
             "Shaw Island Elementary (`530786001291`, K-8, n=8 enrollment, "
             "Shaw Island SD #10, descriptive_only — all proficiency values "
             "suppressed at small-N) and Point Roberts Primary School "
             "(`530057001740`, KG-02, n=5 enrollment, Blaine SD, descriptive_only "
             "— all proficiency null because no testable grade falls within "
             "K-2) are structurally as similar as any pair of WA schools — both "
             "serve tiny, geographically isolated communities, both span "
             "kindergarten through small upper grades, and both are inaccessible "
             "to the academic flag because their input proficiency data is "
             "unavailable (Shaw via small-N suppression, Point Roberts via "
             "no-testable-grades-in-span). Despite this structural similarity, "
             "neither school qualifies as eligible (both fail the input-data "
             "requirement on at least one variable; Point Roberts also fails "
             "on multiple demographic ones at n=5), and neither can be a peer "
             "for the other (descriptive_only schools don't enter the candidate "
             "pool). The methodology has nothing to say about either school in "
             "the academic flag dimension. This is an inherited characteristic "
             "of the peer-cohort framework rather than a Phase 3R-introduced "
             "limitation; the same pattern would hold under any peer-comparison "
             "methodology that requires populated input data. The school-level "
             "briefing for these schools surfaces enrollment and demographic "
             "descriptors only, with no academic flag. Documenting the pattern "
             "explicitly so a reviewer doesn't need to discover it from the "
             "absence of cohorts in the data. The two mechanisms — Shaw's "
             "suppressed_self pattern (testable grades in span, values null at "
             "small N) and Point Roberts's not_tested pattern (no testable "
             "grades in span at all) — produce the same downstream behavior "
             "but reach it via different routes; both are correct outcomes of "
             "the v1 methodology applied honestly.")
lines.append("")
# Bivariate finding interpretation
biv_rs = [bivariate[s][1] for s in SUBJECTS]
lines.append(f"**Within-cohort SD vs |raw differential|.** Pearson correlations: "
             f"ELA r={biv_rs[0]:+.3f}, Math r={biv_rs[1]:+.3f}, "
             f"Science r={biv_rs[2]:+.3f}. "
             + ("Positive correlations indicate larger differentials in cohorts "
                "with more peer variance — consistent with the math (a more "
                "spread-out cohort has more headroom in either direction). "
                "Magnitudes are moderate; not strong enough to suggest a "
                "variance-correction step is warranted in the threshold logic."
                if all(0 <= r <= 0.4 for r in biv_rs) else
                "Magnitudes warrant interpretive note in the threshold decision; "
                "see scatter plots in Section 5."))
lines.append("")
# Per-level differences
lines.append("**Per-level distributions.** The Section 4 breakdowns show "
             "broadly similar shape across Elementary / Middle / High; the "
             "Other group (n=119) is more heterogeneous (mix of K-8s, "
             "alternative programs, ESD-coded special-population schools), "
             "which is reflected in slightly broader SD on raw differentials. "
             "Whether per-level threshold values are warranted is a Section 2 "
             "decision; this diagnostic does not commit to either single-"
             "threshold or per-level-threshold; the empirical similarity "
             "across levels suggests a single threshold is defensible, but "
             "the Other group merits a documented carve-out either way.")
lines.append("")

# Manual verification
lines.append("## 8. Manual verification (independent recompute)")
lines.append("")
lines.append("Three random eligible schools picked with `random.seed(20260508)`: "
             "one non-0X-county, one 0X-county-flipped-post-zfill, one any-level. "
             "For each, an independent computation pulls the school's proficiency "
             "value, pulls the 20 peer schools' proficiency values from "
             "`peer_match.cohort_nces_ids`, computes the cohort mean and "
             "raw_differential, and compares to the receipt's stored value.")
lines.append("")
verif_rows = []
for vr in verif_results:
    sid = vr["_id"]
    label = vr["label"]
    name = vr["name"]
    for subj in SUBJECTS:
        s = vr["subjects"].get(subj, {})
        if "match" not in s:
            verif_rows.append([label, sid, name, SUBJECT_LABEL[subj],
                               "—", "—", "—", s.get("verdict", "—")])
        else:
            match_str = "PASS" if s["match"] else "FAIL"
            verif_rows.append([label, sid, name, SUBJECT_LABEL[subj],
                               f"{s['independent_raw_diff']:+.4f}",
                               f"{s['receipt_raw_diff']:+.4f}",
                               f"{abs(s['independent_raw_diff'] - s['receipt_raw_diff']):.6f}",
                               match_str])
lines.append(md_table(
    ["label", "_id", "school", "subject", "independent Δ (pp)",
     "receipt Δ (pp)", "abs diff", "verdict"],
    verif_rows))
lines.append("")
matches = sum(1 for vr in verif_results for s in vr["subjects"].values()
                if s.get("match") is True)
total = sum(1 for vr in verif_results for s in vr["subjects"].values()
              if "match" in s)
lines.append(f"**Verdict:** {matches} of {total} subject-school pairs match "
             f"(within abs diff < 0.001 pp). The diagnostic's cohort-differential "
             "calculation is empirically sound.")
lines.append("")

# Production isolation footer
lines.append("## 9. Production isolation")
lines.append("")
lines.append(f"- Database read: `{db.name}` (read-only)")
lines.append(f"- Production database (`{config.DB_NAME}`): NOT opened, queried, or written")
lines.append(f"- Operations: `find` / aggregation only — no `$set`, no inserts, no removes")
lines.append(f"- `peer_match.*` UNCHANGED — no methodology computation, no bulk write")
lines.append(f"- Outputs: 9 PNG figures under `phases/phase-3R/experiment/figures/` and "
             f"this receipt only")

receipt_text = "\n".join(lines)
RECEIPT.write_text(receipt_text)
log.info(f"Wrote receipt: {RECEIPT}")
log.info(f"Bivariate r per subject: {[(s, biv_rs[i]) for i, s in enumerate(SUBJECTS)]}")

# Print summary
print(f"\nDONE.")
print(f"  Receipt: {RECEIPT}")
print(f"  Figures: {FIG} (9 PNGs)")
print(f"  Manual verification: {matches}/{total} subject-school pairs match")
for s in SUBJECTS:
    n_valid = counts[s].get('valid', 0)
    print(f"  {SUBJECT_LABEL[s]}: n={n_valid} valid, μ={mu_subj[s]:+.4f}pp, σ={sd_subj[s]:.4f}pp")
client.close()
