"""
14_compute_percentiles.py — Calculate percentile ranks for 8 curated metrics.

PURPOSE: For each school, compute percentile ranks (0-100) within three scopes:
         state (all WA schools), district, and peer cohort.
INPUTS:  data/schools_pipeline.json, flag_thresholds.yaml
OUTPUTS: Adds derived.percentiles section to each school.

PERCENTILE FORMULA: pct = (count_below + 0.5 * count_equal) / total * 100
  For "lower is better" metrics (like discipline rate), the result is flipped
  so that a school with a low discipline rate gets a HIGH percentile.

SCOPE RULES:
  - State: all WA schools with a non-null value for that metric
  - District: within the same district.nces_id, only if 2+ schools have data
  - Peer: within the same derived.peer_cohort, only if 5+ schools have data
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    load_flag_thresholds, get_nested, FAIRHAVEN_NCESSCH
)


def compute_percentile_rank(value, all_values, lower_is_better):
    """Compute the percentile rank of a value within a list of values.

    Uses the formula: (count_below + 0.5 * count_equal) / total * 100.
    For "lower is better" metrics, flips the result: 100 - pct.
    Returns an integer 0-100.
    """
    total = len(all_values)
    if total == 0:
        return None

    count_below = sum(1 for v in all_values if v < value)
    count_equal = sum(1 for v in all_values if v == value)

    pct = (count_below + 0.5 * count_equal) / total * 100

    if lower_is_better:
        pct = 100 - pct

    return round(pct)


def main():
    logger = setup_logging("14_compute_percentiles")
    logger.info("Computing percentile ranks for 8 metrics across 3 scopes.")

    schools = load_schools()
    thresholds = load_flag_thresholds()

    metrics = thresholds["percentile_metrics"]
    min_district = thresholds["percentile_min_district"]
    min_peer = thresholds["percentile_min_peer"]

    logger.info(f"Loaded {len(schools)} schools.")
    logger.info(f"Metrics: {list(metrics.keys())}")
    logger.info(f"Min district size: {min_district}, min peer size: {min_peer}")

    # For each metric, collect values by scope (state, district, peer)
    for metric_key, metric_config in metrics.items():
        field_path = metric_config["field"]
        lower_is_better = metric_config["polarity"] == "lower_is_better"
        label = metric_config["label"]

        # Collect all non-null values grouped by scope
        state_values = []
        district_values = defaultdict(list)
        peer_values = defaultdict(list)

        # First pass: collect values
        for ncessch, doc in schools.items():
            val = get_nested(doc, field_path)
            if val is None:
                continue

            state_values.append((ncessch, val))

            district_id = doc.get("district", {}).get("nces_id")
            if district_id:
                district_values[district_id].append((ncessch, val))

            peer_cohort = doc.get("derived", {}).get("peer_cohort")
            if peer_cohort:
                peer_values[peer_cohort].append((ncessch, val))

        # Second pass: compute percentiles for each school
        # Pre-compute value lists for efficiency
        state_vals_only = [v for _, v in state_values]

        district_vals_by_id = {}
        for did, pairs in district_values.items():
            if len(pairs) >= min_district:
                district_vals_by_id[did] = [v for _, v in pairs]

        peer_vals_by_cohort = {}
        for cohort, pairs in peer_values.items():
            if len(pairs) >= min_peer:
                peer_vals_by_cohort[cohort] = [v for _, v in pairs]

        for ncessch, doc in schools.items():
            if "derived" not in doc:
                doc["derived"] = {}
            if "percentiles" not in doc["derived"]:
                doc["derived"]["percentiles"] = {}

            val = get_nested(doc, field_path)
            if val is None:
                doc["derived"]["percentiles"][metric_key] = {
                    "state": None, "district": None, "peer": None
                }
                continue

            # State percentile
            state_pct = compute_percentile_rank(val, state_vals_only, lower_is_better)

            # District percentile
            district_id = doc.get("district", {}).get("nces_id")
            if district_id and district_id in district_vals_by_id:
                district_pct = compute_percentile_rank(
                    val, district_vals_by_id[district_id], lower_is_better
                )
            else:
                district_pct = None

            # Peer percentile
            peer_cohort = doc.get("derived", {}).get("peer_cohort")
            if peer_cohort and peer_cohort in peer_vals_by_cohort:
                peer_pct = compute_percentile_rank(
                    val, peer_vals_by_cohort[peer_cohort], lower_is_better
                )
            else:
                peer_pct = None

            doc["derived"]["percentiles"][metric_key] = {
                "state": state_pct,
                "district": district_pct,
                "peer": peer_pct,
            }

        logger.info(
            f"{label}: {len(state_values)} schools with state percentile, "
            f"{len(district_vals_by_id)} qualifying districts, "
            f"{len(peer_vals_by_cohort)} qualifying peer cohorts."
        )

    # Fairhaven verification
    if FAIRHAVEN_NCESSCH in schools:
        fh_pct = schools[FAIRHAVEN_NCESSCH].get("derived", {}).get("percentiles", {})
        logger.info("Fairhaven percentiles:")
        for metric_key in metrics:
            p = fh_pct.get(metric_key, {})
            logger.info(
                f"  {metric_key}: state={p.get('state')}, "
                f"district={p.get('district')}, peer={p.get('peer')}"
            )

    # Sanity check: percentiles should be 0-100 with no out-of-range values
    out_of_range = 0
    for ncessch, doc in schools.items():
        pcts = doc.get("derived", {}).get("percentiles", {})
        for metric_key, scopes in pcts.items():
            for scope, val in scopes.items():
                if val is not None and (val < 0 or val > 100):
                    out_of_range += 1
                    logger.warning(
                        f"Out-of-range percentile: {ncessch} {metric_key} {scope}={val}"
                    )

    if out_of_range == 0:
        logger.info("PASS: All percentiles are in 0-100 range.")
    else:
        logger.error(f"FAIL: {out_of_range} percentile values out of 0-100 range.")

    save_schools(schools)
    logger.info("Step 14 complete. Percentile ranks computed.")


if __name__ == "__main__":
    main()
