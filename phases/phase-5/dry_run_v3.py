# PURPOSE: Third Phase 5 dry run — 50 stratified schools through Stage 2 only.
#          Reuses Stage 1 output from stage1_results.jsonl. Writes layer3_narrative
#          to MongoDB, runs auto-checks, computes cost distribution, projects
#          remaining 1,739-school cost from observed median + p90.
#
# INPUTS:
#   - phases/phase-5/production_run/v3_sample.json (50 NCES IDs picked by build step)
#   - phases/phase-5/production_run/stage1_results.jsonl (Stage 1 inputs)
#   - prompts/layer3_stage2_sonnet_narrative_v1.txt (system + user template)
# OUTPUTS:
#   - MongoDB schools.<id>.layer3_narrative for the 50 schools
#   - phases/phase-5/dry_run_narratives_v3.md (Finder-readable, with auto-check flags)

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

from pipeline.layer3_prompts import load_stage2, fill_user

SONNET_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "layer3_v1"
MAX_TOKENS = 2000

SONNET_IN = 3.00
SONNET_OUT = 15.00
BATCH_DISCOUNT = 0.5
CACHE_READ_MULT = 0.10
CACHE_WRITE_1H_MULT = 2.00

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
SAMPLE_PATH = os.path.join(RUN_DIR, "v3_sample.json")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
OUT_MD = os.path.join(PROJECT_ROOT, "phases", "phase-5", "dry_run_narratives_v3.md")


# Auto-check phrase lists — taken from run_round1.py:304-388 so we use the same
# checks the Phase 4.5 validation used.
HALLUCINATION_PHRASES = [
    "placed on leave", "later cleared", "cleared in", "reinstated",
    "no charges were filed", "charges were dropped", "found not guilty",
    "returned to duty", "resigned", "was fired", "was terminated",
    "stepped down", "was suspended", "was arrested",
]
STUDENT_ID_PATTERNS = [
    (r"\b\d{1,2}-year-old\b", "age"),
    (r"\bspecial needs\b", "disability"),
    (r"\bdisabled\b", "disability"),
    (r"\bautistic\b", "disability"),
    (r"\bIEP student\b", "disability"),
    (r"\bfreshman\b", "grade"),
    (r"\bsophomore\b", "grade"),
    (r"\bjunior\b", "grade"),
    (r"\bsenior\b", "grade"),
]
DEATH_CIRC_PHRASES = [
    "suicide", "overdose", "drowning", "drowned", "hanged", "hanging",
    "starvation", "wooded area", "on school grounds", "at the school",
    "in the gymnasium", "in the bathroom", "found dead",
]
GENDERED_STUDENT_PATTERNS = [
    r"\b(his|her|she|he)\s+(daughter|son|child)\b",
    r"\b(daughter|son)\s+(of|was|is)\b",
    r"\b(male|female)\s+student\b",
]
EVALUATIVE_PHRASES = [
    "controversial", "divisive", "progressive", "conservative",
    "culture war", "woke",
]


def auto_check(narrative, included_findings):
    """Return dict of category -> list of violation phrases. Hallucination check
    only flags phrases NOT present in the source findings text (the same logic
    Phase 4.5 used to distinguish real fabrication from supported language)."""
    nl = (narrative or "").lower()
    incl_text = " ".join((f.get("original_text") or "") for f in included_findings).lower()

    halluc = [p for p in HALLUCINATION_PHRASES if p in nl and p not in incl_text]

    sid = []
    for pat, label in STUDENT_ID_PATTERNS:
        for m in re.findall(pat, narrative or "", re.IGNORECASE):
            sid.append(f"{label}: '{m}'")

    death = [f"'{p}'" for p in DEATH_CIRC_PHRASES if p in nl]

    gen = []
    for pat in GENDERED_STUDENT_PATTERNS:
        for m in re.findall(pat, narrative or "", re.IGNORECASE):
            gen.append(" ".join(t for t in m if t) if isinstance(m, tuple) else str(m))

    eva = [p for p in EVALUATIVE_PHRASES if p in nl]

    has_year = bool(re.search(r"\b(19|20)\d{2}\b", narrative or ""))
    has_undated = bool(re.search(r"undated", narrative or "", re.IGNORECASE))
    if "No significant web-sourced context" in (narrative or ""):
        date_first = []
    elif not has_year and not has_undated:
        date_first = ["narrative has no year or 'undated' marker"]
    else:
        date_first = []

    return {
        "hallucinations": halluc, "student_id_leaks": sid,
        "death_circ": death, "gendered_student": gen,
        "evaluative": eva, "date_first": date_first,
    }


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
    """Walk stage1_results.jsonl, return latest record per requested NCES ID."""
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


def main():
    print("=== Phase 5 dry run v3 — 50 stratified schools ===")
    s2_sys, s2_user_tmpl = load_stage2()

    with open(SAMPLE_PATH) as f:
        sample = json.load(f)
    sample_by_nid = {r["nces_id"]: r for r in sample}
    sample_nids = list(sample_by_nid.keys())
    print(f"Loaded sample: {len(sample_nids)} schools")

    stage1 = load_stage1_records(sample_nids)
    missing = set(sample_nids) - set(stage1.keys())
    if missing:
        print(f"WARNING: missing Stage 1 records for {len(missing)} schools: "
              f"{sorted(missing)}")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000)
    db = mongo.get_default_database()

    # Build batch with cache_control on system. Cache likely won't fire (system
    # prompt below 1024-token min) but the marker is harmless.
    requests = []
    for nid in sample_nids:
        rec = stage1.get(nid)
        if not rec:
            continue
        findings_json = json.dumps(rec["stage1_included"], indent=2, default=str)
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

    print(f"Submitting batch of {len(requests)} requests...")
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
        time.sleep(20)

    # Stream results, collect per-school cost and auto-checks.
    rows = {}  # nid -> dict
    n_succeeded = 0
    n_errored = 0
    total_uncached = total_cache_creation = total_cache_read = total_output = 0

    for result in client.messages.batches.results(batch_id):
        nid = result.custom_id
        rec = stage1.get(nid, {})
        sample_meta = sample_by_nid.get(nid, {})
        rtype = result.result.type
        if rtype != "succeeded":
            err = str(getattr(result.result, "error", rtype))
            payload = {
                "text": "(generation failed at Stage 2 — narrative unavailable)",
                "model": SONNET_MODEL,
                "status": f"stage2_{rtype}",
                "error": err,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_version": PROMPT_VERSION,
            }
            db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": payload}})
            rows[nid] = {"sample_meta": sample_meta, "rec": rec,
                         "narrative": None, "error": err,
                         "tokens": None, "checks": None, "cost": 0.0}
            n_errored += 1
            continue
        msg = result.result.message
        text_content = next((b.text for b in msg.content if b.type == "text"), "")
        parsed = parse_json_response(text_content)
        narrative = (parsed or {}).get("narrative") if parsed else None
        if not narrative:
            narrative = text_content

        u = msg.usage
        uncached_in = getattr(u, "input_tokens", 0) or 0
        cache_creation = getattr(u, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        out = getattr(u, "output_tokens", 0) or 0
        total_uncached += uncached_in
        total_cache_creation += cache_creation
        total_cache_read += cache_read
        total_output += out

        per_school_cost = (
            uncached_in / 1e6 * SONNET_IN * BATCH_DISCOUNT
            + cache_creation / 1e6 * SONNET_IN * CACHE_WRITE_1H_MULT * BATCH_DISCOUNT
            + cache_read / 1e6 * SONNET_IN * CACHE_READ_MULT * BATCH_DISCOUNT
            + out / 1e6 * SONNET_OUT * BATCH_DISCOUNT
        )

        checks = auto_check(narrative, rec.get("stage1_included", []))

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

        rows[nid] = {
            "sample_meta": sample_meta, "rec": rec,
            "narrative": narrative, "error": None,
            "tokens": {
                "uncached_in": uncached_in, "cache_creation": cache_creation,
                "cache_read": cache_read, "output": out,
            },
            "checks": checks, "cost": per_school_cost,
        }
        n_succeeded += 1

    # Cost stats
    costs = [r["cost"] for r in rows.values() if r["error"] is None]
    costs_sorted = sorted(costs)
    n = len(costs_sorted)
    mean_cost = sum(costs) / n if n else 0
    median_cost = statistics.median(costs) if costs else 0
    max_cost = max(costs) if costs else 0
    p90_cost = costs_sorted[int(n * 0.9)] if n else 0
    total_cost = sum(costs)

    REMAINING = 1739
    proj_median = REMAINING * median_cost
    proj_p90 = REMAINING * p90_cost

    print()
    print(f"=== Cost stats over {n} succeeded narratives ===")
    print(f"  Mean per school:   ${mean_cost:.4f}")
    print(f"  Median per school: ${median_cost:.4f}")
    print(f"  90th pct:          ${p90_cost:.4f}")
    print(f"  Max per school:    ${max_cost:.4f}")
    print(f"  Total this run:    ${total_cost:.4f}")
    print(f"  Tokens: uncached_in={total_uncached:,} cache_creation={total_cache_creation:,} "
          f"cache_read={total_cache_read:,} output={total_output:,}")
    print()
    print(f"=== Projection for remaining {REMAINING} schools ===")
    print(f"  Using median (${median_cost:.4f}/school): ${proj_median:.2f}")
    print(f"  Using p90    (${p90_cost:.4f}/school): ${proj_p90:.2f}")
    print(f"  Already-spent total today (this run only): ${total_cost:.4f}")

    # Auto-check rollup
    flagged = []
    for nid, row in rows.items():
        if row["error"] or not row["checks"]:
            continue
        non_empty_cats = {k: v for k, v in row["checks"].items() if v}
        if non_empty_cats:
            flagged.append((nid, row, non_empty_cats))
    print()
    print(f"=== Auto-check flags ===")
    print(f"  Schools with at least one auto-check flag: {len(flagged)} / {n_succeeded}")
    for nid, row, cats in flagged:
        sm = row["sample_meta"]
        print(f"  {nid} | {sm.get('name')[:30]:30s} | flags={list(cats.keys())}")

    # Markdown output
    md = []
    md.append("# Phase 5 Layer 3 — Dry Run v3 Narratives (50 stratified schools)")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Model:** {SONNET_MODEL} (batch + 1-hour prompt cache marker; "
              f"see cache stats below)")
    md.append("")
    md.append(f"## Cost summary")
    md.append("")
    md.append(f"- Schools succeeded: {n_succeeded} / {len(sample_nids)}")
    md.append(f"- Errored: {n_errored}")
    md.append(f"- Mean per school: **${mean_cost:.4f}**")
    md.append(f"- Median per school: **${median_cost:.4f}**")
    md.append(f"- 90th percentile: **${p90_cost:.4f}**")
    md.append(f"- Max per school: **${max_cost:.4f}**")
    md.append(f"- Total this run: **${total_cost:.4f}**")
    md.append(f"- Tokens: uncached_in={total_uncached:,}, "
              f"cache_creation={total_cache_creation:,}, "
              f"cache_read={total_cache_read:,}, output={total_output:,}")
    md.append("")
    md.append(f"## Projection for remaining {REMAINING} schools")
    md.append("")
    md.append(f"- Using median per-school: **${proj_median:.2f}**")
    md.append(f"- Using 90th percentile per-school: **${proj_p90:.2f}**")
    md.append("")
    md.append(f"## Auto-check rollup")
    md.append("")
    md.append(f"- Schools with any auto-check flag: **{len(flagged)} / {n_succeeded}**")
    if flagged:
        md.append("")
        md.append("| NCES | School | Flagged categories |")
        md.append("|------|--------|--------------------|")
        for nid, row, cats in flagged:
            sm = row["sample_meta"]
            md.append(f"| `{nid}` | {sm.get('name')} | {', '.join(cats.keys())} |")
    md.append("")
    md.append("## Sample composition")
    md.append("")
    by_stratum = {"big": [], "mid": [], "small": []}
    east = []
    for nid, row in rows.items():
        sm = row["sample_meta"]
        by_stratum[sm.get("stratum", "?")].append((nid, sm))
        if sm.get("eastside"):
            east.append((nid, sm))
    md.append(f"- Big-district (18+): {len(by_stratum['big'])}")
    md.append(f"- Mid-district (10-17): {len(by_stratum['mid'])}")
    md.append(f"- Small-district (<10): {len(by_stratum['small'])}")
    md.append(f"- East-of-Cascades (any stratum): {len(east)}")
    md.append("")
    md.append("---")
    md.append("")

    # Sort: big first, then mid, then small; within each, by name
    sort_order = {"big": 0, "mid": 1, "small": 2}
    items = sorted(rows.items(),
                   key=lambda x: (sort_order.get(x[1]["sample_meta"].get("stratum"), 9),
                                  x[1]["sample_meta"].get("name", "")))

    for nid, row in items:
        sm = row["sample_meta"]
        rec = row["rec"]
        flags = ""
        if row["checks"]:
            non_empty = [k for k, v in row["checks"].items() if v]
            if non_empty:
                flags = f" &middot; **AUTO-CHECK FLAGS:** {', '.join(non_empty)}"
        eastside_marker = " &middot; east-of-Cascades" if sm.get("eastside") else ""
        cost_str = f"${row['cost']:.4f}" if row["error"] is None else "ERROR"
        md.append(f"## {sm.get('name')}")
        md.append("")
        md.append(f"**NCES:** `{nid}` &middot; **District:** {sm.get('district_name')} "
                  f"&middot; stratum=**{sm.get('stratum')}**{eastside_marker}")
        md.append(f"**Stage 1 included:** {sm.get('stage1_included_count')} "
                  f"&middot; **Source findings:** {sm.get('source_findings_count')} "
                  f"&middot; **Stage 0 dropped:** {sm.get('stage0_dropped_count', 0)} "
                  f"&middot; **Cost:** {cost_str}{flags}")
        md.append("")
        if row["error"]:
            md.append(f"**ERROR:** {row['error']}")
            md.append("")
        else:
            for para in (row["narrative"] or "").split("\n\n"):
                p = para.strip()
                if p:
                    md.append(p)
                    md.append("")
            if row["checks"]:
                non_empty = {k: v for k, v in row["checks"].items() if v}
                if non_empty:
                    md.append("**Auto-check details:**")
                    for k, v in non_empty.items():
                        md.append(f"- {k}: {v}")
                    md.append("")
        md.append("---")
        md.append("")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md))
    print(f"\nWrote: {OUT_MD}")
    print(f"50 schools' layer3_narrative updated in MongoDB.")


if __name__ == "__main__":
    main()
