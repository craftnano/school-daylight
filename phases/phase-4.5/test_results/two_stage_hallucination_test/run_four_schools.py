# PURPOSE: Two-stage pipeline hallucination validation on 4 schools
# INPUTS: Cached raw responses from Round 2 test run
# OUTPUTS: Per-school JSON files + summary evaluation
# DOES NOT: Modify any existing prompts, configs, or logs
# This is a standalone experiment extending the Juanita two-stage test.

import os
import sys
import json
import re
import time
from datetime import datetime
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

SCHOOLS = [
    {
        "nces_id": "530033000043",
        "label": "Bainbridge Island SD",
        "reason": "Multiple findings including suicide settlement, bullying verdict, abuse lawsuit. High narrative complexity.",
    },
    {
        "nces_id": "530048000119",
        "label": "Bethel SD",
        "reason": "2016 + 2025 pattern exception. Two findings connected across a decade.",
    },
    {
        "nces_id": "530039000082",
        "label": "Phantom Lake Elementary",
        "reason": "Principal placed on administrative leave twice. Pattern detection case.",
    },
    {
        "nces_id": "530807001334",
        "label": "Soap Lake Elementary",
        "reason": "Superintendent investigation with exoneration. Resolution is stated in the finding.",
    },
]

# --- Stage 1 Prompt: Haiku Triage ---
# Same as Juanita test — recency rules from sonnet_layer3_prompt_test_v2.txt
STAGE1_PROMPT = """You are a finding triage assistant for school briefings. Your job is to evaluate each finding and decide whether it should be included in or excluded from a parent-facing narrative.

## RECENCY RULES — Apply to every finding

- Adverse outcomes (settlements, convictions, sustained investigations): include only if within 10 years
- Allegations, dismissals, unresolved matters: include only if within 5 years
- PATTERN EXCEPTION: If 2+ findings of the same type (e.g., sexual abuse settlements, failure-to-report cases) exist within a 20-year window, ALL findings in the pattern stay. The pattern is the finding.
- CONDUCT-DATE ANCHOR: When a recent institutional response (lawsuit filing, settlement, investigation, or policy change) addresses underlying conduct that occurred more than 20 years ago, exclude the finding — even if the institutional response itself is recent. The date of the institutional response alone does not make ancient conduct current. Exception: if the finding is part of a documented pattern where at least one other finding of the same type involves conduct within the last 20 years, include all findings in the pattern. When evaluating recency, anchor to when the conduct occurred, not when the institution responded to it.
- DISMISSED CASES: Dismissed, withdrawn, or otherwise resolved-without-adverse-finding cases are subject to the 5-year window, not the 10-year window. The pattern exception does not apply to dismissed cases — a pattern requires sustained findings, not sustained allegations that were rejected.
- SEVERITY EXCEPTION: If a finding involves credible allegations of sexual violence against students AND institutional suppression of reporting or investigation (e.g., administrators discouraging police involvement, failure to notify authorities), the finding may be included beyond the standard 10-year window even without a pattern match. The combination of severity and institutional complicity makes these findings relevant to current school culture regardless of age.

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

# --- Stage 2 Prompt: Sonnet Narrative Writing ---
# Enhanced from Juanita test with student identifier stripping, consolidation, and phrasing variety
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


def load_round1_narrative(nces_id):
    """Load the Round 1 single-stage narrative for comparison."""
    path = os.path.join(RAW_RESPONSES_DIR, f"{nces_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        data = json.load(f)
    parsed = data.get("parsed")
    if parsed:
        return parsed.get("narrative", "")
    return data.get("raw_response", "")


def parse_json_response(raw_text):
    """Parse JSON from an API response, handling markdown fences."""
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


def check_hallucinations(narrative, included_findings):
    """
    Compare every factual claim in the narrative against the included findings.
    Returns list of potential hallucinations found.
    """
    # Check for specific known hallucination patterns
    hallucination_phrases = [
        "placed on leave",
        "later cleared",
        "cleared in",
        "reinstated",
        "no charges were filed",
        "charges were dropped",
        "found not guilty",
        "returned to duty",
        "resigned",
        "was fired",
        "was terminated",
        "stepped down",
        "was suspended",
        "was arrested",
    ]

    # Build a combined text of all included finding texts for comparison
    included_text = ""
    for f in included_findings:
        included_text += " " + f.get("original_text", "")

    included_lower = included_text.lower()
    narrative_lower = narrative.lower()

    found = []
    for phrase in hallucination_phrases:
        if phrase in narrative_lower and phrase not in included_lower:
            found.append(f"'{phrase}' appears in narrative but not in any included finding")

    return found


def check_student_identifiers(narrative):
    """Check for student age, disability, or identifying descriptors."""
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
        matches = re.findall(pattern, narrative, re.IGNORECASE)
        if matches:
            for m in matches:
                found.append(f"{label}: '{m}'")

    return found


def run_school(api_client, school_info, timestamp):
    """Run two-stage pipeline on one school. Returns results dict."""
    nces_id = school_info["nces_id"]
    label = school_info["label"]

    print(f"\n{'=' * 60}")
    print(f"{label} ({nces_id})")
    print(f"{'=' * 60}")

    # Load findings
    school_name, district_name, findings = load_cached_findings(nces_id)
    if findings is None:
        print(f"  ERROR: No cached findings for {nces_id}")
        return {"error": f"No cached findings for {nces_id}"}

    print(f"  School: {school_name}")
    print(f"  District: {district_name}")
    print(f"  Findings: {len(findings)}")

    # Prepare findings for Stage 1
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

    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)

    # --- Stage 1: Haiku ---
    print(f"\n  Stage 1 (Haiku)...")
    stage1_user_msg = (
        f"School: {school_name}\n"
        f"District: {district_name}\n"
        f"NCES ID: {nces_id}\n\n"
        f"Findings to evaluate:\n\n{findings_json}\n\n"
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
    print(f"  Haiku: {stage1_usage['input_tokens']} in / {stage1_usage['output_tokens']} out")

    stage1_parsed = parse_json_response(stage1_raw)
    if not stage1_parsed:
        print(f"  ERROR: Could not parse Stage 1 JSON")
        return {"error": "Stage 1 JSON parse failure", "stage1_raw": stage1_raw}

    included = stage1_parsed.get("included", [])
    excluded = stage1_parsed.get("excluded", [])
    print(f"  Included: {len(included)}, Excluded: {len(excluded)}")

    for item in included:
        idx = item.get("finding_index", "?")
        theme = item.get("theme", "?")
        rationale = item.get("rationale", "")
        print(f"    INCLUDE [{idx}] ({theme}): {rationale[:80]}")
    for item in excluded:
        idx = item.get("finding_index", "?")
        rationale = item.get("rationale", "")
        print(f"    EXCLUDE [{idx}]: {rationale[:80]}")

    time.sleep(RATE_LIMIT_SECONDS)

    # --- Stage 2: Sonnet ---
    print(f"\n  Stage 2 (Sonnet)...")

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
        print(f"  Sonnet: {stage2_usage['input_tokens']} in / {stage2_usage['output_tokens']} out")

        stage2_parsed = parse_json_response(stage2_raw)
        narrative = stage2_parsed.get("narrative", "") if stage2_parsed else stage2_raw

    # --- Checks ---
    hallucinations = check_hallucinations(narrative, included)
    student_ids = check_student_identifiers(narrative)

    print(f"\n  Hallucinations: {len(hallucinations)}")
    for h in hallucinations:
        print(f"    {h}")
    print(f"  Student ID leaks: {len(student_ids)}")
    for s in student_ids:
        print(f"    {s}")

    # Load Round 1 comparison
    round1_narrative = load_round1_narrative(nces_id)

    return {
        "nces_id": nces_id,
        "label": label,
        "school_name": school_name,
        "district_name": district_name,
        "findings_count": len(findings),
        "stage1": {
            "raw": stage1_raw,
            "parsed": stage1_parsed,
            "usage": stage1_usage,
            "included_count": len(included),
            "excluded_count": len(excluded),
        },
        "stage2": {
            "raw": stage2_raw,
            "parsed": stage2_parsed,
            "narrative": narrative,
            "usage": stage2_usage,
        },
        "hallucinations": hallucinations,
        "student_id_leaks": student_ids,
        "round1_narrative": round1_narrative,
    }


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Two-Stage Hallucination Validation — {timestamp}")
    print(f"Schools: {len(SCHOOLS)}")
    print(f"Models: {HAIKU_MODEL} (Stage 1), {SONNET_MODEL} (Stage 2)")

    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    all_results = {}

    for i, school in enumerate(SCHOOLS):
        result = run_school(api_client, school, timestamp)
        all_results[school["nces_id"]] = result

        # Save individual school result
        school_path = os.path.join(OUTPUT_DIR, f"{school['nces_id']}_{school['label'].replace(' ', '_')}.json")
        with open(school_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        # Rate limit between schools (except last)
        if i < len(SCHOOLS) - 1 and "error" not in result:
            time.sleep(RATE_LIMIT_SECONDS)

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    total_hallucinations = 0
    total_student_ids = 0
    total_haiku_in = 0
    total_haiku_out = 0
    total_sonnet_in = 0
    total_sonnet_out = 0

    for nid, r in all_results.items():
        if "error" in r:
            continue
        total_hallucinations += len(r["hallucinations"])
        total_student_ids += len(r["student_id_leaks"])
        total_haiku_in += r["stage1"]["usage"]["input_tokens"]
        total_haiku_out += r["stage1"]["usage"]["output_tokens"]
        total_sonnet_in += r["stage2"]["usage"]["input_tokens"]
        total_sonnet_out += r["stage2"]["usage"]["output_tokens"]

    haiku_cost = (total_haiku_in / 1_000_000) * 0.80 + (total_haiku_out / 1_000_000) * 4.0
    sonnet_cost = (total_sonnet_in / 1_000_000) * 3.0 + (total_sonnet_out / 1_000_000) * 15.0
    total_cost = haiku_cost + sonnet_cost

    print(f"Total hallucinations: {total_hallucinations}")
    print(f"Total student ID leaks: {total_student_ids}")
    print(f"Haiku cost: ${haiku_cost:.4f} ({total_haiku_in:,} in / {total_haiku_out:,} out)")
    print(f"Sonnet cost: ${sonnet_cost:.4f} ({total_sonnet_in:,} in / {total_sonnet_out:,} out)")
    print(f"Total cost: ${total_cost:.4f}")

    # Save summary
    summary = {
        "timestamp": timestamp,
        "schools_tested": len(SCHOOLS),
        "total_hallucinations": total_hallucinations,
        "total_student_id_leaks": total_student_ids,
        "cost": {
            "haiku": {"input_tokens": total_haiku_in, "output_tokens": total_haiku_out, "cost": round(haiku_cost, 4)},
            "sonnet": {"input_tokens": total_sonnet_in, "output_tokens": total_sonnet_out, "cost": round(sonnet_cost, 4)},
            "total": round(total_cost, 4),
        },
        "per_school": {},
    }
    for nid, r in all_results.items():
        if "error" in r:
            summary["per_school"][nid] = {"error": r["error"]}
        else:
            summary["per_school"][nid] = {
                "label": r["label"],
                "findings": r["findings_count"],
                "included": r["stage1"]["included_count"],
                "excluded": r["stage1"]["excluded_count"],
                "hallucinations": len(r["hallucinations"]),
                "hallucination_details": r["hallucinations"],
                "student_id_leaks": len(r["student_id_leaks"]),
                "student_id_details": r["student_id_leaks"],
            }

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary saved: {summary_path}")
    print("Done.")


if __name__ == "__main__":
    main()
