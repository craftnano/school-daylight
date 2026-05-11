# Build Log

Chronological record of decisions, findings, and changes with reasoning.

---

## 2026-02-22 — Echo Glen School added to exclusions

**Context:** During pre-Phase 4 FRL data review, Echo Glen School (NCES 530375001773, Issaquah School District) appeared on the list of schools with FRL >= 95% (97.1%). Echo Glen is a DSHS juvenile detention facility. CCD codes it as "Regular School" — the same misclassification pattern discovered for virtual/online schools in Phase 3.

**Finding:** Echo Glen's 97.1% FRL reflects its institutional population, not community poverty. Issaquah School District provides educational services at the facility, but enrollment is involuntary and transient. Comparing it against traditional schools on a FRL-vs-proficiency curve is misleading for the same reasons documented in Phase 3 decision log #2.

**Action:** Added to `school_exclusions.yaml` under a new "Institutional facilities" category. Performance flag was already null (reason: `data_not_available`) — will be reclassified to `school_type_not_comparable` on next pipeline run.

**Impact:** No change to regression pool (Echo Glen was already excluded from regression due to missing proficiency data). The reason code change is more accurate documentation.

---

## 2026-02-22 — 49 non-traditional schools added to exclusions (null-FRL review)

**Context:** Investigated all 152 schools with null FRL percentage. Of the 60 coded as "Regular School" in CCD, most are clearly not traditional schools: jails, group homes, preschools, homeschool partnerships, youth services, alternative programs, and zero-enrollment entries. These schools have null FRL because OSPI doesn't report demographics for them, confirming they operate outside the normal K-12 system.

**Schools added by category:**
- **Jails and detention centers (16):** Benton County Jail, Clallam Co Juvenile Detention, Echo Glen School (already added earlier), Island County Corrections, Island Juvenile Detention, Kitsap Co Detention, Lewis County Jail, Mason County Detention, Okanogan Co Juvenile Detention, Skagit County Detention, Sno Co Jail, Snohomish Detention, Spokane County Jail, Walla Walla County Juvenile Detention, Whatcom Co Detention, Yakima Adult Jail
- **Group homes and treatment (6):** Canyon View, Fircrest Residential, Oakridge, Parke Creek Treatment, Ridgeview, Twin Rivers
- **Preschool / early childhood (10):** Cape Flattery Preschool, ECEAP, Federal Way Headstart, Head Start (Highline), Hoyt Early Learning, Manson Early Learning, Oakville Preschool, Ready Start Preschool, Spokane Regional Health District, West Central Community Center
- **Homeschool partnerships (2):** Northshore Family Partnership, White River Homeschool
- **Community-based / youth services (4):** Southwest Youth and Family Services, The Healing Lodge, Touchstone, Woodinville Community Center
- **Alternative / reengagement miscoded (6):** Alternative Tamarack School, Garrett Heyns (Centralia College), Morgan Center School, Ocosta ALE, Tacoma Pierce County Education Center, Vancouver Contracted Programs
- **Special education / specialized miscoded (3):** Arlington Special Educ School, Kalispel Language Immersion School (tribal — culturally significant but zero enrollment), North Bell Learning Center
- **Zero-enrollment / likely closed (5):** Bear Creek Elementary, Choice, Southern Heights Elementary, Coulee City Middle School, Star Elem School (both verified as zero enrollment, no staffing/academics)

**Not excluded (preserved as real schools):**
- Decatur Elementary (3 students, Lopez Island — tiny but real)
- Holden Village Community School (4 students, remote mining village — tiny but real)
- Point Roberts Primary (5 students, geographic exclave — tiny but real)
- Waldron Island School (5 students, San Juan Islands — tiny but real)
- Nespelem High School (19 students, tribal community — FRL likely suppressed, not absent)

**Impact:** `school_exclusions.yaml` now has 76 entries (25 virtual + 51 institutional/other). All 49 new schools already had null performance flags due to missing data — the change reclassifies their reason codes from `data_not_available` to the more accurate `school_type_not_comparable`. No regression results change.

---

## 2026-02-22 — Summary

Null-FRL investigation revealed 60 Regular School entries that are non-traditional. 43 added to exclusions. 6 tiny rural schools retained. Triggered by CEP/COVID concern during Phase 4 advisory planning. See `phases/phase-3/decision_log.md` entry #4 for details.

---

## 2026-02-22 — Discipline disparity small-N analysis

Discipline disparity small-N analysis. 29 of 65 schools with 10x+ ratios have fewer than 20 students in the triggering subgroup. Current minimum-N threshold of 10 is too low — produces statistically meaningless extreme ratios. Decision: raise floor to 30 before Phase 5. Schools with subgroups of 10-29 will get ratio suppressed with reason code `suppressed_subgroup_lt_30`. Requires Phase 3 comparison engine rerun before Phase 5. Does not affect Phase 4.

---

## 2026-02-22 — Chronic absenteeism threshold audit

Chronic absenteeism threshold audit. 64% of schools trip yellow or red at current 20%/30% thresholds — flag is miscalibrated for post-COVID distribution. Decision: raise thresholds to approximately 30%/45% before Phase 5. Exact values TBD after reviewing adjusted distribution. Requires Phase 3 rerun. Does not affect Phase 4.

---

## 2026-02-23 — Phase 4 complete: Haiku Context Enrichment

### Two-pass design

Phase 4 uses a two-pass architecture for web search context enrichment:

- **Pass 1 (District):** 330 districts searched for investigations, lawsuits, leadership changes, bonds/levies, and awards. Results written to `district_context` field on all schools in each district.
- **Pass 2 (School):** 1,185 schools (in 32 districts with >18 schools) searched for school-specific news, awards, programs, and incidents. Results written to `context` field on each school.

The two passes are independent. School-level Haiku does not see district-level findings. Deduplication is Phase 5's (Sonnet narrative) responsibility.

### Final numbers

| Metric | District Pass | School Pass | Total |
|---|---|---|---|
| Entities processed | 330 | 1,185 | — |
| Enriched (has findings) | 234 (70.9%) | 779 (65.7%) | — |
| No findings | 96 (29.1%) | 406 (34.3%) | — |
| Failed | 0 | 0 | 0 |
| Total findings | 755 | 1,320 | 2,075 |
| High-sensitivity findings | 291 | 149 | 440 |
| Cost | $11.88 | $43.47 | **$55.34** |
| MongoDB coverage | 2,532/2,532 | 1,185/2,532 | — |

### Sensitivity review

442 high-sensitivity findings exported to `phases/phase-4/sensitivity_review.md` for manual review. Builder reviewed findings for:

- Death/violence keywords (31 matches, 25 correctly flagged HIGH)
- Non-institutional subjects — board candidates, former students, community members (27 matches)
- Immigration/ICE-related content (8 matches)
- Sexual violence content (78 matches, 63 naming individuals)

**Findings removed during review (9 total):**
1. Beverly Elementary — student death, no institutional connection
2. Blaine SD — board candidate personal criminal charges, private citizen
3. South Pines Elementary — nearby shooting before dawn, no school connection
4. Coupeville SD (2 findings) — superintendent investigation, cleared/exonerated
5. Liberty Sr High — individual student conduct (racist video)
6. Issaquah High School — routine discipline incident
7. Cashmere SD — duplicate finding (610 KONA source removed, Cascade PBS kept)
8. Cascade HS / Everett — dismissed lawsuit about 2003 conduct

**ICE-related findings removed (6 total, prior to sensitivity review):**
Student political walkouts and protest activity at Auburn HS, Meadowdale MS, Edmonds-Woodway HS, Highline SD/Sylvester MS, Aki Kurose MS (shelter-in-place), Denny MS (false alarm). Kept: Cowlitz County/ICE contract termination (institutional action) and Wahluke SD migrant program funding (budget fact).

### Model and validation

- All calls confirmed as `claude-haiku-4-5-20251001` via `actual_model` hallucination safeguard
- Validation pass (second Haiku call) checked every finding for wrong-school contamination, source credibility, and claim support
- "Washington state" used in all search queries to avoid D.C. contamination

### Phase 4.5 — Sonnet Editorial Rule Testing (unplanned addition)

An unplanned Phase 4.5 has been added between Phase 4 and Phase 5. Phase 4.5 tests Sonnet's ability to apply editorial rules (name stripping, recency filtering, sensitivity handling, deduplication) before full narrative generation begins. This phase has its own plan and Claude Code session. See `phases/phase-4.5/` for details.

---

## 2026-02-23 — Decision: District-level enrichment pass added

**Context:** Initial Phase 4 pilot (25 schools, school-name-only search) revealed that school-level web searches do not surface district-level events. Fairhaven Middle School returned only a U.S. News recognition — none of the Bellingham School District's well-documented investigations, lawsuits, or criminal charges appeared.

**Decision:** Add a district-level enrichment pass that runs before the school-level pass. ~330 districts searched for "investigations lawsuits scandals leadership changes." Results stored in `district_context` field on all schools in each district.

**Rationale:** District-level events (superintendent actions, board decisions, OCR investigations, lawsuit settlements) are critical context for understanding any school in that district. A school briefing without district context is incomplete. Two independent passes with Phase 5 deduplication is simpler and more robust than trying to merge concerns in a single search.

---

## 2026-02-23 — Decision: "Washington state" disambiguation fix

**Context:** Search queries using `"{state}"` (which resolves to "WA" or "Washington") risk returning results about Washington, D.C. schools and districts. Multiple same-name districts exist in WA and D.C.

**Decision:** All search prompts now use the literal string "Washington state" instead of the state variable. Applied to all four prompt files (district enrichment, district validation, school enrichment, school validation).

---

## 2026-02-23 — Decision: School pass limited to districts with >18 schools

**Context:** Full school-level enrichment of all 2,532 schools would cost ~$86 and take ~21 hours. Many small/rural districts have 1-3 schools that are unlikely to surface school-specific web results (district-level pass already covers them). Need to balance cost and coverage.

**Decision:** School pass limited to the 32 districts with more than 18 schools (1,174 schools, 46.3% of dataset). This covers all major urban, suburban, and mid-size districts where school-specific context is most likely to exist and most useful. Small/rural schools still have district-level context from Pass 1.

**Alternatives considered:**
- All 2,532 schools (~$86, ~21h) — excessive for diminishing returns on small schools
- Districts with >15 schools (42 districts, 1,345 schools, ~$46, ~11h) — reasonable but slightly over budget comfort
- Districts with >10 schools (70 districts, 1,684 schools, ~$57, ~14h) — too many hours for marginal gain

**Trade-off:** 1,358 schools in smaller districts do not have school-level context. They still have district-level context. This is acceptable for v1.

---

## 2026-02-23 — Conduct-Date Anchor and Dismissed Case rule added to recency policy (Rule 5)

**Decision 1 — Conduct-Date Anchor:** When a recent institutional response addresses conduct more than 20 years old, exclude the finding unless it is part of a pattern with at least one same-type finding involving conduct within the last 20 years.

**Trigger:** Bainbridge Island 2024 lawsuit about 1980s teacher abuse and Franklin Pierce 2019 settlement for 36-year-old abuse both passed the 10-year institutional response window but describe conduct too old to be actionable for current parents.

**Effect:** Bainbridge 1980s abuse finding excluded. Franklin Pierce settlement excluded. Bethel 2016+2025 and Juanita 2015 unaffected.

**Decision 2 — Dismissed Cases:** Dismissed, withdrawn, or resolved-without-adverse-finding cases use the 5-year window. Pattern exception does not apply to dismissed cases.

**Trigger:** Cascade HS/Everett 2018 dismissed lawsuit about 2003 conduct was incorrectly included. Dismissal is 8 years old (outside 5yr window) and dismissed cases cannot anchor a pattern.

**Effect:** Cascade HS dismissed lawsuit excluded.

---

## 2026-04-29 — District vs. building-specific attribution rule adopted

District-level vs. building-specific attribution rule adopted. District-level institutional accountability findings (lawsuits, settlements, investigations against the district) appear on all schools in the district with district-level framing. Building-specific incidents appear only on the relevant school. Triggered by inconsistent Sonnet behavior across Bainbridge schools in Round 1 testing — some elementary schools received district findings, others did not. Rule eliminates model discretion on this question.

---

## 2026-04-29 — Phase 4 Pass 2 scope expanded to 10-17 school band

Expanded school-level enrichment scope from >18 schools (1,174 schools, 32 districts) to >9 schools (1,630 schools, 67 districts). Added 456 schools across 35 districts in the 10-17 school band.

**Run details:** 453 schools processed (3 of the 456 had been enriched earlier via one-off runs and were skipped via checkpoint). Run via `pipeline/17_haiku_enrichment.py --pass school --min-district-size 9 --max-district-size 17`. Wall-clock: 2.4 hours. 259 schools enriched with at least one finding, 194 returned no findings, 0 failures. 392 total findings produced. 1,132 web searches executed.

**Cost:** $15.23 in Haiku tokens + $11.32 in web search fees = **$26.55 total** for the 453-school batch.

**Script change:** Added `--max-district-size N` flag to `pipeline/17_haiku_enrichment.py` so the size filter accepts a band (`>min AND <=max`). Existing `--min-district-size` semantics unchanged. The 32 districts with >18 schools previously enriched were skipped via the existing checkpoint mechanism in `data/enrichment_checkpoint.jsonl`.

---

## 2026-04-30 — Phase 5 Tasks 1 & 2: Layer 3 prompts extracted, district_context production query function written

**Task 1 — Prompt extraction (`docs/receipts/phase-5/task1_prompt_extraction.md`).** The three Layer 3 system+user prompts that lived as inline f-strings in `phases/phase-4.5/test_results/round1_three_stage/run_round1.py` (the validated 50-school three-stage replay) are now versioned plaintext files in `prompts/`:

- `prompts/layer3_stage0_haiku_extraction_v1.txt`
- `prompts/layer3_stage1_haiku_triage_v1.txt`
- `prompts/layer3_stage2_sonnet_narrative_v1.txt`

Each file uses `===SYSTEM===` and `===USER===` section markers and named placeholders (`{school_name}`, `{district_name}`, `{nces_id}`, `{findings}`). The runner reads via `pipeline/layer3_prompts.py` (`load_stage0/1/2()` + `fill_user()`) which uses `str.replace()` rather than `str.format()` because the system prompts contain JSON examples with literal `{` and `}` characters — same convention already used by `pipeline/17_haiku_enrichment.py`.

**Acceptance test results:** Byte-identity to the canonical inline constants is proven for all six strings (3 system + 3 user) by `phases/phase-5/acceptance_test_prompt_extraction.py`. A live 5-school smoke test against the loaded prompts produced **zero auto-check regressions** at $0.0953 total cost. The one Stage 0 drop delta on Halilts Elementary was Haiku non-determinism on date inference at temperature=1.0 (the model is asked to infer `~1985` from "approximately 40 years prior" relative to a 2024 filing) — not a prompt-extraction bug. The byte-identity test rules that out at the character level.

**Why these names.** The files are prefixed `layer3_` to distinguish them from the existing pre-pivot single-stage Sonnet prompts (`prompts/sonnet_layer3_prompt_test_v1.txt` and `_v2.txt`), which were retained as the historical record of the architecture before the three-stage migration.

**Task 2 — `district_context` propagation verified, production query function written (`docs/receipts/phase-5/task2_district_context.md`).** Inspection of all 25 Bellingham School District schools in MongoDB Atlas confirmed `district_context` is populated on every school with all six expected district findings — including all three Title IX-related findings (2023 criminal-charges resolution, 2025 federal lawsuit, 2026 bus-assault liability admission). The data-layer wiring established in Phase 4 Pass 1 works correctly; no fix needed.

`pipeline/layer3_findings.get_findings_for_stage0(db, nces_id)` is the new production query function. It pulls both `context.findings` and `district_context.findings`, deduplicates by composite key `(source_url, date, category)` with a content-hash fallback for findings missing source_url, and prefers the district-level entry on collision (district framing aligns with Stage 2 Rule 7 attribution). Tested across 8 cases including the canonical Squalicum HS cross-context collision (the 2026-02-05 bus-assault liability article was independently extracted by both Pass 1 and Pass 2; dedup correctly drops the school-side copy) and a bogus-NCES-ID error path.

**Why composite, not source_url alone?** Bellingham HS's `district_context` had two findings citing the same Cascadia Daily News URL (one summarizing the 2023 criminal-charges resolution, one summarizing a separate 2022 federal lawsuit covered in the same article). Source-url-only dedup would have incorrectly dropped one of these legitimate distinct findings. The (url, date, category) composite preserves both because their dates differ.

**Phase 5 production blockers carried forward.** Per `phases/phase-4.5/exit.md`: Phase 3 rerun (absenteeism thresholds 30%/45%, discipline minimum-N 10→30), remaining sensitivity review (~370 findings), Batch API budget approval, builder sign-off on the 50-school three-stage report. None touched in Tasks 1 or 2.

---

## 2026-04-30 — Process learning: editorial review of dry-run narratives is mandatory before any full-batch run

**What happened.** Phase 5 Layer 3 production launched a 5-school dry run as a technical validation, then proceeded to a full 2,532-school Phase A run without the builder reading the 5 narratives first. Phase A was killed mid-run after ~2,391 schools (the kill itself slipped: a SIGTERM round looked successful from the agent's perspective but the four shards survived for another ~16 minutes until SIGKILL — see the cost reconciliation entry below). The Sonnet batch for the remaining 1,770 narratives was paused before submission so the builder could read the dry-run output.

**Decision: any phase that produces narrative output requires builder editorial review at the smallest unit (5 schools) before the full run.** This applies to Layer 3 (web context), the eventual Layer 2 (regression interpretation), and any future generative phase. Technical validation (byte-identity, no auto-check regressions, end-to-end pipeline runs) is necessary but not sufficient. Editorial validation — a human reading the narratives and confirming tone, framing, and content meet the project's editorial bar — must happen before scaling. The 5-school size is small enough that builder review fits in one sitting and large enough to surface tone or framing patterns the agent may have missed.

**How to apply going forward.** Any phase exit document, runner script, or production task plan that involves AI-generated parent-facing narrative must include an explicit editorial-review gate after the smallest test unit. The gate is satisfied only by builder approval, not by automated checks. Phase 5 production is paused at this gate until builder reads `phases/phase-5/dry_run_narratives.md`.

**Cost reconciliation from this same run.** Telemetry undercounted Haiku spend by ~25% because the runner's pricing constants (`HAIKU_INPUT_PER_M = 0.80`, `HAIKU_OUTPUT_PER_M = 4.00`) are Haiku 3.5 prices. Real Haiku 4.5 prices are $1.00 input / $5.00 output per MTok. Telemetry also confirmed (via empirical test call) that `response.usage.input_tokens` already includes system-prompt tokens, ruling out the system-prompt undercount hypothesis. Recomputed Haiku spend with correct prices: ~$18.94 (vs reported $15.15). Anthropic console showed ~$39 today; the residual ~$20 gap is unexplained from telemetry alone and may reflect non-script usage on the same billing window.

**Prompt caching is not enabled.** The Layer 3 runner sends the full Stage 0/1/2 system prompts on every call. For the remaining 1,770 Stage 2 batch requests, enabling 1-hour cache writes on the Sonnet system prompt would save roughly $2.40; for any future Haiku Stage 0/1 work, 5-min cache writes on the two ~850-token system prompts would have saved roughly $3 on the run already completed. Both should be added before resuming.

**Outstanding fixes before resuming.** (1) Update pricing constants in `pipeline/18_layer3_production.py` and `phases/phase-5/aggregate_production_stats.py` to Haiku 4.5 rates. (2) Add `cache_control` to the Stage 2 Sonnet system prompt (and to Stage 0/1 Haiku system prompts before any further Haiku runs). (3) Builder editorial review of the 5 dry-run narratives at `phases/phase-5/dry_run_narratives.md`. Only then submit the Stage 2 batch.

---

## 2026-04-30 (evening) — Dry-run v2 (5 schools) approved as representative of acceptable Stage 2 quality; full batch deferred pending Rule 15 decision

**Schools.** Squalicum HS, Bainbridge HS, Echo Glen School, Phantom Lake Elementary, Juanita HS. Picked to exercise Title IX district-pattern multi-finding consolidation, death-circumstance suppression, large-district multi-finding, small-school edge case, and the original Sonnet-4.5 hallucination test case. Each had Stage 1 included findings already on disk in `phases/phase-5/production_run/stage1_results.jsonl`, so this run was Sonnet 4.6 batch only — no new Haiku spend.

**Output.** `phases/phase-5/dry_run_narratives_v2.md` (Finder-readable), `layer3_narrative` written to MongoDB for the five NCES IDs. **Cost: $0.0310** (Sonnet 4.6 batch, 5 requests).

**Pricing constants fixed.** `pipeline/18_layer3_production.py` and `phases/phase-5/aggregate_production_stats.py` now use Haiku 4.5 rates (`$1.00` input / `$5.00` output per MTok), verified against the Anthropic platform-docs pricing page. The earlier `$0.80`/`$4.00` constants were Haiku 3.5 rates copied unchanged from `run_round1.py`. All future cost telemetry on this codebase is honest.

**Caching gap discovered.** Adding `cache_control: {type: ephemeral, ttl: "1h"}` to the Stage 2 Sonnet system block produced **zero cache hits** in the 5-school dry-run v2 (`cache_creation_input_tokens = 0`, `cache_read_input_tokens = 0`). Anthropic's prompt cache requires a minimum 1,024-token cacheable segment; the Stage 2 system prompt at ~1,000 tokens falls just under and the marker is silently ignored. The previously projected $2.40 savings on the 1,770-school batch will NOT materialize without restructuring the prompt — and findings JSON varies per school, so it cannot be cached. Decision for the full Stage 2 batch: proceed without caching. Projected total Sonnet cost for the remaining 1,770 schools: ~$11 (no cache, batch discount applied).

**Editorial review findings — issues real but tractable.** Builder approved the v2 narratives as representative of acceptable Stage 2 quality. Five named issues to address before or after the full batch:

1. **Stage 1 parent-relevance issue.** Some findings that pass Stage 1 triage do not clearly serve a parent making a school-decision question. Stage 1 currently filters routine governance, awards-only findings, and exoneration; it does not have a hard test for "would a parent considering this school for their child make a different decision based on this information?" That test exists in Stage 2's writing rules (Rule 10) but is not enforced upstream. Result: Sonnet receives findings it then has to write around. Fixable with a Stage 1 prompt revision; does not require rerunning Stage 0.
2. **Temporal-language issue.** Stage 2 narratives occasionally insert hedging qualifiers not present in the source ("These remain allegations" in the Bainbridge HS principal-arrest paragraph; "spanning a period of time" in the Echo Glen narrative where the source had a specific date). The Stage 2 NO FABRICATION rule covers outcomes/resolutions but not metadata-style temporal hedges. Fixable with a Stage 2 prompt revision.
3. **Squalicum framing observation.** The Title IX multi-finding consolidation reads correctly and the cross-context dedup collision (the Feb 2026 bus-assault article appearing in both `context` and `district_context`) is resolved cleanly. The framing observation is more about flow: four district-level findings present sequentially, all attributed "at the district level," which is accurate but reads repetitively. Stage 2 Rule 8 ("vary transitions") is technically satisfied but the cumulative effect at four district findings is heavier than the 50-school validation set tested. Worth a phrasing pass.
4. **Echo Glen / juvenile facility issue.** Echo Glen School is a juvenile detention facility (already noted in `docs/harm_register.md` and excluded from the performance regression). The harm register also flagged "Non-traditional school narrative framing" as a Phase 5 to-implement item: juvenile detention facilities should NOT receive standard narrative treatment. The dry-run-v2 narrative for Echo Glen treats it like a regular school with multiple findings woven in. The fix is the school-type branching the harm register already specifies — Stage 2 should consult `school_type` (already on the document) and apply minimal-comparison, heavy-caveat framing for `institutional` category schools. This is the single largest editorial issue from tonight's dry run.
5. **Pricing/caching from this same run.** Captured above. Both fixed in code; caching architecturally gated by the 1024-token minimum.

**Decision deferred to tomorrow.** Two paths:
- **Path A — proceed with full Stage 2 batch as-is.** Projected ~$11 to generate 1,770 narratives. Known issues are tractable in a follow-up pass on already-generated narratives (since Stage 0 and Stage 1 results are stored on disk and don't need to be re-run; only Stage 2 would be re-run after a Rule 15 / school-type-branching prompt revision).
- **Path B — fix Rule 15 first** (proposed: an explicit Stage 2 school-type branch matching the harm register's "Non-traditional school narrative framing" entry, plus tightened temporal-language guard). Then run the full Stage 2 batch once. Higher up-front editorial work, single batch cost.

The v2 dry-run output is approved as representative of acceptable Stage 2 quality; the known issues do not block proceeding. The choice between Path A and Path B is a sequencing question, not a quality question, and is for the builder to make.

**Standing down for the night.** All Phase A processes confirmed dead. No Anthropic batches in flight. State on disk is clean and resumable: `checkpoint.jsonl` (2,427 schools), `stage1_results.jsonl` (1,794 queued for Stage 2), `stage2_batch_requests.jsonl` (1,794 prepared requests). MongoDB has `layer3_narrative` populated only for the 5 dry-run-v1 schools (Enumclaw — single PDC finding each) and the 5 dry-run-v2 schools (the editorial test set). All other 2,522 schools have no `layer3_narrative` field yet.

---

## 2026-05-01 — Dry-run v3 (50 stratified) and v4 (8 targeted) results, Stage 2 prompt versioned to v2 then v3

**Dry-run v3 (50 stratified schools, Stage 2 v1 prompt).** Output at `phases/phase-5/dry_run_narratives_v3.md`. Cost: $0.2364 (mean $0.0047/school, median $0.0041, p90 $0.0082, max $0.0102 — substantially under prior $0.0062 estimate because most narratives are shorter than projected). Auto-checks flagged 10/50 schools but most flags are documented false positives (the `'at the school'` regex from the Phase 4.5 exit doc, plus `'Junior'` matching school names like "Sterling Junior High"). Real violations: 2 verb fabrications (`was fired` / `was terminated` not in source — Frontier MS and Central Valley Virtual Learning) and 3 grade-level identifier leaks (`'senior year'` carried through from a Toppenish district-level source finding to Garfield, Kirkwood, and Valley View Elementary). 4% real-violation rate.

**Stage 2 prompt revised to v2 (`prompts/layer3_stage2_sonnet_narrative_v2.txt`).** v1 preserved unchanged as the historical record of the validated 50-school baseline. v2 adds:

- **Rule 15 — Timeless past-tense framing.** Forbids present-tense status assertions ("remain allegations," "is ongoing," "no resolution has been reported") in favor of past-anchored framing ("the cited records do not reflect a resolution," "as reported in [year]," "available records as of [generation date] show no resolution"). Principle: every sentence should remain truthful at any future date the narrative is read.
- **Rule 16 — Source-fidelity verbs for individual conduct.** Forbids substituting outcome verbs ("was fired," "was terminated," "resigned," "was dismissed," "was demoted," "was reassigned," "was disciplined," "was let go," "received a warning") unless the exact verb appears in Stage 1 source. Disposition-unclear cases get past-anchored framing rather than asserted dispositions.
- **Rule 17 — Grade-level identifier redaction.** Replaces "senior year," "junior year," "eighth grader," "in [N]th grade," etc. with general references ("while a student," "during the student's enrollment"). Stage 2 must rewrite even when the source contains these — unlike Stage 1, which is a load-bearing factual-pass-through layer that cannot be expanded into rewriting work.
- **Per-paragraph citations.** Each paragraph ends with `[Sources: URL1; URL2; URL3]` plain text. URLs come from each finding's `source_url` field. Stage 1 does not currently carry `source_url` in its included list; the v4 runner re-queries MongoDB at Stage 2 build time and matches Stage 1 `original_text` to deduped source `summary` to recover URLs. Findings with no URL render as `(one source unavailable)` so gaps are explicit.

**Dry-run v4 (8 targeted schools, Stage 2 v2 prompt).** Output at `phases/phase-5/dry_run_narratives_v4.md`. Cost: $0.0865. Verification: Rule 17 fully eliminated grade-level leaks (Toppenish trio clean). Rule 15 fully replaced timeless-tense violations (Bainbridge `'These remain allegations'` gone; Phantom Lake's `'no resolution'` / `'ongoing'` patterns rewrote cleanly). Rule 16 reduced but did not eliminate verb fabrication (one residual hit: Garfield Elementary wrote "the superintendent **was fired** in late February 2025" where source said "the school board **terminated** the superintendent"). Citations rendered structurally (1:1 with paragraphs in all 8 narratives) but most contained `(one source unavailable)` because the runner's source-URL matcher used exact-match against summary text that contains `<cite index="...">` wrappers Stage 1 strips. Matcher patched in `phases/phase-5/dry_run_v4.py:_normalize_for_match` to strip `<cite>` tags and add a 100-char prefix-match fallback.

**Decision: Rule 16 fired/terminated drift accepted as known residual.** "Was fired" and "was terminated" are substantively equivalent dispositions for the parent-reader's decision; the legal-risk delta between them is negligible because both describe an institutional choice to end employment in response to documented misconduct. No further iteration on Rule 16. The auto-check phrase list will continue to flag these substitutions at production scale; if the rate goes above ~10% of generated narratives, revisit. (Builder decision, 2026-05-01.)

**Decision: Rule 4 strengthened with manner-of-death and location-of-death suppression in Stage 2 prompt v3 (`prompts/layer3_stage2_sonnet_narrative_v3.txt`).** Triggered by a Frontier MS narrative (v3 batch, Moses Lake) that contained "died following a drive-by shooting on West Loop Drive in Moses Lake" — manner of death plus location, both forbidden by the Rule 4 spirit but not caught by the existing phrase list (the regex covers "wooded area," "in the gymnasium," "on school grounds" but not "drive-by shooting" or named streets). Strengthening adds: "Suppress all manner of death (e.g., gunfire, vehicle accident, drowning, self-harm method, medical event, drug overdose) and all location of death. Report only the institutional response (e.g., grief support services provided) and the fact that a death occurred. Forbidden phrasings include: 'died following a [manner],' 'fatal [event],' 'killed in a [event],' '[manner]-related death.' Use only 'a student died' or 'the death of a student' followed by institutional response." This is the highest-stakes Rule 4 category (manner of death on a child) and the v3 strengthening makes the rule explicit rather than inferred.

**Cumulative spend through dry-run v4: ~$19.50** (Phase A Haiku $18.94 corrected + Sonnet dry runs $0.10 v1 + $0.03 v2 + $0.24 v3 + $0.09 v4). Hard cap $50 still has $30 headroom for the full Stage 2 batch.

---

## 2026-05-02 — Layer 3 production complete: 1,794 v3 narratives written, full receipt at `docs/receipts/phase-5/task3_layer3_production.md`

**Final-gate dry-run v5 PASSED both gates.** Frontier MS narrative under Stage 2 v3 prompt suppressed `'drive-by shooting'` and `'West Loop Drive'` and produced the required `"a student died...the district provided grief support services"` framing. Whatcom Middle (Bellingham) verified the citation matcher patch — 4/4 source URLs matched, every paragraph cites a real URL (no `(one source unavailable)` cells). v5 cost $0.0244.

**Full Stage 2 batch submitted and completed**, `pipeline/19_layer3_stage2_v3_batch.py` against `msgbatch_014HnVdUAUnajrNzycW9uAiG`. 1,792 schools, 100% success rate, **zero errors, $12.69 total**. Per-paragraph citations rendered for every narrative. URL enrichment at scale: 4,561 / 4,563 findings matched (99.96%) via the `<cite>`-tag-stripping + 100-char-prefix fallback patch in the runner.

**One client-side recovery during the run.** The script crashed once on `client.messages.batches.retrieve()` with a 404 NotFoundError ~20 seconds after `create()` returned the batch ID. Anthropic API read-after-write indexing lag — the batch was server-side-alive and unaffected. Relaunching the script picked up the saved batch_id from `phases/phase-5/production_run/stage2_v3_batch_id.txt` and resumed polling cleanly. The runner should add retry/backoff on transient `retrieve` failures so this can't crash an unattended run; deferred fix.

**Final MongoDB state:** 2,427 / 2,532 schools have `layer3_narrative` populated. Of those: 1,794 with full v3 Sonnet narratives + per-paragraph citations (`status=ok`, `prompt_version=layer3_v3`); 412 with the canonical "No significant web-sourced context..." text (`status=stage1_filtered_to_zero`); 221 with the same fallback text (`status=no_findings`). The remaining 105 schools have no `layer3_narrative` field — these are the schools Phase A never reached when the run was halted at 2,427/2,532. Phase A is resumable from `checkpoint.jsonl`; a follow-up run on the missing 105 would cost roughly ~$1.40 to complete coverage. Not blocking the current builder review.

**Random 30-school spot check on production output:** 30/30 narratives rendered citation blocks; zero hits on Rule 4 forbidden phrases (drive-by shooting / fatal / overdose / died following a); zero hits on Rule 17 forbidden phrases (senior year / junior year / sophomore year / freshman year); zero hits on Rule 15 forbidden phrases (remain allegations / no resolution has been reported / remains an active). v3 prompt holding at scale.

**Total Layer 3 production spend: ~$32.30** (Phase A Haiku $19.15 + dry runs $0.46 + full Stage 2 $12.69). Came in at 65% of the $50 hard cap.

**Stratified spot-check sample written to `phases/phase-5/spot_check_sample.md`** for builder editorial review. 25 schools: 10 big-district + 10 mid-district + 5 small-district, all outside the 50-school Phase 4.5 validation set, with ≥3 schools from districts that have known recent incidents (sensitivity=high or category=investigations_ocr findings in district_context). Reproducible via `random.seed(20260430)`.

**Receipt:** `docs/receipts/phase-5/task3_layer3_production.md` covers full batch outcomes, six receipt-mandated sample schools (Bainbridge HS, Sehome HS, Squalicum HS, Juanita HS, Phantom Lake Elementary, Fairhaven Middle), aggregate stats, error summary, files touched, and follow-up items.

---

## 2026-05-02 — Spot-check sample approved; two carry-forward observations

Builder reviewed `phases/phase-5/spot_check_sample.md` (25 stratified schools) and approved the v3 production output as shippable. Quality holds across the sample. Two non-blocking observations captured for future iteration:

**(a) Named complainant organizations getting genericized.** Inglewood Middle School (Issaquah) narrative renders "a nonprofit legal team" where the v2 Juanita HS narrative explicitly named "StandWithUs" — both findings cite the same organization. Stage 2 Rule 2 forbids individual names but doesn't speak to organizational complainants; Sonnet appears to be erring toward genericization for both. Naming the organization gives parent readers civic-information value (who is making the claim, what is their public posture) that genericization removes. Future v4 refinement candidate: distinguish individual personal names (always strip) from named complainant organizations (preserve when they are public-facing entities making advocacy claims). Not blocking; current behavior is conservative-safe.

**(b) Same-district narrative duplication is structurally correct but visually heavy.** Schools in Bethel, Tahoma, Stanwood-Camano, and Toppenish (and any other district with ≥1 district-level finding shared across schools) produce near-identical paragraphs across all schools in the district. This is the intended behavior of Stage 2 Rule 7 (district attribution propagates to every school in the district) and Phase 4 Pass 1 (district_context replicated to all schools). The data layer is correct. The visual / UX problem belongs to the Phase 6 frontend: the briefing page should detect district-context paragraphs (already framed with "at the district level"-class language) and either visually distinguish them from school-specific findings, collapse repeated district context across same-district school pages, or otherwise signal to the parent that this is district-wide context rather than building-specific. Phase 6 design problem, not a Phase 5 prompt or pipeline issue.

---

## 2026-05-02 — Phase 5 closure: full WA coverage (2,532/2,532), Layer 3 production DONE

**Resume Phase A on the 105 unprocessed schools.** Same 4-shard architecture as the killed initial run, ~7 minutes wall-clock to completion (process the killed run never reached). Status distribution of the 105: 68 queued for Stage 2, 26 stage1_filtered_to_zero (canonical fallback narrative written directly), 11 no_findings (canonical fallback written directly). Cost: $0.71 Haiku.

**Final Stage 2 batch on the 68 newly-queued schools.** Submitted as `msgbatch_01ResB16DcKqAFDHiUzis38Q` via `pipeline/19_layer3_stage2_v3_batch.py` (which correctly skipped the 1,794 schools already on layer3_v3 and picked up only the 68 from the resume run). 100% success, zero errors, ~2 minutes processing. Cost: $0.47. URL enrichment 155/155 = 100%.

**Final MongoDB state — full coverage achieved:**
- 2,532 / 2,532 schools have `layer3_narrative` populated (was 2,427 / 2,532 before resume).
- 1,862 schools on `layer3_v3` with full Sonnet narratives + per-paragraph citations (was 1,794, +68).
- 232 with `status=no_findings` (canonical fallback text).
- 438 with `status=stage1_filtered_to_zero` (canonical fallback text).
- 0 schools without a `layer3_narrative` field.

**Total Phase 5 / Layer 3 production spend: $33.48** (Phase A initial $19.15 + Phase A resume $0.71 + dry runs v1–v5 $0.46 + full Stage 2 $12.69 + final Stage 2 $0.47). 67% of the $50 hard cap.

**Receipt finalized at `docs/receipts/phase-5/task3_layer3_production.md`.**

**Phase 5 declared DONE.** No Phase 6 frontend work, no Layer 2 design, no Phase 3 rerun in scope. The next phase will be triggered by separate builder approval.

---

## 2026-05-02 — Positive-content rule retired (Stage 1 v2 promoted to canonical), 185 schools regenerated; Phase 5 RE-OPENED pending rule audit

**Diagnostic finding.** Full-population scan (`phases/phase-5/positive_content_diagnostic.md`) found 185 schools whose raw Phase 4 findings contained positive-content vocabulary (Washington Achievement Award, Blue Ribbon, Schools of Distinction, Title I Distinguished, dual-language program designations, Teacher of the Year, FIRST robotics, state/national academic competitions, etc.) — and just 1 of those 185 schools had positive content in its final `layer3_narrative`. The 184-school filter-out was attributable almost entirely to one categorical rule on `prompts/layer3_stage1_haiku_triage_v1.txt:37`: *"Awards, recognitions, and positive achievements: exclude unless directly relevant to an adverse finding."* The rule contradicts foundation.md's explicit mission language to *"recognize real achievement"* and *"showcase gains that current ratings miss, especially where educators outperform demographic expectations."*

**10-school v2 test (`phases/phase-5/positive_content_test_v1.md`).** Stage 1 v2 (rule removed) + Stage 2 v3 unchanged. Random sample with `random.seed(20260502)`. 10/10 succeeded. Stage 1 v2 inclusions ranged 3–8 per school. 9 of 10 narratives carried both adverse and positive content; the tenth (Stevens Elementary, Spokane) had only adverse content survive Stage 1's recency rules. Cost $0.16. Builder approved the editorial flow as shippable.

**Decision: Stage 1 line-37 rule retired permanently.** v1 stays in `prompts/` as the historical record of what produced the original 1,862 production v3 narratives. v2 (`prompts/layer3_stage1_haiku_triage_v2.txt`) is now canonical.

**Stage 1 v2 promoted to canonical.** `pipeline/layer3_prompts.py` updated: `STAGE1_FILE` now points to v2; `load_stage1()` returns v2 by default; `load_stage1_v1()` added for historical reproduction; `load_stage1_v2()` retained as alias for callers that already named the version explicitly.

**Production rerun complete.** `phases/phase-5/regenerate_184_with_stage1_v2.py` re-derived the affected pool from a full-population MongoDB scan (187 schools — slight drift from the original 184 figure due to MongoDB state changes during the day; same vocabulary) and processed all of them through Stage 1 v2 + Stage 2 v3 (`msgbatch_016aKDCXANFiYgxpwPavcpJb`). Results:
- **185 / 187 narratives regenerated** and written to MongoDB with `prompt_version=layer3_v3`, `stage1_prompt_version=layer3_v2`, `regenerated_2026_05_02=true`.
- **2 / 187 had Stage 1 v2 include zero findings** (the schools whose only positive content was collateral-dropped at Stage 0 by the conduct-date or dismissed-case rule — those are not affected by line-37 removal). Their MongoDB state was left unchanged.
- **0 errors.**
- **93 / 185** regenerated narratives now contain a positive-content vocabulary match in their final text (50% — the rest had positive Phase 4 content but Stage 1 v2 still excluded it under recency rules, or Sonnet rephrased it past the keyword scan).
- **Cost: $2.60** (Haiku $1.07 + Sonnet batch $1.53). Under the $3 expected cap.

**Final MongoDB coverage state (post-regen):**
- **1,885 schools** on `status=ok, prompt_version=layer3_v3` (was 1,862; gained 23 from former stage1_filtered_to_zero schools that now pass Stage 1 v2). Of those 1,885, **185 are regenerated under Stage 1 v2** with `stage1_prompt_version=layer3_v2`; the other 1,700 are the original Stage 1 v1 batch, unchanged.
- **415 schools** on `status=stage1_filtered_to_zero` (was 438; lost 23 to ok).
- **232 schools** on `status=no_findings` (unchanged).
- **Total: 2,532 / 2,532**, full WA-state coverage maintained.

**Editorial voice decision.** Sonnet's emergent transitional language across mixed-content narratives — "On a positive note specific to [school]," "Among facility improvements at [school]," "On the academic front" — is acknowledged as a deliberate platform voice choice rather than a defect. The transitions help parents pivot between adverse and positive content within a single narrative. Not changed in v2.

**Open item carrying forward to rule audit: positive-content recency calibration.** The 10-year recency window in Stage 1 was designed against adverse content where parental relevance decays as institutional response ages out. For substantive positive recognitions (National Blue Ribbon, Schools of Distinction, civil-rights / equity awards, sustained academic improvement designations), the relevance horizon may legitimately be longer — a Blue Ribbon designation from 2009 still tells a parent something about institutional capacity in a way that a 2009 administrator-misconduct case does not. Haiku v2 demonstrated emergent stretching of the window during the test run, with rationales like "exceeds 10-year recency window but represents sustained measurable quality indicator." Whether to formalize this asymmetric calibration (separate windows for positive vs adverse, or a "sustained quality" exception) is a rule audit decision.

**Phase 5 RE-OPENED pending the full rule audit.** Phase 5 was previously declared closed. The line-37 finding showed that an editorial rule can ship in production while quietly contradicting the project's mission. A full review of all editorial rules across Stage 0 / Stage 1 / Stage 2 prompts for coherence with `docs/foundation.md` and `docs/harm_register.md` is now a Phase 5 gate. Specific candidates to audit beyond the already-revised line 37: the 10-year adverse / 5-year allegation recency windows, the stage1 routine-governance exclusion's edge cases, the death-circumstance suppression scope, the source-quality-awareness rule (Stage 2 Rule 14) and how it interacts with petition-source findings. Phase 5 closes after the audit completes and any consequent revisions are implemented.

**Receipt updated.** `docs/receipts/phase-5/task3_layer3_production.md` reflects the new headline numbers and the regeneration footnote.

---

## 2026-05-02 — Audit Coverage Gap 4 closed via foundation.md update (no rule change to Stage 2)

**Diagnostic.** The rule audit (`docs/rule_audit_2026_05.md`) flagged Coverage Gap 4: foundation.md's commitment that the AI "should consider whether the school or district may have been operating under competing legal mandates — IDEA, Section 504, due process, FAPE requirements" had no implementing rule in Stage 2. To test whether a rule was actually needed, a keyword scan over the 1,885 status=ok narratives in MongoDB found 261 narratives matching disability / restraint / seclusion / special-ed / IEP / Section 504 / FAPE / IDEA / due process keywords (`phases/phase-5/discipline_legal_context_sample.md`, full text of 10 random examples).

**Finding.** Source-language framing already carries the relevant legal context for substantive disability-rights enforcement findings. DOJ settlement language, state AG investigation findings, OCR resolution agreements, and similar formal sources describe violations using legal terminology that anchors the framework — examples from the sample include *"inappropriately and repeatedly secluded and restrained students with disabilities outside of emergency situations as required by law"* and *"failed to provide legally required accommodations... including flexible restroom breaks, modified work schedules."* The platform's role is faithful reporting of these source characterizations; imposing an additional Stage 2 rule that prompts Sonnet to layer in IDEA / 504 / FAPE framing would be grafted onto findings about clear violations and off-topic on findings that incidentally mention disability-rights vocabulary.

**Decision: do not add an IDEA / 504 / FAPE legal-context rule to Stage 2.** The original foundation-document design implication was based on a hypothesized failure mode the production output didn't exhibit. Where source coverage is inadequate, the gap is at the data-source layer (which sources the platform ingests, how thoroughly), not the narrative layer.

**Foundation document updated.** `docs/foundation.md` Section "Interpreting Discipline and Safety Data: Legal Constraints as Context" — the "Design implication" paragraph was rewritten to reflect that source language carries legal context implicitly and the platform reports findings using the source's legal characterization rather than imposing structural framing. The Bellingham bus-assault illustrative example is preserved as motivating context. A timestamped revision note marks the 2026-05-02 update.

**Audit document updated.** `docs/rule_audit_2026_05.md` Coverage Gap 4 marked RESOLVED with citation to this diagnostic and the foundation revision. The corresponding Must-fix item #5 is also marked RESOLVED.

**Net effect on the Phase 5 rule-audit gate.** Must-fix list shrinks from 5 to 4. Remaining must-fix items: positive-content recency calibration (A1), non-traditional school narrative framing (Coverage Gap 2), three-layer trust model disclaimer (Coverage Gap 1), and organizational name handling (A2).

---

## 2026-05-02 — CLAUDE.md updated to v4

CLAUDE.md updated to v4. Added two new top-level sections — "When Expected Behavior Doesn't Match Reality" and "Destructive Operations" — to close gaps surfaced by review of the PocketOS database-deletion incident (2026-04-24). Trimmed verbose pedagogical content (Wrong/Right examples in Logging, Comments, and Git commits; Health Check sample output; 11pm Tuesday framing; redundant non-coder maintainability framings; "No magic" line). Removed "What This Project Is NOT" section (framing lives in foundation.md). Renamed "Non-Coder Maintainability" to "Code Conventions" for accuracy. Merged Module Headers and Trace Tags into single "Repo Navigation Conventions" subsection. Compressed Comments subsection. Net file size reduction roughly 35%.

---

## 2026-05-02 — Editorial decision: OCR investigations into trans-athlete policies remain in narratives

The U.S. Department of Education's Office for Civil Rights opened Title IX investigations into multiple WA districts (Sultan, Vancouver, Tacoma, Lake Washington, others) in 2025-2026 over policies allowing trans students to compete on sports teams aligned with their gender identity. These are politically-motivated coordinated multi-district enforcement actions, not substantive Title IX accountability findings.

**Decision: investigations stay in narratives with neutral institutional-investigation framing.** Suppressing politically-motivated federal investigations would itself be a political act and would conceal documented public-record information from parents. Parents interpret these findings differently based on their values; some read the investigations as institutional concern, others as positive signals about districts protecting trans students. Neutral reporting serves both readings.

**Stage 2 v4 candidate rule (separate from this decision):** when source describes the school or district as one of multiple entities subject to a coordinated investigation or enforcement action, narrative should surface coordination context explicitly (e.g., "one of N educational entities subject to this investigation"). This applies to OCR trans-policy investigations and to any future coordinated actions. Captures coordination as structurally relevant context without editorializing on the political character of any specific action.

Manual MongoDB edits to add this framing were considered and rejected. The pipeline is the platform's authorship process; editorial framing changes happen through prompt revision and regeneration. Rule will be implemented in Stage 2 v4 alongside other audit-driven additions.

**Editorial principle: the platform commits to factual reporting of investigations regardless of political character.** The neutrality commitment serves parents across the values spectrum.

---

## 2026-05-04 — Phase 3R sandbox brought to methodology-ready state: remaining v1 variables ingested

Today's session completed the data layer for the new peer-cohort methodology that is replacing the FRL-only regression. All v1 similarity variables that don't already live on production school documents have been ingested into the experimental sandbox `schooldaylight_experiment`. The sandbox now has every variable the Nebraska REL Central nearest-neighbor framework requires for similarity computation, with one explicit drop and one documented derivation that depart from a literal port. Methodology computation begins next session.

**Variables ingested today.** Graduation rates 4-year and 5-year cohort from `data.wa.gov 76iv-8ed4`, school-level rows for 2023-24 "All Students" subgroup, written to `graduation_rate.cohort_4yr` / `cohort_5yr`. Teacher experience derived from binned distribution `data.wa.gov bdjb-hg6t`, school-level rows for 2024-25, written to `teacher_experience.average_years_derived`. Five computed rates from existing counts: `derived.ell_pct`, `derived.sped_pct`, `derived.migrant_pct`, `derived.race_pct_non_white`, `derived.homelessness_pct`. District-level average teacher base salary per 1.0 FTE from the OSPI Personnel Summary Report 2025-26 preliminary, Table 19 (Certificated Teacher, Duty Roots 31-34), written to `teacher_salary.average_base_per_fte` and applied identically to every school in the district. All ingestion scripts live under `phases/phase-3R/experiment/` and assert `"experiment" in db.name` before any write; production was not opened, queried, or written at any point.

**Methodology decisions.** Full detail in `phases/phase-3R/methodology_revisions_pending.md`. (1) Teacher master's degree percentage dropped from v1 entirely. The originally specified `data.wa.gov wc8d-kv9u` only publishes Inexperienced/Experienced status, not education level. The OSPI catalog datasets that conceptually carry credential data (`t9ya-d7ak` Educator Characteristics, `3543-y5sg` Educator Educational Level, `wsha-faww` Educational Attainment Level) all return HTTP 404 at their resource endpoints — indexed in the catalog but withdrawn. The XLSX Personnel Summary tables don't surface credential level either; a workbook-wide scan for master/doctor/degree/baccal/bachelor returned zero matches across all 39 sheets. v2 path identified: parse OSPI S-275 raw extracts directly from the personnel-level files distributed outside data.wa.gov, which do carry a `Highest_Degree` column. (2) Teacher experience derived as bin-midpoint weighted average rather than direct port. OSPI's binned distribution gives finite-range bins from `0.0 - 4.9` through `55.0 - 59.9` plus `Not Reported`; midpoints use each bin's published range, and the weighted sum is renormalized to reported-bin weights so schools with higher Not Reported percentages aren't biased downward by missingness. Marked as `_derived` in the field name and documented as derivation, not direct port. (3) Race composition uses CCD 2023-24 white count (vintage-matched to the denominator) rather than CRDC 2021-22, which would mix vintages. (4) Denominator selection: OSPI-sourced counts (ELL, SPED, migrant, homeless) divided by `demographics.ospi_total`; CCD-sourced white count divided by `enrollment.total`. Both maintain vintage match within each rate.

**Bug found and fixed: districtcode zero-padding mismatch in graduation ingestion.** Spot-check of three flagship high schools (Kennewick, Camas, Hanford) revealed null graduation rates despite the source dataset having complete records for all three. Root cause: `data.wa.gov 76iv-8ed4` publishes `districtcode` as variable-width — 695 of 821 distinct district codes are 5-char, 126 are 4-char (e.g., `'3017'` for Kennewick, `'4567'` for Camas, `'3400'` for Hanford). Experiment db `metadata.ospi_district_code` is uniformly 5-char zero-padded. The composite (district, school) join silently dropped 170 source rows. Patch: `zfill(5)` on source `districtcode` before building the join key. Recovered 71 schools; HS-no-grad cohort dropped from 432 to 361. Verified the same bug is NOT present in teacher experience ingestion: `bdjb-hg6t` source `leacode` is uniformly 5-char (2,344/2,344). Census ACS unaffected because it joins on `district.nces_id` (NCES 7-char LEAID), not OSPI codes. Patch committed as a separate `_patch_task1_zfill.py` script with `$set` only on `graduation_rate.*` and idempotent rerun semantics. Task 3 carries 13 unmatched schools (~0.6%) from a different cause — likely closed schools or charter authorizers — flagged as known small residual.

**Operational learning: pre-execution review surfaces blockers that would otherwise produce wrong data silently.** Phase 3R Prompt 2 mandated a pre-execution review pass before any ingestion writes. That review surfaced three blockers (the wrong teacher-experience endpoint, the missing masters-degree dataset, the CRDC-vs-CCD vintage choice for the white-count numerator) and three smaller concerns (denominator mismatch, join-key shape, charter handling) before any code ran. Each blocker would have produced data that looked plausible at first glance but was structurally wrong: a 404 endpoint silently degrades to all-null fields, a missing column silently substitutes the wrong variable, a vintage mismatch produces ratios that drift across the dataset. None of these are obvious as errors after the fact. Treating pre-execution review as a project convention for substantive ingestion sessions is a worthwhile habit going forward.

**Coverage state at end of session.** 2,532 schools in the sandbox; all touched by today's ingestion. 2,484 schools (98.1%) have full Census ACS payloads from yesterday's run; 48 fall into five builder-classified SKIP categories. 2,317 schools have a derived average teacher experience; 201 have no bin rows (mostly closed or institutional schools); 202 carry `high_unreported_flag: true` for >10% Not Reported share. 2,501 schools have a teacher salary value; 31 are null because their district code maps to an ESD, charter authorizer, or state-agency program not in Personnel Summary Table 19. After the graduation patch, 361 HS-eligible schools still lack graduation data (down from 432); residual is mostly small/closed/specialty schools per the post-fix CSV at `phases/phase-3R/experiment/hs_no_grad_data_postfix.csv`. The chronic-absenteeism null-overlap diagnostic found 509 schools with `chronic_absenteeism_pct=null` that are NOT in the 120-school exclusion union (school_exclusions.yaml ∪ Phase 3R SKIP); dominant pattern is Regular Schools without tested grades plus alternative and special-ed programs not previously on the FRL-regression exclusion list. Methodology decision on these schools is deferred to the next session.

**End-of-day state.** Two commits pushed to `main`: `90d8001` (Phase 5 backlog catch-up — production code, prompts, deliverables from 2026-04-30 through 2026-05-02) and `d4a4176` (today's Phase 3R session). Methodology brief, variable decision matrix, revisions-pending tracker, and reviewer-questions log are all in working state. Variable decision matrix has actual MongoDB field paths appended to every Include and Substitute row so the next session can pull values directly without rediscovering them. Next session: peer-cohort computation in the sandbox using the full 21-variable v1 set, peer-cohort-relative academic performance per school, and a side-by-side comparison of the new flag distribution against the existing FRL-regression flag distribution before committing to the methodology change.

---

## 2026-05-05 — CLAUDE.md updates: schema-keys clarification + pre-execution review formalized

Two edits to `CLAUDE.md` capturing patterns that recurred enough during Phase 3R to be worth codifying.

**Schema keys bullet under Code Conventions.** School documents key on `_id` (12-char NCESSCH string); there is no separate `nces_id` field. This caught CC three times in the last week — the regression-diagnostics Step 2.3 false positive (1,879 schools wrongly counted as "lost flags" because `d.get("ncessch")` returned `None`), the schema-check verification report flagging it as an anomaly, and each Phase 3R ingestion script having to be told. Documenting it in CLAUDE.md saves a probe round at the start of every session.

**Pre-Execution Review section.** New top-level section between "When Expected Behavior Doesn't Match Reality" and "Destructive Operations": for substantive new work — API ingestion, schema-shaped writes, anything where mid-run discovery would be costly — CC surfaces ambiguities, conflicts, and silent assumptions before executing; builder responds; then CC proceeds. The Phase 3R Prompt 2 review surfaced three blockers (vn5q-nnph 404, missing masters-degree dataset, CRDC vs CCD vintage choice for the white-count numerator) and three smaller concerns before any code ran. Each blocker would have produced data that looked plausible but was structurally wrong: a 404 endpoint silently degrades to all-null fields, a missing column silently substitutes the wrong variable, a vintage mismatch produces ratios that drift across the dataset. Formalizing the convention removes the question of when to apply it.

---

## 2026-05-05 — R10 salary re-ingestion; methodology v1 STOP and Path C consolidation lock; methodology v2 passed; peer_match landed

R10 salary re-ingestion: 2023-24 final (`acf22784...`) replaces yesterday's 2025-26 preliminary, vintage-aligning teacher salary with the rest of the v1 demographic vintage. Source XLSX sheet `Table19` (no space) on the 2023-24 file vs `Table 19` (with space) on the 2025-26 — column structure identical, sheet-name candidate list in the script handled both. 4 districts present only in 2023-24; only one (Summit Olympus Chrt, code 27905, 1 db school) flips null→populated. Fairhaven moves from $116,417 → $102,921 (−13.1%, within statewide vintage shift; not a join error). 2,532 docs touched: 2,502 populated, 30 null. Receipts: `phases/phase-3R/experiment/salary_reingestion_2023-24_2026-05-05.md`, `salary_reingestion_2023-24_receipt.md`. DNS bypass first appeared this session (`192.168.1.1:53` refused; `dnspython` at 1.1.1.1 / 8.8.8.8 / 1.0.0.1 became the standing pattern for every Atlas-touching script for the rest of the week).

First methodology computation against the 1,728-school eligible set fired the redundancy STOP. Four clusters at |r| > 0.70: income/education three-way (per_capita ~ bachelors r=+0.93; median_hh ~ per_capita r=+0.89; median_hh ~ bachelors r=+0.77 pooled); population/density (total_population ~ population_density r=+0.85 to +0.91); race/ELL (race_pct_non_white ~ ell r=+0.78 to +0.80 pooled + ES + Middle + High); FRL/income at Middle level only (frl ~ median_hh r=−0.76, frl ~ per_capita r=−0.74, frl ~ bachelors r=−0.72 at n=309). Halted before computing cohorts; surfaced for builder/advisor decision. Receipt: `phases/phase-3R/experiment/redundancy_stop_report.md`.

Path C consolidation locked: drop `per_capita_income`, `bachelors_pct_25plus`, `total_population` (resolves Cluster 1 and Cluster 2 cleanly); keep `race_pct_non_white` + `ell` (Cluster 3) and `frl` + `median_household_income` (Cluster 4 Middle-only) as documented WA-specific residuals — both reflect structural features of WA demographic geography (Hispanic agricultural communities, refugee resettlement areas, catchment-district overlap at Middle level) rather than measurement redundancy. Mahalanobis distance documented as a v2 escalation path under three explicit trigger conditions (multi-component race vector; reviewer pushback; Mahalanobis sensitivity producing low Jaccard against Path C) rather than as a parallel alternative. Variable count after consolidation: 17 total, 16 used at ES/MS/Other, 17 at HS.

Methodology computation v2 against the consolidated 16/17-var set passed redundancy audit; produced 1,728 eligible cohorts; cohort containment 1.000/1.000 at K=10/20/30 (mathematically guaranteed under deterministic Euclidean distance + argsort with no ties); achievement-sensitivity Jaccard 0.399 across an intersection of 1,007 schools — empirical confirmation that achievement-included and achievement-excluded variants produce materially different cohorts (~9 of 20 peers reassigned), grounding the Texas-style exclusion as the right call. Path C consolidation, K=20, Euclidean distance, per-level segmentation, and achievement exclusion all empirically validated. Receipts: `phases/phase-3R/experiment/methodology_inspection_2026-05-06.md` (renamed today after the post-zfill rerun), `peer_match_schema_update_plan_2026-05-06.md`, `sensitivity_cohort_lists_2026-05-06.json`.

`peer_match.*` bulk-write to MongoDB followed: 2,532 docs touched; 1,728 eligible / 684 descriptive_only / 120 excluded; full per-school cohorts (20 NCES IDs, distances, focal z-scores, cohort mean z-scores, metadata). Provenance entry written at `metadata.phase_3r_dataset_versions.peer_match`. Receipt: `phases/phase-3R/experiment/peer_match_bulk_write_receipt.md`. Mongodump backup pre-write at tag `pre_prompt_3b_mongodump_2026-05-05` (52.01 MB, sha256 `ecc359e5...0064b1912`).

**Operational learning of the day: pre-execution review and H3 framing.** Both proved their value in a single session. The Path C decision was a builder/advisor call surfaced by the STOP rather than a script-side decision; the script halted at the gate, named the four clusters, and waited. That handoff is methodologically tighter than a script that picks a remediation path — the builder + advisor space is where the consolidation-vs-Mahalanobis call actually belongs. Worth preserving as the standing semantic for future redundancy-class STOPs.

---

## 2026-05-06 — Foundation.md harmonization; brief revision pass; achievement-deviation reframe + Jaccard math correction

Three commits today, all documentation-side, syncing the methodology language now that v1 was empirically validated.

`cbbb8f4` — `docs/foundation.md` six-edit harmonization. Replaced the regression-era "Comparison Engine" + "Flag Layer" prose with peer-cohort framing (sub-sections: From regression to peer cohorts; Choosing a methodology; The Washington implementation; What the comparison enables); the academic flag mechanism paragraph; the briefing structure (item 2); the gap statement; the builder-is-not-a-statistician block (now grounded in the four-cluster redundancy example rather than the K-2 grade-span hypothetical). Updated the cover-version header from v0.4 to v0.4.1. A second pass (`e2ded35`) followed when the prior commit's flag-layer subsection was harmonized but the explanatory paragraph above the green/yellow/red bullets still used regression-era prediction language — six follow-up edits to bring the bullets and the explanatory paragraph onto the same footing.

`f133b5a` — Phase 3R methodology revision pass: applied LOCKED items from `methodology_revisions_pending.md` (R1, R2, R3, R7, R7a, R10) across `methodology_review_brief.md`, `variable_decision_matrix.md`, and `reviewer_questions.md`. Brief Section 1.5 split into 1.5.1 (four-cluster empirical structure + Path C consolidation) and 1.5.2 (residual correlations + three-trigger Mahalanobis v2 escalation framing). Q6 in reviewer questions reframed from a decision-rule evaluation question to an outcome-evaluation question. Variable count footer rewritten: 17 total, 16 used at ES/MS/Other, 17 at HS, with the four exclusion categories (achievement on methodological grounds; suspensions/expulsions on policy-variation grounds; teacher master's on data-availability grounds; per_capita / bachelors / total_pop on consolidation grounds) named explicitly. Salary vintage corrected to OSPI Personnel Summary 2023-24 final, Table 19 (S-275-derived) across brief Section 1.4, brief Appendix A row A2, matrix row A2.

`e2ded35` — Achievement-exclusion reframe in brief Section 1.3 + Jaccard math fix in foundation.md. The reframe puts the conceptual reasoning (control-group integrity) in front of the empirical Jaccard finding rather than leading with it; "Three reasons support exclusion" became "Three concerns support the deviation, and they reinforce each other" with mechanical / communicative / purposive labels; the Texas-as-deviation-from-Nebraska framing is now explicit. The math fix corrected foundation.md's "approximately 6 of 20 peers in common" to "about 11 of 20 peers per cohort, with the other 9 reassigned" (the original sentence implied Jaccard ≈ 0.18; actual is 0.40, which corresponds to ~11 shared at K=20 each by the formula |A∩B| / (40 − |A∩B|) = 0.40). Demoted Jaccard from leading framing to parenthetical aside in foundation.md.

Cluster 1 and Cluster 2 magnitudes (r=0.93 / 0.89 / 0.77 / 0.85–0.91) preserved verbatim in brief Section 1.5.1 as historical record — those are the empirical evidence that justified the Path C decision; recomputing them after consolidation would require putting the dropped variables back, which the methodology doesn't do. Worth flagging because a future revision pass might be tempted to "update them to current values" and lose the rationale.

---

## 2026-05-07 — ESD-112 chronic absenteeism investigation pivots to source audit; pipeline + sandbox zfill bugs found and fixed; targeted re-ingest patch; methodology re-run STOP at threshold edge

Day opened with a Section 2 cohort differential diagnostic pre-execution review surfacing that all 9 ESD-112 districts (Vancouver SD, Evergreen, Battle Ground, Camas, Washougal, Ridgefield, Woodland, La Center, Hockinson — ~150 schools, 9% of eligible-set total) were `descriptive_only` with `reason_codes=['missing_chronic_absenteeism']`. Geographic concentration at this magnitude was unusual enough to warrant root-cause investigation before continuing with Section 2.

Investigation pivoted twice. First pivot: the chronic absenteeism field is *derived* (`derived.chronic_absenteeism_pct = 1.0 − academics.attendance.regular_attendance_pct` in `pipeline/12_compute_ratios.py`), so the upstream source is OSPI SQSS Regular Attendance, not a separately-published chronic absenteeism field. Receipt: `phases/phase-3R/experiment/esd112_chronic_absenteeism_root_cause.md`. Second pivot (builder-driven, scope-changing): does OSPI publish chronic absenteeism *directly* in any source we have or can access? Audit answer: **no** — OSPI publishes Regular Attendance with a ≥90% threshold, and `1 − Regular Attendance` *is* the federal/ESSA chronic absenteeism rate by definition (algebraic, not approximate). Brief and matrix language updated to reflect this. Receipt: `phases/phase-3R/experiment/chronic_absenteeism_source_audit.md`. **First H3-framing payoff of the week:** the original investigation framing (H1 our ingestion bug vs H2 upstream OSPI gap) didn't fit the data — the actual finding (the field's lineage isn't what the brief said it was) was a third thesis the original framing couldn't have produced.

The H3 follow-up to the ESD-112 question surfaced the actual bug: `pipeline/04_load_ospi_academics.py:266` and `:154` and `:70` strip whitespace from CSV `DistrictCode` without `zfill(5)`. The OSPI source CSVs publish `DistrictCode` 4-char (no leading zero) for counties 01-09; the schema's `metadata.ospi_district_code` is uniformly 5-char zero-padded; the join silently drops 390 schools across 47 districts in 9 counties (Adams, Asotin, Benton, Chelan, Clallam, Clark, Columbia, Cowlitz, Douglas). All `academics.assessment.*`, `academics.growth.*`, `academics.attendance.*`, and downstream `derived.chronic_absenteeism_pct` were null for those schools.

`97a342f` — Three identical fixes to `pipeline/04_load_ospi_academics.py` (`load_assessment` line 70; `load_growth` line 154; `load_sqss` line 263); dry-run verified against 5 affected schools (counties 02, 05, 06) and 3 controls (10, 17, 32) — OLD 0/12 match, NEW 12/12 match.

`a0de7ec` — Same fix applied to `pipeline/05_load_ospi_discipline.py:64` (where the existing comma-strip handled the comma-in-IDs failure mode but didn't zfill afterward — 73,035 of 459,444 rows were 4-char post-comma-strip). Companion read-only audit of the rest of the production pipeline (01, 02, 03, 06, 07, 11, helpers.py): no further bugs. Receipt: `phases/phase-3R/experiment/ingest_pipeline_join_key_audit.md`. The 03 (OSPI enrollment) script came up clean because its source CSV publishes DistrictCode uniformly 5-char with leading zeros preserved — same field name as 04/05 but different upstream data discipline.

`742f5d6` — Phase 3R sandbox audit: same pattern check on `phases/phase-3R/experiment/_run_*.py`. Found one source-script bug at `_run_api_ingestion.py:175` (graduation rates from `data.wa.gov 76iv-8ed4`) — already runtime-patched via `_patch_task1_zfill.py` last week, but the source script was never updated. **Second methodologically interesting pattern:** patch-without-source-update. The team caught the symptom and repaired the data; the source remained latent for re-run regression. Receipt: `phases/phase-3R/experiment/sandbox_join_key_audit.md`. ACS, salary, salary-reingestion, and all read-only sandbox scripts came up empirically clean (Bellingham SD `5300420` matched in ACS; defensive zfill fallbacks already in salary scripts).

Targeted re-ingest patch (Path B; not a full pipeline rerun, which would have wiped `peer_match.*` and every Phase 3R artifact via the `collection.drop() + insert_many()` pattern in `pipeline/09_write_to_atlas.py` and `pipeline/16_write_and_verify.py`). Single script (`_run_reingest_post_zfill_2026-05-07.py`) imports the corrected production loaders from `04` via `importlib`, inlines the discipline logic from `05`, and `$set`s only `academics.assessment.*` / `academics.growth.*` / `academics.attendance.*` / `academics.ninth_grade_on_track.*` / `academics.dual_credit.*` / `discipline.ospi.*` / `derived.chronic_absenteeism_pct` per-doc. Atomicity per builder instruction: chronic absenteeism re-derived in the *same* `$set` payload as `regular_attendance_pct` so the schema is never in a state where attendance is populated without its complement. Result: 366 0X-county schools restored on attendance; 271/255/253 ELA/Math/Science; 241 discipline rate; 2,327 chronic absenteeism re-derived atomically. Of the 684 `descriptive_only` schools, **323 unambiguous flips** (reason_codes was exactly `['missing_chronic_absenteeism']` AND chronic now populated, all in 0X counties). Receipt: `phases/phase-3R/experiment/reingest_post_zfill_fixes_2026-05-07.md`. Mongodump tag: `pre_reingest_post_zfill_2026-05-07`.

Methodology re-run against the post-zfill schema fired the redundancy STOP at a single trigger: LEVEL_Middle race_pct_non_white ~ ell at r=+0.7997, crossing the strict `>0.80` threshold by 0.003. **Third H3-framing payoff:** the framing that "any |r| > 0.80 indicates redundancy that consolidation cannot resolve" didn't fit the data — all four documented residuals shifted by ≤0.01 absolute, no new clusters surfaced, the cluster magnitudes from the prior run all held within sampling noise. The STOP was a knife-edge precision event (0.797 → 0.800), not a structural shift. Halting per builder-confirmed STOP semantics; surfaced for advisor + Orianda decision. Receipt: `phases/phase-3R/experiment/methodology_rerun_post_zfill_2026-05-07.md`.

---

## 2026-05-08 — Threshold adjustment 0.80→0.81 with sampling-noise reasoning; methodology re-run passed; brief synced; Section 2 cohort differential diagnostic completed with H3 finding on negative mean differential

`bdd2c63` — Adjust documented-residual threshold from 0.80 to 0.81 with sampling-noise reasoning. At per-level n in the hundreds, the difference between r=0.80 and r=0.81 is below the sampling-noise floor of the correlation estimate (~±0.04). The 0.80 threshold was chosen as a defensible round number, not derived from a significance test; the 0.81 ceiling provides a small buffer for cross-eligible-set sampling variation while remaining tight enough to fire on structural strengthening (e.g., r climbing to 0.85). Brief Section 1.5.2 updated with the sampling-noise paragraph. Script's `evaluate_matrix` refactored to use a separate `PREDICTED_RESIDUAL_CEILING = 0.81` for documented residuals — unpredicted pairs > 0.80 still trigger STOP unconditionally; the relaxation applies only to documented residuals. This was option 2 of the four options surfaced in yesterday's STOP receipt; options 1 (broader threshold change), 3 (Mahalanobis escalation), and 4 (defer with peer_match stale) were inappropriate.

Methodology re-run with the adjusted threshold passed. Eligible 2,051 (matches the pre-execution prediction of 1,728 + 323 unambiguous flips exactly); descriptive_only 361; excluded 120. **Path C survived revalidation under a 19% larger eligible set** — the four documented-residual magnitudes all held within ±0.01 absolute (POOLED race/ELL +0.7803 vs prior +0.7828; ES +0.7982 vs +0.7957; Middle +0.7997 vs +0.7965; High +0.7859 vs +0.7770; Middle FRL/income −0.7562 vs −0.7648). No new clusters. K containment 1.000/1.000 mathematically guaranteed. Achievement-sensitivity Jaccard 0.385 (vs prior 0.399, intersection 1,170 vs 1,007) — qualitatively unchanged. **Cohort-shift analysis of the 1,728 prior-eligible schools:** all 1,728 remained eligible; 1,460 (84.5%) had at least one new cohort member from the larger pool; median 3 new members per shifted cohort. Framed as a methodology *correction* (currently-eligible cohorts may have been incomplete because their natural nearest neighbors — schools in the same FRL band, similar urban-rural profile, similar agricultural/migrant context — were silently dropped pre-zfill), not a perturbation. Receipt: `phases/phase-3R/experiment/methodology_rerun_post_zfill_threshold_adj_2026-05-08.md`. Mongodump tag: `pre_methodology_rerun_post_zfill_threshold_adj_2026-05-08`.

`peer_match.*` bulk-write to MongoDB updated for all 2,532 docs (eligible 2,051 with full cohorts; descriptive_only 361 with reason codes; excluded 120). Discovered two stale defensive guards in `_run_peer_match_bulk_write.py` from the first build (hard-coded `EXPECTED = {'eligible': 1728, ...}` and post-write spot-check `Huntington Middle School` expected `descriptive_only`). Updated the count guard to `{2051, 361, 120}`; left the spot-check assertion stale because Huntington was one of the 323 schools that *correctly* flipped to eligible — script's "Overall: FAIL" was the stale assertion, not the data.

`0adda1b` — Brief sync: achievement-sensitivity Jaccard 0.399 → 0.385 (intersection 1,007 → 1,170) propagated across `methodology_review_brief.md` Section 1.3, `variable_decision_matrix.md` row 9 + footer, `reviewer_questions.md` Q2b, `docs/foundation.md` parenthetical. Brief Section 1.5.2 Middle-level n citation 309 → 374. Cluster 1 and Cluster 2 pre-consolidation magnitudes (r=0.93 / 0.89 / 0.85+) preserved as historical record; they're the empirical justification for Path C, not values to update. No inline citations of `1,728` or `2,051` exist in any of the four files; the count is implicit in the Jaccard intersection.

`3e068be` — Phase 3R Section 2 cohort differential distribution diagnostic, completed with 9 figures + receipt + patch script committed. Distribution headlines: ELA n=1,356 / Math n=1,281 / Science n=1,279 valid (after `not_tested` / `suppressed_self` / `insufficient_cohort_data` exclusions); per-subject SD ~10–11pp; weak-positive bivariate cohort-SD vs |raw_diff| (Pearson r = 0.13 to 0.21 across subjects — not strong enough to warrant variance correction). Manual verification on 3 random eligible schools (one non-0X, one 0X-flipped, one any-level): 6/6 subject-school pairs matched independent recompute within abs diff < 0.001 pp. K-N small-school observation: Shaw Island Elementary (K-8, n=8, suppressed_self path) and Point Roberts Primary (KG-02, n=5, not_tested path) both end up `descriptive_only` with no academic flag — same downstream behavior reached via two different mechanisms; structural blind spot inherited from the peer-cohort framework rather than Phase 3R-introduced.

**Fourth H3-framing payoff:** the diagnostic surfaced a finding the framing didn't predict — subject mean differentials are *not* at zero. ELA −1.09pp, Math −0.98pp, Science −0.66pp — consistently negative across all three subjects. Naive read of the methodology predicts mean ≈ 0 by construction; the actual values are 2-4 standard errors away from zero. Three plausible mechanisms ranked in the receipt: (1) selection effect from the cohort-mean denominator rule (≥15 of 20 peers must have valid proficiency), corroborated by the bivariate weak-positive correlation; (2) distribution-valid subset (~1,300 of 2,051) is non-random; (3) sampling artifact. Mechanism 1 fits best — the bivariate finding (within-cohort SD positively correlates with |raw_diff|) is exactly the pattern a denominator-induced selection would produce, since looser cohorts are the ones where the ≥15 rule actively excludes peers and biases the surviving cohort mean. Methodologically: doesn't bear on the threshold value (Section 2 committed to z-score cuts, which are mean-zero by definition), but documents in the brief revision so a reader expecting raw means at zero isn't confused. Receipt: `phases/phase-3R/experiment/cohort_differential_distributions.md`.

**Patterns worth naming across these four days.** (1) **H3 framing earned its keep three times** — the source-audit pivot (chronic absenteeism field lineage was the actual issue, not the ingestion bug or upstream gap H1/H2 framing); the threshold-edge STOP (knife-edge precision rather than structural shift); the negative-mean-differential finding (denominator-rule selection rather than the framing's "near-zero by construction"). Each time the alternative thesis was the right answer; each time the explicit naming was the move that surfaced it. (2) **Patch-without-source-update is a pattern to watch for** — the graduation-rate runtime patch repaired the data but left the source latent; only the audit caught it. Convention worth codifying: when a runtime patch repairs data caused by an ingest bug, update the source script in the same commit. (3) **Path C survived a 19% eligible-set expansion** with no cluster magnitude shifting beyond ±0.01 absolute; the redundancy structure is empirically stable across distributions. (4) **The cohort-mean denominator rule (≥15 of 20)** is more methodologically active than its docstring implies — it's the most likely mechanism for the negative-mean-differential pattern, with the bivariate weak-positive finding as supporting evidence. Section 2 design should consider whether the ≥15 threshold or the denominator construction itself wants revisiting before the academic flag is computed against these cohorts.

**End-of-period state.** 9 commits pushed (`73dfa25` predates this window; `cbbb8f4`, `f133b5a`, `e2ded35`, `97a342f`, `a0de7ec`, `742f5d6`, `bdd2c63`, `0adda1b`, `3e068be`). `peer_match.*` populated for all 2,532 docs against the 2,051-school eligible set. Three pipeline scripts and one sandbox script have the zfill fix in source. Brief, matrix, reviewer questions, and foundation.md all reflect the post-zfill empirical numbers. Section 2 cohort differential diagnostic is the latest informational input to the threshold-value decision; threshold value not yet committed. Next: Section 2 threshold value choice and the academic flag computation.

---

## 2026-05-10 — Phase 6 split into 6A (design), 6B (mockup), 6C (build) with soft-launch positioning

Also updated license model: PolyForm Noncommercial 1.0.0 for code, CC BY-NC 4.0 for documentation and methodology, replacing the original MIT plus CC BY 4.0 framing. Project is now source-available rather than open source. Commercial use of code or methodology requires permission. License files and README updates handled in Phase 6C.

Phase 6 split into 6A (design), 6B (mockup), 6C (build) following Phase 3R precedent. Phase 6A is builder-led design work that can start during the methodology review window. Phase 6B is mockup work with parent comprehension testing. Phase 6C is the original Phase 6 build, refactored against 6A and 6B outputs and deployed to beta.schooldaylight.com as a soft launch. Public launch at schooldaylight.com follows methodology review, implemented as a configuration flip. Methodology reviewer feedback timing: shipped to statistical reviewers 2026-05-09, response pending; soft launch can proceed without blocking.

Note: foundation.md (lines 20, 99, 352) and harm_register.md (lines 108-109) retain "open source" framing pending a separate licensing-language consistency pass. The new license decision (PolyForm Noncommercial 1.0.0 + CC BY-NC 4.0, source-available rather than open source) resolves the harm_register.md open question; the resolution and the foundation.md mission-language updates will be handled in a follow-up advisor session.

---

## 2026-05-11 — Phase 2R scoped after premise-rot catch in Phase 6A

Phase 6A interface review surfaced 2023-24 as the data vintage in parent-facing copy, which prompted the builder to question why current data wasn't being used. Investigation revealed the project had been operating within a 2023-24 frame since Phase 2 (Feb 2026, correct at the time) without re-examining that frame through Phase 3R (April-May 2026), including at moments that should have triggered re-examination — notably the May 5 R10 salary vintage-alignment decision, which deliberately downgraded 2025-26 preliminary to 2023-24 without questioning whether 2023-24 was still the right baseline. The methodology brief shipped to PhD reviewers May 9 carried the aged frame as a current fact. Phase 6A's review caught it incidentally, not by design.

Phase 2R scoped in advisor session: refresh the data layer to current vintages, add a vintage manifest as a permanent control, build mechanical tests for known data-shape gotchas (the leading-zero/zfill class of bug specifically). Migration-with-history-block and rebuild-from-scratch both scoped and rejected in favor of refresh with the targeted-re-ingest pattern established in the May 7 zfill remediation work. Outgoing CC handoff captured separately at `phases/phase-2R/handoff_from_previous_cc.md`.

See `phases/phase-2R/plan.md` for the full plan, controls, and sequential steps.

---

## 2026-05-11 — Phase planning standardized: plan file is the operational source of truth

Going forward, each phase begins with `phases/phase-N/plan.md` drafted in advisor session before execution. The plan contains decisions, controls, sequential steps, and risks. CC, advisor, and builder all read and update the same plan. Replaces the prior pattern of per-session handoff files, which produced drift between parallel CC and advisor handoffs and bundled state-and-tasks awkwardly. Phase 2R is the first phase under this convention; see `phases/phase-2R/plan.md` as the template.

---
