# Phase 4 — Context File

**Phase:** Haiku Context Enrichment
**Started:** 2026-02-22
**Status:** Implementing (two-pass design)

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
- **Distinct districts:** 330
- **Exclusion field:** `derived.performance_flag_absent_reason: "school_type_not_comparable"` (468 schools)
- **School types:** Regular (2,089), Alternative (341), Career & Tech (20), Special Ed (82)
- Phase 4 adds two new top-level keys: `district_context` (Pass 1) and `context` (Pass 2)

## Fairhaven (Golden School)

- `_id`: `530042000104`
- Name: Fairhaven Middle School
- District: Bellingham School District
- City: Bellingham, WA
- **Golden school gate:** Builder reviews all returned findings (school + district) against known local reality. No specific incidents pre-specified as pass/fail criteria.

## Two-Pass Design (Added After Pilot Review)

The original single-pass (school-only) pilot showed that school-name searches don't reliably surface district-level events. Fairhaven's search returned only a U.S. News recognition — no district-level investigations appeared because the queries were too school-specific.

**Fix:** Pass 1 searches at the district level ("Bellingham School District Washington state investigations..."), Pass 2 searches at the school level for awards/programs/school news. Phase 5 draws from both layers.

## Web Search Token Cost (From Pilot Data)

- Average per-entity cost: ~$0.034 (tokens) + ~$0.025 (web search)
- Average web searches per entity: ~2.5
- Projected full batch: ~$161 total (both passes)

## Files Created by This Phase

- `pipeline/17_haiku_enrichment.py` — Main enrichment script (both passes)
- `prompts/district_enrichment_v1.txt` — District enrichment prompt (NEW)
- `prompts/district_validation_v1.txt` — District validation prompt (NEW)
- `prompts/context_enrichment_v1.txt` — School enrichment prompt (updated: "Washington state")
- `prompts/context_validation_v1.txt` — School validation prompt (updated: "Washington state")
- `data/district_enrichment_checkpoint.jsonl` — District pass checkpoint (NEW)
- `data/enrichment_checkpoint.jsonl` — School pass checkpoint
- `phases/phase-4/pilot_report.md` — Combined pilot results for human review
- `phases/phase-4/receipt.md` — Verification receipt

## Decisions From Builder (Carried Into This Phase)

1. Two-pass design: district-level (Pass 1) then school-level (Pass 2)
2. "Washington state" in all queries to avoid D.C. contamination
3. Max 2 web searches per enrichment call, max 1 per validation call
4. Categories: news, investigations_ocr, awards_recognition, leadership, programs, community_investment, other
5. Skip validation if zero findings
6. Prompt versioning on every document
7. Sensitivity flagging for active investigations, lawsuits, criminal charges, abuse
8. Resume capability via separate checkpoint files per pass
9. Haiku only, no extended thinking
10. Retry cap: 3 attempts with exponential backoff
11. Rate limit: 5 RPM, built into script
12. Pilot batches for each pass before full runs
13. DonorsChoose, Blue Ribbon, Green Ribbon deferred to post-launch
14. 468 excluded schools — enrichment runs on all of them
15. District findings framed as district-level in Phase 5, not attributed to individual school
