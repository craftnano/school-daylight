# Phase 4 — Plan: Haiku Context Enrichment

**Date:** 2026-02-22
**Phase:** AI Layer — Haiku Context Enrichment
**Depends on:** Phase 3 (APPROVED 2026-02-21)

---

## What This Phase Does

For each school, call Haiku with web search to find contextual signals — news, investigations, awards, leadership changes, OCR complaints, programs. A second Haiku call validates each finding. Results are stored as a `context` field on each school's MongoDB document.

---

## Decision: Enrich All 2,532 Schools (Including Excluded)

The 468 schools excluded from performance regression (`school_type_not_comparable`) are alternative, career-tech, and special education schools. **Context enrichment should run on all of them.** Reason: exclusion is about performance comparison, not relevance. A parent looking at an alternative school still needs to know about investigations, lawsuits, or awards. An alternative school with criminal charges against leadership is just as important to surface as a regular school with the same issue.

The only modification: tag excluded schools in checkpoint output so we can analyze enrichment quality separately if needed. No code-path difference.

---

## Architecture

### One Script: `pipeline/09_haiku_enrichment.py`

Why 09? It runs after the Phase 3 comparison engine (08). It reads from MongoDB and writes back to MongoDB. It does not depend on any local CSV files.

### Two Prompts (Versioned, Stored as Plaintext)

1. **`prompts/context_enrichment_v1.txt`** — Enrichment prompt. Tells Haiku what to search for, what categories to fill, how to structure output, disambiguation rules.

2. **`prompts/context_validation_v1.txt`** — Validation prompt. Receives the enrichment findings and checks: right school? credible source? claim supported by source? Flags wrong-school contamination and unsupported claims.

### Output Schema (Added to Each School Document)

```
context: {
    status: "enriched" | "no_findings" | "failed" | "skipped",
    prompt_version: "v1",
    validation_prompt_version: "v1",
    generated_at: "2026-02-22T...",  # ISO 8601
    model: "claude-haiku-4-5-20251001",
    cost: {
        enrichment_input_tokens: int,
        enrichment_output_tokens: int,
        validation_input_tokens: int,
        validation_output_tokens: int,
        web_search_requests: int,
        total_input_tokens: int,
        total_output_tokens: int
    },
    findings: [
        {
            category: "news" | "investigations_ocr" | "awards_recognition" | "leadership" | "programs" | "community_investment" | "other",
            subcategory: str | null,  # Required if category is "other"
            summary: str,             # 1-3 sentence summary of the finding
            source_url: str,
            source_name: str,         # e.g., "Bellingham Herald", "OSPI"
            source_content_summary: str,  # Brief summary of what the source page says (survives link rot)
            date: str | null,         # ISO date if known, null if not
            confidence: "high" | "medium" | "low",
            sensitivity: "high" | "normal",  # "high" = active investigations, lawsuits, criminal charges, abuse
            validated: true | false,
            validation_notes: str | null  # Why validator flagged or confirmed
        }
    ],
    validation_summary: {
        findings_submitted: int,
        findings_confirmed: int,
        findings_rejected: int,
        findings_downgraded: int,  # Confidence lowered
        wrong_school_detected: int
    },
    error: str | null  # If status is "failed", explains why
}
```

---

## Flow Per School

```
1. Build search context: name + district + city + state
2. Call Haiku with enrichment prompt + web search (max 2 searches)
3. Parse JSON response
   ├── Zero findings → status="no_findings", skip validation, move on
   └── Has findings →
       4. Call Haiku with validation prompt + web search (max 1 search)
       5. Parse validation response
       6. Merge: remove rejected findings, update confidence scores
7. Write context to MongoDB document
8. Append to checkpoint file (JSONL)
9. Log summary for this school
```

---

## Rate Limiting Strategy

**Constraint:** Tier 1, 5 requests per minute for Haiku.

**Approach:** Token-bucket rate limiter with 5 tokens, refilling 1 every 12 seconds. Before each API call, the script waits until a token is available. This means:
- Worst case (every school has findings, needs validation): 2 calls/school → 2.5 schools/min → ~17 hours
- Best case (many schools return nothing): approaches 5 schools/min → ~8.5 hours
- Realistic estimate: ~10-13 hours for the full batch

**No hammering:** The rate limiter prevents 429 errors rather than relying on retry-after-429. If a 429 does happen (edge case), the retry logic waits the full retry-after period before continuing.

---

## Resume Capability

**Checkpoint file:** `data/enrichment_checkpoint.jsonl` — one JSON line per school.

Each line: `{"ncessch": "530042000104", "status": "enriched", "findings_count": 3, "timestamp": "2026-02-22T..."}`

On startup, the script:
1. Reads the checkpoint file (if it exists)
2. Builds a set of already-processed NCES IDs
3. Skips those schools
4. Logs: "Resuming: 1,200 of 2,532 schools already processed. Continuing from school 1,201."

The checkpoint file is append-only during a run. Results are written to both MongoDB and checkpoint simultaneously, so either can serve as ground truth.

---

## Retry Logic

- Max 3 retries per school on API errors (timeout, 500, 529)
- Exponential backoff: 5s, 15s, 45s
- 429 errors: wait `retry-after` header value (or 60s if not present), does NOT count against retry limit
- After 3 failed retries: `status="failed"`, `error="<description>"`, move to next school
- Failed schools do NOT trigger additional web searches — the retry reuses the same prompt, not a new search

---

## Cost Controls

| Control | Limit |
|---------|-------|
| Model | `claude-haiku-4-5-20251001` only |
| Extended thinking | Disabled |
| Web searches per enrichment call | Max 2 |
| Web searches per validation call | Max 1 |
| Max output tokens per call | 2,000 (enrichment), 1,500 (validation) |
| Retries per school | 3 |
| Rate limit | 5 RPM via token bucket |

**Cost estimate per school (from test calls):**
- Enrichment: ~12K input tokens + ~500 output tokens + 1-2 web searches
- Validation: ~15K input tokens + ~300 output tokens + 0-1 web searches
- Haiku pricing: $0.80/MTok input, $4.00/MTok output
- Web search: $10/1000 searches
- **Estimated per-school cost: $0.04-0.06**
- **Full batch estimate: $100-$150 for 2,532 schools**

The pilot of 25 schools will give us a real per-school cost before committing to the full batch.

---

## Pilot Batch: 25 Schools

### Selection Criteria

Pick a representative mix that tests edge cases:

| Category | Count | Why |
|----------|-------|-----|
| **Fairhaven** (golden school) | 1 | Must verify known facts |
| **Large district — Seattle** | 4 | High chance of news, investigations |
| **Large district — Spokane** | 3 | Second largest district |
| **Large district — Bellingham** | 2 | Fairhaven's district, other schools |
| **Mid-size district** | 5 | Moderate news coverage |
| **Rural, small enrollment** | 5 | Expected to return few/no findings |
| **Excluded (alternative/special ed)** | 3 | Test enrichment on non-traditional schools |
| **Charter school** | 2 | Sometimes attract news coverage |

The script will select specific schools from MongoDB by querying for these criteria. Exact NCES IDs will be logged in the pilot report.

### Pilot Report Contents

Saved as `phases/phase-4/pilot_report.md`:
- List of 25 schools with findings count
- Average cost per school (actual)
- Total cost of pilot run
- Projected cost for full batch
- All "other" category findings (for human review of category fit)
- All "sensitivity: high" findings (for human review)
- All validation rejections (for prompt quality assessment)
- Fairhaven findings vs. known facts
- Schools with zero findings (expected for rural?)
- Any errors or failed schools

**Full batch does NOT run until builder reviews and approves pilot report.**

---

## Prompt Design (Summary — Full Text in Prompt Files)

### Enrichment Prompt

System instructions tell Haiku to:
1. Search for `[school name] [district] [city] [state]`
2. Look across predefined categories (news, investigations, awards, etc.)
3. Reject any result that doesn't match on at least district AND city
4. Return structured JSON matching the schema above
5. Include source content summaries that survive link rot
6. Flag findings involving active investigations, lawsuits, criminal charges, or abuse as `sensitivity: "high"`
7. Use "other" category with a subcategory string for anything that doesn't fit standard categories

### Validation Prompt

System instructions tell Haiku to:
1. Review each finding from the enrichment pass
2. Check: Is this the right school? (Name + district + city match)
3. Check: Is the source credible? (News outlets, government sites, official school pages > random blogs, forums)
4. Check: Does the cited source actually support the claimed finding?
5. Optionally perform one web search to verify a claim if needed
6. Return a validated set: confirmed, rejected (with reason), or downgraded (confidence lowered)

---

## What Gets Written to MongoDB

After enrichment + validation:
```python
db.schools.update_one(
    {"_id": ncessch},
    {"$set": {"context": context_document}}
)
```

The `context` key is a new top-level field. It does not modify any existing fields. This makes the operation safe and non-destructive — if something goes wrong, we can `$unset` the `context` field from all documents and start over.

---

## Logging

Following CLAUDE.md rules — complete English sentences, not codes.

**Per-school log line:**
```
School 1,201/2,532: Fairhaven Middle School (530042000104). Enrichment found 4 findings. Validation confirmed 3, rejected 1 (wrong school). Cost: $0.05. Elapsed: 14s.
```

**Summary at end of batch:**
```
Batch complete. 2,532 schools processed in 11h 42m.
  Enriched: 1,847 (73.0%)
  No findings: 612 (24.2%)
  Failed: 73 (2.9%)
  Total cost: $127.43
  Sensitivity=high findings: 34 (need human review)
  Category=other findings: 89 (need human review)
  Failed schools logged to: logs/enrichment_failures_2026-02-22.csv
```

**Log files:**
- Console output (always)
- `logs/enrichment_YYYY-MM-DD_HHMMSS.log` (timestamped log file)
- `logs/enrichment_failures_YYYY-MM-DD.csv` (failed schools with error details)

---

## Testing and Verification

### During Pilot
1. Fairhaven must surface the Bellingham assault case / administrator criminal charges
2. At least some Seattle schools should have news findings
3. Rural schools may legitimately have zero findings — that's OK
4. No hallucinated findings (validation should catch these)
5. All source URLs should be real (spot-check manually)

### After Full Batch
1. Fairhaven golden school verification (field-by-field)
2. Distribution summary: how many enriched, no findings, failed
3. Sensitivity findings count for human review queue
4. "Other" findings count for human review queue
5. Cost summary: actual vs. estimated
6. Sample 10 random schools — do findings look real?

---

## Files This Phase Creates

| File | Purpose |
|------|---------|
| `pipeline/09_haiku_enrichment.py` | Main enrichment script |
| `prompts/context_enrichment_v1.txt` | Enrichment prompt template |
| `prompts/context_validation_v1.txt` | Validation prompt template |
| `data/enrichment_checkpoint.jsonl` | Resume checkpoint |
| `phases/phase-4/pilot_report.md` | Pilot results for human review |
| `phases/phase-4/receipt.md` | Verification receipt |
| `logs/enrichment_*.log` | Run logs |
| `logs/enrichment_failures_*.csv` | Failed school details |

---

## Sequence of Work

1. Write enrichment prompt (`prompts/context_enrichment_v1.txt`)
2. Write validation prompt (`prompts/context_validation_v1.txt`)
3. Build the enrichment script (`pipeline/09_haiku_enrichment.py`)
4. Run pilot batch (25 schools)
5. Generate pilot report → **HUMAN REVIEW GATE**
6. (After approval) Run full batch
7. Generate verification receipt
8. Commit everything
