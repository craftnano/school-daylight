"""
13_assign_peer_groups.py — Assign peer cohorts for meaningful comparisons.

PURPOSE: Each school gets assigned to a peer cohort based on three dimensions:
         school level, enrollment size, and FRL percentage. This creates groups
         of roughly similar schools for percentile comparisons in step 14.
INPUTS:  data/schools_pipeline.json, flag_thresholds.yaml
OUTPUTS: Adds derived.peer_cohort, derived.frl_band, derived.enrollment_band,
         derived.level_group to each school.

PEER COHORT STRING FORMAT: "{level_group}_{enrollment_band}_{frl_band}"
  Example: "Middle_Large_MidFRL"

NULL PEER COHORT when: missing FRL or enrollment = 0 or null.
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools,
    load_flag_thresholds, FAIRHAVEN_NCESSCH
)


def assign_band(value, bands):
    """Find which band a numeric value falls into.

    Returns the band name (e.g., "Small", "MidFRL") or None if no match.
    """
    for band in bands:
        if band["min"] <= value <= band["max"]:
            return band["name"]
    return None


def main():
    logger = setup_logging("13_assign_peer_groups")
    logger.info("Assigning peer groups based on level, enrollment, and FRL.")

    schools = load_schools()
    thresholds = load_flag_thresholds()

    enrollment_bands = thresholds["enrollment_bands"]
    frl_bands = thresholds["frl_bands"]
    level_groups = thresholds["level_groups"]

    logger.info(f"Loaded {len(schools)} schools.")
    logger.info(f"Enrollment bands: {[b['name'] for b in enrollment_bands]}")
    logger.info(f"FRL bands: {[b['name'] for b in frl_bands]}")
    logger.info(f"Level groups: {list(level_groups.keys())}")

    assigned = 0
    null_peer = 0
    cohort_counts = Counter()

    for ncessch, doc in schools.items():
        if "derived" not in doc:
            doc["derived"] = {}

        derived = doc["derived"]

        # Get the three dimensions
        level = doc.get("level", "")
        enrollment = doc.get("enrollment", {}).get("total")
        frl_pct = doc.get("demographics", {}).get("frl_pct")

        # Map level to level group
        level_group = level_groups.get(level)
        if level_group is None and level:
            # Try to handle unexpected level values gracefully
            logger.warning(
                f"Unknown school level '{level}' for {doc.get('name', ncessch)} ({ncessch}). "
                f"Mapping to 'Other'."
            )
            level_group = "Other"

        derived["level_group"] = level_group

        # Assign enrollment band
        if enrollment and enrollment > 0:
            derived["enrollment_band"] = assign_band(enrollment, enrollment_bands)
        else:
            derived["enrollment_band"] = None

        # Assign FRL band
        if frl_pct is not None:
            derived["frl_band"] = assign_band(frl_pct, frl_bands)
        else:
            derived["frl_band"] = None

        # Build peer cohort string — only if all three dimensions are present
        if derived["level_group"] and derived["enrollment_band"] and derived["frl_band"]:
            cohort = f"{derived['level_group']}_{derived['enrollment_band']}_{derived['frl_band']}"
            derived["peer_cohort"] = cohort
            cohort_counts[cohort] += 1
            assigned += 1
        else:
            derived["peer_cohort"] = None
            null_peer += 1

    logger.info(f"Peer cohorts assigned: {assigned} schools. {null_peer} have null peer cohort.")
    logger.info(f"Total unique cohorts: {len(cohort_counts)}")

    # Log cohort distribution (sorted by count descending)
    logger.info("Top 10 peer cohorts by size:")
    for cohort, count in cohort_counts.most_common(10):
        logger.info(f"  {cohort}: {count} schools")

    # Log smallest cohorts (potential concern for percentile computation)
    small_cohorts = [(c, n) for c, n in cohort_counts.items() if n < 5]
    if small_cohorts:
        logger.info(f"{len(small_cohorts)} cohorts have fewer than 5 schools "
                     "(peer percentiles will be null for these):")
        for cohort, count in sorted(small_cohorts, key=lambda x: x[1]):
            logger.info(f"  {cohort}: {count} schools")

    # Fairhaven verification
    if FAIRHAVEN_NCESSCH in schools:
        fh = schools[FAIRHAVEN_NCESSCH]["derived"]
        logger.info(f"Fairhaven level_group: {fh.get('level_group')}")
        logger.info(f"Fairhaven enrollment_band: {fh.get('enrollment_band')}")
        logger.info(f"Fairhaven frl_band: {fh.get('frl_band')}")
        logger.info(f"Fairhaven peer_cohort: {fh.get('peer_cohort')}")

        expected = "Middle_Large_MidFRL"
        actual = fh.get("peer_cohort")
        if actual == expected:
            logger.info(f"PASS: Fairhaven peer cohort is '{expected}'.")
        else:
            logger.error(
                f"FAIL: Fairhaven peer cohort is '{actual}', expected '{expected}'. "
                "Check FRL bands or enrollment bands in flag_thresholds.yaml."
            )

    save_schools(schools)
    logger.info("Step 13 complete. Peer groups assigned.")


if __name__ == "__main__":
    main()
