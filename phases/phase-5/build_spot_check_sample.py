# PURPOSE: Build the stratified 25-school spot-check sample for builder review.
#          Selection rule (per Phase 5 handoff):
#            - 10 schools from districts with 18+ schools (well-enriched / Pass 2 priority)
#            - 10 schools from districts with 10-17 schools (Pass 2 expanded band)
#            -  5 schools from districts with <10 schools (district-level context only)
#          Constraints:
#            - All 25 schools must be OUTSIDE the 50-school validation set
#            - At least 3 schools must come from districts with known recent incidents
#              (any school in the district has district_context findings tagged
#              category=investigations_ocr OR sensitivity=high)
#            - Each chosen school must have layer3_narrative.status == "ok"
#              (we want a real narrative for the builder to review, not a
#              "No significant web-sourced context..." fallback)
#          Sampling within strata is deterministic via random.seed for reproducibility.
#
# INPUTS:
#   - phases/phase-5/production_run/spot_check_prep.json (district sizes, val set)
#   - MongoDB schools collection — must have layer3_narrative populated (Phase B done)
# OUTPUTS:
#   - phases/phase-5/spot_check_sample.md
#
# RUN: python3 phases/phase-5/build_spot_check_sample.py

import os
import sys
import json
import random
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
from pymongo import MongoClient

PREP_PATH = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run",
                        "spot_check_prep.json")
OUT_PATH = os.path.join(PROJECT_ROOT, "phases", "phase-5", "spot_check_sample.md")

random.seed(20260430)


def has_recent_incident(doc):
    """True if the school's district_context has any high-sensitivity or
    investigations_ocr finding."""
    findings = (doc.get("district_context") or {}).get("findings") or []
    for f in findings:
        if f.get("sensitivity") == "high":
            return True
        if f.get("category") == "investigations_ocr":
            return True
    return False


def main():
    with open(PREP_PATH) as f:
        prep = json.load(f)
    val_set = set(prep["validation_set_nces_ids"])
    district_sizes = prep["district_sizes"]
    big = set(prep["big_districts"])
    mid = set(prep["mid_districts"])
    small = set(prep["small_districts"])
    val_districts = set(prep["validation_set_districts"])
    print(f"Loaded prep: {len(val_set)} val schools, "
          f"big={len(big)} mid={len(mid)} small={len(small)} districts")

    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client.get_default_database()

    # Pull all candidates: schools NOT in val set with layer3_narrative.status=ok.
    candidates = list(db.schools.find(
        {
            "_id": {"$nin": list(val_set)},
            "layer3_narrative.status": "ok",
        },
        {
            "_id": 1, "name": 1, "district.name": 1,
            "layer3_narrative": 1, "district_context": 1,
        },
    ))
    print(f"Eligible candidates (status=ok, not in val set): {len(candidates)}")

    # Bucket by district size
    bucket_big, bucket_mid, bucket_small = [], [], []
    for d in candidates:
        dname = (d.get("district") or {}).get("name", "")
        if dname in big:
            bucket_big.append(d)
        elif dname in mid:
            bucket_mid.append(d)
        elif dname in small:
            bucket_small.append(d)
    print(f"Bucketed: big={len(bucket_big)} mid={len(bucket_mid)} small={len(bucket_small)}")

    # Recent-incident pool
    incident_candidates = [d for d in candidates if has_recent_incident(d)]
    print(f"Schools in districts with recent incidents (high-sens or investigations_ocr): "
          f"{len(incident_candidates)}")

    # Select 3+ from incident pool first to satisfy the constraint, distributing
    # across strata where possible.
    incident_picks = []
    incident_pool_by_bucket = {"big": [], "mid": [], "small": []}
    for d in incident_candidates:
        dname = (d.get("district") or {}).get("name", "")
        if dname in big:
            incident_pool_by_bucket["big"].append(d)
        elif dname in mid:
            incident_pool_by_bucket["mid"].append(d)
        elif dname in small:
            incident_pool_by_bucket["small"].append(d)

    # Take 1 from each stratum where available, then fill to 3 total
    for stratum in ("big", "mid", "small"):
        pool = incident_pool_by_bucket[stratum]
        if pool:
            incident_picks.append(random.choice(pool))
    while len(incident_picks) < 3 and incident_candidates:
        # Pick any incident school not already chosen
        chosen_ids = {x["_id"] for x in incident_picks}
        remaining = [d for d in incident_candidates if d["_id"] not in chosen_ids]
        if not remaining:
            break
        incident_picks.append(random.choice(remaining))

    print(f"Reserved {len(incident_picks)} incident-district picks (across strata).")

    # Now fill each bucket to its target, accounting for incident picks already in it
    targets = {"big": 10, "mid": 10, "small": 5}
    chosen = list(incident_picks)
    chosen_ids = {x["_id"] for x in chosen}

    def stratum_of(school):
        dname = (school.get("district") or {}).get("name", "")
        if dname in big: return "big"
        if dname in mid: return "mid"
        if dname in small: return "small"
        return None

    for stratum, target in targets.items():
        pool = {"big": bucket_big, "mid": bucket_mid, "small": bucket_small}[stratum]
        already = sum(1 for x in chosen if stratum_of(x) == stratum)
        need = target - already
        avail = [d for d in pool if d["_id"] not in chosen_ids]
        random.shuffle(avail)
        for d in avail[:need]:
            chosen.append(d)
            chosen_ids.add(d["_id"])

    print(f"Final selection: {len(chosen)} schools")
    # Sanity: should be exactly 25
    counts = {"big": 0, "mid": 0, "small": 0}
    for d in chosen:
        s = stratum_of(d)
        if s:
            counts[s] += 1
    print(f"Counts: {counts}")

    # Write the markdown report
    lines = []
    lines.append("# Phase 5 Layer 3 — Stratified Spot-Check Sample (25 schools)")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("**Selection design:**")
    lines.append("")
    lines.append("- 10 schools from districts with 18+ schools (well-enriched, Pass 2 priority).")
    lines.append("- 10 schools from districts with 10-17 schools (Pass 2 expanded band).")
    lines.append("-  5 schools from districts with fewer than 10 schools (district-level context only).")
    lines.append("- All 25 schools are OUTSIDE the 50-school Phase 4.5 validation set.")
    lines.append("- At least 3 schools come from districts with known recent incidents")
    lines.append("  (district_context contains a sensitivity=high or category=investigations_ocr finding).")
    lines.append("- Each school has layer3_narrative.status == \"ok\" (real narrative, not the")
    lines.append("  \"No significant web-sourced context...\" fallback).")
    lines.append("- Sampling is reproducible: random.seed(20260430).")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sort: big first, then mid, then small; within each, by district then name
    def sortkey(d):
        s = stratum_of(d) or "z"
        return (
            {"big": 0, "mid": 1, "small": 2}[s],
            (d.get("district") or {}).get("name", ""),
            d.get("name", ""),
        )
    chosen.sort(key=sortkey)

    incident_ids = {x["_id"] for x in incident_picks}

    for d in chosen:
        nid = d["_id"]
        name = d.get("name", "?")
        dname = (d.get("district") or {}).get("name", "?")
        stratum = stratum_of(d)
        size = district_sizes.get(dname, 0)
        narrative = (d.get("layer3_narrative") or {}).get("text", "")
        s1_inc = (d.get("layer3_narrative") or {}).get("stage1_included_count", 0)
        incident_note = " | districts-with-recent-incidents pick" if nid in incident_ids else ""
        stratum_label = {
            "big": "Stratum: big district (18+ schools)",
            "mid": "Stratum: mid district (10-17 schools)",
            "small": "Stratum: small district (<10 schools)",
        }[stratum]
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"**NCES:** `{nid}` &middot; **District:** {dname} ({size} schools){incident_note}")
        lines.append("")
        lines.append(f"_{stratum_label} &middot; Stage 1 included findings: {s1_inc}_")
        lines.append("")
        for para in (narrative or "").split("\n\n"):
            p = para.strip()
            if p:
                lines.append(p)
                lines.append("")
        lines.append("---")
        lines.append("")

    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote: {OUT_PATH}")
    print(f"Stratum counts: {counts}, incident picks: {len(incident_picks)}")


if __name__ == "__main__":
    main()
