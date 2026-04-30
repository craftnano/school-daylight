# Phase 4 Exit Document — Haiku Context Enrichment

**Date:** 2026-02-23
**Phase:** 4 — AI Layer: Haiku Context Enrichment
**Status:** COMPLETE
**Next:** Phase 4.5 (Sonnet Editorial Rule Testing — unplanned phase added during sensitivity review)

---

## What Was Built

Two-pass Haiku enrichment pipeline with web search. District-level pass finds district-wide context (investigations, lawsuits, leadership, scandals). School-level pass finds school-specific context (news, incidents, awards, programs). Validation call checks each finding for wrong-school contamination, source credibility, and claim support. Results stored as `context` and `district_context` fields on each school's MongoDB document.

### Files Created
- `pipeline/17_haiku_enrichment.py` — Main enrichment script with `--pass district|school` CLI
- `prompts/context_enrichment_v1.txt` — School-level enrichment prompt
- `prompts/context_validation_v1.txt` — School-level validation prompt
- `prompts/district_enrichment_v1.txt` — District-level enrichment prompt
- `prompts/district_validation_v1.txt` — District-level validation prompt
- `data/enrichment_checkpoint.jsonl` — Resume checkpoint
- `phases/phase-4/pilot_report.md` — Pilot results (25 schools)
- `phases/phase-4/sensitivity_review.md` — 442 high-sensitivity findings for human review
- `phases/phase-4/receipt.md` — Verification receipt

---

## Results

### District Pass
- **330 districts** processed
- **751 findings** total
- **All 2,532 schools** now have `district_context` field
- **0 failures**

### School Pass
- **1,185 schools** processed (schools in 32 largest districts — districts with 18+ schools)
- **1,320 findings** total
- **779 schools** enriched with findings (65.7%)
- **406 schools** no findings (34.3%)
- **0 failures**
- Remaining 1,347 schools have district-level context only

### Coverage Decision
School-level enrichment limited to districts with 18+ schools due to API credit exhaustion. All 2,532 schools have district-level context. Schools in smaller districts are less likely to have individual news coverage, and district-level findings cover the most significant issues. This is a defensible scope decision, not a gap.

### Cost
- **Pilot (25 schools):** $0.85
- **Full batch (both passes):** ~$82 total
- **Per-school average:** $0.034
- Model verified as Haiku on every call via `actual_model` field

---

## Sensitivity Review (In Progress)

442 high-sensitivity findings exported to `phases/phase-4/sensitivity_review.md` for builder review. Review is partially complete. Builder reviewed ~70 findings in detail during this session. Key dispositions:

### Findings Removed from MongoDB
1. **Beverly Elementary** (530240000330) — student death (child murdered by relative), no institutional connection
2. **Blaine SD** (530057000130) — board candidate arrested, private citizen with no institutional role
3. **South Pines Elementary** (530111000201) — shooting nearby before dawn, no school connection
4. **Coupeville SD** (530180000289) — superintendent investigated and cleared, exoneration
5. **Liberty Sr High** (530375000576) — student racist video, individual student conduct
6. **Issaquah High School** (530375000574) — fistfight between brothers, routine discipline incident
7. **Everett SD** (530267000391) — dismissed lawsuit about conduct from 2003, dismissed + old
8. **Cashmere SD duplicate** — 610 KONA source removed, Cascade PBS source retained
9. **Six ICE-related student political activity findings** — Auburn HS, Meadowdale MS, Edmonds-Woodway HS, Highline SD/Sylvester MS, Denny MS (false alarm), Aki Kurose MS (shelter-in-place)

### Findings Retained (ICE-related institutional actions)
- **Cowlitz County Youth Services Center** — ended ICE contract for holding undocumented youth (institutional decision)
- **Wahluke SD** — declining enrollment and federal migrant program funding cuts (reframed as budget/enrollment)

### Remaining Review
~370 findings still need review. This work continues in parallel with Phase 4.5 and must complete before Phase 5 production.

---

## Scans Completed

### Death/Suicide Keyword Scan
- **31 matches** found across all findings
- **0 student deaths** slipped through
- Matches were: adult deaths (superintendent, teacher), historical memorials, threat incidents, false positives ("skilled" matching "killed")
- 25 of 31 correctly flagged HIGH sensitivity (80.6%)
- 31 matches retained as Phase 4.5 Sonnet test cases

### ICE/Immigration Scan
- **8 matches** found
- 1 institutional action retained (Cowlitz)
- 1 reframed as budget (Wahluke)
- 6 removed (student political activity, false alarm, reactive shelter-in-place)

### Sexual Violence Scan
- **78 findings** total
- 77 of 78 correctly flagged HIGH sensitivity (98.7%)
- 63 of 78 name individuals (80.8%) — all names to be stripped in Phase 5 output
- 60% from 2023 or later
- Full review pending

---

## Editorial Rules Established (Carry Forward to Phase 5)

These rules emerged from the sensitivity review and are encoded in the Phase 4.5 Sonnet test prompt and test plan.

1. **No individual names in output.** Names retained in source data for pattern detection. Stripped from all parent-facing narrative. No exceptions — includes superintendents, principals, public officials.
2. **No student names ever.** Students referenced by role only. Future "notable alumni" feature would require separate review.
3. **No student death details.** Institutional responses (lawsuits, settlements, investigations) may be surfaced. Manner of death never included. Student never named or identified.
4. **Date-first formatting.** Every finding leads with the year. Unknown dates disclosed as "in an undated report."
5. **Recency policy.** Adverse outcomes: 10-year window. Allegations/dismissals: 5-year window. Pattern exception: 2+ same-type findings within 20-year window all stay.
6. **Exoneration exclusion.** Investigations concluded with no adverse finding are removed entirely.
7. **No institutional connection = exclude.** Geographic proximity is not relevance.
8. **Private citizen exclusion.** Candidates, volunteers, parents, community members with no institutional role are excluded.
9. **Individual student conduct excluded** unless it triggered institutional response (credible threat, lockdown, arrest).
10. **Parent relevance filter.** Procedural governance, board politics, inside-baseball excluded.
11. **Politically sensitive neutrality.** Facts only, no evaluative language, no culture war framing.
12. **Community action at scale.** 500+ signatures with substantive demands may be included, framed as community concern not fact.
13. **Consolidate related findings.** Same saga = one narrative arc.
14. **Source quality awareness.** Weaker sources get appropriate hedging.

---

## Harm Register Updates

The following entries were added or drafted during this phase:

1. **Student deaths excluded from enrichment findings** — with carve-out for institutional accountability responses
2. **Individual names stripped from briefing output only** — names retained in source data for pattern detection
3. **Student names never appear in briefings** — with future notable alumni exception noted

---

## Design Decisions Made

### District-Level Enrichment (Unplanned Addition)
School-level searches missed district-level stories (superintendent scandals, district lawsuits, bond failures). Added a district-level pass as a first pass before school-level enrichment. 330 districts, all 2,532 schools receive district context.

### Washington State Disambiguation Fix
Added "Washington state" to search queries to prevent D.C. contamination. Builder intuition, confirmed as necessary.

### Script Renumber (09 → 17)
Enrichment script numbered as `17_haiku_enrichment.py` to fit pipeline sequence after other scripts added during Phase 3.

### School Coverage Threshold (18+ Schools per District)
School-level enrichment limited to districts with 18+ schools due to credit exhaustion. Decision made during batch run. Defensible: smaller districts' significant findings are captured at district level.

---

## Open Items (Carry Forward)

### Blocks Phase 5 Production
- [ ] Phase 4.5 Sonnet editorial rule testing — all 14 tests must pass
- [ ] Remaining sensitivity review (~370 findings)
- [ ] Phase 3 rerun: absenteeism thresholds (30%/45%) and discipline minimum-N (10→30)
- [ ] Sexual violence findings full review (78 findings)
- [ ] "Other" category findings review and disposition
- [ ] Batch API pricing confirmed and budget approved for Phase 5

### Carry Forward Design Decisions
- [ ] "school_closure" should be promoted from "other" to a standard category
- [ ] Template vs. LLM boundary for Layer 2 (regression interpretation) — may not need per-school Sonnet calls
- [ ] Recency severity override — does a cover-up of attempted rape expire the same as a contract dispute? To be informed by Phase 4.5 test results.
- [ ] License choice before launch — prevent derivative works reducing data to scores/rankings
- [ ] Exoneration scan — CC should search for "cleared," "exonerated," "not sustained," "no finding of wrongdoing" across all findings

### Future Feature Ideas (Parking Lot)
- "Other schools in this district" link on briefing page
- Notable alumni feature (requires its own review)

---

## Human Review Log
- Reviewed pilot report (25 schools): Cost on target, zero failures, Fairhaven finding verified against local knowledge. Approved full batch.
- Reviewed sensitivity export (442 findings): ~70 findings reviewed in detail. 9 removals executed. 14 editorial rules established. Remaining ~370 findings review in progress.
- Reviewed death/suicide scan (31 matches): Zero student deaths in dataset. All matches were adult deaths, memorials, or false positives.
- Reviewed ICE/immigration scan (8 matches): 6 removed, 1 retained as institutional action, 1 reframed.
- Reviewed sexual violence scan (78 findings): Sensitivity flagging 98.7% correct. Full review pending.

---

## Go/No-Go
Phase 4: **GO.** Enrichment pipeline complete. Proceed to Phase 4.5 (Sonnet Editorial Rule Testing).

Phase 4.5 does NOT require Phase 3 rerun. Phase 5 production does.

Sensitivity review is partially complete. Remaining review continues in parallel with Phase 4.5 and must finish before Phase 5 production starts.

**Approved by:** Orianda (builder/project owner)
**Date:** 2026-02-23

---

## Process Lessons

### The sensitivity review is the product design phase
Phase 4 was planned as a technical enrichment step. The sensitivity review turned it into the phase where every editorial rule for the product was established. The findings forced real decisions about what parents see and don't see. This work cannot be skipped or automated.

### Don't let the AI be the last eyes on harm decisions
Advisory chat missed the Beverly Elementary student death during the review walkthrough. Builder caught it. The human review gate is not ceremonial — it's structural.

### Scope expansion can be responsible
Adding district-level enrichment and Phase 4.5 testing were both unplanned. Both made the product better. The discipline is not "stick to the plan" — it's "document why you're deviating and what it costs."

### The hardest findings are the most important to get right
Dead children, sexual abuse, political flashpoints. The temptation is to exclude all of it for safety. The right answer is surgical: exclude what harms, keep what informs, frame what's ambiguous. That takes human judgment, not rules.
