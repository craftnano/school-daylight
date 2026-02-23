# Phase 4 — Context File

**Phase:** Haiku Context Enrichment
**Started:** 2026-02-22
**Status:** Planning

---

## Environment Verified

| Dependency | Status | Details |
|-----------|--------|---------|
| MongoDB Atlas | OK | `schooldaylight.schools`, 2,532 documents |
| Anthropic API | OK | `claude-haiku-4-5-20251001`, web search tool use works |
| Rate limit | Tier 1 | 5 requests per minute for Haiku |

## Key MongoDB Facts

- **Database:** `schooldaylight` (no underscore)
- **Collection:** `schools`
- **Document count:** 2,532
- **No `context` field exists yet** — Phase 4 creates this
- **Exclusion field:** `derived.performance_flag_absent_reason: "school_type_not_comparable"` (468 schools)
- **School types:** Regular (2,089), Alternative (341), Career & Tech (20), Special Ed (82)

## Fairhaven (Golden School)

- `_id`: `530042000104`
- Name: Fairhaven Middle School
- District: Bellingham
- City: Bellingham, WA
- **Known facts to verify:**
  - Bellingham district assault case
  - Administrator criminal charges
  - These should appear in enrichment findings

## Document Structure (Top-Level Keys)

`_id, name, district, address, school_type, level, grade_span, is_charter, website, phone, metadata, enrollment, demographics, academics, discipline, finance, safety, staffing, course_access, derived`

Phase 4 adds a new top-level `context` key.

## Web Search Token Cost (From Test Call)

- Single enrichment call: ~12K input tokens, ~300-500 output tokens, 1-2 web searches
- `server_tool_use` field tracks web search count
- Usage object also tracks `cache_creation`, `cache_read_input_tokens`

## Files Created by This Phase

- `pipeline/09_haiku_enrichment.py` — Main enrichment script
- `prompts/context_enrichment_v1.txt` — Enrichment prompt template
- `prompts/context_validation_v1.txt` — Validation prompt template
- `data/enrichment_checkpoint.jsonl` — Resume checkpoint (per-school results)
- `phases/phase-4/pilot_report.md` — Pilot batch results for human review
- `phases/phase-4/receipt.md` — Verification receipt

## Decisions From Builder (Carried Into This Phase)

1. One broad web search per school, not multiple targeted searches
2. Max 2 web searches per enrichment call, max 1 per validation call
3. Categories: news, investigations_ocr, awards_recognition, leadership, programs, community_investment, other
4. Skip validation if zero findings
5. School name + district + city + state for disambiguation
6. Prompt versioning on every document
7. Sensitivity flagging for active investigations, lawsuits, criminal charges, abuse
8. Resume capability via checkpoint file
9. Haiku only, no extended thinking
10. Retry cap: 3 attempts with exponential backoff
11. Rate limit: 5 RPM, built into script
12. Pilot batch of 25 schools before full run
13. DonorsChoose, Blue Ribbon, Green Ribbon deferred to post-launch
14. 468 excluded schools — builder asked to consider whether to enrich them
