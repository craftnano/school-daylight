# Phase 2R — Vintage inventory: remaining 16 variables

Read-only side-by-side inventory across `schooldaylight` (historical) and `schooldaylight_experiment` (operating Phase 3R artifacts) for the 16 v1 similarity variables not covered in the teacher_experience round.

Sample schools (same 5 used for teacher_experience):
- `530042000104` — Fairhaven Middle
- `530423000670` — Juanita HS
- `530927001579` — Lewis and Clark HS
- `530393000610` — Washington Elementary
- `530000102795` — Thunder Mountain Middle

Format per variable: Section A (literal sample values, side-by-side), vintage stamp table, Section B (source), Section C (pipeline filter), vintage triangulation (empirical / pipeline-encoded / documentation-inferred). Non-uniform vintage stamps within the 5-school sample are flagged in place.

## Key findings (summary index)

**Database-shape finding (informs every variable below):**

- `schooldaylight` (historical) carries Phase 2 outputs only: enrollment, demographics (FRL/ELL/SPED/Homeless/Migrant counts), academics.attendance, derived.chronic_absenteeism_pct. **It carries NONE of the Phase 3R artifacts:** no `graduation_rate`, no `derived.<x>_pct` ratios for ell/sped/migrant/homelessness/race, no `census_acs`, no `teacher_salary`, no `teacher_experience`.
- `schooldaylight_experiment` (operating) carries the same Phase 2 outputs plus the full Phase 3R artifact set.
- Both databases share Phase 5 `layer3_narrative` and `derived.flags` (per orientation preamble in the teacher_experience round).
- For 11 of the 16 variables (3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17 — every Phase-3R-added variable), the side-by-side comparison line is uniformly **"absent in schooldaylight, present in schooldaylight_experiment"**. The only "same across DBs" variables are 1 (enrollment), 2 (chronic absenteeism, with caveats), and 4 (FRL pct).

**Non-uniformity flag in the 5-school sample (1 instance):**

- **Variable 2 — chronic absenteeism rate.** In `schooldaylight` (historical), the `academics.attendance.year` stamp is `"2024-25"` for Fairhaven, Juanita HS, and Thunder Mountain Middle, but ABSENT for Lewis and Clark HS and Washington Elementary. These two schools also have **null `derived.chronic_absenteeism_pct`** in historical but populated values in experiment (0.6289 and 0.2336 respectively). Both are in 0X-county districts (Spokane Co district `06037` and Mead district `03017`), matching the population of ~390 schools that the May 7 zfill remediation patched in the experiment database but did NOT patch in production.

**Vintage triangulation mismatches (documentation drift, multiple variables):**

- **Variable 1 (Enrollment).** Matrix row 1 says "OSPI Report Card 2023-24"; pipeline uses CCD (`data/ccd_wa_membership.csv`). Both empirical and pipeline agree on year string `"2023-24"`. Documentation source-type drift, vintage agrees.
- **Variable 2 (Chronic absenteeism).** Matrix row 2 says "OSPI Report Card 2023-24, school-level"; pipeline reads `Report_Card_SQSS_for_2024-25.csv` and stamps `"2024-25"`. The source file's internal `SchoolYear` column has the single value `"2025"` (raw OSPI label), the filename says `2024-25`, the loader stamps `2024-25`, the matrix doc says `2023-24`. Year-string drift across three layers.
- **Variable 5 (Minority rate).** Matrix row 5 says "OSPI 2023-24"; actual upstream is CCD (per `_meta.source` stamp: `"(CCD 2023-24)"`). Source-type drift, vintage agrees.
- **Variables 10-15 (Census ACS / TIGER).** Matrix rows 19/21/23/24/26/27 say "already ingested" with no year stated. Empirical stamps say `acs5_2019_2023` and TIGER 2023. Documentation lacks the vintage entirely.
- **Variable 17 (Teacher salary).** Matrix and brief say `"2023-24"`; stored `dataset_year` is `"2023-24 final"` (more specific). Empirical and pipeline agree. An earlier sandbox-only loader had stamped `"2025-26 preliminary"`; that was overwritten by the May 5 re-ingestion. No live data carries the preliminary stamp.

**Provenance pattern summary:**

| # | Variable | Pattern |
|---|---|---|
| 1 | Enrollment | File-sourced |
| 2 | Chronic absenteeism | Derived from SQSS attendance (file-sourced upstream) |
| 3 | Graduation rate | API-sourced (data.wa.gov 76iv-8ed4), no cache |
| 4 | FRL pct | File-sourced |
| 5 | Minority pct non-white | Derived from CCD enrollment (file-sourced upstream) |
| 6 | Homelessness pct | Derived from OSPI demographics (file-sourced upstream) |
| 7 | ELL pct | Derived from OSPI demographics (file-sourced upstream) |
| 8 | Migrant pct | Derived from OSPI demographics (file-sourced upstream) |
| 10 | Median household income | API-sourced (Census ACS), no cache |
| 11 | Gini index | API-sourced (Census ACS), no cache |
| 12 | Labor force participation | API-sourced (Census ACS subject), no cache |
| 13 | Unemployment rate | API-sourced (Census ACS subject), no cache |
| 14 | Land area | API-sourced (TIGER Gazetteer ZIP, in-memory), no cache |
| 15 | Population density | Derived (Census + TIGER, mixed-year derivation) |
| 16 | SPED pct | Derived from OSPI demographics (file-sourced upstream) |
| 17 | Average teacher salary | File-sourced (S-275 XLSX) |

7 of 16 are API-sourced with no on-disk cache (3, 10, 11, 12, 13, 14, plus teacher experience from the prior round) — those are the variables whose provenance weakens the most under the existing convention.

**Bug-residue finding (Variable 2 detail):**

The May 7 zfill remediation (`_run_reingest_post_zfill_2026-05-07.py`) was applied to `schooldaylight_experiment` only and explicitly NOT to production (`schooldaylight`). In the 5-school sample this surfaces as two of the five schools (40%) having null chronic absenteeism in historical that is populated in experiment. If the wider 390-school cohort behaves similarly, the historical database's 2023-24 frame is also bug-affected, not just stale.

---


## Variable 1: Enrollment (membership)

- **Schema location:** `enrollment.total`
- **Provenance pattern:** File-sourced (CCD WA Membership CSV on disk).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: 588
- `schooldaylight_experiment`: 588
- **Comparison:** same

**530423000670 — Juanita HS**

- `schooldaylight`: 1778
- `schooldaylight_experiment`: 1778
- **Comparison:** same

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: 96
- `schooldaylight_experiment`: 96
- **Comparison:** same

**530393000610 — Washington Elementary**

- `schooldaylight`: 405
- `schooldaylight_experiment`: 405
- **Comparison:** same

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: 506
- `schooldaylight_experiment`: 506
- **Comparison:** same

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `enrollment.year` | `'2023-24'` | `'2023-24'` |
| 530423000670 | `enrollment.year` | `'2023-24'` | `'2023-24'` |
| 530927001579 | `enrollment.year` | `'2023-24'` | `'2023-24'` |
| 530393000610 | `enrollment.year` | `'2023-24'` | `'2023-24'` |
| 530000102795 | `enrollment.year` | `'2023-24'` | `'2023-24'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- File: `data/ccd_wa_membership.csv` (file size 180 KB, mtime 2026-02-21 15:40).
- Header: `ncessch,school_name,total_enrollment,american_indian,asian,black,hispanic,pacific_islander,two_or_more,white,not_specified,male,female`.
- The CSV is the Phase 1 pre-aggregated school-level CCD membership extract (one row per NCESSCH).
- No SchoolYear column in the file; vintage is documented only in the pipeline script and ingestion metadata.
- Underlying federal file on disk: `WA-raw/federal/ccd_sch_052_2425_l_1a_073025.csv` (2.3 GB, December 2025 mtime). This is the 2024-25 CCD Membership national release — but the pre-aggregated `data/ccd_wa_membership.csv` consumed by the pipeline was produced earlier (Feb 2026 mtime) and is stamped 2023-24 by the loader. The 2024-25 national release is present on disk but not yet wired into the pipeline.

### Section C — Pipeline filter / ingestion logic

Pipeline 02 hard-codes `"year": "2023-24"` in the enrollment block (`pipeline/02_load_enrollment.py` line 61). No year filter on the file itself — the file has only one school-level enrollment per NCESSCH.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `enrollment.year` = "2023-24" |
| Empirical (`schooldaylight_experiment`) | `enrollment.year` = "2023-24" |
| Encoded by pipeline / ingestion script | Pipeline 02 hard-codes `"year": "2023-24"` in the enrollment block (`pipeline/02_load_enrollment.py` line 61). No year filter on the file itself — the file has only one school-level enrollment per NCESSCH. |
| Inferred from documentation | `variable_decision_matrix.md` row 1: "OSPI Report Card 2023-24 (already ingested)". `build_log.md` discusses CCD 2023-24 for enrollment. Note: matrix row 1 says OSPI but pipeline uses CCD. |

## Variable 2: Chronic absenteeism rate (substituted for attendance rate)

- **Schema location:** `derived.chronic_absenteeism_pct`
- **Provenance pattern:** Derived (= 1 - academics.attendance.regular_attendance_pct, which is itself file-sourced from OSPI SQSS CSV on disk).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: 0.3997
- `schooldaylight_experiment`: 0.3997
- **Comparison:** same

  Upstream / supporting context:
  - `academics.attendance.regular_attendance_pct` — hist: 0.6003 | exp: 0.6003
  - `academics.attendance.numerator` — hist: 362 | exp: 362
  - `academics.attendance.denominator` — hist: 603 | exp: 603

**530423000670 — Juanita HS**

- `schooldaylight`: 0.2823
- `schooldaylight_experiment`: 0.2823
- **Comparison:** same

  Upstream / supporting context:
  - `academics.attendance.regular_attendance_pct` — hist: 0.7177 | exp: 0.7177
  - `academics.attendance.numerator` — hist: 1299 | exp: 1299
  - `academics.attendance.denominator` — hist: 1810 | exp: 1810

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: null
- `schooldaylight_experiment`: 0.6289
- **Comparison:** different

  Upstream / supporting context:
  - `academics.attendance.regular_attendance_pct` — hist: ABSENT | exp: 0.3711
  - `academics.attendance.numerator` — hist: ABSENT | exp: 36
  - `academics.attendance.denominator` — hist: ABSENT | exp: 97

**530393000610 — Washington Elementary**

- `schooldaylight`: null
- `schooldaylight_experiment`: 0.2336
- **Comparison:** different

  Upstream / supporting context:
  - `academics.attendance.regular_attendance_pct` — hist: ABSENT | exp: 0.7664
  - `academics.attendance.numerator` — hist: ABSENT | exp: 328
  - `academics.attendance.denominator` — hist: ABSENT | exp: 428

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: 0.2089
- `schooldaylight_experiment`: 0.2089
- **Comparison:** same

  Upstream / supporting context:
  - `academics.attendance.regular_attendance_pct` — hist: 0.7911 | exp: 0.7911
  - `academics.attendance.numerator` — hist: 409 | exp: 409
  - `academics.attendance.denominator` — hist: 517 | exp: 517

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `academics.attendance.year` | `'2024-25'` | `'2024-25'` |
| 530423000670 | `academics.attendance.year` | `'2024-25'` | `'2024-25'` |
| 530927001579 | `academics.attendance.year` | ABSENT | `'2024-25'` |
| 530393000610 | `academics.attendance.year` | ABSENT | `'2024-25'` |
| 530000102795 | `academics.attendance.year` | `'2024-25'` | `'2024-25'` |

⚠ NON-UNIFORM `academics.attendance.year` in `schooldaylight` across the 5 sampled schools: distinct values = {('ABSENT',), ('present', '"2024-25"')}

### Section B — Source file or API endpoint

- File: `WA-raw/ospi/Report_Card_SQSS_for_2024-25.csv` (244 MB, mtime 2026-02-21 14:13).
- File's `SchoolYear` column has a single distinct value: `"2025"` (not `"2024-25"`).
- File's `DataAsOf` column sample value: `"2026 Jan 06 12:00:00 AM"`.
- Filter applied at read: `OrganizationLevel == "School"`, `StudentGroupType == "AllStudents"` (note: SQSS uses "All Students" with space; see `pipeline/04_load_ospi_academics.py:255`), `GradeLevel == "All Grades"`.

### Section C — Pipeline filter / ingestion logic

`pipeline/04_load_ospi_academics.py:load_sqss` loads SQSS rows and stamps `attendance["year"] = "2024-25"` (line 281). `pipeline/12_compute_ratios.py:169` derives `derived.chronic_absenteeism_pct = 1.0 - academics.attendance.regular_attendance_pct`. No standalone year filter on the chronic absenteeism field — it inherits the SQSS file's vintage.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `academics.attendance.year` = "2024-25" |
| Empirical (`schooldaylight_experiment`) | `academics.attendance.year` = "2024-25" |
| Encoded by pipeline / ingestion script | `pipeline/04_load_ospi_academics.py:load_sqss` loads SQSS rows and stamps `attendance["year"] = "2024-25"` (line 281). `pipeline/12_compute_ratios.py:169` derives `derived.chronic_absenteeism_pct = 1.0 - academics.attendance.regular_attendance_pct`. No standalone year filter on the chronic absenteeism field — it inherits the SQSS file's vintage. |
| Inferred from documentation | `variable_decision_matrix.md` row 2: "OSPI Report Card 2023-24, school-level". Note: pipeline uses SQSS 2024-25 file; the matrix row claim of "2023-24" is documentation drift. |

## Variable 3: Graduation rate, 4-year (HS-only)

- **Schema location:** `graduation_rate.cohort_4yr`
- **Provenance pattern:** API-sourced with no cache (data.wa.gov SODA endpoint 76iv-8ed4; raw API rows never persisted).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: null
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `graduation_rate.cohort_4yr` — hist: ABSENT | exp: null
  - `graduation_rate.cohort_5yr` — hist: ABSENT | exp: null
  - `graduation_rate.metadata.not_applicable_reason` — hist: ABSENT | exp: 'grade_span_not_high_school'

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.8990147783251
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `graduation_rate.cohort_4yr` — hist: ABSENT | exp: 0.8990147783251
  - `graduation_rate.cohort_5yr` — hist: ABSENT | exp: 0.9632545931758
  - `graduation_rate.metadata.not_applicable_reason` — hist: ABSENT | exp: null

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: null
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `graduation_rate.cohort_4yr` — hist: ABSENT | exp: null
  - `graduation_rate.cohort_5yr` — hist: ABSENT | exp: null
  - `graduation_rate.metadata.not_applicable_reason` — hist: ABSENT | exp: null

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: null
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `graduation_rate.cohort_4yr` — hist: ABSENT | exp: null
  - `graduation_rate.cohort_5yr` — hist: ABSENT | exp: null
  - `graduation_rate.metadata.not_applicable_reason` — hist: ABSENT | exp: 'grade_span_not_high_school'

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: null
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `graduation_rate.cohort_4yr` — hist: ABSENT | exp: null
  - `graduation_rate.cohort_5yr` — hist: ABSENT | exp: null
  - `graduation_rate.metadata.not_applicable_reason` — hist: ABSENT | exp: 'grade_span_not_high_school'

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `graduation_rate.metadata.dataset_year` | ABSENT | `'2023-24'` |
| 530042000104 | `graduation_rate.metadata.source` | ABSENT | `'data.wa.gov 76iv-8ed4'` |
| 530042000104 | `graduation_rate.metadata.fetch_timestamp` | ABSENT | `'2026-05-05T00:54:45Z'` |
| 530423000670 | `graduation_rate.metadata.dataset_year` | ABSENT | `'2023-24'` |
| 530423000670 | `graduation_rate.metadata.source` | ABSENT | `'data.wa.gov 76iv-8ed4'` |
| 530423000670 | `graduation_rate.metadata.fetch_timestamp` | ABSENT | `'2026-05-05T00:54:45Z'` |
| 530927001579 | `graduation_rate.metadata.dataset_year` | ABSENT | `'2023-24'` |
| 530927001579 | `graduation_rate.metadata.source` | ABSENT | `'data.wa.gov 76iv-8ed4'` |
| 530927001579 | `graduation_rate.metadata.fetch_timestamp` | ABSENT | `'2026-05-05T00:54:45Z'` |
| 530393000610 | `graduation_rate.metadata.dataset_year` | ABSENT | `'2023-24'` |
| 530393000610 | `graduation_rate.metadata.source` | ABSENT | `'data.wa.gov 76iv-8ed4'` |
| 530393000610 | `graduation_rate.metadata.fetch_timestamp` | ABSENT | `'2026-05-05T00:54:45Z'` |
| 530000102795 | `graduation_rate.metadata.dataset_year` | ABSENT | `'2023-24'` |
| 530000102795 | `graduation_rate.metadata.source` | ABSENT | `'data.wa.gov 76iv-8ed4'` |
| 530000102795 | `graduation_rate.metadata.fetch_timestamp` | ABSENT | `'2026-05-05T00:54:45Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- API endpoint: `https://data.wa.gov/resource/76iv-8ed4.json`.
- No cached source file exists on disk. Grep for `76iv-8ed4` outside logs/docs returns no JSON/CSV/parquet/pickle.
- The fetch occurred 2026-05-05 00:19 UTC per `logs/phase3r_api_ingestion_2026-05-04_17-19-03.log`: 3,007 rows pulled.
- No DataAsOf-equivalent metadata is preserved from the SODA response.

### Section C — Pipeline filter / ingestion logic

Filter encoded in `phases/phase-3R/experiment/_run_api_ingestion.py` lines 165-169: `organizationlevel=School`, `schoolyear=2023-24`, `studentgroup=All Students`. There is no production-pipeline loader for graduation rate; the Phase 3R sandbox script is the only loader. The leading-zero zfill bug was patched in-source per commit `97a342f` / `a0de7ec`-class fix; runtime patch via `_patch_task1_zfill.py` applied to existing experiment data.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `graduation_rate.metadata.dataset_year` ABSENT in all 5; `graduation_rate.metadata.source` ABSENT in all 5; `graduation_rate.metadata.fetch_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `graduation_rate.metadata.dataset_year` = "2023-24"; `graduation_rate.metadata.source` = "data.wa.gov 76iv-8ed4"; `graduation_rate.metadata.fetch_timestamp` = "2026-05-05T00:54:45Z" |
| Encoded by pipeline / ingestion script | Filter encoded in `phases/phase-3R/experiment/_run_api_ingestion.py` lines 165-169: `organizationlevel=School`, `schoolyear=2023-24`, `studentgroup=All Students`. There is no production-pipeline loader for graduation rate; the Phase 3R sandbox script is the only loader. The leading-zero zfill bug was patched in-source per commit `97a342f` / `a0de7ec`-class fix; runtime patch via `_patch_task1_zfill.py` applied to existing experiment data. |
| Inferred from documentation | `variable_decision_matrix.md` row 3: "data.wa.gov Report Card Graduation 2023-24, school-level all-students". |

## Variable 4: FRL (Low Income) rate

- **Schema location:** `demographics.frl_pct`
- **Provenance pattern:** File-sourced (OSPI Report Card Enrollment CSV on disk); ratio computed in-loader as Low_Income / All_Students.

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: 0.4393
- `schooldaylight_experiment`: 0.4393
- **Comparison:** same

  Upstream / supporting context:
  - `demographics.frl_count` — hist: 257 | exp: 257
  - `demographics.ospi_total` — hist: 585 | exp: 585

**530423000670 — Juanita HS**

- `schooldaylight`: 0.28
- `schooldaylight_experiment`: 0.28
- **Comparison:** same

  Upstream / supporting context:
  - `demographics.frl_count` — hist: 492 | exp: 492
  - `demographics.ospi_total` — hist: 1757 | exp: 1757

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: 0.4483
- `schooldaylight_experiment`: 0.4483
- **Comparison:** same

  Upstream / supporting context:
  - `demographics.frl_count` — hist: 39 | exp: 39
  - `demographics.ospi_total` — hist: 87 | exp: 87

**530393000610 — Washington Elementary**

- `schooldaylight`: 0.7786
- `schooldaylight_experiment`: 0.7786
- **Comparison:** same

  Upstream / supporting context:
  - `demographics.frl_count` — hist: 306 | exp: 306
  - `demographics.ospi_total` — hist: 393 | exp: 393

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: 0.2903
- `schooldaylight_experiment`: 0.2903
- **Comparison:** same

  Upstream / supporting context:
  - `demographics.frl_count` — hist: 135 | exp: 135
  - `demographics.ospi_total` — hist: 465 | exp: 465

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `demographics.year` | `'2023-24'` | `'2023-24'` |
| 530423000670 | `demographics.year` | `'2023-24'` | `'2023-24'` |
| 530927001579 | `demographics.year` | `'2023-24'` | `'2023-24'` |
| 530393000610 | `demographics.year` | `'2023-24'` | `'2023-24'` |
| 530000102795 | `demographics.year` | `'2023-24'` | `'2023-24'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- File: `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` (7.0 MB, mtime 2026-02-21 13:36).
- File's `SchoolYear` column has a single distinct value: `"2023-24"`.
- File's `DataAsOf` column has a single distinct value: `"2024 Jun 18 12:00:00 AM"`.
- This single file is the source for variables 4, 6, 7, 8, and 16 (FRL, Homeless, ELL, Migrant, SPED) — confirmed by `pipeline/03_load_ospi_enrollment.py`.

### Section C — Pipeline filter / ingestion logic

`pipeline/03_load_ospi_enrollment.py` hard-codes the filename and stamps `demographics["year"] = "2023-24"` (line 89). Filter: `OrganizationLevel == "School"` AND `GradeLevel == "All Grades"` (line 61). FRL ratio is computed in-loader as `frl_count / all_students_val` (line 98).

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `demographics.year` = "2023-24" |
| Empirical (`schooldaylight_experiment`) | `demographics.year` = "2023-24" |
| Encoded by pipeline / ingestion script | `pipeline/03_load_ospi_enrollment.py` hard-codes the filename and stamps `demographics["year"] = "2023-24"` (line 89). Filter: `OrganizationLevel == "School"` AND `GradeLevel == "All Grades"` (line 61). FRL ratio is computed in-loader as `frl_count / all_students_val` (line 98). |
| Inferred from documentation | `variable_decision_matrix.md` row 4: "OSPI 2023-24 (already ingested)". |

## Variable 5: Minority rate (% non-white)

- **Schema location:** `derived.race_pct_non_white`
- **Provenance pattern:** Derived (computed in Phase 3R sandbox = 1 − enrollment.by_race.white / enrollment.total; upstream is the CCD-sourced enrollment block from variable 1).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.33163265306122447
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `enrollment.by_race.white` — hist: 393 | exp: 393
  - `enrollment.total` — hist: 588 | exp: 588
  - `enrollment.year` — hist: '2023-24' | exp: '2023-24'

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.5050618672665916
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `enrollment.by_race.white` — hist: 880 | exp: 880
  - `enrollment.total` — hist: 1778 | exp: 1778
  - `enrollment.year` — hist: '2023-24' | exp: '2023-24'

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.38541666666666663
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `enrollment.by_race.white` — hist: 59 | exp: 59
  - `enrollment.total` — hist: 96 | exp: 96
  - `enrollment.year` — hist: '2023-24' | exp: '2023-24'

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.6395061728395062
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `enrollment.by_race.white` — hist: 146 | exp: 146
  - `enrollment.total` — hist: 405 | exp: 405
  - `enrollment.year` — hist: '2023-24' | exp: '2023-24'

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.31818181818181823
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `enrollment.by_race.white` — hist: 345 | exp: 345
  - `enrollment.total` — hist: 506 | exp: 506
  - `enrollment.year` — hist: '2023-24' | exp: '2023-24'

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `derived.race_pct_non_white_meta.source` | ABSENT | `'1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)'` |
| 530042000104 | `derived.race_pct_non_white_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530423000670 | `derived.race_pct_non_white_meta.source` | ABSENT | `'1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)'` |
| 530423000670 | `derived.race_pct_non_white_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530927001579 | `derived.race_pct_non_white_meta.source` | ABSENT | `'1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)'` |
| 530927001579 | `derived.race_pct_non_white_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530393000610 | `derived.race_pct_non_white_meta.source` | ABSENT | `'1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)'` |
| 530393000610 | `derived.race_pct_non_white_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530000102795 | `derived.race_pct_non_white_meta.source` | ABSENT | `'1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)'` |
| 530000102795 | `derived.race_pct_non_white_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream values come from `data/ccd_wa_membership.csv` (see Variable 1 Section B).
- No standalone source file for this derived rate.

### Section C — Pipeline filter / ingestion logic

Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (lines 405-409): `race_pct = 1.0 - (enrollment.by_race.white / enrollment.total)`. Vintage stamp on the `_meta` block stamps `"source": "1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)"`. No year filter; inherits enrollment vintage.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `derived.race_pct_non_white_meta.source` ABSENT in all 5; `derived.race_pct_non_white_meta.compute_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `derived.race_pct_non_white_meta.source` = "1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)"; `derived.race_pct_non_white_meta.compute_timestamp` = "2026-05-05T00:19:03Z" |
| Encoded by pipeline / ingestion script | Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (lines 405-409): `race_pct = 1.0 - (enrollment.by_race.white / enrollment.total)`. Vintage stamp on the `_meta` block stamps `"source": "1 - (enrollment.by_race.white / enrollment.total) (CCD 2023-24)"`. No year filter; inherits enrollment vintage. |
| Inferred from documentation | `variable_decision_matrix.md` row 5: "OSPI 2023-24 (already ingested), single percent non-white". Note: matrix says OSPI but the actual upstream is CCD enrollment (build log clarified). |

## Variable 6: Homeless rate

- **Schema location:** `derived.homelessness_pct`
- **Provenance pattern:** Derived (computed in Phase 3R sandbox = homeless_count / ospi_total; upstream is the OSPI Enrollment CSV used for variable 4).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.06837606837606838
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.homeless_count` — hist: 40 | exp: 40
  - `demographics.ospi_total` — hist: 585 | exp: 585

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.029595902105862264
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.homeless_count` — hist: 52 | exp: 52
  - `demographics.ospi_total` — hist: 1757 | exp: 1757

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.06896551724137931
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.homeless_count` — hist: 6 | exp: 6
  - `demographics.ospi_total` — hist: 87 | exp: 87

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.030534351145038167
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.homeless_count` — hist: 12 | exp: 12
  - `demographics.ospi_total` — hist: 393 | exp: 393

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.02795698924731183
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.homeless_count` — hist: 13 | exp: 13
  - `demographics.ospi_total` — hist: 465 | exp: 465

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `derived.homelessness_pct_meta.source` | ABSENT | `'demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530042000104 | `derived.homelessness_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530423000670 | `derived.homelessness_pct_meta.source` | ABSENT | `'demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530423000670 | `derived.homelessness_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530927001579 | `derived.homelessness_pct_meta.source` | ABSENT | `'demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530927001579 | `derived.homelessness_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530393000610 | `derived.homelessness_pct_meta.source` | ABSENT | `'demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530393000610 | `derived.homelessness_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530000102795 | `derived.homelessness_pct_meta.source` | ABSENT | `'demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530000102795 | `derived.homelessness_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` (see Variable 4 Section B).
- No standalone source file for this derived rate.

### Section C — Pipeline filter / ingestion logic

Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 404): `homeless_pct = safe_ratio(demo.get('homeless_count'), ospi_total)`. `_meta` stamp identifies upstream as `demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)`.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `derived.homelessness_pct_meta.source` ABSENT in all 5; `derived.homelessness_pct_meta.compute_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `derived.homelessness_pct_meta.source` = "demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)"; `derived.homelessness_pct_meta.compute_timestamp` = "2026-05-05T00:19:03Z" |
| Encoded by pipeline / ingestion script | Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 404): `homeless_pct = safe_ratio(demo.get('homeless_count'), ospi_total)`. `_meta` stamp identifies upstream as `demographics.homeless_count / demographics.ospi_total (OSPI 2023-24)`. |
| Inferred from documentation | `variable_decision_matrix.md` row 6: "OSPI Report Card 2023-24, school-level". |

## Variable 7: EL / LEP rate

- **Schema location:** `derived.ell_pct`
- **Provenance pattern:** Derived (ell_count / ospi_total); upstream is OSPI Enrollment CSV used for variable 4.

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.05982905982905983
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.ell_count` — hist: 35 | exp: 35
  - `demographics.ospi_total` — hist: 585 | exp: 585

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.11326124075128059
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.ell_count` — hist: 199 | exp: 199
  - `demographics.ospi_total` — hist: 1757 | exp: 1757

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.04597701149425287
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.ell_count` — hist: 4 | exp: 4
  - `demographics.ospi_total` — hist: 87 | exp: 87

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.22900763358778625
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.ell_count` — hist: 90 | exp: 90
  - `demographics.ospi_total` — hist: 393 | exp: 393

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.07956989247311828
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.ell_count` — hist: 37 | exp: 37
  - `demographics.ospi_total` — hist: 465 | exp: 465

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `derived.ell_pct_meta.source` | ABSENT | `'demographics.ell_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530042000104 | `derived.ell_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530423000670 | `derived.ell_pct_meta.source` | ABSENT | `'demographics.ell_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530423000670 | `derived.ell_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530927001579 | `derived.ell_pct_meta.source` | ABSENT | `'demographics.ell_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530927001579 | `derived.ell_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530393000610 | `derived.ell_pct_meta.source` | ABSENT | `'demographics.ell_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530393000610 | `derived.ell_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530000102795 | `derived.ell_pct_meta.source` | ABSENT | `'demographics.ell_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530000102795 | `derived.ell_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` (see Variable 4 Section B).
- No standalone source file for this derived rate.

### Section C — Pipeline filter / ingestion logic

Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 401): `ell_pct = safe_ratio(demo.get('ell_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `derived.ell_pct_meta.source` ABSENT in all 5; `derived.ell_pct_meta.compute_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `derived.ell_pct_meta.source` = "demographics.ell_count / demographics.ospi_total (OSPI 2023-24)"; `derived.ell_pct_meta.compute_timestamp` = "2026-05-05T00:19:03Z" |
| Encoded by pipeline / ingestion script | Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 401): `ell_pct = safe_ratio(demo.get('ell_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24. |
| Inferred from documentation | `variable_decision_matrix.md` row 7: "OSPI 2023-24 (already ingested); WA term is EL/ML". |

## Variable 8: Migrant rate

- **Schema location:** `derived.migrant_pct`
- **Provenance pattern:** Derived (migrant_count / ospi_total); upstream is OSPI Enrollment CSV used for variable 4.

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.migrant_count` — hist: 0 | exp: 0
  - `demographics.ospi_total` — hist: 585 | exp: 585

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.0005691519635742744
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.migrant_count` — hist: 1 | exp: 1
  - `demographics.ospi_total` — hist: 1757 | exp: 1757

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.011494252873563218
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.migrant_count` — hist: 1 | exp: 1
  - `demographics.ospi_total` — hist: 87 | exp: 87

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.08142493638676845
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.migrant_count` — hist: 32 | exp: 32
  - `demographics.ospi_total` — hist: 393 | exp: 393

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.migrant_count` — hist: 0 | exp: 0
  - `demographics.ospi_total` — hist: 465 | exp: 465

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `derived.migrant_pct_meta.source` | ABSENT | `'demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530042000104 | `derived.migrant_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530423000670 | `derived.migrant_pct_meta.source` | ABSENT | `'demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530423000670 | `derived.migrant_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530927001579 | `derived.migrant_pct_meta.source` | ABSENT | `'demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530927001579 | `derived.migrant_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530393000610 | `derived.migrant_pct_meta.source` | ABSENT | `'demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530393000610 | `derived.migrant_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530000102795 | `derived.migrant_pct_meta.source` | ABSENT | `'demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530000102795 | `derived.migrant_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` (see Variable 4 Section B).
- No standalone source file for this derived rate.

### Section C — Pipeline filter / ingestion logic

Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 403): `migrant_pct = safe_ratio(demo.get('migrant_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `derived.migrant_pct_meta.source` ABSENT in all 5; `derived.migrant_pct_meta.compute_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `derived.migrant_pct_meta.source` = "demographics.migrant_count / demographics.ospi_total (OSPI 2023-24)"; `derived.migrant_pct_meta.compute_timestamp` = "2026-05-05T00:19:03Z" |
| Encoded by pipeline / ingestion script | Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 403): `migrant_pct = safe_ratio(demo.get('migrant_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24. |
| Inferred from documentation | `variable_decision_matrix.md` row 8: "OSPI 2023-24 (already ingested)". |

## Variable 10: Median household income (Census ACS B19013_001E)

- **Schema location:** `census_acs.median_household_income.value`
- **Provenance pattern:** API-sourced with no cache (Census ACS 5-year API endpoint; raw API rows never persisted).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 72424.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.median_household_income.moe` — hist: ABSENT | exp: 3061.0
  - `census_acs._meta.district_geoid` — hist: ABSENT | exp: '5300420'
  - `census_acs._meta.unmatched_reason` — hist: ABSENT | exp: null

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 167899.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.median_household_income.moe` — hist: ABSENT | exp: 5276.0
  - `census_acs._meta.district_geoid` — hist: ABSENT | exp: '5304230'
  - `census_acs._meta.unmatched_reason` — hist: ABSENT | exp: null

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 85251.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.median_household_income.moe` — hist: ABSENT | exp: 2393.0
  - `census_acs._meta.district_geoid` — hist: ABSENT | exp: '5309270'
  - `census_acs._meta.unmatched_reason` — hist: ABSENT | exp: null

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 80550.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.median_household_income.moe` — hist: ABSENT | exp: 3973.0
  - `census_acs._meta.district_geoid` — hist: ABSENT | exp: '5303930'
  - `census_acs._meta.unmatched_reason` — hist: ABSENT | exp: null

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 118845.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.median_household_income.moe` — hist: ABSENT | exp: 6966.0
  - `census_acs._meta.district_geoid` — hist: ABSENT | exp: '5300001'
  - `census_acs._meta.unmatched_reason` — hist: ABSENT | exp: null

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530042000104 | `census_acs._meta.acs_base_api_url` | ABSENT | `'https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53'` |
| 530042000104 | `census_acs._meta.fetched_at` | ABSENT | `'2026-05-04T06:25:42Z'` |
| 530042000104 | `census_acs.median_household_income.census_code` | ABSENT | `'B19013_001E'` |
| 530423000670 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530423000670 | `census_acs._meta.acs_base_api_url` | ABSENT | `'https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53'` |
| 530423000670 | `census_acs._meta.fetched_at` | ABSENT | `'2026-05-04T06:25:42Z'` |
| 530423000670 | `census_acs.median_household_income.census_code` | ABSENT | `'B19013_001E'` |
| 530927001579 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530927001579 | `census_acs._meta.acs_base_api_url` | ABSENT | `'https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53'` |
| 530927001579 | `census_acs._meta.fetched_at` | ABSENT | `'2026-05-04T06:25:42Z'` |
| 530927001579 | `census_acs.median_household_income.census_code` | ABSENT | `'B19013_001E'` |
| 530393000610 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530393000610 | `census_acs._meta.acs_base_api_url` | ABSENT | `'https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53'` |
| 530393000610 | `census_acs._meta.fetched_at` | ABSENT | `'2026-05-04T06:25:42Z'` |
| 530393000610 | `census_acs.median_household_income.census_code` | ABSENT | `'B19013_001E'` |
| 530000102795 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530000102795 | `census_acs._meta.acs_base_api_url` | ABSENT | `'https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53'` |
| 530000102795 | `census_acs._meta.fetched_at` | ABSENT | `'2026-05-04T06:25:42Z'` |
| 530000102795 | `census_acs.median_household_income.census_code` | ABSENT | `'B19013_001E'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- API endpoint: `https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53`.
- This single fetch supplies B19013 (median household income), B19301 (per capita income), B19083 (Gini), and B01003 (total population) for every WA unified school district.
- No on-disk cache of the API response. `VINTAGE` constant in the loader is the string `"acs5_2019_2023"` — i.e. the ACS 5-year release covering 2019-2023, accessed via the `/data/2023/...` URL.

### Section C — Pipeline filter / ingestion logic

`phases/phase-3R/experiment/_run_acs_ingestion.py` line 57: `VINTAGE = "acs5_2019_2023"`. Endpoint URL fetched once at run start (line 165). Filter is geographic only (`state:53`, all WA unified school districts). No year filter beyond the API path itself.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs._meta.vintage` ABSENT in all 5; `census_acs._meta.acs_base_api_url` ABSENT in all 5; `census_acs._meta.fetched_at` ABSENT in all 5; `census_acs.median_household_income.census_code` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs._meta.vintage` = "acs5_2019_2023"; `census_acs._meta.acs_base_api_url` = "https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53"; `census_acs._meta.fetched_at` = "2026-05-04T06:25:42Z"; `census_acs.median_household_income.census_code` = "B19013_001E" |
| Encoded by pipeline / ingestion script | `phases/phase-3R/experiment/_run_acs_ingestion.py` line 57: `VINTAGE = "acs5_2019_2023"`. Endpoint URL fetched once at run start (line 165). Filter is geographic only (`state:53`, all WA unified school districts). No year filter beyond the API path itself. |
| Inferred from documentation | `variable_decision_matrix.md` row 19: "Census ACS B19013_001E at district geography (already ingested)". No vintage year stated in the matrix. |

## Variable 11: Gini index (Census ACS B19083_001E)

- **Schema location:** `census_acs.gini_index.value`
- **Provenance pattern:** API-sourced with no cache (same Census ACS endpoint as variable 10).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.471
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.gini_index.moe` — hist: ABSENT | exp: 0.0146

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.4633
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.gini_index.moe` — hist: ABSENT | exp: 0.0094

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.4498
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.gini_index.moe` — hist: ABSENT | exp: 0.0119

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.4383
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.gini_index.moe` — hist: ABSENT | exp: 0.0173

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.3973
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.gini_index.moe` — hist: ABSENT | exp: 0.0237

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530042000104 | `census_acs.gini_index.census_code` | ABSENT | `'B19083_001E'` |
| 530423000670 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530423000670 | `census_acs.gini_index.census_code` | ABSENT | `'B19083_001E'` |
| 530927001579 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530927001579 | `census_acs.gini_index.census_code` | ABSENT | `'B19083_001E'` |
| 530393000610 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530393000610 | `census_acs.gini_index.census_code` | ABSENT | `'B19083_001E'` |
| 530000102795 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530000102795 | `census_acs.gini_index.census_code` | ABSENT | `'B19083_001E'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Same endpoint as variable 10 (`B19083_001E` is one of the base table fields in the single ACS fetch).

### Section C — Pipeline filter / ingestion logic

Same script as variable 10 (`_run_acs_ingestion.py`). Geographic-only filter (`state:53`). VINTAGE = `acs5_2019_2023`.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs._meta.vintage` ABSENT in all 5; `census_acs.gini_index.census_code` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs._meta.vintage` = "acs5_2019_2023"; `census_acs.gini_index.census_code` = "B19083_001E" |
| Encoded by pipeline / ingestion script | Same script as variable 10 (`_run_acs_ingestion.py`). Geographic-only filter (`state:53`). VINTAGE = `acs5_2019_2023`. |
| Inferred from documentation | `variable_decision_matrix.md` row 21: "Census ACS B19083_001E (already ingested)". |

## Variable 12: Labor force participation rate, 16+ (Census ACS S2301_C02_001E)

- **Schema location:** `census_acs.labor_force_participation_rate_16plus.value`
- **Provenance pattern:** API-sourced with no cache (Census ACS subject-table endpoint).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 65.2
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.labor_force_participation_rate_16plus.moe` — hist: ABSENT | exp: 1.3

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 70.0
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.labor_force_participation_rate_16plus.moe` — hist: ABSENT | exp: 0.9

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 65.9
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.labor_force_participation_rate_16plus.moe` — hist: ABSENT | exp: 1.0

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 62.2
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.labor_force_participation_rate_16plus.moe` — hist: ABSENT | exp: 1.3

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 66.4
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.labor_force_participation_rate_16plus.moe` — hist: ABSENT | exp: 2.1

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530042000104 | `census_acs.labor_force_participation_rate_16plus.census_code` | ABSENT | `'S2301_C02_001E'` |
| 530423000670 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530423000670 | `census_acs.labor_force_participation_rate_16plus.census_code` | ABSENT | `'S2301_C02_001E'` |
| 530927001579 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530927001579 | `census_acs.labor_force_participation_rate_16plus.census_code` | ABSENT | `'S2301_C02_001E'` |
| 530393000610 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530393000610 | `census_acs.labor_force_participation_rate_16plus.census_code` | ABSENT | `'S2301_C02_001E'` |
| 530000102795 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530000102795 | `census_acs.labor_force_participation_rate_16plus.census_code` | ABSENT | `'S2301_C02_001E'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- API endpoint (subject tables): `https://api.census.gov/data/2023/acs/acs5/subject?get=NAME,S1501_C02_015E,S1501_C02_015M,S2301_C02_001E,S2301_C02_001M,S2301_C04_001E,S2301_C04_001M&for=school+district+(unified):*&in=state:53`.
- This subject-table fetch supplies S1501 (bachelor's pct), S2301 LFP, and S2301 unemployment.

### Section C — Pipeline filter / ingestion logic

Same script as variable 10. VINTAGE = `acs5_2019_2023`.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs._meta.vintage` ABSENT in all 5; `census_acs.labor_force_participation_rate_16plus.census_code` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs._meta.vintage` = "acs5_2019_2023"; `census_acs.labor_force_participation_rate_16plus.census_code` = "S2301_C02_001E" |
| Encoded by pipeline / ingestion script | Same script as variable 10. VINTAGE = `acs5_2019_2023`. |
| Inferred from documentation | `variable_decision_matrix.md` row 23: "Census ACS S2301 (already ingested)". |

## Variable 13: Unemployment rate, 16+ (Census ACS S2301_C04_001E)

- **Schema location:** `census_acs.unemployment_rate_16plus.value`
- **Provenance pattern:** API-sourced with no cache (same Census ACS subject endpoint as variable 12).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 5.3
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.unemployment_rate_16plus.moe` — hist: ABSENT | exp: 0.8

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 4.4
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.unemployment_rate_16plus.moe` — hist: ABSENT | exp: 0.5

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 5.2
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.unemployment_rate_16plus.moe` — hist: ABSENT | exp: 0.8

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 4.8
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.unemployment_rate_16plus.moe` — hist: ABSENT | exp: 1.1

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 3.3
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `census_acs.unemployment_rate_16plus.moe` — hist: ABSENT | exp: 1.3

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530042000104 | `census_acs.unemployment_rate_16plus.census_code` | ABSENT | `'S2301_C04_001E'` |
| 530423000670 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530423000670 | `census_acs.unemployment_rate_16plus.census_code` | ABSENT | `'S2301_C04_001E'` |
| 530927001579 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530927001579 | `census_acs.unemployment_rate_16plus.census_code` | ABSENT | `'S2301_C04_001E'` |
| 530393000610 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530393000610 | `census_acs.unemployment_rate_16plus.census_code` | ABSENT | `'S2301_C04_001E'` |
| 530000102795 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530000102795 | `census_acs.unemployment_rate_16plus.census_code` | ABSENT | `'S2301_C04_001E'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Same endpoint as variable 12.

### Section C — Pipeline filter / ingestion logic

Same script as variable 10. VINTAGE = `acs5_2019_2023`.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs._meta.vintage` ABSENT in all 5; `census_acs.unemployment_rate_16plus.census_code` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs._meta.vintage` = "acs5_2019_2023"; `census_acs.unemployment_rate_16plus.census_code` = "S2301_C04_001E" |
| Encoded by pipeline / ingestion script | Same script as variable 10. VINTAGE = `acs5_2019_2023`. |
| Inferred from documentation | `variable_decision_matrix.md` row 24: "Census ACS S2301 (already ingested)". |

## Variable 14: Land area, sq miles (TIGER 2023 Gazetteer ALAND_SQMI)

- **Schema location:** `census_acs.land_area_sq_miles.value`
- **Provenance pattern:** API-sourced with no cache (TIGER 2023 Gazetteer ZIP — the loader downloads the ZIP, extracts the TXT in memory, and discards both).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 90.908
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 68.704
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 52.634
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 291.649
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 449.356
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs._meta.tiger_gazetteer_url` | ABSENT | `'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip'` |
| 530042000104 | `census_acs.land_area_sq_miles.source` | ABSENT | `'TIGER 2023 Unified Gazetteer ALAND_SQMI'` |
| 530423000670 | `census_acs._meta.tiger_gazetteer_url` | ABSENT | `'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip'` |
| 530423000670 | `census_acs.land_area_sq_miles.source` | ABSENT | `'TIGER 2023 Unified Gazetteer ALAND_SQMI'` |
| 530927001579 | `census_acs._meta.tiger_gazetteer_url` | ABSENT | `'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip'` |
| 530927001579 | `census_acs.land_area_sq_miles.source` | ABSENT | `'TIGER 2023 Unified Gazetteer ALAND_SQMI'` |
| 530393000610 | `census_acs._meta.tiger_gazetteer_url` | ABSENT | `'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip'` |
| 530393000610 | `census_acs.land_area_sq_miles.source` | ABSENT | `'TIGER 2023 Unified Gazetteer ALAND_SQMI'` |
| 530000102795 | `census_acs._meta.tiger_gazetteer_url` | ABSENT | `'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip'` |
| 530000102795 | `census_acs.land_area_sq_miles.source` | ABSENT | `'TIGER 2023 Unified Gazetteer ALAND_SQMI'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- File URL: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip`.
- Downloaded into memory at run time (`_run_acs_ingestion.py` lines 195-201). Neither the ZIP nor the extracted `.txt` is persisted to disk.
- Inside the ZIP: tab-delimited national Unified School District file; filtered to `USPS == "WA"` in-memory.

### Section C — Pipeline filter / ingestion logic

Same script as variable 10. The land_area field is stored under `census_acs.land_area_sq_miles` with `source = "TIGER 2023 Unified Gazetteer ALAND_SQMI"`. No year filter at fetch — the URL is year-specific (`2023_Gazetteer`).

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs._meta.tiger_gazetteer_url` ABSENT in all 5; `census_acs.land_area_sq_miles.source` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs._meta.tiger_gazetteer_url` = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip"; `census_acs.land_area_sq_miles.source` = "TIGER 2023 Unified Gazetteer ALAND_SQMI" |
| Encoded by pipeline / ingestion script | Same script as variable 10. The land_area field is stored under `census_acs.land_area_sq_miles` with `source = "TIGER 2023 Unified Gazetteer ALAND_SQMI"`. No year filter at fetch — the URL is year-specific (`2023_Gazetteer`). |
| Inferred from documentation | `variable_decision_matrix.md` row 26: "TIGER Gazetteer ALAND (already ingested)". No vintage year stated in the matrix. |

## Variable 15: Population density, per sq mile (B01003 / ALAND_SQMI)

- **Schema location:** `census_acs.population_density_per_sq_mile.value`
- **Provenance pattern:** Derived (computed in-loader as B01003_001E / TIGER ALAND_SQMI; both upstream values are API-sourced without cache).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 1245.3799445593347
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 3172.3480437820217
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 3195.8999886005245
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 343.7351062407209
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 62.57399478364593
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `census_acs.population_density_per_sq_mile.computed_from` | ABSENT | `'total_population / land_area_sq_miles'` |
| 530042000104 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530423000670 | `census_acs.population_density_per_sq_mile.computed_from` | ABSENT | `'total_population / land_area_sq_miles'` |
| 530423000670 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530927001579 | `census_acs.population_density_per_sq_mile.computed_from` | ABSENT | `'total_population / land_area_sq_miles'` |
| 530927001579 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530393000610 | `census_acs.population_density_per_sq_mile.computed_from` | ABSENT | `'total_population / land_area_sq_miles'` |
| 530393000610 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |
| 530000102795 | `census_acs.population_density_per_sq_mile.computed_from` | ABSENT | `'total_population / land_area_sq_miles'` |
| 530000102795 | `census_acs._meta.vintage` | ABSENT | `'acs5_2019_2023'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream: B01003_001E from ACS base fetch (variable 10); ALAND_SQMI from TIGER 2023 Gazetteer (variable 14).

### Section C — Pipeline filter / ingestion logic

Same script as variable 10. Computed at lines 254-256 of `_run_acs_ingestion.py`: `pop_density = pop_var['value'] / aland`. Stored with field `computed_from = "total_population / land_area_sq_miles"`.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `census_acs.population_density_per_sq_mile.computed_from` ABSENT in all 5; `census_acs._meta.vintage` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `census_acs.population_density_per_sq_mile.computed_from` = "total_population / land_area_sq_miles"; `census_acs._meta.vintage` = "acs5_2019_2023" |
| Encoded by pipeline / ingestion script | Same script as variable 10. Computed at lines 254-256 of `_run_acs_ingestion.py`: `pop_density = pop_var['value'] / aland`. Stored with field `computed_from = "total_population / land_area_sq_miles"`. |
| Inferred from documentation | `variable_decision_matrix.md` row 27: "Computed B01003 / ALAND (already ingested)". Note: relies on ACS 2019-2023 numerator and TIGER 2023 denominator — mixed-year derivation. |

## Variable 16: SPED percentage (addition from Texas)

- **Schema location:** `derived.sped_pct`
- **Provenance pattern:** Derived (sped_count / ospi_total); upstream is OSPI Enrollment CSV used for variable 4.

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.1675213675213675
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.sped_count` — hist: 98 | exp: 98
  - `demographics.ospi_total` — hist: 585 | exp: 585

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.10756972111553785
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.sped_count` — hist: 189 | exp: 189
  - `demographics.ospi_total` — hist: 1757 | exp: 1757

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.39080459770114945
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.sped_count` — hist: 34 | exp: 34
  - `demographics.ospi_total` — hist: 87 | exp: 87

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.24681933842239187
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.sped_count` — hist: 97 | exp: 97
  - `demographics.ospi_total` — hist: 393 | exp: 393

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 0.12473118279569892
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `demographics.sped_count` — hist: 58 | exp: 58
  - `demographics.ospi_total` — hist: 465 | exp: 465

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `derived.sped_pct_meta.source` | ABSENT | `'demographics.sped_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530042000104 | `derived.sped_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530423000670 | `derived.sped_pct_meta.source` | ABSENT | `'demographics.sped_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530423000670 | `derived.sped_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530927001579 | `derived.sped_pct_meta.source` | ABSENT | `'demographics.sped_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530927001579 | `derived.sped_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530393000610 | `derived.sped_pct_meta.source` | ABSENT | `'demographics.sped_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530393000610 | `derived.sped_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |
| 530000102795 | `derived.sped_pct_meta.source` | ABSENT | `'demographics.sped_count / demographics.ospi_total (OSPI 2023-24)'` |
| 530000102795 | `derived.sped_pct_meta.compute_timestamp` | ABSENT | `'2026-05-05T00:19:03Z'` |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- Upstream values come from `WA-raw/ospi/Report_Card_Enrollment_2023-24_School_Year.csv` (see Variable 4 Section B).

### Section C — Pipeline filter / ingestion logic

Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 402): `sped_pct = safe_ratio(demo.get('sped_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `derived.sped_pct_meta.source` ABSENT in all 5; `derived.sped_pct_meta.compute_timestamp` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `derived.sped_pct_meta.source` = "demographics.sped_count / demographics.ospi_total (OSPI 2023-24)"; `derived.sped_pct_meta.compute_timestamp` = "2026-05-05T00:19:03Z" |
| Encoded by pipeline / ingestion script | Computed in `phases/phase-3R/experiment/_run_api_ingestion.py` Task 4 (line 402): `sped_pct = safe_ratio(demo.get('sped_count'), ospi_total)`. `_meta` stamp identifies upstream as OSPI 2023-24. |
| Inferred from documentation | `variable_decision_matrix.md` row A1: "OSPI 2023-24 (already ingested)". |

## Variable 17: Average teacher salary, base per 1.0 FTE (S-275-derived)

- **Schema location:** `teacher_salary.average_base_per_fte`
- **Provenance pattern:** File-sourced (OSPI Personnel Summary XLSX on disk).

### Section A — MongoDB sample values (both databases)

**530042000104 — Fairhaven Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 102921
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `teacher_salary.average_base_per_fte` — hist: ABSENT | exp: 102921
  - `teacher_salary.district_code` — hist: ABSENT | exp: ABSENT

**530423000670 — Juanita HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 88463
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `teacher_salary.average_base_per_fte` — hist: ABSENT | exp: 88463
  - `teacher_salary.district_code` — hist: ABSENT | exp: ABSENT

**530927001579 — Lewis and Clark HS**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 85992
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `teacher_salary.average_base_per_fte` — hist: ABSENT | exp: 85992
  - `teacher_salary.district_code` — hist: ABSENT | exp: ABSENT

**530393000610 — Washington Elementary**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 89375
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `teacher_salary.average_base_per_fte` — hist: ABSENT | exp: 89375
  - `teacher_salary.district_code` — hist: ABSENT | exp: ABSENT

**530000102795 — Thunder Mountain Middle**

- `schooldaylight`: ABSENT
- `schooldaylight_experiment`: 96367
- **Comparison:** absent in schooldaylight, present in schooldaylight_experiment

  Upstream / supporting context:
  - `teacher_salary.average_base_per_fte` — hist: ABSENT | exp: 96367
  - `teacher_salary.district_code` — hist: ABSENT | exp: ABSENT

### Vintage stamps in or near the variable block (per school, both DBs)

| School | Path | schooldaylight | schooldaylight_experiment |
| --- | --- | --- | --- |
| 530042000104 | `teacher_salary.metadata.dataset_year` | ABSENT | `'2023-24 final'` |
| 530042000104 | `teacher_salary.metadata.source` | ABSENT | `'OSPI Personnel Summary Report 2023-24 final, Table 19'` |
| 530042000104 | `teacher_salary.metadata.sheet` | ABSENT | ABSENT |
| 530423000670 | `teacher_salary.metadata.dataset_year` | ABSENT | `'2023-24 final'` |
| 530423000670 | `teacher_salary.metadata.source` | ABSENT | `'OSPI Personnel Summary Report 2023-24 final, Table 19'` |
| 530423000670 | `teacher_salary.metadata.sheet` | ABSENT | ABSENT |
| 530927001579 | `teacher_salary.metadata.dataset_year` | ABSENT | `'2023-24 final'` |
| 530927001579 | `teacher_salary.metadata.source` | ABSENT | `'OSPI Personnel Summary Report 2023-24 final, Table 19'` |
| 530927001579 | `teacher_salary.metadata.sheet` | ABSENT | ABSENT |
| 530393000610 | `teacher_salary.metadata.dataset_year` | ABSENT | `'2023-24 final'` |
| 530393000610 | `teacher_salary.metadata.source` | ABSENT | `'OSPI Personnel Summary Report 2023-24 final, Table 19'` |
| 530393000610 | `teacher_salary.metadata.sheet` | ABSENT | ABSENT |
| 530000102795 | `teacher_salary.metadata.dataset_year` | ABSENT | `'2023-24 final'` |
| 530000102795 | `teacher_salary.metadata.source` | ABSENT | `'OSPI Personnel Summary Report 2023-24 final, Table 19'` |
| 530000102795 | `teacher_salary.metadata.sheet` | ABSENT | ABSENT |

Vintage stamps uniform across the 5 sampled schools (within each DB) for every stamp path listed.

### Section B — Source file or API endpoint

- File: `phases/phase-3R/ingestion_data/table_15-40_school_district_personnel_summary_profiles_2023-24.xlsx` (note: also exists alongside the 2025-26 preliminary file in the same directory).
- Two candidate files on disk: the 2023-24 final and the 2025-26 preliminary. Phase 3R's salary loader was rerun on 2026-05-05 (`_run_salary_reingestion_2023-24.py`) to vintage-align downward to 2023-24 final per the May 5 R10 decision.
- Sheet: `Table19` (no space in 2023-24 file; with space in 2025-26 file).
- No SchoolYear column in the workbook; vintage is the filename and the loader's `YEAR_STR` constant.

### Section C — Pipeline filter / ingestion logic

`phases/phase-3R/experiment/_run_salary_reingestion_2023-24.py` line 217: `YEAR_STR = "2023-24 final"`. Reads `Table19` sheet (line 105-107) and parses base salary (col index 5). Each school inherits its district's average via `metadata.ospi_district_code`. Note: an earlier loader `_run_salary_ingestion.py` used the 2025-26 preliminary file and stamped `dataset_year = "2025-26 preliminary"`; the May 5 re-ingestion replaced that with 2023-24 final values across all docs.

### Vintage triangulation

| Source | Vintage |
|---|---|
| Empirical (`schooldaylight`) | `teacher_salary.metadata.dataset_year` ABSENT in all 5; `teacher_salary.metadata.source` ABSENT in all 5; `teacher_salary.metadata.sheet` ABSENT in all 5 |
| Empirical (`schooldaylight_experiment`) | `teacher_salary.metadata.dataset_year` = "2023-24 final"; `teacher_salary.metadata.source` = "OSPI Personnel Summary Report 2023-24 final, Table 19"; `teacher_salary.metadata.sheet` ABSENT in all 5 |
| Encoded by pipeline / ingestion script | `phases/phase-3R/experiment/_run_salary_reingestion_2023-24.py` line 217: `YEAR_STR = "2023-24 final"`. Reads `Table19` sheet (line 105-107) and parses base salary (col index 5). Each school inherits its district's average via `metadata.ospi_district_code`. Note: an earlier loader `_run_salary_ingestion.py` used the 2025-26 preliminary file and stamped `dataset_year = "2025-26 preliminary"`; the May 5 re-ingestion replaced that with 2023-24 final values across all docs. |
| Inferred from documentation | `variable_decision_matrix.md` rows 16-18 and A2: "OSPI Personnel Summary Reports 2023-24, Table 19 (Average Base Salary per 1.0 FTE), district-level". |

---

Sanity check: 16 variables emitted above; teacher_experience (variable 9) was covered in the prior round. Total = 17, matching `variable_decision_matrix.md` v1 set.
