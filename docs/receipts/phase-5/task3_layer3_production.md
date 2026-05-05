# Phase 5 — Task 3 Verification Receipt: Layer 3 Production Run

**Date:** 2026-05-02 (UTC)
**Task:** Generate web-sourced-context narratives for the production set, write to MongoDB, deliver a stratified spot-check sample for builder review.
**Result:** PASS (with one carry-forward: 105 schools never processed by Phase A; see below).

---

## Headline

- **2,532 / 2,532 schools have `layer3_narrative` populated** — full Washington-state coverage. (Updated 2026-05-02 after the resume run on the 105 schools the killed Phase A had not reached, then again later 2026-05-02 after the Stage 1 v2 regeneration on the affected pool.)
- **1,885 schools have full Sonnet 4.6 narratives with per-paragraph citations** (`status=ok`, `prompt_version=layer3_v3`). Of those, **185 schools** were regenerated under Stage 1 v2 (positive-content rule retired) and carry `stage1_prompt_version=layer3_v2, regenerated_2026_05_02=true`; the other **1,700** are the original Stage 1 v1 production batch, unchanged.
- **647 schools have the canonical fallback narrative** ("No significant web-sourced context was found for this school.") — `status=no_findings` (232) or `status=stage1_filtered_to_zero` (415). These are correct outcomes for schools whose Phase 4 enrichment surfaced nothing publishable, or whose findings did not survive Stage 1's recency / parent-relevance / pattern triage.
- **0 schools without `layer3_narrative`** — full coverage maintained.
- **Zero Stage 2 errors** across all three production batches (1,792-school full batch, 68-school resume batch, 185-school regeneration batch).

---

## Total Project Spend

| Phase | What | Cost |
|---|---|---:|
| Phase A initial | Stage 0 + Stage 1 Haiku across 2,427 schools (corrected $1/$5 pricing) | $19.15 |
| Phase A resume | Stage 0 + Stage 1 Haiku across the remaining 105 schools | $0.71 |
| Dry runs v1–v5 | Sonnet 4.6 batch on 70 distinct schools (5+5+50+8+2) | $0.46 |
| Full Stage 2 | Sonnet 4.6 batch on 1,792 schools, prompt v3 | $12.69 |
| Final Stage 2 | Sonnet 4.6 batch on 68 newly-queued schools from the resume Phase A | $0.47 |
| Positive-content rule diagnostic | full population scan, no API spend | $0.00 |
| 10-school v2 test | Stage 1 v2 + Stage 2 v3 random sample | $0.16 |
| Stage 1 v2 regeneration | 185 schools across affected pool, Stage 1 v2 + Stage 2 v3 | $2.60 |
| **Total Layer 3 production** | | **~$36.24** |

Hard cap was $50; came in at ~72% of cap including the v2 promotion + regeneration cycle. Caching never fired (system prompt fell below Anthropic's 1,024-token minimum cacheable segment), so projected cache savings did not materialize but the run stayed comfortably under cap regardless.

---

## Architecture Used

The full batch ran with:
- **Stage 0** (Haiku 4.5, structured extraction + Python conduct-date / dismissed-case rules): from Phase A, pre-computed.
- **Stage 1** (Haiku 4.5, editorial triage with recency / severity / pattern rules): from Phase A, pre-computed. Output stored in `phases/phase-5/production_run/stage1_results.jsonl` (1,794 schools queued for Stage 2).
- **Stage 2** (Sonnet 4.6 batch, prompt `layer3_stage2_sonnet_narrative_v3.txt`):
  - 9 original writing rules (date-first, no names, no student identifiers, death-related institutional response, consolidation, neutral tone, district-attribution, vary transitions, gender-neutral student references).
  - **Rule 15** — timeless past-tense framing (added v2).
  - **Rule 16** — source-fidelity verbs for individual conduct (added v2; fired/terminated drift accepted as known residual per builder decision 2026-05-01).
  - **Rule 17** — grade-level identifier redaction (added v2).
  - **Rule 4 strengthened** — explicit manner-of-death and location-of-death suppression, with required phrasings (added v3 after Frontier MS "drive-by shooting on West Loop Drive" leak).
  - **Per-paragraph citations** — `[Sources: URL1; URL2]` block at end of each paragraph (added v2).
- **URL enrichment**: Stage 1 doesn't carry `source_url` through. The full-batch runner re-queries each school's deduped findings via `pipeline.layer3_findings.get_findings_for_stage0()` and matches Stage 1 `original_text` to source `summary` (with `<cite>` tag stripping and 100-char prefix fallback). 99.96% of findings (4,561 / 4,563) matched at scale; the 2 unmatched render as `[Sources: ... (one source unavailable)]`.

---

## Rule Compliance at Scale

A random 30-school sample of v3 production narratives, checked for v3 rule compliance:

| Check | Result |
|---|---|
| Has `[Sources: ...]` citation block | 30 / 30 |
| Rule 4 forbidden phrases (`drive-by shooting`, `died following a`, `fatal shooting`, `overdose`) | 0 hits |
| Rule 17 forbidden phrases (`senior year`, `junior year`, `sophomore year`, `freshman year`) | 0 hits |
| Rule 15 forbidden phrases (`remain allegations`, `remains an active`, `no resolution has been reported`) | 0 hits |

Rule 16's accepted-residual "fired vs terminated" drift is not auto-checked here; per builder decision it's a known accepted substitution (substantively equivalent, legal-risk delta negligible).

---

## Sample Narratives — Receipt-Mandated Six-School Spot Check

The handoff named six specific schools whose narratives the builder wants to read first.

### Bainbridge High School (`530033000043`)

> In 2023, at the district level, a $300,000 verdict was rendered against the Bainbridge Island School District in connection with its failure to protect a student from aggressive bullying and sexual harassment. The cited records do not reflect a resolution beyond the awarded damages.
>
> Also in 2023, the Bainbridge Island School District resolved a civil lawsuit with a $1.325 million settlement stemming from the district's liability for a student's death. Available records do not reflect any further institutional action beyond the settlement.
>
> In 2026, the principal of Bainbridge High School was arrested by the Poulsbo Police Department on allegations of driving under the influence, reckless endangerment, and driving with a suspended license. Following the arrest, the principal was placed on leave. The cited records do not reflect a disposition beyond the placement on leave.

(MongoDB record, prompt_version=layer3_v2 — generated during dry-run v4. Death-circumstance suppression on the suicide settlement passes: no manner, no location, no physical circumstance.)

### Sehome High School (`530042000113`)

In MongoDB on prompt_version=layer3_v3 (full batch). Multi-paragraph district-level Title IX consolidation with citation blocks. The district-attribution rule resolves cleanly across the three Title IX-related findings.

### Squalicum High School (`530042002693`)

In MongoDB on prompt_version=layer3_v3 (full batch). The cross-context dedup case (the Feb 2026 bus-assault liability article was independently extracted by both Pass 1 and Pass 2) is resolved at the data layer; the narrative reads cleanly with a single attribution per article.

### Juanita High School (`530423000670`)

In MongoDB on prompt_version=layer3_v3 (full batch). The original Sonnet-4.5 hallucination case continues to NOT exhibit the "placed on leave but later cleared" fabrication that triggered the architecture pivot. The 2015 Juanita-incident finding is presented as the source describes it (administrators discouraging police involvement) with no fabricated outcome.

### Phantom Lake Elementary (`530039000082`)

In MongoDB on prompt_version=layer3_v3 (full batch). Multi-finding consolidated narrative covering district financial oversight, two principal administrative-leave incidents, OCR investigation, and a series of legal actions. Rule 15 timeless-tense and Rule 17 grade-level redaction both apply.

### Fairhaven Middle School (`530042000104`)

In MongoDB on prompt_version=layer3_v3 (full batch). The golden school. Bellingham district context (Title IX district pattern + bond + levy) attached to the school via the district_context propagation that Task 2 verified.

For full text of all six, query MongoDB directly:
```python
for nid in ["530033000043","530042000113","530042002693","530423000670","530039000082","530042000104"]:
    doc = db.schools.find_one({"_id": nid}, {"name":1,"layer3_narrative.text":1})
    print(doc["name"]); print(doc["layer3_narrative"]["text"]); print("---")
```

---

## Stratified Spot-Check Sample (25 schools)

Generated at `phases/phase-5/spot_check_sample.md`. Selection design:
- 10 schools from districts with 18+ schools (well-enriched / Pass 2 priority).
- 10 schools from districts with 10–17 schools (Pass 2 expanded band).
- 5 schools from districts with fewer than 10 schools (district-level context only).
- All 25 schools are OUTSIDE the 50-school Phase 4.5 validation set.
- ≥3 schools come from districts with known recent incidents (district_context contains a sensitivity=high or category=investigations_ocr finding) — actual count: 3.
- Each school has `layer3_narrative.status == "ok"`.
- Sampling is reproducible: `random.seed(20260430)`.

Stratum counts: big=10, mid=10, small=5. Open the markdown file in Finder for builder review.

---

## Errors and Failures

- **Zero** Stage 2 generation errors across 1,792 batch requests.
- **Zero** schools with `layer3_narrative.error` set.
- **2 / 4,563** findings (0.04%) had no source_url and rendered as `(one source unavailable)` in their citation block. This is expected behavior — Phase 4 enrichment occasionally produces findings without URLs.
- **One client-side recovery**: the Stage 2 batch script crashed once on `client.messages.batches.retrieve()` with a 404 NotFoundError ~20 seconds after `create()` returned the batch ID. This is an Anthropic API read-after-write indexing lag race condition. The batch was server-side-alive and unaffected; relaunching the script picked up the saved batch_id from `phases/phase-5/production_run/stage2_v3_batch_id.txt` and resumed polling. Completion succeeded normally. Worth noting: the runner should add retry/backoff on transient `retrieve` failures so this can't crash an unattended run; not done in this iteration.

---

## What's NOT Done

- ~~**105 unprocessed schools.**~~ **DONE 2026-05-02.** Resume Phase A processed all 105 schools (status distribution: 68 queued for Stage 2, 26 stage1_filtered_to_zero, 11 no_findings). The 68 queued schools went through a final Sonnet v3 batch (`msgbatch_01ResB16DcKqAFDHiUzis38Q`, 100% success, $0.47). Final coverage is now 2,532 / 2,532. Resume cycle total cost: $1.18.
- **Cache effectiveness.** Adding `cache_control` markers to the system prompt produced zero cache hits because the system prompt is below Anthropic's 1,024-token minimum cacheable segment. Acceptable trade-off for this run; would need a prompt-restructuring effort to materialize savings on a future re-generation.

---

## Files Touched

- New: `prompts/layer3_stage2_sonnet_narrative_v2.txt` (Rules 15, 16, 17, citations).
- New: `prompts/layer3_stage2_sonnet_narrative_v3.txt` (Rule 4 strengthened with manner/location-of-death suppression).
- Modified: `pipeline/layer3_prompts.py` — added `load_stage2_v2()` and `load_stage2_v3()`. v1 preserved as default.
- Modified: `pipeline/18_layer3_production.py` — pricing constants corrected to Haiku 4.5 ($1/$5).
- New: `pipeline/19_layer3_stage2_v3_batch.py` — full-batch runner with v3 prompt + URL enrichment.
- New dry-run scripts: `phases/phase-5/dry_run_v3.py`, `dry_run_v4.py`, `dry_run_v5.py`.
- New: `phases/phase-5/build_spot_check_sample.py`, `phases/phase-5/aggregate_production_stats.py`.
- New: `phases/phase-5/dry_run_narratives_v3.md`, `v4.md`, `v5.md`.
- New: `phases/phase-5/spot_check_sample.md` (the 25-school review document).
- New: `docs/receipts/phase-5/task3_layer3_production.md` (this file).

MongoDB writes:
- `schools.<id>.layer3_narrative` populated for 2,427 of 2,532 schools.

---

## Decision

**Task 3: PASS — full WA-state coverage achieved. Phase 5 RE-OPENED 2026-05-02 evening pending the rule audit.**

Three production batches generated cleanly: the full 1,792-school batch (`msgbatch_014HnVdUAUnajrNzycW9uAiG`), the 68-school resume batch (`msgbatch_01ResB16DcKqAFDHiUzis38Q`), and the 185-school Stage 1 v2 regeneration batch (`msgbatch_016aKDCXANFiYgxpwPavcpJb`). Zero errors across all three. Rule 4 strengthened with manner-of-death suppression behaved as designed under live test. Citations render with real URLs at 99.96% match rate. Total cost ($36.24) came in at 72% of the $50 hard cap. Six receipt-mandated sample schools all produced sensible narratives. Twenty-five-school stratified spot-check was reviewed and approved by the builder. **2,532 / 2,532 schools have `layer3_narrative` populated** — full Washington-state Layer 3 coverage maintained.

**Stage 1 v2 promotion (2026-05-02 evening).** A full-population diagnostic found 185 schools whose raw Phase 4 findings contained positive-content vocabulary (Blue Ribbon, Schools of Distinction, Title I Distinguished, dual-language program designations, Teacher of the Year, FIRST robotics, state/national academic competitions, etc.) and exactly 1 of those 185 had positive content in its final narrative. The 184-school filter-out came almost entirely from one categorical Stage 1 rule (v1 line 37) that contradicted foundation.md's "recognize real achievement" mission. Rule retired permanently. Stage 1 v2 promoted to canonical. 185 affected schools regenerated under Stage 1 v2 + Stage 2 v3 unchanged. 93 of those 185 narratives now contain positive content directly; the other 92 had positive findings filtered out by recency rules, which is a separate question carrying forward to the rule audit.

Carry-forward observations in the build log: (a) Stage 2 genericizes named complainant organizations (e.g., "StandWithUs" → "a nonprofit legal team") — candidate for v4 refinement; (b) same-district narrative duplication across schools is structurally correct district-attribution but creates near-identical paragraphs across same-district school pages — Phase 6 frontend design problem; (c) Sonnet's emergent "On a positive note specific to..." transitional language between adverse and positive content is a deliberate platform voice choice, not a defect; (d) **positive-content recency calibration** is the open audit item — the 10-year window may be too short for substantive sustained recognitions like Blue Ribbon; (e) Phase 5 is not closed until the **full rule audit** of all editorial rules across Stage 0/1/2 prompts for coherence with foundation.md and harm_register.md is complete.

Cache-hit gap remains an architectural limit (system prompt below 1,024-token minimum), not blocking.

**Approved by:** Claude Code (Phase 5 agent)
**Date:** 2026-05-02 (initial production run); 2026-05-02 evening (Stage 1 v2 regeneration). Phase 5 re-opened pending rule audit.
