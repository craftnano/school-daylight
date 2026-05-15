# Phase 2R: 2024-25 Data Refresh — Plan (v2)

## What this file is

Plan for refreshing School Daylight's data layer to current vintages, aligning with OSPI's current proficiency framing, and consolidating the project's two-database structure into a single operating database. This is v2 of the Phase 2R plan, rewritten after a substantive advisor session on 2026-05-13 that materially clarified the scope.

The v1 plan (now archived) was drafted on 2026-05-11 based on assumptions about the database structure, vintage policy, and academic_flag implementation status that the audit conducted on 2026-05-13 either contradicted or refined. Where v1 and v2 conflict, v2 supersedes.

## Why v2

The 2026-05-13 advisor session, supported by a comprehensive read-only audit by a fresh CC session, surfaced several findings that reshaped Phase 2R:

- **Operational database is `schooldaylight_experiment`, not `schooldaylight`.** Phase 3R wrote its outputs to the experiment database as a defensive isolation pattern. That database has been the operating data layer ever since. The historical `schooldaylight` carries Phase 2's February 2026 baseline plus Phase 5 narratives, but none of the Phase 3R additions (peer_match, refreshed teacher experience, R10 salary, derived demographic rates, census_acs).
- **The vintage staleness was a policy artifact, not just a data lag.** Phase 3R operated under an implicit "vintage alignment" policy that prioritized statistical-reviewer convention over user-currency needs. That policy was never explicitly endorsed; it accumulated through individually-defensible decisions (notably R10 on 2026-05-05). The corrected policy: use most recent published data per variable, with explicit status disclosure where preliminary.
- **R10 (the 2026-05-05 salary vintage-alignment decision) is reversed under the new policy.** OSPI S-275 2024-25 final has been available since 2025-11-25 (verified by CC on 2026-05-13). Salary refreshes to 2024-25 final, not 2025-26 preliminary, and not 2023-24 final.
- **OSPI publicly adopted L2-L4 ("foundational grade-level knowledge") framing on 2024-09-10**, following a Smarter Balanced vendor clarification. The project has been using L3+L4 ("consistent grade-level knowledge") for ~20 months, diverging from OSPI's public framing. Phase 2R adopts L2-L4 to align with the state's current public characterization.
- **academic_flag is designed but NOT computed.** The Phase 3R Section 2 methodology specified the cohort-based flag, the cohort statistics were computed and written to MongoDB as `peer_match` blocks, but the flag computation itself was never written. No script computes academic_flag values; no documents carry the field. Phase 2R does not implement academic_flag — that work belongs to a successor phase.

## Scope (Option 1, locked)

Phase 2R does these things, and only these things:

1. **Refresh the data sources to current vintages.** Seven sources, each documented below.
2. **Switch the assessment loader to L2-L4 (foundational grade-level knowledge) column.** One-line column change in the assessment loader.
3. **Re-run the existing cohort statistics computation** against refreshed data and the L2-L4 definition. Uses `_run_methodology_computation_v2_consolidated.py` as it currently exists; no methodology changes.
4. **Rename `schooldaylight_experiment` → `schooldaylight`.** Archive the old `schooldaylight` as a mongodump for forensic reference, then drop.
5. **Generate `docs/vintage_manifest.yaml`** mechanically from the loaders during ingestion. Documents source URL, vintage label, fetch timestamp, dataset identifier, and filter parameters for every source.

Phase 2R does NOT:
- Implement academic_flag computation. Deferred to successor phase.
- Recalibrate `flag_thresholds.yaml` for the L2-L4 distribution. The existing regression-era thresholds will produce different `performance_flag` values under L2-L4; this is expected and acceptable since `performance_flag` is itself being replaced. Successor phase handles recalibration coordinated with academic_flag implementation.
- Regenerate Phase 5 narratives. Narratives stay held until the methodology phase completes, since narratives should render against academic_flag, not performance_flag, and academic_flag isn't being implemented in Phase 2R.
- Update render-side / parent-facing copy. Phase 6A work resumes after Phase 2R completes.
- Resolve the K=20 cohort-size question or the ≥15 cohort-mean denominator rule. Both are open methodology questions for the successor phase.

## Decisions already made

Settled in advisor sessions on 2026-05-11 and 2026-05-13. Don't relitigate without naming a specific concern.

- **Database consolidation: Option A.** Rename `schooldaylight_experiment` to `schooldaylight`; archive and drop the old `schooldaylight`. Single operating database going forward.
- **Vintage policy: use most recent published data per variable, with explicit status disclosure where preliminary.** Replaces the implicit vintage-alignment policy that emerged during Phase 3R. Vintage alignment is preserved within the similarity vector at the time of cohort computation (a methodological requirement) but does not propagate to per-variable ingestion choices.
- **R10 reversal.** Teacher salary refreshes to OSPI S-275 2024-25 final (available since 2025-11-25). The May 5 vintage-alignment-downgrade to 2023-24 is undone.
- **Proficiency definition: L2-L4 ("foundational grade-level knowledge").** Aligns with OSPI's public framing as of 2024-09-10 and with Smarter Balanced's vendor clarification.
- **CCD enrollment: use the 2024-25 preliminary file already on disk.** NCES `ccd_sch_052_2425_l_1a_073025.csv`. Preliminary status disclosed in provenance metadata per the vintage policy.
- **Ingestion method: API preferred where available.** For sources where SODA endpoints are available (OSPI Enrollment, OSPI Assessment, graduation rate, teacher experience), use the API. For sources without API (CCD preliminary, TIGER Gazetteer), use the file with full provenance stamping.
- **Verification breadth.** Fairhaven Middle School plus 4 spot-check schools used in the audit: Juanita HS (530423000670), Lewis and Clark HS (530927001579), Washington Elementary (530393000610), Thunder Mountain Middle (530000102795). Plus 1-2 additional schools chosen by builder if needed for specific diagnostic coverage.
- **Narratives held.** No regeneration in Phase 2R. The methodology phase will handle narrative regeneration after academic_flag implementation lands.

## Refresh targets and provenance

Seven sources. Each entry includes the current state, the refresh target, the ingestion mechanism, and any open verification items.

### Source 1: NCES Common Core of Data (CCD)

- **Variables fed:** Enrollment (`enrollment.total`), Minority rate (`derived.race_pct_non_white`, derived from CCD white count and total)
- **Current state in production:** 2023-24, pre-aggregated CSV at `data/ccd_wa_membership.csv`
- **Refresh target:** 2024-25 preliminary, from on-disk file `WA-raw/federal/ccd_sch_052_2425_l_1a_073025.csv` (2.3 GB, December 2025 release)
- **Ingestion:** File-based. Substantial loader rewrite required (CC's earlier scope: three calls plus pivot-aggregate). The pre-aggregation logic currently in Phase 1 needs to be rewritten or replaced to produce the equivalent extract from the new file.
- **Provenance status:** Preliminary. Vintage stamp explicitly records preliminary status.
- **Open items:** None. Loader work is in scope; CC drafts the rewrite as part of Phase 2R execution.

### Source 2: OSPI Report Card — Enrollment

- **Variables fed:** FRL rate (`demographics.frl_pct`), Homeless rate (`derived.homelessness_pct`), ELL/LEP rate (`derived.ell_pct`), Migrant rate (`derived.migrant_pct`), SPED rate (`derived.sped_pct`)
- **Current state in production:** 2023-24, CSV file at `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv`
- **Refresh target:** 2024-25 final, SODA endpoint `data.wa.gov/resource/2rwv-gs2e.json`. Last refreshed 2025-06-18.
- **Ingestion:** SODA API. Lightweight loader update (~30 lines per CC: CSV-reader → SODA pager plus 10 column-name string changes).
- **Provenance status:** Final.
- **Open items:** None.

### Source 3: OSPI Report Card — Assessment Data

- **Variables fed:** Proficiency (`academics.assessment.ela_proficiency_pct`, `math_proficiency_pct`, `science_proficiency_pct`), feeds the existing `derived.performance_flag` computation
- **Current state in production:** 2023-24, CSV file. Reads "Percent Consistent Grade Level Knowledge And Above" (L3+L4) column.
- **Refresh target:** 2024-25 via SODA endpoint `data.wa.gov/resource/h5d9-vgwi.json`. Published 2025-09-10.
- **Ingestion:** SODA API. Column read changes from "Percent Consistent Grade Level Knowledge And Above" (L3+L4) to "Percent Foundational Grade-Level Knowledge And Above" (L2-L4).
- **Provenance status:** Final.
- **Open items:** None. The fieldName mismatches CC documented (truncations in newer datasets) are handled by reading by display name where possible.

### Source 4: OSPI Report Card — SQSS (chronic absenteeism / attendance)

- **Variables fed:** Chronic absenteeism rate (`derived.chronic_absenteeism_pct`, derived from `academics.attendance.regular_attendance_pct`)
- **Current state in production:** 2024-25 in experiment, already current per the audit. Historical `schooldaylight` has bug residue (40% of audit sample had null values from un-remediated zfill).
- **Refresh target:** No vintage change needed; data is already current. The database consolidation (Step 4) drops the historical bug residue automatically.
- **Ingestion:** No change.
- **Provenance status:** Final.
- **Open items:** None. Confirm during Phase 2R execution that the rename preserves the current 2024-25 values without regression.

### Source 5: data.wa.gov — Graduation Rate

- **Variables fed:** 4-year graduation rate, HS-only (`graduation_rate.cohort_4yr`)
- **Current state in production:** 2023-24 from SODA endpoint `data.wa.gov/resource/76iv-8ed4.json`
- **Refresh target:** 2024-25 final, SODA endpoint `data.wa.gov/resource/isxb-523t.json`. Published 2026-01-08, 99,634 rows. Per OSPI convention, new vintages get new dataset IDs; `76iv-8ed4` stays at 2023-24 in place.
- **Ingestion:** SODA API. Two string substitutions in `_run_api_ingestion.py`: endpoint URL (`76iv-8ed4` → `isxb-523t`) and filter (`schoolyear=2023-24` → `schoolyear=2024-25`). Column structure identical to 2023-24 dataset; no schema or logic change required.
- **Provenance status:** Final.
- **Open items:** None.

### Source 6: OSPI S-275 Personnel Summary

- **Variables fed:** Average teacher salary, district base per FTE (`teacher_salary.average_base_per_fte`)
- **Current state in production:** 2023-24 final, XLSX file at `phases/phase-3R/ingestion_data/table_15-40_school_district_personnel_summary_profiles_2023-24.xlsx`. Set on 2026-05-05 by R10 (now reversed).
- **Refresh target:** 2024-25 final, XLSX file at `https://ospi.k12.wa.us/sites/default/files/2025-02/table_15-40_school_district_personnel_summary_profiles_2024-25.xlsx`. Published 2025-11-25. Sheet count (39) and column structure match the 2023-24 file at the load-bearing read positions (district code at row[0], base salary at row[5]).
- **Ingestion:** File-based. Lightweight filename and year-stamp update. The minor sheet-name variation between vintages ("Table 19" with space in 2024-25 vs "Table19" without space in 2023-24) is already handled by the existing loader's sheet-name fallback list (`_run_salary_reingestion_2023-24.py` lines 105-107); no code change required for that variation.
- **Provenance status:** Final.
- **Open items:** None.

### Source 7: U.S. Census Bureau

Two sub-sources, both Census-published, both API-sourced.

#### 7a: Census ACS 5-year API

- **Variables fed:** Median household income (`census_acs.median_household_income.value`), Gini index (`census_acs.gini_index.value`), Labor force participation 16+ (`census_acs.labor_force_participation_rate_16plus.value`), Unemployment 16+ (`census_acs.unemployment_rate_16plus.value`), B01003 total population (numerator of population density `census_acs.population_density_per_sq_mile.value`)
- **Current state in production:** ACS 5-year 2019-2023, endpoint `api.census.gov/data/2023/acs/acs5`
- **Refresh target:** ACS 5-year 2020-2024, endpoint `api.census.gov/data/2024/acs/acs5`. Published December 2025.
- **Ingestion:** API. Three string changes in `_run_acs_ingestion.py` (URL, vintage constant, vintage stamp).
- **Provenance status:** Final.
- **Open items:** None. CC confirmed 2020-2024 endpoint live and serving on 2026-05-13.

#### 7b: TIGER Gazetteer

- **Variables fed:** Land area (`census_acs.land_area_sq_miles.value`), ALAND denominator of population density
- **Current state in production:** TIGER 2023 Gazetteer
- **Refresh target:** TIGER 2024 Gazetteer at `www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_unsd_national.zip`. Published 2024-08-30.
- **Ingestion:** File from URL (static zip, no API). One string change in the loader.
- **Provenance status:** Final.
- **Open items:** None.

## Controls

Five controls. The original v1 plan had several controls oriented around migration risk (parallel-collection protocol, side-by-side diff receipts) that are not relevant under Option 1's database rename approach. The surviving controls close failure modes the refresh path itself surfaces.

### Control 1: Vintage manifest

**What:** `docs/vintage_manifest.yaml` generated mechanically by the loaders at each ingestion. One entry per source-dataset combination (probably 7-8 entries given Source 7's two sub-sources and any other splits). Each entry: source name, current vintage in use, publication date, source URL or endpoint, fetch timestamp, expected refresh cadence, last verified current date.

**When checked:** At every phase exit going forward, not just Phase 2R. If anything is older than its refresh cadence, that's a stop.

**Closes:** Premise rot. The staleness lesson that triggered Phase 2R becomes a routine mechanical check rather than accidental discovery.

**Priority:** Highest-leverage control. Build during Phase 2R execution as part of loader work; do not defer.

### Control 2: Backup-restorability check

**What:** Before destructive operations (the rename and drop of historical `schooldaylight`), dump the database. Restore the dump into a sandbox collection. Confirm document count matches. Spot-read Fairhaven. Three-line receipt: dump path plus SHA256, restore document count, golden-school field check.

**Closes:** Silent mongodump failure. Also serves as the archive step for the historical `schooldaylight`: the verified dump becomes the durable forensic record of the pre-Phase-2R state.

### Control 3: Pre-execution review for destructive operations

**What:** The rename and drop are destructive operations. Per CLAUDE.md, they require plain-English proposal and plain-English approval before commands are written. CC drafts a step-by-step proposal covering the dump, the verification, the rename, the drop. Builder reviews and approves before any of it executes.

**Closes:** The wrong database getting modified or dropped. Especially important given the experiment-vs-historical confusion this conversation surfaced — the rename procedure must be unambiguous about which database is being archived versus which is being renamed.

### Control 4: API ingestion provenance convention

**What:** Every API-sourced variable must persist, at ingestion time, in an adjacent `_meta` block: (1) the full API endpoint URL with vintage in the path; (2) the canonical vintage label as a string; (3) the fetch timestamp (ISO 8601 UTC); (4) the source dataset identifier; (5) the filter parameters used in the fetch. The build log entry for any API ingestion records the vintage explicitly.

**Closes:** API-no-cache provenance weakness. With API responses not persisted to disk, in-document provenance is the only verifiable record of what was fetched.

**Status:** Already followed implicitly by Phase 3R's API loaders (teacher experience, Census ACS). Phase 2R formalizes as a convention and applies it consistently to the new loaders.

### Control 5: File ingestion year-from-column assertion

**What:** Where a file-sourced loader expects a specific year, the loader reads the year from the file's own SchoolYear column (or equivalent) when available, and asserts the column value matches the expected year before proceeding. Fall back to filename or in-loader stamp only when the file lacks an internal year column.

**Closes:** Loaders silently stamping the wrong year when a source file changes without a filename change. Surfaces vintage mismatches at ingestion time rather than downstream.

**Status:** New convention introduced by Phase 2R. Applied to all file-sourced loaders updated during this phase.

## Sequential plan

The plan splits into pre-execution verification (completed 2026-05-13), execution (loader updates and runs), and verification (post-execution receipts).

### Pre-execution verification (completed 2026-05-13)

#### Step P1 — Confirm graduation rate 2024-25 availability ✓

CC verified on 2026-05-13. 2024-25 graduation data lives in a new SODA dataset `isxb-523t` (published 2026-01-08, 99,634 rows), not in `76iv-8ed4`. Per OSPI convention, new vintages get new dataset IDs. Column structure identical to 2023-24 dataset. Refresh is two string substitutions in the existing loader. See Source 5 above for refresh target details.

#### Step P2 — Confirm S-275 parallel XLSX URL ✓

CC verified on 2026-05-13. The 2024-25 machine-readable XLSX is published at `https://ospi.k12.wa.us/sites/default/files/2025-02/table_15-40_school_district_personnel_summary_profiles_2024-25.xlsx` (HEAD probe 200, 699,479 bytes, published 2025-11-25). Sheet count (39) and column structure match the 2023-24 file at all load-bearing read positions. Minor sheet-name variation handled by existing loader's fallback list. See Source 6 above for refresh target details.

### Execution

Pre-execution review per Control 3 required before Step E1. CC drafts plan, builder approves.

#### Step E1 — Baseline mongodump

Dump both `schooldaylight` and `schooldaylight_experiment`. Two separate dump files, each with SHA256, document count, connection metadata. Stored outside project directory plus cloud copy.

Filenames: `schooldaylight_2026-05-XX_pre_phase_2R.archive` and `schooldaylight_experiment_2026-05-XX_pre_phase_2R.archive`.

Raw source files for all in-scope vintages preserved in `data/archive/2024-25/` with SHA256.

#### Step E2 — Backup-restorability check

Per Control 2. Restore both dumps into sandbox collections. Confirm document counts. Spot-read Fairhaven in each. Receipt: per-database dump path + SHA256, restore document count, golden-school field check.

#### Step E3 — Update loaders

Per the per-source specifications in the Refresh Targets section above. Loader work in dependency order:

- Census ACS URL update (Source 7a) — three string changes
- TIGER URL update (Source 7b) — one string change
- OSPI Enrollment SODA migration (Source 2) — ~30 lines
- OSPI Assessment SODA migration + L2-L4 column switch (Source 3) — ~30 lines + 1 line
- Graduation rate refresh (Source 5) — two string substitutions
- S-275 refresh (Source 6) — filename and year-stamp update
- CCD preliminary file ingestion (Source 1) — substantial loader rewrite

All loaders write provenance metadata per Control 4 (API-sourced) or Control 5 (file-sourced). All loaders update the vintage manifest entry per Control 1.

#### Step E4 — Run refreshed pipeline

CC runs the pipeline end-to-end against `schooldaylight_experiment` (which is currently the operating database; the rename happens in Step E6). Drop-and-recreate semantics per existing pipeline design.

Receipts: SHA256 hashes for all source input files, dataset_version stamp on every document, per-script load summary (rows in, documents written, suppression counts, error counts).

#### Step E5 — Re-run cohort statistics computation

CC re-runs `_run_methodology_computation_v2_consolidated.py` (or its production-pipeline equivalent if promoted during Phase 2R) against the refreshed data. Outputs new `peer_match` blocks for all eligible schools.

Cohorts may shift because the underlying similarity variables refreshed. This is expected. Receipt shows distribution shifts at the cohort level (how many schools changed cohort, distribution of cohort-mean changes, any schools that newly became eligible or descriptive_only).

#### Step E6 — Database rename

After verification (Step V1) confirms the refreshed `schooldaylight_experiment` is in a good state, execute the rename:

1. Dump the current `schooldaylight` (already done in E1 — this is the verification that the archive is still good)
2. Drop `schooldaylight`
3. Rename `schooldaylight_experiment` → `schooldaylight`
4. Verify the renamed database is accessible under the new name with all expected fields

The rename happens after verification, not before, so the audit and verification work happens against the database under its current name and any issues surface before the rename.

#### Step E7 — Generate vintage manifest

`docs/vintage_manifest.yaml` generated from loader outputs. Committed to repo. Build log entry referencing it.

### Verification

#### Step V1 — Field-level verification

Run before E6 (rename). Multiple receipts:

- Fairhaven Middle School field-by-field check against expected values (updated for 2024-25 under L2-L4). Note: golden school expected values need updating; this is an explicit subtask.
- 4 spot-check schools from the audit: Juanita HS, Lewis and Clark HS, Washington Elementary, Thunder Mountain Middle. Plus 1-2 additional if builder identifies specific diagnostic coverage gaps.
- Field-level diff summary: what changed between pre-refresh state and post-refresh state for each variable across the spot-check schools.
- Cohort assignment diff: which spot-check schools changed cohorts, and why (which similarity variables shifted enough to cause the change).

Each receipt stops and waits for builder review.

#### Step V2 — Post-rename verification

Run after E6 (rename). Confirm:

- Database name resolves to `schooldaylight`; old `schooldaylight_experiment` no longer exists
- Document count matches pre-rename experiment document count
- Fairhaven readable, all expected fields present
- Vintage manifest entries all current

## Open items / parking lot

- Successor methodology phase (working name: Phase 7 per old advisor's framing). Scope: implement academic_flag computation script in `pipeline/`, resolve the K=20 cohort-size question and the ≥15 cohort-mean denominator rule, recalibrate `flag_thresholds.yaml` for L2-L4 distribution, update Fairhaven golden school expected values, deprecate or remove `performance_flag`.
- Phase 6A interface work resumes after Phase 2R completes. The flag rendering language work was unaffected by Phase 2R; can pick up where it was paused.
- Methodology brief v1.1: deferred pending Phase 2R completion. Reviewers (Kerry, Ashley) informally notified to hold. Brief revision will land after Phase 2R with refreshed data and corrected vintage policy framing in one coherent update, rather than as a vintage-only correction pass.
- Architecture overview: parked for execution after Phase 2R per separate planning note (`architecture_overview_parking_note.md`).
- Retention policy for the pre-Phase-2R `schooldaylight` archive: indefinite (default) unless storage cost warrants otherwise. The archive is forensic evidence, not active data.

## Risk watch

- **Refresh-correctness drift.** Refreshing seven sources at once means seven possible places for silent error. The field-level verification (V1) is the hedge, but verification is sampling — it can miss errors that don't surface in the sample. Mitigation: the spot-check school selection deliberately spans levels and regions to maximize coverage diversity.
- **Rename blast radius.** The rename in E6 is destructive (drops the old `schooldaylight`). Pre-execution review (Control 3) and backup-restorability check (Control 2) are the named hedges. The rename is sequenced after verification to ensure issues surface before destruction.
- **L2-L4 distribution shift produces unexpected flag movements.** The existing `performance_flag` regression thresholds in `flag_thresholds.yaml` were calibrated for L3+L4. Under L2-L4 (statewide mean ~75% vs ~50%), the threshold bands won't mean what they did. Phase 2R explicitly accepts this — `performance_flag` is being replaced anyway, so its short-term miscalibration is tolerated. Brief language acknowledges that the flag values will recalibrate in the successor phase.
- **CCD preliminary status drift.** The on-disk NCES file is preliminary; NCES may publish revisions. The vintage manifest tracks the preliminary status explicitly. If a finalized 2024-25 CCD ships before the successor phase, that becomes a refresh trigger.
- **Successor phase scope ambiguity.** Phase 2R defers academic_flag work, but the successor phase isn't fully scoped yet. The parking lot above lists what belongs there; a separate scoping conversation needs to settle the phase's boundaries before it executes.
- **Cross-conversation continuity.** This plan rewrite happened in a single advisor session on 2026-05-13 after several hours of audit and discussion. The reasoning is dense; future sessions reading the plan should consult the build log entry for 2026-05-13 for the underlying analysis if anything in the plan reads as underspecified.

## Audit diagnostic scripts and inventory report

The 2026-05-13 audit produced five Python scripts and one consolidated markdown report, all under `phases/phase-2R/`. All scripts are read-only against MongoDB (zero writes, zero pipeline runs) and use `config.py` for connection URIs (never reading `.env` directly). Each script is self-contained and re-runnable; together they are the empirical basis for the audit findings recorded in the 2026-05-13 build-log entry.

### `_run_orientation_check.py` (122 lines)

First diagnostic in the audit sequence. Connects to both `schooldaylight` and `schooldaylight_experiment` and queries one school document to resolve the database-shape question (which database carries Phase 3R artifacts) before per-variable inventory begins. For the target school it reports presence/absence of `peer_match`, `academic_flag` / `academic_flags`, `derived.flags`, `layer3_narrative`, and `teacher_experience`, plus the literal values of `metadata.dataset_version`, `metadata.load_timestamp`, `metadata.phase_3r_ingestion_timestamp`, and `metadata.phase_3r_dataset_versions`. Console output only. Originally executed against an incorrect NCESSCH from the audit prompt — surfaced the canonical-Fairhaven discrepancy that the next script resolved.

### `_run_fairhaven_id_check.py` (48 lines)

Resolves Fairhaven's canonical NCESSCH against both databases by evidence rather than assumption. Probes both candidate IDs (`530219000370` from the original audit prompt; `530042000104` from `pipeline/helpers.py:FAIRHAVEN_NCESSCH`) and additionally does a name-regex search for `/Fairhaven/i` in both databases. Confirmed `530042000104` is the only Fairhaven Middle School document in either database (OSPI district `37501`, OSPI school `2066`), matching the helpers constant and the api_ingestion validation table. Console output only. Read-only. Wrote the canonical-Fairhaven finding to long-term memory.

### `_run_teacher_exp_inventory.py` (213 lines)

First full audit script. Connects to both databases, queries Fairhaven plus four spot-check schools (Juanita HS / Lewis and Clark HS / Washington Elementary Mead / Thunder Mountain Middle), and produces a side-by-side dump of the literal `teacher_experience` block plus all in-block vintage stamps (`dataset_year`, `source`, `fetch_timestamp`, `unreported_pct`, `high_unreported_flag`) and the document-root `metadata.phase_3r_dataset_versions.teacher_experience` entry. Also re-emits the orientation preamble against the corrected NCESSCH. Console output only. This script was the prototype that established the three-section format (MongoDB / source / pipeline filter) and the side-by-side comparison line before the format was scaled to all 16 remaining variables.

### `_run_full_inventory.py` (859 lines)

Main audit deliverable. Connects to both databases once, queries the same five sample schools, and walks 16 v1 similarity variables (variables 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17 — every v1 variable except teacher_experience, which the dedicated script above covers). For each variable, pulls the literal stored value from both databases, the in-block vintage stamps (e.g., `demographics.year`, `census_acs._meta.vintage`, `graduation_rate.metadata.dataset_year`, `derived.race_pct_non_white_meta.source`, `teacher_salary.metadata.dataset_year`), and the upstream count/denominator pairs where the variable is a derived ratio. Includes an automated non-uniformity check that compares each vintage stamp across the five sampled schools within each database and flags any variable whose stamps disagree. Writes the consolidated report to `phases/phase-2R/inventory_remaining_16.md` (no MongoDB writes). Read-only against MongoDB; the single output file is the only filesystem write.

### `_run_fairhaven_field_probe.py` (64 lines)

Written for the 2026-05-13 academic_flag verification request. Pulls the full Fairhaven document from `schooldaylight_experiment`, enumerates every top-level field, every key under `derived.*`, and the full `peer_match.*` block. Searches for any field named `academic_flag`, `academic_flags`, or `academic_performance_flag` at document root or under `derived`. Console output only. Read-only. Empirically confirmed that no academic_flag-shaped field exists in the operating database, while peer_match (the upstream block the flag would consume) is fully populated with K=20 cohort metadata stamped 2026-05-08T17:26:35Z.

### `inventory_remaining_16.md` (1,498 lines)

The consolidated audit deliverable produced by `_run_full_inventory.py`. Opens with a "Key findings" summary covering the database-shape finding (`schooldaylight` carries only Phase 2 baseline + Phase 5 narratives; all Phase 3R artifacts live in `schooldaylight_experiment`), the one non-uniformity flag found in the five-school sample (Variable 2 chronic absenteeism, two 0X-county schools null in historical / populated in experiment — the May 7 zfill-remediation residue), the vintage-triangulation mismatches per variable, the provenance-pattern classification table (7 of 16 are API-sourced with no on-disk cache), and the bug-residue finding cross-referencing the zfill remediation. Then a variable-by-variable section for each of the 16 variables, with Section A (literal sample values side-by-side in both databases for all five sample schools, including upstream count/denominator context for derived ratios), a per-school vintage-stamps table, a uniformity flag if any vintage stamp differs across the five schools within a database, Section B (source file path with size/mtime or API endpoint URL), Section C (pipeline filter or ingestion-script logic with line references), and a four-row vintage-triangulation table contrasting empirical state in each database against the pipeline-encoded vintage and the documentation-inferred vintage. The document is the empirical record behind every claim in the 2026-05-13 audit-findings build-log entry.
