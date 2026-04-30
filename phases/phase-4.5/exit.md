# Phase 4.5 Exit Document — Sonnet Editorial Rule Testing

**Date:** 2026-04-29
**Phase:** 4.5 — AI Layer: Sonnet Editorial Rule Testing
**Status:** COMPLETE
**Next:** Phase 5 (Production Briefing Generation)

---

## What Was Built

A three-stage AI pipeline that produces parent-facing web-context narratives for Washington schools. The pipeline replaces the original single-stage Sonnet design after a confirmed hallucination on Juanita HS (Sonnet fabricated "placed on leave but later cleared"). Architecture validated end-to-end on the original 50-school Round 1 corpus with zero hallucinations.

```
Stage 0: Haiku structured extraction → Python rule application
         (conduct-date anchor + dismissed-case rule)
   ↓ findings that pass eligibility windows
Stage 1: Haiku triage
         (recency, severity exception, exclusion rules; pattern detection)
   ↓ pre-triaged findings
Stage 2: Sonnet 4.6 narrative
         (14 editorial rules; date-first; name stripping; consolidation)
   ↓
Per-school narrative ready for briefing
```

### Files Created
- `tests/sonnet_narrative_test.py` — Single-stage Sonnet rule-test harness (Round 1)
- `tests/sonnet_test_config.yaml` — Round 1 50-school config restored from targeted retest
- `tests/sonnet_test_config.targeted_6school.yaml.bak` — Backup of the Round 2 targeted retest config
- `prompts/sonnet_layer3_prompt_test_v1.txt` — Original single-stage Sonnet prompt
- `prompts/sonnet_layer3_prompt_test_v2.txt` — v2 single-stage prompt (added conduct-date anchor + dismissed-case rules — model failed to apply both, leading to the move to code pre-filter)
- `phases/phase-4.5/sonnet_test_plan.md` (a.k.a. `phase4_5_sonnet_test_plan.md`) — 14-test plan
- `phases/phase-4.5/phase_4_5_handoff.md` — Original Feb 2026 handoff
- `phases/phase-4.5/phase4_5_handoff_resume.md` — April 2026 resume bridge after multi-month gap
- `phases/phase-4.5/test_results/2026-02-23_*` — Round 1 single-stage results (50 schools)
- `phases/phase-4.5/test_results/raw_responses/` — Cached per-school findings + Round 1 narratives (58 schools)
- `phases/phase-4.5/test_results/juanita_two_stage_test/run_two_stage.py` — First two-stage validation
- `phases/phase-4.5/test_results/two_stage_hallucination_test/run_four_schools.py` — Four-school hallucination check
- `phases/phase-4.5/test_results/two_stage_five_school_test/run_five_schools.py` — Sonnet 4.6 + three-fix validation
- `phases/phase-4.5/test_results/three_stage_prefilter_test/run_six_schools.py` — Stage 0 pre-filter validation (Bainbridge + Everett targets)
- `phases/phase-4.5/test_results/round1_three_stage/run_round1.py` — Full 50-school 3-stage replay with Round 1 regression diff
- `phases/phase-4.5/test_results/round1_three_stage/report_2026-04-29_222845.md` — Markdown report organized by Tests 1–14

---

## Results

### Architecture Validation (Three-Stage Pipeline)
- **5-school targeted hallucination test** (Bainbridge, Bethel, Phantom Lake, Soap Lake, Juanita): **0 hallucinations**, **0 student ID leaks**, **0 gender leaks**, **0 real death-circumstance violations**.
- **6-school pre-filter validation** (above 5 + Everett): both stuck-rule cases (Bainbridge 1985 lawsuit, Everett 2018 dismissed lawsuit) correctly dropped at Stage 0.
- **50-school Round 1 replay** (full Round 1 corpus, three-stage): **0 real regressions** vs Round 1 single-stage baseline. 6 auto-flagged "regressions" all confirmed as check-regex artifacts (false positives — death-context-agnostic substring matches).

### All 14 Editorial Rules Passing
Every editorial rule established during Phase 4 sensitivity review is now enforced and validated:
1. No individual names ✓
2. No student names ✓
3. No student death details (manner, location, circumstance all stripped) ✓
4. Date-first formatting (Stage 1 forces date pass-through; 100% of included findings carry dates) ✓
5. Recency policy (10/5/20 windows; severity exception; pattern exception) ✓
6. Exoneration exclusion ✓
7. No institutional connection = exclude ✓
8. Private citizen exclusion ✓
9. Individual student conduct exclusion ✓
10. Parent relevance filter ✓
11. Politically sensitive neutrality (no banned evaluative language) ✓
12. Community action at scale framing ✓
13. Consolidate related findings ✓
14. Source quality awareness ✓

### Three Prompt Fixes Applied (Stage 1 + Stage 2)
1. **Stage 1 date pass-through** — Haiku now emits `date` field in every included finding even when the date lives in metadata, not summary text. Prevents Stage 2 narratives like "something happened" with no year.
2. **Stage 2 gender-neutral student references** — Source text often retains "his daughter," "her son" for student subjects; Sonnet now neutralizes to "the student / they / their child" to prevent identification through demographic narrowing.
3. **Stage 2 death-location stripping** — Rule 4 strengthened to forbid manner of death, *both* specific and general locations ("wooded area at the end of school property" / "on school grounds" / "at the school"), and physical circumstances. Frames around the institutional response only.

### Conduct-Date Anchor + Dismissed-Case Moved to Code Pre-Filter (Stage 0)
Both rules failed when expressed in prompts: Sonnet 4.5, Sonnet 4.6, and Haiku all interpreted SEVERITY EXCEPTION as overriding CONDUCT-DATE ANCHOR for ancient sexual-abuse conduct. Solution: Stage 0 uses Haiku as a structured extractor (conduct dates, response dates, response type, finding type tag) and applies the rules in Python:
- **CONDUCT-DATE ANCHOR**: drop findings where conduct ended >20 years before today, unless another finding in the same school has the same `finding_type_tag` and conduct within the last 20 years (pattern exception).
- **DISMISSED-CASE RULE**: drop findings where `response_type ∈ {dismissal, withdrawal, resolution_without_finding}` and response date is >5 years old. Pattern exception does not apply to dismissed cases.

In the 50-school replay, Stage 0 dropped 15 findings: 14 via conduct-date anchor (mostly the Bainbridge 1985 teacher-abuse lawsuit attached as a district finding to all 10 Bainbridge schools) + 1 via dismissed-case (Everett 2018 lawsuit re: 2003 conduct).

### District-Attribution Rule Encoded (Stage 2 Rule 7)
Round 1 testing showed inconsistent Sonnet behavior across Bainbridge schools — some elementary schools received district findings, others did not. Stage 2 Rule 7 was rewritten:

> Lawsuits, settlements, and investigations against the district appear on all schools in the district, framed with "at the district level" or equivalent. Building-specific incidents (events that occurred at a particular school) appear only on that school's briefing. When you receive a finding, treat it as district-level if it names the district as the actor or defendant; treat it as building-specific only if it names a specific school as the locus of the incident.

The rule was propagated to Stage 2 in all five extant runner scripts. Note: Stage 2 enforces *framing*, not *attribution*. The "appear on all schools in the district" guarantee is upstream — currently the Phase 4 Pass 1 district pass attaches `district_context` to every school in the district, so Stage 2 receives both `context` (school) and `district_context` (district) findings already correctly scoped. Phase 5 production should keep this dual-context wiring intact.

### Model Updated to Sonnet 4.6
Stage 2 narrative model bumped from `claude-sonnet-4-5-20250929` to `claude-sonnet-4-6` (Feb 2026 release). Same price ($3/$15 per MTok). Stage 0 + Stage 1 stay on `claude-haiku-4-5-20251001`. Sonnet 4.6 follows the editorial rules markedly better than 4.5; in side-by-side testing, 4.6 produced cleaner narratives with no fabrication and tighter consolidation across the 50-school corpus.

### Scope Expanded to 10–17 District-Size Band
Phase 4 originally enriched the 32 districts with >18 schools (1,174 schools, 46.3% of the 2,532 total). Phase 4.5 expanded school-level enrichment to the 35 districts in the 10-17 school band (456 schools, 35 districts), bringing total school-level coverage to 1,630 schools across 67 districts (64.3%).
- Run completed via `pipeline/17_haiku_enrichment.py --pass school --min-district-size 9 --max-district-size 17` (a `--max-district-size` flag was added in this phase).
- 453 schools processed (3 already enriched via earlier one-offs).
- **392 new findings** produced. 259 schools enriched, 194 no_findings, 0 failures.
- Cost: $26.55 ($15.23 Haiku tokens + $11.32 web search fees).

### Cost Summary (Phase 4.5)
| Run | Cost |
|-----|------|
| Round 1 single-stage 50-school Sonnet test | $1.03 |
| Round 2 targeted 6-school single-stage retest | $0.13 |
| Juanita two-stage test | $0.029 |
| 4-school two-stage hallucination validation | $0.049 |
| 5-school two-stage with Sonnet 4.6 + fixes | $0.083 |
| 6-school three-stage pre-filter validation | $0.123 |
| 50-school three-stage Round 1 replay | $0.826 |
| Phase 4 Pass 2 expansion (10-17 band, 453 schools) | $26.55 |
| **Phase 4.5 total** | **$28.82** |

Cumulative project total through Phase 4.5: **~$112** ($82 Phase 4 + $0.13 single-stage tests + $1.07 multi-stage tests + $26.55 Phase 4.5 enrichment expansion).

---

## Design Decisions Made

### Three-Stage > Two-Stage > Single-Stage (Architecture Migration)
Single-stage Sonnet hallucinated. Two-stage (Haiku triage → Sonnet narrative) tested clean on 5 schools but couldn't apply conduct-date anchor or dismissed-case rules consistently. Three-stage (Stage 0 code pre-filter → Stage 1 Haiku triage → Stage 2 Sonnet narrative) makes the rule decisions deterministic where they should be and leaves model judgment where it must be.

### Don't Make the Model Decide What's a "Pattern"
Pattern matching (multiple same-type findings in a window) was implemented as `finding_type_tag` equality across Haiku extractions. The Stage 0 prompt gives Haiku a fixed vocabulary of tags and instructs it to use the same tag for the same type of conduct. Python compares tags. Pattern decisions are now reproducible and auditable.

### Death-Circumstance Regex Stays Conservative
The auto-check that flags `'at the school'`, `'was found'`, etc. produces false positives in non-death contexts (e.g., court rulings: "the district was found to have failed..."; school-as-setting: "staff at the school did not follow the plan"). Builder elected not to tighten the regex — the false positives are loud but harmless and human review catches the real cases.

### Three-Stage Cost Increase Is Acceptable
Stage 0 adds ~$0.005/school in Haiku tokens and one extra rate-limited call. Total per-school cost on the 50-school replay: $0.0165. For 2,532 schools at production: ~$42 (without Batch API; ~$21 with the 50% batch discount). Acceptable.

### Sonnet 4.6 Over 4.5 Is a Free Upgrade
No price increase; meaningfully better instruction following on the editorial rules. No reason to stay on 4.5.

---

## Harm Register Updates (Carry Forward)

These editorial rules and harm considerations are encoded in `prompts/` and validated by tests. The harm register at `docs/harm_register.md` should be updated to reflect:

1. **Conduct-date anchor enforced via code, not model** — prevents the Bainbridge-style 1980s lawsuit appearing on a contemporary school briefing.
2. **Dismissed-case rule enforced via code, not model** — prevents the Everett-style dismissed-decade-ago lawsuit appearing on a contemporary briefing.
3. **Death-location and circumstance stripping** — the Bainbridge "wooded location" leakage on the suicide settlement was the canonical failure case; the strengthened Rule 4 covers manner, specific location, general location, and physical circumstance.
4. **Gender-neutral student pronouns** — added because gendered pronouns combined with other narrowing details can identify a student even without a name.
5. **District attribution rule** — district-level institutional accountability findings appear on all schools in the district, framed with "at the district level"; building-specific incidents appear only on that school.

---

## Open Items (Carry Forward to Phase 5)

### Blocks Phase 5 Production
- [ ] Phase 3 rerun: absenteeism thresholds (30%/45%) and discipline minimum-N (10→30)
- [ ] Remaining sensitivity review (~370 findings still need builder-level review)
- [ ] Sexual violence findings full review (78 findings)
- [ ] "Other" category findings review and disposition
- [ ] Batch API budget approved for Phase 5 production run
- [ ] Wire Stage 2's `district_context` reading correctly for production (verify district findings are passed to every school in a district per the new Rule 7 framing)
- [ ] Builder review of Phase 4.5 50-school report (`report_2026-04-29_222845.md`) — formal sign-off on the three-stage pipeline before production

### Carry Forward Design Decisions
- [ ] "school_closure" promotion from "other" to a standard category (carried over from Phase 4)
- [ ] Template vs. LLM boundary for Layer 2 (regression interpretation) — may not need per-school Sonnet calls (carried over from Phase 4)
- [ ] License choice before launch — prevent derivative works reducing data to scores/rankings (carried over from Phase 4)
- [ ] Exoneration scan — search for "cleared," "exonerated," "not sustained," "no finding of wrongdoing" across all findings (carried over from Phase 4)
- [ ] Tighten death-circumstance regex if the false-positive volume causes review fatigue at production scale
- [ ] Decide whether to extract embedded Stage 0/1/2 prompts from the runner scripts into versioned files in `prompts/` per the project convention (deferred during Phase 4.5: "ship first, organize later")
- [ ] Refactor the duplicated Stage 1/Stage 2 prompts living in five separate runner scripts into a single shared module before they drift further

### Future Feature Ideas (Parking Lot — carried forward)
- "Other schools in this district" link on briefing page
- Notable alumni feature (requires its own review)

### Coverage Gap (Documented, Not Closed)
- 894 schools in 263 small/single-school districts (≤9 schools) still have only Pass 1 district-level context, no Pass 2 school-level enrichment. Defensible: smaller districts' significant findings are captured at district level, and individual news coverage of a 1–9-school district's individual school is rare. Revisit only if Phase 5 surfaces a coverage complaint.

---

## Human Review Log
- Reviewed Round 1 50-school single-stage report: identified the Juanita HS hallucination ("placed on leave but later cleared") that triggered the architecture pivot.
- Reviewed Juanita two-stage test: zero hallucinations confirmed; approved expansion to 4-school then 5-school validation.
- Reviewed 5-school two-stage test with Sonnet 4.6 + three prompt fixes: zero real violations, fixes verified against the Bainbridge suicide-settlement litmus test ("in connection with a student's death" — no manner, no location).
- Reviewed 6-school three-stage validation: Bainbridge 1985 lawsuit and Everett 2018 dismissed lawsuit both correctly dropped at Stage 0, confirming the pre-filter approach.
- Reviewed 50-school three-stage Round 1 replay: zero regressions confirmed by inspection of all 6 auto-flagged cases. Stage 0 drops audited and judged correct.
- Approved district-attribution rule wording before propagation to all five Stage 2 prompts.
- Approved Phase 4 Pass 2 expansion to 10-17 school band before kicking off the 2.4-hour run.

---

## Go/No-Go
Phase 4.5: **GO.** Three-stage pipeline validated end-to-end. Zero hallucinations. All 14 editorial rules passing. Conduct-date anchor and dismissed-case rule enforced in code. Editorial rule wording stable across the prompt fleet. Model upgraded to Sonnet 4.6. School-level enrichment expanded to the 10-17 band.

Phase 5 production does NOT start until the blockers above are cleared (notably the Phase 3 rerun, the remaining sensitivity review, and Batch API budget approval).

**Approved by:** Orianda (builder/project owner)
**Date:** 2026-04-29

---

## Process Lessons

### When the model can't apply the rule, the rule isn't the model's job
Three different model versions (Sonnet 4.5, Sonnet 4.6, Haiku 4.5) failed to apply the conduct-date anchor consistently. The right answer wasn't more prompt engineering — it was recognizing that "extract the dates" is a fact-finding task the model is good at, and "compare the dates against a 20-year window" is a comparison task code is good at. Putting them in the same call asked the model to do both, and it preferred to invoke whichever rule felt most relevant per finding.

### Validation is not the same as enforcement
The original v2 prompt added the conduct-date anchor as text. Validation cases caught the failure. Adding more prompt text didn't fix it. Stage 0 fixed it because Stage 0 doesn't trust the model with the comparison.

### "Both two-stage scripts" can mean five
Editorial rules that need to apply at production should be applied wherever the relevant prompt is embedded. The Stage 2 prompt was duplicated across five runner scripts during validation. Future phases should extract the prompts into versioned files in `prompts/` so a rule change is one edit, not five.

### A long sensitivity review is a feature, not a bug
The Bainbridge 1985 lawsuit, Everett 2018 dismissal, Franklin Pierce 36-year-old settlement — all were examples that wouldn't have surfaced as failure cases without the deep human review. Phase 4.5 added two phases of work that weren't in the original plan (two-stage validation, three-stage pre-filter), and both came directly from real cases the builder noticed in test output.

### The hardest rules to write are the rules to put in code
"Don't include the conduct location" is a writing rule. "Don't include findings where conduct is older than 20 years unless there's a same-type pattern within the window" is a procedural rule. Procedural rules belong in code. Writing rules belong in prompts. Untangling which is which is the actual work of the editorial layer.
