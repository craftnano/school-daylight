# Phase 2R — Tasks

Checklist derived from `plan.md` "Sequential plan" section. Check off as completed.

For full step descriptions, decisions, and controls, read `plan.md`. This file is the execution checklist.

## Pre-CC work (advisor and builder)

Runs roughly in parallel. Produces the artifacts the new CC session needs as input. Steps A and B time-sensitive — gate the brief update to Kerry and Ashley by end of week.

- [ ] **Step A — Fact-check pass on May 9 brief.** Per Control 3. Audit existing claims (vintage, S-275 publishing schedule, CRDC status, statutory references, citations). Output: structured receipt of claim list, citation status, action taken. Surfaces whether the v1.1 update is one-section or larger.
- [ ] **Step B — Methodology brief v1.1 update.** Vintage-corrected brief to Kerry and Ashley by Friday May 15. Section 1.12 rewrite, Section 2.8 vintage line, Appendix A citations. Diagnostic sections (2.3, 2.4, 2.5) noted as 2023-24 with refresh in progress; v1.2 with refreshed diagnostics follows after Phase 2R completes.
- [x] **Step C — Updates to durable docs.** Build sequence note (Phase 2R note added 2026-05-11), foundation doc known-risks entries (#8 Premise Rot, #9 LLM Confidence-as-Evidence added 2026-05-11), build log entry (2026-05-11 entry added).

## CC work (new session)

Opens after Step A completes and the new CC session is set up with appropriate context (CLAUDE.md, foundation.md, build-sequence.md, this plan, and the outgoing CC handoff at `handoff_from_previous_cc.md`).

- [ ] **Step 1 — Vintage manifest seed.** Per Control 1. New CC's first deliverable. `docs/vintage_manifest.yaml` listing every external source with current vintage, publication date, source URL, refresh cadence, last verified date, who verified. Manifest also answers refresh-scope question.
- [ ] **Step 2 — Baseline mongodump and archive.** Dump the database. Receipt: dump path, file size, SHA256, document count by collection, connection URI structure, auth method, Mongo version. Stored outside project directory plus cloud copy. Filename `schools_dump_2026-05-XX_pre_phase_2R.archive`. Raw 2023-24 source files preserved in `data/archive/2023-24/` with SHA256.
- [ ] **Step 3 — Backup-restorability check.** Per Control 2. Restore dump into sandbox collection. Confirm document count, spot-read Fairhaven. Three-line receipt: dump path + SHA256, restore document count, golden-school field check. Only then proceed.
- [ ] **Step 4 — Pre-execution review.** CC inspects and reports before any pipeline code changes: 2024-25 OSPI Assessment structure + outgoing CC's predicted gotchas (confirm/refute/no longer applies for each); other 2024-25 OSPI files; S-275 2024-25 publication status; ACS 2020-2024 vintage status; teacher experience 2025-26 status; drift check vs live 2023-24 values. Builder reads. Nothing else happens until builder responds.
- [ ] **Step 5 — Builder reviews findings.** Approve refresh scope, confirm any code changes for 2024-25 column shape differences, approve test list.
- [ ] **Step 6 — Build tests per "Tests to build" section.** Per Control 5. Tests 1 through 8 built in `tests/`. Tests run green against existing 2023-24 first. Test 9 (drift monitor) deferred to post-launch. Resolves `tests/run_tests.py` documentation drift. Output: test inventory document + receipt confirming green run against 2023-24.
- [ ] **Step 7 — Pipeline target-collection guard.** Per Control 4. Add pre-flight guard to pipeline scripts doing `collection.drop()`, `drop_collection()`, or `deleteMany`. Refuses to proceed against live `schools` without explicit `--allow-live` flag.
- [ ] **Step 8 — Refresh ingest.** Run pipeline end-to-end against current vintages. Drop and recreate schools collection. Receipts: SHA256 hashes for all source inputs, dataset_version stamp on every document, per-script load summary.
- [ ] **Step 9 — Recompute cohorts and academic flags.** Re-run cohort matching and academic flag computation against refreshed variables. Receipt makes distribution shifts visible at the cohort level.
- [ ] **Step 10 — Verification.** Multiple receipts, each waits for builder review. Fairhaven field-by-field; 5-6 spot-check schools (diverse: ceiling, suppression, multi-source, builder-personal); field-level diff summary 2023-24 vs 2024-25; Tests 1-8 green against refreshed data.
- [ ] **Step 11 — Phase 5 narrative regeneration.** Batch regenerate the 1,885 existing narratives against refreshed data. Sonnet batch run.
- [ ] **Step 12 — Methodology brief v1.2.** Builder rewrites diagnostic sections (2.3, 2.4, 2.5) against refreshed data. Methodology unchanged. Ships to Kerry and Ashley as the promised v1.2 follow-up. Advisor helps with prose.
- [ ] **Step 13 — Launch analysis.** Cohort-stability findings written up as launch material. Runs against 2023-24 archive + live 2024-25. Format and venue decided separately.
- [ ] **Step 14 — Soft launch.** After Phase 5 regeneration and launch piece are done. New target date set during Phase 2R execution.
