# Phase 4 — Plan: Haiku Context Enrichment

**Date:** 2026-02-22
**Phase:** AI Layer — Haiku Context Enrichment
**Depends on:** Phase 3 (APPROVED 2026-02-21)

---

## What This Phase Does

Two-pass enrichment via Haiku with web search:

1. **Pass 1 — District-level enrichment.** For each of ~330 distinct districts, search for district-wide contextual signals: investigations, lawsuits, scandals, leadership changes. Findings are stored as `district_context` on every school document in that district. This catches events that affect schools but don't appear in school-specific searches (e.g., a district superintendent's criminal charges, a district-wide OCR investigation).

2. **Pass 2 — School-level enrichment.** For each of 2,532 schools, search for school-specific signals: awards, programs, individual school news. Findings are stored as `context` on the school document. This is the existing per-school search.

Both passes use the same validation pattern (second Haiku call checks each finding), same sensitivity flagging, same cost controls.

Phase 5 narratives draw from both layers. District findings are framed as district-level context, not attributed to the individual school.

---

## Decision: Enrich All 2,532 Schools (Including Excluded)

The 468 schools excluded from performance regression (`school_type_not_comparable`) are alternative, career-tech, and special education schools. **Context enrichment should run on all of them.** Reason: exclusion is about performance comparison, not relevance. A parent looking at an alternative school still needs to know about investigations, lawsuits, or awards. An alternative school with criminal charges against leadership is just as important to surface as a regular school with the same issue.

The only modification: tag excluded schools in checkpoint output so we can analyze enrichment quality separately if needed. No code-path difference.

---

## Decision: "Washington state" in All Search Queries

All search queries — both district-level and school-level — use "Washington state" instead of "Washington" to avoid contamination from Washington, D.C. results. This applies to both enrichment prompts and any hardcoded query patterns.

---

## Architecture

### One Script: `pipeline/17_haiku_enrichment.py`

Why 17? Pipeline numbering continues from Phase 3 (01-16 already exist). It reads from MongoDB and writes back to MongoDB. It does not depend on any local CSV files.

Two run modes:
- `--pass district` — Run Pass 1 (district-level enrichment)
- `--pass school` — Run Pass 2 (school-level enrichment)
- `--pilot` — Pilot batch (applicable to either pass)

### Four Prompts (Versioned, Stored as Plaintext)

1. **`prompts/district_enrichment_v1.txt`** — District enrichment prompt. Searches for district-wide investigations, lawsuits, scandals, leadership changes.
2. **`prompts/district_validation_v1.txt`** — District validation prompt. Checks: right district? credible source? claim supported?
3. **`prompts/context_enrichment_v1.txt`** — School enrichment prompt. Searches for school-specific awards, programs, news.
4. **`prompts/context_validation_v1.txt`** — School validation prompt. Checks: right school? credible source? claim supported?

### Output Schema — District Context (Pass 1)

Stored as `district_context` on every school document in the district:

```
district_context: {
    district_name: str,
    status: "enriched" | "no_findings" | "failed",
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
        total_output_tokens: int,
        actual_model: str
    },
    findings: [
        {
            category: "news" | "investigations_ocr" | "awards_recognition" | "leadership" | "programs" | "community_investment" | "other",
            subcategory: str | null,
            summary: str,
            source_url: str,
            source_name: str,
            source_content_summary: str,
            date: str | null,
            confidence: "high" | "medium" | "low",
            sensitivity: "high" | "normal",
            validated: true | false,
            validation_notes: str | null
        }
    ],
    validation_summary: {
        findings_submitted: int,
        findings_confirmed: int,
        findings_rejected: int,
        findings_downgraded: int,
        wrong_school_detected: int
    },
    error: str | null
}
```

### Output Schema — School Context (Pass 2)

Stored as `context` on each school document (unchanged from original plan):

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
        total_output_tokens: int,
        actual_model: str
    },
    findings: [
        {
            category: "news" | "investigations_ocr" | "awards_recognition" | "leadership" | "programs" | "community_investment" | "other",
            subcategory: str | null,
            summary: str,
            source_url: str,
            source_name: str,
            source_content_summary: str,
            date: str | null,
            confidence: "high" | "medium" | "low",
            sensitivity: "high" | "normal",
            validated: true | false,
            validation_notes: str | null
        }
    ],
    validation_summary: {
        findings_submitted: int,
        findings_confirmed: int,
        findings_rejected: int,
        findings_downgraded: int,
        wrong_school_detected: int
    },
    error: str | null
}
```

---

## Flow — Pass 1 (District)

```
1. Query MongoDB for distinct district names (~330)
2. For each district:
   a. Call Haiku with district enrichment prompt + web search (max 2 searches)
      Search: "[district name] Washington state investigations lawsuits scandals leadership changes"
   b. Parse JSON response
      ├── Zero findings → status="no_findings", skip validation
      └── Has findings →
          c. Call Haiku with district validation prompt + web search (max 1 search)
          d. Parse validation response
          e. Merge: remove rejected findings, update confidence scores
   f. Write district_context to EVERY school document in that district
   g. Append to district checkpoint file
   h. Log summary
```

## Flow — Pass 2 (School)

```
1. For each school (all 2,532):
   a. Call Haiku with school enrichment prompt + web search (max 2 searches)
      Search: "[school name] [district name] [city] Washington state"
   b. Parse JSON response
      ├── Zero findings → status="no_findings", skip validation
      └── Has findings →
          c. Call Haiku with school validation prompt + web search (max 1 search)
          d. Parse validation response
          e. Merge: remove rejected findings, update confidence scores
   f. Write context to school document
   g. Append to school checkpoint file
   h. Log summary
```

---

## Rate Limiting Strategy

**Constraint:** Tier 1, 5 requests per minute for Haiku.

**Approach:** Token-bucket rate limiter with 5 tokens, refilling 1 every 12 seconds. Before each API call, the script waits until a token is available. Same rate limiter for both passes (they run sequentially, not concurrently).

**Pass 1 time estimate (~330 districts):**
- Worst case (every district has findings, needs validation): 2 calls/district → 165 districts/hour → ~2 hours
- Best case (many districts return nothing): approaches 5 districts/min → ~1.1 hours
- Realistic estimate: ~1.5–2 hours

**Pass 2 time estimate (2,532 schools):**
- Same as original plan: ~10-13 hours realistic

**Total: ~12-15 hours for both passes.**

**No hammering:** The rate limiter prevents 429 errors rather than relying on retry-after-429. If a 429 does happen (edge case), the retry logic waits the full retry-after period before continuing.

---

## Resume Capability

Two separate checkpoint files (passes run independently):

**District checkpoint:** `data/district_enrichment_checkpoint.jsonl`
Each line: `{"district_name": "Bellingham School District", "status": "enriched", "findings_count": 3, "schools_updated": 12, "timestamp": "..."}`

**School checkpoint:** `data/enrichment_checkpoint.jsonl`
Each line: `{"ncessch": "530042000104", "status": "enriched", "findings_count": 3, "timestamp": "..."}`

On startup, each pass reads its checkpoint, builds a set of already-processed entities, and skips them.

---

## Retry Logic

Same for both passes:

- Max 3 retries per entity on API errors (timeout, 500, 529)
- Exponential backoff: 5s, 15s, 45s
- 429 errors: wait `retry-after` header value (or 60s if not present), does NOT count against retry limit
- After 3 failed retries: `status="failed"`, `error="<description>"`, move to next entity
- Failed entities do NOT trigger additional web searches — the retry reuses the same prompt, not a new search

---

## Cost Controls

| Control | Limit |
|---------|-------|
| Model | `claude-haiku-4-5-20251001` only |
| Extended thinking | Disabled |
| Web searches per enrichment call | Max 2 (both passes) |
| Web searches per validation call | Max 1 (both passes) |
| Max output tokens per call | 4,096 (both passes) |
| Retries per entity | 3 |
| Rate limit | 5 RPM via token bucket |

**Cost estimate (from pilot data):**

| Pass | Entities | Avg cost/entity | Projected total |
|------|----------|----------------|----------------|
| District (Pass 1) | ~330 | ~$0.034 | ~$11 |
| School (Pass 2) | 2,532 | ~$0.034 | ~$86 |
| Web search (both) | ~6,400 searches | $10/1000 | ~$64 |
| **Total** | | | **~$161** |

Pilot of each pass will give real numbers before committing to full batches.

---

## Pilot Batches

### Pass 1 Pilot: 10 Districts

Pick a representative mix:
- 3 large districts (Seattle, Spokane, Bellingham) — high chance of findings
- 4 mid-size districts (Tacoma, Yakima, Kennewick, Olympia)
- 3 small/rural districts — expected to return few/no findings

### Pass 2 Pilot: 25 Schools (Already Completed)

The original school-level pilot ran successfully (16 enriched, 9 no findings, 0 failures). It will be re-run after prompt updates ("Washington state" fix) and after Pass 1 completes, so the builder can evaluate both layers together.

### Pilot Report Contents

Saved as `phases/phase-4/pilot_report.md` (updated for both passes):
- Per-district and per-school results with findings counts
- Average cost per entity (actual) for each pass
- Total cost and projected full-batch cost
- All "other" category findings (for human review)
- All "sensitivity: high" findings (for human review)
- All validation rejections (for prompt quality assessment)
- Fairhaven: all findings (school + district) for builder review against known local reality
- Any errors or failed entities

**Full batch does NOT run until builder reviews and approves pilot results for each pass.**

---

## Prompt Design (Summary — Full Text in Prompt Files)

### District Enrichment Prompt (NEW)

System instructions tell Haiku to:
1. Search for `[district name] Washington state investigations lawsuits scandals leadership changes`
2. Focus on district-wide events: superintendent/board actions, OCR or state investigations, lawsuits, financial scandals, bond measures, district-wide policy changes
3. Reject any result that refers to a different district or a different state (especially Washington, D.C.)
4. Return structured JSON matching the district_context schema
5. Include source content summaries that survive link rot
6. Flag findings involving active investigations, lawsuits, criminal charges, or abuse as `sensitivity: "high"`
7. Do NOT include individual school-level events — those belong in the school-level pass

### District Validation Prompt (NEW)

System instructions tell Haiku to:
1. Review each finding from the district enrichment pass
2. Check: Is this the right district? (Name and state match)
3. Check: Is the source credible?
4. Check: Does the cited source actually support the claimed finding?
5. Specifically check for Washington state vs. Washington, D.C. contamination
6. Optionally perform one web search to verify a claim if needed
7. Return a validated set: confirmed, rejected (with reason), or downgraded

### School Enrichment Prompt (Updated)

System instructions tell Haiku to:
1. Search for `[school name] [district name] [city] Washington state`
2. Look across predefined categories: awards, programs, school-specific news, leadership
3. Reject any result that doesn't match on at least district AND city
4. Do NOT duplicate district-level findings — those are handled separately
5. Return structured JSON matching the context schema
6. Include source content summaries that survive link rot
7. Flag findings involving active investigations, lawsuits, criminal charges, or abuse as `sensitivity: "high"`
8. Use "other" category with a subcategory string for anything that doesn't fit standard categories

### School Validation Prompt (Updated)

System instructions tell Haiku to:
1. Review each finding from the school enrichment pass
2. Check: Is this the right school? (Name + district + city match)
3. Check: Is the source credible?
4. Check: Does the cited source actually support the claimed finding?
5. Optionally perform one web search to verify a claim if needed
6. Return a validated set: confirmed, rejected (with reason), or downgraded

---

## What Gets Written to MongoDB

### Pass 1 — District Context

After enrichment + validation for a district, write to ALL schools in that district:
```python
db.schools.update_many(
    {"district.name": district_name},
    {"$set": {"district_context": district_context_document}}
)
```

The `district_context` key is a new top-level field. Every school in the district gets the same district_context document. This is intentional — district-level findings apply to the whole district.

### Pass 2 — School Context

After enrichment + validation for a school:
```python
db.schools.update_one(
    {"_id": ncessch},
    {"$set": {"context": context_document}}
)
```

The `context` key is a new top-level field per school.

Both fields are safe and non-destructive — if something goes wrong, we can `$unset` either field from all documents and start over.

---

## Logging

Following CLAUDE.md rules — complete English sentences, not codes.

**Pass 1 per-district log line:**
```
District 45/330: Bellingham School District (12 schools). Enrichment found 3 findings. Validation confirmed 2, rejected 1 (wrong district). Cost: $0.04. Elapsed: 18s.
```

**Pass 2 per-school log line:**
```
School 1,201/2,532: Fairhaven Middle School (530042000104). Enrichment found 4 findings. Validation confirmed 3, rejected 1 (wrong school). Cost: $0.05. Elapsed: 14s.
```

**Summary at end of each pass:**
```
Pass 1 complete. 330 districts processed in 1h 42m.
  Enriched: 187 (56.7%)
  No findings: 128 (38.8%)
  Failed: 15 (4.5%)
  Total cost: $11.22
  Sensitivity=high findings: 12 (need human review)
```

**Log files:**
- Console output (always)
- `logs/enrichment_YYYY-MM-DD_HHMMSS.log` (timestamped log file)
- `logs/enrichment_failures_YYYY-MM-DD.csv` (failed entities with error details)

---

## Testing and Verification

### During Pilot (Pass 1)
1. Bellingham district: builder reviews all findings against known local reality
2. Seattle district: should surface investigations or news given district size
3. Small rural districts: may legitimately have zero findings — that's OK
4. No Washington, D.C. contamination in results
5. All source URLs should be real (spot-check manually)

### During Pilot (Pass 2)
1. Fairhaven: builder reviews school-level + district-level findings together for credibility and completeness
2. At least some schools should have school-specific findings distinct from district findings
3. No hallucinated findings (validation should catch these)
4. All source URLs should be real (spot-check manually)

### After Full Batch (Both Passes)
1. Fairhaven golden school check: builder reviews all findings (school + district) against known local reality
2. Distribution summary per pass: how many enriched, no findings, failed
3. Sensitivity findings count for human review queue
4. "Other" findings count for human review queue
5. Cost summary per pass: actual vs. estimated
6. Sample 10 random schools — do school + district findings look real and non-overlapping?

---

## Files This Phase Creates

| File | Purpose |
|------|---------|
| `pipeline/17_haiku_enrichment.py` | Main enrichment script (both passes) |
| `prompts/district_enrichment_v1.txt` | District enrichment prompt template (NEW) |
| `prompts/district_validation_v1.txt` | District validation prompt template (NEW) |
| `prompts/context_enrichment_v1.txt` | School enrichment prompt template (updated) |
| `prompts/context_validation_v1.txt` | School validation prompt template (updated) |
| `data/district_enrichment_checkpoint.jsonl` | District pass resume checkpoint (NEW) |
| `data/enrichment_checkpoint.jsonl` | School pass resume checkpoint |
| `phases/phase-4/pilot_report.md` | Combined pilot results for human review |
| `phases/phase-4/receipt.md` | Verification receipt |
| `logs/enrichment_*.log` | Run logs |
| `logs/enrichment_failures_*.csv` | Failed entity details |

---

## Sequence of Work

1. Write district enrichment prompt (`prompts/district_enrichment_v1.txt`)
2. Write district validation prompt (`prompts/district_validation_v1.txt`)
3. Update school enrichment prompt — "Washington state" fix, add note about not duplicating district findings
4. Update school validation prompt — "Washington state" fix
5. Update `pipeline/17_haiku_enrichment.py` — add `--pass district` mode, district checkpoint, district MongoDB write
6. Run Pass 1 pilot (10 districts) → **HUMAN REVIEW GATE**
7. (After approval) Run Pass 1 full batch (~330 districts)
8. Re-run Pass 2 pilot (25 schools, with updated prompts) → **HUMAN REVIEW GATE**
9. (After approval) Run Pass 2 full batch (2,532 schools)
10. Generate combined verification receipt
11. Commit everything
