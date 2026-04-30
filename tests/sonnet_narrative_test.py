# PURPOSE: Test Sonnet editorial rule compliance on Phase 4 enrichment findings
# INPUTS: MongoDB context/district_context findings, prompts/sonnet_layer3_prompt_test_v2.txt
# OUTPUTS: phases/phase-4.5/test_results/test_run_YYYY-MM-DD_HHMMSS.md, raw_responses/*.json
# DOES NOT: Write to MongoDB, modify pipeline, modify prompts
# PHASE: 4.5 — Sonnet Editorial Rule Testing (Round 2, v2 prompt)

import os
import sys
import json
import yaml
import re
import time
from datetime import datetime
from pymongo import MongoClient
import anthropic

# Add project root to path so config.py is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# --- Constants ---

MODEL = "claude-sonnet-4-6"
MAX_OUTPUT_TOKENS = 2000
RATE_LIMIT_SECONDS = 12  # 5 requests per minute
MAX_SCHOOLS_PER_RUN = 50  # safety cap (40 from plan + keyword-scan additions)

# 14 tests, numbered to match the test plan (Test 10 is a data check, not a Sonnet test)
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

DEATH_KEYWORDS = [
    "suicide", "death", "died", "killed", "fatal", "drowning",
    "shooting", "deceased", "tragedy", "memorial", "passed away",
    "overdose", "homicide",
]


# ============================================================
# DATA ACCESS (read-only)
# ============================================================

def connect_to_mongodb():
    """Connect to MongoDB Atlas and return the schools collection."""
    if not config.MONGO_URI:
        print("ERROR: MONGO_URI is empty. Check your .env file.")
        print("  Expected: MONGO_URI=mongodb+srv://...")
        print("  File location: .env in project root")
        sys.exit(1)

    client = MongoClient(config.MONGO_URI)
    # Database name matches pipeline scripts (pipeline/17_haiku_enrichment.py line 46)
    db = client["schooldaylight"]
    count = db.schools.count_documents({})
    print(f"Connected to MongoDB. {count} schools in collection.")
    return db.schools


def load_prompt():
    """Load the Sonnet Layer 3 prompt from the prompts directory."""
    prompt_path = os.path.join(config.PROJECT_ROOT, "prompts", "sonnet_layer3_prompt_test_v2.txt")
    if not os.path.exists(prompt_path):
        print(f"ERROR: Prompt file not found at {prompt_path}")
        sys.exit(1)
    with open(prompt_path, "r") as f:
        return f.read()


def load_test_config():
    """Load test school configuration from YAML."""
    config_path = os.path.join(config.PROJECT_ROOT, "tests", "sonnet_test_config.yaml")
    if not os.path.exists(config_path):
        print(f"ERROR: Test config not found at {config_path}")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_school_findings(collection, nces_id):
    """
    Pull context and district_context findings for a school.
    Returns (school_name, district_name, combined_findings_list) or (None, None, None).
    """
    doc = collection.find_one({"_id": nces_id})
    if not doc:
        return None, None, None

    school_name = doc.get("name", "Unknown")
    district_name = doc.get("district", {}).get("name", "Unknown")

    context_findings = doc.get("context", {}).get("findings", []) or []
    district_findings = doc.get("district_context", {}).get("findings", []) or []

    return school_name, district_name, context_findings + district_findings


# ============================================================
# DYNAMIC SCHOOL RESOLUTION
# ============================================================

def find_death_keyword_schools(collection, keywords):
    """
    Query MongoDB for all schools whose findings contain death/suicide keywords.
    Returns list of {nces_id, name, district}.
    """
    # Build regex alternation: suicide|death|died|...
    pattern = "|".join(re.escape(kw) for kw in keywords)

    query = {
        "$or": [
            {"context.findings.summary": {"$regex": pattern, "$options": "i"}},
            {"district_context.findings.summary": {"$regex": pattern, "$options": "i"}},
        ]
    }
    cursor = collection.find(query, {"_id": 1, "name": 1, "district.name": 1})

    schools = []
    for doc in cursor:
        schools.append({
            "nces_id": doc["_id"],
            "name": doc.get("name", "Unknown"),
            "district": doc.get("district", {}).get("name", "Unknown"),
        })
    return schools


def find_oak_harbor_volunteer(collection):
    """
    Query MongoDB for an Oak Harbor SD school with a volunteer-related finding.
    Returns (nces_id, school_name) or (None, None).
    """
    query = {
        "district.name": {"$regex": "Oak Harbor", "$options": "i"},
        "$or": [
            {"context.findings.summary": {"$regex": "volunteer", "$options": "i"}},
            {"district_context.findings.summary": {"$regex": "volunteer", "$options": "i"}},
        ],
    }
    doc = collection.find_one(query, {"_id": 1, "name": 1})
    if doc:
        return doc["_id"], doc.get("name", "Unknown")
    return None, None


def pick_random_dated_schools(collection, count, exclude_ids):
    """
    Pick `count` random enriched schools with at least one dated finding.
    Excludes schools already in the test set.
    """
    pipeline = [
        {"$match": {
            "context.status": "enriched",
            "context.findings": {"$exists": True, "$ne": []},
            "_id": {"$nin": list(exclude_ids)},
        }},
        {"$sample": {"size": count * 3}},  # oversample to filter
    ]
    candidates = list(collection.aggregate(pipeline))

    selected = []
    for doc in candidates:
        if len(selected) >= count:
            break
        findings = doc.get("context", {}).get("findings", [])
        if any(f.get("date") for f in findings):
            selected.append({
                "nces_id": doc["_id"],
                "name": doc.get("name", "Unknown"),
            })
    return selected


# ============================================================
# TEST 10: DATA-LAYER CONTAMINATION CHECK
# ============================================================

def check_east_valley_contamination(collection, nces_id):
    """
    Check if East Valley SD (Yakima) has findings that belong to East Valley SD (Spokane).
    Returns a plain-English result string.
    """
    doc = collection.find_one({"_id": nces_id})
    if not doc:
        return f"School {nces_id} not found in database."

    findings = []
    findings.extend(doc.get("context", {}).get("findings", []) or [])
    findings.extend(doc.get("district_context", {}).get("findings", []) or [])

    if not findings:
        return f"School {nces_id} has no findings. Nothing to check."

    issues = []
    for f in findings:
        summary = (f.get("summary", "") or "").lower()
        source = (f.get("source_name", "") or "").lower()
        url = (f.get("source_url", "") or "").lower()
        combined = summary + " " + source + " " + url
        # Kaplicky is the specific principal flagged in the test plan
        if "kaplicky" in combined or "spokane" in combined:
            issues.append(
                f"  CONTAMINATION: '{f.get('summary', '')[:150]}'\n"
                f"    Source: {f.get('source_name', 'unknown')} | {f.get('source_url', 'no url')}"
            )

    if issues:
        return "DATA FIX NEEDED — findings attributed to East Valley Yakima may belong to East Valley Spokane:\n" + "\n".join(issues)
    return "No Spokane contamination detected in East Valley Yakima findings."


# ============================================================
# SONNET API CALL
# ============================================================

def call_sonnet(client, system_prompt, school_name, district_name, nces_id, findings):
    """
    Send findings to Sonnet and return (raw_text, usage_dict).
    Raises on API errors — caller handles retries.
    """
    findings_json = json.dumps(findings, indent=2, default=str)

    user_message = (
        f"School: {school_name}\n"
        f"District: {district_name}\n"
        f"NCES ID: {nces_id}\n\n"
        f"Context findings from web search enrichment:\n\n"
        f"{findings_json}\n\n"
        f"Generate the Layer 3 web-sourced context narrative for this school "
        f"following all editorial rules in your system prompt. "
        f"Return your response as JSON with the fields specified in the OUTPUT FORMAT section."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text from response blocks
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

    return raw_text, usage


def parse_sonnet_json(raw_text):
    """
    Parse Sonnet's JSON response. Handles raw JSON, markdown fences, and embedded JSON.
    Returns parsed dict or None.
    """
    # Try raw JSON
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Try markdown code fence
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first JSON object
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# AUTOMATED CHECKS
# ============================================================

def extract_names_from_findings(findings):
    """
    Extract likely PERSON names from finding summaries.
    Returns a set of strings. Filters aggressively to exclude institutional names,
    geographic names, organizational names, and common phrases.
    """
    # Institutional / organizational / geographic words that appear in multi-word
    # capitalized phrases but are NOT person names. Any match containing one of
    # these tokens (case-insensitive) is discarded.
    institutional_tokens = {
        # School/district terms
        "school", "district", "elementary", "middle", "high", "academy",
        "public", "schools", "charter", "magnet", "montessori", "stem",
        "preschool", "kindergarten", "learning", "program", "center",
        "partnership", "education", "educational",
        # Government / legal
        "county", "state", "city", "federal", "national", "department",
        "board", "commission", "committee", "council", "court", "superior",
        "supreme", "appellate", "circuit", "municipal", "tribal",
        "investigation", "investigator", "audit", "auditor", "attorney",
        "sheriff", "police", "enforcement", "administration",
        # Organizations
        "association", "foundation", "institute", "university", "college",
        "corporation", "company", "group", "team", "club", "union",
        "society", "alliance", "coalition", "network", "agency", "bureau",
        "office", "services", "service", "authority",
        # Geography
        "washington", "oregon", "california", "island", "lake", "valley",
        "creek", "river", "mountain", "harbor", "bay", "park", "ridge",
        "hill", "meadow", "forest", "plain", "spring", "falls",
        "spokane", "seattle", "tacoma", "bellevue", "bellingham",
        "everett", "olympia", "vancouver", "portland", "bremerton",
        "edmonds", "issaquah", "redmond", "kirkland", "renton",
        "snohomish", "whatcom", "kitsap", "pierce", "thurston",
        "skagit", "clark", "lewis", "mason", "chelan", "yakima",
        "bainbridge", "whidbey", "camano", "orcas", "vashon",
        # Legal terms
        "sexual", "assault", "misconduct", "harassment", "discrimination",
        "retaliation", "negligence", "wrongful", "motion", "degree",
        "attempted", "possession", "explicit", "conduct", "motivation",
        "felony", "misdemeanor", "conviction", "allegation",
        # Common non-name capitalized words
        "title", "change", "special", "general", "community", "american",
        "christian", "catholic", "lutheran", "baptist", "church",
        "food", "health", "care", "water", "sewer", "fire", "emergency",
        "construction", "bond", "budget", "advisory", "resource", "fair",
        "sports", "unified", "technology", "connectivity", "fund",
        "news", "best", "lighthouse", "deer", "olympic", "view",
        "hand", "green", "broad", "crescent", "madrona", "cedar",
        "civil", "rights", "orchestra", "chamber", "minor", "engaged",
        "medicaid", "administrative", "match", "transit", "safety",
        "management", "effective", "handy", "directors", "resolution",
        # Months and time words (appear capitalized at sentence start)
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "former", "current", "interim",
    }

    names = set()
    for f in findings:
        summary = f.get("summary", "") or ""
        # Match 2-4 consecutive capitalized words
        matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", summary)
        for m in matches:
            tokens = m.lower().split()
            # Skip if ANY token is institutional/geographic/organizational
            if any(t in institutional_tokens for t in tokens):
                continue
            # Skip single-word matches that slipped through (shouldn't happen with {1,3})
            if len(tokens) < 2:
                continue
            names.add(m)
    return names


def check_names_in_output(narrative, input_names):
    """
    Check if any person names from input findings appear in the narrative output.
    Only flags whole-word matches to avoid false positives.
    """
    violations = []

    for name in input_names:
        # Check full name as whole-word match
        if re.search(r"\b" + re.escape(name) + r"\b", narrative, re.IGNORECASE):
            violations.append(f"Person name in output: '{name}'")
            continue
        # Check individual tokens (likely last names) — only tokens 4+ chars
        # that aren't common words
        common_words = {
            # Roles — these appear in both input names and output role references
            "judge", "retired", "vice", "deputy", "former", "acting",
            "interim", "assistant", "associate", "senior", "junior",
            "doctor", "pastor", "reverend", "coach", "officer",
            "superintendent", "principal", "director", "manager",
            "teacher", "counselor", "administrator", "president",
            "secretary", "treasurer", "chair", "commissioner",
            # Non-name words that appear in extracted "names"
            "medicaid", "administrative", "safety", "management",
            "sexual", "motivation", "degree", "assault", "conduct",
            "explicit", "minor", "engaged", "attempted", "possession",
            "civil", "rights", "orchestra", "chamber", "history",
            "effective", "handy",
        }
        parts = name.split()
        for part in parts:
            if len(part) >= 5 and part.lower() not in common_words:
                if re.search(r"\b" + re.escape(part) + r"\b", narrative, re.IGNORECASE):
                    violations.append(f"Possible name fragment '{part}' (from '{name}')")

    return violations


def check_death_keywords_in_output(narrative):
    """
    Check if forbidden death/manner-of-death details appear in output.
    Returns (hard_violations, soft_flags).
    Hard violations = words that should NEVER appear.
    Soft flags = words that might be acceptable in institutional-response framing but need review.
    """
    # These should never appear — they describe manner of death
    # Uses word-boundary matching to avoid false positives (e.g. "changed" matching "hanged")
    forbidden = [
        "suicide", "starvation", "starved", "overdose", "overdosed",
        "drowning", "drowned", "hanged", "hanging", "shot himself",
        "shot herself", "jumped from", "asphyxia", "suffocated",
    ]
    # These might appear in acceptable institutional framing — flag for review
    review_words = [
        "death", "died", "killed", "fatal", "deceased", "homicide",
    ]

    violations = []
    flags = []

    for word in forbidden:
        # Word-boundary match to prevent substring false positives
        if re.search(r"\b" + re.escape(word) + r"\b", narrative, re.IGNORECASE):
            violations.append(f"FORBIDDEN manner-of-death detail: '{word}'")

    for word in review_words:
        if re.search(r"\b" + re.escape(word) + r"\b", narrative, re.IGNORECASE):
            flags.append(f"Death-related word '{word}' — check if used in acceptable institutional-response framing")

    return violations, flags


def check_date_first(narrative):
    """
    Check that the narrative leads findings with year or 'undated' disclosure.
    Returns list of violation strings.
    """
    # If Sonnet returned "no findings" boilerplate, nothing to check
    if "No significant web-sourced context" in narrative:
        return []

    violations = []
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", narrative))
    has_undated = bool(re.search(r"undated", narrative, re.IGNORECASE))

    if not has_year and not has_undated:
        violations.append("Narrative describes events but contains no year references or undated disclosures")

    return violations


def check_evaluative_language(narrative):
    """Check for banned evaluative/editorial words (political neutrality test)."""
    banned = [
        "controversial", "divisive", "progressive", "conservative",
        "traditional values", "culture war", "woke", "anti-woke",
        "left-wing", "right-wing", "liberal agenda",
    ]
    violations = []
    narrative_lower = narrative.lower()
    for phrase in banned:
        if phrase in narrative_lower:
            violations.append(f"Evaluative language: '{phrase}'")
    return violations


def check_json_structure(parsed):
    """Validate that Sonnet returned the required transparency fields."""
    if parsed is None:
        return ["Failed to parse Sonnet response as JSON"]

    required = [
        "narrative", "findings_used", "findings_excluded",
        "names_stripped", "patterns_detected",
        "politically_sensitive", "undated_findings_present",
    ]
    issues = []
    for field in required:
        if field not in parsed:
            issues.append(f"Missing field: '{field}'")

    if "findings_used" in parsed and not isinstance(parsed["findings_used"], list):
        issues.append("findings_used should be a list")
    if "findings_excluded" in parsed and not isinstance(parsed["findings_excluded"], list):
        issues.append("findings_excluded should be a list")

    return issues


def run_all_checks(narrative, findings):
    """Run every automated check and return a results dict."""
    input_names = extract_names_from_findings(findings)
    death_violations, death_flags = check_death_keywords_in_output(narrative)

    return {
        "input_names_found": sorted(input_names),
        "name_violations": check_names_in_output(narrative, input_names),
        "death_violations": death_violations,
        "death_flags": death_flags,
        "date_violations": check_date_first(narrative),
        "evaluative_violations": check_evaluative_language(narrative),
    }


# ============================================================
# REPORT GENERATION
# ============================================================

def generate_report(report_path, results, contamination_result, timestamp, models_seen):
    """Write the human-readable Markdown test report."""
    lines = []
    lines.append("# Phase 4.5 — Sonnet Editorial Rule Test Report")
    lines.append(f"**Run:** {timestamp}")
    lines.append(f"**Requested model:** {MODEL}")
    lines.append(f"**Actual model(s) returned:** {', '.join(sorted(models_seen)) if models_seen else 'none'}")
    tested = [r for r in results.values() if "narrative" in r]
    skipped = [r for r in results.values() if "error" in r]
    lines.append(f"**Schools tested:** {len(tested)}")
    lines.append(f"**Schools skipped:** {len(skipped)}")
    lines.append("")

    # --- Summary table ---
    lines.append("## Summary")
    lines.append("")
    lines.append("| Test | Rule | Check Type | Schools | Auto Issues |")
    lines.append("|------|------|------------|---------|-------------|")

    for test_num in sorted(TEST_NAMES.keys()):
        schools_in_test = [nid for nid, r in results.items() if test_num in r.get("tests", [])]
        issue_count = 0
        check_type = "HUMAN REVIEW"

        for nid in schools_in_test:
            r = results[nid]
            checks = r.get("checks", {})
            if test_num == 1:
                check_type = "AUTO + REVIEW"
                if checks.get("death_violations"):
                    issue_count += 1
            elif test_num in (2, 7):
                check_type = "AUTO + REVIEW"
                if checks.get("name_violations"):
                    issue_count += 1
            elif test_num == 5:
                check_type = "AUTO"
                if checks.get("date_violations"):
                    issue_count += 1
            elif test_num == 6:
                check_type = "AUTO + REVIEW"
                if checks.get("evaluative_violations"):
                    issue_count += 1

        lines.append(
            f"| {test_num} | {TEST_NAMES[test_num]} | {check_type} | "
            f"{len(schools_in_test)} | {issue_count} |"
        )

    lines.append("")

    # --- Test 10 data check ---
    lines.append("---")
    lines.append("")
    lines.append("## Pre-Flight: Wrong-District Contamination (Data Layer Check)")
    lines.append("")
    lines.append(contamination_result)
    lines.append("")

    # --- Detailed results per test ---
    for test_num in sorted(TEST_NAMES.keys()):
        schools_in_test = [
            (nid, results[nid])
            for nid in results
            if test_num in results[nid].get("tests", [])
        ]
        if not schools_in_test:
            continue

        lines.append("---")
        lines.append("")
        lines.append(f"## Test {test_num}: {TEST_NAMES[test_num]}")
        lines.append("")

        for nces_id, r in schools_in_test:
            lines.append(f"### {r.get('school_name', 'Unknown')} ({nces_id})")
            lines.append("")

            if "error" in r:
                lines.append(f"**SKIPPED:** {r['error']}")
                lines.append("")
                continue

            lines.append(f"**Findings in:** {r.get('findings_count', 0)}")
            lines.append("")

            # Collapsible input findings
            if r.get("findings_in"):
                lines.append("<details>")
                lines.append("<summary>Input findings (click to expand)</summary>")
                lines.append("")
                for j, f in enumerate(r["findings_in"]):
                    cat = f.get("category", "unknown")
                    date = f.get("date", "undated")
                    conf = f.get("confidence", "unknown")
                    sens = f.get("sensitivity", "normal")
                    lines.append(f"**Finding {j+1}** ({cat}, {date}, confidence: {conf}, sensitivity: {sens})")
                    lines.append(f"> {f.get('summary', 'No summary')}")
                    lines.append("")
                lines.append("</details>")
                lines.append("")

            # Sonnet output
            narrative = r.get("narrative", "")
            lines.append("**Sonnet output:**")
            lines.append("")
            # Use blockquote, preserving paragraphs
            for para in narrative.split("\n\n"):
                para = para.strip()
                if para:
                    lines.append(f"> {para}")
                    lines.append(">")
            lines.append("")

            # What to check for this specific test
            check_inst = r.get("check_instructions", {}).get(test_num, "")
            if check_inst:
                lines.append(f"**What to check:** {check_inst}")
                lines.append("")

            # Automated check results relevant to this test
            checks = r.get("checks", {})
            auto_lines = []

            if test_num == 1:
                if checks.get("death_violations"):
                    auto_lines.append("FAIL (auto): " + "; ".join(checks["death_violations"]))
                else:
                    auto_lines.append("PASS (auto): No forbidden death/manner-of-death details")
                if checks.get("death_flags"):
                    for flag in checks["death_flags"]:
                        auto_lines.append(f"REVIEW: {flag}")

            if test_num in (2, 7):
                if checks.get("name_violations"):
                    auto_lines.append("FAIL (auto): " + "; ".join(checks["name_violations"]))
                else:
                    auto_lines.append("PASS (auto): No input names found in output")
                if checks.get("input_names_found"):
                    auto_lines.append(f"Names scanned: {', '.join(checks['input_names_found'])}")

            if test_num == 5:
                if checks.get("date_violations"):
                    auto_lines.append("FAIL (auto): " + "; ".join(checks["date_violations"]))
                else:
                    auto_lines.append("PASS (auto): Year references or undated disclosures present")

            if test_num == 6:
                if checks.get("evaluative_violations"):
                    auto_lines.append("FAIL (auto): " + "; ".join(checks["evaluative_violations"]))
                else:
                    auto_lines.append("PASS (auto): No banned evaluative language detected")

            # JSON structure — always relevant
            json_issues = r.get("json_issues", [])
            if json_issues:
                auto_lines.append("FAIL (auto): JSON — " + "; ".join(json_issues))

            if auto_lines:
                for al in auto_lines:
                    lines.append(f"- {al}")
                lines.append("")

            # Transparency fields from Sonnet
            parsed = r.get("parsed")
            if parsed:
                excluded = parsed.get("findings_excluded", [])
                if excluded:
                    lines.append("**Findings excluded by Sonnet:**")
                    for exc in excluded:
                        if isinstance(exc, dict):
                            lines.append(f"- {exc.get('finding_id', '?')}: {exc.get('reason', 'no reason')}")
                        else:
                            lines.append(f"- {exc}")
                    lines.append("")

                patterns = parsed.get("patterns_detected", [])
                if patterns:
                    lines.append(f"**Patterns detected:** {', '.join(str(p) for p in patterns)}")
                    lines.append("")

            lines.append("**PASS / FAIL / NEEDS REVIEW:** ______")
            lines.append("")
            lines.append("**Builder notes:** ______")
            lines.append("")

    # --- Cost summary ---
    lines.append("---")
    lines.append("")
    lines.append("## Cost Summary")
    lines.append("")
    total_in = sum(r.get("usage", {}).get("input_tokens", 0) for r in results.values())
    total_out = sum(r.get("usage", {}).get("output_tokens", 0) for r in results.values())
    # Sonnet pricing as of 2026-02: $3/MTok input, $15/MTok output
    cost = (total_in / 1_000_000) * 3.0 + (total_out / 1_000_000) * 15.0
    lines.append(f"- Input tokens: {total_in:,}")
    lines.append(f"- Output tokens: {total_out:,}")
    lines.append(f"- Estimated cost: ${cost:.2f}")
    lines.append(f"- Model(s): {', '.join(sorted(models_seen)) if models_seen else 'none'}")
    lines.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Phase 4.5 Sonnet Editorial Rule Test — {timestamp}")
    print(f"Model: {MODEL}")
    print()

    # --- Setup output directories ---
    results_dir = os.path.join(config.PHASES_DIR, "phase-4.5", "test_results")
    raw_dir = os.path.join(results_dir, "raw_responses")
    os.makedirs(raw_dir, exist_ok=True)

    # --- Load prompt ---
    system_prompt = load_prompt()
    print(f"Loaded Sonnet prompt ({len(system_prompt)} chars)")

    # --- Connect to MongoDB (read-only) ---
    collection = connect_to_mongodb()

    # --- Load test config ---
    test_cfg = load_test_config()

    # =========================================
    # PRE-FLIGHT: Test 10 data contamination
    # =========================================
    print()
    print("=" * 60)
    print("Pre-Flight: Test 10 — Wrong-District Contamination Check")
    print("=" * 60)
    east_valley_id = test_cfg.get("data_checks", {}).get("east_valley_yakima", "530537000805")
    contamination_result = check_east_valley_contamination(collection, east_valley_id)
    print(contamination_result)
    if "DATA FIX NEEDED" in contamination_result:
        print()
        print("WARNING: Data contamination detected. Report this to the builder.")
        print("Continuing with remaining tests — East Valley Yakima is not in the Sonnet test batch.")

    # =========================================
    # RESOLVE DYNAMIC SCHOOLS (skipped for targeted retests)
    # =========================================
    targeted = test_cfg.get("targeted_retest", False)

    oak_id = None
    keyword_schools = []
    random_schools = []

    if targeted:
        print()
        print("=" * 60)
        print("Targeted retest — skipping dynamic school resolution")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("Resolving dynamic test schools")
        print("=" * 60)

        # Death/suicide keyword scan for Test 1
        keywords = test_cfg.get("death_keywords", DEATH_KEYWORDS)
        keyword_schools = find_death_keyword_schools(collection, keywords)
        print(f"Death/suicide keyword scan: {len(keyword_schools)} schools matched")

        # Oak Harbor volunteer for Test 3
        oak_id, oak_name = find_oak_harbor_volunteer(collection)
        if oak_id:
            print(f"Oak Harbor volunteer: {oak_name} ({oak_id})")
        else:
            print("Oak Harbor volunteer: not found — skipping")

        # 5 random dated schools for Test 5
        static_ids = {s["nces_id"] for s in test_cfg.get("schools", [])}
        random_schools = pick_random_dated_schools(collection, count=5, exclude_ids=static_ids)
        print(f"Random dated schools for Test 5: {len(random_schools)} selected")
        for rs in random_schools:
            print(f"  {rs['name']} ({rs['nces_id']})")

    # =========================================
    # BUILD FULL SCHOOL LIST
    # =========================================

    # all_schools: nces_id -> {name, district, tests: [int], check_instructions: {int: str}}
    all_schools = {}

    # Static schools from config
    for s in test_cfg.get("schools", []):
        nid = s["nces_id"]
        all_schools[nid] = {
            "name": s["name"],
            "district": s.get("district", ""),
            "tests": list(s["tests"]),
            "check_instructions": {int(k): v for k, v in s.get("check_instructions", {}).items()},
        }

    if not targeted:
        # Oak Harbor
        if oak_id and oak_id not in all_schools:
            all_schools[oak_id] = {
                "name": oak_name,
                "district": "Oak Harbor SD",
                "tests": [3],
                "check_instructions": {
                    3: "Volunteer finding — exclude if no institutional role. Include institutional failure if present.",
                },
            }

        # Random dated schools for Test 5
        for rs in random_schools:
            nid = rs["nces_id"]
            if nid not in all_schools:
                all_schools[nid] = {
                    "name": rs["name"],
                    "district": "",
                    "tests": [5],
                    "check_instructions": {5: "Random school — confirm date-first formatting."},
                }
            else:
                if 5 not in all_schools[nid]["tests"]:
                    all_schools[nid]["tests"].append(5)

        # Keyword-matched schools for Test 1
        for ks in keyword_schools:
            nid = ks["nces_id"]
            if nid not in all_schools:
                all_schools[nid] = {
                    "name": ks["name"],
                    "district": ks["district"],
                    "tests": [1],
                    "check_instructions": {1: "Keyword-matched — scan output for death/suicide content."},
                }
            else:
                if 1 not in all_schools[nid]["tests"]:
                    all_schools[nid]["tests"].append(1)

        # Test 7 (student name suppression) applies to every school in full runs
        for nid in all_schools:
            if 7 not in all_schools[nid]["tests"]:
                all_schools[nid]["tests"].append(7)

    total = len(all_schools)
    print()
    print(f"Total unique schools to test: {total}")

    if not targeted and total > MAX_SCHOOLS_PER_RUN:
        print(f"WARNING: {total} exceeds safety cap of {MAX_SCHOOLS_PER_RUN}. Trimming keyword-scan schools.")
        # Keep all static schools, trim keyword-only additions
        static_nids = {s["nces_id"] for s in test_cfg.get("schools", [])}
        if oak_id:
            static_nids.add(oak_id)
        for rs in random_schools:
            static_nids.add(rs["nces_id"])

        keyword_only = [nid for nid in all_schools if nid not in static_nids]
        # Keep enough keyword schools to stay under cap
        allowed = MAX_SCHOOLS_PER_RUN - len(static_nids)
        for nid in keyword_only[allowed:]:
            del all_schools[nid]
        total = len(all_schools)
        print(f"Trimmed to {total} schools.")

    # =========================================
    # CALL SONNET
    # =========================================
    print()
    print("=" * 60)
    print("Calling Sonnet")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    results = {}
    models_seen = set()
    school_list = list(all_schools.items())

    for i, (nces_id, info) in enumerate(school_list):
        print(f"\n[{i+1}/{total}] {info['name']} ({nces_id})")

        # Pull findings
        school_name, district_name, findings = get_school_findings(collection, nces_id)

        if school_name is None:
            print("  SKIP — school not found in MongoDB")
            results[nces_id] = {
                "school_name": info["name"],
                "district_name": info.get("district", ""),
                "error": "School not found in MongoDB",
                "tests": info["tests"],
                "check_instructions": info.get("check_instructions", {}),
            }
            continue

        if not findings:
            print("  SKIP — no findings")
            results[nces_id] = {
                "school_name": school_name,
                "district_name": district_name,
                "findings_count": 0,
                "error": "No findings in context or district_context",
                "tests": info["tests"],
                "check_instructions": info.get("check_instructions", {}),
            }
            continue

        print(f"  {len(findings)} findings")

        # Call Sonnet
        try:
            raw_text, usage = call_sonnet(
                client, system_prompt, school_name, district_name, nces_id, findings,
            )
            models_seen.add(usage["actual_model"])
            print(
                f"  Sonnet: {usage['input_tokens']} in / {usage['output_tokens']} out "
                f"(model: {usage['actual_model']})"
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            results[nces_id] = {
                "school_name": school_name,
                "district_name": district_name,
                "findings_count": len(findings),
                "findings_in": findings,
                "error": f"API error: {e}",
                "tests": info["tests"],
                "check_instructions": info.get("check_instructions", {}),
            }
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        # Parse JSON
        parsed = parse_sonnet_json(raw_text)
        narrative = parsed.get("narrative", "") if parsed else raw_text
        json_issues = check_json_structure(parsed)

        # Automated checks
        checks = run_all_checks(narrative, findings)

        # Store result
        results[nces_id] = {
            "school_name": school_name,
            "district_name": district_name,
            "findings_count": len(findings),
            "findings_in": findings,
            "raw_response": raw_text,
            "parsed": parsed,
            "narrative": narrative,
            "usage": usage,
            "tests": info["tests"],
            "check_instructions": info.get("check_instructions", {}),
            "checks": checks,
            "json_issues": json_issues,
        }

        # Save raw response to disk
        raw_path = os.path.join(raw_dir, f"{nces_id}.json")
        with open(raw_path, "w") as f:
            json.dump(
                {
                    "nces_id": nces_id,
                    "school_name": school_name,
                    "district_name": district_name,
                    "findings_in": findings,
                    "raw_response": raw_text,
                    "parsed": parsed,
                    "usage": usage,
                    "timestamp": datetime.now().isoformat(),
                },
                f,
                indent=2,
                default=str,
            )

        # Rate limit (skip on last school)
        if i < total - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    # =========================================
    # GENERATE REPORT
    # =========================================
    print()
    print("=" * 60)
    print("Generating test report")
    print("=" * 60)

    report_path = os.path.join(results_dir, f"test_run_{timestamp}.md")
    generate_report(report_path, results, contamination_result, timestamp, models_seen)
    print(f"Report: {report_path}")

    # Quick console summary
    tested_count = len([r for r in results.values() if "narrative" in r])
    error_count = len([r for r in results.values() if "error" in r])
    auto_fail_count = 0
    for r in results.values():
        checks = r.get("checks", {})
        if (checks.get("death_violations") or checks.get("name_violations")
                or checks.get("date_violations") or checks.get("evaluative_violations")):
            auto_fail_count += 1

    print()
    print(f"Schools tested: {tested_count}")
    print(f"Schools skipped/errored: {error_count}")
    print(f"Schools with auto-detected issues: {auto_fail_count}")
    print(f"All results need human review — see report.")


def reanalyze():
    """
    Re-run automated checks and regenerate report from saved raw responses.
    No Sonnet API calls. No MongoDB access needed (findings are in the saved JSON).
    Usage: python3 tests/sonnet_narrative_test.py --reanalyze
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Phase 4.5 — Reanalyze from saved responses — {timestamp}")

    results_dir = os.path.join(config.PHASES_DIR, "phase-4.5", "test_results")
    raw_dir = os.path.join(results_dir, "raw_responses")

    if not os.path.exists(raw_dir):
        print(f"ERROR: No raw responses found at {raw_dir}. Run the full test first.")
        sys.exit(1)

    # Load test config to get test assignments and check instructions
    test_cfg = load_test_config()
    school_config = {}
    for s in test_cfg.get("schools", []):
        school_config[s["nces_id"]] = {
            "tests": list(s["tests"]),
            "check_instructions": {int(k): v for k, v in s.get("check_instructions", {}).items()},
        }

    # Load all raw response files
    raw_files = sorted(f for f in os.listdir(raw_dir) if f.endswith(".json"))
    print(f"Found {len(raw_files)} raw response files")

    results = {}
    models_seen = set()

    for fname in raw_files:
        raw_path = os.path.join(raw_dir, fname)
        with open(raw_path, "r") as f:
            data = json.load(f)

        nces_id = data["nces_id"]
        findings = data.get("findings_in", [])
        raw_text = data.get("raw_response", "")
        usage = data.get("usage", {})
        parsed = data.get("parsed")

        if usage.get("actual_model"):
            models_seen.add(usage["actual_model"])

        # Re-parse if needed
        if parsed is None:
            parsed = parse_sonnet_json(raw_text)

        narrative = parsed.get("narrative", "") if parsed else raw_text
        json_issues = check_json_structure(parsed)

        # Re-run automated checks with fixed logic
        checks = run_all_checks(narrative, findings)

        # Get test assignments — from config if available, otherwise default to [1, 7]
        cfg = school_config.get(nces_id, {"tests": [1, 7], "check_instructions": {}})

        # Schools from keyword scan get Test 1 + Test 7
        tests = list(cfg["tests"])
        if 7 not in tests:
            tests.append(7)

        results[nces_id] = {
            "school_name": data.get("school_name", "Unknown"),
            "district_name": data.get("district_name", "Unknown"),
            "findings_count": len(findings),
            "findings_in": findings,
            "raw_response": raw_text,
            "parsed": parsed,
            "narrative": narrative,
            "usage": usage,
            "tests": tests,
            "check_instructions": cfg["check_instructions"],
            "checks": checks,
            "json_issues": json_issues,
        }

    # Contamination result from previous run
    contamination_result = (
        "DATA FIX NEEDED — findings attributed to East Valley Yakima may belong to "
        "East Valley Spokane (see previous run output for details)"
    )

    report_path = os.path.join(results_dir, f"test_run_{timestamp}_reanalyzed.md")
    generate_report(report_path, results, contamination_result, timestamp, models_seen)
    print(f"Report: {report_path}")

    tested_count = len([r for r in results.values() if "narrative" in r])
    auto_fail_count = 0
    for r in results.values():
        checks = r.get("checks", {})
        if (checks.get("death_violations") or checks.get("name_violations")
                or checks.get("date_violations") or checks.get("evaluative_violations")):
            auto_fail_count += 1

    print(f"Schools reanalyzed: {tested_count}")
    print(f"Schools with auto-detected issues: {auto_fail_count}")


if __name__ == "__main__":
    if "--reanalyze" in sys.argv:
        reanalyze()
    else:
        main()
