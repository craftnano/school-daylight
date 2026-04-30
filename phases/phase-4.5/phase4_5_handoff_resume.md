# School Daylight — Phase 4.5 Handoff (Resume Point: April 2026)

## What This Document Is
This is a handoff document for Claude Code, written by the advisory chat (Claude.ai) to bridge a gap between sessions. The builder (Orianda) paused work in late February 2026 and is resuming in late April 2026. The previous CC session expired without writing its own handoff.

## Project Summary
School Daylight is a civic data transparency tool that generates AI-written school briefings for Washington state K-12 parents. The pipeline combines federal/state education data (Phases 2-3) with web-sourced public findings (Phase 4) into narratives written by Claude under 14 editorial rules.

## Current Phase: 4.5 (Sonnet Editorial Rule Testing)
Phase 4.5 validates that the AI can write about sensitive school findings responsibly before running production on all 2,532 schools (Phase 5).

## Architecture: Two-Stage Pipeline (Validated, Not Yet Production-Ready)

The original single-stage approach (Sonnet does everything) produced at least one confirmed hallucination — Sonnet fabricated "placed on leave but later cleared" for Juanita HS when no such outcome existed in the input data.

The validated replacement is a two-stage pipeline:

- **Stage 1 (Haiku):** Triage. For each finding, apply recency rules, output include/exclude with rule citation. Pass through only facts explicitly stated in the finding text. Do not add any outcomes, resolutions, or dispositions not in the source. Tag each included finding by theme.
- **Stage 2 (Sonnet):** Narrative writing. Write the briefing using only the findings Haiku passed through. Do not add any facts not present in the input. Follow formatting and editorial rules.

This was tested on 5 schools (Juanita, Bainbridge, Bethel, Phantom Lake, Soap Lake) with **zero hallucinations** across all 5, compared to at least 1 in single-stage. Cost: ~$0.012/school.

### Model Update Required
Tests were run on `claude-sonnet-4-5-20250929` and `claude-haiku-4-5-20251001`. As of April 2026:
- **Stage 1:** Use `claude-haiku-4-5-20251001` (unchanged)
- **Stage 2:** Use `claude-sonnet-4-6` (new model, released Feb 17 2026 — better instruction following, same price $3/$15 per MTok)

Update the model IDs in the pipeline config and test scripts before running anything.

## Three Prompt Fixes Needed (Stage 2)

These were identified in the two-stage testing but not yet applied:

### 1. Date Pass-Through
**Problem:** Stage 1 passes finding summary text but sometimes drops dates that live in metadata, not the summary. Stage 2 narrative says something happened but not when.
**Fix:** Stage 1 prompt must always include the finding date in its pass-through output, even if it's not in the summary text.

### 2. Gender Pronoun Stripping
**Problem:** Raw finding text contains "his daughter," "she reported," etc. Haiku correctly passes through the text without modification, but Sonnet doesn't neutralize gendered language that could help identify students.
**Fix:** Add to Stage 2 prompt: "Neutralize gendered language in student contexts. Replace 'his daughter,' 'her son,' 'she,' 'he' with gender-neutral alternatives when referring to students."

### 3. Death-Location Stripping
**Problem:** The rules suppress "suicide" correctly, but Sonnet still wrote "wooded location at the end of school property" for the Bainbridge case — nearly as identifying as naming the manner of death.
**Fix:** Add to Stage 2 prompt: "When referencing a death-related institutional response, do not include location details, manner of death, or physical circumstances. Frame only around the institutional response (lawsuit, settlement, investigation) and its outcome."

## Conduct-Date Anchor — Code Pre-Filter Likely Needed

**Rule:** When a recent institutional response (lawsuit, settlement) addresses underlying conduct more than 20 years old, exclude the finding unless it's part of a pattern with same-type findings involving conduct within 20 years.

**Status:** This rule was added to the Sonnet prompt (`sonnet_layer3_prompt_test_v2.txt`) but both Sonnet and Haiku consistently fail to apply it. Franklin Pierce was correctly excluded, but Bainbridge 1980s abuse was included in both single-stage and two-stage tests.

**Recommended approach:** Move to a code pre-filter that runs before Stage 1. Extract conduct date from finding text (may need a quick Haiku extraction call), compare to institutional response date, exclude if conduct > 20 years old and no same-type pattern exists. This removes the judgment call from the model entirely.

**However:** Sonnet 4.6 may handle this better than the older Sonnet. Test first before building the pre-filter.

## Dismissed-Case Rule — Same Situation

**Rule:** Dismissed, withdrawn, or resolved-without-adverse-finding cases use the 5-year window. Pattern exception does not apply to dismissed cases.

**Status:** Added to v2 prompt. Cascade HS/Everett dismissed 2018 lawsuit was still included in testing. Same recommendation: test with Sonnet 4.6 first, build code pre-filter if it still fails.

## Key Prompt Files
- **v1 prompt (original):** `prompts/sonnet_layer3_test_v1.txt`
- **v2 prompt (conduct-date anchor + dismissed cases added):** `prompts/sonnet_layer3_prompt_test_v2.txt`
- Stage 1 and Stage 2 prompts from two-stage testing are in `phases/phase-4.5/test_results/juanita_two_stage_test/` and `phases/phase-4.5/test_results/two_stage_hallucination_test/`

## Test Results Location
- Round 1 (50 schools, single-stage): `phases/phase-4.5/test_results/2026-02-23_224243/`
- Round 2 targeted retest (6 schools, single-stage v2): results in the test_results directory
- Juanita two-stage test: `phases/phase-4.5/test_results/juanita_two_stage_test/`
- 4-school hallucination test: `phases/phase-4.5/test_results/two_stage_hallucination_test/`

## Other Open Items

### District-Level vs. Building-Specific Findings
**Decision needed (from builder):** When a lawsuit/settlement is against the district but the incident occurred at a specific school, does the finding appear on all schools in the district or only the relevant building?
- Sonnet made its own inconsistent calls (some Bainbridge elementary schools got district findings, others didn't)
- Ordway Elementary test showed Sonnet excluding district lawsuit settlements when viewed from a different building
- **Builder's tentative direction:** District-level institutional accountability findings (lawsuits, settlements, investigations) appear on all schools; building-specific incidents appear only on the relevant building. Not yet encoded in prompt.

### 10-17 School District Expansion
The current pipeline covers districts with 18+ schools (2,532 schools). The builder was exploring whether to add districts with 10-17 schools before the Phase 5 production run. MongoDB was down when the count was attempted. Now that Atlas is back up, run the count to inform the decision.

### Batch API
The Phase 5 production run should use the Anthropic Batch API (50% cost reduction for async processing). School briefings don't need real-time responses. Estimated production cost: ~$31 standard, ~$16 with batch.

### Pre-Phase 5 Checklist (from test plan)
- [ ] All Phase 4.5 tests pass
- [ ] Harm register entries current and reflected in prompts
- [ ] Phase 3 rerun complete (absenteeism thresholds, discipline minimum-N)
- [ ] Remaining sensitivity review complete (all 442 findings)
- [ ] Batch API pricing confirmed and budget approved
- [ ] Name-stripping instruction verified in prompt
- [ ] Date-first formatting instruction verified in prompt
- [ ] Three-layer trust model implemented in prompt architecture

## Key Project Documents
- `docs/foundation.md` — Project principles
- `docs/build_sequence.md` — Phase-by-phase plan
- `docs/harm_register.md` — Living harm document
- `docs/build_log.md` — Decision log
- `CLAUDE.md` — CC operating instructions
- `phases/phase-4.5/sonnet_test_plan.md` — Test plan (renamed to `phase4_5_sonnet_test_plan.md` by CC)
- `tests/sonnet_narrative_test.py` — Test script
- `tests/sonnet_test_config.yaml` — Test config (currently pointed at v2 prompt, 6-school targeted list)

## What To Do Next
1. Update model IDs to `claude-sonnet-4-6` and `claude-haiku-4-5-20251001`
2. Apply the three Stage 2 prompt fixes (dates, gender pronouns, death locations)
3. Run the 5 hallucination test schools through the updated two-stage pipeline
4. Check whether Sonnet 4.6 handles conduct-date anchor and dismissed-case rules
5. If rules still fail, build code pre-filter
6. Run a broader validation batch
7. Proceed to Phase 5 production

## Cost History
- Phase 4 (Haiku enrichment): ~$82
- Phase 4.5 Round 1 (50 schools, single-stage): $1.03
- Phase 4.5 Round 2 (6 schools, targeted): $0.13
- Phase 4.5 Juanita two-stage: $0.029
- Phase 4.5 4-school hallucination test: $0.049
- **Total project to date: ~$83.24**
