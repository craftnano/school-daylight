# PURPOSE: Three-stage pipeline validation on 6 schools.
#   Stage 0: Haiku structured extraction → Python rule application (conduct-date anchor + dismissed-case)
#   Stage 1: Haiku triage on surviving findings (recency, severity, exclusion rules)
#   Stage 2: Sonnet narrative on Stage 1 included findings (writing rules)
#
# WHY STAGE 0 EXISTS:
#   Both Sonnet and Haiku consistently failed to apply the conduct-date anchor and dismissed-case rules
#   when those rules competed with the severity exception or with Haiku's tendency to anchor on response
#   date. Per the April 2026 resume doc, structured extraction + Python comparison removes the judgment
#   from the model. Haiku still does the extraction (a fact-finding task), but the rule logic is code.
#
# RULES APPLIED IN STAGE 0:
#   1. CONDUCT-DATE ANCHOR — Drop a finding if its underlying conduct ended more than 20 years
#      before today (2026-04-29 → cutoff 2006-04-29), UNLESS another finding in the same school
#      shares its finding_type_tag and has conduct within the last 20 years (the documented pattern).
#   2. DISMISSED-CASE RULE — Drop a finding if it resolved without an adverse finding (dismissal,
#      withdrawal, resolution-without-adverse-finding) and that resolution date is more than 5 years
#      before today (cutoff 2021-04-29). The pattern exception does NOT apply to dismissed cases.
#
# CONSERVATIVE PRINCIPLE: We only drop a finding when we have positive evidence under the rule.
#   Missing dates, ambiguous response_type, or extraction failures default to KEEP and let Stage 1
#   handle it. Stage 0 is a sieve, not a filter — surviving findings still go through Stage 1 triage.
#
# INPUTS: Cached raw responses from Round 2 single-stage test (raw_responses/<nces_id>.json)
# OUTPUTS: Per-school JSON + summary.json in this directory
# DOES NOT: Modify any pipeline output, MongoDB, prompts in prompts/, or prior test results
# MODELS: Haiku 4.5 (Stage 0 + Stage 1), Sonnet 4.6 (Stage 2)

import os
import sys
import json
import re
import time
from datetime import datetime, date
import anthropic

# Add project root to path so config.py is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import config

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
RATE_LIMIT_SECONDS = 12
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_RESPONSES_DIR = os.path.join(config.PROJECT_ROOT, "phases", "phase-4.5", "test_results", "raw_responses")

# RULE: Today's date is the anchor for both windows. Hard-coded so re-runs are reproducible.
# If you re-run this in the future, update TODAY to the actual date so the windows track time.
TODAY = date(2026, 4, 29)
CUTOFF_20YR = date(TODAY.year - 20, TODAY.month, TODAY.day)  # 2006-04-29
CUTOFF_5YR = date(TODAY.year - 5, TODAY.month, TODAY.day)    # 2021-04-29

# Response types that count as "dismissed / no adverse finding"
DISMISSED_TYPES = {"dismissal", "withdrawal", "resolution_without_finding"}

SCHOOLS = [
    {
        "nces_id": "530033000043",
        "label": "Bainbridge Island SD",
        "reason": "Conduct-date anchor test: 2024 lawsuit re: abuse from ~1985 should be dropped at Stage 0.",
    },
    {
        "nces_id": "530048000119",
        "label": "Bethel SD",
        "reason": "Pattern exception control: 2016 + 2025 same-type findings, both should survive.",
    },
    {
        "nces_id": "530039000082",
        "label": "Phantom Lake Elementary",
        "reason": "Mixed: recent leadership pattern + older Bellevue district lawsuits, some pattern-eligible.",
    },
    {
        "nces_id": "530807001334",
        "label": "Soap Lake Elementary",
        "reason": "Recent governance findings, 2022/2024 — should pass Stage 0 unchanged.",
    },
    {
        "nces_id": "530423000670",
        "label": "Juanita HS",
        "reason": "Original hallucination case (single-stage), severity-exception keeper. Should pass Stage 0 unchanged.",
    },
    {
        "nces_id": "530267000391",
        "label": "Everett SD",
        "reason": "Dismissed-case test: 2018 lawsuit dismissed re: 2003 conduct. Should be dropped at Stage 0.",
    },
]


# ============================================================
# STAGE 0 PROMPT — STRUCTURED EXTRACTION ONLY
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


# ============================================================
# STAGE 1 PROMPT — TRIAGE (unchanged from run_five_schools.py)
# ============================================================

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


# ============================================================
# STAGE 2 PROMPT — NARRATIVE (unchanged from run_five_schools.py)
# ============================================================

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
# DATA HELPERS
# ============================================================

def load_cached_findings(nces_id):
    """Load findings from cached raw response file."""
    path = os.path.join(RAW_RESPONSES_DIR, f"{nces_id}.json")
    if not os.path.exists(path):
        return None, None, None
    with open(path, "r") as f:
        data = json.load(f)
    return (
        data.get("school_name", "Unknown"),
        data.get("district_name", "Unknown"),
        data.get("findings_in", []),
    )


def parse_json_response(raw_text):
    """Parse JSON from an API response, handling markdown fences and embedded JSON."""
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
    """
    Parse a date string from Stage 0 extraction. Accepts YYYY, YYYY-MM, YYYY-MM-DD.
    Returns a date or None.
    For year-only and month-only, picks end of period (Dec 31, last day of month) so
    'latest' comparisons are conservative (i.e., "could the conduct have extended into
    the recent window?" — yes, give it the benefit).
    """
    if s is None:
        return None
    s = str(s).strip().lower()
    if s in ("", "null", "none", "undated", "unknown"):
        return None
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        try:
            y, mo = int(m.group(1)), int(m.group(2))
            # Use 28 to avoid month-end quirks
            return date(y, mo, 28)
        except ValueError:
            return None
    # YYYY
    m = re.match(r"^(\d{4})$", s)
    if m:
        return date(int(m.group(1)), 12, 31)
    return None


# ============================================================
# STAGE 0: HAIKU EXTRACTION + PYTHON RULES
# ============================================================

def stage0_prefilter(api_client, findings_for_prompt):
    """
    Run Stage 0 pre-filter on a school's findings.
    Returns (kept_indices, dropped_records, extractions_by_idx, raw_response, usage).
    """
    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)
    user_msg = (
        f"Extract structured fields from each of these findings. "
        f"Do not make editorial decisions — only extract dates and type tags.\n\n"
        f"Findings:\n\n{findings_json}\n\n"
        f"Return the JSON output as specified in the system prompt."
    )

    response = api_client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS,
        system=STAGE0_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw_text = ""
    for block in response.content:
        if block.type == "text":
            raw_text = block.text
            break

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "actual_model": response.model,
    }

    parsed = parse_json_response(raw_text)
    extractions = parsed.get("extractions", []) if parsed else []
    by_idx = {}
    for e in extractions:
        idx = e.get("finding_index")
        if idx is not None:
            by_idx[idx] = e

    # ---- Apply rules in Python ----

    # First pass: classify each finding by its extraction
    classifications = []
    for f in findings_for_prompt:
        idx = f["index"]
        ext = by_idx.get(idx, {})
        conduct_latest = parse_extracted_date(ext.get("conduct_date_latest"))
        response_dt = parse_extracted_date(ext.get("response_date"))
        rtype = (ext.get("response_type") or "unclear").lower().strip()
        tag = (ext.get("finding_type_tag") or "").strip().lower()
        is_dismissed = rtype in DISMISSED_TYPES
        ancient_conduct = conduct_latest is not None and conduct_latest < CUTOFF_20YR
        classifications.append({
            "index": idx,
            "extraction": ext,
            "conduct_latest": conduct_latest,
            "response_dt": response_dt,
            "response_type": rtype,
            "tag": tag,
            "is_dismissed": is_dismissed,
            "ancient_conduct": ancient_conduct,
        })

    # Build pattern-eligible tag set for the conduct-date anchor:
    # tags that have at least one NON-dismissed finding with conduct within the last 20 years.
    pattern_eligible_tags = set()
    for c in classifications:
        if (not c["is_dismissed"]
                and c["conduct_latest"] is not None
                and c["conduct_latest"] >= CUTOFF_20YR
                and c["tag"]):
            pattern_eligible_tags.add(c["tag"])

    # Second pass: apply rules
    kept_indices = []
    dropped = []
    for c in classifications:
        idx = c["index"]
        ext = c["extraction"]

        # RULE: Dismissed-case 5-year window. No pattern exception.
        if c["is_dismissed"]:
            if c["response_dt"] is not None and c["response_dt"] < CUTOFF_5YR:
                dropped.append({
                    "finding_index": idx,
                    "rule": "DISMISSED_CASE_OUT_OF_WINDOW",
                    "reason": (
                        f"Response type '{c['response_type']}' (dismissed/withdrawn/no-finding) "
                        f"with response date {ext.get('response_date')} is more than 5 years before "
                        f"today ({TODAY.isoformat()}; cutoff {CUTOFF_5YR.isoformat()}). "
                        f"Pattern exception does not apply to dismissed cases."
                    ),
                    "extraction": ext,
                })
                continue
            # Otherwise: keep — either response date unknown (conservative) or within window
            kept_indices.append(idx)
            continue

        # RULE: Conduct-date anchor — conduct >20yr ago, no same-tag pattern in window
        if c["ancient_conduct"]:
            if c["tag"] and c["tag"] in pattern_eligible_tags:
                # Pattern exception keeps it
                kept_indices.append(idx)
                continue
            dropped.append({
                "finding_index": idx,
                "rule": "CONDUCT_DATE_ANCHOR",
                "reason": (
                    f"Conduct latest date {ext.get('conduct_date_latest')} is more than 20 years "
                    f"before today ({TODAY.isoformat()}; cutoff {CUTOFF_20YR.isoformat()}). "
                    f"No same-type pattern (tag={c['tag'] or '<none>'}) exists with conduct within "
                    f"the last 20 years."
                ),
                "extraction": ext,
            })
            continue

        # Default: keep
        kept_indices.append(idx)

    return kept_indices, dropped, by_idx, raw_text, usage


# ============================================================
# AUTOMATED OUTPUT CHECKS (carried forward from run_five_schools.py)
# ============================================================

def check_hallucinations(narrative, included_findings):
    hallucination_phrases = [
        "placed on leave", "later cleared", "cleared in", "reinstated",
        "no charges were filed", "charges were dropped", "found not guilty",
        "returned to duty", "resigned", "was fired", "was terminated",
        "stepped down", "was suspended", "was arrested",
    ]
    included_text = " ".join(f.get("original_text", "") for f in included_findings)
    included_lower = included_text.lower()
    narrative_lower = narrative.lower()
    return [
        f"'{p}' appears in narrative but not in any included finding"
        for p in hallucination_phrases
        if p in narrative_lower and p not in included_lower
    ]


def check_student_identifiers(narrative):
    patterns = [
        (r"\b\d{1,2}-year-old\b", "age descriptor"),
        (r"\bspecial needs\b", "disability descriptor"),
        (r"\bdisabled\b", "disability descriptor"),
        (r"\bhandicapped\b", "disability descriptor"),
        (r"\bautistic\b", "disability descriptor"),
        (r"\bIEP student\b", "disability descriptor"),
        (r"\b504 student\b", "disability descriptor"),
        (r"\bfreshman\b", "grade-level identifier"),
        (r"\bsophomore\b", "grade-level identifier"),
        (r"\bjunior\b", "grade-level identifier"),
        (r"\bsenior\b", "grade-level identifier"),
        (r"\b\d+th[- ]grade\b", "grade-level identifier"),
        (r"\b\d+th grader\b", "grade-level identifier"),
    ]
    found = []
    for pattern, label in patterns:
        for m in re.findall(pattern, narrative, re.IGNORECASE):
            found.append(f"{label}: '{m}'")
    return found


def check_death_circumstances(narrative):
    forbidden_phrases = [
        "suicide", "overdose", "overdosed", "drowning", "drowned",
        "hanged", "hanging", "shot himself", "shot herself", "shot themselves",
        "starvation", "starved", "asphyxia", "suffocated",
        "wooded area", "wooded location", "on school grounds", "at the school",
        "in the gymnasium", "in the bathroom", "in the classroom",
        "near campus", "off campus", "at home", "in the woods",
        "was found", "found dead", "discovered by",
    ]
    narr_lower = narrative.lower()
    return [f"death-circumstance phrase: '{p}'" for p in forbidden_phrases if p in narr_lower]


def check_gendered_pronouns_for_students(narrative):
    student_context_patterns = [
        r"\b(his|her|she|he)\s+(daughter|son|child)\b",
        r"\b(daughter|son)\s+(of|was|is)\b",
        r"\bthe\s+(boy|girl)\s+(student|child)?\b",
        r"\b(male|female)\s+student\b",
    ]
    flags = []
    for pat in student_context_patterns:
        for m in re.findall(pat, narrative, re.IGNORECASE):
            if isinstance(m, tuple):
                flags.append(f"gendered student reference: '{' '.join(m)}'")
            else:
                flags.append(f"gendered student reference: '{m}'")
    return flags


# ============================================================
# PER-SCHOOL RUNNER
# ============================================================

def run_school(api_client, school_info):
    nces_id = school_info["nces_id"]
    label = school_info["label"]

    print(f"\n{'=' * 60}")
    print(f"{label} ({nces_id})")
    print(f"{'=' * 60}")

    school_name, district_name, findings = load_cached_findings(nces_id)
    if findings is None:
        print(f"  ERROR: No cached findings for {nces_id}")
        return {"error": f"No cached findings for {nces_id}"}

    print(f"  School: {school_name}")
    print(f"  District: {district_name}")
    print(f"  Findings: {len(findings)}")

    # Build findings_for_prompt with stable indices
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

    # ---- Stage 0: Pre-filter ----
    print(f"\n  Stage 0 (Haiku extraction + Python rules)...")
    kept_indices, dropped, extractions_by_idx, stage0_raw, stage0_usage = stage0_prefilter(
        api_client, findings_for_prompt
    )
    print(f"  Stage 0: {stage0_usage['input_tokens']} in / {stage0_usage['output_tokens']} out")
    print(f"  Kept: {len(kept_indices)}, Dropped: {len(dropped)}")
    for d in dropped:
        ext = d["extraction"]
        print(f"    DROP [{d['finding_index']}] {d['rule']}: "
              f"conduct={ext.get('conduct_date_latest')} "
              f"response={ext.get('response_date')} "
              f"type={ext.get('response_type')} "
              f"tag={ext.get('finding_type_tag')}")
        print(f"           reason: {d['reason']}")

    # Findings that passed Stage 0 are what we feed Stage 1
    kept_findings_for_prompt = [f for f in findings_for_prompt if f["index"] in kept_indices]

    time.sleep(RATE_LIMIT_SECONDS)

    # ---- Stage 1: Triage on surviving findings ----
    print(f"\n  Stage 1 (Haiku triage)...")
    findings_json = json.dumps(kept_findings_for_prompt, indent=2, default=str)
    stage1_user_msg = (
        f"School: {school_name}\n"
        f"District: {district_name}\n"
        f"NCES ID: {nces_id}\n\n"
        f"Findings to evaluate (already passed conduct-date anchor and dismissed-case "
        f"pre-filter):\n\n{findings_json}\n\n"
        f"Apply the recency rules and exclusion rules to each finding. "
        f"Return the JSON output as specified."
    )

    response1 = api_client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS,
        system=STAGE1_PROMPT,
        messages=[{"role": "user", "content": stage1_user_msg}],
    )

    stage1_raw = ""
    for block in response1.content:
        if block.type == "text":
            stage1_raw = block.text
            break

    stage1_usage = {
        "input_tokens": response1.usage.input_tokens,
        "output_tokens": response1.usage.output_tokens,
        "actual_model": response1.model,
    }
    print(f"  Stage 1: {stage1_usage['input_tokens']} in / {stage1_usage['output_tokens']} out")

    stage1_parsed = parse_json_response(stage1_raw)
    if not stage1_parsed:
        print(f"  ERROR: Could not parse Stage 1 JSON")
        return {
            "nces_id": nces_id, "label": label,
            "school_name": school_name, "district_name": district_name,
            "findings_count": len(findings),
            "stage0": {
                "raw": stage0_raw, "usage": stage0_usage,
                "extractions": extractions_by_idx,
                "kept_indices": kept_indices, "dropped": dropped,
            },
            "stage1": {"raw": stage1_raw, "usage": stage1_usage,
                       "error": "Stage 1 JSON parse failure"},
        }

    included = stage1_parsed.get("included", [])
    excluded = stage1_parsed.get("excluded", [])
    included_with_date = sum(1 for it in included if it.get("date"))
    print(f"  Included: {len(included)}, Excluded: {len(excluded)}")
    print(f"  Included findings with date field: {included_with_date}/{len(included)}")
    for item in included:
        idx = item.get("finding_index", "?")
        theme = item.get("theme", "?")
        date_s = item.get("date", "MISSING")
        rationale = item.get("rationale", "")
        print(f"    INCLUDE [{idx}] ({theme}, {date_s}): {rationale[:80]}")
    for item in excluded:
        idx = item.get("finding_index", "?")
        rationale = item.get("rationale", "")
        print(f"    EXCLUDE [{idx}]: {rationale[:80]}")

    time.sleep(RATE_LIMIT_SECONDS)

    # ---- Stage 2: Sonnet narrative ----
    print(f"\n  Stage 2 (Sonnet narrative)...")
    if not included:
        print(f"  No findings included — skipping Stage 2")
        narrative = "No significant web-sourced context was found for this school."
        stage2_usage = {"input_tokens": 0, "output_tokens": 0, "actual_model": SONNET_MODEL}
        stage2_raw = ""
        stage2_parsed = {"narrative": narrative}
    else:
        stage2_findings = json.dumps(included, indent=2, default=str)
        stage2_user_msg = (
            f"School: {school_name}\n"
            f"District: {district_name}\n"
            f"NCES ID: {nces_id}\n\n"
            f"The following findings have been pre-triaged and approved for inclusion. "
            f"Write the narrative using ONLY these findings. Do not add any information "
            f"not present in the finding text.\n\n"
            f"Approved findings:\n\n{stage2_findings}\n\n"
            f"Write the narrative following all rules in your system prompt. "
            f"Return your response as JSON with the fields specified in the OUTPUT FORMAT section."
        )
        response2 = api_client.messages.create(
            model=SONNET_MODEL,
            max_tokens=MAX_TOKENS,
            system=STAGE2_PROMPT,
            messages=[{"role": "user", "content": stage2_user_msg}],
        )
        stage2_raw = ""
        for block in response2.content:
            if block.type == "text":
                stage2_raw = block.text
                break
        stage2_usage = {
            "input_tokens": response2.usage.input_tokens,
            "output_tokens": response2.usage.output_tokens,
            "actual_model": response2.model,
        }
        print(f"  Stage 2: {stage2_usage['input_tokens']} in / {stage2_usage['output_tokens']} out")
        stage2_parsed = parse_json_response(stage2_raw)
        narrative = stage2_parsed.get("narrative", "") if stage2_parsed else stage2_raw

    # ---- Output checks ----
    hallucinations = check_hallucinations(narrative, included)
    student_ids = check_student_identifiers(narrative)
    death_violations = check_death_circumstances(narrative)
    gender_flags = check_gendered_pronouns_for_students(narrative)

    print(f"\n  Hallucinations: {len(hallucinations)}")
    for h in hallucinations:
        print(f"    {h}")
    print(f"  Student ID leaks: {len(student_ids)}")
    for s in student_ids:
        print(f"    {s}")
    print(f"  Death-circumstance violations: {len(death_violations)}")
    for d in death_violations:
        print(f"    {d}")
    print(f"  Gendered-student flags: {len(gender_flags)}")
    for g in gender_flags:
        print(f"    {g}")

    return {
        "nces_id": nces_id,
        "label": label,
        "school_name": school_name,
        "district_name": district_name,
        "findings_count": len(findings),
        "stage0": {
            "raw": stage0_raw,
            "usage": stage0_usage,
            "extractions": extractions_by_idx,
            "kept_indices": kept_indices,
            "dropped": dropped,
        },
        "stage1": {
            "raw": stage1_raw,
            "parsed": stage1_parsed,
            "usage": stage1_usage,
            "included_count": len(included),
            "excluded_count": len(excluded),
            "included_with_date": included_with_date,
        },
        "stage2": {
            "raw": stage2_raw,
            "parsed": stage2_parsed,
            "narrative": narrative,
            "usage": stage2_usage,
        },
        "hallucinations": hallucinations,
        "student_id_leaks": student_ids,
        "death_circumstance_violations": death_violations,
        "gendered_student_flags": gender_flags,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Three-Stage 6-School Validation — {timestamp}")
    print(f"Schools: {len(SCHOOLS)}")
    print(f"Models: Haiku (Stage 0 + Stage 1), Sonnet 4.6 (Stage 2)")
    print(f"Today: {TODAY.isoformat()}")
    print(f"Cutoffs: 20yr → {CUTOFF_20YR.isoformat()}, 5yr → {CUTOFF_5YR.isoformat()}")
    print(f"Output dir: {OUTPUT_DIR}")

    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    all_results = {}

    for i, school in enumerate(SCHOOLS):
        result = run_school(api_client, school)
        all_results[school["nces_id"]] = result

        school_path = os.path.join(
            OUTPUT_DIR, f"{school['nces_id']}_{school['label'].replace(' ', '_')}.json"
        )
        with open(school_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        if i < len(SCHOOLS) - 1 and "error" not in result:
            time.sleep(RATE_LIMIT_SECONDS)

    # ---- Summary ----
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    totals = {
        "stage0_dropped": 0,
        "stage1_excluded": 0,
        "hallucinations": 0,
        "student_id_leaks": 0,
        "death_circumstance_violations": 0,
        "gendered_student_flags": 0,
    }
    cost_in = {"haiku": 0, "sonnet": 0}
    cost_out = {"haiku": 0, "sonnet": 0}

    for nid, r in all_results.items():
        if "error" in r:
            continue
        totals["stage0_dropped"] += len(r["stage0"]["dropped"])
        if "excluded_count" in r["stage1"]:
            totals["stage1_excluded"] += r["stage1"]["excluded_count"]
        totals["hallucinations"] += len(r.get("hallucinations", []))
        totals["student_id_leaks"] += len(r.get("student_id_leaks", []))
        totals["death_circumstance_violations"] += len(r.get("death_circumstance_violations", []))
        totals["gendered_student_flags"] += len(r.get("gendered_student_flags", []))
        cost_in["haiku"] += r["stage0"]["usage"]["input_tokens"]
        cost_out["haiku"] += r["stage0"]["usage"]["output_tokens"]
        cost_in["haiku"] += r["stage1"]["usage"]["input_tokens"]
        cost_out["haiku"] += r["stage1"]["usage"]["output_tokens"]
        cost_in["sonnet"] += r["stage2"]["usage"]["input_tokens"]
        cost_out["sonnet"] += r["stage2"]["usage"]["output_tokens"]

    haiku_cost = (cost_in["haiku"] / 1_000_000) * 0.80 + (cost_out["haiku"] / 1_000_000) * 4.0
    sonnet_cost = (cost_in["sonnet"] / 1_000_000) * 3.0 + (cost_out["sonnet"] / 1_000_000) * 15.0
    total_cost = haiku_cost + sonnet_cost

    print(f"Stage 0 findings dropped: {totals['stage0_dropped']}")
    print(f"Stage 1 findings excluded: {totals['stage1_excluded']}")
    print(f"Hallucinations: {totals['hallucinations']}")
    print(f"Student ID leaks: {totals['student_id_leaks']}")
    print(f"Death-circumstance flags: {totals['death_circumstance_violations']}")
    print(f"Gendered-student flags: {totals['gendered_student_flags']}")
    print(f"Haiku cost: ${haiku_cost:.4f} ({cost_in['haiku']:,} in / {cost_out['haiku']:,} out)")
    print(f"Sonnet cost: ${sonnet_cost:.4f} ({cost_in['sonnet']:,} in / {cost_out['sonnet']:,} out)")
    print(f"Total cost: ${total_cost:.4f}")

    summary = {
        "timestamp": timestamp,
        "today": TODAY.isoformat(),
        "cutoffs": {"20yr": CUTOFF_20YR.isoformat(), "5yr": CUTOFF_5YR.isoformat()},
        "models": {
            "stage0_haiku": HAIKU_MODEL,
            "stage1_haiku": HAIKU_MODEL,
            "stage2_sonnet": SONNET_MODEL,
        },
        "schools_tested": len(SCHOOLS),
        "totals": totals,
        "cost": {
            "haiku": {"input_tokens": cost_in["haiku"], "output_tokens": cost_out["haiku"], "cost": round(haiku_cost, 4)},
            "sonnet": {"input_tokens": cost_in["sonnet"], "output_tokens": cost_out["sonnet"], "cost": round(sonnet_cost, 4)},
            "total": round(total_cost, 4),
        },
        "per_school": {},
    }
    for nid, r in all_results.items():
        if "error" in r:
            summary["per_school"][nid] = {"error": r["error"]}
        else:
            stage0_drop_summary = [
                {"finding_index": d["finding_index"], "rule": d["rule"], "reason": d["reason"]}
                for d in r["stage0"]["dropped"]
            ]
            summary["per_school"][nid] = {
                "label": r["label"],
                "findings_in": r["findings_count"],
                "stage0_kept": len(r["stage0"]["kept_indices"]),
                "stage0_dropped": stage0_drop_summary,
                "stage1_included": r["stage1"].get("included_count", 0),
                "stage1_excluded": r["stage1"].get("excluded_count", 0),
                "hallucinations": r.get("hallucinations", []),
                "student_id_leaks": r.get("student_id_leaks", []),
                "death_circumstance_violations": r.get("death_circumstance_violations", []),
                "gendered_student_flags": r.get("gendered_student_flags", []),
                "narrative": r["stage2"]["narrative"],
            }

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary saved: {summary_path}")
    print("Done.")


if __name__ == "__main__":
    main()
