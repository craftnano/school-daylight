# Phase 2 Implementation Plan: ETL Pipeline + MongoDB Load

**Approved:** 2026-02-21
**Approved by:** Orianda (builder/project owner)
**Status:** APPROVED — proceed with implementation

---

## Builder Clarifications (incorporated into plan)

1. **Step 06 PPE join**: Verify whether SchoolCode is unique statewide or if DistrictCode is needed to disambiguate. Log any collisions where multiple schools share the same SchoolCode.
2. **Step 04 Growth fallback**: Fall back to 2023-24 ONLY when the school has zero rows in the 2024-25 file. If the school is present in 2024-25 but suppressed, keep the suppressed null — do NOT fall back.
3. **Step 10 Fairhaven values**: All expected values come from `phases/phase-1/fairhaven_test.md` (the Phase 1 verified source of truth), not re-derived from raw files.

---

## Context

Phase 1 is complete and approved. The data dictionary (`data/data_dictionary.yaml`), MongoDB schema (`data/schema.yaml`), crosswalk logic, and suppression rules are all verified. WA-only extracts exist for CCD and CRDC data. OSPI files are read directly (they're already WA-only). MongoDB Atlas is connected and reachable.

This phase builds the pipeline that transforms raw data into MongoDB documents and loads them into Atlas.

---

## Architecture Decision: Intermediate JSON File

Each numbered script reads source data and writes its fields into a shared intermediate file (`data/schools_pipeline.json`). This is a dictionary keyed by NCESSCH.

- Step 01 creates it fresh (guarantees idempotency — every run starts clean)
- Steps 02–08 load it, add their section, save it back
- Step 09 reads the final JSON and pushes all documents to MongoDB Atlas
- Step 10 verifies against the live database and generates the receipt

**Why JSON, not MongoDB updates:** One write to Atlas at the end, not 10 round-trips per school. The intermediate JSON is human-readable — the builder can open it and inspect any school at any stage. Total size ~15 MB for 2,566 schools, fits easily in memory.

**Why not one big script:** Each step is independently debuggable. If step 05 breaks, the builder can fix it and re-run from step 05 without re-reading CCD and CRDC data. The numbered files show the sequence at a glance.

---

## Data Source Routing

| Source | Read from | Why |
|--------|-----------|-----|
| CCD Directory | `data/ccd_wa_directory.csv` | Phase 1 already filtered to WA |
| CCD Membership | `data/ccd_wa_membership.csv` | Phase 1 already aggregated per school |
| CRDC (13 files) | `data/crdc_wa/*.csv` | Phase 1 already filtered to WA |
| OSPI (7 files) | `WA-raw/ospi/*.csv` | No Phase 1 extract needed — files are already WA-only from the state |

---

## File Listing

```
pipeline/
├── helpers.py                    # Shared: logging, suppression, parsing, load/save
├── 01_build_spine.py             # CCD Directory → base documents + crosswalk
├── 02_load_enrollment.py         # CCD Membership → enrollment by race/sex
├── 03_load_ospi_enrollment.py    # OSPI Enrollment → FRL, ELL, SPED, foster, homeless
├── 04_load_ospi_academics.py     # OSPI Assessment + Growth + SQSS
├── 05_load_ospi_discipline.py    # OSPI Discipline → rates (comma-bug handling)
├── 06_load_ospi_finance.py       # OSPI PPE → per-pupil expenditure
├── 07_load_crdc.py               # All 13 CRDC files → discipline/safety/staffing/courses
├── 08_finalize.py                # Add metadata, compute join_status, log summary
├── 09_write_to_atlas.py          # Drop collection, insert all documents
├── 10_verify.py                  # Fairhaven check, integrity checks, generate receipt
├── run_pipeline.py               # Runs all steps in order
cleaning_rules.yaml               # Every transformation, readable without code (project root)
```

Output documentation:
```
phases/phase-2/
├── receipt.md                    # Verification receipt with SHA256 hashes
├── decision_log.md               # Pipeline design decisions
├── fairhaven_test.md             # Field-by-field against live MongoDB
├── phase_exit.md                 # Placeholder for builder review
```

---

## Script-by-Script Breakdown

### helpers.py — Shared Utilities

Not a pipeline step. Imported by every script.

**Functions:**
- `setup_logging(script_name)` — Dual output: console + timestamped file in `logs/`. Returns a logger. Log messages are complete English sentences per CLAUDE.md.
- `load_schools()` — Load `data/schools_pipeline.json`. Returns dict keyed by NCESSCH.
- `save_schools(schools)` — Save dict back to `data/schools_pipeline.json`.
- `parse_crdc_value(val)` — Handle CRDC suppression: -9 → `None` with `not_applicable` flag, -5/-4/-3 → `None` with `suppressed` flag, -12/-13 → `None` with `unknown_negative` flag, 0 → `0` (real zero). Returns `(value, flag_dict_or_None)`.
- `parse_ospi_suppression(val, dat_field=None)` — Handle OSPI suppression: `N<10` → `None` + suppressed, `*` → `None` + suppressed, `No Students` → `None` + no_students, values starting with `<` or `>` → `None` + top_bottom_range. Returns `(value, flag_dict_or_None)`.
- `parse_percentage(val)` — Strip `%`, convert to 0.0–1.0 decimal. `"64.90%"` → `0.649`.
- `safe_int(val)` — Convert to int, return `None` if not possible.
- `safe_float(val)` — Strip commas, convert to float, return `None` if not possible.
- `compute_sha256(filepath)` — SHA256 hash of a file for the receipt.
- `RACE_SUFFIXES` — Dict mapping CRDC race/sex suffixes to schema keys (reuse from schema_preflight.py pattern).

### 01_build_spine.py — CCD Directory → Base Documents

```
PURPOSE: Create one document per WA school from CCD Directory. This is the pipeline's starting point.
INPUTS: data/ccd_wa_directory.csv
OUTPUTS: Creates data/schools_pipeline.json with ~2,566 base documents
JOIN KEYS: NCESSCH (primary key for all downstream joins)
SUPPRESSION HANDLING: None needed for directory fields
RECEIPT: phases/phase-2/receipt.md — spine section
FAILURE MODES: Missing NCESSCH, non-WA schools leaking in
```

**What it does:**
1. Delete any existing `data/schools_pipeline.json` (idempotent fresh start)
2. Read `data/ccd_wa_directory.csv` with `dtype=str`
3. Filter to open schools only
4. For each school, create a document with:
   - `_id`: NCESSCH (12-char string)
   - `name`: SCH_NAME
   - `district.name`: LEA_NAME
   - `district.nces_id`: LEAID
   - `address`: LSTREET1, LCITY, LSTATE, LZIP
   - `school_type`: SCH_TYPE_TEXT
   - `level`: LEVEL
   - `grade_span`: GSLO, GSHI
   - `is_charter`: CHARTER_TEXT → boolean
   - `website`: WEBSITE
   - `phone`: PHONE
   - `metadata.ospi_district_code`: parsed from ST_SCHID (middle segment)
   - `metadata.ospi_school_code`: parsed from ST_SCHID (last segment)
5. Save to `data/schools_pipeline.json`
6. Log: "Created N base documents. Fairhaven (530042000104): [found/not found]."

### 02_load_enrollment.py — CCD Membership → Enrollment

```
PURPOSE: Add enrollment data (total, by race, by sex) from CCD Membership
INPUTS: data/ccd_wa_membership.csv, data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with enrollment section
JOIN KEYS: ncessch (membership) → _id (spine)
SUPPRESSION HANDLING: CCD -1 → null + not_reported
RECEIPT: phases/phase-2/receipt.md — enrollment section
FAILURE MODES: Schools in spine but not in membership (103 have 0 enrollment)
```

### 03_load_ospi_enrollment.py — OSPI Demographics

```
PURPOSE: Add FRL, ELL, SPED, and other demographic subgroup counts from OSPI Enrollment
INPUTS: WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv, data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with demographics section
JOIN KEYS: DistrictCode + SchoolCode → metadata.ospi_district_code + metadata.ospi_school_code
SUPPRESSION HANDLING: OSPI N<10 → null + suppressed. "No Students" → null. Blank/empty → null.
RECEIPT: phases/phase-2/receipt.md — demographics section
FAILURE MODES: 6 schools with 9xx district codes won't match — log, don't fail
```

### 04_load_ospi_academics.py — Assessment + Growth + Attendance

```
PURPOSE: Add proficiency, growth SGP, attendance, 9th grade on track, and dual credit
INPUTS: Assessment, Growth (2024-25 + 2023-24), SQSS files + schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with academics section
JOIN KEYS: DistrictCode + SchoolCode → crosswalk
SUPPRESSION HANDLING: N<10 → null + suppressed. DATReason='NULL' is NOT suppression.
RECEIPT: phases/phase-2/receipt.md — academics section
FAILURE MODES: Growth StudentGroupType "AllStudents" (no space). SQSS "All Students" (with space).
```

**Growth fallback rule (clarification #2):** Fall back to 2023-24 ONLY when the school has zero rows in the 2024-25 file. If the school appears in 2024-25 but is suppressed, keep the suppressed null — do NOT fall back.

### 05_load_ospi_discipline.py — Discipline Rates

```
PURPOSE: Add aggregate discipline rates from OSPI
INPUTS: WA-raw/ospi/Report_Card_Discipline_for_2023-24.csv, data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with discipline.ospi section
JOIN KEYS: DistrictCode + SchoolCode → crosswalk (STRIP COMMAS FIRST)
SUPPRESSION HANDLING: N<10/*/Top-Bottom Range → null + suppressed
RECEIPT: phases/phase-2/receipt.md — discipline section
FAILURE MODES: COMMA-IN-IDS BUG. GradeLevel is "All" not "All Grades".
```

### 06_load_ospi_finance.py — Per-Pupil Expenditure

```
PURPOSE: Add per-pupil expenditure data from OSPI PPE
INPUTS: WA-raw/ospi/Per_Pupil_Expenditure_AllYears.csv, data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with finance section
JOIN KEYS: SchoolCode → metadata.ospi_school_code (verify uniqueness — see clarification #1)
SUPPRESSION HANDLING: None expected
RECEIPT: phases/phase-2/receipt.md — finance section
FAILURE MODES: Multi-year file — filter to 2023-24. Dollar values have commas.
```

**SchoolCode uniqueness (clarification #1):** Before joining, check whether SchoolCode is unique statewide or if multiple schools share the same code across districts. If collisions exist, add DistrictCode (via `County District Code` column) to disambiguate. Log any collisions found.

### 07_load_crdc.py — All 13 CRDC Files

```
PURPOSE: Add CRDC data: discipline by race/sex/disability, safety, staffing, course access
INPUTS: data/crdc_wa/*.csv (13 files), data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with discipline.crdc, safety, staffing, course_access
JOIN KEYS: COMBOKEY (12-char) → _id (NCESSCH, direct match)
SUPPRESSION HANDLING: -9 → not_applicable. -5/-4/-3 → suppressed. -12/-13 → unknown_negative (LOG ALL).
                      0 → 0 (genuine zero).
RECEIPT: phases/phase-2/receipt.md — CRDC section
FAILURE MODES: ~128 schools missing CRDC (post-2021-22). Expected.
```

### 08_finalize.py — Metadata + Join Status

Adds `metadata.dataset_version`, `metadata.load_timestamp`, `metadata.data_vintage`, and `metadata.join_status` to every document.

### 09_write_to_atlas.py — Push to MongoDB

Drop `schools` collection, insert all documents, create `name` index.

### 10_verify.py — Fairhaven Check + Receipt

**Clarification #3:** All Fairhaven expected values come from `phases/phase-1/fairhaven_test.md`, not re-derived from raw files. This is the Phase 1 verified source of truth.

### run_pipeline.py — Orchestrator

Runs all steps in order. Supports `--step N` for single-step execution.

---

## cleaning_rules.yaml

Located at project root. Contains every transformation the pipeline applies, readable without code. See full structure in the plan file at `.claude/plans/`.

---

## Commit Plan

One commit per completed step (10 commits total).

---

## Verification Strategy

1. Fairhaven field-by-field against live MongoDB (13+ fields from Phase 1 fairhaven_test.md)
2. Join rate < 5% failure
3. Suppression integrity (no suppressed values stored as 0)
4. Type checks (NCES IDs are strings, percentages in 0.0–1.0)
5. Document count matches open WA schools
6. SHA256 hashes for all source files
7. -12/-13 instance log

---

## Known Issues

1. CRDC -12/-13: Log all 1,694 instances
2. OSPI Top/Bottom Range: null/suppressed
3. OSPI Discipline comma-in-IDs: strip in step 05
4. 6 unmatched OSPI schools (9xx codes): log, don't fail
5. ~128 CCD schools without CRDC: mark as missing_crdc
6. Growth PercentLowGrowth: verify if counts or percentages during implementation

---

## Deviation Policy

If anything changes during implementation, note the deviation in `phases/phase-2/decision_log.md` with reasoning.
