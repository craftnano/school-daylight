"""
15_regression_and_flags.py — Performance regression + climate/equity flags.

PURPOSE: Part A — Run FRL-vs-proficiency regression per school level, compute
         residuals and z-scores, assign performance flags (outperforming,
         as_expected, underperforming).
         Part B — Apply climate/equity flag thresholds with structured metadata.
         Part C — Compute flag_absent_reason for every school missing a flag.

INPUTS:  data/schools_pipeline.json, flag_thresholds.yaml
OUTPUTS: Adds derived.performance_flag, derived.regression_*, derived.flags

REGRESSION APPROACH: Per-level (Elementary, Middle, High, Other) instead of
  single statewide. This is a documented deviation from the build sequence
  (see phases/phase-3/decision_log.md #1). Empirically validated: statewide
  gives Fairhaven z=0.89 (yellow), per-level gives z=1.33 (green).
"""

import os
import sys
from collections import defaultdict

import numpy as np
from sklearn.linear_model import LinearRegression

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    load_flag_thresholds, get_nested, FAIRHAVEN_NCESSCH
)


# ============================================================================
# GRADE SPAN HELPER — determines if a school's grades include tested grades
# ============================================================================

# Map grade strings from CCD to numeric values for range comparison.
# PK=-1, KG=0, 01-12=1-12, UG=13 (ungraded).
GRADE_TO_NUM = {
    "PK": -1, "KG": 0, "UG": 13,
    "01": 1, "02": 2, "03": 3, "04": 4, "05": 5, "06": 6,
    "07": 7, "08": 8, "09": 9, "10": 10, "11": 11, "12": 12,
}


def grade_span_includes_tested(doc, tested_grades_str):
    """Check if a school's grade span includes any tested grades.

    Returns True if the school serves at least one grade in tested_grades_str,
    False if it definitely doesn't, None if we can't determine (missing data).
    """
    grade_span = doc.get("grade_span", {})
    low = grade_span.get("low")
    high = grade_span.get("high")

    if not low or not high:
        return None

    low_num = GRADE_TO_NUM.get(str(low).strip().zfill(2))
    high_num = GRADE_TO_NUM.get(str(high).strip().zfill(2))

    if low_num is None or high_num is None:
        return None

    # Convert tested grade strings to numbers
    tested_nums = set()
    for g in tested_grades_str:
        num = GRADE_TO_NUM.get(g.strip().zfill(2))
        if num is not None:
            tested_nums.add(num)

    # Check if any tested grade falls within the school's range
    for t in tested_nums:
        if low_num <= t <= high_num:
            return True

    return False


# ============================================================================
# PART A: PERFORMANCE REGRESSION
# ============================================================================

def run_regression(schools, thresholds, logger):
    """Run FRL-vs-proficiency regression per school level group.

    Assigns performance_flag, regression_predicted, regression_residual,
    regression_zscore, regression_group, and regression_r_squared to each
    school that has the required data (FRL + ELA + Math proficiency).
    """
    threshold_sd = thresholds["regression"]["threshold_sd"]
    min_group_size = thresholds["regression"]["min_group_size"]

    logger.info(f"Regression threshold: ±{threshold_sd} SD. Min group size: {min_group_size}.")

    # Collect schools with non-null FRL + proficiency composite
    # (composite was computed in step 12)
    regression_ready = []
    for ncessch, doc in schools.items():
        frl = doc.get("demographics", {}).get("frl_pct")
        composite = doc.get("derived", {}).get("proficiency_composite")
        level_group = doc.get("derived", {}).get("level_group")

        if frl is not None and composite is not None and level_group is not None:
            regression_ready.append({
                "ncessch": ncessch,
                "frl": frl,
                "composite": composite,
                "level_group": level_group,
            })

    logger.info(f"{len(regression_ready)} schools are regression-ready (have FRL + composite + level).")

    # Group by level
    by_level = defaultdict(list)
    for entry in regression_ready:
        by_level[entry["level_group"]].append(entry)

    # Fit statewide model first (fallback for small groups)
    all_X = np.array([[e["frl"]] for e in regression_ready])
    all_y = np.array([e["composite"] for e in regression_ready])

    statewide_model = LinearRegression()
    statewide_model.fit(all_X, all_y)
    statewide_r2 = statewide_model.score(all_X, all_y)
    statewide_residuals = all_y - statewide_model.predict(all_X)
    statewide_sd = float(np.std(statewide_residuals))

    logger.info(f"Statewide regression: R²={statewide_r2:.3f}, SD={statewide_sd:.4f}, "
                f"slope={statewide_model.coef_[0]:.3f}, intercept={statewide_model.intercept_:.3f}")

    # Fit per-level models
    level_models = {}
    for level_group, entries in sorted(by_level.items()):
        n = len(entries)
        if n >= min_group_size:
            X = np.array([[e["frl"]] for e in entries])
            y = np.array([e["composite"] for e in entries])

            model = LinearRegression()
            model.fit(X, y)
            r2 = model.score(X, y)
            residuals = y - model.predict(X)
            sd = float(np.std(residuals))

            level_models[level_group] = {
                "model": model,
                "r2": r2,
                "sd": sd,
                "n": n,
            }

            logger.info(
                f"  {level_group}: n={n}, R²={r2:.3f}, SD={sd:.4f}, "
                f"slope={model.coef_[0]:.3f}, intercept={model.intercept_:.3f}"
            )
        else:
            logger.info(f"  {level_group}: n={n} (< {min_group_size}), using statewide fallback.")

    # Assign performance flags
    flag_counts = defaultdict(int)

    for entry in regression_ready:
        ncessch = entry["ncessch"]
        frl = entry["frl"]
        composite = entry["composite"]
        level_group = entry["level_group"]
        doc = schools[ncessch]

        # Use per-level model if available, otherwise statewide fallback
        if level_group in level_models:
            lm = level_models[level_group]
            model = lm["model"]
            sd = lm["sd"]
            r2 = lm["r2"]
            group_used = level_group
        else:
            model = statewide_model
            sd = statewide_sd
            r2 = statewide_r2
            group_used = "statewide"

        predicted = float(model.predict([[frl]])[0])
        residual = composite - predicted
        zscore = residual / sd if sd > 0 else 0.0

        # Flag assignment
        if zscore > threshold_sd:
            flag = "outperforming"
        elif zscore < -threshold_sd:
            flag = "underperforming"
        else:
            flag = "as_expected"

        flag_counts[flag] += 1

        doc["derived"]["performance_flag"] = flag
        doc["derived"]["regression_predicted"] = round(predicted, 4)
        doc["derived"]["regression_residual"] = round(residual, 4)
        doc["derived"]["regression_zscore"] = round(zscore, 2)
        doc["derived"]["regression_group"] = group_used
        doc["derived"]["regression_r_squared"] = round(r2, 3)

    # Schools without regression data get null
    for ncessch, doc in schools.items():
        if "performance_flag" not in doc.get("derived", {}):
            if "derived" not in doc:
                doc["derived"] = {}
            doc["derived"]["performance_flag"] = None
            doc["derived"]["regression_predicted"] = None
            doc["derived"]["regression_residual"] = None
            doc["derived"]["regression_zscore"] = None
            doc["derived"]["regression_group"] = None
            doc["derived"]["regression_r_squared"] = None

    total_flagged = sum(flag_counts.values())
    for flag_name in ["outperforming", "as_expected", "underperforming"]:
        count = flag_counts[flag_name]
        pct = count / total_flagged * 100 if total_flagged > 0 else 0
        logger.info(f"  {flag_name}: {count} schools ({pct:.1f}%)")

    # Per-level flag distribution
    for level_group in sorted(by_level.keys()):
        level_flags = defaultdict(int)
        for entry in by_level[level_group]:
            flag = schools[entry["ncessch"]]["derived"]["performance_flag"]
            level_flags[flag] += 1
        n = len(by_level[level_group])
        logger.info(
            f"  {level_group}: "
            + ", ".join(f"{f}={c} ({c/n*100:.1f}%)" for f, c in sorted(level_flags.items()))
        )


# ============================================================================
# PART B: CLIMATE & EQUITY FLAGS
# ============================================================================

def apply_flags(schools, thresholds, logger):
    """Apply climate and equity flag thresholds with structured metadata."""
    flag_configs = thresholds["flags"]

    for flag_name, flag_config in flag_configs.items():
        if flag_name == "no_counselor":
            # Special case: binary flag (zero counselors), not threshold-based
            apply_no_counselor_flag(schools, flag_config, logger)
            continue

        field = flag_config["field"]
        yellow_threshold = flag_config["yellow_threshold"]
        red_threshold = flag_config["red_threshold"]
        threshold_source = flag_config["threshold_source"]

        green_count = 0
        yellow_count = 0
        red_count = 0
        null_count = 0

        for ncessch, doc in schools.items():
            if "derived" not in doc:
                doc["derived"] = {}
            if "flags" not in doc["derived"]:
                doc["derived"]["flags"] = {}

            val = get_nested(doc, field)

            if val is None:
                # Flag will be set to null — reason assigned in Part C
                doc["derived"]["flags"][flag_name] = {"color": None}
                null_count += 1
                continue

            # Determine color
            if val > red_threshold:
                color = "red"
                metadata_text = flag_config["red"]
                threshold_used = red_threshold
                red_count += 1
            elif val > yellow_threshold:
                color = "yellow"
                metadata_text = flag_config["yellow"]
                threshold_used = yellow_threshold
                yellow_count += 1
            else:
                color = "green"
                green_count += 1
                doc["derived"]["flags"][flag_name] = {
                    "color": "green",
                    "raw_value": round(val, 4) if isinstance(val, float) else val,
                }
                continue

            # Store flag with full metadata
            doc["derived"]["flags"][flag_name] = {
                "color": color,
                "raw_value": round(val, 4) if isinstance(val, float) else val,
                "threshold": threshold_used,
                "threshold_source": threshold_source,
                "what_it_means": metadata_text["what_it_means"],
                "what_it_might_not_mean": metadata_text["what_it_might_not_mean"],
                "parent_question": metadata_text["parent_question"],
            }

        logger.info(
            f"Flag '{flag_name}': green={green_count}, yellow={yellow_count}, "
            f"red={red_count}, null={null_count}"
        )


def apply_no_counselor_flag(schools, flag_config, logger):
    """Apply the no-counselor flag — a binary flag for zero counselor FTE."""
    threshold_source = flag_config["threshold_source"]
    metadata_text = flag_config["red"]
    count = 0

    for ncessch, doc in schools.items():
        if "derived" not in doc:
            doc["derived"] = {}
        if "flags" not in doc["derived"]:
            doc["derived"]["flags"] = {}

        no_counselor = doc.get("derived", {}).get("no_counselor")

        if no_counselor is True:
            doc["derived"]["flags"]["no_counselor"] = {
                "color": "red",
                "raw_value": 0.0,
                "threshold_source": threshold_source,
                "what_it_means": metadata_text["what_it_means"],
                "what_it_might_not_mean": metadata_text["what_it_might_not_mean"],
                "parent_question": metadata_text["parent_question"],
            }
            count += 1

    logger.info(f"Flag 'no_counselor': {count} schools have zero counselor FTE.")


# ============================================================================
# PART C: FLAG ABSENT REASONS
# ============================================================================

def assign_flag_absent_reasons(schools, thresholds, logger):
    """For every school missing a flag, assign a high-confidence reason.

    Three categories only — no speculation:
    - grade_span_not_tested: school doesn't serve tested grades (3-8, 10)
    - suppressed_n_lt_10: the underlying metric was suppressed for privacy
    - data_not_available: everything else
    """
    tested_grades = thresholds["flag_absent_reasons"]["grade_span_not_tested"]["tested_grades"]

    # Which flags need absent reasons? All threshold-based flags + performance
    flag_to_field = {}
    for flag_name, flag_config in thresholds["flags"].items():
        if flag_name == "no_counselor":
            continue
        flag_to_field[flag_name] = flag_config["field"]

    reason_counts = defaultdict(lambda: defaultdict(int))

    for ncessch, doc in schools.items():
        derived = doc.get("derived", {})
        flags = derived.get("flags", {})

        # --- Performance flag absent reason ---
        if derived.get("performance_flag") is None:
            reason = determine_performance_absent_reason(doc, tested_grades)
            derived["performance_flag_absent_reason"] = reason
            reason_counts["performance"][reason] += 1

        # --- Climate/equity flag absent reasons ---
        for flag_name, field_path in flag_to_field.items():
            flag_data = flags.get(flag_name, {})
            if flag_data.get("color") is None:
                reason = determine_flag_absent_reason(doc, field_path, tested_grades)
                flag_data["flag_absent_reason"] = reason
                flags[flag_name] = flag_data
                reason_counts[flag_name][reason] += 1

        if flags:
            derived["flags"] = flags

    # Log reason distribution
    for flag_name, reasons in sorted(reason_counts.items()):
        total = sum(reasons.values())
        parts = [f"{reason}={count}" for reason, count in sorted(reasons.items())]
        logger.info(f"Flag absent reasons for '{flag_name}' ({total} total): {', '.join(parts)}")


def determine_performance_absent_reason(doc, tested_grades):
    """Determine why a school has no performance flag.

    Performance requires FRL + ELA + Math proficiency. Check grade span first,
    then suppression, then default to data_not_available.
    """
    # Check if grade span excludes tested grades
    has_tested = grade_span_includes_tested(doc, tested_grades)
    if has_tested is False:
        return "grade_span_not_tested"

    # Check if proficiency was suppressed (look for suppression markers)
    assessment = doc.get("academics", {}).get("assessment", {})
    if is_suppressed(assessment, "ela_proficiency_pct") or is_suppressed(assessment, "math_proficiency_pct"):
        return "suppressed_n_lt_10"

    return "data_not_available"


def determine_flag_absent_reason(doc, field_path, tested_grades):
    """Determine why a specific climate/equity flag is null.

    Checks grade span (for assessment-related flags), suppression markers,
    then defaults to data_not_available.
    """
    # Assessment-related fields: check grade span
    if "proficiency" in field_path or "attendance" in field_path or "absenteeism" in field_path:
        has_tested = grade_span_includes_tested(doc, tested_grades)
        if has_tested is False:
            return "grade_span_not_tested"

    # Check for suppression at the source field level
    # Walk the field path to find if the parent section has suppression markers
    parts = field_path.split(".")
    parent = doc
    for part in parts[:-1]:
        parent = parent.get(part, {}) if isinstance(parent, dict) else {}

    if isinstance(parent, dict):
        leaf = parts[-1]
        # Check for explicit suppression flag stored alongside the field
        suppressed_key = f"{leaf}_suppressed"
        if parent.get(suppressed_key):
            return "suppressed_n_lt_10"

    return "data_not_available"


def is_suppressed(section, field_name):
    """Check if a field in a section was marked as suppressed.

    OSPI data stores suppression flags as {field}_suppressed: true
    in the same section as the field.
    """
    if not isinstance(section, dict):
        return False
    return section.get(f"{field_name}_suppressed", False)


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger = setup_logging("15_regression_and_flags")
    logger.info("Running regression analysis and applying climate/equity flags.")

    schools = load_schools()
    thresholds = load_flag_thresholds()

    logger.info(f"Loaded {len(schools)} schools.")

    # Part A: Performance regression
    logger.info("--- Part A: Performance Regression ---")
    run_regression(schools, thresholds, logger)

    # Part B: Climate & equity flags
    logger.info("--- Part B: Climate & Equity Flags ---")
    apply_flags(schools, thresholds, logger)

    # Part C: Flag absent reasons
    logger.info("--- Part C: Flag Absent Reasons ---")
    assign_flag_absent_reasons(schools, thresholds, logger)

    # Fairhaven verification
    if FAIRHAVEN_NCESSCH in schools:
        fh = schools[FAIRHAVEN_NCESSCH]
        d = fh.get("derived", {})
        logger.info("--- Fairhaven Verification ---")
        logger.info(f"  performance_flag: {d.get('performance_flag')}")
        logger.info(f"  regression_zscore: {d.get('regression_zscore')}")
        logger.info(f"  regression_group: {d.get('regression_group')}")
        logger.info(f"  regression_r_squared: {d.get('regression_r_squared')}")

        flags = d.get("flags", {})
        for flag_name, flag_data in sorted(flags.items()):
            color = flag_data.get("color")
            reason = flag_data.get("flag_absent_reason")
            val = flag_data.get("raw_value")
            logger.info(f"  flag '{flag_name}': color={color}, raw_value={val}, absent_reason={reason}")

        # Gate check: Fairhaven MUST be outperforming
        if d.get("performance_flag") == "outperforming":
            logger.info("  PASS: Fairhaven is 'outperforming' (green).")
        else:
            logger.error(
                f"  FAIL: Fairhaven performance_flag is '{d.get('performance_flag')}', "
                "expected 'outperforming'. This is a gate check failure. "
                "Check the per-level regression model for Middle schools."
            )

    save_schools(schools)
    logger.info("Step 15 complete. Regression and flags applied.")


if __name__ == "__main__":
    main()
