# PURPOSE: Task 1 acceptance smoke test. Reruns the three-stage pipeline on 5 schools
#          from the validated 50-school set, USING THE EXTRACTED PROMPT FILES (not the
#          inline constants in run_round1.py), and writes a diff report against the
#          cached round1_three_stage output.
#
#          Byte-identity of prompt strings is already proven by
#          acceptance_test_prompt_extraction.py. This script is the live end-to-end
#          smoke test the builder asked for in the Phase 5 handoff. It is not
#          production code; it is validation infrastructure.
#
# NOTES ON BIT-IDENTITY OF NARRATIVES:
#   The Anthropic Claude API is stochastic at temperature>0 (the runner uses default
#   temperature, which is 1.0). Calling the API again with the same prompts WILL NOT
#   reproduce the exact narrative text, even though the prompt strings are byte-identical.
#   What we CAN compare deterministically:
#     - Stage 0 Python rule application (given Haiku's extraction, the rules are
#       deterministic). Haiku's extraction itself can vary slightly between runs, so
#       Stage 0 drop counts may differ at the margin — but typically match.
#     - Auto-check counts (hallucinations, student ID leaks, death-circumstance leaks,
#       gendered-student references, evaluative language, date-first formatting).
#       These should all stay at zero, matching the cached run.
#     - Overall narrative quality and structure (qualitative spot-check).
#
# INPUTS:
#   prompts/layer3_stage0_haiku_extraction_v1.txt
#   prompts/layer3_stage1_haiku_triage_v1.txt
#   prompts/layer3_stage2_sonnet_narrative_v1.txt
#   phases/phase-4.5/test_results/raw_responses/<nces_id>.json (cached findings_in)
#   phases/phase-4.5/test_results/round1_three_stage/<nces_id>.json (cached three-stage output)
# OUTPUTS:
#   phases/phase-5/smoke_test_output/<nces_id>.json — per-school full record
#   phases/phase-5/smoke_test_output/diff_report.md — comparison report
#
# COST: ~$0.08 across 5 schools. Same per-school cost as the 50-school replay (~$0.0165).

import os
import sys
import json
import re
import time
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
import anthropic
from pipeline.layer3_prompts import load_stage0, load_stage1, load_stage2, fill_user

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
RATE_LIMIT_SECONDS = 12

# Use the SAME cutoffs as the cached run (run_round1.py:50-53). This makes the Python
# rule application reproduce the cached Stage 0 decisions. Hardcoding is intentional.
TODAY = date(2026, 4, 29)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

RAW_RESPONSES_DIR = os.path.join(
    PROJECT_ROOT, "phases", "phase-4.5", "test_results", "raw_responses",
)
CACHED_3STAGE_DIR = os.path.join(
    PROJECT_ROOT, "phases", "phase-4.5", "test_results", "round1_three_stage",
)
OUTPUT_DIR = os.path.join(HERE, "smoke_test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 5 schools selected from the round1_three_stage replay. These were chosen to
# exercise distinct code paths (Stage 0 drop confirmed, district vs school-level
# attribution, varied finding counts). Each appears in the cached three-stage
# results, so we have a baseline for comparison.
SMOKE_SCHOOLS = [
    {"nces_id": "530033000043", "name": "Bainbridge High School"},          # 1985 lawsuit Stage 0 drop
    {"nces_id": "530033000044", "name": "Halilts Elementary School"},       # Bainbridge district-attribution
    {"nces_id": "530375001773", "name": "Echo Glen School"},                # Most complex (6 incl, 4 excl)
    {"nces_id": "530267000391", "name": "Cascade High School"},             # Standard 3 incl / 3 excl
    {"nces_id": "530375000579", "name": "Maywood Middle School"},           # 3 incl / 6 excl
]


# ============================================================
# HELPERS — minimal copies from run_round1.py for the acceptance test only.
# Production code will live in pipeline/layer3_pipeline.py once Phase 5 starts.
# ============================================================

def parse_json_response(raw_text):
    """Extract a JSON object from a raw model response, tolerating ```json fences."""
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
    """Convert a YYYY / YYYY-MM / YYYY-MM-DD string to a date, or None on failure."""
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


def all_checks(narrative, included_findings):
    nl = narrative.lower()
    incl_text = " ".join(f.get("original_text", "") for f in included_findings).lower()
    halluc = [p for p in HALLUCINATION_PHRASES if p in nl and p not in incl_text]
    sid = []
    for pat, label in STUDENT_ID_PATTERNS:
        for m in re.findall(pat, narrative, re.IGNORECASE):
            sid.append(f"{label}: '{m}'")
    death = [f"'{p}'" for p in DEATH_CIRC_PHRASES if p in nl]
    gen = []
    for pat in GENDERED_STUDENT_PATTERNS:
        for m in re.findall(pat, narrative, re.IGNORECASE):
            gen.append(" ".join(t for t in m if t) if isinstance(m, tuple) else str(m))
    eva = [p for p in EVALUATIVE_PHRASES if p in nl]
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", narrative))
    has_undated = bool(re.search(r"undated", narrative, re.IGNORECASE))
    if "No significant web-sourced context" in narrative:
        date_first = []
    elif not has_year and not has_undated:
        date_first = ["narrative has no year or 'undated' marker"]
    else:
        date_first = []
    return {
        "hallucinations": halluc, "student_id_leaks": sid, "death_circ": death,
        "gendered_student": gen, "evaluative": eva, "date_first": date_first,
    }


# ============================================================
# THREE STAGES — using LOADED prompts from prompts/
# ============================================================

# Load prompts ONCE at module level. fail-fast if anything is wrong.
S0_SYS, S0_USER_TMPL = load_stage0()
S1_SYS, S1_USER_TMPL = load_stage1()
S2_SYS, S2_USER_TMPL = load_stage2()


def stage0(api_client, findings_for_prompt):
    """Haiku structured extraction + Python rule application (conduct-date anchor + dismissed-case)."""
    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)
    user_msg = fill_user(S0_USER_TMPL, findings=findings_json)
    response = api_client.messages.create(
        model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
        system=S0_SYS,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "")
    usage = {"input_tokens": response.usage.input_tokens,
             "output_tokens": response.usage.output_tokens}
    parsed = parse_json_response(raw) or {}
    extractions = parsed.get("extractions", [])
    by_idx = {e.get("finding_index"): e for e in extractions if e.get("finding_index") is not None}

    # Apply Python rules (verbatim from run_round1.py:469-528).
    classifications = []
    for f in findings_for_prompt:
        idx = f["index"]
        ext = by_idx.get(idx, {})
        conduct_latest = parse_extracted_date(ext.get("conduct_date_latest"))
        response_dt = parse_extracted_date(ext.get("response_date"))
        rtype = (ext.get("response_type") or "unclear").lower().strip()
        tag = (ext.get("finding_type_tag") or "").strip().lower()
        classifications.append({
            "index": idx, "extraction": ext,
            "conduct_latest": conduct_latest, "response_dt": response_dt,
            "response_type": rtype, "tag": tag,
            "is_dismissed": rtype in DISMISSED_TYPES,
            "ancient_conduct": conduct_latest is not None and conduct_latest < CUTOFF_20YR,
        })
    pattern_eligible_tags = set()
    for c in classifications:
        if (not c["is_dismissed"] and c["conduct_latest"] is not None
                and c["conduct_latest"] >= CUTOFF_20YR and c["tag"]):
            pattern_eligible_tags.add(c["tag"])

    kept_indices = []
    dropped = []
    for c in classifications:
        idx = c["index"]
        ext = c["extraction"]
        if c["is_dismissed"]:
            if c["response_dt"] is not None and c["response_dt"] < CUTOFF_5YR:
                dropped.append({"finding_index": idx, "rule": "DISMISSED_CASE_OUT_OF_WINDOW",
                                "extraction": ext})
                continue
            kept_indices.append(idx); continue
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pattern_eligible_tags:
                kept_indices.append(idx); continue
            dropped.append({"finding_index": idx, "rule": "CONDUCT_DATE_ANCHOR",
                            "extraction": ext})
            continue
        kept_indices.append(idx)
    return kept_indices, dropped, by_idx, raw, usage


def stage1(api_client, school_name, district_name, nces_id, kept_findings):
    """Haiku triage on findings that survived Stage 0."""
    findings_json = json.dumps(kept_findings, indent=2, default=str)
    user_msg = fill_user(S1_USER_TMPL,
                         school_name=school_name, district_name=district_name,
                         nces_id=nces_id, findings=findings_json)
    response = api_client.messages.create(
        model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
        system=S1_SYS,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "")
    usage = {"input_tokens": response.usage.input_tokens,
             "output_tokens": response.usage.output_tokens}
    return parse_json_response(raw), raw, usage


def stage2(api_client, school_name, district_name, nces_id, included):
    """Sonnet 4.6 narrative writing on Stage 1 included findings."""
    if not included:
        msg = "No significant web-sourced context was found for this school."
        return ({"narrative": msg}, "", {"input_tokens": 0, "output_tokens": 0}, msg)
    findings_json = json.dumps(included, indent=2, default=str)
    user_msg = fill_user(S2_USER_TMPL,
                         school_name=school_name, district_name=district_name,
                         nces_id=nces_id, findings=findings_json)
    response = api_client.messages.create(
        model=SONNET_MODEL, max_tokens=MAX_TOKENS,
        system=S2_SYS,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "")
    usage = {"input_tokens": response.usage.input_tokens,
             "output_tokens": response.usage.output_tokens}
    parsed = parse_json_response(raw)
    narrative = parsed.get("narrative", "") if parsed else raw
    return parsed, raw, usage, narrative


# ============================================================
# RUN ONE SCHOOL
# ============================================================

def run_school(api_client, school):
    nces_id = school["nces_id"]
    name = school["name"]
    raw_path = os.path.join(RAW_RESPONSES_DIR, f"{nces_id}.json")
    with open(raw_path) as f:
        cached_raw = json.load(f)
    school_name = cached_raw.get("school_name", name)
    district_name = cached_raw.get("district_name", "")
    findings = cached_raw.get("findings_in", [])
    findings_for_prompt = []
    for i, f in enumerate(findings):
        findings_for_prompt.append({
            "index": i + 1,
            "category": f.get("category", "unknown"),
            "date": f.get("date") or "undated",
            "confidence": f.get("confidence", "unknown"),
            "sensitivity": f.get("sensitivity", "normal"),
            "summary": f.get("summary", "No summary"),
        })

    kept, dropped, extractions, s0_raw, s0_usage = stage0(api_client, findings_for_prompt)
    kept_for_prompt = [f for f in findings_for_prompt if f["index"] in kept]
    time.sleep(RATE_LIMIT_SECONDS)

    s1_parsed, s1_raw, s1_usage = stage1(
        api_client, school_name, district_name, nces_id, kept_for_prompt
    )
    included = (s1_parsed or {}).get("included", [])
    excluded = (s1_parsed or {}).get("excluded", [])
    time.sleep(RATE_LIMIT_SECONDS)

    s2_parsed, s2_raw, s2_usage, narrative = stage2(
        api_client, school_name, district_name, nces_id, included
    )

    checks_new = all_checks(narrative, included)

    return {
        "nces_id": nces_id, "name": school_name, "district_name": district_name,
        "findings_count": len(findings),
        "stage0": {"kept_count": len(kept), "dropped": dropped,
                   "extractions": extractions, "usage": s0_usage},
        "stage1": {"included_count": len(included), "excluded_count": len(excluded),
                   "usage": s1_usage},
        "stage2": {"narrative": narrative, "usage": s2_usage},
        "checks": checks_new,
    }


# ============================================================
# DIFF AGAINST CACHED
# ============================================================

def diff_against_cached(new_record, nces_id):
    """Compare key structural properties against the cached round1_three_stage record."""
    cached_path = os.path.join(CACHED_3STAGE_DIR, f"{nces_id}.json")
    with open(cached_path) as f:
        cached = json.load(f)

    # Stage 0 drop comparison
    cached_dropped_rules = sorted([d["rule"] for d in cached.get("stage0", {}).get("dropped", [])])
    new_dropped_rules = sorted([d["rule"] for d in new_record["stage0"]["dropped"]])
    cached_drop_indices = sorted([d["finding_index"] for d in cached.get("stage0", {}).get("dropped", [])])
    new_drop_indices = sorted([d["finding_index"] for d in new_record["stage0"]["dropped"]])

    # Stage 1 include/exclude counts
    cached_s1_inc = cached.get("stage1", {}).get("included_count", 0)
    cached_s1_exc = cached.get("stage1", {}).get("excluded_count", 0)
    new_s1_inc = new_record["stage1"]["included_count"]
    new_s1_exc = new_record["stage1"]["excluded_count"]

    # Auto-checks — both should be all-zero
    cached_checks_pass = all(not v for v in cached.get("checks_new", {}).values())
    new_checks_pass = all(not v for v in new_record["checks"].values())

    return {
        "stage0_drops_match_rules": cached_dropped_rules == new_dropped_rules,
        "stage0_drops_match_indices": cached_drop_indices == new_drop_indices,
        "cached_stage0_dropped_indices": cached_drop_indices,
        "new_stage0_dropped_indices": new_drop_indices,
        "stage1_included_delta": new_s1_inc - cached_s1_inc,
        "stage1_excluded_delta": new_s1_exc - cached_s1_exc,
        "cached_s1_inc": cached_s1_inc, "cached_s1_exc": cached_s1_exc,
        "new_s1_inc": new_s1_inc, "new_s1_exc": new_s1_exc,
        "cached_checks_all_zero": cached_checks_pass,
        "new_checks_all_zero": new_checks_pass,
        "new_check_violations": {k: v for k, v in new_record["checks"].items() if v},
        "narrative_byte_identical": cached.get("stage2", {}).get("narrative", "") ==
                                    new_record["stage2"]["narrative"],
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Smoke test — 5 schools through Layer 3 with extracted prompts")
    print(f"Cutoffs: today={TODAY.isoformat()}, 20yr={CUTOFF_20YR.isoformat()}, 5yr={CUTOFF_5YR.isoformat()}")
    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    results = {}
    diffs = {}
    total_haiku_in = total_haiku_out = total_sonnet_in = total_sonnet_out = 0

    for i, school in enumerate(SMOKE_SCHOOLS):
        nid = school["nces_id"]; name = school["name"]
        print(f"\n[{i+1}/{len(SMOKE_SCHOOLS)}] {name} ({nid})")
        try:
            r = run_school(api_client, school)
        except Exception as e:
            print(f"  EXCEPTION: {type(e).__name__}: {e}")
            results[nid] = {"error": f"{type(e).__name__}: {e}"}
            continue
        out_path = os.path.join(OUTPUT_DIR, f"{nid}.json")
        with open(out_path, "w") as f:
            json.dump(r, f, indent=2, default=str)
        results[nid] = r
        diffs[nid] = diff_against_cached(r, nid)
        s0d = len(r["stage0"]["dropped"]); s1i = r["stage1"]["included_count"]; s1e = r["stage1"]["excluded_count"]
        total_haiku_in += r["stage0"]["usage"]["input_tokens"] + r["stage1"]["usage"]["input_tokens"]
        total_haiku_out += r["stage0"]["usage"]["output_tokens"] + r["stage1"]["usage"]["output_tokens"]
        total_sonnet_in += r["stage2"]["usage"]["input_tokens"]
        total_sonnet_out += r["stage2"]["usage"]["output_tokens"]
        d = diffs[nid]
        print(f"  Stage 0: kept={r['stage0']['kept_count']} dropped={s0d} | rules_match={d['stage0_drops_match_rules']}")
        print(f"  Stage 1: incl={s1i} excl={s1e} (cached: incl={d['cached_s1_inc']} excl={d['cached_s1_exc']})")
        print(f"  Stage 2 auto-checks all-zero: {d['new_checks_all_zero']}")
        if i < len(SMOKE_SCHOOLS) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    # Cost
    haiku_cost = (total_haiku_in / 1e6) * 0.80 + (total_haiku_out / 1e6) * 4.0
    sonnet_cost = (total_sonnet_in / 1e6) * 3.0 + (total_sonnet_out / 1e6) * 15.0

    # Diff report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_path = os.path.join(OUTPUT_DIR, f"diff_report_{timestamp}.md")
    lines = []
    lines.append("# Phase 5 Task 1 Smoke Test — 5-School Diff Report")
    lines.append(f"\n**Run:** {timestamp}")
    lines.append(f"**Cutoffs:** today={TODAY.isoformat()}, 20yr={CUTOFF_20YR.isoformat()}, 5yr={CUTOFF_5YR.isoformat()}")
    lines.append(f"**Models:** {HAIKU_MODEL} (Stage 0+1), {SONNET_MODEL} (Stage 2)")
    lines.append(f"**Cost:** Haiku ${haiku_cost:.4f} ({total_haiku_in:,} in / {total_haiku_out:,} out), "
                 f"Sonnet ${sonnet_cost:.4f} ({total_sonnet_in:,} in / {total_sonnet_out:,} out), "
                 f"**Total: ${haiku_cost + sonnet_cost:.4f}**")
    lines.append("")
    lines.append("Note: narratives are NOT expected to be byte-identical to cached output. The Anthropic API")
    lines.append("is stochastic at temperature>0; same prompts produce same distribution, not same string.")
    lines.append("Byte-identity of prompts is proven in acceptance_test_prompt_extraction.py.")
    lines.append("")
    lines.append("## Per-school diff")
    lines.append("")
    for nid, r in results.items():
        if "error" in r:
            lines.append(f"### {nid} — ERROR: {r['error']}\n")
            continue
        d = diffs[nid]
        lines.append(f"### {r['name']} ({nid})")
        lines.append(f"- Stage 0 drops match rules: **{d['stage0_drops_match_rules']}** "
                     f"(new: {d['new_stage0_dropped_indices']}, cached: {d['cached_stage0_dropped_indices']})")
        lines.append(f"- Stage 0 drops match finding indices: **{d['stage0_drops_match_indices']}**")
        lines.append(f"- Stage 1 included delta: {d['stage1_included_delta']:+d} "
                     f"(new {d['new_s1_inc']} vs cached {d['cached_s1_inc']})")
        lines.append(f"- Stage 1 excluded delta: {d['stage1_excluded_delta']:+d} "
                     f"(new {d['new_s1_exc']} vs cached {d['cached_s1_exc']})")
        lines.append(f"- Auto-checks all-zero (new): **{d['new_checks_all_zero']}**, "
                     f"cached: **{d['cached_checks_all_zero']}**")
        if d["new_check_violations"]:
            lines.append(f"  - Violations: {d['new_check_violations']}")
        lines.append(f"- Narrative byte-identical to cached: {d['narrative_byte_identical']} "
                     f"(expected False — LLM stochasticity)")
        lines.append("")
        lines.append("**New narrative:**")
        for para in r["stage2"]["narrative"].split("\n\n"):
            p = para.strip()
            if p:
                lines.append(f"> {p}\n>")
        lines.append("")

    # Pass/fail summary
    all_drops_match = all(d["stage0_drops_match_rules"] for d in diffs.values())
    all_checks_clean = all(d["new_checks_all_zero"] for d in diffs.values())
    lines.append("## Summary")
    lines.append(f"- Stage 0 drop rules match cached for all 5 schools: **{all_drops_match}**")
    lines.append(f"- Auto-checks all-zero across all 5 schools: **{all_checks_clean}**")
    lines.append(f"- Total cost: **${haiku_cost + sonnet_cost:.4f}**")
    if all_drops_match and all_checks_clean:
        lines.append("\n**SMOKE TEST: PASS.** Loaded prompts produce expected behavior.")
    else:
        lines.append("\n**SMOKE TEST: NEEDS REVIEW.** See per-school deltas.")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\nReport saved: {report_path}")
    print(f"Total cost: ${haiku_cost + sonnet_cost:.4f}")
    print(f"All Stage 0 drop rules match: {all_drops_match}")
    print(f"All auto-checks clean: {all_checks_clean}")
    return 0 if (all_drops_match and all_checks_clean) else 1


if __name__ == "__main__":
    sys.exit(main())
