"""
17_haiku_enrichment.py — Two-pass Haiku web search context enrichment.

PURPOSE: Pass 1 (district): For each district, search for district-wide contextual
         signals (investigations, lawsuits, leadership changes). Store as
         district_context on every school in the district.
         Pass 2 (school): For each school, search for school-specific signals
         (awards, programs, news). Store as context on the school document.
INPUTS:  MongoDB Atlas (schooldaylight.schools),
         prompts/district_enrichment_v1.txt, prompts/district_validation_v1.txt,
         prompts/context_enrichment_v1.txt, prompts/context_validation_v1.txt
OUTPUTS: Adds district_context and context fields to school documents in MongoDB.
         Writes checkpoints to data/district_enrichment_checkpoint.jsonl and
         data/enrichment_checkpoint.jsonl. Logs to logs/enrichment_*.log.
JOIN KEYS: _id (NCESSCH), district.name
SUPPRESSION HANDLING: N/A — this step adds AI-sourced context, not tabular data.
RECEIPT: phases/phase-4/receipt.md
FAILURE MODES: API timeout → retry with backoff. 429 rate limit → wait and retry
               (does not count against retry limit). JSON parse failure → retry.
               After 3 failed retries, entity marked as failed and skipped.
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
DATABASE_NAME = "schooldaylight"

# Prompt paths — four prompts for two passes
DISTRICT_ENRICHMENT_PROMPT = os.path.join(config.PROJECT_ROOT, "prompts", "district_enrichment_v1.txt")
DISTRICT_VALIDATION_PROMPT = os.path.join(config.PROJECT_ROOT, "prompts", "district_validation_v1.txt")
SCHOOL_ENRICHMENT_PROMPT = os.path.join(config.PROJECT_ROOT, "prompts", "context_enrichment_v1.txt")
SCHOOL_VALIDATION_PROMPT = os.path.join(config.PROJECT_ROOT, "prompts", "context_validation_v1.txt")

# Checkpoint paths — separate files so passes can run independently
DISTRICT_CHECKPOINT_PATH = os.path.join(config.DATA_DIR, "district_enrichment_checkpoint.jsonl")
SCHOOL_CHECKPOINT_PATH = os.path.join(config.DATA_DIR, "enrichment_checkpoint.jsonl")

# Cost controls from plan
MAX_ENRICHMENT_SEARCHES = 2
MAX_VALIDATION_SEARCHES = 1
# Haiku generates intro text + tool use tokens before writing JSON.
# 2000 was too tight — model ran out of output tokens before finishing JSON.
# 4096 gives plenty of room. Actual output is typically ~600-800 tokens.
MAX_ENRICHMENT_TOKENS = 4096
MAX_VALIDATION_TOKENS = 4096
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
# PROMPT LOADING AND FILLING
# ============================================================================

def load_prompt(path):
    """Load a prompt template from a text file. Returns the template string."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Prompt file not found at {path}. "
            "Make sure the prompts/ directory contains all four prompt files "
            "(district_enrichment, district_validation, context_enrichment, context_validation)."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def fill_district_prompt(template, district_name):
    """Fill a district-level prompt template.

    Uses str.replace() instead of str.format() because the prompt templates
    contain JSON examples with curly braces that would break .format().
    """
    return template.replace("{district_name}", district_name)


def fill_school_prompt(template, school):
    """Fill a school-level prompt template with school details.

    Uses str.replace() instead of str.format() because the prompt templates
    contain JSON examples with curly braces that would break .format().
    """
    district_name = school.get("district", {}).get("name", "Unknown District")
    city = school.get("address", {}).get("city", "Unknown City")
    state = school.get("address", {}).get("state", "WA")

    result = template.replace("{school_name}", school["name"])
    result = result.replace("{district_name}", district_name)
    result = result.replace("{city}", city)
    result = result.replace("{state}", state)
    return result


def fill_district_validation_prompt(template, district_name, findings_json):
    """Fill a district validation prompt with district name and findings."""
    result = template.replace("{district_name}", district_name)
    result = result.replace("{findings_json}", findings_json)
    return result


def fill_school_validation_prompt(template, school, findings_json):
    """Fill a school validation prompt with school details and findings."""
    district_name = school.get("district", {}).get("name", "Unknown District")
    city = school.get("address", {}).get("city", "Unknown City")
    state = school.get("address", {}).get("state", "WA")

    result = template.replace("{school_name}", school["name"])
    result = result.replace("{district_name}", district_name)
    result = result.replace("{city}", city)
    result = result.replace("{state}", state)
    result = result.replace("{findings_json}", findings_json)
    return result


# ============================================================================
# JSON PARSING — Haiku sometimes wraps JSON in markdown fences
# ============================================================================

def extract_json(text):
    """Parse JSON from Haiku's response, handling multiple formats.

    Haiku sometimes returns:
    1. Raw JSON (ideal)
    2. JSON wrapped in ```json ... ``` fences
    3. Prose text followed by a ```json ... ``` block
    This function handles all three cases.
    """
    if text is None:
        return None

    text = text.strip()

    # Case 1: text starts with { — try direct parse
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Case 2/3: look for a ```json ... ``` block anywhere in the text
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Case 4: look for a JSON object anywhere in the text (starts with {, ends with })
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ============================================================================
# API CALLS — enrichment and validation (shared by both passes)
# ============================================================================

def call_enrichment(client, prompt_text, rate_limiter, logger):
    """Call Haiku with web search for context enrichment.

    Returns (text_content, usage_dict, actual_model) or raises on API error.
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

    # Extract the last text block from the response (earlier text blocks are
    # intro text before/between web searches; the JSON is in the final one)
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

    Returns (text_content, usage_dict, actual_model) or raises on API error.
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
            # Count wrong-school/wrong-district rejections
            notes_lower = notes.lower()
            if ("wrong" in notes_lower and
                    ("school" in notes_lower or "district" in notes_lower or "state" in notes_lower)):
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
# CHECKPOINT — resume capability (works for both passes)
# ============================================================================

def load_checkpoint(checkpoint_path, key_field):
    """Load already-processed entity keys from a checkpoint file.

    Args:
        checkpoint_path: Path to the JSONL checkpoint file.
        key_field: The JSON field that identifies each entity (e.g., "ncessch"
                   for schools, "district_name" for districts).

    Returns a set of already-processed entity keys.
    """
    processed = set()
    if not os.path.exists(checkpoint_path):
        return processed

    with open(checkpoint_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                processed.add(record[key_field])
            except (json.JSONDecodeError, KeyError):
                continue

    return processed


def write_checkpoint(checkpoint_path, record):
    """Append a checkpoint record."""
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    with open(checkpoint_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ============================================================================
# API CALL WITH RETRY — shared retry logic for both passes
# ============================================================================

def call_with_retry(call_fn, client, prompt_text, rate_limiter, logger, entity_name):
    """Call an API function with retry logic.

    Args:
        call_fn: Either call_enrichment or call_validation.
        entity_name: Human-readable name for logging (school or district name).

    Returns (text_content, usage_dict, actual_model) or raises after max retries.
    Returns (None, {}, None) if all retries exhausted and caller should handle gracefully.
    """
    retries = 0
    while retries <= MAX_RETRIES:
        try:
            return call_fn(client, prompt_text, rate_limiter, logger)
        except Exception as e:
            error_str = str(e)

            # 429 rate limit — wait and retry, does NOT count against retry limit
            if "429" in error_str or "rate" in error_str.lower():
                logger.info(f"  Rate limited on {entity_name}. Waiting 60 seconds.")
                time.sleep(60)
                continue

            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF[retries - 1]
            logger.info(f"  API error on {entity_name} (attempt {retries}/{MAX_RETRIES}): {error_str}. Retrying in {wait}s.")
            time.sleep(wait)

    # Should not reach here, but just in case
    raise RuntimeError(f"Unexpected: exceeded retry loop for {entity_name}")


# ============================================================================
# BUILD CONTEXT DOCUMENT — shared between passes
# ============================================================================

def build_context_doc(status, findings, validation_summary, cost, error=None,
                      prompt_version="v1", validation_prompt_version="v1",
                      district_name=None):
    """Build a context document for either pass."""
    doc = {
        "status": status,
        "prompt_version": prompt_version,
        "validation_prompt_version": validation_prompt_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "cost": cost,
        "findings": findings,
        "validation_summary": validation_summary,
        "error": error,
    }
    # District context includes the district name for clarity
    if district_name is not None:
        doc["district_name"] = district_name
    return doc


def build_cost_dict(enrichment_usage, validation_usage, actual_model):
    """Combine enrichment and validation usage into a single cost dict."""
    total_web = (enrichment_usage.get("web_search_requests", 0) +
                 validation_usage.get("web_search_requests", 0))
    return {
        "enrichment_input_tokens": enrichment_usage.get("enrichment_input_tokens", 0),
        "enrichment_output_tokens": enrichment_usage.get("enrichment_output_tokens", 0),
        "validation_input_tokens": validation_usage.get("validation_input_tokens", 0),
        "validation_output_tokens": validation_usage.get("validation_output_tokens", 0),
        "web_search_requests": total_web,
        "total_input_tokens": (enrichment_usage.get("enrichment_input_tokens", 0) +
                               validation_usage.get("validation_input_tokens", 0)),
        "total_output_tokens": (enrichment_usage.get("enrichment_output_tokens", 0) +
                                validation_usage.get("validation_output_tokens", 0)),
        "actual_model": actual_model or MODEL,
    }


# ============================================================================
# PROCESS ONE ENTITY — generic enrichment + validation pipeline
# ============================================================================

def run_enrichment_pipeline(client, enrichment_prompt, validation_prompt_fn,
                            rate_limiter, logger, entity_name):
    """Run enrichment + validation for one entity (district or school).

    Args:
        enrichment_prompt: The filled enrichment prompt string.
        validation_prompt_fn: A callable that takes (sanitized_findings_json) and
                              returns the filled validation prompt string.
        entity_name: Human-readable name for logging.

    Returns (status, validated_findings, validation_summary, cost_dict).
    """
    # Step 1: Enrichment call
    enrichment_text, enrichment_usage, enrichment_model = call_with_retry(
        call_enrichment, client, enrichment_prompt, rate_limiter, logger, entity_name
    )

    # Step 2: Parse enrichment response
    enrichment_data = extract_json(enrichment_text)

    if enrichment_data is None:
        error_msg = (f"Could not parse enrichment JSON. "
                     f"Raw response: {enrichment_text[:200] if enrichment_text else 'None'}")
        cost = build_cost_dict(enrichment_usage, {}, enrichment_model)
        return ("failed", [], None, cost, error_msg)

    raw_findings = enrichment_data.get("findings", [])

    # Step 3: If no findings, skip validation — save tokens
    if len(raw_findings) == 0:
        cost = build_cost_dict(enrichment_usage, {}, enrichment_model)
        return ("no_findings", [], None, cost, None)

    # Step 4: Sanitize findings
    sanitized = [sanitize_finding(f) for f in raw_findings]

    # Step 5: Validation call
    findings_json = json.dumps(sanitized, indent=2)
    validation_prompt = validation_prompt_fn(findings_json)

    validation_text = None
    validation_usage = {}
    try:
        validation_text, validation_usage, _ = call_with_retry(
            call_validation, client, validation_prompt, rate_limiter, logger,
            f"validation for {entity_name}"
        )
    except Exception as e:
        # Validation failed but enrichment succeeded — store unvalidated
        logger.info(f"  Validation failed for {entity_name} after {MAX_RETRIES} retries. "
                    "Storing unvalidated findings.")

    # Step 6: Merge validation results
    if validation_text:
        validation_data = extract_json(validation_text)
    else:
        validation_data = None

    if validation_data:
        validated_findings, validation_summary = validate_findings(sanitized, validation_data)
    else:
        # Validation parse failed — keep all findings but mark as unvalidated
        validated_findings = sanitized
        for f in validated_findings:
            f["validated"] = False
            f["validation_notes"] = "Validation pass failed or returned unparseable response."
        validation_summary = {
            "findings_submitted": len(sanitized),
            "findings_confirmed": 0,
            "findings_rejected": 0,
            "findings_downgraded": 0,
            "wrong_school_detected": 0,
        }

    cost = build_cost_dict(enrichment_usage, validation_usage, enrichment_model)
    return ("enriched", validated_findings, validation_summary, cost, None)


# ============================================================================
# PASS 1: DISTRICT-LEVEL ENRICHMENT
# ============================================================================

def process_district(district_name, client, enrichment_template, validation_template,
                     rate_limiter, db, logger):
    """Run enrichment + validation for one district. Write to all schools in district.

    Returns (status, findings_count, cost_dict).
    """
    # Build prompts
    enrichment_prompt = fill_district_prompt(enrichment_template, district_name)

    def make_validation_prompt(findings_json):
        return fill_district_validation_prompt(validation_template, district_name, findings_json)

    # Run the pipeline
    status, findings, val_summary, cost, error = run_enrichment_pipeline(
        client, enrichment_prompt, make_validation_prompt,
        rate_limiter, logger, district_name
    )

    # Build context document
    context_doc = build_context_doc(
        status=status,
        findings=findings,
        validation_summary=val_summary,
        cost=cost,
        error=error,
        district_name=district_name,
    )

    # Write to ALL schools in this district
    result = db.schools.update_many(
        {"district.name": district_name},
        {"$set": {"district_context": context_doc}}
    )
    schools_updated = result.modified_count

    return (status, len(findings), cost, schools_updated)


def select_pilot_districts(db, logger):
    """Select 10 representative districts for the pilot batch.

    Returns a list of district name strings.
    """
    pilot = []

    # 3 large districts
    for name_pattern in ["Seattle", "Spokane School District", "Bellingham"]:
        match = db.schools.find_one(
            {"district.name": {"$regex": name_pattern, "$options": "i"}},
            {"district.name": 1}
        )
        if match:
            pilot.append(match["district"]["name"])

    # 4 mid-size districts
    for name_pattern in ["Tacoma", "Yakima", "Kennewick", "Olympia"]:
        match = db.schools.find_one(
            {"district.name": {"$regex": name_pattern, "$options": "i"}},
            {"district.name": 1}
        )
        if match:
            pilot.append(match["district"]["name"])

    # 3 small/rural districts — pick districts with only 1-2 schools
    small = list(db.schools.aggregate([
        {"$group": {"_id": "$district.name", "count": {"$sum": 1}}},
        {"$match": {"count": {"$lte": 2}, "_id": {"$nin": pilot}}},
        {"$limit": 3}
    ]))
    pilot.extend([s["_id"] for s in small])

    # Deduplicate
    seen = set()
    unique = []
    for d in pilot:
        if d not in seen:
            seen.add(d)
            unique.append(d)

    logger.info(f"Selected {len(unique)} pilot districts.")
    return unique


# ============================================================================
# PASS 2: SCHOOL-LEVEL ENRICHMENT
# ============================================================================

def process_school(school, client, enrichment_template, validation_template,
                   rate_limiter, db, logger):
    """Run enrichment + validation for one school. Write to MongoDB.

    Returns (status, findings_count, cost_dict).
    """
    ncessch = school["_id"]

    # Build prompts
    enrichment_prompt = fill_school_prompt(enrichment_template, school)

    def make_validation_prompt(findings_json):
        return fill_school_validation_prompt(validation_template, school, findings_json)

    # Run the pipeline
    status, findings, val_summary, cost, error = run_enrichment_pipeline(
        client, enrichment_prompt, make_validation_prompt,
        rate_limiter, logger, school["name"]
    )

    # Build context document
    context_doc = build_context_doc(
        status=status,
        findings=findings,
        validation_summary=val_summary,
        cost=cost,
        error=error,
    )

    # Write to this school's document
    db.schools.update_one(
        {"_id": ncessch},
        {"$set": {"context": context_doc}}
    )

    return (status, len(findings), cost)


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
    for dist in ["Tacoma", "Olympia", "Yakima", "Kennewick", "Everett"]:
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

def generate_pilot_report(results, pass_name, total_entities_full_batch, logger):
    """Generate the pilot report markdown file.

    Args:
        results: list of result dicts (keys vary by pass type).
        pass_name: "district" or "school".
        total_entities_full_batch: total count for cost projection.
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
    per_entity_cost = cost_usd / len(results) if results else 0
    projected_full = per_entity_cost * total_entities_full_batch

    entity_label = "District" if pass_name == "district" else "School"
    name_key = "district_name" if pass_name == "district" else "name"

    lines = []
    lines.append(f"# Phase 4 — Pilot Batch Report ({entity_label} Pass)")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**{entity_label}s processed:** {len(results)}")
    lines.append(f"**Model:** {MODEL}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Enriched (has findings): {enriched_count}")
    lines.append(f"- No findings: {no_findings_count}")
    lines.append(f"- Failed: {failed_count}")
    lines.append(f"- Total findings: {total_findings}")
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    lines.append(f"- Total input tokens: {total_cost_input:,}")
    lines.append(f"- Total output tokens: {total_cost_output:,}")
    lines.append(f"- Total web searches: {total_web_searches}")
    lines.append(f"- **Total cost (tokens only): ${cost_usd:.2f}**")
    lines.append(f"- **Per-{pass_name} average: ${per_entity_cost:.4f}**")
    lines.append(f"- **Projected full batch ({total_entities_full_batch} {pass_name}s): ${projected_full:.2f}**")
    if len(results) > 0:
        avg_searches = total_web_searches / len(results)
        lines.append(f"- Web search cost: ~${total_web_searches * 0.01:.2f} pilot, "
                     f"~${avg_searches * total_entities_full_batch * 0.01:.2f} projected full batch")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-entity results table
    lines.append(f"## Per-{entity_label} Results")
    lines.append("")
    extra_col = "| Schools Updated " if pass_name == "district" else ""
    extra_hdr = "|----------------- " if pass_name == "district" else ""
    lines.append(f"| # | {entity_label} | Status | Findings | Web Searches {extra_col}| Actual Model |")
    lines.append(f"|---|--------|--------|----------|------------- {extra_hdr}|--------------|")
    for i, r in enumerate(results, 1):
        model_check = r["cost"].get("actual_model", "unknown")
        model_ok = "OK" if MODEL in str(model_check) else f"MISMATCH: {model_check}"
        name = r.get(name_key, r.get("name", "Unknown"))
        extra_val = f"| {r.get('schools_updated', 'N/A')} " if pass_name == "district" else ""
        lines.append(f"| {i} | {name} | {r['status']} | {r['findings_count']} | "
                     f"{r['cost'].get('web_search_requests', 0)} {extra_val}| {model_ok} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Fairhaven section (school pass) or Bellingham section (district pass)
    if pass_name == "district":
        bellingham = [r for r in results if "Bellingham" in r.get("district_name", "")]
        if bellingham:
            bh = bellingham[0]
            lines.append("## Bellingham School District (Golden School's District)")
            lines.append("")
            lines.append(f"**Status:** {bh['status']}")
            lines.append(f"**Findings:** {bh['findings_count']}")
            lines.append("")
            for j, f in enumerate(bh.get("findings", []), 1):
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
            lines.append("**Builder: review these findings against known local reality.**")
            lines.append("")
            lines.append("---")
            lines.append("")
    else:
        fairhaven = [r for r in results if r.get("ncessch") == FAIRHAVEN_NCESSCH]
        if fairhaven:
            fh = fairhaven[0]
            lines.append("## Fairhaven Middle School (Golden School)")
            lines.append("")
            lines.append(f"**Status:** {fh['status']}")
            lines.append(f"**Findings:** {fh['findings_count']}")
            lines.append("")
            for j, f in enumerate(fh.get("findings", []), 1):
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
            lines.append("**Builder: review these findings against known local reality.**")
            lines.append("")
            lines.append("---")
            lines.append("")

    # Sensitivity=high findings
    high_sensitivity = []
    for r in results:
        entity = r.get(name_key, r.get("name", "Unknown"))
        for f in r.get("findings", []):
            if f.get("sensitivity") == "high":
                high_sensitivity.append({"entity": entity, "finding": f})

    lines.append("## Sensitivity=High Findings (Need Human Review)")
    lines.append("")
    if high_sensitivity:
        for hs in high_sensitivity:
            lines.append(f"- **{hs['entity']}**: {hs['finding'].get('summary', 'N/A')} "
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
        entity = r.get(name_key, r.get("name", "Unknown"))
        for f in r.get("findings", []):
            if f.get("category") == "other":
                other_findings.append({"entity": entity, "finding": f})

    lines.append("## Category=Other Findings (Need Human Review)")
    lines.append("")
    if other_findings:
        for of_item in other_findings:
            lines.append(f"- **{of_item['entity']}**: {of_item['finding'].get('summary', 'N/A')} "
                        f"(subcategory: {of_item['finding'].get('subcategory', 'none')}, "
                        f"source: {of_item['finding'].get('source_name', 'unknown')})")
    else:
        lines.append("None found in pilot batch.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Validation rejections
    rejections = []
    for r in results:
        entity = r.get(name_key, r.get("name", "Unknown"))
        vs = r.get("validation_summary")
        if vs and vs.get("findings_rejected", 0) > 0:
            rejections.append({"entity": entity, "summary": vs})

    lines.append("## Validation Rejections")
    lines.append("")
    if rejections:
        for rej in rejections:
            vs = rej["summary"]
            lines.append(f"- **{rej['entity']}**: {vs.get('findings_rejected', 0)} rejected "
                        f"({vs.get('wrong_school_detected', 0)} wrong-entity)")
    else:
        lines.append("No findings were rejected by the validation pass.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Findings by category
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
        description="Two-pass Haiku web search context enrichment for WA schools."
    )
    parser.add_argument(
        "--pass", dest="pass_type", choices=["district", "school"], required=True,
        help="Which pass to run: 'district' (Pass 1) or 'school' (Pass 2)."
    )
    parser.add_argument(
        "--pilot", action="store_true",
        help="Run pilot batch only."
    )
    parser.add_argument(
        "--school", dest="single_school", type=str, default=None,
        help="Run school enrichment for a single school by NCESSCH ID (school pass only)."
    )
    parser.add_argument(
        "--district", dest="single_district", type=str, default=None,
        help="Run district enrichment for a single district by name (district pass only)."
    )
    parser.add_argument(
        "--min-district-size", dest="min_district_size", type=int, default=None,
        help="School pass only: only process schools in districts with more than N schools."
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear checkpoint file for this pass and start fresh."
    )
    args = parser.parse_args()

    pass_type = args.pass_type
    logger = setup_logging("enrichment")
    logger.info("=" * 70)
    logger.info(f"Phase 4: Haiku Context Enrichment — {pass_type.upper()} pass")
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

    # Load prompts for the appropriate pass
    if pass_type == "district":
        enrichment_path = DISTRICT_ENRICHMENT_PROMPT
        validation_path = DISTRICT_VALIDATION_PROMPT
        checkpoint_path = DISTRICT_CHECKPOINT_PATH
        checkpoint_key = "district_name"
    else:
        enrichment_path = SCHOOL_ENRICHMENT_PROMPT
        validation_path = SCHOOL_VALIDATION_PROMPT
        checkpoint_path = SCHOOL_CHECKPOINT_PATH
        checkpoint_key = "ncessch"

    logger.info("Loading prompt templates...")
    enrichment_template = load_prompt(enrichment_path)
    validation_template = load_prompt(validation_path)
    logger.info(f"  Enrichment: {enrichment_path}")
    logger.info(f"  Validation: {validation_path}")

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
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            logger.info(f"Checkpoint file cleared: {checkpoint_path}")

    already_processed = load_checkpoint(checkpoint_path, checkpoint_key)
    if already_processed:
        logger.info(f"Checkpoint: {len(already_processed)} {pass_type}s already processed.")

    # ================================================================
    # DISTRICT PASS
    # ================================================================
    if pass_type == "district":
        # Select districts to process
        if args.single_district:
            districts = [args.single_district]
            logger.info(f"Single district mode: {args.single_district}")
        elif args.pilot:
            districts = select_pilot_districts(db, logger)
            districts = [d for d in districts if d not in already_processed]
            logger.info(f"Pilot mode: {len(districts)} districts to process.")
        else:
            all_districts = sorted(db.schools.distinct("district.name"))
            districts = [d for d in all_districts if d not in already_processed]
            logger.info(f"Full batch mode: {len(districts)} districts to process "
                        f"({len(already_processed)} already done, {len(all_districts)} total).")

        if not districts:
            logger.info("No districts to process.")
            mongo_client.close()
            return

        results = []
        start_time = time.monotonic()
        total = len(districts)

        for i, district_name in enumerate(districts, 1):
            district_start = time.monotonic()
            school_count = db.schools.count_documents({"district.name": district_name})

            try:
                status, findings_count, cost, schools_updated = process_district(
                    district_name, api_client, enrichment_template, validation_template,
                    rate_limiter, db, logger
                )

                elapsed = time.monotonic() - district_start
                cost_usd = (cost.get("total_input_tokens", 0) * 0.80 +
                            cost.get("total_output_tokens", 0) * 4.00) / 1_000_000

                logger.info(
                    f"District {i}/{total}: {district_name} ({school_count} schools). "
                    f"{status}, {findings_count} findings, "
                    f"{cost.get('web_search_requests', 0)} web searches, "
                    f"${cost_usd:.4f}, {elapsed:.1f}s."
                )

                write_checkpoint(checkpoint_path, {
                    "district_name": district_name,
                    "status": status,
                    "findings_count": findings_count,
                    "schools_updated": schools_updated,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                if args.pilot or args.single_district:
                    # Read back from MongoDB for the report
                    sample = db.schools.find_one(
                        {"district.name": district_name},
                        {"district_context": 1}
                    )
                    ctx = sample.get("district_context", {}) if sample else {}
                    results.append({
                        "district_name": district_name,
                        "status": status,
                        "findings_count": findings_count,
                        "findings": ctx.get("findings", []),
                        "cost": cost,
                        "validation_summary": ctx.get("validation_summary"),
                        "schools_updated": schools_updated,
                    })

            except Exception as e:
                elapsed = time.monotonic() - district_start
                error_msg = str(e)
                logger.error(
                    f"District {i}/{total}: {district_name}. "
                    f"FAILED after {elapsed:.1f}s: {error_msg}"
                )
                write_checkpoint(checkpoint_path, {
                    "district_name": district_name,
                    "status": "failed",
                    "findings_count": 0,
                    "schools_updated": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": error_msg,
                })

                if args.pilot or args.single_district:
                    results.append({
                        "district_name": district_name,
                        "status": "failed",
                        "findings_count": 0,
                        "findings": [],
                        "cost": {"total_input_tokens": 0, "total_output_tokens": 0,
                                 "web_search_requests": 0, "actual_model": "N/A"},
                        "validation_summary": None,
                        "schools_updated": 0,
                    })

        # Summary
        total_elapsed = time.monotonic() - start_time
        elapsed_str = f"{total_elapsed / 3600:.1f}h" if total_elapsed > 3600 else f"{total_elapsed / 60:.1f}m"
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"District pass complete. {total} districts processed in {elapsed_str}.")
        if results:
            status_counts = Counter(r["status"] for r in results)
            for s, c in status_counts.most_common():
                logger.info(f"  {s}: {c}")
        logger.info("=" * 70)

        if args.pilot and results:
            all_districts_count = len(db.schools.distinct("district.name"))
            generate_pilot_report(results, "district", all_districts_count, logger)
            logger.info("Full batch does NOT run until builder reviews and approves the pilot report.")

    # ================================================================
    # SCHOOL PASS
    # ================================================================
    elif pass_type == "school":
        # Select schools to process
        if args.single_school:
            school_doc = db.schools.find_one({"_id": args.single_school})
            if not school_doc:
                logger.error(f"School {args.single_school} not found in MongoDB.")
                sys.exit(1)
            schools_to_process = [school_doc]
            logger.info(f"Single school mode: {school_doc['name']} ({args.single_school})")
        elif args.pilot:
            schools_to_process = select_pilot_schools(db, logger)
            schools_to_process = [s for s in schools_to_process if s["_id"] not in already_processed]
            logger.info(f"Pilot mode: {len(schools_to_process)} schools to process.")
        else:
            # Optional filter: only schools in districts above a size threshold
            if args.min_district_size:
                big_districts = [d["_id"] for d in db.schools.aggregate([
                    {"$group": {"_id": "$district.name", "count": {"$sum": 1}}},
                    {"$match": {"count": {"$gt": args.min_district_size}}},
                ])]
                query = {"district.name": {"$in": big_districts}}
                logger.info(f"District size filter: >{args.min_district_size} schools → "
                            f"{len(big_districts)} qualifying districts.")
            else:
                query = {}

            all_schools = list(db.schools.find(query, {
                "_id": 1, "name": 1, "district": 1, "address": 1,
                "school_type": 1, "derived.performance_flag_absent_reason": 1
            }))
            schools_to_process = [s for s in all_schools if s["_id"] not in already_processed]
            logger.info(f"Full batch mode: {len(schools_to_process)} schools to process "
                        f"({len(already_processed)} already done, {len(all_schools)} eligible).")

        if not schools_to_process:
            logger.info("No schools to process.")
            mongo_client.close()
            return

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
                cost_usd = (cost.get("total_input_tokens", 0) * 0.80 +
                            cost.get("total_output_tokens", 0) * 4.00) / 1_000_000

                logger.info(
                    f"School {i}/{total}: {school_name} ({ncessch}). "
                    f"{status}, {findings_count} findings, "
                    f"{cost.get('web_search_requests', 0)} web searches, "
                    f"${cost_usd:.4f}, {elapsed:.1f}s."
                )

                write_checkpoint(checkpoint_path, {
                    "ncessch": ncessch,
                    "status": status,
                    "findings_count": findings_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                if args.pilot or args.single_school:
                    context_doc = db.schools.find_one({"_id": ncessch}, {"context": 1})
                    ctx = context_doc.get("context", {}) if context_doc else {}
                    results.append({
                        "ncessch": ncessch,
                        "name": school_name,
                        "district": district_name,
                        "status": status,
                        "findings_count": findings_count,
                        "findings": ctx.get("findings", []),
                        "cost": cost,
                        "validation_summary": ctx.get("validation_summary"),
                    })

            except Exception as e:
                elapsed = time.monotonic() - school_start
                error_msg = str(e)
                logger.error(
                    f"School {i}/{total}: {school_name} ({ncessch}). "
                    f"FAILED after {elapsed:.1f}s: {error_msg}"
                )

                failed_cost = {"total_input_tokens": 0, "total_output_tokens": 0,
                               "web_search_requests": 0, "actual_model": "N/A"}
                failed_doc = build_context_doc("failed", [], None, failed_cost, error=error_msg)
                db.schools.update_one({"_id": ncessch}, {"$set": {"context": failed_doc}})

                write_checkpoint(checkpoint_path, {
                    "ncessch": ncessch,
                    "status": "failed",
                    "findings_count": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": error_msg,
                })

                if args.pilot or args.single_school:
                    results.append({
                        "ncessch": ncessch,
                        "name": school_name,
                        "district": district_name,
                        "status": "failed",
                        "findings_count": 0,
                        "findings": [],
                        "cost": failed_cost,
                        "validation_summary": None,
                    })

        # Summary
        total_elapsed = time.monotonic() - start_time
        elapsed_str = f"{total_elapsed / 3600:.1f}h" if total_elapsed > 3600 else f"{total_elapsed / 60:.1f}m"
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"School pass complete. {total} schools processed in {elapsed_str}.")
        if results:
            status_counts = Counter(r["status"] for r in results)
            for s, c in status_counts.most_common():
                logger.info(f"  {s}: {c}")
        logger.info("=" * 70)

        if args.pilot and results:
            generate_pilot_report(results, "school", doc_count, logger)
            logger.info("Full batch does NOT run until builder reviews and approves the pilot report.")

    mongo_client.close()


if __name__ == "__main__":
    main()
