# PURPOSE: Test the Stage 1 v2 prompt (positive-content exclusion removed) on 10
#          random schools drawn from the 184 affected schools the diagnostic identified.
#
#          Random sample with documented seed (random.seed(20260502)). Stratification
#          NOT used — pure random pick from the affected pool, per builder instruction.
#
#          For each school:
#            - Load deduped findings from MongoDB (get_findings_for_stage0).
#            - Reuse cached Stage 0 drops where available (stage1_results.jsonl).
#              Where unavailable (schools with status=stage1_filtered_to_zero, no
#              cached entry), call Stage 0 Haiku fresh.
#            - Run Stage 1 Haiku with the v2 prompt (rule removed).
#            - If Stage 1 includes ≥1 finding, queue Stage 2.
#            - Submit one Sonnet 4.6 batch (v3 prompt unchanged) for the queued schools.
#            - Stream results, write narratives to a markdown file.
#
#          DOES NOT write to MongoDB. The production v3 narratives stay in place;
#          this is an experimental output for builder review only.
#
# OUTPUT:  phases/phase-5/positive_content_test_v1.md
# COST:    ~$0.10–$0.20 (10 schools × 1–2 Haiku calls + 1 Sonnet batched call each)

import os
import sys
import re
import json
import time
import random
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
import anthropic
from pymongo import MongoClient

from pipeline.layer3_prompts import (load_stage0, load_stage1_v2,
                                     load_stage2_v3, fill_user)
from pipeline.layer3_findings import get_findings_for_stage0

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2200

HAIKU_IN, HAIKU_OUT = 1.00, 5.00
SONNET_IN, SONNET_OUT = 3.00, 15.00
BATCH_DISCOUNT = 0.5

TODAY = date(2026, 5, 2)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
OUT_MD = os.path.join(PROJECT_ROOT, "phases", "phase-5", "positive_content_test_v1.md")


# ---- Re-derive the 184 affected pool using the same vocabulary as positive_content_diagnostic ----
PATTERNS = [
    ("Washington Achievement Award", r"washington achievement award"),
    ("Achievement Award (general)", r"\bachievement award"),
    ("Blue Ribbon", r"blue ribbon"),
    ("Schools of Distinction", r"schools? of distinction"),
    ("OSPI recognition", r"ospi (?:has )?recogn"),
    ("ESSA Distinguished", r"essa distinguished"),
    ("Title I Distinguished", r"title i distinguished"),
    ("Civil Rights Project recognition", r"civil rights project"),
    ("Green Ribbon", r"green ribbon"),
    ("National Blue Ribbon", r"national blue ribbon"),
    ("Milken Award", r"milken (?:award|educator)"),
    ("Presidential Award", r"presidential award"),
    ("National Board Certified", r"national board (?:certified|certification|teacher)"),
    ("Teacher of the Year", r"teacher of the year"),
    ("State champion", r"\bstate champion"),
    ("State finalists", r"state finalist"),
    ("National champion", r"\bnational champion"),
    ("Knowledge Bowl state+", r"knowledge bowl[^.]{0,80}(?:state|national|regional)"),
    ("Science Olympiad state+", r"science olympiad[^.]{0,80}(?:state|national|regional)"),
    ("Math Counts", r"math\s*counts"),
    ("Math Olympiad state+", r"math olympiad[^.]{0,80}(?:state|national|regional)"),
    ("Spelling Bee state+", r"spelling bee[^.]{0,80}(?:state|national|regional)"),
    ("Robotics championship", r"robotics championship"),
    ("FIRST competition", r"\bfirst (?:robotics|competition|tech challenge|lego league)"),
    ("Future Problem Solving", r"future problem solving"),
    ("DECA state+", r"\bdeca\b[^.]{0,80}(?:state|national|regional)"),
    ("FBLA state+", r"\bfbla\b[^.]{0,80}(?:state|national|regional)"),
    ("Quiz Bowl", r"quiz bowl"),
    ("Dual immersion / dual language", r"dual (?:immersion|language)"),
    ("International Baccalaureate", r"international baccalaureate|\bib (?:program|diploma|world school)"),
    ("AP Capstone", r"ap capstone"),
    ("Magnet school", r"magnet school"),
    ("Career pathway", r"career pathway"),
    ("STEM/STEAM designation", r"\bstem\b[^.]{0,40}(?:designation|certified|recognition)|steam[^.]{0,40}(?:designation|certified|recognition)"),
    ("Graduation rate (positive)", r"graduation rate[^.]{0,80}(?:highest|record|improv|gain|rise|rose|increased|all[- ]time)"),
    ("Achievement gap closed/narrowed", r"achievement gap[^.]{0,80}(?:closed|narrowed|reduc|shrank)"),
    ("Proficiency multi-year improvement", r"proficiency[^.]{0,120}(?:year[- ]over[- ]year|multi[- ]year|sustained|consistent|three years|five years)"),
]
COMPILED = [(label, re.compile(pat, re.IGNORECASE)) for label, pat in PATTERNS]


def has_positive_match(text):
    if not text:
        return False
    return any(rx.search(text) for _, rx in COMPILED)


_CITE_RE = re.compile(r"</?cite[^>]*>", re.IGNORECASE)


def _normalize_for_match(s):
    if not s:
        return ""
    s = _CITE_RE.sub("", s)
    return " ".join(s.split())


def parse_extracted_date(s):
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


def stage0_call(client, s0_sys, s0_user_tmpl, findings_for_prompt):
    """Run Stage 0 fresh and apply Python rules. Used only when no cache available."""
    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)
    user_msg = fill_user(s0_user_tmpl, findings=findings_json)
    response = client.messages.create(
        model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
        system=s0_sys,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "")
    parsed = parse_json_response(raw) or {}
    by_idx = {e.get("finding_index"): e
              for e in parsed.get("extractions", [])
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
    pat_eligible = set()
    for c in classifications:
        if (not c["is_dismissed"] and c["conduct_latest"] is not None
                and c["conduct_latest"] >= CUTOFF_20YR and c["tag"]):
            pat_eligible.add(c["tag"])
    kept, dropped = [], []
    for c in classifications:
        idx = c["index"]
        if c["is_dismissed"]:
            if c["response_dt"] is not None and c["response_dt"] < CUTOFF_5YR:
                dropped.append({"finding_index": idx, "rule": "DISMISSED_CASE_OUT_OF_WINDOW"})
                continue
            kept.append(idx)
            continue
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pat_eligible:
                kept.append(idx)
                continue
            dropped.append({"finding_index": idx, "rule": "CONDUCT_DATE_ANCHOR"})
            continue
        kept.append(idx)
    return kept, dropped, response.usage.input_tokens, response.usage.output_tokens


def main():
    print("=== Positive-content test v1 — 10 random schools, Stage 1 v2 + Stage 2 v3 ===")
    s0_sys, s0_user_tmpl = load_stage0()
    s1_sys, s1_user_tmpl = load_stage1_v2()
    s2_sys, s2_user_tmpl = load_stage2_v3()

    db = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000).get_default_database()
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # ---- Re-derive the affected pool: schools whose raw Phase 4 findings contain
    # at least one positive-content vocabulary match. Excludes the 1 school where
    # positive content already reached the final narrative (Ruben Trejo Dual
    # Language Academy, NCES 530825003912) and the 4 stage0_dropped-only schools
    # whose dispositions wouldn't change with rule removal.
    print("Walking population to re-derive affected pool...")
    affected = []
    EXCLUDE = {"530825003912"}  # the 1 already-success
    for doc in db.schools.find({}, {"_id": 1, "name": 1, "district.name": 1,
                                    "context": 1, "district_context": 1,
                                    "layer3_narrative.status": 1}):
        nid = doc["_id"]
        if nid in EXCLUDE:
            continue
        all_findings = []
        all_findings += (doc.get("context") or {}).get("findings") or []
        all_findings += (doc.get("district_context") or {}).get("findings") or []
        for f in all_findings:
            if has_positive_match(f.get("summary") or ""):
                affected.append({
                    "nces_id": nid, "name": doc.get("name", "?"),
                    "district": (doc.get("district") or {}).get("name", "?"),
                    "narrative_status": ((doc.get("layer3_narrative") or {})
                                         .get("status") or "?"),
                })
                break
    print(f"Affected pool size: {len(affected)} schools")

    # Random sample of 10
    random.seed(20260502)
    sample = random.sample(affected, 10)
    print(f"Random seed: 20260502")
    print(f"Sampled 10 schools:")
    for s in sample:
        print(f"  {s['nces_id']} | {s['name'][:35]:35s} | {s['district'][:30]:30s} | "
              f"prior_status={s['narrative_status']}")

    # Stage 1 cached lookup
    stage1_cache = {}
    with open(STAGE1_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            stage1_cache[rec["nces_id"]] = rec

    # ---- Run Stage 0 (cached or fresh) + Stage 1 v2 ----
    s0_input_tok = s0_output_tok = 0
    s1_input_tok = s1_output_tok = 0
    per_school = {}  # nid -> dict
    for s in sample:
        nid = s["nces_id"]
        try:
            deduped, _ = get_findings_for_stage0(db, nid)
        except Exception as e:
            print(f"  {nid}: findings query failed: {e}")
            per_school[nid] = {"error": str(e)}
            continue
        findings_for_prompt = []
        for j, f in enumerate(deduped):
            findings_for_prompt.append({
                "index": j + 1,
                "category": f.get("category", "unknown"),
                "date": f.get("date") or "undated",
                "confidence": f.get("confidence", "unknown"),
                "sensitivity": f.get("sensitivity", "normal"),
                "summary": f.get("summary", "No summary"),
            })

        # Stage 0: prefer cache, fall back to fresh call
        cached = stage1_cache.get(nid)
        if cached:
            dropped_idxs = {d["finding_index"] for d in cached.get("stage0_dropped", [])}
            kept_idxs = [f["index"] for f in findings_for_prompt
                         if f["index"] not in dropped_idxs]
            stage0_source = "cached"
        else:
            kept_idxs, _drops, ti, to = stage0_call(client, s0_sys, s0_user_tmpl,
                                                    findings_for_prompt)
            s0_input_tok += ti
            s0_output_tok += to
            stage0_source = "fresh_haiku"
        kept_for_stage1 = [f for f in findings_for_prompt if f["index"] in kept_idxs]

        if not kept_for_stage1:
            per_school[nid] = {"sample_meta": s, "deduped": deduped,
                               "stage0_source": stage0_source,
                               "stage1_included": [], "stage1_excluded": [],
                               "narrative": None,
                               "note": "Stage 0 dropped all findings; nothing to triage."}
            continue

        # Stage 1 v2 call
        findings_json = json.dumps(kept_for_stage1, indent=2, default=str)
        user_msg = fill_user(s1_user_tmpl,
                             school_name=s["name"], district_name=s["district"],
                             nces_id=nid, findings=findings_json)
        resp = client.messages.create(
            model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
            system=s1_sys,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = next((b.text for b in resp.content if b.type == "text"), "")
        s1_input_tok += resp.usage.input_tokens
        s1_output_tok += resp.usage.output_tokens
        parsed = parse_json_response(raw) or {}
        included = parsed.get("included") or []
        excluded = parsed.get("excluded") or []
        per_school[nid] = {"sample_meta": s, "deduped": deduped,
                           "stage0_source": stage0_source,
                           "stage1_included": included, "stage1_excluded": excluded,
                           "kept_for_stage1": kept_for_stage1,
                           "narrative": None}
        time.sleep(1)
        print(f"  {nid}: stage0={stage0_source} stage1_v2_included={len(included)} "
              f"stage1_v2_excluded={len(excluded)}")

    # ---- Build Stage 2 v3 batch (only schools with ≥1 included) ----
    requests = []
    for nid, info in per_school.items():
        if "error" in info or not info.get("stage1_included"):
            continue
        # Enrich with source URLs
        deduped = info["deduped"]
        by_norm, by_prefix = {}, {}
        for f in deduped:
            n = _normalize_for_match(f.get("summary") or "")
            url = f.get("source_url") or ""
            if n and n not in by_norm:
                by_norm[n] = url
                by_prefix.setdefault(n[:100], url)
        enriched = []
        for f in info["stage1_included"]:
            ot = _normalize_for_match(f.get("original_text") or "")
            url = by_norm.get(ot) or by_prefix.get(ot[:100], "")
            cp = dict(f)
            cp["source_url"] = url or ""
            enriched.append(cp)
        info["enriched"] = enriched
        findings_json = json.dumps(enriched, indent=2, default=str)
        sm = info["sample_meta"]
        user_msg = fill_user(s2_user_tmpl,
                             school_name=sm["name"], district_name=sm["district"],
                             nces_id=nid, findings=findings_json)
        requests.append({
            "custom_id": nid,
            "params": {
                "model": SONNET_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": [{"type": "text", "text": s2_sys,
                            "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
                "messages": [{"role": "user", "content": user_msg}],
            },
        })

    print(f"\nSubmitting Stage 2 batch of {len(requests)} requests...")
    s2_input_tok = s2_output_tok = 0
    if requests:
        batch = client.messages.batches.create(requests=requests)
        bid = batch.id
        print(f"Batch ID: {bid}")
        time.sleep(8)  # let it index before retrieve (mitigate prior race)
        while True:
            b = client.messages.batches.retrieve(bid)
            rc = b.request_counts
            print(f"  status={b.processing_status} processing={rc.processing} "
                  f"succeeded={rc.succeeded} errored={rc.errored}")
            if b.processing_status == "ended":
                break
            time.sleep(15)
        for result in client.messages.batches.results(bid):
            nid = result.custom_id
            if result.result.type != "succeeded":
                per_school[nid]["narrative_error"] = str(getattr(result.result, "error", "?"))
                continue
            msg = result.result.message
            txt = next((b.text for b in msg.content if b.type == "text"), "")
            parsed = parse_json_response(txt)
            narrative = (parsed or {}).get("narrative") if parsed else None
            if not narrative:
                narrative = txt
            per_school[nid]["narrative"] = narrative
            s2_input_tok += msg.usage.input_tokens
            s2_output_tok += msg.usage.output_tokens

    # ---- Cost ----
    haiku_cost = (s0_input_tok + s1_input_tok) / 1e6 * HAIKU_IN \
                 + (s0_output_tok + s1_output_tok) / 1e6 * HAIKU_OUT
    sonnet_cost = s2_input_tok / 1e6 * SONNET_IN * BATCH_DISCOUNT \
                  + s2_output_tok / 1e6 * SONNET_OUT * BATCH_DISCOUNT
    total = haiku_cost + sonnet_cost
    print(f"\nHaiku: ${haiku_cost:.4f} (s0 in={s0_input_tok} out={s0_output_tok}; "
          f"s1 in={s1_input_tok} out={s1_output_tok})")
    print(f"Sonnet (batch): ${sonnet_cost:.4f} (in={s2_input_tok} out={s2_output_tok})")
    print(f"TOTAL: ${total:.4f}")

    # ---- Markdown ----
    md = []
    md.append("# Positive-Content Stage 1 v2 Test — 10 random schools")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Random seed:** 20260502 (`random.seed(20260502)` then `random.sample(pool, 10)`)")
    md.append(f"**Affected pool size:** re-derived from full 2,532-school scan; "
              f"schools whose raw Phase 4 findings contain a positive-content vocabulary match. "
              f"Excludes the 1 already-success school (Ruben Trejo Dual Language Academy).")
    md.append(f"**Stage 1 prompt:** `prompts/layer3_stage1_haiku_triage_v2.txt` (rule on "
              f"line 37 of v1 removed: positive findings now pass through to Stage 2).")
    md.append(f"**Stage 2 prompt:** `prompts/layer3_stage2_sonnet_narrative_v3.txt` "
              f"(unchanged from production).")
    md.append(f"**Total cost:** ${total:.4f} (Haiku ${haiku_cost:.4f} + Sonnet batch ${sonnet_cost:.4f})")
    md.append("")
    md.append("**MongoDB was NOT modified.** Production v3 narratives stay in place. "
              "These are experimental outputs for builder review.")
    md.append("")
    md.append("---")
    md.append("")
    for nid, info in sorted(per_school.items(),
                            key=lambda x: x[1]["sample_meta"]["name"]
                            if "sample_meta" in x[1] else "z"):
        sm = info.get("sample_meta", {})
        md.append(f"## {sm.get('name', nid)}")
        md.append("")
        md.append(f"**NCES:** `{nid}` &middot; **District:** {sm.get('district','?')}")
        md.append(f"**Prior production status:** `{sm.get('narrative_status','?')}` "
                  f"&middot; **Stage 0 source:** {info.get('stage0_source','?')}")
        if info.get("error"):
            md.append(f"**ERROR:** {info['error']}")
            md.append("---"); md.append(""); continue
        inc = info.get("stage1_included") or []
        exc = info.get("stage1_excluded") or []
        md.append(f"**Stage 1 v2 included:** {len(inc)} &middot; "
                  f"**Stage 1 v2 excluded:** {len(exc)}")
        md.append("")
        if not inc:
            note = info.get("note") or "Stage 1 v2 included zero findings — fallback narrative would apply."
            md.append(f"_{note}_")
            md.append("")
            md.append("---"); md.append(""); continue
        if info.get("narrative_error"):
            md.append(f"**Stage 2 ERROR:** {info['narrative_error']}")
            md.append("---"); md.append(""); continue
        narrative = info.get("narrative") or "(no narrative produced)"
        md.append("**Stage 1 v2 included findings (categories & themes):**")
        for f in inc:
            cat_idx = f.get("finding_index")
            theme = f.get("theme", "?")
            rationale = f.get("rationale", "?")
            md.append(f"- finding_index={cat_idx} theme={theme} rationale: {rationale}")
        md.append("")
        md.append("**Generated narrative (Stage 2 v3):**")
        md.append("")
        for para in narrative.split("\n\n"):
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
