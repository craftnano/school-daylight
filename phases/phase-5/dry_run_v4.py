# PURPOSE: Phase 5 dry run v4 — 8 targeted schools through the v2 Stage 2 prompt.
#          Verifies Rule 15 (timeless past-tense), Rule 16 (source-fidelity verbs),
#          Rule 17 (grade-level redaction), and per-paragraph citations.
#
# 8 schools (chosen specifically to verify the rule changes do what they should):
#   - Frontier Middle School (Moses Lake)        — Rule 16: "was terminated" must NOT reappear
#   - Central Valley Virtual Learning            — Rule 16: "was fired" must NOT reappear
#   - Garfield Elementary (Toppenish)            — Rule 17: "senior year" must be replaced
#   - Kirkwood Elementary (Toppenish)            — Rule 17: same
#   - Valley View Elementary (Toppenish)         — Rule 17: same
#   - Squalicum HS (Bellingham)                  — Citations: multi-finding consolidated narrative
#   - Bainbridge HS                              — Rule 15: "These remain allegations" must disappear
#   - Phantom Lake Elementary                    — Rule 15: "no resolution" / "ongoing" must rewrite
#
# SOURCE URL ENRICHMENT: Stage 1 output ("original_text") does not carry source_url.
#   To support per-paragraph citations the runner re-queries each school's full
#   deduped findings list from MongoDB at Stage 2 build time and matches by
#   original_text == summary to recover source_url. The matched URL is added to
#   each finding in the Stage 2 input JSON. The v2 system prompt instructs Sonnet
#   to read source_url and emit [Sources: ...] blocks at paragraph boundaries.
#
# OUTPUT: phases/phase-5/dry_run_narratives_v4.md, MongoDB layer3_narrative for the 8.
# COST: estimated ~$0.05 (8 schools × ~$0.0062/school + small extra output for citations).

import os
import sys
import re
import json
import time
import statistics
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

from pipeline.layer3_prompts import load_stage2_v2, fill_user
from pipeline.layer3_findings import get_findings_for_stage0

SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v2"
MAX_TOKENS = 2200  # slight bump for citation-block tokens

SONNET_IN = 3.00
SONNET_OUT = 15.00
BATCH_DISCOUNT = 0.5
CACHE_READ_MULT = 0.10
CACHE_WRITE_1H_MULT = 2.00

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
OUT_MD = os.path.join(PROJECT_ROOT, "phases", "phase-5", "dry_run_narratives_v4.md")

PICKS = [
    ("530522002625", "Frontier Middle School",
     "Rule 16 verb-anchor: 'was terminated' should NOT reappear"),
    ("530111003788", "Central Valley Virtual Learning",
     "Rule 16 verb-anchor: 'was fired' should NOT reappear"),
    ("530897001531", "Garfield Elementary School",
     "Rule 17 grade-level redaction: 'senior year' should be replaced"),
    ("530897001812", "Kirkwood Elementary School",
     "Rule 17 grade-level redaction: 'senior year' should be replaced"),
    ("530897003027", "Valley View Elementary",
     "Rule 17 grade-level redaction: 'senior year' should be replaced"),
    ("530042002693", "Squalicum High School",
     "Per-paragraph citations: multi-finding consolidated narrative"),
    ("530033000043", "Bainbridge High School",
     "Rule 15 timeless tense: 'These remain allegations' should disappear"),
    ("530039000082", "Phantom Lake Elementary",
     "Rule 15 timeless tense: 'no resolution' / 'ongoing' should rewrite cleanly"),
]


# ----- Verification phrase lists -----
RULE_15_FORBIDDEN = [
    "remain allegations", "remains unresolved", "is currently under investigation",
    "is ongoing", "no resolution has been reported", "no resolution is noted",
    "no resolution of that lawsuit was indicated", "no resolution of",
    "law firms are actively investigating", "remained ongoing",
    "remains an active", "as of the filing date",
]
RULE_16_FORBIDDEN = [
    "was fired", "was terminated", "resigned", "was dismissed",
    "was demoted", "was reassigned", "was disciplined",
    "was let go", "received a warning",
]
RULE_17_FORBIDDEN_PATTERNS = [
    r"\bsenior year\b", r"\bjunior year\b", r"\bsophomore year\b",
    r"\bfreshman year\b", r"\b\d+(?:st|nd|rd|th)\s+grader?\b",
    r"\bin \d+(?:st|nd|rd|th) grade\b", r"\beighth grader?\b",
    r"\bfifth grader?\b", r"\bsenior\b(?!\s+(?:leadership|administrator|advisor|staff|management|official))",
]


def parse_json_response(raw_text):
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


def load_stage1_records(nces_ids):
    """Latest Stage 1 record per requested NCES ID."""
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
            nid = rec.get("nces_id")
            if nid in wanted:
                found[nid] = rec
    return found


_CITE_RE = re.compile(r"</?cite[^>]*>", re.IGNORECASE)


def _normalize_for_match(s):
    """Strip <cite index="...">...</cite> wrappers and collapse whitespace.

    Source summaries on MongoDB documents arrive from Phase 4 enrichment with
    `<cite>` wrappers around the cited content — these are an artifact of how
    Haiku formats web-search citations. Stage 1's "factual pass-through" gives
    us tag-stripped `original_text`. To match Stage 1 output back to source we
    have to strip the same tags.
    """
    if not s:
        return ""
    s = _CITE_RE.sub("", s)
    return " ".join(s.split())


def enrich_with_source_urls(db, nces_id, stage1_included):
    """For each Stage 1 included finding, look up its source_url from MongoDB.

    Strategy: re-query the deduped findings list via get_findings_for_stage0(),
    normalize each source summary (strip <cite> tags, collapse whitespace), and
    build a lookup by normalized text. Match Stage 1's `original_text` (also
    normalized) to recover source_url. Falls back to first-100-char prefix
    match if exact normalized match fails.
    """
    deduped, _meta = get_findings_for_stage0(db, nces_id)
    by_norm = {}
    by_prefix = {}
    for f in deduped:
        s = _normalize_for_match(f.get("summary") or "")
        url = f.get("source_url") or ""
        if s and s not in by_norm:
            by_norm[s] = url
            prefix = s[:100]
            if prefix and prefix not in by_prefix:
                by_prefix[prefix] = url
    enriched = []
    n_matched = 0
    for f in stage1_included:
        out = dict(f)
        ot = _normalize_for_match(f.get("original_text") or "")
        url = by_norm.get(ot)
        if not url:
            # Fallback: prefix match (handles minor trailing-text edits by Haiku).
            url = by_prefix.get(ot[:100], "")
        if url:
            n_matched += 1
        out["source_url"] = url or ""
        enriched.append(out)
    return enriched, n_matched, len(stage1_included)


def main():
    print("=== Phase 5 dry run v4 — 8 targeted schools, Stage 2 v2 prompt ===")
    s2_sys, s2_user_tmpl = load_stage2_v2()
    print(f"Loaded v2 prompt — {len(s2_sys)} chars system, {len(s2_user_tmpl)} chars user template.")

    stage1 = load_stage1_records([nid for nid, _, _ in PICKS])

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    requests = []
    enrichment_log = {}
    for nid, name, rationale in PICKS:
        rec = stage1.get(nid)
        if not rec:
            print(f"WARN: no Stage 1 record for {nid} ({name}) — skipping")
            continue
        enriched, n_matched, n_total = enrich_with_source_urls(
            db, nid, rec["stage1_included"]
        )
        enrichment_log[nid] = (n_matched, n_total)
        print(f"  {nid} {name[:30]:30s}: enriched {n_matched}/{n_total} findings "
              f"with source_url")
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
    total_uncached = total_cache_creation = total_cache_read = total_output = 0
    for result in client.messages.batches.results(batch_id):
        nid = result.custom_id
        rec = stage1.get(nid, {})
        rtype = result.result.type
        if rtype != "succeeded":
            err = str(getattr(result.result, "error", rtype))
            db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": {
                "text": "(generation failed at Stage 2 v2 — narrative unavailable)",
                "model": SONNET_MODEL, "status": f"stage2_{rtype}", "error": err,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_version": PROMPT_VERSION,
            }}})
            rows[nid] = {"narrative": None, "error": err, "tokens": None}
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
        total_uncached += uc_in; total_cache_creation += cc
        total_cache_read += cr; total_output += out
        cost = (uc_in/1e6*SONNET_IN*BATCH_DISCOUNT
                + cc/1e6*SONNET_IN*CACHE_WRITE_1H_MULT*BATCH_DISCOUNT
                + cr/1e6*SONNET_IN*CACHE_READ_MULT*BATCH_DISCOUNT
                + out/1e6*SONNET_OUT*BATCH_DISCOUNT)
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
        rows[nid] = {"narrative": narrative, "error": None,
                     "tokens": {"uc_in": uc_in, "cc": cc, "cr": cr, "out": out},
                     "cost": cost}

    # Verify rule compliance per school
    def check_rules(nid, narrative):
        nl = (narrative or "").lower()
        # Rule 15
        r15 = [p for p in RULE_15_FORBIDDEN if p in nl]
        # Rule 16
        r16 = [p for p in RULE_16_FORBIDDEN if p in nl]
        # Rule 17 — regex; exclude clear non-grade contexts ("senior leadership" etc.)
        r17 = []
        for pat in RULE_17_FORBIDDEN_PATTERNS:
            for m in re.finditer(pat, narrative or "", re.IGNORECASE):
                # Exclude proper nouns: "Junior High" / "Senior High"
                start = m.start()
                window = (narrative or "")[max(0, start-3):m.end()+10]
                if re.search(r"junior\s+high|senior\s+high|senior\s+leadership", window, re.IGNORECASE):
                    continue
                r17.append(m.group())
        # Citations: count [Sources: ...] blocks. Should be ≥ 1, ideally 1 per paragraph.
        n_paragraphs = len([p for p in (narrative or "").split("\n\n") if p.strip()])
        n_citations = len(re.findall(r"\[Sources:\s*[^\]]+\]", narrative or ""))
        return {"rule15": r15, "rule16": r16, "rule17": r17,
                "n_paragraphs": n_paragraphs, "n_citations": n_citations}

    print("\n=== Per-school verification ===")
    verifications = {}
    for nid, name, rationale in PICKS:
        row = rows.get(nid)
        if not row or row["error"]:
            verifications[nid] = None
            continue
        v = check_rules(nid, row["narrative"])
        verifications[nid] = v
        flags = []
        if v["rule15"]: flags.append(f"Rule15:{v['rule15']}")
        if v["rule16"]: flags.append(f"Rule16:{v['rule16']}")
        if v["rule17"]: flags.append(f"Rule17:{v['rule17']}")
        cite_status = ("OK" if v["n_citations"] == v["n_paragraphs"]
                       else f"MISMATCH (paragraphs={v['n_paragraphs']}, citations={v['n_citations']})")
        flag_str = "  " + "; ".join(flags) if flags else "  CLEAN"
        print(f"  {nid} {name[:30]:30s} | citations={cite_status}{flag_str}")

    # Total cost
    haiku_eq = 0  # no Haiku in this run
    sonnet_total = (total_uncached/1e6*SONNET_IN*BATCH_DISCOUNT
                    + total_cache_creation/1e6*SONNET_IN*CACHE_WRITE_1H_MULT*BATCH_DISCOUNT
                    + total_cache_read/1e6*SONNET_IN*CACHE_READ_MULT*BATCH_DISCOUNT
                    + total_output/1e6*SONNET_OUT*BATCH_DISCOUNT)
    print(f"\nTotal Sonnet (batch v2): ${sonnet_total:.4f}")
    print(f"Tokens: uncached_in={total_uncached:,} cache_creation={total_cache_creation:,} "
          f"cache_read={total_cache_read:,} output={total_output:,}")

    # Markdown
    md = []
    md.append("# Phase 5 Layer 3 — Dry Run v4 (8 schools, Stage 2 v2 prompt)")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Model:** {SONNET_MODEL} batch + cache marker (1h ttl)")
    md.append(f"**Prompt version:** layer3_v2 — adds Rules 15, 16, 17 + per-paragraph citations")
    md.append(f"**Total cost:** ${sonnet_total:.4f}")
    md.append("")
    md.append("## Verification summary")
    md.append("")
    md.append("| NCES | School | Cite ratio | Rule 15 | Rule 16 | Rule 17 |")
    md.append("|------|--------|------------|---------|---------|---------|")
    for nid, name, _ in PICKS:
        v = verifications.get(nid)
        if not v:
            md.append(f"| `{nid}` | {name} | — | — | — | — |")
            continue
        cite = f"{v['n_citations']}/{v['n_paragraphs']}"
        r15 = "✓" if not v["rule15"] else f"✗ {v['rule15']}"
        r16 = "✓" if not v["rule16"] else f"✗ {v['rule16']}"
        r17 = "✓" if not v["rule17"] else f"✗ {v['rule17']}"
        md.append(f"| `{nid}` | {name} | {cite} | {r15} | {r16} | {r17} |")
    md.append("")
    md.append("---")
    md.append("")
    for nid, name, rationale in PICKS:
        row = rows.get(nid, {})
        v = verifications.get(nid) or {}
        rec = stage1.get(nid, {})
        n_matched, n_total = enrichment_log.get(nid, (0, 0))
        md.append(f"## {name}")
        md.append("")
        md.append(f"**NCES:** `{nid}` &middot; **District:** {rec.get('district_name','?')}")
        md.append(f"**Test rationale:** {rationale}")
        md.append(f"**Stage 1 included:** {rec.get('stage1_included_count', '?')} "
                  f"&middot; **Source URLs matched:** {n_matched}/{n_total}")
        md.append(f"**Citations rendered:** {v.get('n_citations', '?')} for "
                  f"{v.get('n_paragraphs', '?')} paragraphs")
        flags = []
        if v.get("rule15"): flags.append(f"Rule 15 hits: {v['rule15']}")
        if v.get("rule16"): flags.append(f"Rule 16 hits: {v['rule16']}")
        if v.get("rule17"): flags.append(f"Rule 17 hits: {v['rule17']}")
        if flags:
            md.append(f"**FLAGS:** {' | '.join(flags)}")
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


if __name__ == "__main__":
    main()
