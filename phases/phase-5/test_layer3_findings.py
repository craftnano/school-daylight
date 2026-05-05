# PURPOSE: Exercise pipeline/layer3_findings.get_findings_for_stage0() against the
#          canonical Bellingham test cases and save a diagnostic report. This is
#          the verification that Task 2 wires district_context correctly for Stage 0.
#
# INPUTS: live MongoDB Atlas connection.
# OUTPUTS: phases/phase-5/layer3_findings_test_output/report.md
#
# TEST CASES:
#   - Bellingham HS (530042000099) — district_context only (no school-level findings).
#     Should produce 6 deduped findings (same as district_context).
#   - Sehome HS (530042000113) — 6 district + 4 school findings, no overlap.
#     Should produce 10 deduped findings.
#   - Squalicum HS (530042002693) — 6 district + N school findings, ONE URL overlap
#     on the 2026 bus assault liability article. Should dedup to one fewer than
#     the union, with collision recorded.
#   - Fairhaven Middle (530042000104, golden school) — sanity check.
#   - Whatcom Middle (530042000117) — sanity check.
#   - Options HS (530042001738) — alternative school sanity check.
#   - One non-Bellingham school for negative control (Bainbridge HS, 530033000043).
#   - Bogus NCES ID — confirm error path returns clean metadata.

import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
from pymongo import MongoClient

from pipeline.layer3_findings import get_findings_for_stage0

OUTPUT_DIR = os.path.join(HERE, "layer3_findings_test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_CASES = [
    ("530042000099", "Bellingham HS — district_context only"),
    ("530042000113", "Sehome HS — district + school, no URL overlap"),
    ("530042002693", "Squalicum HS — district + school, KNOWN URL overlap on bus-assault article"),
    ("530042000104", "Fairhaven Middle (golden school)"),
    ("530042000117", "Whatcom Middle"),
    ("530042001738", "Options HS (alternative)"),
    ("530033000043", "Bainbridge HS (non-Bellingham control)"),
    ("999999999999", "Bogus ID — error path test"),
]


def main():
    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client.get_default_database()

    lines = []
    lines.append("# Task 2 Test — get_findings_for_stage0() across canonical cases")
    lines.append("")
    lines.append("Function under test: `pipeline.layer3_findings.get_findings_for_stage0(db, nces_id)`")
    lines.append("")
    lines.append("Test runs the production query function against MongoDB Atlas, prints the")
    lines.append("source counts, deduped count, and any collisions detected. The receipt")
    lines.append("`docs/receipts/phase-5/task2_district_context.md` reads from this report.")
    lines.append("")

    for nces_id, label in TEST_CASES:
        print(f"\n{nces_id} | {label}")
        findings, meta = get_findings_for_stage0(db, nces_id)
        # Save full raw output per case
        case_path = os.path.join(OUTPUT_DIR, f"{nces_id}.json")
        with open(case_path, "w") as f:
            json.dump({"metadata": meta, "findings_count": len(findings),
                       "findings_preview": [
                           {
                               "category": x.get("category"),
                               "date": x.get("date"),
                               "source_url": x.get("source_url"),
                               "summary_preview": (x.get("summary") or "")[:160],
                           } for x in findings
                       ]}, f, indent=2, default=str)

        lines.append(f"## {label}")
        lines.append(f"**NCES ID:** `{nces_id}`")
        if meta.get("error"):
            lines.append(f"**Error path:** {meta['error']}")
            lines.append("")
            print(f"  ERROR PATH: {meta['error'][:80]}...")
            continue
        lines.append(f"- School: {meta['school_name']} — district: {meta['district_name']}")
        lines.append(f"- Source counts: school_context.findings={meta['n_school']}, "
                     f"district_context.findings={meta['n_district']} "
                     f"(total before dedup: {meta['n_total_before_dedup']})")
        lines.append(f"- Deduped findings to feed Stage 0: **{meta['n_deduped']}** "
                     f"(dropped by dedup: {meta['n_dropped_by_dedup']})")
        lines.append(f"- school_context status: {meta['school_context_status']}, "
                     f"district_context status: {meta['district_context_status']}")
        if meta["dedup_collisions"]:
            lines.append(f"- Dedup collisions:")
            for c in meta["dedup_collisions"]:
                key_str = " | ".join(str(k) for k in c["key"])
                preview = c.get("school_summary_preview", "")
                lines.append(f"  - `{c['layer']} -> {c['kept_layer']}` "
                             f"key=({key_str})")
                if preview:
                    lines.append(f"    school summary preview: {preview}...")
        lines.append("")
        print(f"  school={meta['n_school']} district={meta['n_district']} "
              f"deduped={meta['n_deduped']} collisions={len(meta['dedup_collisions'])}")

    out_path = os.path.join(OUTPUT_DIR, "report.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"\nReport: {out_path}")


if __name__ == "__main__":
    main()
