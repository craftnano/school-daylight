# PURPOSE: Final pre-batch gate. Two schools through Stage 2 v3 prompt:
#          - Frontier MS (Moses Lake)  — verify strengthened Rule 4 suppresses
#            "drive-by shooting" and "West Loop Drive" from the prior v3/v4 narratives.
#          - Whatcom Middle (Bellingham) — fresh school, same district-context
#            structure as Squalicum, used to verify the citation matcher patch
#            (cite-tag stripping + prefix fallback) recovers real source URLs.
#
#          If both gates pass: proceed to full Stage 2 batch in production_run_v3.py.
#          If either fails: stop and report.
#
# OUTPUT: phases/phase-5/dry_run_narratives_v5.md
# COST: ~$0.02 (2 schools)

import os
import sys
import re
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

from pipeline.layer3_prompts import load_stage2_v3, fill_user
from pipeline.layer3_findings import get_findings_for_stage0

SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v3"
MAX_TOKENS = 2200

SONNET_IN = 3.00
SONNET_OUT = 15.00
BATCH_DISCOUNT = 0.5

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
OUT_MD = os.path.join(PROJECT_ROOT, "phases", "phase-5", "dry_run_narratives_v5.md")

PICKS = [
    ("530522002625", "Frontier Middle School",
     "Rule 4 v3 gate: 'drive-by shooting' + 'West Loop Drive' MUST be suppressed; narrative MUST report only 'a student died' + institutional response (grief support)."),
    ("530042000117", "Whatcom Middle School",
     "Citation matcher patch gate: Bellingham source summaries are <cite>-wrapped — patched matcher must recover real source URLs (target ≥3/4 matches; explicit zero '(unavailable)' cells)."),
]

# Forbidden Rule 4 manner/location patterns to verify against narratives.
RULE_4_FORBIDDEN = [
    "drive-by shooting", "drive by shooting", "shooting on", "shot on",
    "west loop drive", "moses lake — gunfire",
    "gunfire", "shot to death", "fatal shooting",
    "vehicle accident", "car crash", "drowned", "hanged", "hanging",
    "overdose", "drug overdose", "self-harm", "suicide",
    "died following", "died following a", "fatal", "killed in",
]


_CITE_RE = re.compile(r"</?cite[^>]*>", re.IGNORECASE)


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


def load_stage1(nces_ids):
    wanted = set(nces_ids)
    found = {}
    with open(STAGE1_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("nces_id") in wanted:
                found[rec["nces_id"]] = rec
    return found


def enrich_with_source_urls(db, nces_id, stage1_included):
    deduped, _ = get_findings_for_stage0(db, nces_id)
    by_norm = {}
    by_prefix = {}
    for f in deduped:
        s = _normalize_for_match(f.get("summary") or "")
        url = f.get("source_url") or ""
        if s and s not in by_norm:
            by_norm[s] = url
            by_prefix.setdefault(s[:100], url)
    out = []
    n_matched = 0
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
    print("=== Phase 5 dry run v5 — final pre-batch gate ===")
    s2_sys, s2_user_tmpl = load_stage2_v3()
    print(f"v3 prompt: {len(s2_sys)} chars system, {len(s2_user_tmpl)} chars user template.")

    stage1 = load_stage1([nid for nid, _, _ in PICKS])
    if len(stage1) != len(PICKS):
        print(f"WARN: missing Stage 1 records — got {set(stage1.keys())} "
              f"need {[nid for nid, _, _ in PICKS]}")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    requests = []
    enrichment_log = {}
    for nid, name, rationale in PICKS:
        rec = stage1.get(nid)
        if not rec:
            continue
        enriched, n_matched, n_total = enrich_with_source_urls(
            db, nid, rec["stage1_included"]
        )
        enrichment_log[nid] = (n_matched, n_total)
        print(f"  {nid} {name[:30]:30s}: enriched {n_matched}/{n_total} with source_url")
        findings_json = json.dumps(enriched, indent=2, default=str)
        user_msg = fill_user(
            s2_user_tmpl,
            school_name=rec["name"], district_name=rec.get("district_name", ""),
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

    print(f"\nSubmitting batch of {len(requests)} requests...")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")
    while True:
        b = client.messages.batches.retrieve(batch_id)
        rc = b.request_counts
        print(f"  status={b.processing_status} processing={rc.processing} "
              f"succeeded={rc.succeeded} errored={rc.errored}")
        if b.processing_status == "ended":
            break
        time.sleep(15)

    rows = {}
    total_in = total_out = 0
    for result in client.messages.batches.results(batch_id):
        nid = result.custom_id
        if result.result.type != "succeeded":
            rows[nid] = {"error": str(getattr(result.result, "error", "unknown")),
                         "narrative": None}
            continue
        msg = result.result.message
        text_content = next((b.text for b in msg.content if b.type == "text"), "")
        parsed = parse_json_response(text_content)
        narrative = (parsed or {}).get("narrative") if parsed else None
        if not narrative:
            narrative = text_content
        u = msg.usage
        in_tok = getattr(u, "input_tokens", 0) or 0
        out_tok = getattr(u, "output_tokens", 0) or 0
        total_in += in_tok
        total_out += out_tok
        rows[nid] = {"error": None, "narrative": narrative,
                     "in_tok": in_tok, "out_tok": out_tok}
        # write to MongoDB
        rec = stage1.get(nid, {})
        db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": {
            "text": narrative, "model": SONNET_MODEL,
            "source_findings_count": rec.get("source_findings_count", 0),
            "stage1_included_count": rec.get("stage1_included_count", 0),
            "stage1_excluded_count": rec.get("stage1_excluded_count", 0),
            "stage0_dropped_count": rec.get("stage0_dropped_count", 0),
            "status": "ok", "error": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "prompt_version": PROMPT_VERSION,
        }}})

    cost = total_in / 1e6 * SONNET_IN * BATCH_DISCOUNT + total_out / 1e6 * SONNET_OUT * BATCH_DISCOUNT
    print(f"\nTotal: ${cost:.4f} ({total_in:,} in / {total_out:,} out)")

    # ---- Gate evaluation ----
    print("\n=== GATE EVALUATION ===")
    gates_passed = True

    # Gate A: Frontier MS — Rule 4 manner/location suppression
    frontier = rows.get("530522002625", {})
    n_frontier = (frontier.get("narrative") or "")
    nl = n_frontier.lower()
    forbidden_hits = [p for p in RULE_4_FORBIDDEN if p in nl]
    requires_present = ("a student died" in nl) or ("the death of a student" in nl) or ("a student from" in nl and "died" in nl)
    print(f"\n[Frontier MS — Rule 4 v3 gate]")
    print(f"  Forbidden phrases hit: {forbidden_hits or 'NONE'}")
    print(f"  Required pattern present (e.g. 'a student died' / 'the death of a student'): {requires_present}")
    frontier_pass = (not forbidden_hits) and requires_present
    print(f"  GATE: {'PASS' if frontier_pass else 'FAIL'}")
    if not frontier_pass:
        gates_passed = False

    # Gate B: Whatcom — citation matcher
    whatcom = rows.get("530042000117", {})
    n_whatcom = (whatcom.get("narrative") or "")
    citations = re.findall(r"\[Sources:\s*([^\]]+)\]", n_whatcom)
    real_url_paragraphs = sum(1 for c in citations if "http" in c and "(one source unavailable)" not in c)
    n_paragraphs = sum(1 for p in n_whatcom.split("\n\n") if p.strip())
    n_match, n_total = enrichment_log.get("530042000117", (0, 0))
    print(f"\n[Whatcom Middle — citation matcher patch gate]")
    print(f"  Source URL match rate: {n_match}/{n_total}")
    print(f"  Citation blocks: {len(citations)} for {n_paragraphs} paragraphs")
    print(f"  Citation blocks with real URLs: {real_url_paragraphs}/{len(citations)}")
    whatcom_pass = (n_match >= max(1, n_total - 1)) and (real_url_paragraphs >= max(1, len(citations) - 1))
    print(f"  GATE: {'PASS' if whatcom_pass else 'FAIL'}")
    if not whatcom_pass:
        gates_passed = False

    print(f"\n{'='*60}")
    print(f"OVERALL: {'BOTH GATES PASS — proceed to full batch' if gates_passed else 'GATE FAIL — stop'}")
    print(f"{'='*60}")

    # ---- Markdown output ----
    md = []
    md.append("# Phase 5 Layer 3 — Dry Run v5 (final pre-batch gate)")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Prompt version:** layer3_v3 — Rule 4 strengthened with manner-of-death + location-of-death suppression")
    md.append(f"**Total cost:** ${cost:.4f}")
    md.append("")
    md.append("## Gate evaluation")
    md.append("")
    md.append(f"- **Frontier MS (Rule 4 v3):** {'PASS' if frontier_pass else 'FAIL'} — forbidden hits: {forbidden_hits or 'none'}; required pattern present: {requires_present}")
    md.append(f"- **Whatcom MS (citation matcher):** {'PASS' if whatcom_pass else 'FAIL'} — URL match {n_match}/{n_total}, real-URL citations {real_url_paragraphs}/{len(citations)}")
    md.append(f"- **Overall:** {'PROCEED TO FULL BATCH' if gates_passed else 'STOP — fix and re-test'}")
    md.append("")
    md.append("---")
    md.append("")
    for nid, name, rationale in PICKS:
        row = rows.get(nid, {})
        rec = stage1.get(nid, {})
        n_match, n_total = enrichment_log.get(nid, (0, 0))
        md.append(f"## {name}")
        md.append("")
        md.append(f"**NCES:** `{nid}` &middot; **District:** {rec.get('district_name', '?')}")
        md.append(f"**Test rationale:** {rationale}")
        md.append(f"**Stage 1 included:** {rec.get('stage1_included_count', '?')}; "
                  f"**Source URLs matched:** {n_match}/{n_total}")
        md.append("")
        if row.get("error"):
            md.append(f"**ERROR:** {row['error']}")
        else:
            for para in (row.get("narrative") or "").split("\n\n"):
                p = para.strip()
                if p:
                    md.append(p)
                    md.append("")
        md.append("---")
        md.append("")
    with open(OUT_MD, "w") as f:
        f.write("\n".join(md))
    print(f"\nWrote: {OUT_MD}")
    return 0 if gates_passed else 1


if __name__ == "__main__":
    sys.exit(main())
