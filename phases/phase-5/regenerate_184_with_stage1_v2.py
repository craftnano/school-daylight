# PURPOSE: Regenerate Layer 3 narratives for the schools whose positive Phase 4
#          findings were filtered out by the v1 Stage 1 line-37 rule. The rule was
#          retired permanently 2026-05-02; v2 is now canonical. This runner re-derives
#          the affected pool, runs Stage 1 v2 + Stage 2 v3 on each school, and writes
#          the new layer3_narrative back to MongoDB (overwriting prior production).
#
# Schools NOT in the affected pool (1,862 production v3 narratives + 670 fallbacks)
# are left untouched.
#
# OUTPUT (filesystem):
#   - phases/phase-5/regen_184_run_log.txt
#   - phases/phase-5/regen_184_results.jsonl  (per-school disposition)
#
# COST: ~$3 expected. Hard cap $5 (script aborts before submitting batch if projection exceeds).

import os, sys, re, json, time, random
from datetime import date, datetime, timezone
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
import anthropic
from pymongo import MongoClient

from pipeline.layer3_prompts import (load_stage0, load_stage1,
                                     load_stage2_v3, fill_user)
from pipeline.layer3_findings import get_findings_for_stage0

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
STAGE1_VERSION = "layer3_v2"
STAGE2_VERSION = "layer3_v3"
PROMPT_VERSION = "layer3_v3"  # narrative payload prompt_version stays v3 (the Stage 2 prompt)
MAX_TOKENS = 2200

HAIKU_IN, HAIKU_OUT = 1.00, 5.00
SONNET_IN, SONNET_OUT = 3.00, 15.00
BATCH_DISCOUNT = 0.5
HARD_CAP_USD = 5.00

TODAY = date(2026, 5, 2)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

RUN_DIR = os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run")
STAGE1_PATH = os.path.join(RUN_DIR, "stage1_results.jsonl")
LOG_PATH = os.path.join(PROJECT_ROOT, "phases", "phase-5", "regen_184_run_log.txt")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "phases", "phase-5", "regen_184_results.jsonl")

# Same vocabulary as positive_content_diagnostic.py
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
EXCLUDE_NIDS = {"530825003912"}  # the 1 already-success school

_CITE_RE = re.compile(r"</?cite[^>]*>", re.IGNORECASE)


def _normalize(s):
    if not s:
        return ""
    s = _CITE_RE.sub("", s)
    return " ".join(s.split())


def has_positive_match(text):
    if not text:
        return False
    return any(rx.search(text) for _, rx in COMPILED)


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


def log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def stage0_call(client, s0_sys, s0_user_tmpl, findings_for_prompt):
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
            kept.append(idx); continue
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pat_eligible:
                kept.append(idx); continue
            dropped.append({"finding_index": idx, "rule": "CONDUCT_DATE_ANCHOR"})
            continue
        kept.append(idx)
    return kept, dropped, response.usage.input_tokens, response.usage.output_tokens


def main():
    log("=== Regeneration of 184 affected schools — Stage 1 v2 + Stage 2 v3 ===")
    s0_sys, s0_user_tmpl = load_stage0()
    s1_sys, s1_user_tmpl = load_stage1()  # canonical = v2 now
    s2_sys, s2_user_tmpl = load_stage2_v3()

    db = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000).get_default_database()
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Re-derive affected pool — full population scan, same logic as the v1 test.
    log("Re-deriving affected pool from full population scan...")
    affected = []
    for doc in db.schools.find({}, {"_id": 1, "name": 1, "district.name": 1,
                                    "context": 1, "district_context": 1,
                                    "layer3_narrative.status": 1,
                                    "layer3_narrative.text": 1}):
        nid = doc["_id"]
        if nid in EXCLUDE_NIDS:
            continue
        all_findings = (doc.get("context") or {}).get("findings") or []
        all_findings = all_findings + ((doc.get("district_context") or {}).get("findings") or [])
        match_in_raw = any(has_positive_match(f.get("summary") or "") for f in all_findings)
        if not match_in_raw:
            continue
        # Already-in-final-narrative? Compare against current text just to be safe.
        narr_text = ((doc.get("layer3_narrative") or {}).get("text") or "")
        # Skip if narrative ALREADY contains all matched vocabulary AND prior status=ok.
        # Simpler: include all schools where raw has a positive match — v2 will redo
        # the triage and the resulting narrative will be the new authoritative one.
        affected.append({
            "nces_id": nid, "name": doc.get("name", "?"),
            "district": (doc.get("district") or {}).get("name", "?"),
            "narrative_status": ((doc.get("layer3_narrative") or {}).get("status") or "?"),
        })
    log(f"Affected pool size: {len(affected)} schools")

    # Cached stage1 lookup (for stage0_dropped indices)
    stage1_cache = {}
    with open(STAGE1_PATH) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            stage1_cache[rec["nces_id"]] = rec

    # ---- Stage 0 (cached or fresh) + Stage 1 v2 ----
    s0_in = s0_out = 0
    s1_in = s1_out = 0
    per_school = {}
    n_processed = 0
    for s in affected:
        nid = s["nces_id"]
        n_processed += 1
        try:
            deduped, _ = get_findings_for_stage0(db, nid)
        except Exception as e:
            log(f"  {nid}: findings query failed: {e}")
            per_school[nid] = {"sample_meta": s, "error": f"findings_query: {e}"}
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

        cached = stage1_cache.get(nid)
        if cached:
            dropped_idxs = {d["finding_index"] for d in cached.get("stage0_dropped", [])}
            kept_idxs = [f["index"] for f in findings_for_prompt
                         if f["index"] not in dropped_idxs]
            s0_source = "cached"
        else:
            try:
                kept_idxs, _drops, ti, to = stage0_call(client, s0_sys, s0_user_tmpl,
                                                        findings_for_prompt)
            except Exception as e:
                log(f"  {nid}: stage0 fresh call failed: {e}")
                per_school[nid] = {"sample_meta": s, "error": f"stage0: {e}"}
                continue
            s0_in += ti; s0_out += to
            s0_source = "fresh_haiku"
        kept_for_stage1 = [f for f in findings_for_prompt if f["index"] in kept_idxs]
        if not kept_for_stage1:
            per_school[nid] = {"sample_meta": s, "deduped": deduped,
                               "stage0_source": s0_source,
                               "stage1_included": [], "stage1_excluded": [],
                               "note": "Stage 0 dropped all findings."}
            continue

        # Stage 1 v2 (canonical now)
        findings_json = json.dumps(kept_for_stage1, indent=2, default=str)
        user_msg = fill_user(s1_user_tmpl,
                             school_name=s["name"], district_name=s["district"],
                             nces_id=nid, findings=findings_json)
        try:
            resp = client.messages.create(
                model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
                system=s1_sys,
                messages=[{"role": "user", "content": user_msg}],
            )
        except Exception as e:
            log(f"  {nid}: stage1 v2 call failed: {e}")
            per_school[nid] = {"sample_meta": s, "error": f"stage1: {e}"}
            continue
        raw = next((b.text for b in resp.content if b.type == "text"), "")
        s1_in += resp.usage.input_tokens
        s1_out += resp.usage.output_tokens
        parsed = parse_json_response(raw) or {}
        included = parsed.get("included") or []
        excluded = parsed.get("excluded") or []
        per_school[nid] = {"sample_meta": s, "deduped": deduped,
                           "stage0_source": s0_source,
                           "stage1_included": included, "stage1_excluded": excluded}

        if n_processed % 25 == 0:
            running_haiku = (s0_in + s1_in) / 1e6 * HAIKU_IN \
                            + (s0_out + s1_out) / 1e6 * HAIKU_OUT
            log(f"  ... {n_processed}/{len(affected)} processed, "
                f"haiku running ${running_haiku:.4f}")
        time.sleep(0.5)

    haiku_cost = (s0_in + s1_in) / 1e6 * HAIKU_IN + (s0_out + s1_out) / 1e6 * HAIKU_OUT
    log(f"Stage 1 v2 pass complete. Haiku spend: ${haiku_cost:.4f}")

    # ---- Build Stage 2 v3 batch ----
    requests = []
    for nid, info in per_school.items():
        if info.get("error") or not info.get("stage1_included"):
            continue
        deduped = info["deduped"]
        by_norm, by_prefix = {}, {}
        for f in deduped:
            n = _normalize(f.get("summary") or "")
            url = f.get("source_url") or ""
            if n and n not in by_norm:
                by_norm[n] = url
                by_prefix.setdefault(n[:100], url)
        enriched = []
        for f in info["stage1_included"]:
            ot = _normalize(f.get("original_text") or "")
            url = by_norm.get(ot) or by_prefix.get(ot[:100], "")
            cp = dict(f); cp["source_url"] = url or ""
            enriched.append(cp)
        info["enriched"] = enriched
        sm = info["sample_meta"]
        findings_json = json.dumps(enriched, indent=2, default=str)
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

    # Cost projection check
    proj_sonnet = len(requests) * 0.012
    if haiku_cost + proj_sonnet > HARD_CAP_USD:
        log(f"COST CAP HIT: ${haiku_cost+proj_sonnet:.4f} > ${HARD_CAP_USD}. Aborting before submit.")
        return 1
    log(f"Submitting Stage 2 batch of {len(requests)} requests "
        f"(projected sonnet ${proj_sonnet:.2f})...")
    s2_in = s2_out = 0
    n_succeeded = n_errored = 0
    if requests:
        batch = client.messages.batches.create(requests=requests)
        bid = batch.id
        log(f"Batch ID: {bid}")
        time.sleep(8)
        while True:
            b = client.messages.batches.retrieve(bid)
            rc = b.request_counts
            log(f"  status={b.processing_status} processing={rc.processing} "
                f"succeeded={rc.succeeded} errored={rc.errored}")
            if b.processing_status == "ended":
                break
            time.sleep(20)
        for result in client.messages.batches.results(bid):
            nid = result.custom_id
            info = per_school[nid]
            sm = info["sample_meta"]
            if result.result.type != "succeeded":
                err = str(getattr(result.result, "error", "?"))
                info["narrative_error"] = err
                n_errored += 1
                continue
            msg = result.result.message
            txt = next((b.text for b in msg.content if b.type == "text"), "")
            parsed = parse_json_response(txt)
            narrative = (parsed or {}).get("narrative") if parsed else None
            if not narrative:
                narrative = txt
            info["narrative"] = narrative
            s2_in += msg.usage.input_tokens
            s2_out += msg.usage.output_tokens
            n_succeeded += 1

            # Write to MongoDB — overwrite layer3_narrative for this school.
            db.schools.update_one({"_id": nid}, {"$set": {"layer3_narrative": {
                "text": narrative,
                "model": SONNET_MODEL,
                "source_findings_count": len(info["deduped"]),
                "stage1_included_count": len(info["stage1_included"]),
                "stage1_excluded_count": len(info["stage1_excluded"]),
                "stage0_dropped_count": (len(info["deduped"])
                                         - len([f for f in info["deduped"]
                                                if any(s["index"] == ix
                                                       for ix in [])])),  # not tracked here
                "status": "ok",
                "error": None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_version": PROMPT_VERSION,           # Stage 2 = layer3_v3
                "stage1_prompt_version": STAGE1_VERSION,    # Stage 1 = layer3_v2
                "regenerated_2026_05_02": True,
            }}})

    sonnet_cost = s2_in / 1e6 * SONNET_IN * BATCH_DISCOUNT + s2_out / 1e6 * SONNET_OUT * BATCH_DISCOUNT
    total_cost = haiku_cost + sonnet_cost

    # Schools where Stage 1 v2 still filtered everything out (no narrative regenerated)
    n_zero = sum(1 for i in per_school.values()
                 if not i.get("error") and not i.get("stage1_included"))
    n_with_narrative = n_succeeded
    n_errored_total = sum(1 for i in per_school.values() if i.get("error")) + n_errored

    # Detect schools whose new narrative contains positive content
    n_now_has_positive = 0
    for nid, info in per_school.items():
        narr = info.get("narrative") or ""
        if narr and has_positive_match(narr):
            n_now_has_positive += 1

    # Per-school results JSONL
    if os.path.exists(RESULTS_PATH):
        os.remove(RESULTS_PATH)
    with open(RESULTS_PATH, "w") as f:
        for nid, info in per_school.items():
            sm = info["sample_meta"]
            row = {
                "nces_id": nid,
                "name": sm.get("name"),
                "district": sm.get("district"),
                "prior_status": sm.get("narrative_status"),
                "stage0_source": info.get("stage0_source"),
                "stage1_v2_included": len(info.get("stage1_included") or []),
                "stage1_v2_excluded": len(info.get("stage1_excluded") or []),
                "narrative_written": bool(info.get("narrative")),
                "narrative_has_positive": has_positive_match(info.get("narrative") or ""),
                "error": info.get("error") or info.get("narrative_error"),
            }
            f.write(json.dumps(row, default=str) + "\n")

    log("")
    log("=== REGENERATION COMPLETE ===")
    log(f"Schools in affected pool:                {len(affected)}")
    log(f"Schools regenerated (Stage 2 succeeded): {n_with_narrative}")
    log(f"Schools where Stage 1 v2 included zero:  {n_zero}")
    log(f"Schools with errors:                     {n_errored_total}")
    log(f"Regenerated narratives that now contain positive content: {n_now_has_positive}")
    log(f"Haiku cost:  ${haiku_cost:.4f}")
    log(f"Sonnet cost: ${sonnet_cost:.4f}")
    log(f"TOTAL COST:  ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
