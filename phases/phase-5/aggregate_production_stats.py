# PURPOSE: After Phase B completes, produce the aggregate stats and sample narratives
#          needed for docs/receipts/phase-5/task3_layer3_production.md.
#
# INPUTS:  MongoDB schools.layer3_narrative,
#          phases/phase-5/production_run/checkpoint.jsonl,
#          phases/phase-5/production_run/stage1_results.jsonl,
#          phases/phase-5/production_run/stage2_batch_results.jsonl
# OUTPUTS: Prints stats; writes receipt-ready artifacts to
#          phases/phase-5/production_run/receipt_artifacts/.

import os
import sys
import json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
from pymongo import MongoClient

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
ART_DIR = os.path.join(RUN_DIR, "receipt_artifacts")
os.makedirs(ART_DIR, exist_ok=True)

# Pricing — Haiku 4.5 / Sonnet 4.6 verified against
# https://platform.claude.com/docs/en/about-claude/pricing on 2026-04-30.
HAIKU_IN_PER_M, HAIKU_OUT_PER_M = 1.00, 5.00
SONNET_IN_PER_M, SONNET_OUT_PER_M = 3.00, 15.00
BATCH_DISCOUNT = 0.5

# Receipt sample schools — the canonical set the handoff named.
RECEIPT_SAMPLES = [
    ("530033000043", "Bainbridge High School"),
    ("530042000104", "Fairhaven Middle School"),
    ("530042000113", "Sehome High School"),
    ("530042002693", "Squalicum High School"),
    ("530423000670", "Juanita High School"),
    ("530039000082", "Phantom Lake Elementary"),
]


def main():
    # --- Status distribution from MongoDB ---
    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client.get_default_database()
    all_docs = list(db.schools.find({}, {"_id": 1, "layer3_narrative": 1}))
    status_counts = Counter()
    n_with_narrative = 0
    n_without_narrative = 0
    for d in all_docs:
        n = d.get("layer3_narrative")
        if not n:
            n_without_narrative += 1
            continue
        n_with_narrative += 1
        status_counts[n.get("status", "unknown")] += 1
    total_schools = len(all_docs)
    print(f"Total schools in DB: {total_schools}")
    print(f"  With layer3_narrative: {n_with_narrative}")
    print(f"  Without: {n_without_narrative}")
    print(f"Status distribution:")
    for s, c in status_counts.most_common():
        print(f"  {s}: {c}")

    # --- Cost from checkpoint + batch results ---
    haiku_in, haiku_out = 0, 0
    cp_path = os.path.join(RUN_DIR, "checkpoint.jsonl")
    if os.path.exists(cp_path):
        with open(cp_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    haiku_in += rec.get("haiku_in", 0) or 0
                    haiku_out += rec.get("haiku_out", 0) or 0
                except json.JSONDecodeError:
                    pass

    sonnet_in, sonnet_out = 0, 0
    n_s2_succeeded = 0
    n_s2_errored = 0
    br_path = os.path.join(RUN_DIR, "stage2_batch_results.jsonl")
    if os.path.exists(br_path):
        with open(br_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("type") == "succeeded":
                        n_s2_succeeded += 1
                        sonnet_in += rec.get("input_tokens", 0) or 0
                        sonnet_out += rec.get("output_tokens", 0) or 0
                    else:
                        n_s2_errored += 1
                except json.JSONDecodeError:
                    pass

    haiku_cost = haiku_in / 1e6 * HAIKU_IN_PER_M + haiku_out / 1e6 * HAIKU_OUT_PER_M
    sonnet_cost = (sonnet_in / 1e6 * SONNET_IN_PER_M +
                   sonnet_out / 1e6 * SONNET_OUT_PER_M) * BATCH_DISCOUNT
    total_cost = haiku_cost + sonnet_cost
    print()
    print(f"Haiku tokens: {haiku_in:,} in / {haiku_out:,} out → ${haiku_cost:.4f}")
    print(f"Sonnet (batch): {sonnet_in:,} in / {sonnet_out:,} out → ${sonnet_cost:.4f}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Stage 2 succeeded: {n_s2_succeeded}")
    print(f"Stage 2 errored: {n_s2_errored}")

    # --- Errors from MongoDB ---
    error_docs = list(db.schools.find(
        {"layer3_narrative.error": {"$ne": None, "$exists": True}},
        {"_id": 1, "name": 1, "layer3_narrative.status": 1, "layer3_narrative.error": 1}
    ))
    print(f"\nSchools with layer3_narrative.error set: {len(error_docs)}")
    for d in error_docs[:20]:
        n = d.get("layer3_narrative", {})
        print(f"  {d['_id']} | {d['name'][:40]:40s} | {n.get('status')} | {n.get('error')[:80] if n.get('error') else ''}")

    # --- Receipt sample narratives ---
    samples_out = []
    for nid, name in RECEIPT_SAMPLES:
        d = db.schools.find_one({"_id": nid}, {"name": 1, "district.name": 1, "layer3_narrative": 1})
        if not d:
            samples_out.append({"nces_id": nid, "name": name, "error": "not in DB"})
            continue
        n = d.get("layer3_narrative") or {}
        samples_out.append({
            "nces_id": nid,
            "name": d.get("name", name),
            "district": (d.get("district") or {}).get("name"),
            "status": n.get("status"),
            "model": n.get("model"),
            "stage1_included_count": n.get("stage1_included_count"),
            "narrative": n.get("text", ""),
        })

    # Save artifacts
    stats_path = os.path.join(ART_DIR, "stats.json")
    with open(stats_path, "w") as f:
        json.dump({
            "total_schools": total_schools,
            "n_with_narrative": n_with_narrative,
            "n_without_narrative": n_without_narrative,
            "status_counts": dict(status_counts),
            "haiku_in": haiku_in, "haiku_out": haiku_out, "haiku_cost": haiku_cost,
            "sonnet_in": sonnet_in, "sonnet_out": sonnet_out, "sonnet_cost": sonnet_cost,
            "total_cost": total_cost,
            "n_s2_succeeded": n_s2_succeeded, "n_s2_errored": n_s2_errored,
            "errors": [{"nces_id": d["_id"], "name": d.get("name"),
                        "status": (d.get("layer3_narrative") or {}).get("status"),
                        "error": (d.get("layer3_narrative") or {}).get("error")}
                       for d in error_docs],
        }, f, indent=2, default=str)
    samples_path = os.path.join(ART_DIR, "receipt_samples.json")
    with open(samples_path, "w") as f:
        json.dump(samples_out, f, indent=2, default=str)
    print(f"\nSaved: {stats_path}, {samples_path}")


if __name__ == "__main__":
    main()
