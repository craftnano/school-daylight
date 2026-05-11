# Phase 2R: 2024-25 Data Refresh — Sequential Plan

## What this file is

Plan for refreshing School Daylight from 2023-24 to 2024-25 OSPI vintage. Tracks the sequence, decisions, and controls. Receipts and execution details live in `phases/phase-2R/` alongside this plan.

Phase 2R follows the precedent of Phase 3R: an "R" suffix marks a structural expansion of an original phase. Phase 2R expands Phase 2 (the data layer) with current vintages, a permanent vintage manifest, and mechanical tests for known data-shape gotchas.

Naming and scope settled in advisor planning session on May 11, 2026. The plan integrates handoff knowledge from the outgoing CC session (separately saved as `handoff_from_previous_cc.md`).

## Durable-doc updates (do before opening CC session)

These updates need to land in the project's durable documents before Phase 2R execution begins. The lesson lives in three places — build sequence (structural plan), foundation doc (known risks), build log (chronological record) — each doing a different job.

### build-sequence.md

Add the following note in the phase numbering section, following the existing Phase 6 split note (line 17):

> **Phase 2R note.** Phase 2 has been expanded with Phase 2R (data refresh) following the precedent of Phase 3R. Phase 2R refreshes the data layer from 2023-24 to 2024-25 vintages for OSPI sources, adds a permanent vintage manifest control, and converts known data-shape gotchas into mechanical tests. The phase was added in May 2026 after a case of premise rot was caught during Phase 6A interface review. See `phases/phase-2R/` for plan, controls, and diagnosis.

### foundation.md (known risks section)

Add:

> **Premise rot.** A frame that was correct when established can continue to be operated within after the conditions that made it correct have changed. In February 2026, the Phase 2 pipeline used 2023-24 OSPI data as the current vintage, which was correct at the time. Through Phase 3R (April-May 2026) the project continued operating within that frame even as 2024-25 became available and even at moments that should have triggered re-examination — the May 5 salary R10 decision, for example, deliberately vintage-aligned a 2025-26 preliminary file downward to 2023-24 without questioning whether 2023-24 itself was still the appropriate baseline. The methodology brief shipped to reviewers on May 9 asserted 2023-24 as the most current available cycle, by which point that claim had aged out of accuracy without anyone noticing. The vintage manifest (`docs/vintage_manifest.yaml`) is the permanent control: every external source has a documented current vintage, publication date, refresh cadence, and last-verified date, audited at every phase exit. The discipline isn't catching a single staleness; it's forcing the frame to be re-questioned routinely.

> **LLM confidence-as-evidence.** Confident prose about a domain reads as evidence of careful reasoning. For human-authored writing, this heuristic is usually reliable. For AI-assisted writing, it is not — fluent generation can produce confident-sounding claims that the underlying reasoning does not support. The asymmetric risk is highest for factual claims about external state, which are both the easiest for an LLM to assert with unwarranted confidence and the easiest for a human to verify independently. The fact-check pass on external-facing documents (Control 3 in Phase 2R) is the named control: every claim about external state requires a source URL and a verified-on date, applied as discipline rather than vigilance.

### build_log.md

Add a dated entry for May 11, 2026 recording: a case of premise rot caught during Phase 6A interface review (the parent-facing copy was surfacing 2023-24 as the data vintage, prompting the builder to question why current data wasn't being used); investigation revealed the project had been operating within a 2023-24 frame since Phase 2 (Feb 2026, correct at the time) without re-examining that frame through Phase 3R (April-May 2026) even at moments that should have triggered it (notably the May 5 R10 salary vintage-alignment decision); the methodology brief shipped to PhD reviewers May 9 carried the aged frame as a current fact; the Phase 6A interface review caught it incidentally rather than by design. Scoping of Phase 2R as a data refresh (not migration, not rebuild) settled in advisor session May 11. Outgoing CC handoff captured. Link to `phases/phase-2R/plan.md`.

## Decisions already made

These were settled in the advisor session on May 11, 2026. Don't relitigate without reason.

- **Approach: refresh, not migration or rebuild.** Drop-and-recreate the schools collection against current vintages, per the pipeline's existing idempotent design (CLAUDE.md: "Pipeline is idempotent. Drop and recreate collection on each full load. Safe to run twice"). Refresh is what the architecture was built for. Migration with a history block was scoped and rejected as engineering complexity in service of a feature (cross-vintage comparison in the live schema) that isn't a parent-facing requirement. Clean rebuild was scoped and rejected as introducing more risk than it removed and lacking the speed advantage that would justify the disruption.
- **2023-24 retention: archived, not live.** Before refresh, archive the current database (mongodump + raw 2023-24 source files preserved). 2023-24 is queryable from the archive for research purposes (e.g., the cohort-stability launch analysis) but not present in the live schema.
- **Proficiency definition:** Adopt OSPI's new Levels 2-4 definition. Match what the state publishes. The methodology is definition-agnostic — it operates on whatever proficiency rate OSPI publishes, not on a definition choice. Section 1.12 of the methodology brief is rewritten to acknowledge the definitional shift.
- **Verification breadth:** Fairhaven plus 5-6 additional spot-check schools chosen for diversity (ceiling effects, suppression, multi-source interaction, builder-personal sanity check).
- **Cohort-stability analysis:** Run as launch material, not as a Phase 2R verification step. Happens in a separate analytical environment against the 2023-24 archive and the live 2024-25 data, not as a feature in the production schema.
- **May 15 soft launch:** Gone. Reset after Phase 2R lands and Phase 5 narrative regeneration completes.
- **Reviewer brief update:** Path A. Vintage-corrected v1.1 to Kerry and Ashley by end of week. Methodology unchanged. Diagnostic numbers (bucket distributions, Fairhaven specifics, negative-mean magnitudes) noted as 2023-24 with refresh in progress. v1.2 with refreshed diagnostics follows when Phase 2R completes. Kerry and Ashley were informally notified May 11.
- **Ingestion method:** API preferred for all sources. CC attempts API first. If a source has no API or the API doesn't expose what's needed, CC reports what's needed (URL, filename, expected structure) and stops; builder downloads to a specified directory and CC resumes.

## Controls

The refresh path doesn't require migration-specific controls (parallel-collection protocol, side-by-side diff receipts, definition-comparability receipts). What survives are the controls that close failure modes the existing toolkit leaves open regardless of path. Five controls, plus three updates to existing controls.

Most are permanent infrastructure. The vintage manifest stays forever; the tests stay forever; the brief fact-check pass becomes phase-exit hygiene for any phase that produces external-facing documentation.

### Control 1: Vintage manifest

**What:** `docs/vintage_manifest.yaml` listing every external source. For each entry: name, current vintage in use, publication date of that vintage, source URL, expected refresh cadence, "last verified current" date, who verified.

**When checked:** At every phase exit. If anything is older than its refresh cadence, that's a stop.

**Closes:** Premise rot. The staleness lesson that triggered this phase becomes routine check rather than accidental discovery.

**Priority:** Highest-leverage control on the list. Cheapest to build, prevents the exact failure mode that caused this crisis. Build first.

### Control 2: Backup-restorability check

**What:** Before destructive operations, dump the database. Restore the dump into a sandbox collection. Confirm document count matches. Spot-read Fairhaven. Three-line receipt: dump path plus SHA256, restore document count, golden-school field check.

**Closes:** Silent mongodump failure. Completes-but-not-restorable is a known Atlas SRV failure mode. Also serves as the archive step for 2023-24: the verified dump becomes the durable record of the pre-refresh state.

### Control 3: Fact-check pass on brief claims

**What:** Every claim in the methodology brief about external state (vintages, definitions, sources, refresh cadences, regulatory references) requires a citation: source URL plus last-verified date. Output is a receipt: claim list, citation status (cited / inferred / missing), action taken.

**Closes:** AI-confident-prose halo. Section 1.12's vintage claim was wrong because it was generated as confident prose without verification. Other claims in the May 9 brief currently in reviewers' hands may have the same problem.

**Priority:** Time-sensitive. The May 9 brief is in reviewers' hands now. Fact-check pass on the existing brief should happen before the rewrite — it surfaces whether the rewrite is one-section (just vintage) or larger.

### Control 4: Pipeline target-collection guard

**What:** Pre-flight check before any pipeline script that does `collection.drop()`, `drop_collection()`, or `deleteMany`. Read intended target collection name, refuse to proceed if it matches the live collection without an explicit runtime flag.

**Closes:** Pipeline drop-and-replace risk on the wrong target. The pipeline is designed for drop-and-recreate semantics, but the guard exists for the case where a script is run against the wrong database or with the wrong env vars loaded.

### Control 5: Testing-layer audit and gotcha-to-test conversion

**What:** Convert the outgoing CC's gotcha list into mechanical tests. Each gotcha currently caught by vigilance becomes a deterministic check that fails the ingest. The "Tests to build" section below specifies them. Also resolves CLAUDE.md drift: `tests/run_tests.py` is referenced in CLAUDE.md but doesn't exist — either build it or update CLAUDE.md to match the actual test layout.

**Closes:** Vigilance-doesn't-scale. Every "X bit us in pipelines 04, 05, 09, and a sandbox" pattern in the handoff is evidence that human-level vigilance was the existing control and it failed multiple times across multiple scripts.

**Priority:** High. Tests must be in place before refresh ingest of 2024-25 data, otherwise the same bugs may recur on the new vintage.

## Existing controls to update

- **CLAUDE.md.** Add a "Refresh Safety" section: pipeline target-collection guard (Control 4), backup-restorability requirement before any refresh, vintage manifest as a phase-exit requirement. Resolve the `tests/run_tests.py` reference drift.

- **Receipt template.** Add a top-line vintage manifest cross-reference: "Sources used in this phase, with vintage and publication date." If the vintage manifest hasn't been audited within N days of the phase, that's a stop.

- **Phase exit template.** Add two required sections: (a) fact-check status — claims in any new documentation verified against citation discipline; (b) external-perspective audit — one artifact reviewed through an external reader's lens (parent for interface artifacts, methodology reviewer for brief artifacts). Phase 6A's interface review caught the staleness; this promotes that pattern from accident to requirement.

## Tests to build

The outgoing CC's gotcha list is, in another light, a list of bugs that should have been mechanical tests but weren't. Every "watch for X" is a place where the existing testing layer didn't catch X and a human had to. Each test below pairs with one or more gotchas and converts vigilance into a deterministic check.

The tests go in the existing `tests/` directory. Control 7 (testing-layer audit) resolves whether they wire to a `run_tests.py` entry point or to whatever actually exists.

Tests must be in place before 2024-25 ingest. Otherwise the same bugs recur on the new vintage.

### Test 1: ID dtype check

At every `read_csv` / `read_excel`, assert ID columns are string-typed and length-correct. Cover: `NCESSCH` (12 chars), `ST_SCHID`, `DistrictCode`, `SchoolCode`, `COMBOKEY`, county codes, `LEAID`. Fail on any value that's not a string or that's shorter than expected.

Catches: leading-zero strip. Outgoing CC: bit pipelines 04, 05, 09, and one sandbox script in Phase 3R; 390 schools across 9 counties affected.

### Test 2: Comma-in-IDs check

At Discipline file ingest specifically, assert no ID values contain commas after strip. Fail on any.

Catches: Discipline-only quirk where `SchoolCode` renders as "2,066" rather than 2066. Fairhaven (37501 / 2066) is the test exemplar.

### Test 3: Grade label vocabulary check

Maintain `tests/expected_grade_labels.yaml` per source file. Compare ingested labels against expected. Fail on unrecognized values.

Catches: "All" (Discipline) vs "All Grades" (other OSPI files) silent drift. Also surfaces any new label OSPI introduces without ad-hoc normalization.

### Test 4: Suppression marker vocabulary check

Maintain `tests/expected_suppression_markers.yaml` per source file (`N<10`, `*`, `No Students`, `Top/Bottom Range` for OSPI). At ingest, assert every value that looks like potential suppression matches an expected marker. Fail on unknown.

Catches: new suppression markers OSPI may introduce; also prevents the Growth file's `DATReason="NULL"` (which means "no special reason," not suppression) from being misclassified.

### Test 5: Pipeline target-collection guard

Pre-flight check before any pipeline script that does `collection.drop()`, `drop_collection()`, or `deleteMany`. Read intended target collection name, refuse to proceed if it matches live `schools` unless an explicit `--allow-live` runtime flag is passed.

Catches: pipeline/09 and pipeline/16 silently wiping enriched fields. Outgoing CC: single highest-risk landmine for migration. This test is the mechanical version of Control 3's parallel-collection protocol.

### Test 6: Atlas storage threshold check

After every load, query collection stats, compute percentage of M0 ceiling (512MB) used. Warn at 80%, stop at 95%.

Catches: silent approach to ceiling. The schema change in this phase potentially doubles per-doc weight on the academic block.

### Test 7: Schema invariant tests

Run after every ingest:

- Every document has `_id` as 12-char string; no separate `nces_id` field exists
- Every percentage field is decimal 0.0–1.0 (never raw 0–100)
- Every document has `metadata.dataset_version` and `metadata.load_timestamp` at root
- Suppressed values stored as `null` with `"suppressed": true`, never as zero or empty string

Catches: schema drift on CLAUDE.md-mandated invariants that currently rely on convention rather than enforcement.

### Test 8: FRL source check

Assert FRL ("Low Income") values originate from OSPI source, not CCD. Codified as a source-tag check on the field.

Catches: silent use of unreliable CCD FRL data for WA.

### Test 9: Drift monitor (periodic, not ingest-time)

Different from the rest. Runs on a schedule, not at ingest. Sample a small set of schools and fields. Fetch fresh values from OSPI's published API or files. Compare against MongoDB values. Alert on divergence.

Catches: post-load silent drift (the chronic absenteeism precedent). Operates between releases, not only at release time. Worth scoping carefully — this is the only test that requires standing infrastructure, not just a check at load time. Probably out of scope for this phase's initial test build, but worth specifying now so the design isn't lost.

## Sequential plan

The plan splits into two parts: pre-CC work (advisor and builder, this week) and CC work (new session, after pre-CC work resolves and the vintage manifest is seeded).

### Pre-CC work (advisor and builder)

These run roughly in parallel. Together they produce the artifacts the new CC session needs as input.

#### Step A — Fact-check pass on May 9 brief

Per Control 3. Audit existing claims in the May 9 methodology brief, not just Section 1.12's vintage error. Identify any other external-state claims (S-275 publishing schedule, CRDC status, statutory references, citations) that need correction or qualification. Output is a structured receipt: claim list, citation status (cited / inferred / missing), action taken. Surfaces whether the brief update is one-section (Section 1.12 plus Appendix A citations) or larger.

Done by advisor and builder together. Time-sensitive — gates the brief update.

#### Step B — Methodology brief v1.1 update

Vintage-corrected brief shipped to Kerry and Ashley by end of week (Friday May 15). Section 1.12 rewritten to acknowledge the 2024-25 publication and the L2-4 definitional shift. Section 2.8 vintage line updated. Appendix A vintage citations updated. Diagnostic sections (2.3 bucket distribution, 2.4 negative-mean magnitudes, 2.5 Fairhaven specifics) noted as 2023-24 with refresh in progress; v1.2 with refreshed diagnostics follows when Phase 2R completes.

Drafted by advisor and builder. Fact-check pass from Step A informs scope.

#### Step C — Updates to durable docs

Per the "Durable-doc updates" section at the top of this plan. Build sequence note, foundation doc known-risks entry, build log entry. Done by builder.

### CC work (new session)

Opens after Step A completes and the new CC session is set up with appropriate context (CLAUDE.md, foundation.md, build-sequence.md, this plan, and the outgoing CC handoff).

#### Step 1 — Vintage manifest seed

Per Control 1. New CC's first deliverable. Inventory every external source the project uses: current vintage in production, publication date, source URL, refresh cadence, last verified current, who verified. The outgoing CC's handoff plus the data dictionary supply most of the source list.

The manifest also answers the scope question: which sources are in refresh-scope depends on which show as stale. OSPI assessment, growth, ELL, enrollment, demographics, attendance (within SQSS), discipline — confirmed stale. S-275 personnel, ACS 5-year, teacher experience distribution — status TBD.

#### Step 2 — Baseline mongodump and archive

Dump the current state of the database. This serves two purposes: the standard pre-destructive-operation backup, and the durable archive of 2023-24 for future research use (cohort-stability launch analysis runs against this dump).

Receipt includes: dump file path, file size, SHA256 hash, document count by collection, connection URI structure (without secrets), auth method, Mongo version. Stored outside the project directory plus a copy to cloud storage. Date-stamped filename: `schools_dump_2026-05-XX_pre_phase_2R.archive`.

Raw 2023-24 source files also preserved in `data/archive/2023-24/` with SHA256 hashes if not already so.

#### Step 3 — Backup-restorability check

Per Control 2. Restore the dump into a sandbox collection. Confirm document count matches. Spot-read Fairhaven. Three-line receipt: dump path plus SHA256, restore document count, golden-school field check. Only then proceed.

This is the durable confirmation that the 2023-24 archive is recoverable, not just present on disk.

#### Step 4 — Pre-execution review

CC inspects and reports on the following before touching any pipeline code:

- 2024-25 OSPI Report Card Assessment Data: structure, per-level counts present or absent, column-name changes against existing 2023-24 ingest, suppression marker conventions, school count. Confirms or refutes the outgoing CC's predicted gotchas (leading-zero bug, comma-in-IDs in Discipline, "All" vs "All Grades" label drift, suppression markers, FRL source). Each gotcha gets a binary outcome: confirmed, refuted, or no longer applies.
- Other 2024-25 OSPI files: Growth, English Learner Assessment, Enrollment, Demographics, Attendance (within SQSS), Discipline — confirm publication and structure.
- S-275 Personnel Summary Reports 2024-25: confirm whether published. If yes, refresh-scope. If no, the v1 finance variable continues with 2023-24 data and the vintage manifest documents the lag.
- ACS 5-year estimates: check whether 2020-2024 vintage available. If yes, refresh-scope (every cohort assignment shifts). If no, continue with 2019-2023.
- Teacher Experience Distribution: check whether 2025-26 vintage available.
- Drift check: compare live 2023-24 values in MongoDB to OSPI's published 2023-24 numbers for a sample of fields and schools. Surface any silent drift (chronic absenteeism had a known instance) so it's distinguished from refresh changes downstream.

Output: structured pre-execution review document. Builder reads. Nothing else happens until builder responds.

#### Step 5 — Builder reviews findings

Approve refresh scope (which sources are in, which stay), confirm any code changes needed to handle 2024-25 column shape differences, approve the test list from the "Tests to build" section.

#### Step 6 — Build tests per "Tests to build" section

Per Control 5. Tests 1 through 8 built in `tests/` before refresh ingest begins. Tests run green against the existing 2023-24 data first — if they don't, that surfaces pre-existing bugs separate from the refresh, and those get resolved or documented before the refresh proceeds. Test 9 (drift monitor) deferred to post-launch.

This step also resolves the `tests/run_tests.py` documentation drift.

Output: test inventory document showing each test, what it covers, where it lives, how it runs. Receipt confirms tests run green against existing 2023-24.

#### Step 7 — Pipeline target-collection guard

Per Control 4. Add the pre-flight guard to pipeline scripts that do `collection.drop()`, `drop_collection()`, or `deleteMany`. The guard checks the target collection name against an allowed list and refuses to proceed without an explicit runtime flag for live collections.

This is the mechanical version of "don't drop the wrong collection" — separate from the discipline of not running scripts against production accidentally.

#### Step 8 — Refresh ingest

CC runs the pipeline end-to-end against current vintages. Drop and recreate the schools collection. The pipeline was designed for this; the tests built in Step 6 catch the predicted gotchas at ingest if they recur.

Receipts: SHA256 hashes for all source input files, dataset_version stamp on every document, per-script load summary (rows in, documents written, suppression counts, error counts).

#### Step 9 — Recompute cohorts and academic flags

CC re-runs cohort matching and academic flag computation against refreshed variables. Cohorts may shift; flags may shift; the z-score distribution may shift under the new proficiency definition. This is expected. The receipt makes distribution shifts visible at the cohort level.

#### Step 10 — Verification

Multiple receipts. Each stops and waits for builder review.

- Fairhaven Middle School field-by-field check against expected values (updated for 2024-25 under L2-4).
- 5-6 spot-check schools, named in the CC kickoff prompt. Diverse selection: high-performing suburban (ceiling effects), small rural (suppression), large urban high-ELL (multi-source interaction), one builder-personal sanity check, one or two more.
- Field-level summary of what changed between 2023-24 and 2024-25 for these schools.
- Tests 1 through 8 run green against the refreshed data.

#### Step 11 — Phase 5 narrative regeneration

Batch regenerate the 1,885 existing narratives against refreshed data. Sonnet batch run.

#### Step 12 — Methodology brief v1.2

Builder rewrites diagnostic-bearing sections (2.3, 2.4, 2.5) against refreshed data. Methodology unchanged. Ships to Kerry and Ashley as the promised v1.2 follow-up. Advisor helps with prose.

#### Step 13 — Launch analysis

Cohort-stability findings written up as launch material. Runs in a separate analytical environment against the 2023-24 archive (the verified mongodump) and the live 2024-25 data. Format and venue (LinkedIn essay, Sovereign Ground post, methodology appendix) decided separately.

#### Step 14 — Soft launch

After Phase 5 regeneration completes and launch piece is drafted. New target date set during Phase 2R execution, not now.

## Open questions / parking lot

- ACS 2020-2024 vintage status (resolved by pre-execution review).
- S-275 2024-25 publication status (resolved by pre-execution review).
- Teacher experience 2025-26 vintage status (resolved by pre-execution review).
- Phase 6A coordination during Phase 2R: copy needs to be vintage-neutral or use placeholder tokens. May warrant a pause on 6A work until Phase 2R lands — worth a separate decision.
- Launch venue for cohort-stability analysis: School Daylight methodology appendix, Sovereign Ground post, or LinkedIn essay. Decide closer to launch.
- Retention policy for the 2023-24 mongodump archive: indefinite, defined retention period, or only as long as needed for the launch analysis.

## Risk watch (phase-specific)

- **Premise rot recurrence.** The vintage manifest is the named control. If the manifest gets built but not audited at phase exits, the discipline lapses and the next staleness goes undetected again. Phase 2R receipt should include an explicit "manifest audited at phase exit" line item.
- **Leading-zero regression.** Same pandas bug, same OSPI file shapes, predictable repeat. Test 1 (ID dtype check) is the mechanical hedge. The bug bit four pipeline scripts in Phase 3R; the test prevents recurrence on the new vintage.
- **Cascade rot.** Refresh → recompute cohorts → recompute flags → recompute z-score distribution → regenerate narratives → invalidate cache. Errors compound across steps; a wrong intermediate can produce plausible-looking final output. Tests 1-8 audit intermediate state at each pipeline stage, not just endpoints.
- **Silent transformation across the wider data.** Fairhaven passing is necessary but not sufficient evidence the other 2,531 schools refreshed correctly. The diverse spot-check schools are the hedge. If verification surfaces unexpected patterns, pause before regenerating narratives.
- **Reviewer credibility.** May 9 brief currently has wrong vintage. Fact-check pass (Control 3) is time-sensitive. The v1.1 update going out by Friday is the recovery; the v1.2 follow-up with refreshed diagnostics is the completion.
- **No-code rule under pressure.** If builder finds themselves rubber-stamping receipts they don't fully understand because the alternative is asking CC to redo work again, pause. That's a signal, not just fatigue. The phase has a real deadline (v1.1 brief by Friday) but the data work has no external deadline — don't compress verification to make calendar pressure go away.
- **Coordination across humans.** Pre-execution review and STOP conditions don't reach across the boundary to PhD reviewers. The reviewer reconciliation work is a different mode than the codebase work. Builder judgment is the only governance available for it.
