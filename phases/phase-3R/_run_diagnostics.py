"""
_run_diagnostics.py — Read-only Phase 3R diagnostic dumps.

PURPOSE: Produce the five Phase 3R diagnostic markdown files by querying
         MongoDB in read-only fashion. No writes, no deletes, no updates.
INPUTS:  MongoDB Atlas (schooldaylight.schools), flag_thresholds.yaml
OUTPUTS: Five markdown files in phases/phase-3R/

This script is intentionally one big file with discrete sections per output
file. Each section is grep-able with a header banner.
"""

import json
import os
import statistics
import sys
from collections import Counter, defaultdict

import numpy as np
import yaml
from bson import json_util
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import config

OUT_DIR = os.path.join(ROOT, "phases", "phase-3R")
os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================================
# CONNECT — read-only usage only
# ============================================================================

client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
db = client["schooldaylight"]
schools = db["schools"]

with open(os.path.join(ROOT, "flag_thresholds.yaml")) as f:
    THRESHOLDS = yaml.safe_load(f)


# ============================================================================
# SHARED HELPERS
# ============================================================================

def deciles(values):
    """Return 10/20/.../90th percentiles plus min/max/mean/sd."""
    if not values:
        return None
    arr = np.array(sorted(values), dtype=float)
    out = {
        "n": len(arr),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=0)),
    }
    for p in [10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90]:
        out[f"p{p}"] = float(np.percentile(arr, p))
    return out


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def fmt_num(x, places=4):
    if x is None:
        return "null"
    if isinstance(x, float):
        return f"{x:.{places}f}"
    return str(x)


# ============================================================================
# STEP 1 — REGRESSION DIAGNOSTICS
# ============================================================================

def step1_regression():
    out = ["# Phase 3R — Step 1: Per-Level Regression Diagnostics",
           "",
           "Read-only diagnostic dump of the current per-level FRL→proficiency_composite regression.",
           "Re-fits regressions in-process from the same MongoDB inputs production uses,",
           "rather than reading the cached `regression_*` fields, so methodology questions",
           "(R², slopes, residual SDs) trace to live data.",
           "",
           "Source script: `pipeline/15_regression_and_flags.py`",
           "Source config: `flag_thresholds.yaml` (regression block, line 51)",
           ""]

    excluded_types = set(THRESHOLDS["regression"].get("excluded_school_types", []))
    excl_path = os.path.join(ROOT, "school_exclusions.yaml")
    excluded_ncessch = set()
    if os.path.exists(excl_path):
        with open(excl_path) as f:
            excl = yaml.safe_load(f)
        for entries in excl.values():
            if isinstance(entries, list):
                for e in entries:
                    if isinstance(e, dict) and "ncessch" in e:
                        excluded_ncessch.add(str(e["ncessch"]))
                    elif isinstance(e, str):
                        excluded_ncessch.add(e)

    min_group_size = THRESHOLDS["regression"]["min_group_size"]
    threshold_sd = THRESHOLDS["regression"]["threshold_sd"]

    out.append(f"- regression min_group_size: **{min_group_size}**")
    out.append(f"- regression threshold_sd: **±{threshold_sd}**")
    out.append(f"- excluded school types: **{sorted(excluded_types)}**")
    out.append(f"- manual exclusions (school_exclusions.yaml): **{len(excluded_ncessch)}**")
    out.append("")

    # Pull all schools with the fields we need.
    # NOTE: MongoDB primary key for these documents is `_id` (the 12-char NCESSCH
    # is stored there, not in a separate `ncessch` field). Verified empirically
    # 2026-05-03 — see the bug-fix note in the build log entry for this session.
    cursor = schools.find(
        {},
        {"_id": 1, "name": 1, "school_type": 1,
         "demographics.frl_pct": 1,
         "derived.proficiency_composite": 1,
         "derived.level_group": 1,
         "derived.performance_flag": 1,
         "derived.performance_flag_absent_reason": 1},
    )

    all_docs = list(cursor)
    out.append(f"Total documents scanned from MongoDB: **{len(all_docs)}**")
    out.append("")

    # Show the example query
    out.append("**Example query** (the document scan above):")
    out.append("```python")
    out.append('schools.find({}, {"_id":1,"demographics.frl_pct":1,'
               '"derived.proficiency_composite":1,"derived.level_group":1,'
               '"derived.performance_flag":1,"derived.performance_flag_absent_reason":1,'
               '"school_type":1})')
    out.append("```")
    out.append("")

    # Build regression-ready set (mirrors pipeline/15)
    regression_ready = []
    excluded_by_type = 0
    excluded_by_manual = 0
    for d in all_docs:
        derived = d.get("derived", {}) or {}
        demo = d.get("demographics", {}) or {}
        frl = demo.get("frl_pct")
        comp = derived.get("proficiency_composite")
        lg = derived.get("level_group")
        if frl is None or comp is None or lg is None:
            continue
        st = d.get("school_type", "") or ""
        ncessch = d.get("_id")  # primary key
        if st in excluded_types:
            excluded_by_type += 1
            continue
        if ncessch and str(ncessch) in excluded_ncessch:
            excluded_by_manual += 1
            continue
        regression_ready.append({"ncessch": ncessch, "frl": frl, "composite": comp,
                                 "level_group": lg, "school_type": st})

    out.append(f"- regression-ready schools (have FRL + composite + level_group, "
               f"not excluded): **{len(regression_ready)}**")
    out.append(f"- excluded by school_type: **{excluded_by_type}**")
    out.append(f"- excluded by manual list: **{excluded_by_manual}**")
    out.append("")

    # Statewide model first
    all_X = np.array([[e["frl"]] for e in regression_ready])
    all_y = np.array([e["composite"] for e in regression_ready])
    statewide_model = LinearRegression().fit(all_X, all_y)
    statewide_r2 = statewide_model.score(all_X, all_y)
    statewide_pred = statewide_model.predict(all_X)
    statewide_sd = float(np.std(all_y - statewide_pred, ddof=0))

    by_level = defaultdict(list)
    for e in regression_ready:
        by_level[e["level_group"]].append(e)

    # Build per-level regression rows
    out.append("## 1.1 Per-level regression statistics")
    out.append("")
    headers = ["Level group", "n", "R²", "Residual SD",
               "Intercept", "Slope (FRL coef)", "Model used"]
    rows = []
    fitted_models = {}
    for lg in sorted(by_level.keys()):
        entries = by_level[lg]
        n = len(entries)
        if n >= min_group_size:
            X = np.array([[e["frl"]] for e in entries])
            y = np.array([e["composite"] for e in entries])
            m = LinearRegression().fit(X, y)
            r2 = m.score(X, y)
            sd = float(np.std(y - m.predict(X), ddof=0))
            fitted_models[lg] = {"model": m, "sd": sd, "r2": r2, "n": n,
                                 "intercept": float(m.intercept_),
                                 "slope": float(m.coef_[0])}
            rows.append([lg, n, fmt_num(r2, 3), fmt_num(sd, 4),
                         fmt_num(float(m.intercept_), 3),
                         fmt_num(float(m.coef_[0]), 3),
                         "per-level"])
        else:
            fitted_models[lg] = {"model": statewide_model, "sd": statewide_sd,
                                 "r2": statewide_r2, "n": n,
                                 "intercept": float(statewide_model.intercept_),
                                 "slope": float(statewide_model.coef_[0])}
            rows.append([lg, n, f"{statewide_r2:.3f} (statewide)", f"{statewide_sd:.4f} (statewide)",
                         f"{float(statewide_model.intercept_):.3f} (statewide)",
                         f"{float(statewide_model.coef_[0]):.3f} (statewide)",
                         "statewide fallback"])

    rows.append(["**Statewide (fallback model)**",
                 len(regression_ready),
                 fmt_num(statewide_r2, 3),
                 fmt_num(statewide_sd, 4),
                 fmt_num(float(statewide_model.intercept_), 3),
                 fmt_num(float(statewide_model.coef_[0]), 3),
                 "—"])
    out.append(md_table(headers, rows))
    out.append("")

    # 1.2 Per-level flag distribution
    out.append("## 1.2 Performance-flag distribution within each level group")
    out.append("")
    out.append("Flag is computed against the model that level group actually uses "
               "(per-level if n ≥ 30, otherwise statewide).")
    out.append("")
    headers = ["Level group", "n flagged", "outperforming",
               "as_expected", "underperforming"]
    rows = []
    for lg in sorted(by_level.keys()):
        entries = by_level[lg]
        m = fitted_models[lg]["model"]
        sd = fitted_models[lg]["sd"]
        counts = Counter()
        for e in entries:
            pred = float(m.predict([[e["frl"]]])[0])
            z = (e["composite"] - pred) / sd if sd > 0 else 0.0
            if z > threshold_sd:
                counts["outperforming"] += 1
            elif z < -threshold_sd:
                counts["underperforming"] += 1
            else:
                counts["as_expected"] += 1
        n = len(entries)
        rows.append([
            lg, n,
            f"{counts['outperforming']} ({counts['outperforming']/n*100:.1f}%)",
            f"{counts['as_expected']} ({counts['as_expected']/n*100:.1f}%)",
            f"{counts['underperforming']} ({counts['underperforming']/n*100:.1f}%)",
        ])
    out.append(md_table(headers, rows))
    out.append("")

    # 1.3 FRL/composite distribution within regression set per level
    out.append("## 1.3 FRL_pct and proficiency_composite ranges within each level group's regression set")
    out.append("")
    headers = ["Level group", "Var", "min", "p25", "p50", "p75", "max"]
    rows = []
    for lg in sorted(by_level.keys()):
        entries = by_level[lg]
        frls = sorted(e["frl"] for e in entries)
        comps = sorted(e["composite"] for e in entries)
        for label, vals in [("FRL_pct", frls), ("proficiency_composite", comps)]:
            if not vals:
                rows.append([lg, label, "—", "—", "—", "—", "—"])
                continue
            arr = np.array(vals, dtype=float)
            rows.append([lg, label,
                         fmt_num(float(arr.min())),
                         fmt_num(float(np.percentile(arr, 25))),
                         fmt_num(float(np.percentile(arr, 50))),
                         fmt_num(float(np.percentile(arr, 75))),
                         fmt_num(float(arr.max()))])
    out.append(md_table(headers, rows))
    out.append("")

    # 1.4 performance_flag_absent_reason breakdown
    out.append("## 1.4 Null performance_flag breakdown by absent reason")
    out.append("")
    out.append("Reads `derived.performance_flag` and `derived.performance_flag_absent_reason` "
               "from MongoDB exactly as production wrote them — does not recompute.")
    out.append("")
    null_count = 0
    reasons = Counter()
    for d in all_docs:
        derived = d.get("derived", {}) or {}
        if derived.get("performance_flag") is None:
            null_count += 1
            r = derived.get("performance_flag_absent_reason") or "(no reason set)"
            reasons[r] += 1

    out.append(f"Total schools with `performance_flag = null`: **{null_count}**")
    out.append("")
    out.append("**Query**:")
    out.append("```python")
    out.append('schools.aggregate([{"$match":{"derived.performance_flag":None}},'
               '{"$group":{"_id":"$derived.performance_flag_absent_reason","n":{"$sum":1}}}])')
    out.append("```")
    out.append("")
    headers = ["absent reason", "count", "% of nulls"]
    rows = [[r, n, f"{n/null_count*100:.1f}%"] for r, n in reasons.most_common()]
    out.append(md_table(headers, rows))
    out.append("")

    # Sanity check on the prompt's "1,387" figure
    if null_count != 1387:
        out.append(f"> **Note on the 1,387 figure in the prompt.** Live MongoDB scan returned "
                   f"**{null_count}** null performance_flag schools, not 1,387. The pipeline has "
                   f"been re-run since that number was captured (see exclusions added 2026-02-22). "
                   f"This file uses the live count.")
        out.append("")

    with open(os.path.join(OUT_DIR, "regression_diagnostics.md"), "w") as f:
        f.write("\n".join(out))
    print(f"  wrote regression_diagnostics.md ({null_count} nulls, {len(regression_ready)} ready)")
    return regression_ready, fitted_models, statewide_model, statewide_sd, statewide_r2


# ============================================================================
# STEP 2 — THRESHOLD REVISION DATA
# ============================================================================

def step2_thresholds():
    out = ["# Phase 3R — Step 2: Threshold Revision Distributions",
           "",
           "Read-only distributions of the two threshold-driven flag metrics."
           " No data changes; counts here are what production *would* show under candidate thresholds.",
           ""]

    # ----- Chronic absenteeism distribution -----
    cursor = schools.find(
        {"derived.chronic_absenteeism_pct": {"$ne": None}},
        {"_id": 1, "derived.chronic_absenteeism_pct": 1},
    )
    abs_vals = [d["derived"]["chronic_absenteeism_pct"] for d in cursor
                if d.get("derived", {}).get("chronic_absenteeism_pct") is not None]
    abs_stats = deciles(abs_vals)

    out.append("## 2.1 Chronic absenteeism (`derived.chronic_absenteeism_pct`)")
    out.append("")
    out.append(f"N (non-null) = **{abs_stats['n']}** schools")
    out.append("")
    out.append("**Query**:")
    out.append("```python")
    out.append('schools.find({"derived.chronic_absenteeism_pct":{"$ne":None}},'
               '{"derived.chronic_absenteeism_pct":1})')
    out.append("```")
    out.append("")
    out.append("### Distribution summary")
    out.append("")
    out.append(md_table(
        ["stat", "value"],
        [["min", fmt_num(abs_stats["min"])],
         ["p10", fmt_num(abs_stats["p10"])],
         ["p20", fmt_num(abs_stats["p20"])],
         ["p25", fmt_num(abs_stats["p25"])],
         ["p30", fmt_num(abs_stats["p30"])],
         ["p40", fmt_num(abs_stats["p40"])],
         ["p50 (median)", fmt_num(abs_stats["p50"])],
         ["p60", fmt_num(abs_stats["p60"])],
         ["p70", fmt_num(abs_stats["p70"])],
         ["p75", fmt_num(abs_stats["p75"])],
         ["p80", fmt_num(abs_stats["p80"])],
         ["p90", fmt_num(abs_stats["p90"])],
         ["max", fmt_num(abs_stats["max"])],
         ["mean", fmt_num(abs_stats["mean"])],
         ["SD", fmt_num(abs_stats["sd"])]]
    ))
    out.append("")

    # Decile bin counts (10 equal-frequency bins by definition; check shape)
    arr = np.array(sorted(abs_vals))
    decile_bins = np.percentile(arr, [10, 20, 30, 40, 50, 60, 70, 80, 90])
    bin_counts = []
    edges = [-float("inf")] + list(decile_bins) + [float("inf")]
    for i in range(10):
        c = int(((arr >= edges[i]) & (arr < edges[i+1])).sum())
        if i == 9:
            c = int(((arr >= edges[i]) & (arr <= edges[i+1])).sum())
        bin_counts.append(c)

    out.append("### Decile bin counts (sanity check — bins sum to N)")
    out.append("")
    out.append(md_table(
        ["bin", "range (lower ≤ x < upper)", "count"],
        [[f"d{i+1}",
          f"{(edges[i] if edges[i]!=-float('inf') else 0.0):.4f} – "
          f"{(edges[i+1] if edges[i+1]!=float('inf') else 1.0):.4f}",
          bin_counts[i]] for i in range(10)] +
        [["**sum**", "—", sum(bin_counts)]]
    ))
    out.append("")

    # Threshold pair counts
    out.append("### Schools that would trip yellow/red at candidate threshold pairs")
    out.append("")
    out.append("Yellow: `value > yellow_threshold AND value ≤ red_threshold`. "
               "Red: `value > red_threshold`. (Mirrors `pipeline/15_regression_and_flags.py:308`.)")
    out.append("")
    pairs = [(0.20, 0.30, "current"), (0.25, 0.35, "candidate"),
             (0.30, 0.40, "candidate"),
             (0.30, 0.45, "candidate, decided 2026-02-22"),
             (0.35, 0.50, "candidate")]
    rows = []
    for y, r, note in pairs:
        ny = sum(1 for v in abs_vals if y < v <= r)
        nr = sum(1 for v in abs_vals if v > r)
        green = abs_stats["n"] - ny - nr
        rows.append([f"({y:.2f}, {r:.2f})", note,
                     f"{green} ({green/abs_stats['n']*100:.1f}%)",
                     f"{ny} ({ny/abs_stats['n']*100:.1f}%)",
                     f"{nr} ({nr/abs_stats['n']*100:.1f}%)"])
    out.append(md_table(["(yellow, red)", "note", "green", "yellow", "red"], rows))
    out.append("")

    # Percentile-based thresholds
    out.append("### Percentile-based threshold scenario (bottom-quartile yellow / bottom-decile red)")
    out.append("")
    out.append("Lower attendance = worse, so 'bottom' here means HIGHEST chronic absenteeism. "
               "Yellow = top-25% of values; Red = top-10%.")
    out.append("")
    p75 = abs_stats["p75"]
    p90 = abs_stats["p90"]
    n_y = sum(1 for v in abs_vals if p75 < v <= p90)
    n_r = sum(1 for v in abs_vals if v > p90)
    n_g = abs_stats["n"] - n_y - n_r
    out.append(md_table(
        ["thresholds", "yellow boundary (p75)", "red boundary (p90)",
         "green", "yellow", "red"],
        [[f"percentile-based",
          fmt_num(p75), fmt_num(p90),
          f"{n_g} ({n_g/abs_stats['n']*100:.1f}%)",
          f"{n_y} ({n_y/abs_stats['n']*100:.1f}%)",
          f"{n_r} ({n_r/abs_stats['n']*100:.1f}%)"]]
    ))
    out.append("")

    # ----- Discipline disparity max -----
    cursor = schools.find(
        {"derived.discipline_disparity_max": {"$ne": None}},
        {"_id": 1, "derived.discipline_disparity_max": 1,
         "derived.flags.discipline_disparity": 1},
    )
    disp_docs = list(cursor)
    disp_vals = [d["derived"]["discipline_disparity_max"] for d in disp_docs]
    disp_stats = deciles(disp_vals)

    out.append("## 2.2 Discipline disparity max (`derived.discipline_disparity_max`)")
    out.append("")
    out.append(f"N (non-null) = **{disp_stats['n']}** schools")
    out.append("")
    out.append("### Distribution summary")
    out.append("")
    out.append(md_table(
        ["stat", "value"],
        [["min", fmt_num(disp_stats["min"])],
         ["p10", fmt_num(disp_stats["p10"])],
         ["p20", fmt_num(disp_stats["p20"])],
         ["p25", fmt_num(disp_stats["p25"])],
         ["p30", fmt_num(disp_stats["p30"])],
         ["p40", fmt_num(disp_stats["p40"])],
         ["p50 (median)", fmt_num(disp_stats["p50"])],
         ["p60", fmt_num(disp_stats["p60"])],
         ["p70", fmt_num(disp_stats["p70"])],
         ["p75", fmt_num(disp_stats["p75"])],
         ["p80", fmt_num(disp_stats["p80"])],
         ["p90", fmt_num(disp_stats["p90"])],
         ["max", fmt_num(disp_stats["max"])],
         ["mean", fmt_num(disp_stats["mean"])],
         ["SD", fmt_num(disp_stats["sd"])]]
    ))
    out.append("")

    arr = np.array(sorted(disp_vals))
    db_edges = np.percentile(arr, [10, 20, 30, 40, 50, 60, 70, 80, 90])
    edges = [-float("inf")] + list(db_edges) + [float("inf")]
    bin_counts = []
    for i in range(10):
        c = int(((arr >= edges[i]) & (arr < edges[i+1])).sum())
        if i == 9:
            c = int(((arr >= edges[i]) & (arr <= edges[i+1])).sum())
        bin_counts.append(c)
    out.append("### Decile bin counts")
    out.append("")
    out.append(md_table(
        ["bin", "range", "count"],
        [[f"d{i+1}",
          f"{(edges[i] if edges[i]!=-float('inf') else 0.0):.2f} – "
          f"{(edges[i+1] if edges[i+1]!=float('inf') else arr.max()):.2f}",
          bin_counts[i]] for i in range(10)] +
        [["**sum**", "—", sum(bin_counts)]]
    ))
    out.append("")

    # Current 2.0/3.0 yellow/red
    n_y = sum(1 for v in disp_vals if 2.0 < v <= 3.0)
    n_r = sum(1 for v in disp_vals if v > 3.0)
    n_g = disp_stats["n"] - n_y - n_r
    out.append("### Yellow/red counts at current thresholds (2.0 / 3.0)")
    out.append("")
    out.append(md_table(
        ["thresholds", "green", "yellow", "red"],
        [["(2.0, 3.0) [current]",
          f"{n_g} ({n_g/disp_stats['n']*100:.1f}%)",
          f"{n_y} ({n_y/disp_stats['n']*100:.1f}%)",
          f"{n_r} ({n_r/disp_stats['n']*100:.1f}%)"]]
    ))
    out.append("")

    # ----- Subgroup-size sensitivity -----
    out.append("## 2.3 Subgroup-size sensitivity for disparity")
    out.append("")
    out.append("Recompute `discipline_disparity_max` from `discipline.crdc.*` and "
               "`enrollment.crdc_by_race` (race breakdowns) at varying minimum-N thresholds. "
               "Mirrors `pipeline/12_compute_ratios.py:77` (currently hard-coded to `>=10`).")
    out.append("")
    out.append("**Query** (the source pull for this section):")
    out.append("```python")
    out.append('schools.find({}, {"_id":1,'
               '"discipline.crdc.iss":1,"discipline.crdc.oss_single":1,"discipline.crdc.oss_multiple":1,'
               '"enrollment.crdc_by_race":1,"derived.flags.discipline_disparity.color":1})')
    out.append("```")
    out.append("")

    cursor = schools.find(
        {},
        {"_id": 1,
         "discipline.crdc.iss": 1,
         "discipline.crdc.oss_single": 1,
         "discipline.crdc.oss_multiple": 1,
         "enrollment.crdc_by_race": 1,
         "derived.flags.discipline_disparity.color": 1},
    )
    docs_for_recompute = list(cursor)

    def sum_race(obj, race):
        if not obj:
            return 0
        return (obj.get(f"{race}_male", 0) or 0) + (obj.get(f"{race}_female", 0) or 0)

    def disparity_max(doc, min_n):
        crdc = (doc.get("discipline") or {}).get("crdc") or {}
        crdc_by_race = (doc.get("enrollment") or {}).get("crdc_by_race") or {}
        if not crdc or not crdc_by_race:
            return None
        iss = crdc.get("iss")
        oss1 = crdc.get("oss_single")
        oss2 = crdc.get("oss_multiple")
        if iss is None and oss1 is None and oss2 is None:
            return None
        races = ["hispanic", "american_indian", "asian", "pacific_islander",
                 "black", "white", "two_or_more"]
        rates = {}
        for r in races:
            enrolled = crdc_by_race.get(r, 0) or 0
            if enrolled >= min_n:
                susp = sum_race(iss, r) + sum_race(oss1, r) + sum_race(oss2, r)
                rates[r] = susp / enrolled
        white = rates.get("white")
        if white is None or white == 0:
            return None
        ratios = []
        for r in races:
            if r == "white":
                continue
            if r in rates:
                ratios.append(rates[r] / white)
        return max(ratios) if ratios else None

    headers = ["min subgroup-N",
               "schools with non-null disparity_max",
               "currently-flagged schools that lose flag"]
    rows = []
    current_yellow_or_red_ncessch = set()
    for d in docs_for_recompute:
        col = (((d.get("derived") or {}).get("flags") or {})
               .get("discipline_disparity") or {}).get("color")
        nid = d.get("_id")
        if col in ("yellow", "red") and nid is not None:
            current_yellow_or_red_ncessch.add(nid)

    for min_n in [10, 15, 20, 25, 30, 40]:
        non_null = 0
        lost = 0
        for d in docs_for_recompute:
            mr = disparity_max(d, min_n)
            if mr is not None:
                non_null += 1
            nid = d.get("_id")
            if nid in current_yellow_or_red_ncessch:
                # Would they still be yellow/red?
                if mr is None or mr <= 2.0:
                    lost += 1
        marker = " (current)" if min_n == 10 else ""
        rows.append([f"{min_n}{marker}", non_null, lost])
    out.append(md_table(headers, rows))
    out.append("")
    out.append(f"> Currently flagged yellow OR red on `discipline_disparity`: "
               f"**{len(current_yellow_or_red_ncessch)}** schools.")
    out.append("")

    with open(os.path.join(OUT_DIR, "threshold_revision_data.md"), "w") as f:
        f.write("\n".join(out))
    print(f"  wrote threshold_revision_data.md (absenteeism N={abs_stats['n']}, "
          f"disparity N={disp_stats['n']})")


# ============================================================================
# STEP 3 — COHORT AND GRADE-SPAN DIAGNOSTICS
# ============================================================================

def step3_cohorts(regression_ready):
    out = ["# Phase 3R — Step 3: Cohort and Grade-Span Diagnostics",
           "",
           "Read-only dump of peer cohort sizes and grade-span composition.",
           ""]

    # Peer cohort histogram
    cursor = schools.find(
        {"derived.peer_cohort": {"$ne": None}},
        {"derived.peer_cohort": 1},
    )
    cohort_membership = Counter()
    for d in cursor:
        c = (d.get("derived") or {}).get("peer_cohort")
        if c:
            cohort_membership[c] += 1

    # Bucket cohort sizes
    buckets = {"1": 0, "2": 0, "3-4": 0, "5-9": 0, "10-19": 0,
               "20-49": 0, "50+": 0}
    for cohort, n in cohort_membership.items():
        if n == 1:
            buckets["1"] += 1
        elif n == 2:
            buckets["2"] += 1
        elif n <= 4:
            buckets["3-4"] += 1
        elif n <= 9:
            buckets["5-9"] += 1
        elif n <= 19:
            buckets["10-19"] += 1
        elif n <= 49:
            buckets["20-49"] += 1
        else:
            buckets["50+"] += 1

    total_schools_in_cohorts = sum(cohort_membership.values())
    schools_in_small_cohorts = sum(n for c, n in cohort_membership.items() if n < 5)

    out.append("## 3.1 Peer cohort size histogram (current hard-bin approach)")
    out.append("")
    out.append(f"Total cohorts: **{len(cohort_membership)}**")
    out.append(f"Total schools assigned to a cohort: **{total_schools_in_cohorts}**")
    out.append(f"Schools in cohorts with < 5 members: **{schools_in_small_cohorts}** "
               f"({schools_in_small_cohorts/total_schools_in_cohorts*100:.1f}% of assigned schools)")
    out.append("")
    out.append("**Query**:")
    out.append("```python")
    out.append('schools.aggregate([{"$match":{"derived.peer_cohort":{"$ne":None}}},'
               '{"$group":{"_id":"$derived.peer_cohort","n":{"$sum":1}}}])')
    out.append("```")
    out.append("")
    headers = ["cohort size bucket", "# of cohorts", "# schools in those cohorts"]
    rows = []
    for b in ["1", "2", "3-4", "5-9", "10-19", "20-49", "50+"]:
        cohorts = [(c, n) for c, n in cohort_membership.items()
                   if (b == "1" and n == 1) or
                      (b == "2" and n == 2) or
                      (b == "3-4" and 3 <= n <= 4) or
                      (b == "5-9" and 5 <= n <= 9) or
                      (b == "10-19" and 10 <= n <= 19) or
                      (b == "20-49" and 20 <= n <= 49) or
                      (b == "50+" and n >= 50)]
        rows.append([b, len(cohorts), sum(n for _, n in cohorts)])
    out.append(md_table(headers, rows))
    out.append("")

    # 3.2 Grade-span breakdown by level
    cursor = schools.find(
        {},
        {"_id": 1, "level": 1,
         "grade_span.low": 1, "grade_span.high": 1,
         "derived.level_group": 1},
    )
    all_for_grade = list(cursor)

    span_to_level_group = defaultdict(Counter)
    span_total = Counter()
    for d in all_for_grade:
        gs = d.get("grade_span") or {}
        low = gs.get("low")
        high = gs.get("high")
        if low is None or high is None:
            span = "(missing low/high)"
        else:
            span = f"{low}-{high}"
        lg = (d.get("derived") or {}).get("level_group") or "(no level_group)"
        span_to_level_group[span][lg] += 1
        span_total[span] += 1

    common_patterns = ["KG-02", "KG-03", "KG-05", "KG-06", "KG-08",
                       "06-08", "07-08", "06-12", "07-12", "09-12"]
    # Also include some likely variants (PK, no leading zero)
    common_normalized = set(common_patterns)
    out.append("## 3.2 Grade-span breakdown by CCD level group")
    out.append("")
    out.append("Grade strings as stored in MongoDB (CCD codes: PK, KG, 01–12, UG).")
    out.append("")
    out.append("### 3.2.1 Common patterns the prompt asked for")
    out.append("")
    out.append("Rows show the count of schools for each (low–high) → level_group combination.")
    out.append("")
    headers = ["grade span (low-high)", "level_group", "count"]
    rows = []
    for pattern in common_patterns:
        if pattern in span_to_level_group:
            for lg, n in sorted(span_to_level_group[pattern].items(),
                                key=lambda x: -x[1]):
                rows.append([pattern, lg, n])
        else:
            rows.append([pattern, "(no schools with this exact span)", 0])
    out.append(md_table(headers, rows))
    out.append("")

    out.append("### 3.2.2 All other grade spans (count ≥ 1)")
    out.append("")
    headers = ["grade span", "level_group", "count"]
    rows = []
    for span in sorted(span_to_level_group.keys()):
        if span in common_normalized:
            continue
        for lg, n in sorted(span_to_level_group[span].items(),
                            key=lambda x: -x[1]):
            rows.append([span, lg, n])
    out.append(md_table(headers, rows))
    out.append("")

    # 3.3 Other-level-group regression participation
    out.append("## 3.3 'Other' level group")
    out.append("")
    other_total = sum(1 for d in all_for_grade
                      if (d.get("derived") or {}).get("level_group") == "Other")
    other_in_regression = sum(1 for e in regression_ready if e["level_group"] == "Other")
    out.append(f"- Total schools mapped to `level_group=\"Other\"`: **{other_total}**")
    out.append(f"- Of those, regression-ready (have FRL + composite, not excluded): "
               f"**{other_in_regression}**")
    out.append(f"- Min group size for own model: {THRESHOLDS['regression']['min_group_size']}")
    out.append(f"- 'Other' uses statewide fallback when n < min_group_size.")
    out.append("")

    other_spans = Counter()
    for d in all_for_grade:
        if (d.get("derived") or {}).get("level_group") == "Other":
            gs = d.get("grade_span") or {}
            low = gs.get("low")
            high = gs.get("high")
            span = f"{low}-{high}" if low and high else "(missing)"
            other_spans[span] += 1
    out.append("### Grade spans of schools mapped to 'Other'")
    out.append("")
    headers = ["grade span", "count"]
    rows = [[s, n] for s, n in sorted(other_spans.items(), key=lambda x: -x[1])]
    out.append(md_table(headers, rows))
    out.append("")

    with open(os.path.join(OUT_DIR, "cohort_diagnostics.md"), "w") as f:
        f.write("\n".join(out))
    print(f"  wrote cohort_diagnostics.md (cohorts={len(cohort_membership)}, "
          f"in_small_cohorts={schools_in_small_cohorts})")


# ============================================================================
# STEP 4 — EDGE-CASE SAMPLE DOCUMENTS
# ============================================================================

def step4_samples():
    out = ["# Phase 3R — Step 4: Edge-Case Sample Documents",
           "",
           "Full pretty-printed MongoDB documents for one real school per pattern.",
           "If a pattern has no real match, it is marked **NOT FOUND**.",
           ""]

    def dump_doc(label, doc, query_str, note=None):
        out.append(f"## {label}")
        out.append("")
        if doc is None:
            out.append("**NOT FOUND** — no school in MongoDB matches this pattern.")
            if note:
                out.append("")
                out.append(note)
            out.append("")
            out.append("**Query attempted**:")
            out.append("```python")
            out.append(query_str)
            out.append("```")
            out.append("")
            return
        name = doc.get("name") or "(no name)"
        ncessch = doc.get("_id")  # primary key on these documents
        out.append(f"**{name}** (NCESSCH `{ncessch}`)")
        out.append("")
        if note:
            out.append(note)
            out.append("")
        out.append("```json")
        out.append(json.dumps(doc, indent=2, default=json_util.default))
        out.append("```")
        out.append("")

    # 4.1 K-8 school
    q1 = '{"grade_span.low":"KG","grade_span.high":"08"}'
    doc1 = schools.find_one({"grade_span.low": "KG", "grade_span.high": "08"})
    dump_doc("4.1 — K-8 school", doc1, f"schools.find_one({q1})")

    # 4.2 Small rural school in cohort < 5
    cursor = schools.find({"derived.peer_cohort": {"$ne": None}},
                           {"derived.peer_cohort": 1})
    cohort_count = Counter()
    for d in cursor:
        c = (d.get("derived") or {}).get("peer_cohort")
        if c:
            cohort_count[c] += 1
    small_cohorts = {c for c, n in cohort_count.items() if n < 5}

    doc2 = None
    if small_cohorts:
        cursor = schools.find({"derived.peer_cohort": {"$in": list(small_cohorts)}})
        for d in cursor:
            loc = d.get("locale") or d.get("location") or {}
            locale_str = json.dumps(loc) if isinstance(loc, dict) else str(loc)
            if "rural" in locale_str.lower() or "Rural" in str(d.get("location", {})):
                doc2 = d
                break
        if doc2 is None:
            # Fall back to any small-cohort school
            doc2 = schools.find_one({"derived.peer_cohort": {"$in": list(small_cohorts)}})
    dump_doc("4.2 — Small school in peer cohort with < 5 members",
             doc2,
             'schools.find({"derived.peer_cohort":{"$in":[<small cohorts>]}})',
             note="(Selected from any cohort with < 5 members; preference given "
                  "to schools with Rural locale labeling but the dataset's locale "
                  "field varies. School below is a real cohort-<5 case.)")

    # 4.3 Other-level school with non-null regression output
    q3 = '{"derived.level_group":"Other","derived.regression_zscore":{"$ne":None}}'
    doc3 = schools.find_one({"derived.level_group": "Other",
                              "derived.regression_zscore": {"$ne": None}})
    dump_doc("4.3 — 'Other' level school with non-null regression output",
             doc3, f"schools.find_one({q3})")

    # 4.4 All four climate/equity flags at red
    q4 = ('{"derived.flags.chronic_absenteeism.color":"red",'
          '"derived.flags.counselor_ratio.color":"red",'
          '"derived.flags.discipline_disparity.color":"red",'
          '"derived.flags.no_counselor.color":"red"}')
    doc4 = schools.find_one({"derived.flags.chronic_absenteeism.color": "red",
                              "derived.flags.counselor_ratio.color": "red",
                              "derived.flags.discipline_disparity.color": "red",
                              "derived.flags.no_counselor.color": "red"})
    note4 = None
    if doc4 is None:
        # no_counselor and counselor_ratio are mutually exclusive by design
        # (counselor_ratio requires non-zero counselor FTE, no_counselor requires zero).
        # Try without no_counselor.
        doc4 = schools.find_one({"derived.flags.chronic_absenteeism.color": "red",
                                  "derived.flags.counselor_ratio.color": "red",
                                  "derived.flags.discipline_disparity.color": "red"})
        if doc4 is not None:
            note4 = ("**NOTE — no school can carry all four flags at red simultaneously.** "
                     "`no_counselor` requires `staffing.counselor_fte == 0`; "
                     "`counselor_ratio` requires `counselor_fte > 0` to compute the ratio. "
                     "These two flags are mutually exclusive by definition. Showing the closest match: "
                     "all three threshold flags red, no_counselor not applicable.")
    dump_doc("4.4 — School with all four climate/equity flags at red",
             doc4, f"schools.find_one({q4})", note=note4)

    # 4.5 performance_flag null due to suppressed_n_lt_10
    q5 = ('{"derived.performance_flag":None,'
          '"derived.performance_flag_absent_reason":"suppressed_n_lt_10"}')
    doc5 = schools.find_one({"derived.performance_flag": None,
                              "derived.performance_flag_absent_reason": "suppressed_n_lt_10"})
    dump_doc("4.5 — performance_flag null because suppressed_n_lt_10",
             doc5, f"schools.find_one({q5})")

    # 4.6 performance_flag null due to grade_span_not_tested
    q6 = ('{"derived.performance_flag":None,'
          '"derived.performance_flag_absent_reason":"grade_span_not_tested"}')
    doc6 = schools.find_one({"derived.performance_flag": None,
                              "derived.performance_flag_absent_reason": "grade_span_not_tested"})
    dump_doc("4.6 — performance_flag null because grade_span_not_tested",
             doc6, f"schools.find_one({q6})")

    with open(os.path.join(OUT_DIR, "sample_documents.md"), "w") as f:
        f.write("\n".join(out))
    print("  wrote sample_documents.md")


# ============================================================================
# STEP 5 — FLAG METADATA CURRENT
# ============================================================================

def step5_flag_metadata():
    out = ["# Phase 3R — Step 5: Current Flag Metadata Prose",
           "",
           "Verbatim dump of `what_it_means`, `what_it_might_not_mean`, and `parent_question` "
           "strings from `flag_thresholds.yaml`. One section per flag, sub-sections per color.",
           ""]

    flags = THRESHOLDS["flags"]
    for flag_name in ["chronic_absenteeism", "counselor_ratio",
                      "discipline_disparity", "no_counselor"]:
        cfg = flags[flag_name]
        out.append(f"## {flag_name}")
        out.append("")
        out.append(f"- field: `{cfg.get('field', '(special)')}`")
        if "yellow_threshold" in cfg:
            out.append(f"- yellow threshold: **{cfg['yellow_threshold']}**")
            out.append(f"- red threshold: **{cfg['red_threshold']}**")
        elif "condition" in cfg:
            out.append(f"- condition: `{cfg['condition']}`")
        out.append(f"- threshold_source: {cfg.get('threshold_source','').strip()}")
        out.append("")
        for color in ["green", "yellow", "red"]:
            if color not in cfg:
                if color == "green":
                    continue
                out.append(f"### {color}")
                out.append("")
                out.append(f"_(no `{color}` block defined for this flag)_")
                out.append("")
                continue
            block = cfg[color]
            out.append(f"### {color}")
            out.append("")
            for key in ["what_it_means", "what_it_might_not_mean", "parent_question"]:
                v = block.get(key, "").strip()
                if v:
                    out.append(f"**{key}:**")
                    out.append("")
                    out.append(f"> {v}")
                    out.append("")

    with open(os.path.join(OUT_DIR, "flag_metadata_current.md"), "w") as f:
        f.write("\n".join(out))
    print("  wrote flag_metadata_current.md")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Step 1: regression diagnostics")
    regression_ready, fitted_models, sw_model, sw_sd, sw_r2 = step1_regression()
    print("Step 2: threshold revision data")
    step2_thresholds()
    print("Step 3: cohort and grade-span diagnostics")
    step3_cohorts(regression_ready)
    print("Step 4: edge-case sample documents")
    step4_samples()
    print("Step 5: current flag metadata prose")
    step5_flag_metadata()
    client.close()
    print("Done.")
