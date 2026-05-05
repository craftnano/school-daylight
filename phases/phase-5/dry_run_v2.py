# PURPOSE: Second editorial dry run for Phase 5 Layer 3. Generates Stage 2 narratives
#          for exactly 5 schools selected to exercise the rules the first Enumclaw
#          dry run did not cover:
#            - Squalicum HS (Bellingham — Title IX district pattern, multi-finding,
#              cross-context dedup collision on the bus-assault article)
#            - Bainbridge HS (death-circumstance suppression test case)
#            - Echo Glen School (Issaquah, large district, multi-finding)
#            - Phantom Lake Elementary (Bellevue, small school edge case)
#            - Juanita HS (the original Sonnet-4.5 hallucination case)
#
#          Reuses Stage 1 output from phases/phase-5/production_run/stage1_results.jsonl
#          (so no Haiku spend), submits a tiny 5-request Sonnet 4.6 batch with
#          prompt caching (1-hour TTL) on the Stage 2 system prompt, polls,
#          writes layer3_narrative to MongoDB, and produces a Finder-readable
#          markdown file.
#
# COST: real Stage 2 cost reported with corrected Haiku 4.5 / Sonnet 4.6 prices
#       and cache-aware accounting (cache_creation + cache_read tokens billed
#       distinctly from regular input).
#
# SAFETY: this script touches ONLY the 5 NCES IDs listed below. It does not
#         submit the full 1,770-school batch. It does not re-run Stage 0 or
#         Stage 1.
#
# OUTPUTS:
#   - phases/phase-5/dry_run_narratives_v2.md (Finder-readable)
#   - MongoDB schools.<id>.layer3_narrative for the 5 schools (overwrites prior)

import os
import sys
import json
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
import anthropic
from pymongo import MongoClient

from pipeline.layer3_prompts import load_stage2, fill_user

# ----- 5 schools selected per the handoff -----
PICKS = [
    ("530042002693", "Squalicum High School",
     "Bellingham — Title IX district pattern, multi-finding, cross-context dedup case"),
    ("530033000043", "Bainbridge High School",
     "Death-circumstance suppression test case (suicide settlement)"),
    ("530375001773", "Echo Glen School",
     "Issaquah district, multi-finding (Stage 1 included 6)"),
    ("530039000082", "Phantom Lake Elementary",
     "Bellevue, small school edge case"),
    ("530423000670", "Juanita High School",
     "Original Sonnet 4.5 hallucination test case"),
]

SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v1"
MAX_TOKENS = 2000

# Pricing (per million tokens) — verified 2026-04-30 against Anthropic platform docs.
SONNET_IN = 3.00
SONNET_OUT = 15.00
BATCH_DISCOUNT = 0.5
CACHE_READ_MULT = 0.10  # multiplier on base input price for cache hits
CACHE_WRITE_1H_MULT = 2.00  # multiplier on base input price for 1-hour cache writes

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
OUT_MD = os.path.join(PROJECT_ROOT, "phases", "phase-5", "dry_run_narratives_v2.md")


def load_stage1_for_picks():
    """Walk stage1_results.jsonl, collect the latest record for each picked NCES ID."""
    wanted = {nid for nid, _, _ in PICKS}
    found = {}  # nid -> stage1 record (latest wins on duplicate)
    with open(STAGE1_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            nid = rec.get("nces_id")
            if nid in wanted:
                found[nid] = rec
    missing = wanted - set(found.keys())
    if missing:
        raise RuntimeError(
            f"Missing Stage 1 results for: {sorted(missing)}. "
            f"These NCES IDs are not in {STAGE1_PATH}. They may not have been "
            "processed by the killed Phase A run, or their Stage 1 inclusions "
            "were zero (status=stage1_filtered_to_zero) and so no Stage 2 "
            "request was queued. Use the Phase A runner to re-process them, "
            "or pick alternate schools that are queued."
        )
    return found


def build_batch_request(nid, stage1_rec, system_template, user_template):
    """Build a Stage 2 batch request with 1-hour prompt cache on the system block."""
    findings = stage1_rec["stage1_included"]
    findings_json = json.dumps(findings, indent=2, default=str)
    user_msg = fill_user(
        user_template,
        school_name=stage1_rec["name"],
        district_name=stage1_rec.get("district_name", ""),
        nces_id=nid,
        findings=findings_json,
    )
    return {
        "custom_id": nid,
        "params": {
            "model": SONNET_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": [
                {
                    "type": "text",
                    "text": system_template,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ],
            "messages": [{"role": "user", "content": user_msg}],
        },
    }


def parse_json_response(raw_text):
    import re
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def main():
    print("=== Phase 5 dry run v2 — 5 schools, Stage 2 only, with prompt caching ===")
    s2_sys, s2_user_tmpl = load_stage2()
    stage1_records = load_stage1_for_picks()
    print(f"Loaded Stage 1 records for {len(stage1_records)} / {len(PICKS)} schools.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    # Build batch requests with cache_control on the system prompt.
    requests = []
    notes = {}
    for nid, name, note in PICKS:
        rec = stage1_records[nid]
        requests.append(build_batch_request(nid, rec, s2_sys, s2_user_tmpl))
        notes[nid] = (name, note, rec)

    # Submit batch
    print(f"Submitting batch of {len(requests)} requests...")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")

    # Poll
    while True:
        b = client.messages.batches.retrieve(batch_id)
        rc = b.request_counts
        print(f"  status={b.processing_status} processing={rc.processing} "
              f"succeeded={rc.succeeded} errored={rc.errored}")
        if b.processing_status == "ended":
            break
        time.sleep(15)

    # Stream results, parse, write to MongoDB, accumulate cost.
    rows = []  # one per school in PICKS order
    rows_by_nid = {}
    total_cache_creation = 0
    total_cache_read = 0
    total_uncached_input = 0
    total_output = 0
    n_succeeded = 0
    n_errored = 0

    for result in client.messages.batches.results(batch_id):
        nid = result.custom_id
        name, note, rec = notes.get(nid, (None, None, None))
        rtype = result.result.type
        if rtype != "succeeded":
            err = str(getattr(result.result, "error", rtype))
            db.schools.update_one(
                {"_id": nid},
                {"$set": {"layer3_narrative": {
                    "text": "(generation failed at Stage 2 — narrative unavailable)",
                    "model": SONNET_MODEL,
                    "status": f"stage2_{rtype}",
                    "error": err,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "prompt_version": PROMPT_VERSION,
                }}}
            )
            rows_by_nid[nid] = {"name": name, "note": note, "error": err,
                                "narrative": None, "rec": rec}
            n_errored += 1
            continue

        msg = result.result.message
        text_content = ""
        for block in msg.content:
            if block.type == "text":
                text_content = block.text
                break
        parsed = parse_json_response(text_content)
        narrative = (parsed or {}).get("narrative") if parsed else None
        if not narrative:
            narrative = text_content  # fallback

        # Cache-aware token accounting. Anthropic returns:
        #   usage.input_tokens — tokens NOT served from cache (uncached input)
        #   usage.cache_creation_input_tokens — tokens written to cache
        #   usage.cache_read_input_tokens — tokens served from cache (90% off)
        u = msg.usage
        uncached_in = getattr(u, "input_tokens", 0) or 0
        cache_creation = getattr(u, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        out = getattr(u, "output_tokens", 0) or 0
        total_uncached_input += uncached_in
        total_cache_creation += cache_creation
        total_cache_read += cache_read
        total_output += out

        # Write to MongoDB
        payload = {
            "text": narrative,
            "model": SONNET_MODEL,
            "source_findings_count": rec.get("source_findings_count", 0),
            "dedup_collisions_count": rec.get("dedup_collisions_count", 0),
            "stage0_dropped_count": rec.get("stage0_dropped_count", 0),
            "stage1_included_count": rec.get("stage1_included_count", 0),
            "stage1_excluded_count": rec.get("stage1_excluded_count", 0),
            "status": "ok",
            "error": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "prompt_version": PROMPT_VERSION,
        }
        db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": payload}})
        rows_by_nid[nid] = {"name": name, "note": note, "error": None,
                            "narrative": narrative, "rec": rec,
                            "tokens": {"uncached_in": uncached_in,
                                       "cache_creation": cache_creation,
                                       "cache_read": cache_read,
                                       "output": out}}
        n_succeeded += 1

    # Cost computation with batch + caching multipliers.
    # Batch discount applies on top of cache multipliers.
    uncached_cost = total_uncached_input / 1e6 * SONNET_IN * BATCH_DISCOUNT
    cache_write_cost = (total_cache_creation / 1e6 * SONNET_IN
                        * CACHE_WRITE_1H_MULT * BATCH_DISCOUNT)
    cache_read_cost = (total_cache_read / 1e6 * SONNET_IN
                       * CACHE_READ_MULT * BATCH_DISCOUNT)
    output_cost = total_output / 1e6 * SONNET_OUT * BATCH_DISCOUNT
    total_cost = uncached_cost + cache_write_cost + cache_read_cost + output_cost

    # What this run would have cost WITHOUT caching (every request charged at full
    # batch input rate). Useful for showing the savings.
    no_cache_input_cost = ((total_uncached_input + total_cache_creation + total_cache_read)
                           / 1e6 * SONNET_IN * BATCH_DISCOUNT)
    no_cache_total = no_cache_input_cost + output_cost
    savings = no_cache_total - total_cost

    # Print summary
    print()
    print(f"=== Stage 2 batch results ===")
    print(f"Succeeded: {n_succeeded} / {len(PICKS)}")
    print(f"Errored:   {n_errored}")
    print(f"Tokens:")
    print(f"  uncached input:        {total_uncached_input:,}")
    print(f"  cache_creation_input:  {total_cache_creation:,}  (1-hour TTL)")
    print(f"  cache_read_input:      {total_cache_read:,}")
    print(f"  output:                {total_output:,}")
    print(f"Cost (Sonnet 4.6 batch + 1h cache):")
    print(f"  uncached input @ ${SONNET_IN * BATCH_DISCOUNT:.2f}/MTok: ${uncached_cost:.4f}")
    print(f"  cache write 1h @ ${SONNET_IN * CACHE_WRITE_1H_MULT * BATCH_DISCOUNT:.2f}/MTok: ${cache_write_cost:.4f}")
    print(f"  cache read     @ ${SONNET_IN * CACHE_READ_MULT * BATCH_DISCOUNT:.2f}/MTok: ${cache_read_cost:.4f}")
    print(f"  output         @ ${SONNET_OUT * BATCH_DISCOUNT:.2f}/MTok: ${output_cost:.4f}")
    print(f"  TOTAL:         ${total_cost:.4f}")
    print(f"  (vs no caching: ${no_cache_total:.4f}, savings: ${savings:.4f})")

    # Write the markdown file
    md = []
    md.append("# Phase 5 Layer 3 — Dry Run v2 Narratives (5 schools)")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Model:** {SONNET_MODEL} (batch + 1-hour prompt cache on system prompt)")
    md.append(f"**Cost:** ${total_cost:.4f} (savings vs no-cache: ${savings:.4f})")
    md.append("")
    md.append("These five schools were selected to exercise rules the first")
    md.append("Enumclaw dry run did not cover: Title IX multi-finding consolidation,")
    md.append("death-circumstance suppression, large-district multi-finding narratives,")
    md.append("a small-school edge case, and the original Sonnet hallucination case.")
    md.append("")
    md.append("Each narrative is rendered below. Read carefully and approve or flag")
    md.append("specific edits before approving the full 1,770-school batch.")
    md.append("")
    md.append("---")
    md.append("")
    for nid, name, note in PICKS:
        row = rows_by_nid.get(nid)
        if not row:
            md.append(f"## {name}")
            md.append("")
            md.append(f"**NCES:** `{nid}` &middot; **No result returned for this NCES ID.**")
            md.append("")
            md.append("---")
            md.append("")
            continue
        rec = row["rec"]
        md.append(f"## {row['name']}")
        md.append("")
        md.append(f"**NCES:** `{nid}` &middot; **District:** {rec.get('district_name', '')}")
        md.append(f"**Selection rationale:** {row['note']}")
        md.append(f"**Stage 1 included findings:** {rec.get('stage1_included_count', '?')} "
                  f"&middot; **Source findings (deduped):** {rec.get('source_findings_count', '?')} "
                  f"&middot; **Stage 0 dropped:** {rec.get('stage0_dropped_count', 0)}")
        md.append("")
        if row["error"]:
            md.append(f"**ERROR:** {row['error']}")
        else:
            for para in (row["narrative"] or "").split("\n\n"):
                p = para.strip()
                if p:
                    md.append(p)
                    md.append("")
        md.append("---")
        md.append("")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md))
    print(f"\nWrote: {OUT_MD}")
    print(f"5 schools' layer3_narrative updated in MongoDB.")


if __name__ == "__main__":
    main()
