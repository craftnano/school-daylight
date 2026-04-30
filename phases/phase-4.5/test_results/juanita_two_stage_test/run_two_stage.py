# PURPOSE: Two-stage pipeline experiment — Haiku triage + Sonnet narrative for Juanita HS
# INPUTS: MongoDB findings for Juanita HS (530423000670)
# OUTPUTS: stage1_output.json, stage2_output.json, evaluation.md
# DOES NOT: Modify any existing prompts, configs, or logs
# This is a standalone experiment, not part of the main test harness.

import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
import anthropic

# Add project root to path so config.py is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
import config

JUANITA_NCES_ID = "530423000670"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
# Cached findings from Round 2 test run — used when MongoDB is unavailable
CACHED_RAW_PATH = os.path.join(
    config.PROJECT_ROOT, "phases", "phase-4.5", "test_results",
    "raw_responses", f"{JUANITA_NCES_ID}.json"
)

# --- Stage 1 Prompt: Haiku Triage ---
# Recency rules extracted verbatim from sonnet_layer3_prompt_test_v2.txt Rule 5
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

## YOUR TASK

For each finding below, output:
1. "include" or "exclude"
2. A one-line rule citation explaining why
3. For INCLUDED findings: a theme tag — one of: safety, legal, governance, academic, community_investment, recognition

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
      "theme": "safety|legal|governance|academic|community_investment|recognition",
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
STAGE2_PROMPT = """You are writing the web-sourced context section of a school briefing for parents. You will receive pre-triaged findings that have already passed editorial review. Your ONLY job is to write the narrative. Do not re-evaluate inclusion decisions.

## WRITING RULES

1. **Date-first:** Every finding must lead with the year. "In 2024, ..." or "In an undated report, ..."
2. **No individual names:** Use role descriptions only. "a teacher," "the principal," "the superintendent." Never output any person's name.
3. **No student names or identifiers:** Students are "a student," "a freshman," "several students." Nothing more specific.
4. **Death-related institutional responses:** When a finding involves a death, reference ONLY the institutional response — the lawsuit, settlement, investigation, or policy change and its outcome. Do NOT include any of the following, even if present in the source: manner of death (suicide, overdose, drowning, hanging, shooting, starvation, etc.); location of death — neither specific ("wooded area at the end of school property," "in the gymnasium") nor general ("on school grounds," "at the school," "near campus"); physical circumstances (time of day, what was found, who found them, what was used). Frame only around what the institution did, what it failed to do, or how it was held accountable. A reader should learn that there was litigation or an investigation, not how the death occurred.
5. **Consolidate related findings:** Multiple findings from the same incident = one paragraph.
6. **Neutral tone:** No evaluative language ("controversial," "divisive," "progressive," "conservative"). Pure factual reporting.
7. **District-level vs. building-specific attribution:** Lawsuits, settlements, and investigations against the district appear on all schools in the district, framed with "at the district level" or equivalent. Building-specific incidents (events that occurred at a particular school) appear only on that school's briefing. When you receive a finding, treat it as district-level if it names the district as the actor or defendant; treat it as building-specific only if it names a specific school as the locus of the incident.
8. **Gender-neutral student references:** Neutralize gendered language whenever it refers to a student. Replace "his daughter," "her son," "she," "he" with gender-neutral forms ("the student," "their child," "they") in any context where a student is the subject. Source text often retains gendered pronouns; do not pass them through. This prevents identification through demographic narrowing. Gendered pronouns for adults in institutional roles (teachers, administrators) are also disallowed under Rule 2 — use the role title instead.

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


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Juanita HS Two-Stage Pipeline Test — {timestamp}")
    print()

    # --- Load Juanita findings ---
    # Try MongoDB first; fall back to cached raw response from previous test run
    all_findings = None
    school_name = None
    district_name = None

    try:
        client_mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client_mongo["schooldaylight"]
        collection = db.schools
        doc = collection.find_one({"_id": JUANITA_NCES_ID})
        if doc:
            school_name = doc.get("name", "Unknown")
            district_name = doc.get("district", {}).get("name", "Unknown")
            context_findings = doc.get("context", {}).get("findings", []) or []
            district_findings = doc.get("district_context", {}).get("findings", []) or []
            all_findings = context_findings + district_findings
            print(f"Loaded findings from MongoDB")
    except Exception as e:
        print(f"MongoDB unavailable ({type(e).__name__}), loading from cached raw response")

    if all_findings is None:
        if not os.path.exists(CACHED_RAW_PATH):
            print(f"ERROR: No cached findings at {CACHED_RAW_PATH} and MongoDB unavailable.")
            sys.exit(1)
        with open(CACHED_RAW_PATH, "r") as f:
            cached = json.load(f)
        school_name = cached.get("school_name", "Unknown")
        district_name = cached.get("district_name", "Unknown")
        all_findings = cached.get("findings_in", [])
        print(f"Loaded findings from cached file")

    print(f"School: {school_name}")
    print(f"District: {district_name}")
    print(f"Total findings: {len(all_findings)}")
    print()

    # --- Prepare findings for Stage 1 ---
    # Number each finding for reference
    findings_for_prompt = []
    for i, f in enumerate(all_findings):
        findings_for_prompt.append({
            "index": i + 1,
            "category": f.get("category", "unknown"),
            "date": f.get("date") or "undated",
            "confidence": f.get("confidence", "unknown"),
            "sensitivity": f.get("sensitivity", "normal"),
            "summary": f.get("summary", "No summary"),
        })

    findings_json = json.dumps(findings_for_prompt, indent=2, default=str)

    # --- Stage 1: Haiku Triage ---
    print("=" * 60)
    print("STAGE 1: Haiku Triage")
    print("=" * 60)

    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    stage1_user_msg = (
        f"School: {school_name}\n"
        f"District: {district_name}\n"
        f"NCES ID: {JUANITA_NCES_ID}\n\n"
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

    print(f"Haiku: {stage1_usage['input_tokens']} in / {stage1_usage['output_tokens']} out (model: {stage1_usage['actual_model']})")

    # Parse Stage 1 output
    import re
    stage1_parsed = None
    try:
        stage1_parsed = json.loads(stage1_raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", stage1_raw, re.DOTALL)
        if match:
            try:
                stage1_parsed = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        if not stage1_parsed:
            match = re.search(r"\{.*\}", stage1_raw, re.DOTALL)
            if match:
                try:
                    stage1_parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

    if not stage1_parsed:
        print("ERROR: Could not parse Stage 1 output as JSON.")
        print("Raw output:")
        print(stage1_raw)
        sys.exit(1)

    included = stage1_parsed.get("included", [])
    excluded = stage1_parsed.get("excluded", [])
    print(f"Included: {len(included)} findings")
    print(f"Excluded: {len(excluded)} findings")
    print()

    for item in included:
        idx = item.get("finding_index", "?")
        theme = item.get("theme", "?")
        rationale = item.get("rationale", "no rationale")
        print(f"  INCLUDE [{idx}] ({theme}): {rationale}")

    for item in excluded:
        idx = item.get("finding_index", "?")
        rationale = item.get("rationale", "no rationale")
        print(f"  EXCLUDE [{idx}]: {rationale}")

    # Save Stage 1 output
    stage1_path = os.path.join(OUTPUT_DIR, "stage1_output.json")
    with open(stage1_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "model": HAIKU_MODEL,
            "actual_model": stage1_usage["actual_model"],
            "usage": stage1_usage,
            "raw_response": stage1_raw,
            "parsed": stage1_parsed,
            "findings_input": findings_for_prompt,
        }, f, indent=2, default=str)
    print(f"\nStage 1 saved: {stage1_path}")

    # --- Stage 2: Sonnet Narrative ---
    print()
    print("=" * 60)
    print("STAGE 2: Sonnet Narrative")
    print("=" * 60)

    # Build Stage 2 input from Stage 1 included findings
    stage2_findings = json.dumps(included, indent=2, default=str)

    stage2_user_msg = (
        f"School: {school_name}\n"
        f"District: {district_name}\n"
        f"NCES ID: {JUANITA_NCES_ID}\n\n"
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

    print(f"Sonnet: {stage2_usage['input_tokens']} in / {stage2_usage['output_tokens']} out (model: {stage2_usage['actual_model']})")

    # Parse Stage 2 output
    stage2_parsed = None
    try:
        stage2_parsed = json.loads(stage2_raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", stage2_raw, re.DOTALL)
        if match:
            try:
                stage2_parsed = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        if not stage2_parsed:
            match = re.search(r"\{.*\}", stage2_raw, re.DOTALL)
            if match:
                try:
                    stage2_parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

    narrative = ""
    if stage2_parsed:
        narrative = stage2_parsed.get("narrative", "")
    else:
        narrative = stage2_raw

    print()
    print("--- NARRATIVE OUTPUT ---")
    print(narrative)
    print("--- END NARRATIVE ---")

    # Save Stage 2 output
    stage2_path = os.path.join(OUTPUT_DIR, "stage2_output.json")
    with open(stage2_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "model": SONNET_MODEL,
            "actual_model": stage2_usage["actual_model"],
            "usage": stage2_usage,
            "raw_response": stage2_raw,
            "parsed": stage2_parsed,
            "narrative": narrative,
        }, f, indent=2, default=str)
    print(f"\nStage 2 saved: {stage2_path}")

    # --- Cost ---
    total_in = stage1_usage["input_tokens"] + stage2_usage["input_tokens"]
    total_out = stage1_usage["output_tokens"] + stage2_usage["output_tokens"]
    # Haiku: $0.80/MTok in, $4/MTok out; Sonnet: $3/MTok in, $15/MTok out
    haiku_cost = (stage1_usage["input_tokens"] / 1_000_000) * 0.80 + (stage1_usage["output_tokens"] / 1_000_000) * 4.0
    sonnet_cost = (stage2_usage["input_tokens"] / 1_000_000) * 3.0 + (stage2_usage["output_tokens"] / 1_000_000) * 15.0
    total_cost = haiku_cost + sonnet_cost

    print()
    print("=" * 60)
    print("COST SUMMARY")
    print("=" * 60)
    print(f"Stage 1 (Haiku):  {stage1_usage['input_tokens']:,} in / {stage1_usage['output_tokens']:,} out = ${haiku_cost:.4f}")
    print(f"Stage 2 (Sonnet): {stage2_usage['input_tokens']:,} in / {stage2_usage['output_tokens']:,} out = ${sonnet_cost:.4f}")
    print(f"Total:            {total_in:,} in / {total_out:,} out = ${total_cost:.4f}")

    # --- Hallucination check ---
    print()
    print("=" * 60)
    print("HALLUCINATION CHECK")
    print("=" * 60)
    hallucination_phrases = [
        "placed on leave",
        "later cleared",
        "cleared in",
        "reinstated",
        "no charges were filed",
        "charges were dropped",
        "found not guilty",
        "exonerated",
        "returned to duty",
    ]
    hallucinations_found = []
    for phrase in hallucination_phrases:
        if phrase.lower() in narrative.lower():
            hallucinations_found.append(phrase)

    if hallucinations_found:
        print(f"WARNING: Potential hallucinations detected: {hallucinations_found}")
    else:
        print("CLEAN: None of the checked hallucination phrases found in narrative.")

    print()
    print("Done. See evaluation.md for full analysis.")


if __name__ == "__main__":
    main()
