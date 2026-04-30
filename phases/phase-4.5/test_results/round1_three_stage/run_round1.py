# PURPOSE: Round 1 50-school replay through the three-stage pipeline.
#   Stage 0: Haiku structured extraction → Python conduct-date anchor + dismissed-case rules
#   Stage 1: Haiku triage on surviving findings
#   Stage 2: Sonnet 4.6 narrative on Stage 1 included findings
#
# INPUTS:
#   tests/sonnet_test_config.yaml — the restored 50-school list with test assignments
#   phases/phase-4.5/test_results/raw_responses/<nces_id>.json — Round 1 cached findings + narratives
#
# OUTPUTS:
#   phases/phase-4.5/test_results/round1_three_stage/<nces_id>.json — per-school full record
#   phases/phase-4.5/test_results/round1_three_stage/summary.json — totals + per-school summary
#   phases/phase-4.5/test_results/round1_three_stage/report_<timestamp>.md — Round-1-formatted
#       Markdown report organized by the 14 tests, with regressions called out inline.
#
# REGRESSION DEFINITION:
#   A regression is when an automated check passed under the Round 1 narrative but fails under
#   the new narrative. Formal categories tracked:
#     - new hallucination phrase that was not in Round 1
#     - new student ID leak that was not in Round 1
#     - new death-circumstance phrase that was not in Round 1
#     - new gendered-student reference that was not in Round 1
#     - missing date-first formatting (Round 1 had years; new run does not)
#     - new evaluative-language phrase that was not in Round 1
#   Improvements (Round 1 had X violation, new run does not) are reported but NOT regressions.
#
# DOES NOT: Modify MongoDB, pipeline output, prompts in prompts/, or prior test results.

import os
import sys
import json
import re
import time
import yaml
from datetime import datetime, date
import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import config

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
RATE_LIMIT_SECONDS = 12
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_RESPONSES_DIR = os.path.join(config.PROJECT_ROOT, "phases", "phase-4.5", "test_results", "raw_responses")
CONFIG_PATH = os.path.join(config.PROJECT_ROOT, "tests", "sonnet_test_config.yaml")

# Pre-filter cutoffs — fixed for reproducibility
TODAY = date(2026, 4, 29)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)  # 2006-04-29
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)    # 2021-04-29
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

TEST_NAMES = {
    1: "Death/Suicide Suppression",
    2: "Name Stripping + Pattern Detection",
    3: "Private Citizen Exclusion",
    4: "Exoneration Handling",
    5: "Date-First Formatting",
    6: "Politically Sensitive Neutrality",
    7: "Student Name Suppression",
    8: "Duplicate / Same-Saga Consolidation",
    9: "Geographic Proximity != Relevance",
    11: "Recency Policy",
    12: "Parent Relevance Filter",
    13: "Community Action — Source Quality",
    14: "Excluded Schools Still Get Findings",
}


# ============================================================
# PROMPTS — copies of the Stage 0/1/2 prompts validated in run_six_schools.py
# ============================================================

STAGE0_PROMPT = """You are a structured-extraction assistant for school finding analysis. Your ONLY job is to extract dates and a type tag from each finding. Do NOT make inclusion or exclusion decisions. Do NOT apply editorial rules. The downstream code applies the rules; you only report what the text says.

For each finding, output:

- conduct_date_earliest: Earliest date the underlying conduct/behavior occurred. The conduct is the alleged or actual behavior the finding is about — the abuse, the bullying, the cyber attack, the misconduct — NOT the lawsuit or settlement. Format: YYYY, YYYY-MM, or YYYY-MM-DD. If only an approximate description is given (e.g., "approximately four decades ago" relative to a 2024 filing → ~1984), compute the implied year and note the inference in rationale. Output null if genuinely not stated.

- conduct_date_latest: Latest date the underlying conduct occurred. Same format. If conduct was a single event, equal to earliest. Output null if not stated.

- response_date: Date of the institutional response — the lawsuit filing, settlement, verdict, investigation start, dismissal, or other formal action by the school/district/legal system. This is distinct from when the conduct occurred. If multiple response actions are mentioned, use the most recent. Output null if not stated.

- response_type: One of:
  * lawsuit_filing — a complaint was filed
  * settlement — money paid to settle a claim
  * verdict — court ruling against (or in favor of) one side
  * investigation — investigation opened or ongoing
  * dismissal — case dismissed by court
  * withdrawal — claim withdrawn by plaintiff
  * resolution_without_finding — concluded with no adverse determination (exoneration, cleared, etc.)
  * conviction — criminal conviction
  * policy_change — institutional policy change
  * other — anything else (resignation, leave, award, etc.)
  * unclear — cannot tell from the text

- finding_type_tag: A short snake_case slug describing the type of underlying issue, used for pattern matching across findings within a school. Use a consistent vocabulary. Examples:
  * sexual_abuse_by_staff
  * sexual_abuse_by_student
  * bullying_failure_to_protect
  * racial_discrimination
  * disability_discrimination
  * antisemitism_complaint
  * cybersecurity_breach
  * leadership_misconduct
  * financial_emergency
  * gun_on_premises
  * student_death_negligence
  * civil_rights_complaint
  * staff_misconduct_other
  * positive_recognition (for awards/recognitions)
  * routine_governance (for routine appointments, policy announcements)

- rationale: One sentence describing how you extracted these fields. If you inferred a date from approximate language, say so.

OUTPUT FORMAT:
```json
{
  "extractions": [
    {
      "finding_index": 1,
      "conduct_date_earliest": "1984 or null",
      "conduct_date_latest": "1986 or null",
      "response_date": "2024-12-18 or null",
      "response_type": "lawsuit_filing",
      "finding_type_tag": "sexual_abuse_by_staff",
      "rationale": "Lawsuit filed 2024-12-18 alleges abuse 'approximately four decades ago' → ~1984-1986."
    }
  ]
}
```

Return one extraction object per finding. The finding_index must match the input."""

STAGE1_PROMPT = """You are a finding triage assistant for school briefings. Your job is to evaluate each finding and decide whether it should be included in or excluded from a parent-facing narrative.

## RECENCY RULES — Apply to every finding

- Adverse outcomes (settlements, convictions, sustained investigations): include only if within 10 years
- Allegations, dismissals, unresolved matters: include only if within 5 years
- PATTERN EXCEPTION: If 2+ findings of the same type (e.g., sexual abuse settlements, failure-to-report cases) exist within a 20-year window, ALL findings in the pattern stay. The pattern is the finding.
- SEVERITY EXCEPTION: If a finding involves credible allegations of sexual violence against students AND institutional suppression of reporting or investigation (e.g., administrators discouraging police involvement, failure to notify authorities), the finding may be included beyond the standard 10-year window even without a pattern match. The combination of severity and institutional complicity makes these findings relevant to current school culture regardless of age.

NOTE: The conduct-date anchor and dismissed-case rules have already been applied by an upstream pre-filter. You do not need to re-apply them. Findings reaching you have already passed those checks.

## ADDITIONAL EXCLUSION RULES

- Private citizens (candidates, volunteers, parents, former students with no institutional role): exclude
- Events with no institutional connection (geographic proximity only): exclude
- Exonerated findings (cleared, charges dropped, acquitted): exclude entirely
- Individual student conduct (unless it triggered institutional response): exclude

## POSITIVE FINDINGS

- Awards, recognitions, and positive achievements: exclude unless directly relevant to an adverse finding (e.g., an award that was later revoked, a program cited in a lawsuit).
- Routine leadership appointments, board governance, policy announcements: exclude.

## YOUR TASK

For each finding below, output:
1. "include" or "exclude"
2. A one-line rule citation explaining why
3. For INCLUDED findings: a theme tag — one of: safety, legal, governance, academic, community_investment

## CRITICAL INSTRUCTION — FACTUAL PASS-THROUGH ONLY

For every included finding, you must pass through ONLY the facts explicitly stated in the finding text. Specifically:
- Do NOT add any outcome, resolution, or disposition that is not explicitly stated in the finding text.
- If a finding describes an allegation but does not state a resolution, pass it through WITHOUT a resolution.
- Do NOT infer, assume, or add what happened after the events described.
- Do NOT add context from your own knowledge about the case, the people involved, or the outcome.
- The original finding text must be passed through UNCHANGED.
- ALWAYS emit the finding's `date` from the input metadata in your output, even if the date is not mentioned in the summary text. If the input date is missing or "undated," output "undated." The downstream narrative writer needs the date to lead every finding with a year — do not drop it.

## OUTPUT FORMAT

Return a JSON object with two arrays:
```json
{
  "included": [
    {
      "finding_index": 1,
      "original_text": "the exact finding text, unchanged",
      "date": "YYYY or YYYY-MM-DD from input metadata, or 'undated'",
      "theme": "safety|legal|governance|academic|community_investment",
      "rationale": "one-line rule citation for inclusion"
    }
  ],
  "excluded": [
    {
      "finding_index": 2,
      "rationale": "one-line rule citation for exclusion"
    }
  ]
}
```"""

STAGE2_PROMPT = """You are writing the web-sourced context section of a school briefing for parents. You will receive pre-triaged findings that have already passed editorial review. Your ONLY job is to write the narrative. Do not re-evaluate inclusion decisions.

## WRITING RULES

1. **Date-first:** Every finding must lead with the year. "In 2024, ..." or "In an undated report, ..."
2. **No individual names:** Use role descriptions only. "a teacher," "the principal," "the superintendent." Never output any person's name.
3. **No student names or identifiers:** Students are "a student," "a freshman," "several students." Nothing more specific. Do not include age, disability status, or any combination of descriptors that could identify a specific student. "An 18-year-old special needs student" is too specific — use "a student" instead.
4. **Death-related institutional responses:** When a finding involves a death, reference ONLY the institutional response — the lawsuit, settlement, investigation, or policy change and its outcome. Do NOT include any of the following, even if present in the source: manner of death (suicide, overdose, drowning, hanging, shooting, starvation, etc.); location of death — neither specific ("wooded area at the end of school property," "in the gymnasium") nor general ("on school grounds," "at the school," "near campus"); physical circumstances (time of day, what was found, who found them, what was used). Frame only around what the institution did, what it failed to do, or how it was held accountable. A reader should learn that there was litigation or an investigation, not how the death occurred.
5. **Consolidate related findings:** Multiple findings from the same incident or ongoing story should be woven into one paragraph. Present connected events as a single narrative thread in chronological order. Do not list them as separate items.
6. **Neutral tone:** No evaluative language ("controversial," "divisive," "progressive," "conservative"). Pure factual reporting.
7. **District-level vs. building-specific attribution:** Lawsuits, settlements, and investigations against the district appear on all schools in the district, framed with "at the district level" or equivalent (vary the phrasing across paragraphs — do not repeat the same framing phrase). Building-specific incidents (events that occurred at a particular school) appear only on that school's briefing. When you receive a finding, treat it as district-level if it names the district as the actor or defendant; treat it as building-specific only if it names a specific school as the locus of the incident.
8. **Vary transitions:** Use different opening phrases across paragraphs. Do not start multiple paragraphs the same way.
9. **Gender-neutral student references:** Neutralize gendered language whenever it refers to a student. Replace "his daughter," "her son," "she," "he" with gender-neutral forms ("the student," "their child," "they") in any context where a student is the subject. Source text often retains gendered pronouns; do not pass them through. This prevents identification through demographic narrowing. Gendered pronouns for adults in institutional roles (teachers, administrators) are also disallowed under Rule 2 — use the role title instead.

## CRITICAL RULE — NO FABRICATION

Write ONLY using facts present in the provided findings. Specifically:
- Do NOT add any outcomes, resolutions, consequences, or follow-up actions that are not stated in the findings.
- If a finding describes an allegation with no stated resolution, present it as an allegation with no resolution. Do not invent what happened next.
- If a finding does not mention a person being placed on leave, cleared, fired, or any other outcome — do not add that information.
- You have no knowledge beyond what is provided. Act accordingly.

## OUTPUT FORMAT

Return JSON:
```json
{
  "narrative": "Your prose paragraphs here.",
  "findings_used": ["brief identifier for each finding used"],
  "names_stripped": ["role description used for each named individual"]
}
```"""


# ============================================================
# HELPERS
# ============================================================

def parse_json_response(raw_text):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
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


def load_cached(nces_id):
    path = os.path.join(RAW_RESPONSES_DIR, f"{nces_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def round1_narrative(cached):
    """Extract the Round 1 single-stage narrative from cached raw response."""
    if cached is None:
        return ""
    parsed = cached.get("parsed")
    if parsed and isinstance(parsed, dict):
        return parsed.get("narrative", "") or ""
    return cached.get("raw_response", "") or ""


# ============================================================
# AUTOMATED CHECKS
# ============================================================

HALLUCINATION_PHRASES = [
    "placed on leave", "later cleared", "cleared in", "reinstated",
    "no charges were filed", "charges were dropped", "found not guilty",
    "returned to duty", "resigned", "was fired", "was terminated",
    "stepped down", "was suspended", "was arrested",
]


def check_hallucinations(narrative, included_findings):
    included_text = " ".join(f.get("original_text", "") for f in included_findings).lower()
    nl = narrative.lower()
    return [p for p in HALLUCINATION_PHRASES if p in nl and p not in included_text]


STUDENT_ID_PATTERNS = [
    (r"\b\d{1,2}-year-old\b", "age"),
    (r"\bspecial needs\b", "disability"),
    (r"\bdisabled\b", "disability"),
    (r"\bhandicapped\b", "disability"),
    (r"\bautistic\b", "disability"),
    (r"\bIEP student\b", "disability"),
    (r"\b504 student\b", "disability"),
    (r"\bfreshman\b", "grade"),
    (r"\bsophomore\b", "grade"),
    (r"\bjunior\b", "grade"),
    (r"\bsenior\b", "grade"),
    (r"\b\d+th[- ]grade\b", "grade"),
    (r"\b\d+th grader\b", "grade"),
]


def check_student_identifiers(narrative):
    found = []
    for pat, label in STUDENT_ID_PATTERNS:
        for m in re.findall(pat, narrative, re.IGNORECASE):
            found.append(f"{label}: '{m}'")
    return found


DEATH_CIRC_PHRASES = [
    "suicide", "overdose", "overdosed", "drowning", "drowned",
    "hanged", "hanging", "shot himself", "shot herself", "shot themselves",
    "starvation", "starved", "asphyxia", "suffocated",
    "wooded area", "wooded location", "on school grounds", "at the school",
    "in the gymnasium", "in the bathroom", "in the classroom",
    "near campus", "off campus", "at home", "in the woods",
    "was found", "found dead", "discovered by",
]


def check_death_circumstances(narrative):
    nl = narrative.lower()
    return [f"'{p}'" for p in DEATH_CIRC_PHRASES if p in nl]


GENDERED_STUDENT_PATTERNS = [
    r"\b(his|her|she|he)\s+(daughter|son|child)\b",
    r"\b(daughter|son)\s+(of|was|is)\b",
    r"\bthe\s+(boy|girl)\s+(student|child)?\b",
    r"\b(male|female)\s+student\b",
]


def check_gendered_pronouns_for_students(narrative):
    flags = []
    for pat in GENDERED_STUDENT_PATTERNS:
        for m in re.findall(pat, narrative, re.IGNORECASE):
            if isinstance(m, tuple):
                flags.append(" ".join(t for t in m if t))
            else:
                flags.append(str(m))
    return flags


EVALUATIVE_PHRASES = [
    "controversial", "divisive", "progressive", "conservative",
    "traditional values", "culture war", "woke", "anti-woke",
    "left-wing", "right-wing", "liberal agenda",
]


def check_evaluative_language(narrative):
    nl = narrative.lower()
    return [p for p in EVALUATIVE_PHRASES if p in nl]


def check_date_first(narrative):
    if "No significant web-sourced context" in narrative:
        return []
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", narrative))
    has_undated = bool(re.search(r"undated", narrative, re.IGNORECASE))
    if not has_year and not has_undated:
        return ["Narrative describes events but contains no year references or undated disclosures"]
    return []


def all_checks(narrative, included_findings):
    return {
        "hallucinations": check_hallucinations(narrative, included_findings),
        "student_id_leaks": check_student_identifiers(narrative),
        "death_circ": check_death_circumstances(narrative),
        "gendered_student": check_gendered_pronouns_for_students(narrative),
        "evaluative": check_evaluative_language(narrative),
        "date_first": check_date_first(narrative),
    }


def regression_diff(round1_checks, new_checks):
    """
    A regression is a violation appearing now that did NOT appear in Round 1.
    Returns dict of category -> list of new violations (regressions only).
    """
    diff = {}
    for cat, new_list in new_checks.items():
        old_list = round1_checks.get(cat, [])
        old_set = set(map(str, old_list))
        new_only = [x for x in new_list if str(x) not in old_set]
        if new_only:
            diff[cat] = new_only
    return diff


def improvement_diff(round1_checks, new_checks):
    """Violations present in Round 1 but absent now."""
    diff = {}
    for cat, old_list in round1_checks.items():
        new_list = new_checks.get(cat, [])
        new_set = set(map(str, new_list))
        gone = [x for x in old_list if str(x) not in new_set]
        if gone:
            diff[cat] = gone
    return diff


# ============================================================
# STAGE 0 + STAGE 1 + STAGE 2
# ============================================================

def stage0_prefilter(api_client, findings_for_prompt):
    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)
    user_msg = (
        f"Extract structured fields from each of these findings. "
        f"Do not make editorial decisions — only extract dates and type tags.\n\n"
        f"Findings:\n\n{findings_json}\n\n"
        f"Return the JSON output as specified in the system prompt."
    )
    response = api_client.messages.create(
        model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
        system=STAGE0_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = ""
    for block in response.content:
        if block.type == "text":
            raw = block.text
            break
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "actual_model": response.model,
    }
    parsed = parse_json_response(raw)
    extractions = parsed.get("extractions", []) if parsed else []
    by_idx = {e.get("finding_index"): e for e in extractions if e.get("finding_index") is not None}

    # Apply rules
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
            "conduct_latest": conduct_latest,
            "response_dt": response_dt,
            "response_type": rtype, "tag": tag,
            "is_dismissed": rtype in DISMISSED_TYPES,
            "ancient_conduct": conduct_latest is not None and conduct_latest < CUTOFF_20YR,
        })

    pattern_eligible_tags = set()
    for c in classifications:
        if (not c["is_dismissed"]
                and c["conduct_latest"] is not None
                and c["conduct_latest"] >= CUTOFF_20YR
                and c["tag"]):
            pattern_eligible_tags.add(c["tag"])

    kept_indices = []
    dropped = []
    for c in classifications:
        idx = c["index"]
        ext = c["extraction"]
        if c["is_dismissed"]:
            if c["response_dt"] is not None and c["response_dt"] < CUTOFF_5YR:
                dropped.append({
                    "finding_index": idx,
                    "rule": "DISMISSED_CASE_OUT_OF_WINDOW",
                    "reason": (
                        f"Dismissed/withdrawn case with response date {ext.get('response_date')} "
                        f"more than 5 years before {TODAY.isoformat()} (cutoff {CUTOFF_5YR.isoformat()})."
                    ),
                    "extraction": ext,
                })
                continue
            kept_indices.append(idx)
            continue
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pattern_eligible_tags:
                kept_indices.append(idx)
                continue
            dropped.append({
                "finding_index": idx,
                "rule": "CONDUCT_DATE_ANCHOR",
                "reason": (
                    f"Conduct latest {ext.get('conduct_date_latest')} more than 20 years before "
                    f"{TODAY.isoformat()} (cutoff {CUTOFF_20YR.isoformat()}); no same-tag pattern in window."
                ),
                "extraction": ext,
            })
            continue
        kept_indices.append(idx)

    return kept_indices, dropped, by_idx, raw, usage


def stage1_triage(api_client, school_name, district_name, nces_id, kept_findings):
    findings_json = json.dumps(kept_findings, indent=2, default=str)
    user_msg = (
        f"School: {school_name}\nDistrict: {district_name}\nNCES ID: {nces_id}\n\n"
        f"Findings to evaluate (already passed Stage 0 pre-filter):\n\n{findings_json}\n\n"
        f"Apply the recency rules and exclusion rules. Return JSON as specified."
    )
    response = api_client.messages.create(
        model=HAIKU_MODEL, max_tokens=MAX_TOKENS,
        system=STAGE1_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = ""
    for block in response.content:
        if block.type == "text":
            raw = block.text
            break
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "actual_model": response.model,
    }
    parsed = parse_json_response(raw)
    return parsed, raw, usage


def stage2_narrative(api_client, school_name, district_name, nces_id, included):
    if not included:
        return (
            {"narrative": "No significant web-sourced context was found for this school."},
            "", {"input_tokens": 0, "output_tokens": 0, "actual_model": SONNET_MODEL},
            "No significant web-sourced context was found for this school.",
        )
    stage2_findings = json.dumps(included, indent=2, default=str)
    user_msg = (
        f"School: {school_name}\nDistrict: {district_name}\nNCES ID: {nces_id}\n\n"
        f"The following findings have been pre-triaged and approved for inclusion. "
        f"Write the narrative using ONLY these findings. Do not add any information "
        f"not present in the finding text.\n\n"
        f"Approved findings:\n\n{stage2_findings}\n\n"
        f"Write the narrative following all rules. Return JSON."
    )
    response = api_client.messages.create(
        model=SONNET_MODEL, max_tokens=MAX_TOKENS,
        system=STAGE2_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = ""
    for block in response.content:
        if block.type == "text":
            raw = block.text
            break
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "actual_model": response.model,
    }
    parsed = parse_json_response(raw)
    narrative = parsed.get("narrative", "") if parsed else raw
    return parsed, raw, usage, narrative


# ============================================================
# RUN ONE SCHOOL
# ============================================================

def run_school(api_client, school_cfg):
    nces_id = school_cfg["nces_id"]
    name = school_cfg["name"]
    tests = school_cfg.get("tests", [])

    cached = load_cached(nces_id)
    if cached is None:
        return {"nces_id": nces_id, "name": name, "tests": tests, "error": "No cached findings"}

    school_name = cached.get("school_name", name)
    district_name = cached.get("district_name", "")
    findings = cached.get("findings_in", [])
    if not findings:
        return {
            "nces_id": nces_id, "name": school_name, "district_name": district_name,
            "tests": tests, "error": "Cached file has zero findings",
            "round1_narrative": round1_narrative(cached),
        }

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

    # Stage 0
    kept_indices, dropped, extractions, s0_raw, s0_usage = stage0_prefilter(
        api_client, findings_for_prompt
    )
    kept_for_prompt = [f for f in findings_for_prompt if f["index"] in kept_indices]
    time.sleep(RATE_LIMIT_SECONDS)

    # Stage 1
    s1_parsed, s1_raw, s1_usage = stage1_triage(
        api_client, school_name, district_name, nces_id, kept_for_prompt
    )
    if not s1_parsed:
        return {
            "nces_id": nces_id, "name": school_name, "district_name": district_name,
            "tests": tests, "findings_in": findings,
            "stage0": {"raw": s0_raw, "usage": s0_usage, "kept": kept_indices, "dropped": dropped, "extractions": extractions},
            "stage1": {"raw": s1_raw, "usage": s1_usage, "error": "JSON parse failure"},
            "round1_narrative": round1_narrative(cached),
        }
    included = s1_parsed.get("included", [])
    excluded = s1_parsed.get("excluded", [])
    time.sleep(RATE_LIMIT_SECONDS)

    # Stage 2
    s2_parsed, s2_raw, s2_usage, narrative = stage2_narrative(
        api_client, school_name, district_name, nces_id, included
    )

    # Auto-checks: new vs Round 1
    new_checks = all_checks(narrative, included)
    r1_narr = round1_narrative(cached)
    # For Round 1 baseline, run the same checks but use the Round 1 included findings as
    # context. We don't have Round 1's Stage-1 included list directly, so use the full
    # finding list — this is the most charitable baseline (anything in finding text counts
    # as "supported"). That makes hallucination diffs conservative.
    r1_baseline_findings = [{"original_text": f.get("summary", "")} for f in findings]
    r1_checks = all_checks(r1_narr, r1_baseline_findings)
    regressions = regression_diff(r1_checks, new_checks)
    improvements = improvement_diff(r1_checks, new_checks)

    return {
        "nces_id": nces_id, "name": school_name, "district_name": district_name,
        "tests": tests, "findings_count": len(findings), "findings_in": findings,
        "stage0": {
            "raw": s0_raw, "usage": s0_usage,
            "kept_indices": kept_indices,
            "dropped": dropped,
            "extractions": extractions,
        },
        "stage1": {
            "raw": s1_raw, "parsed": s1_parsed, "usage": s1_usage,
            "included_count": len(included), "excluded_count": len(excluded),
        },
        "stage2": {
            "raw": s2_raw, "parsed": s2_parsed, "usage": s2_usage,
            "narrative": narrative,
        },
        "checks_new": new_checks,
        "round1_narrative": r1_narr,
        "checks_round1": r1_checks,
        "regressions": regressions,
        "improvements": improvements,
    }


# ============================================================
# REPORT
# ============================================================

def render_report(report_path, results, timestamp):
    lines = []
    lines.append("# Phase 4.5 — Round 1 50-School Replay (Three-Stage Pipeline)")
    lines.append("")
    lines.append(f"**Run:** {timestamp}")
    lines.append(f"**Pipeline:** Stage 0 (Haiku extraction + Python rules) → Stage 1 (Haiku triage) → Stage 2 (Sonnet 4.6 narrative)")
    lines.append(f"**Stage 0 cutoffs:** today={TODAY.isoformat()}, 20yr={CUTOFF_20YR.isoformat()}, 5yr={CUTOFF_5YR.isoformat()}")
    lines.append(f"**Comparison baseline:** Round 1 single-stage Sonnet 4.5 narratives in raw_responses/")
    lines.append("")

    # ---- Summary table ----
    tested = [r for r in results.values() if "stage2" in r]
    skipped = [r for r in results.values() if "error" in r]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Schools attempted: {len(results)}")
    lines.append(f"- Schools tested through Stage 2: {len(tested)}")
    lines.append(f"- Schools skipped/errored: {len(skipped)}")
    lines.append("")

    # Regression totals
    reg_totals = {}
    imp_totals = {}
    schools_with_regressions = []
    for nid, r in results.items():
        if "regressions" not in r:
            continue
        if any(r["regressions"].values()):
            schools_with_regressions.append((nid, r))
        for cat, items in r.get("regressions", {}).items():
            reg_totals[cat] = reg_totals.get(cat, 0) + len(items)
        for cat, items in r.get("improvements", {}).items():
            imp_totals[cat] = imp_totals.get(cat, 0) + len(items)

    lines.append(f"- Schools with at least one regression: {len(schools_with_regressions)}")
    lines.append("")
    if reg_totals:
        lines.append("### Regression totals (new violations not present in Round 1)")
        for cat in sorted(reg_totals):
            lines.append(f"- {cat}: {reg_totals[cat]}")
        lines.append("")
    else:
        lines.append("**No regressions detected across any auto-check category.**")
        lines.append("")
    if imp_totals:
        lines.append("### Improvements (Round 1 violations no longer present)")
        for cat in sorted(imp_totals):
            lines.append(f"- {cat}: {imp_totals[cat]}")
        lines.append("")

    # Stage 0 totals
    s0_dropped = sum(len(r["stage0"]["dropped"]) for r in tested)
    s0_dropped_by_rule = {}
    for r in tested:
        for d in r["stage0"]["dropped"]:
            s0_dropped_by_rule[d["rule"]] = s0_dropped_by_rule.get(d["rule"], 0) + 1
    lines.append(f"- Stage 0 findings dropped: {s0_dropped}")
    for rule, cnt in sorted(s0_dropped_by_rule.items()):
        lines.append(f"  - {rule}: {cnt}")
    lines.append("")

    # Cost
    h_in = sum(r["stage0"]["usage"]["input_tokens"] + r["stage1"]["usage"]["input_tokens"] for r in tested)
    h_out = sum(r["stage0"]["usage"]["output_tokens"] + r["stage1"]["usage"]["output_tokens"] for r in tested)
    s_in = sum(r["stage2"]["usage"]["input_tokens"] for r in tested)
    s_out = sum(r["stage2"]["usage"]["output_tokens"] for r in tested)
    haiku_cost = (h_in / 1_000_000) * 0.80 + (h_out / 1_000_000) * 4.0
    sonnet_cost = (s_in / 1_000_000) * 3.0 + (s_out / 1_000_000) * 15.0
    lines.append("### Cost")
    lines.append(f"- Haiku: ${haiku_cost:.4f} ({h_in:,} in / {h_out:,} out)")
    lines.append(f"- Sonnet: ${sonnet_cost:.4f} ({s_in:,} in / {s_out:,} out)")
    lines.append(f"- **Total: ${haiku_cost + sonnet_cost:.4f}**")
    lines.append("")

    # ---- Per-test sections ----
    for tnum in sorted(TEST_NAMES.keys()):
        schools_in_test = sorted(
            [(nid, r) for nid, r in results.items() if tnum in r.get("tests", [])],
            key=lambda x: x[1].get("name", x[0]),
        )
        if not schools_in_test:
            continue
        lines.append("---")
        lines.append("")
        lines.append(f"## Test {tnum}: {TEST_NAMES[tnum]}")
        lines.append(f"_{len(schools_in_test)} schools_")
        lines.append("")

        for nid, r in schools_in_test:
            name = r.get("name", "?")
            lines.append(f"### {name} ({nid})")
            lines.append("")
            if "error" in r:
                lines.append(f"**SKIPPED:** {r['error']}")
                lines.append("")
                continue

            # Stage 0 dropped
            dropped = r["stage0"]["dropped"]
            if dropped:
                lines.append("**Stage 0 pre-filter dropped:**")
                for d in dropped:
                    lines.append(f"- Finding [{d['finding_index']}] — {d['rule']}: {d['reason']}")
                lines.append("")

            lines.append(f"**Findings in:** {r['findings_count']} | "
                         f"**Stage 0 kept:** {len(r['stage0']['kept_indices'])} | "
                         f"**Stage 1 included:** {r['stage1']['included_count']} | "
                         f"**Stage 1 excluded:** {r['stage1']['excluded_count']}")
            lines.append("")

            # Input findings (collapsible)
            findings_in = r.get("findings_in", [])
            if findings_in:
                lines.append("<details>")
                lines.append("<summary>Input findings (click to expand)</summary>")
                lines.append("")
                for j, f in enumerate(findings_in):
                    lines.append(
                        f"**Finding {j+1}** ({f.get('category','?')}, {f.get('date','undated')}, "
                        f"confidence: {f.get('confidence','?')}, sensitivity: {f.get('sensitivity','normal')})"
                    )
                    lines.append(f"> {f.get('summary','No summary')}")
                    lines.append("")
                lines.append("</details>")
                lines.append("")

            # New narrative
            narrative = r["stage2"]["narrative"]
            lines.append("**New three-stage output:**")
            lines.append("")
            for para in narrative.split("\n\n"):
                p = para.strip()
                if p:
                    lines.append(f"> {p}")
                    lines.append(">")
            lines.append("")

            # Round 1 baseline
            r1n = r.get("round1_narrative", "")
            lines.append("<details>")
            lines.append("<summary>Round 1 single-stage output (baseline)</summary>")
            lines.append("")
            for para in r1n.split("\n\n"):
                p = para.strip()
                if p:
                    lines.append(f"> {p}")
                    lines.append(">")
            lines.append("")
            lines.append("</details>")
            lines.append("")

            # Auto-check results new vs round1
            new_c = r["checks_new"]
            r1_c = r["checks_round1"]
            lines.append("**Auto-checks (new run):**")
            for cat in ["hallucinations", "student_id_leaks", "death_circ", "gendered_student", "evaluative", "date_first"]:
                new_v = new_c.get(cat, [])
                r1_v = r1_c.get(cat, [])
                tag = "PASS" if not new_v else "FLAG"
                lines.append(f"- {cat}: {tag} (new: {len(new_v)}, round1: {len(r1_v)})")
                if new_v:
                    for v in new_v:
                        lines.append(f"  - new: {v}")
            lines.append("")

            # Regressions
            regs = r.get("regressions", {})
            if regs:
                lines.append("**REGRESSIONS (new in this run, not present in Round 1):**")
                for cat, items in regs.items():
                    for it in items:
                        lines.append(f"- {cat}: {it}")
                lines.append("")

            # Improvements
            imps = r.get("improvements", {})
            if imps:
                lines.append("<details>")
                lines.append("<summary>Improvements vs Round 1</summary>")
                lines.append("")
                for cat, items in imps.items():
                    for it in items:
                        lines.append(f"- {cat}: {it}")
                lines.append("")
                lines.append("</details>")
                lines.append("")

            lines.append("**PASS / FAIL / NEEDS REVIEW:** ______")
            lines.append("")
            lines.append("**Builder notes:** ______")
            lines.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Round 1 50-School Three-Stage Replay — {timestamp}")

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    schools = cfg.get("schools", [])
    print(f"Loaded {len(schools)} schools from config")
    print(f"Models: {HAIKU_MODEL} (Stage 0 + Stage 1), {SONNET_MODEL} (Stage 2)")
    print(f"Today: {TODAY.isoformat()} | 20yr cutoff: {CUTOFF_20YR.isoformat()} | 5yr cutoff: {CUTOFF_5YR.isoformat()}")

    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    results = {}

    for i, school_cfg in enumerate(schools):
        nid = school_cfg["nces_id"]
        name = school_cfg["name"]
        print(f"\n[{i+1}/{len(schools)}] {name} ({nid})")
        try:
            r = run_school(api_client, school_cfg)
        except Exception as e:
            print(f"  EXCEPTION: {type(e).__name__}: {e}")
            r = {"nces_id": nid, "name": name, "tests": school_cfg.get("tests", []),
                 "error": f"Exception during run: {type(e).__name__}: {e}"}
        results[nid] = r

        # Save per-school JSON
        out_path = os.path.join(OUTPUT_DIR, f"{nid}.json")
        with open(out_path, "w") as f:
            json.dump(r, f, indent=2, default=str)

        # Quick console line
        if "error" in r:
            print(f"  ERROR: {r['error']}")
        else:
            s0d = len(r["stage0"]["dropped"])
            s1i = r["stage1"]["included_count"]
            s1e = r["stage1"]["excluded_count"]
            n_regs = sum(len(v) for v in r.get("regressions", {}).values())
            print(f"  Stage 0 dropped: {s0d}, Stage 1 incl: {s1i}, excl: {s1e}, regressions: {n_regs}")

        # Rate limit between schools
        if i < len(schools) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    # ---- Save summary + report ----
    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    summary = {
        "timestamp": timestamp,
        "today": TODAY.isoformat(),
        "cutoffs": {"20yr": CUTOFF_20YR.isoformat(), "5yr": CUTOFF_5YR.isoformat()},
        "models": {
            "stage0_haiku": HAIKU_MODEL,
            "stage1_haiku": HAIKU_MODEL,
            "stage2_sonnet": SONNET_MODEL,
        },
        "schools_attempted": len(results),
        "per_school": {
            nid: {
                "name": r.get("name", "?"),
                "tests": r.get("tests", []),
                "error": r.get("error"),
                "stage0_dropped": [
                    {"finding_index": d["finding_index"], "rule": d["rule"], "reason": d["reason"]}
                    for d in r.get("stage0", {}).get("dropped", [])
                ],
                "stage1_included": r.get("stage1", {}).get("included_count"),
                "stage1_excluded": r.get("stage1", {}).get("excluded_count"),
                "regressions": r.get("regressions", {}),
                "improvements": r.get("improvements", {}),
                "narrative": r.get("stage2", {}).get("narrative", ""),
            }
            for nid, r in results.items()
        },
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary saved: {summary_path}")

    report_path = os.path.join(OUTPUT_DIR, f"report_{timestamp}.md")
    render_report(report_path, results, timestamp)
    print(f"Report saved: {report_path}")
    print("Done.")


if __name__ == "__main__":
    main()
