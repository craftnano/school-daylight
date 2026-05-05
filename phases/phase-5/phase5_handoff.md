# Phase 5 — Production Narrative Generation

**Date:** 2026-04-30
**Phase:** 5 — Production Briefing Generation
**Depends on:** Phase 4.5 (COMPLETE), Phase 4 (COMPLETE), Phases 2-3 (COMPLETE, rerun deferred — see Open Items)
**GitHub:** https://github.com/craftnano/school-daylight (public)

---

## What This Phase Does

Generate production-quality school briefings for all schools in the pipeline. This is the phase where the validated three-stage narrative pipeline runs at scale across 1,630+ enriched schools, producing the Layer 3 (web-sourced findings) narratives that will appear in the final product.

This phase also includes designing and building Layer 2 (data interpretation narratives) — the natural-language descriptions of how each school performs relative to peers, which has not been built yet.

---

## What's Already Built and Validated

### Three-Stage Pipeline (Layer 3 — Web-Sourced Findings)

Validated across 50 schools with zero hallucinations, zero regressions. Cost: $0.0165/school.

1. **Stage 0 (code pre-filter):** Python enforces mechanical rules the models consistently failed at. Conduct-date anchor (exclude findings where underlying conduct >20yr old unless same-type pattern exists within 20yr). Dismissed-case rule (5yr window, no pattern exception). Findings that fail these checks are dropped before the model sees them.
2. **Stage 1 (Haiku triage, `claude-haiku-4-5-20251001`):** Editorial judgment. Applies recency windows (10yr adverse, 5yr allegations, 20yr pattern exception), severity exceptions, parent relevance filter, theme tagging. Passes through only facts explicitly stated in each finding. Does not add outcomes, resolutions, or dispositions.
3. **Stage 2 (Sonnet narrative, `claude-sonnet-4-6`):** Writing only. Generates parent-facing narrative from Stage 1 output. Cannot add facts not in the input. Strips names, suppresses death details, neutralizes gendered student language, strips death locations, applies date-first formatting, frames politically sensitive topics neutrally.

### 14 Editorial Rules (All Passing)

1. No individual names in output (people referenced by role only)
2. No student names ever
3. No student death details (institutional responses only, no manner/location/circumstances)
4. Date-first formatting (year leads every finding; undated findings disclosed as "in an undated report")
5. Recency policy (10yr adverse outcomes, 5yr allegations, 20yr pattern exception, conduct-date anchor, dismissed-case rule)
6. Exoneration exclusion (no adverse finding = exclude; exoneration included when it completes a story)
7. District-level vs. building-specific attribution (district findings on all schools with "at the district level" framing; building-specific incidents only on relevant school)
8. Private citizen exclusion (no institutional role = exclude)
9. Individual student conduct exclusion (unless institutional response triggered)
10. Parent relevance filter ("would a parent make a different decision?")
11. Politically sensitive neutrality (facts only, no editorial)
12. Community action at scale (500+ signatures, substantive = include with "community concern" framing)
13. Consolidate related findings (chronological, connected as patterns)
14. Source quality awareness

### Data Coverage

| Tier | Districts | Schools | School-Level Enrichment |
|------|-----------|---------|------------------------|
| >18 schools per district | 32 | 1,174 | Complete |
| 10-17 schools per district | 35 | 456 | Complete (392 new findings) |
| <10 schools per district | 263 | 902 | District-level only (no school-specific web search) |
| **Total** | **330** | **2,532** | **1,630 enriched (64.7%)** |

---

## What Needs to Be Built in Phase 5

### Layer 3 Production Run

Run the three-stage pipeline on all 1,630 enriched schools. Store narratives in MongoDB.

- Use the **Batch API** (50% cost reduction for async processing). School briefings don't need real-time responses.
- Estimated cost: ~$27 standard, ~$14 with Batch API.
- The 902 schools without school-level enrichment still need briefings — they'll produce mostly empty Layer 3s ("No significant web-sourced context was found") or district-level-only narratives. Still run them through the pipeline for completeness.

### Layer 2 (Data Interpretation Narrative) — NOT YET DESIGNED

This is the narrative interpretation of the structured data from Phases 2-3. Example output: "This school's chronic absenteeism rate of 38% is above the statewide median but consistent with schools serving similar demographics."

Layer 2 does not exist yet. Design decisions needed:

- **Separate Sonnet call** from Layer 3 to prevent cross-contamination (per three-layer trust model in harm register)
- **What data feeds it:** proficiency flags, absenteeism rates, discipline ratios, per-pupil spending, staffing, demographic comparisons, peer cohort position
- **Tone and framing:** informative, not alarmist. "Stands out," "differs from peers," "worth asking about" — not "warning" or "failing"
- **Threshold dependency:** Layer 2 references green/yellow/red flags, which depend on the Phase 3 rerun (see Open Items)

### Three-Layer Trust Model

The briefing must visually and structurally separate:
1. **Layer 1:** Verified data presented visually (charts, tables, flags). No AI interpretation.
2. **Layer 2:** AI narrative interpretation of verified data only. Clearly labeled as AI-generated.
3. **Layer 3:** Web-sourced findings clearly labeled with LLM/web disclaimer.

Implementation may involve separate Sonnet calls with different system prompts to make cross-contamination structurally impossible.

---

## Open Items Carrying Forward

### Phase 3 Rerun (Blocks Layer 2, Does NOT Block Layer 3)

Two changes require re-running the Phase 3 comparison engine:

1. **Chronic absenteeism thresholds:** Current 20%/30% flags 64% of schools post-COVID. Proposed approach: set thresholds based on actual distribution percentiles rather than pre-COVID research baselines. Pull the distribution, pick cutoffs, document methodology. A statistician (Ashley) has agreed to review — but review can happen post-launch. Pick thresholds now, adjust later if needed.
2. **Discipline disparity minimum-N:** Add N=30 subgroup minimum below which disparity ratios are suppressed. Standard statistical convention.

Builder decided to defer this to Phase 5. It blocks Layer 2 design but not Layer 3 production.

### Sensitivity Review (~370 Remaining)

Phase 4 produced 442 high-sensitivity findings. ~70 were manually reviewed, producing the 14 editorial rules. ~370 remain unreviewed. The three-stage pipeline with zero hallucinations makes this less critical than originally envisioned, but unknown finding types could still surface. Builder's decision: trust the pipeline and spot-check rather than reviewing all 370 before production.

### Statistician Review (Blocks Launch, Not Production)

A qualified statistician will review the regression methodology, threshold calibrations, peer cohort definitions, and disparity ratio calculations before briefings are published. Ashley (PhD, quantitative methods) has agreed to review. This blocks publication, not the production run itself.

### District-Level Finding Propagation

The Stage 2 prompt tells Sonnet to frame district findings as "at the district level." But the pipeline must actually deliver district-level findings to every school in the district at query/generation time. Two options: copy findings in MongoDB (data duplication) or pull both school + district findings at runtime (smarter query). This is a Phase 5 wiring task.

### Prompt Extraction Refactor

Two-stage prompts are still embedded as Python string constants in test scripts under `phases/phase-4.5/test_results/`. CLAUDE.md convention says prompts should live in `prompts/` as versioned plaintext. Extract to `prompts/sonnet_two_stage_haiku_v1.txt` and `prompts/sonnet_two_stage_sonnet_v1.txt` before production.

---

## Key Documents

- `CLAUDE.md` — CC operating instructions. Read it first.
- `docs/foundation.md` — Project principles, architecture, known risks. v0.4, April 2026.
- `docs/build_sequence.md` — Phase-by-phase build plan.
- `docs/harm_register.md` — Living harm document. Multiple entries drive Layer 3 rules.
- `docs/build_log.md` — Decision log. All Phase 4.5 decisions logged here.
- `phases/phase-4.5/exit.md` — Phase 4.5 exit document. Summarizes validated architecture.
- `phases/phase-4.5/sonnet_test_plan.md` — Test plan with all 14 tests.
- `prompts/sonnet_layer3_prompt_test_v2.txt` — Single-stage Sonnet prompt (superseded by two-stage but useful as reference for editorial rules).
- Test scripts with embedded two-stage prompts:
  - `phases/phase-4.5/test_results/round1_three_stage/run_round1.py` — Most recent, most complete. Use as starting point for production script.
  - `phases/phase-4.5/test_results/three_stage_prefilter_test/run_six_schools.py` — First three-stage implementation.
- `tests/sonnet_test_config.yaml` — 50-school test config.

---

## Cost Controls

| Control | Limit |
|---------|-------|
| Stage 2 model | `claude-sonnet-4-6` |
| Stage 0+1 model | `claude-haiku-4-5-20251001` |
| API mode | Batch API (50% discount) for production run |
| Max output tokens per call | 2,000 |
| Extended thinking | Disabled |
| Estimated Layer 3 production cost | ~$14 with Batch API (1,630 enriched + 902 district-only) |
| API budget remaining | ~$132 |
| Hard spend cap | Builder will confirm |

---

## Sequence of Work

1. Read `CLAUDE.md`
2. Read `phases/phase-4.5/exit.md` and `docs/harm_register.md`
3. Extract two-stage prompts from test scripts into `prompts/` as versioned plaintext
4. Build district-level finding propagation (runtime query or MongoDB copy)
5. Build production script: Stage 0 → Stage 1 → Stage 2, reading from MongoDB, writing narratives back to MongoDB
6. Wire up Batch API for Stage 2 Sonnet calls
7. Run Layer 3 production on all 2,532 schools → **HUMAN REVIEW GATE** (builder spot-checks sample)
8. Design Layer 2 prompt and architecture (separate Sonnet call, data-only input)
9. Run Phase 3 rerun (absenteeism thresholds + discipline minimum-N)
10. Run Layer 2 production on all 2,532 schools → **HUMAN REVIEW GATE**
11. Implement three-layer trust model in output format

**Publication does NOT happen until:**
- Statistician review complete
- Builder approves production output
- Three-layer trust model implemented
- README/methodology page written

---

## What NOT to Do

- Do NOT modify Phase 4 enrichment scripts or prompts
- Do NOT modify the 14 editorial rules without builder approval
- Do NOT publish or expose briefings externally — this phase produces content, it does not launch
- Do NOT skip the Batch API for production runs — standard API at scale burns budget unnecessarily
- Do NOT blend Layer 2 and Layer 3 content in the same Sonnet call — cross-contamination is a harm register item

---

## Builder Context

The builder is not a developer. The entire project has been built through Claude Code without the builder writing code. All architectural and editorial decisions are the builder's. CC writes code, the builder makes design choices.

The builder will spot-check production output against specific schools she knows well (Bainbridge, Bellingham, Juanita, Phantom Lake, Fairhaven). Make output human-readable. When in doubt about an editorial judgment, surface it to the builder rather than making a unilateral call.

The GitHub repo is public. All commits are visible. Do not commit credentials, raw test outputs with sensitive content, or the `.env` file.

---

## Cost History

| Phase | Cost |
|-------|------|
| Phase 4 original (1,185 entities) | $55.34 |
| Phase 4 expansion (453 schools, 10-17 band) | $26.55 |
| Phase 4.5 Round 1 (50 schools, single-stage) | $1.03 |
| Phase 4.5 Round 2 (6 schools, targeted) | $0.13 |
| Phase 4.5 Juanita two-stage test | $0.03 |
| Phase 4.5 4-school hallucination test | $0.05 |
| Phase 4.5 5-school Sonnet 4.6 validation | $0.08 |
| Phase 4.5 6-school three-stage pre-filter test | $0.12 |
| Phase 4.5 50-school Round 1 three-stage validation | $0.83 |
| **Total project to date** | **~$84** |
| API balance remaining | ~$132 |
