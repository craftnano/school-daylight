"""
17_haiku_enrichment.py — Haiku web search context enrichment for every school.

PURPOSE: For each school, call Haiku with web search to find contextual signals
         (news, investigations, awards, leadership changes, programs). A second
         Haiku call validates each finding. Store results in MongoDB.
INPUTS:  MongoDB Atlas (schooldaylight.schools), prompts/context_enrichment_v1.txt,
         prompts/context_validation_v1.txt
OUTPUTS: Adds context field to each school document in MongoDB. Writes checkpoint
         to data/enrichment_checkpoint.jsonl. Logs to logs/enrichment_*.log.
JOIN KEYS: _id (NCESSCH)
SUPPRESSION HANDLING: N/A — this step adds AI-sourced context, not tabular data.
RECEIPT: phases/phase-4/receipt.md
FAILURE MODES: API timeout → retry with backoff. 429 rate limit → wait and retry
               (does not count against retry limit). JSON parse failure → retry.
               After 3 failed retries, school marked as failed and skipped.
"""

import os
import sys
import json
import time
import logging
import argparse
import re
from datetime import datetime, timezone
from collections import Counter

# Add pipeline dir and project root to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers import setup_logging, FAIRHAVEN_NCESSCH
import config


# ============================================================================
# CONSTANTS
# ============================================================================

MODEL = "claude-haiku-4-5-20251001"
ENRICHMENT_PROMPT_PATH = os.path.join(config.PROJECT_ROOT, "prompts", "context_enrichment_v1.txt")
VALIDATION_PROMPT_PATH = os.path.join(config.PROJECT_ROOT, "prompts", "context_validation_v1.txt")
CHECKPOINT_PATH = os.path.join(config.DATA_DIR, "enrichment_checkpoint.jsonl")
DATABASE_NAME = "schooldaylight"

# Cost controls from plan
MAX_ENRICHMENT_SEARCHES = 2
MAX_VALIDATION_SEARCHES = 1
MAX_ENRICHMENT_TOKENS = 2000
MAX_VALIDATION_TOKENS = 1500
MAX_RETRIES = 3
RETRY_BACKOFF = [5, 15, 45]  # seconds

# Rate limit: 5 requests per minute = 1 token per 12 seconds
RATE_LIMIT_RPM = 5
TOKEN_REFILL_INTERVAL = 60.0 / RATE_LIMIT_RPM  # 12 seconds

# Valid categories — Haiku must use one of these
VALID_CATEGORIES = {
    "news", "investigations_ocr", "awards_recognition",
    "leadership", "programs", "community_investment", "other"
}


# ============================================================================
# RATE LIMITER — token bucket that prevents 429 errors
# ============================================================================

class RateLimiter:
    """Simple token-bucket rate limiter.

    Starts with `capacity` tokens. Each call to wait() consumes one token.
    Tokens refill at one per `refill_interval` seconds. If the bucket is
    empty, wait() blocks until a token becomes available.
    """

    def __init__(self, capacity, refill_interval):
        self.capacity = capacity
        self.refill_interval = refill_interval
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def wait(self):
        """Block until a token is available, then consume it."""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            new_tokens = elapsed / self.refill_interval
            if new_tokens >= 1:
                self.tokens = min(self.capacity, self.tokens + int(new_tokens))
                self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Sleep until next token arrives
            wait_time = self.refill_interval - (now - self.last_refill) % self.refill_interval
            time.sleep(wait_time)


# ============================================================================
# PROMPT LOADING
# ============================================================================

def load_prompt(path):
    """Load a prompt template from a text file. Returns the template string."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Prompt file not found at {path}. "
            "Make sure the prompts/ directory contains the enrichment and "
            "validation prompt files."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def fill_enrichment_prompt(template, school):
    """Fill the enrichment prompt template with school details."""
    district_name = school.get("district", {}).get("name", "Unknown District")
    city = school.get("address", {}).get("city", "Unknown City")
    state = school.get("address", {}).get("state", "WA")

    return template.format(
        school_name=school["name"],
        district_name=district_name,
        city=city,
        state=state
    )


def fill_validation_prompt(template, school, findings_json):
    """Fill the validation prompt template with school details and findings."""
    district_name = school.get("district", {}).get("name", "Unknown District")
    city = school.get("address", {}).get("city", "Unknown City")
    state = school.get("address", {}).get("state", "WA")

    return template.format(
        school_name=school["name"],
        district_name=district_name,
        city=city,
        state=state,
        findings_json=findings_json
    )


# ============================================================================
# JSON PARSING — Haiku sometimes wraps JSON in markdown fences
# ============================================================================

def extract_json(text):
    """Parse JSON from Haiku's response, stripping markdown fences if present.

    Haiku is instructed to return raw JSON, but sometimes wraps it in
    ```json ... ``` blocks anyway. This handles both cases.
    """
    if text is None:
        return None

    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence (```json or just ```)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ============================================================================
# API CALLS — enrichment and validation
# ============================================================================

def call_enrichment(client, prompt_text, rate_limiter, logger):
    """Call Haiku with web search for context enrichment.

    Returns (parsed_json, usage_dict, actual_model) or raises on API error.
    """
    rate_limiter.wait()

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_ENRICHMENT_TOKENS,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": MAX_ENRICHMENT_SEARCHES
        }],
        messages=[{"role": "user", "content": prompt_text}]
    )

    # Extract the text block from the response (may contain server_tool_use
    # and web_search_tool_result blocks before the final text)
    text_content = None
    for block in response.content:
        if block.type == "text":
            text_content = block.text

    # LINEAGE: context.enrichment — track what model actually responded
    actual_model = response.model

    usage = response.usage
    web_searches = 0
    if hasattr(usage, "server_tool_use") and usage.server_tool_use:
        web_searches = getattr(usage.server_tool_use, "web_search_requests", 0)

    usage_dict = {
        "enrichment_input_tokens": usage.input_tokens,
        "enrichment_output_tokens": usage.output_tokens,
        "web_search_requests": web_searches,
    }

    return text_content, usage_dict, actual_model


def call_validation(client, prompt_text, rate_limiter, logger):
    """Call Haiku with web search for finding validation.

    Returns (parsed_json, usage_dict, actual_model) or raises on API error.
    """
    rate_limiter.wait()

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_VALIDATION_TOKENS,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": MAX_VALIDATION_SEARCHES
        }],
        messages=[{"role": "user", "content": prompt_text}]
    )

    text_content = None
    for block in response.content:
        if block.type == "text":
            text_content = block.text

    actual_model = response.model

    usage = response.usage
    web_searches = 0
    if hasattr(usage, "server_tool_use") and usage.server_tool_use:
        web_searches = getattr(usage.server_tool_use, "web_search_requests", 0)

    usage_dict = {
        "validation_input_tokens": usage.input_tokens,
        "validation_output_tokens": usage.output_tokens,
        "web_search_requests": web_searches,
    }

    return text_content, usage_dict, actual_model


# ============================================================================
# FINDING VALIDATION — merge enrichment + validation results
# ============================================================================

def validate_findings(findings, validation_data):
    """Apply validation judgments to enrichment findings.

    Returns (validated_findings_list, validation_summary_dict).
    Rejected findings are removed. Downgraded findings get updated confidence.
    """
    validations = validation_data.get("validations", [])
    summary = validation_data.get("summary", {})

    validated = []
    confirmed_count = 0
    rejected_count = 0
    downgraded_count = 0
    wrong_school_count = 0

    for v in validations:
        idx = v.get("finding_index")
        if idx is None or idx >= len(findings):
            continue

        finding = findings[idx].copy()
        judgment = v.get("judgment", "confirmed")
        notes = v.get("notes", "")

        if judgment == "rejected":
            rejected_count += 1
            if "wrong" in notes.lower() and "school" in notes.lower():
                wrong_school_count += 1
            continue  # Do not include rejected findings

        if judgment == "downgraded":
            downgraded_count += 1
            new_conf = v.get("confidence_adjustment", "low")
            finding["confidence"] = new_conf

        if judgment == "confirmed":
            confirmed_count += 1

        finding["validated"] = True
        finding["validation_notes"] = notes
        validated.append(finding)

    validation_summary = {
        "findings_submitted": len(findings),
        "findings_confirmed": confirmed_count,
        "findings_rejected": rejected_count,
        "findings_downgraded": downgraded_count,
        "wrong_school_detected": wrong_school_count,
    }

    return validated, validation_summary


# ============================================================================
# SANITIZE FINDINGS — ensure schema compliance
# ============================================================================

def sanitize_finding(finding):
    """Ensure a finding dict has all required fields with correct types.

    Haiku is instructed to return the right schema, but we enforce it here
    to prevent malformed data from reaching MongoDB.
    """
    category = finding.get("category", "other")
    if category not in VALID_CATEGORIES:
        category = "other"

    return {
        "category": category,
        "subcategory": finding.get("subcategory") if category == "other" else None,
        "summary": str(finding.get("summary", "")),
        "source_url": str(finding.get("source_url", "")),
        "source_name": str(finding.get("source_name", "")),
        "source_content_summary": str(finding.get("source_content_summary", "")),
        "date": finding.get("date"),  # null or ISO string
        "confidence": finding.get("confidence", "low") if finding.get("confidence") in ("high", "medium", "low") else "low",
        "sensitivity": finding.get("sensitivity", "normal") if finding.get("sensitivity") in ("high", "normal") else "normal",
        "validated": finding.get("validated", False),
        "validation_notes": finding.get("validation_notes"),
    }


# ============================================================================
# CHECKPOINT — resume capability
# ============================================================================

def load_checkpoint():
    """Load already-processed NCES IDs from the checkpoint file.

    Returns a set of NCESSCH strings that have already been processed.
    """
    processed = set()
    if not os.path.exists(CHECKPOINT_PATH):
        return processed

    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                processed.add(record["ncessch"])
            except (json.JSONDecodeError, KeyError):
                continue

    return processed


def write_checkpoint(ncessch, status, findings_count, error=None):
    """Append a checkpoint record for one school."""
    record = {
        "ncessch": ncessch,
        "status": status,
        "findings_count": findings_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        record["error"] = error

    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ============================================================================
# PROCESS ONE SCHOOL — the core loop body
# ============================================================================

def process_school(school, client, enrichment_template, validation_template,
                   rate_limiter, db, logger):
    """Run enrichment + validation for one school. Write results to MongoDB.

    Returns (status, findings_count, cost_dict) or raises after max retries.
    """
    ncessch = school["_id"]
    school_name = school["name"]

    # Step 1: Build and send enrichment prompt
    prompt_text = fill_enrichment_prompt(enrichment_template, school)

    enrichment_text = None
    enrichment_usage = {}
    enrichment_model = None
    retries = 0

    while retries <= MAX_RETRIES:
        try:
            enrichment_text, enrichment_usage, enrichment_model = call_enrichment(
                client, prompt_text, rate_limiter, logger
            )
            break
        except Exception as e:
            error_str = str(e)

            # 429 rate limit — wait and retry, does NOT count against retry limit
            if "429" in error_str or "rate" in error_str.lower():
                logger.info(f"  Rate limited on {school_name}. Waiting 60 seconds.")
                time.sleep(60)
                continue

            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF[retries - 1]
            logger.info(f"  API error on {school_name} (attempt {retries}/{MAX_RETRIES}): {error_str}. Retrying in {wait}s.")
            time.sleep(wait)

    # Step 2: Parse enrichment response
    enrichment_data = extract_json(enrichment_text)

    if enrichment_data is None:
        # JSON parse failure — treat as failed
        error_msg = f"Could not parse enrichment JSON. Raw response: {enrichment_text[:200] if enrichment_text else 'None'}"
        context_doc = build_failed_context(error_msg, enrichment_usage, enrichment_model)
        write_to_mongo(db, ncessch, context_doc)
        return ("failed", 0, context_doc.get("cost", {}))

    raw_findings = enrichment_data.get("findings", [])

    # Step 3: If no findings, skip validation
    if len(raw_findings) == 0:
        context_doc = build_no_findings_context(enrichment_usage, enrichment_model)
        write_to_mongo(db, ncessch, context_doc)
        return ("no_findings", 0, context_doc.get("cost", {}))

    # Step 4: Sanitize findings before validation
    sanitized_findings = [sanitize_finding(f) for f in raw_findings]

    # Step 5: Run validation pass
    findings_json = json.dumps(sanitized_findings, indent=2)
    validation_prompt = fill_validation_prompt(validation_template, school, findings_json)

    validation_text = None
    validation_usage = {}
    validation_model = None
    retries = 0

    while retries <= MAX_RETRIES:
        try:
            validation_text, validation_usage, validation_model = call_validation(
                client, validation_prompt, rate_limiter, logger
            )
            break
        except Exception as e:
            error_str = str(e)

            if "429" in error_str or "rate" in error_str.lower():
                logger.info(f"  Rate limited on validation for {school_name}. Waiting 60 seconds.")
                time.sleep(60)
                continue

            retries += 1
            if retries > MAX_RETRIES:
                # Validation failed but enrichment succeeded — store unvalidated
                logger.info(f"  Validation failed for {school_name} after {MAX_RETRIES} retries. Storing unvalidated findings.")
                validation_text = None
                break
            wait = RETRY_BACKOFF[retries - 1]
            logger.info(f"  Validation API error on {school_name} (attempt {retries}/{MAX_RETRIES}): {error_str}. Retrying in {wait}s.")
            time.sleep(wait)

    # Step 6: Merge validation results
    if validation_text:
        validation_data = extract_json(validation_text)
    else:
        validation_data = None

    if validation_data:
        validated_findings, validation_summary = validate_findings(sanitized_findings, validation_data)
    else:
        # Validation parse failed — keep all findings but mark as unvalidated
        validated_findings = sanitized_findings
        for f in validated_findings:
            f["validated"] = False
            f["validation_notes"] = "Validation pass failed or returned unparseable response."
        validation_summary = {
            "findings_submitted": len(sanitized_findings),
            "findings_confirmed": 0,
            "findings_rejected": 0,
            "findings_downgraded": 0,
            "wrong_school_detected": 0,
        }

    # Step 7: Build and write context document
    total_web_searches = enrichment_usage.get("web_search_requests", 0) + validation_usage.get("web_search_requests", 0)

    cost = {
        "enrichment_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
        "enrichment_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
        "validation_input_tokens": validation_usage.get("validation_input_tokens", 0),
        "validation_output_tokens": validation_usage.get("validation_output_tokens", 0),
        "web_search_requests": total_web_searches,
        "total_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0) + validation_usage.get("validation_input_tokens", 0),
        "total_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0) + validation_usage.get("validation_output_tokens", 0),
        "actual_model": enrichment_model or MODEL,
    }

    context_doc = {
        "status": "enriched",
        "prompt_version": "v1",
        "validation_prompt_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "cost": cost,
        "findings": validated_findings,
        "validation_summary": validation_summary,
        "error": None,
    }

    write_to_mongo(db, ncessch, context_doc)
    return ("enriched", len(validated_findings), cost)


# ============================================================================
# HELPER BUILDERS — context documents for edge cases
# ============================================================================

def build_no_findings_context(enrichment_usage, actual_model):
    """Build a context document when enrichment returns zero findings."""
    return {
        "status": "no_findings",
        "prompt_version": "v1",
        "validation_prompt_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "cost": {
            "enrichment_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
            "enrichment_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
            "validation_input_tokens": 0,
            "validation_output_tokens": 0,
            "web_search_requests": enrichment_usage.get("web_search_requests", 0),
            "total_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
            "total_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
            "actual_model": actual_model or MODEL,
        },
        "findings": [],
        "validation_summary": None,
        "error": None,
    }


def build_failed_context(error_msg, enrichment_usage, actual_model):
    """Build a context document when processing fails."""
    return {
        "status": "failed",
        "prompt_version": "v1",
        "validation_prompt_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "cost": {
            "enrichment_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
            "enrichment_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
            "validation_input_tokens": 0,
            "validation_output_tokens": 0,
            "web_search_requests": enrichment_usage.get("web_search_requests", 0),
            "total_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
            "total_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
            "actual_model": actual_model or MODEL,
        },
        "findings": [],
        "validation_summary": None,
        "error": error_msg,
    }


# ============================================================================
# MONGODB WRITE
# ============================================================================

def write_to_mongo(db, ncessch, context_doc):
    """Write the context document to a school's MongoDB document."""
    db.schools.update_one(
        {"_id": ncessch},
        {"$set": {"context": context_doc}}
    )


# ============================================================================
# PILOT SCHOOL SELECTION
# ============================================================================

def select_pilot_schools(db, logger):
    """Select 25 representative schools for the pilot batch.

    Returns a list of school documents from MongoDB.
    """
    pilot_ids = []

    # 1. Fairhaven (golden school) — always included
    pilot_ids.append(FAIRHAVEN_NCESSCH)

    # 2. Large district: Seattle (4 schools)
    seattle = list(db.schools.find(
        {"district.name": {"$regex": "Seattle", "$options": "i"},
         "school_type": "Regular School"},
        {"_id": 1}
    ).limit(4))
    pilot_ids.extend([s["_id"] for s in seattle])

    # 3. Large district: Spokane (3 schools)
    spokane = list(db.schools.find(
        {"district.name": {"$regex": "Spokane School District", "$options": "i"},
         "school_type": "Regular School"},
        {"_id": 1}
    ).limit(3))
    pilot_ids.extend([s["_id"] for s in spokane])

    # 4. Bellingham district (2 more, not Fairhaven)
    bellingham = list(db.schools.find(
        {"district.name": {"$regex": "Bellingham", "$options": "i"},
         "school_type": "Regular School",
         "_id": {"$ne": FAIRHAVEN_NCESSCH}},
        {"_id": 1}
    ).limit(2))
    pilot_ids.extend([s["_id"] for s in bellingham])

    # 5. Mid-size districts (5 schools from different districts)
    # Tacoma, Olympia, Yakima, Kennewick, Everett
    mid_districts = ["Tacoma", "Olympia", "Yakima", "Kennewick", "Everett"]
    for dist in mid_districts:
        school = db.schools.find_one(
            {"district.name": {"$regex": dist, "$options": "i"},
             "school_type": "Regular School"},
            {"_id": 1}
        )
        if school:
            pilot_ids.append(school["_id"])

    # 6. Rural, small enrollment (5 schools with enrollment < 100)
    rural = list(db.schools.find(
        {"enrollment.total": {"$lt": 100, "$gt": 0},
         "school_type": "Regular School",
         "_id": {"$nin": pilot_ids}},
        {"_id": 1}
    ).limit(5))
    pilot_ids.extend([s["_id"] for s in rural])

    # 7. Excluded schools — alternative/special ed (3 schools)
    excluded = list(db.schools.find(
        {"derived.performance_flag_absent_reason": "school_type_not_comparable",
         "_id": {"$nin": pilot_ids}},
        {"_id": 1}
    ).limit(3))
    pilot_ids.extend([s["_id"] for s in excluded])

    # 8. Charter schools (2 schools)
    charters = list(db.schools.find(
        {"is_charter": True,
         "_id": {"$nin": pilot_ids}},
        {"_id": 1}
    ).limit(2))
    pilot_ids.extend([s["_id"] for s in charters])

    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for pid in pilot_ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)

    # Fetch full documents
    schools = []
    for ncessch in unique_ids:
        doc = db.schools.find_one({"_id": ncessch})
        if doc:
            schools.append(doc)

    logger.info(f"Selected {len(schools)} pilot schools from {len(unique_ids)} candidates.")
    return schools


# ============================================================================
# PILOT REPORT GENERATION
# ============================================================================

def generate_pilot_report(results, logger):
    """Generate the pilot report markdown file.

    Args:
        results: list of dicts with keys: ncessch, name, district, status,
                 findings_count, findings, cost, validation_summary, category
    """
    report_path = os.path.join(config.PHASES_DIR, "phase-4", "pilot_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    total_cost_input = sum(r["cost"].get("total_input_tokens", 0) for r in results)
    total_cost_output = sum(r["cost"].get("total_output_tokens", 0) for r in results)
    total_web_searches = sum(r["cost"].get("web_search_requests", 0) for r in results)
    total_findings = sum(r["findings_count"] for r in results)
    enriched_count = sum(1 for r in results if r["status"] == "enriched")
    no_findings_count = sum(1 for r in results if r["status"] == "no_findings")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # Haiku pricing: $0.80/MTok input, $4.00/MTok output
    cost_usd = (total_cost_input * 0.80 + total_cost_output * 4.00) / 1_000_000
    per_school_cost = cost_usd / len(results) if results else 0
    projected_full = per_school_cost * 2532

    lines = []
    lines.append("# Phase 4 — Pilot Batch Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Schools processed:** {len(results)}")
    lines.append(f"**Model:** {MODEL}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Enriched (has findings): {enriched_count}")
    lines.append(f"- No findings: {no_findings_count}")
    lines.append(f"- Failed: {failed_count}")
    lines.append(f"- Total findings across all schools: {total_findings}")
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    lines.append(f"- Total input tokens: {total_cost_input:,}")
    lines.append(f"- Total output tokens: {total_cost_output:,}")
    lines.append(f"- Total web searches: {total_web_searches}")
    lines.append(f"- **Total cost (tokens only): ${cost_usd:.2f}**")
    lines.append(f"- **Per-school average: ${per_school_cost:.4f}**")
    lines.append(f"- **Projected full batch (2,532 schools): ${projected_full:.2f}**")
    lines.append(f"- Note: web search cost ($10/1000 searches) adds ~${total_web_searches * 0.01:.2f} for pilot, ~${total_web_searches / len(results) * 2532 * 0.01:.2f} projected for full batch")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-school results table
    lines.append("## Per-School Results")
    lines.append("")
    lines.append("| # | School | District | Status | Findings | Web Searches | Actual Model |")
    lines.append("|---|--------|----------|--------|----------|-------------|--------------|")
    for i, r in enumerate(results, 1):
        model_check = r["cost"].get("actual_model", "unknown")
        model_ok = "OK" if MODEL in str(model_check) else f"MISMATCH: {model_check}"
        lines.append(f"| {i} | {r['name']} | {r['district']} | {r['status']} | {r['findings_count']} | {r['cost'].get('web_search_requests', 0)} | {model_ok} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Fairhaven section
    fairhaven = [r for r in results if r["ncessch"] == FAIRHAVEN_NCESSCH]
    if fairhaven:
        fh = fairhaven[0]
        lines.append("## Fairhaven Middle School (Golden School)")
        lines.append("")
        lines.append(f"**Status:** {fh['status']}")
        lines.append(f"**Findings:** {fh['findings_count']}")
        lines.append("")
        if fh["findings"]:
            for j, f in enumerate(fh["findings"], 1):
                lines.append(f"### Finding {j}: {f.get('category', 'unknown')}")
                lines.append("")
                lines.append(f"- **Summary:** {f.get('summary', 'N/A')}")
                lines.append(f"- **Source:** [{f.get('source_name', 'N/A')}]({f.get('source_url', '')})")
                lines.append(f"- **Source content:** {f.get('source_content_summary', 'N/A')}")
                lines.append(f"- **Date:** {f.get('date', 'unknown')}")
                lines.append(f"- **Confidence:** {f.get('confidence', 'unknown')}")
                lines.append(f"- **Sensitivity:** {f.get('sensitivity', 'normal')}")
                lines.append(f"- **Validated:** {f.get('validated', False)}")
                if f.get("validation_notes"):
                    lines.append(f"- **Validation notes:** {f['validation_notes']}")
                lines.append("")
        else:
            lines.append("No findings returned. Builder should evaluate whether this is expected.")
            lines.append("")
        if fh.get("validation_summary"):
            vs = fh["validation_summary"]
            lines.append(f"**Validation summary:** {vs.get('findings_submitted', 0)} submitted, "
                        f"{vs.get('findings_confirmed', 0)} confirmed, "
                        f"{vs.get('findings_rejected', 0)} rejected, "
                        f"{vs.get('findings_downgraded', 0)} downgraded, "
                        f"{vs.get('wrong_school_detected', 0)} wrong-school")
            lines.append("")
        lines.append("**Builder: review these findings against known local reality.**")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Sensitivity=high findings
    high_sensitivity = []
    for r in results:
        for f in r.get("findings", []):
            if f.get("sensitivity") == "high":
                high_sensitivity.append({"school": r["name"], "finding": f})

    lines.append("## Sensitivity=High Findings (Need Human Review)")
    lines.append("")
    if high_sensitivity:
        for hs in high_sensitivity:
            lines.append(f"- **{hs['school']}**: {hs['finding'].get('summary', 'N/A')} "
                        f"(category: {hs['finding'].get('category', 'unknown')}, "
                        f"source: {hs['finding'].get('source_name', 'unknown')})")
    else:
        lines.append("None found in pilot batch.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Category=other findings
    other_findings = []
    for r in results:
        for f in r.get("findings", []):
            if f.get("category") == "other":
                other_findings.append({"school": r["name"], "finding": f})

    lines.append("## Category=Other Findings (Need Human Review)")
    lines.append("")
    if other_findings:
        for of in other_findings:
            lines.append(f"- **{of['school']}**: {of['finding'].get('summary', 'N/A')} "
                        f"(subcategory: {of['finding'].get('subcategory', 'none')}, "
                        f"source: {of['finding'].get('source_name', 'unknown')})")
    else:
        lines.append("None found in pilot batch.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Validation rejections
    rejections = []
    for r in results:
        vs = r.get("validation_summary")
        if vs and vs.get("findings_rejected", 0) > 0:
            rejections.append({"school": r["name"], "summary": vs})

    lines.append("## Validation Rejections")
    lines.append("")
    if rejections:
        for rej in rejections:
            vs = rej["summary"]
            lines.append(f"- **{rej['school']}**: {vs.get('findings_rejected', 0)} rejected "
                        f"({vs.get('wrong_school_detected', 0)} wrong-school)")
    else:
        lines.append("No findings were rejected by the validation pass.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # All findings by category
    cat_counts = Counter()
    for r in results:
        for f in r.get("findings", []):
            cat_counts[f.get("category", "unknown")] += 1

    lines.append("## Findings by Category")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for cat in sorted(cat_counts.keys()):
        lines.append(f"| {cat} | {cat_counts[cat]} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Full batch does NOT run until builder reviews and approves this report.**")

    report_text = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"Pilot report written to {report_path}")
    return report_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Haiku web search context enrichment for WA schools."
    )
    parser.add_argument(
        "--pilot", action="store_true",
        help="Run pilot batch only (25 representative schools)."
    )
    parser.add_argument(
        "--school", type=str, default=None,
        help="Run enrichment for a single school by NCESSCH ID."
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear checkpoint file and start fresh (does not clear MongoDB context fields)."
    )
    args = parser.parse_args()

    logger = setup_logging("enrichment")
    logger.info("=" * 70)
    logger.info("Phase 4: Haiku Context Enrichment")
    logger.info("=" * 70)

    # Validate prerequisites
    if not config.ANTHROPIC_API_KEY:
        logger.error(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file. "
            "Get your key from console.anthropic.com."
        )
        sys.exit(1)

    if not config.MONGO_URI:
        logger.error(
            "MONGO_URI is not set. Add it to your .env file. "
            "This is your MongoDB Atlas connection string."
        )
        sys.exit(1)

    # Load prompts
    logger.info("Loading prompt templates...")
    enrichment_template = load_prompt(ENRICHMENT_PROMPT_PATH)
    validation_template = load_prompt(VALIDATION_PROMPT_PATH)
    logger.info(f"  Enrichment prompt: {ENRICHMENT_PROMPT_PATH}")
    logger.info(f"  Validation prompt: {VALIDATION_PROMPT_PATH}")

    # Connect to services
    logger.info("Connecting to MongoDB Atlas...")
    from pymongo import MongoClient
    mongo_client = MongoClient(config.MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    doc_count = db.schools.count_documents({})
    logger.info(f"  Connected. {doc_count} school documents found.")

    logger.info("Connecting to Anthropic API...")
    import anthropic
    api_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    logger.info(f"  Connected. Model: {MODEL}")

    # Set up rate limiter
    rate_limiter = RateLimiter(capacity=RATE_LIMIT_RPM, refill_interval=TOKEN_REFILL_INTERVAL)

    # Handle checkpoint
    if args.reset:
        if os.path.exists(CHECKPOINT_PATH):
            os.remove(CHECKPOINT_PATH)
            logger.info("Checkpoint file cleared.")

    already_processed = load_checkpoint()
    if already_processed:
        logger.info(f"Checkpoint: {len(already_processed)} schools already processed.")

    # Select schools to process
    if args.school:
        # Single school mode
        school_doc = db.schools.find_one({"_id": args.school})
        if not school_doc:
            logger.error(f"School {args.school} not found in MongoDB.")
            sys.exit(1)
        schools_to_process = [school_doc]
        logger.info(f"Single school mode: {school_doc['name']} ({args.school})")
    elif args.pilot:
        schools_to_process = select_pilot_schools(db, logger)
        # For pilot, also remove already-processed schools
        schools_to_process = [s for s in schools_to_process if s["_id"] not in already_processed]
        logger.info(f"Pilot mode: {len(schools_to_process)} schools to process.")
    else:
        # Full batch — all schools, skip already-processed
        all_schools = list(db.schools.find({}, {
            "_id": 1, "name": 1, "district": 1, "address": 1,
            "school_type": 1, "derived.performance_flag_absent_reason": 1
        }))
        schools_to_process = [s for s in all_schools if s["_id"] not in already_processed]
        logger.info(f"Full batch mode: {len(schools_to_process)} schools to process "
                    f"({len(already_processed)} already done, {doc_count} total).")

    if not schools_to_process:
        logger.info("No schools to process. All done or empty selection.")
        return

    # Process schools
    results = []
    start_time = time.monotonic()
    total = len(schools_to_process)

    for i, school in enumerate(schools_to_process, 1):
        ncessch = school["_id"]
        school_name = school.get("name", "Unknown")
        district_name = school.get("district", {}).get("name", "Unknown")
        school_start = time.monotonic()

        try:
            status, findings_count, cost = process_school(
                school, api_client, enrichment_template, validation_template,
                rate_limiter, db, logger
            )

            elapsed = time.monotonic() - school_start
            cost_input = cost.get("total_input_tokens", 0)
            cost_output = cost.get("total_output_tokens", 0)
            cost_usd = (cost_input * 0.80 + cost_output * 4.00) / 1_000_000
            web_searches = cost.get("web_search_requests", 0)

            logger.info(
                f"School {i}/{total}: {school_name} ({ncessch}). "
                f"{status}, {findings_count} findings, "
                f"{web_searches} web searches, ${cost_usd:.4f}, {elapsed:.1f}s."
            )

            write_checkpoint(ncessch, status, findings_count)

            # Collect results for pilot report
            # For the pilot report, we need the full context back from MongoDB
            if args.pilot or args.school:
                context_doc = db.schools.find_one({"_id": ncessch}, {"context": 1})
                context = context_doc.get("context", {}) if context_doc else {}
                results.append({
                    "ncessch": ncessch,
                    "name": school_name,
                    "district": district_name,
                    "status": status,
                    "findings_count": findings_count,
                    "findings": context.get("findings", []),
                    "cost": cost,
                    "validation_summary": context.get("validation_summary"),
                })

        except Exception as e:
            elapsed = time.monotonic() - school_start
            error_msg = str(e)
            logger.error(
                f"School {i}/{total}: {school_name} ({ncessch}). "
                f"FAILED after {elapsed:.1f}s: {error_msg}"
            )

            # Write failed context to MongoDB
            failed_context = build_failed_context(error_msg, {}, None)
            write_to_mongo(db, ncessch, failed_context)
            write_checkpoint(ncessch, "failed", 0, error=error_msg)

            if args.pilot or args.school:
                results.append({
                    "ncessch": ncessch,
                    "name": school_name,
                    "district": district_name,
                    "status": "failed",
                    "findings_count": 0,
                    "findings": [],
                    "cost": {"total_input_tokens": 0, "total_output_tokens": 0,
                             "web_search_requests": 0, "actual_model": "N/A"},
                    "validation_summary": None,
                })

    # Summary
    total_elapsed = time.monotonic() - start_time
    elapsed_str = f"{total_elapsed / 3600:.1f}h" if total_elapsed > 3600 else f"{total_elapsed / 60:.1f}m"
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Batch complete. {total} schools processed in {elapsed_str}.")

    status_counts = Counter(r["status"] for r in results) if results else Counter()
    for s, c in status_counts.most_common():
        logger.info(f"  {s}: {c}")
    logger.info("=" * 70)

    # Generate pilot report if in pilot mode
    if args.pilot and results:
        report_path = generate_pilot_report(results, logger)
        logger.info(f"Pilot report: {report_path}")
        logger.info("Full batch does NOT run until builder reviews and approves the pilot report.")

    mongo_client.close()


if __name__ == "__main__":
    main()
