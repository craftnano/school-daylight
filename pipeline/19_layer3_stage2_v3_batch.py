# PURPOSE: Submit the full Layer 3 Stage 2 production batch using prompt v3.
#          Reads stage1_results.jsonl (all schools queued for Stage 2 from Phase A),
#          enriches each finding with source_url via the patched matcher, builds one
#          big batch with the v3 system prompt + cache_control marker, submits to
#          Anthropic Message Batches API, polls until done, streams results, writes
#          layer3_narrative to MongoDB for each school.
#
# INPUTS:
#   - phases/phase-5/production_run/stage1_results.jsonl
#   - prompts/layer3_stage2_sonnet_narrative_v3.txt
#   - MongoDB schools.<id> (read context + district_context for URL enrichment)
# OUTPUTS:
#   - MongoDB schools.<id>.layer3_narrative for every queued school
#   - phases/phase-5/production_run/stage2_v3_batch_id.txt
#   - phases/phase-5/production_run/stage2_v3_batch_results.jsonl
#   - phases/phase-5/production_run/stage2_v3_run_log.txt
#
# COST CONTROL: Hard cap $30 (the original $50 cap minus already-spent ~$19.50).
#   Aborts before submission if projected cost exceeds cap.
#
# IDEMPOTENCY: Each MongoDB write is $set, so re-running this script is safe; it
#   will overwrite existing layer3_narrative entries with fresh outputs.
#
# SKIPS: Schools already processed with prompt_version="layer3_v3" (i.e., v5 dry-run).
#        They are excluded from the batch to avoid wasting tokens. Schools with
#        older prompt versions (v1/v2 from earlier dry runs) WILL be re-run so the
#        whole production set ends up on v3.

import os
import sys
import re
import json
import time
import argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
import anthropic
from pymongo import MongoClient

from pipeline.layer3_prompts import load_stage2_v3, fill_user
from pipeline.layer3_findings import get_findings_for_stage0

SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v3"
MAX_TOKENS = 2200

SONNET_IN = 3.00
SONNET_OUT = 15.00
BATCH_DISCOUNT = 0.5
HARD_COST_CAP_USD = 30.00  # leaves ~$0.50 cushion under the original $50 cap

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
BATCH_ID_PATH = os.path.join(RUN_DIR, "stage2_v3_batch_id.txt")
RESULTS_PATH = os.path.join(RUN_DIR, "stage2_v3_batch_results.jsonl")
RUN_LOG_PATH = os.path.join(RUN_DIR, "stage2_v3_run_log.txt")

_CITE_RE = re.compile(r"</?cite[^>]*>", re.IGNORECASE)


def log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    with open(RUN_LOG_PATH, "a") as f:
        f.write(line + "\n")


def _normalize_for_match(s):
    if not s:
        return ""
    s = _CITE_RE.sub("", s)
    return " ".join(s.split())


def parse_json_response(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def enrich_with_source_urls(db, nces_id, stage1_included):
    deduped, _ = get_findings_for_stage0(db, nces_id)
    by_norm, by_prefix = {}, {}
    for f in deduped:
        s = _normalize_for_match(f.get("summary") or "")
        url = f.get("source_url") or ""
        if s and s not in by_norm:
            by_norm[s] = url
            by_prefix.setdefault(s[:100], url)
    out, n_matched = [], 0
    for f in stage1_included:
        ot = _normalize_for_match(f.get("original_text") or "")
        url = by_norm.get(ot) or by_prefix.get(ot[:100], "")
        copy = dict(f)
        copy["source_url"] = url or ""
        if url:
            n_matched += 1
        out.append(copy)
    return out, n_matched, len(stage1_included)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", type=str, default=None,
                        help="Resume an existing submitted batch instead of submitting fresh.")
    parser.add_argument("--dry-build", action="store_true",
                        help="Build requests, project cost, but do NOT submit.")
    args = parser.parse_args()

    log(f"=== Layer 3 Stage 2 v3 full batch run ===")
    s2_sys, s2_user_tmpl = load_stage2_v3()
    log(f"Loaded v3 prompt: {len(s2_sys)} chars system, {len(s2_user_tmpl)} chars user template.")

    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Resolve batch_id
    batch_id = args.batch_id
    if not batch_id and os.path.exists(BATCH_ID_PATH):
        with open(BATCH_ID_PATH) as f:
            batch_id = f.read().strip()
            log(f"Resuming saved batch_id: {batch_id}")

    if not batch_id:
        # Build fresh batch
        log("Reading stage1_results.jsonl...")
        latest_by_nid = {}
        with open(STAGE1_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                latest_by_nid[rec["nces_id"]] = rec
        log(f"Queued schools (deduped): {len(latest_by_nid)}")

        # Skip schools already on v3
        skip_v3 = set()
        for doc in db.schools.find(
            {"layer3_narrative.prompt_version": PROMPT_VERSION,
             "layer3_narrative.status": "ok"},
            {"_id": 1},
        ):
            skip_v3.add(doc["_id"])
        log(f"Already on layer3_v3 (will skip): {len(skip_v3)}")

        to_run = [latest_by_nid[nid] for nid in latest_by_nid if nid not in skip_v3]
        log(f"Schools to process this batch: {len(to_run)}")

        # Build requests
        requests = []
        n_match_total = n_findings_total = 0
        for rec in to_run:
            nid = rec["nces_id"]
            try:
                enriched, n_m, n_t = enrich_with_source_urls(
                    db, nid, rec["stage1_included"]
                )
            except Exception as e:
                log(f"  WARN: enrichment failed for {nid}: {e} — skipping")
                continue
            n_match_total += n_m
            n_findings_total += n_t
            findings_json = json.dumps(enriched, indent=2, default=str)
            user_msg = fill_user(
                s2_user_tmpl,
                school_name=rec["name"],
                district_name=rec.get("district_name", ""),
                nces_id=nid, findings=findings_json,
            )
            requests.append({
                "custom_id": nid,
                "params": {
                    "model": SONNET_MODEL,
                    "max_tokens": MAX_TOKENS,
                    "system": [{
                        "type": "text", "text": s2_sys,
                        "cache_control": {"type": "ephemeral", "ttl": "1h"},
                    }],
                    "messages": [{"role": "user", "content": user_msg}],
                },
            })

        log(f"Built {len(requests)} requests; URL enrichment {n_match_total}/{n_findings_total} "
            f"({100*n_match_total/max(1,n_findings_total):.1f}%).")

        # Cost projection from v5 per-school average ($0.0244 / 2 = $0.0122)
        per_school_proj = 0.0122
        proj_total = per_school_proj * len(requests)
        log(f"Projected cost (v5 per-school × N): ~${proj_total:.2f}")
        if proj_total > HARD_COST_CAP_USD:
            log(f"COST CAP HIT: projected ${proj_total:.2f} > cap ${HARD_COST_CAP_USD:.2f}. Abort.")
            return 1

        if args.dry_build:
            log("--dry-build set; not submitting.")
            return 0

        log("Submitting batch...")
        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        with open(BATCH_ID_PATH, "w") as f:
            f.write(batch_id)
        log(f"Batch submitted: {batch_id}")

    # Poll
    poll_seconds = 30
    while True:
        b = client.messages.batches.retrieve(batch_id)
        rc = b.request_counts
        log(f"  status={b.processing_status} processing={rc.processing} "
            f"succeeded={rc.succeeded} errored={rc.errored} canceled={rc.canceled} "
            f"expired={rc.expired}")
        if b.processing_status == "ended":
            break
        time.sleep(poll_seconds)

    # Stream results, write to MongoDB
    n_succeeded = n_errored = 0
    total_uncached = total_cache_creation = total_cache_read = total_output = 0
    if os.path.exists(RESULTS_PATH):
        os.remove(RESULTS_PATH)

    log("Streaming results and writing to MongoDB...")
    for result in client.messages.batches.results(batch_id):
        nid = result.custom_id
        rtype = result.result.type
        if rtype != "succeeded":
            err = str(getattr(result.result, "error", rtype))
            db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": {
                "text": "(generation failed at Stage 2 v3 — narrative unavailable)",
                "model": SONNET_MODEL, "status": f"stage2_{rtype}", "error": err,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_version": PROMPT_VERSION,
            }}})
            with open(RESULTS_PATH, "a") as f:
                f.write(json.dumps({"custom_id": nid, "type": rtype, "error": err}) + "\n")
            n_errored += 1
            continue

        msg = result.result.message
        text_content = next((b.text for b in msg.content if b.type == "text"), "")
        parsed = parse_json_response(text_content)
        narrative = (parsed or {}).get("narrative") if parsed else None
        if not narrative:
            narrative = text_content

        u = msg.usage
        uc_in = getattr(u, "input_tokens", 0) or 0
        cc = getattr(u, "cache_creation_input_tokens", 0) or 0
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        out = getattr(u, "output_tokens", 0) or 0
        total_uncached += uc_in
        total_cache_creation += cc
        total_cache_read += cr
        total_output += out

        # Pull stage1 metadata for the layer3_narrative payload
        # (lookup once, cached in caller scope; rebuild quickly here)
        # We cached latest_by_nid above only when building fresh batch; on resume we need it.
        # Cheapest: re-read from MongoDB stage1_results aggregate via a helper call.
        # For simplicity, re-read stage1_results.jsonl on resume.
        # (only done once per result-streaming pass)
        # Implementation: lazy-load if needed.
        s1_rec = _stage1_lookup(nid)

        payload = {
            "text": narrative,
            "model": SONNET_MODEL,
            "source_findings_count": s1_rec.get("source_findings_count", 0),
            "stage0_dropped_count": s1_rec.get("stage0_dropped_count", 0),
            "stage1_included_count": s1_rec.get("stage1_included_count", 0),
            "stage1_excluded_count": s1_rec.get("stage1_excluded_count", 0),
            "status": "ok", "error": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "prompt_version": PROMPT_VERSION,
        }
        db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": payload}})
        with open(RESULTS_PATH, "a") as f:
            f.write(json.dumps({
                "custom_id": nid, "type": "succeeded", "narrative": narrative,
                "input_tokens": uc_in, "cache_creation_tokens": cc,
                "cache_read_tokens": cr, "output_tokens": out,
            }, default=str) + "\n")
        n_succeeded += 1
        if n_succeeded % 100 == 0:
            running = (total_uncached / 1e6 * SONNET_IN * BATCH_DISCOUNT
                       + total_output / 1e6 * SONNET_OUT * BATCH_DISCOUNT)
            log(f"  ... wrote {n_succeeded} narratives, running cost ≈ ${running:.2f}")

    final_cost = (total_uncached / 1e6 * SONNET_IN * BATCH_DISCOUNT
                  + total_cache_creation / 1e6 * SONNET_IN * 2.0 * BATCH_DISCOUNT
                  + total_cache_read / 1e6 * SONNET_IN * 0.10 * BATCH_DISCOUNT
                  + total_output / 1e6 * SONNET_OUT * BATCH_DISCOUNT)
    log(f"\n=== DONE ===")
    log(f"Stage 2 succeeded: {n_succeeded}")
    log(f"Stage 2 errored:   {n_errored}")
    log(f"Tokens: uncached_in={total_uncached:,} cache_creation={total_cache_creation:,} "
        f"cache_read={total_cache_read:,} output={total_output:,}")
    log(f"Total Sonnet (batch v3): ${final_cost:.4f}")


_S1_CACHE = None


def _stage1_lookup(nid):
    global _S1_CACHE
    if _S1_CACHE is None:
        _S1_CACHE = {}
        with open(STAGE1_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    _S1_CACHE[rec["nces_id"]] = rec
                except json.JSONDecodeError:
                    pass
    return _S1_CACHE.get(nid, {})


if __name__ == "__main__":
    sys.exit(main() or 0)
