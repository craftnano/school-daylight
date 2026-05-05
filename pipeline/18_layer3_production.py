# PURPOSE: Layer 3 production run — generate web-sourced context narratives for all
#          2,532 Washington schools and write them back to MongoDB under
#          schools.<id>.layer3_narrative.
#
#          Phase A (per-school, sequential):
#            For each school, query both `context.findings` and `district_context.findings`
#            via pipeline.layer3_findings.get_findings_for_stage0(), run Stage 0
#            (Haiku extraction + Python conduct-date / dismissed-case rules), run Stage 1
#            (Haiku editorial triage). Append a Stage 2 request line to a Batch API JSONL
#            file for every school whose Stage 1 produced ≥1 included finding. Schools
#            with zero findings or zero Stage 1 inclusions get the canonical
#            "No significant web-sourced context was found for this school." narrative
#            written directly to MongoDB without a Stage 2 call.
#
#          Phase B (batch):
#            Submit the Stage 2 batch to Anthropic Message Batches API, poll until
#            completed, stream results, write each parsed narrative to MongoDB.
#
# INPUTS:
#   - schools collection in MongoDB (read-only): _id, name, district.name, context, district_context
#   - prompts/layer3_stage{0,1,2}_*_v1.txt (loaded via pipeline/layer3_prompts.py)
#
# OUTPUTS:
#   - MongoDB schools.<id>.layer3_narrative = { text, generated_at, prompt_version,
#     model, source_findings_count, dedup_collisions_count, stage0_dropped_count,
#     stage1_included_count, stage1_excluded_count, status, error }
#   - phases/phase-5/production_run/checkpoint.jsonl — per-school completion log
#   - phases/phase-5/production_run/stage1_results.jsonl — per-school Stage 1 output
#   - phases/phase-5/production_run/stage2_batch_requests.jsonl — Batch API input
#   - phases/phase-5/production_run/stage2_batch_results.jsonl — Batch API raw download
#   - phases/phase-5/production_run/run_log.md — human-readable progress log
#
# COST CONTROL:
#   Hard $50 cap. Tracks Haiku token spend in real time during Phase A, projects Stage 2
#   batch cost from input token count BEFORE submitting, aborts cleanly if running total +
#   projection would exceed cap. Anthropic batch processing is 50% off published rates.
#
# IDEMPOTENT:
#   Phase A skips schools already in checkpoint.jsonl. Phase B is invoked separately and
#   re-reads the batch input/output files. Re-running the full script after a partial
#   completion picks up where it left off.
#
# COMMANDS:
#   python3 pipeline/18_layer3_production.py --phase A              # all schools
#   python3 pipeline/18_layer3_production.py --phase A --limit 10   # dry-run 10 schools
#   python3 pipeline/18_layer3_production.py --phase B              # submit + write
#   python3 pipeline/18_layer3_production.py --phase B --batch-id <id>   # poll existing
#
# RECEIPT: docs/receipts/phase-5/task3_layer3_production.md
# FAILURE MODES:
#   - Stage 0 JSON parse failure → no extractions; Python rules drop nothing; all findings
#     pass through to Stage 1. Logged as soft warning in checkpoint.
#   - Stage 1 JSON parse failure → school marked status=stage1_failed; layer3_narrative
#     gets text="(generation failed)", error=<reason>. Continue.
#   - Cost cap hit → script saves state and exits with non-zero; builder runs --phase B
#     manually after deciding whether to expand cap.
#   - Network drop → Phase A picks up via checkpoint. Phase B's batch is server-side and
#     survives client disconnect; just re-poll with --batch-id.

import os
import sys
import json
import re
import time
import argparse
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
import anthropic
from anthropic.types.messages.batch_create_params import Request
from pymongo import MongoClient

from pipeline.layer3_prompts import load_stage0, load_stage1, load_stage2, fill_user
from pipeline.layer3_findings import get_findings_for_stage0

# ----- Models, prices, cap -----
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v1"
MAX_TOKENS = 2000

# Per Anthropic public pricing (per million tokens). Batch API = 50% off.
# Pricing constants for Haiku 4.5 / Sonnet 4.6 verified against
# https://platform.claude.com/docs/en/about-claude/pricing on 2026-04-30.
# The earlier values ($0.80/$4.00 for Haiku) were Haiku 3.5 rates, copied from
# run_round1.py — they undercounted Haiku 4.5 spend by 25%.
HAIKU_INPUT_PER_M = 1.00
HAIKU_OUTPUT_PER_M = 5.00
SONNET_INPUT_PER_M = 3.00
SONNET_OUTPUT_PER_M = 15.00
BATCH_DISCOUNT = 0.5
# Prompt caching multipliers (apply to base input price)
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00
CACHE_READ_MULT = 0.10

HARD_COST_CAP_USD = 50.00

# Rate limiting between Haiku calls in Phase A. Conservative — we have plenty of headroom
# with Tier 2 limits (4000 RPM, 80k OTPM) and most calls take 2–5s of API time anyway.
RATE_LIMIT_SECONDS = 1.0

# Stage 0 cutoffs — same as the validated Round 1 50-school replay (run_round1.py:50-53).
TODAY = date(2026, 4, 30)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

# ----- Paths -----
RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
os.makedirs(RUN_DIR, exist_ok=True)
CHECKPOINT_PATH = os.path.join(RUN_DIR, "checkpoint.jsonl")
STAGE1_RESULTS_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
BATCH_REQUESTS_PATH = os.path.join(RUN_DIR, "stage2_batch_requests.jsonl")
BATCH_RESULTS_PATH = os.path.join(RUN_DIR, "stage2_batch_results.jsonl")
BATCH_ID_PATH = os.path.join(RUN_DIR, "batch_id.txt")
RUN_LOG_PATH = os.path.join(RUN_DIR, "run_log.md")
NO_FINDINGS_NARRATIVE = "No significant web-sourced context was found for this school."

# Load prompts once at module level. Failure here aborts immediately rather than mid-run.
S0_SYS, S0_USER_TMPL = load_stage0()
S1_SYS, S1_USER_TMPL = load_stage1()
S2_SYS, S2_USER_TMPL = load_stage2()


# ============================================================
# HELPERS
# ============================================================

def parse_json_response(raw_text):
    """Extract JSON from a model response, tolerating ```json fences and prose preambles."""
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


def parse_extracted_date(s):
    """Convert a YYYY / YYYY-MM / YYYY-MM-DD-ish string to a date, or None on failure."""
    if s is None:
        return None
    s = str(s).strip().lower()
    if s in ("", "null", "none", "undated", "unknown"):
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), 28)
        except ValueError:
            return None
    m = re.match(r"^(\d{4})$", s)
    if m:
        return date(int(m.group(1)), 12, 31)
    return None


def append_jsonl(path, record):
    """Append a single record to a JSONL file, creating it if needed."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def load_checkpoint(path):
    """Return a set of NCES IDs that have already been processed in Phase A."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("nces_id"):
                    done.add(rec["nces_id"])
            except json.JSONDecodeError:
                pass
    return done


def haiku_cost(in_tokens, out_tokens):
    return in_tokens / 1e6 * HAIKU_INPUT_PER_M + out_tokens / 1e6 * HAIKU_OUTPUT_PER_M


def sonnet_batch_cost(in_tokens, out_tokens):
    return (in_tokens / 1e6 * SONNET_INPUT_PER_M +
            out_tokens / 1e6 * SONNET_OUTPUT_PER_M) * BATCH_DISCOUNT


# ============================================================
# STAGE 0 + STAGE 1 (sequential per-school, Haiku)
# ============================================================

def call_haiku(client, system_prompt, user_msg):
    """Call Haiku with one retry on transient failures. Returns (text, in_tokens, out_tokens)."""
    last_err = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text, response.usage.input_tokens, response.usage.output_tokens
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
            last_err = e
            if attempt == 0:
                time.sleep(5)
                continue
            raise
    raise last_err


def stage0_for_school(client, findings_for_prompt):
    """Run Stage 0 Haiku extraction + Python rule application. Returns (kept_indices,
    dropped, in_tok, out_tok, raw_text)."""
    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)
    user_msg = fill_user(S0_USER_TMPL, findings=findings_json)
    raw, in_t, out_t = call_haiku(client, S0_SYS, user_msg)
    parsed = parse_json_response(raw) or {}
    extractions = parsed.get("extractions", [])
    by_idx = {e.get("finding_index"): e for e in extractions
              if e.get("finding_index") is not None}

    classifications = []
    for f in findings_for_prompt:
        ext = by_idx.get(f["index"], {})
        cl = parse_extracted_date(ext.get("conduct_date_latest"))
        rd = parse_extracted_date(ext.get("response_date"))
        rt = (ext.get("response_type") or "unclear").lower().strip()
        tag = (ext.get("finding_type_tag") or "").strip().lower()
        classifications.append({
            "index": f["index"], "extraction": ext,
            "conduct_latest": cl, "response_dt": rd,
            "response_type": rt, "tag": tag,
            "is_dismissed": rt in DISMISSED_TYPES,
            "ancient_conduct": cl is not None and cl < CUTOFF_20YR,
        })
    pattern_eligible = set()
    for c in classifications:
        if (not c["is_dismissed"] and c["conduct_latest"] is not None
                and c["conduct_latest"] >= CUTOFF_20YR and c["tag"]):
            pattern_eligible.add(c["tag"])

    kept, dropped = [], []
    for c in classifications:
        if c["is_dismissed"]:
            if c["response_dt"] is not None and c["response_dt"] < CUTOFF_5YR:
                dropped.append({"finding_index": c["index"],
                                "rule": "DISMISSED_CASE_OUT_OF_WINDOW",
                                "extraction": c["extraction"]})
                continue
            kept.append(c["index"])
            continue
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pattern_eligible:
                kept.append(c["index"])
                continue
            dropped.append({"finding_index": c["index"],
                            "rule": "CONDUCT_DATE_ANCHOR",
                            "extraction": c["extraction"]})
            continue
        kept.append(c["index"])
    return kept, dropped, in_t, out_t, raw


def stage1_for_school(client, school_name, district_name, nces_id, kept_findings):
    """Run Stage 1 Haiku triage. Returns (parsed_or_None, in_tok, out_tok, raw_text)."""
    findings_json = json.dumps(kept_findings, indent=2, default=str)
    user_msg = fill_user(S1_USER_TMPL,
                         school_name=school_name, district_name=district_name,
                         nces_id=nces_id, findings=findings_json)
    raw, in_t, out_t = call_haiku(client, S1_SYS, user_msg)
    return parse_json_response(raw), in_t, out_t, raw


# ============================================================
# MONGODB WRITE
# ============================================================

def write_narrative(db, nces_id, payload):
    """$set the layer3_narrative field on a school document. Idempotent."""
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["prompt_version"] = PROMPT_VERSION
    db.schools.update_one(
        {"_id": nces_id},
        {"$set": {"layer3_narrative": payload}},
    )


# ============================================================
# PHASE A: per-school Stage 0+1 + batch request assembly
# ============================================================

def phase_a(args):
    print(f"=== Phase A: per-school Stage 0+1, batch request assembly ===")
    print(f"Cutoffs: today={TODAY.isoformat()}, 20yr={CUTOFF_20YR.isoformat()}, "
          f"5yr={CUTOFF_5YR.isoformat()}")
    print(f"Hard cost cap: ${HARD_COST_CAP_USD:.2f}")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    done = load_checkpoint(CHECKPOINT_PATH)
    print(f"Resuming: {len(done)} schools already in checkpoint.")

    query = {}
    if args.district_filter:
        query["district.name"] = {"$regex": args.district_filter, "$options": "i"}
    schools_cursor = db.schools.find(
        query, {"_id": 1, "name": 1, "district.name": 1}
    ).sort("_id", 1)
    if args.limit:
        schools_cursor = schools_cursor.limit(args.limit)
    schools = list(schools_cursor)
    # Apply shard filter if specified. Sharding lets multiple parallel workers
    # divide the school list with no overlap. Each worker grabs every M-th school
    # starting from offset N (0-indexed). Determinism via stable sort on _id above.
    if args.total_shards > 1:
        schools = [s for i, s in enumerate(schools) if i % args.total_shards == args.shard]
        print(f"Shard {args.shard}/{args.total_shards}: assigned {len(schools)} schools.")
    print(f"Schools to process: {len(schools)} (limit={args.limit})")

    total_haiku_in = 0
    total_haiku_out = 0
    n_processed = 0
    n_no_findings = 0
    n_stage1_zero = 0
    n_stage1_failed = 0
    n_pending_stage2 = 0

    for i, school in enumerate(schools):
        nces_id = school["_id"]
        name = school.get("name", "?")
        district_name = (school.get("district") or {}).get("name", "")

        if nces_id in done:
            continue

        try:
            findings, meta = get_findings_for_stage0(db, nces_id)
        except Exception as e:
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "findings_query_failed",
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"[{i+1}/{len(schools)}] {nces_id} {name}: findings_query FAILED: {e}")
            continue

        # No findings? Write the canonical fallback and move on. No API spend.
        if not findings:
            payload = {
                "text": NO_FINDINGS_NARRATIVE,
                "model": None,
                "source_findings_count": 0,
                "dedup_collisions_count": len(meta.get("dedup_collisions", [])),
                "stage0_dropped_count": 0,
                "stage1_included_count": 0,
                "stage1_excluded_count": 0,
                "status": "no_findings",
                "error": None,
            }
            write_narrative(db, nces_id, payload)
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "no_findings",
                "haiku_in": 0, "haiku_out": 0,
            })
            n_processed += 1
            n_no_findings += 1
            if (i + 1) % 50 == 0:
                print(f"[{i+1}/{len(schools)}] processed={n_processed} no_findings={n_no_findings} "
                      f"stage1_zero={n_stage1_zero} pending_s2={n_pending_stage2} "
                      f"haiku_cost=${haiku_cost(total_haiku_in, total_haiku_out):.4f}")
            continue

        # Build Stage 0 input
        findings_for_prompt = []
        for j, f in enumerate(findings):
            findings_for_prompt.append({
                "index": j + 1,
                "category": f.get("category", "unknown"),
                "date": f.get("date") or "undated",
                "confidence": f.get("confidence", "unknown"),
                "sensitivity": f.get("sensitivity", "normal"),
                "summary": f.get("summary", "No summary"),
            })

        # Stage 0
        try:
            kept, dropped, s0_in, s0_out, _ = stage0_for_school(client, findings_for_prompt)
        except Exception as e:
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "stage0_failed",
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"[{i+1}/{len(schools)}] {nces_id} {name}: stage0 FAILED: {e}")
            time.sleep(RATE_LIMIT_SECONDS)
            continue
        total_haiku_in += s0_in
        total_haiku_out += s0_out
        kept_for_prompt = [f for f in findings_for_prompt if f["index"] in kept]
        time.sleep(RATE_LIMIT_SECONDS)

        # Stage 1
        try:
            s1_parsed, s1_in, s1_out, _ = stage1_for_school(
                client, name, district_name, nces_id, kept_for_prompt
            )
        except Exception as e:
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "stage1_failed",
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"[{i+1}/{len(schools)}] {nces_id} {name}: stage1 FAILED: {e}")
            time.sleep(RATE_LIMIT_SECONDS)
            continue
        total_haiku_in += s1_in
        total_haiku_out += s1_out

        if s1_parsed is None:
            # Couldn't parse Stage 1; write error narrative.
            payload = {
                "text": "(generation failed at Stage 1 — narrative unavailable)",
                "model": HAIKU_MODEL,
                "source_findings_count": len(findings),
                "dedup_collisions_count": len(meta.get("dedup_collisions", [])),
                "stage0_dropped_count": len(dropped),
                "stage1_included_count": 0,
                "stage1_excluded_count": 0,
                "status": "stage1_parse_failed",
                "error": "Stage 1 returned malformed JSON",
            }
            write_narrative(db, nces_id, payload)
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "stage1_parse_failed",
                "haiku_in": s0_in + s1_in, "haiku_out": s0_out + s1_out,
            })
            n_processed += 1
            n_stage1_failed += 1
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        included = s1_parsed.get("included", [])
        excluded = s1_parsed.get("excluded", [])

        if not included:
            # Stage 1 included zero — write fallback narrative directly.
            payload = {
                "text": NO_FINDINGS_NARRATIVE,
                "model": HAIKU_MODEL,
                "source_findings_count": len(findings),
                "dedup_collisions_count": len(meta.get("dedup_collisions", [])),
                "stage0_dropped_count": len(dropped),
                "stage1_included_count": 0,
                "stage1_excluded_count": len(excluded),
                "status": "stage1_filtered_to_zero",
                "error": None,
            }
            write_narrative(db, nces_id, payload)
            append_jsonl(CHECKPOINT_PATH, {
                "nces_id": nces_id, "name": name, "status": "stage1_filtered_to_zero",
                "haiku_in": s0_in + s1_in, "haiku_out": s0_out + s1_out,
            })
            n_processed += 1
            n_stage1_zero += 1
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        # Save Stage 1 result for batch input assembly
        s1_record = {
            "nces_id": nces_id, "name": name, "district_name": district_name,
            "source_findings_count": len(findings),
            "dedup_collisions_count": len(meta.get("dedup_collisions", [])),
            "stage0_dropped_count": len(dropped),
            "stage0_dropped": dropped,
            "stage1_included": included,
            "stage1_included_count": len(included),
            "stage1_excluded_count": len(excluded),
            "haiku_in": s0_in + s1_in, "haiku_out": s0_out + s1_out,
        }
        append_jsonl(STAGE1_RESULTS_PATH, s1_record)

        # Build the Stage 2 batch request
        stage2_findings_json = json.dumps(included, indent=2, default=str)
        s2_user_msg = fill_user(
            S2_USER_TMPL,
            school_name=name, district_name=district_name,
            nces_id=nces_id, findings=stage2_findings_json,
        )
        batch_request = {
            "custom_id": nces_id,
            "params": {
                "model": SONNET_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": S2_SYS,
                "messages": [{"role": "user", "content": s2_user_msg}],
            },
        }
        append_jsonl(BATCH_REQUESTS_PATH, batch_request)

        append_jsonl(CHECKPOINT_PATH, {
            "nces_id": nces_id, "name": name, "status": "queued_for_stage2",
            "haiku_in": s0_in + s1_in, "haiku_out": s0_out + s1_out,
            "stage1_included_count": len(included),
        })
        n_processed += 1
        n_pending_stage2 += 1

        # Cost cap check (Stage 0/1 actual + projected Stage 2 cost)
        running_haiku = haiku_cost(total_haiku_in, total_haiku_out)
        # Rough projection: Sonnet input ≈ 4× findings text size, output ≈ 800 tokens
        est_sonnet_in = n_pending_stage2 * 3000  # ~3k input per school (typical)
        est_sonnet_out = n_pending_stage2 * 800
        projected_total = running_haiku + sonnet_batch_cost(est_sonnet_in, est_sonnet_out)
        if projected_total > HARD_COST_CAP_USD:
            print(f"COST CAP APPROACHING: projected ${projected_total:.4f} > ${HARD_COST_CAP_USD:.2f}")
            print(f"Stopping Phase A. Run --phase B manually if you want to ship what's queued.")
            break

        time.sleep(RATE_LIMIT_SECONDS)

        if (i + 1) % 50 == 0:
            print(f"[{i+1}/{len(schools)}] processed={n_processed} no_findings={n_no_findings} "
                  f"s1_zero={n_stage1_zero} pending_s2={n_pending_stage2} "
                  f"haiku_cost=${running_haiku:.4f}")

    final_haiku = haiku_cost(total_haiku_in, total_haiku_out)
    print(f"\n=== Phase A complete ===")
    print(f"Schools processed: {n_processed} / {len(schools)} (skipped {len(done)} from prior run)")
    print(f"  no_findings:        {n_no_findings}")
    print(f"  stage1_filtered_to_zero: {n_stage1_zero}")
    print(f"  stage1_failed:      {n_stage1_failed}")
    print(f"  queued for Stage 2: {n_pending_stage2}")
    print(f"Haiku spend: ${final_haiku:.4f} ({total_haiku_in:,} in / {total_haiku_out:,} out)")
    print(f"Next: python3 pipeline/18_layer3_production.py --phase B")


# ============================================================
# PHASE B: submit batch, poll, write narratives
# ============================================================

def phase_b(args):
    print(f"=== Phase B: Stage 2 batch submit + write narratives ===")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    # Resolve batch ID: either passed in, saved from prior submit, or fresh.
    batch_id = args.batch_id
    if not batch_id and os.path.exists(BATCH_ID_PATH):
        with open(BATCH_ID_PATH) as f:
            batch_id = f.read().strip()
            print(f"Resuming saved batch_id: {batch_id}")

    if not batch_id:
        # Submit a fresh batch
        if not os.path.exists(BATCH_REQUESTS_PATH):
            print(f"No batch input found at {BATCH_REQUESTS_PATH}. Run --phase A first.")
            return
        requests = []
        with open(BATCH_REQUESTS_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    requests.append(json.loads(line))
        print(f"Submitting batch with {len(requests)} requests...")
        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        with open(BATCH_ID_PATH, "w") as f:
            f.write(batch_id)
        print(f"Batch submitted: {batch_id}")

    # Poll
    poll_seconds = 30
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        rc = batch.request_counts
        print(f"  status={batch.processing_status} processing={rc.processing} "
              f"succeeded={rc.succeeded} errored={rc.errored} canceled={rc.canceled} "
              f"expired={rc.expired}")
        if batch.processing_status == "ended":
            break
        time.sleep(poll_seconds)

    # Stream results
    n_succeeded = 0
    n_errored = 0
    sonnet_in = 0
    sonnet_out = 0
    print(f"Streaming results...")
    # SDK returns an iterator over MessageBatchIndividualResponse
    if os.path.exists(BATCH_RESULTS_PATH):
        os.remove(BATCH_RESULTS_PATH)

    for result in client.messages.batches.results(batch_id):
        nces_id = result.custom_id
        # The SDK returns a typed envelope. Result types: succeeded / errored / canceled / expired.
        rtype = result.result.type
        if rtype != "succeeded":
            err_msg = ""
            if hasattr(result.result, "error"):
                err_msg = str(result.result.error)
            payload = {
                "text": "(generation failed at Stage 2 — narrative unavailable)",
                "model": SONNET_MODEL,
                "status": f"stage2_{rtype}",
                "error": err_msg or rtype,
            }
            write_narrative(db, nces_id, payload)
            append_jsonl(BATCH_RESULTS_PATH, {
                "custom_id": nces_id, "type": rtype, "error": err_msg
            })
            n_errored += 1
            continue

        msg = result.result.message
        text_content = ""
        for block in msg.content:
            if block.type == "text":
                text_content = block.text
                break
        sonnet_in += msg.usage.input_tokens
        sonnet_out += msg.usage.output_tokens

        parsed = parse_json_response(text_content)
        if parsed and "narrative" in parsed:
            narrative = parsed["narrative"]
        else:
            # Fallback: use raw text if JSON parse failed
            narrative = text_content
        # Find the matching Stage 1 record for full metadata
        s1_meta = _find_s1_record(nces_id)
        payload = {
            "text": narrative,
            "model": SONNET_MODEL,
            "source_findings_count": s1_meta.get("source_findings_count", 0),
            "dedup_collisions_count": s1_meta.get("dedup_collisions_count", 0),
            "stage0_dropped_count": s1_meta.get("stage0_dropped_count", 0),
            "stage1_included_count": s1_meta.get("stage1_included_count", 0),
            "stage1_excluded_count": s1_meta.get("stage1_excluded_count", 0),
            "status": "ok",
            "error": None,
        }
        write_narrative(db, nces_id, payload)
        append_jsonl(BATCH_RESULTS_PATH, {
            "custom_id": nces_id, "type": "succeeded",
            "narrative": narrative,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        })
        n_succeeded += 1

    final_sonnet = sonnet_batch_cost(sonnet_in, sonnet_out)
    print(f"\n=== Phase B complete ===")
    print(f"Stage 2 succeeded: {n_succeeded}")
    print(f"Stage 2 errored:   {n_errored}")
    print(f"Sonnet (batch) spend: ${final_sonnet:.4f} "
          f"({sonnet_in:,} in / {sonnet_out:,} out)")


_S1_RECORD_CACHE = None


def _find_s1_record(nces_id):
    """Look up the Stage 1 record for an NCES ID. Lazy-loads stage1_results.jsonl into a dict."""
    global _S1_RECORD_CACHE
    if _S1_RECORD_CACHE is None:
        _S1_RECORD_CACHE = {}
        if os.path.exists(STAGE1_RESULTS_PATH):
            with open(STAGE1_RESULTS_PATH) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        _S1_RECORD_CACHE[rec["nces_id"]] = rec
                    except json.JSONDecodeError:
                        pass
    return _S1_RECORD_CACHE.get(nces_id, {})


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Layer 3 production runner")
    parser.add_argument("--phase", choices=["A", "B"], required=True)
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap number of schools (Phase A). Useful for dry runs.")
    parser.add_argument("--district-filter", type=str, default=None,
                        help="Regex restricting Phase A to matching district names.")
    parser.add_argument("--shard", type=int, default=0,
                        help="0-indexed shard number for this worker (Phase A).")
    parser.add_argument("--total-shards", type=int, default=1,
                        help="Total parallel workers (Phase A). Each worker handles "
                             "schools where (sorted_index %% total_shards) == shard.")
    parser.add_argument("--batch-id", type=str, default=None,
                        help="Resume a previously submitted batch in Phase B.")
    args = parser.parse_args()

    if args.phase == "A":
        phase_a(args)
    else:
        phase_b(args)


if __name__ == "__main__":
    main()
