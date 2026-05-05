# Phase 3R Prompt 2 — API Ingestion Results

Run timestamp (UTC): **2026-05-05T00:19:03Z**
Database written: **`schooldaylight_experiment`** (production untouched)
Document count: **2532**
Log file: `/Users/oriandaleigh/school-daylight/logs/phase3r_api_ingestion_2026-05-04_17-19-03.log`

Task 2 (teacher qualification — masters degree percentage) was DROPPED per builder ruling. See "Task 2 — Investigation evidence and v2 path" section below for the full evidence trail.

## Methodology decisions applied

**Blocker 1 / Finding 1 — bin midpoints.** Each bin's published range is used (e.g. `25.0-29.9` → `27.45`). The original "cap at 25" rule was dropped because all observed bins are finite-range; no open-ended top bin exists in the 2024-25 data. Bins observed: `0.0 - 4.9` through `55.0 - 59.9`, plus `Not Reported`.

**Blocker 1 / Finding 2 — `Not Reported` handling.** Renormalized to reported-bin weight sum (drop from both numerator and denominator). Schools with >10% Not Reported get `high_unreported_flag: true`.

**Concern 4 — Task 4 denominators.** OSPI-sourced counts (ELL, SPED, migrant, homeless) divided by `demographics.ospi_total`; CCD-sourced white count divided by `enrollment.total`. Vintage-matched within each rate (OSPI 2023-24 / OSPI 2023-24 and CCD 2023-24 / CCD 2023-24).

**Concern 5 — join key.** Composite `(metadata.ospi_district_code, metadata.ospi_school_code)` to source `(leacode, schoolcode)` or `(districtcode, schoolcode)` depending on dataset.

**Concern 6 — charters ingested.** All 2,532 schools eligible for data, including 17 charter schools.

## Task 1 — Graduation rates (76iv-8ed4)

- API endpoint: `https://data.wa.gov/resource/76iv-8ed4.json`
- Filter: `organizationlevel=School`, `schoolyear=2023-24`, `studentgroup=All Students`
- Source rows fetched: **3007**
- Source rows whose (district, school) didn't match any school in the experiment db: **588**
- Schools updated: **2532**

| Outcome | Count | % of total |
|---|---|---|
| HS-eligible (level_group=High OR grade_span.high=12) | 829 | 32.7% |
| HS with at least one cohort rate | 397 | 15.7% |
| HS with NO graduation data (rate fields null) | 432 | 17.1% |
| Non-HS (rate fields null with not_applicable_reason) | 1703 | 67.3% |

Distribution of populated graduation rates:

| field | n_non_null | min | max | mean | median | null_count_in_collection |
|---|---|---|---|---|---|---|
| graduation_rate.cohort_4yr | 359 | 0.0435 | 0.9830 | 0.7681 | 0.8600 | 2173 |
| graduation_rate.cohort_5yr | 347 | 0.0195 | 0.9900 | 0.7882 | 0.8900 | 2185 |

## Task 2 — Teacher qualification (DROPPED per builder Path A)

Per builder ruling, Task 2 was dropped from v1 to avoid creating a redundant tenure variable alongside Task 3's experience derivation. No write to `teacher_qualification.*` was performed. Two-step investigation evidence is preserved here for the v2-path note.

### Step 1: Personnel Summary XLSX (`table_15-40_school_district_personnel_summary_profiles_2025-26.xlsx`)

All 39 sheets (Tables 15 through 40) were inspected. Every sheet uses the same 10-column template focused on FTE counts and salary:

```
District code | District Name | Individuals | Avg Add'l Salary per Indiv. |
Total FTE | Base Salary | Total Salary | Insur. Ben. | Mand. Ben. |
Days in 1.0 FTE
```

Definitive workbook-wide substring scan for `master|doctor|degree|baccal|bachelor|highest-degree|education-level`: **zero matches anywhere in the workbook.** The Personnel Summary tables aggregate S-275 raw data by FTE/headcount/salary only; they do not surface the credential-level dimension that exists in the underlying S-275 personnel records.

### Step 2: data.wa.gov catalog probe

| dataset_id | name | resource status | metadata status |
|---|---|---|---|
| t9ya-d7ak | Educator Characteristics | HTTP 404 | HTTP 404 |
| 3543-y5sg | Educator Educational Level | HTTP 404 | HTTP 404 |
| wsha-faww | Educational Attainment Level | (not probed) | HTTP 404 |
| wc8d-kv9u | Report Card Teacher Qualification Summary 2021-22 to 2024-25 | alive | alive — but only 'Inexperienced Status' / 'Experienced Status' values |
| e28j-uhwn | Report Card Teacher Qualification Summary 2017-18 to 2020-21 | alive | alive — same schema as wc8d-kv9u |

Catalog searches for `certification`, `credential`, `S-275`, `highest degree teacher`, `educator master`, `OSPI educator` surfaced no live data.wa.gov dataset carrying school-level educator credential / education-level data. The three datasets whose names match what we want are all withdrawn at the resource level.

### v2 path note

OSPI publishes annual S-275 raw extracts (CSV/XLSX) outside data.wa.gov, and those rows include a Highest_Degree column at the personnel level. Aggregating Highest_Degree to school level is the v2 candidate path for restoring the credential dimension. v1 ships without it.

## Task 3 — Teacher experience (bdjb-hg6t)

- API endpoint: `https://data.wa.gov/resource/bdjb-hg6t.json`
- Filter: `organizationlevel=School`, `schoolyear=2024-25`
- Source rows fetched: **30472**
- Source rows that didn't match any school in experiment db: **169**
- Schools updated: **2532**

Distinct bins observed in source data (for transparency):

- `0.0 - 4.9` → midpoint = 2.45
- `10.0 - 14.9` → midpoint = 12.45
- `15.0 - 19.9` → midpoint = 17.45
- `20.0 - 24.9` → midpoint = 22.45
- `25.0 - 29.9` → midpoint = 27.45
- `30.0 - 34.9` → midpoint = 32.45
- `35.0 - 39.9` → midpoint = 37.45
- `40.0 - 44.9` → midpoint = 42.45
- `45.0 - 49.9` → midpoint = 47.45
- `5.0 - 9.9` → midpoint = 7.45
- `50.0 - 54.9` → midpoint = 52.45
- `55.0 - 59.9` → midpoint = 57.45
- `Not Reported` → midpoint = None

| Outcome | Count |
|---|---|
| Schools with computed `average_years_derived` | 2317 |
| Schools with no bin rows in source (null + null_reason='no_bin_rows') | 201 |
| Schools with `high_unreported_flag: true` (>10% Not Reported) | 202 |

### Validation table (5 sample schools, run during validation gate)

| School | District | bin rows | weight sum | average_years_derived |
|---|---|---|---|---|
| Fairhaven Middle | Bellingham | 13 | 0.977 | 13.68 |
| Washington Elementary | Mead | 13 | 0.971 | 10.46 |
| Franklin Elementary | Pullman | 13 | 0.998 | 14.92 |
| Delong Elementary | Spokane | 13 | 1.000 | 16.45 |
| Lewis and Clark High | Spokane | 13 | 0.941 | 8.39 (after renormalization) |
| Clark Co Juvenile Detention | ESD 112 | 0 | 0.000 | null (no bin rows) |

Renormalization makes the Lewis and Clark figure (originally 7.90 before renormalization) consistent with the rest of the cohort.

| field | n_non_null | min | max | mean | median | null_count |
|---|---|---|---|---|---|---|
| teacher_experience.average_years_derived | 2317 | 2.4500 | 42.4500 | 13.6150 | 13.4745 | 215 |

## Task 4 — Derived rates from existing counts

- Schools updated (rates set on every doc, with null where input is null): **2532**

**Denominator confirmation.** `enrollment.total` is CCD fall membership (point-in-time, ~Oct 1) per `pipeline/02_load_enrollment.py`. `demographics.ospi_total` is OSPI All Students (same year vintage). Both are point-in-time counts; neither is annual average. STOP-and-report condition NOT triggered.

Distribution summaries:

| field | n_non_null | min | max | mean | median | null_count |
|---|---|---|---|---|---|---|
| derived.ell_pct | 2380 | 0.0000 | 0.9731 | 0.1299 | 0.0812 | 152 |
| derived.sped_pct | 2380 | 0.0000 | 0.9939 | 0.1792 | 0.1617 | 152 |
| derived.migrant_pct | 2380 | 0.0000 | 0.6667 | 0.0226 | 0.0000 | 152 |
| derived.homelessness_pct | 2380 | 0.0000 | 0.6136 | 0.0399 | 0.0268 | 152 |
| derived.race_pct_non_white | 2433 | 0.0000 | 1.0000 | 0.4954 | 0.4730 | 99 |

**[0, 1] range validation.**

- Total non-null computed rates across all 5 fields: **11953**
- Rates outside [0, 1]: **0** (0.00% of non-null)
- In-range fraction: **100.00%** (target ≥ 99%; PASS)

## Task 5 — Chronic absenteeism null overlap diagnostic

READ-ONLY analysis. No writes performed for this task.

| bucket | count |
|---|---|
| `derived.chronic_absenteeism_pct` null total | 571 |
| Already in exclusion union (school_exclusions.yaml ∪ Phase 3R SKIP) | 62 |
| NOT in exclusion union (additional coverage gap) | 509 |
|  |  |
| Reference: school_exclusions.yaml | 78 |
| Reference: Phase 3R SKIP | 48 |
| Reference: union | 120 |

**Additional coverage gap = 509 schools.** Distribution:

### By `derived.level_group`

| level_group | count |
|---|---|
| Elementary | 187 |
| High | 134 |
| Other | 122 |
| Middle | 66 |

### By school type / charter status

| school_type | count |
|---|---|
| Regular School | 347 |
| Alternative School | 96 |
| Special Education School | 57 |
| Career and Technical School | 9 |

### By district size (count of schools per district within experiment db)

| district size bucket | count |
|---|---|
| 1-4 | 83 |
| 5-9 | 100 |
| 10-19 | 121 |
| 20-49 | 196 |
| 50+ | 9 |
| unknown | 0 |

## Task 6 — Document-root provenance metadata

- Schools updated: **2532**

Each touched document now carries:

- `metadata.phase_3r_ingestion_timestamp` = ISO 8601 of this run
- `metadata.phase_3r_dataset_versions` = mapping of new field name → {source, year}

```json
{
  "graduation_rate": {
    "source": "data.wa.gov 76iv-8ed4",
    "year": "2023-24"
  },
  "teacher_experience": {
    "source": "data.wa.gov bdjb-hg6t",
    "year": "2024-25"
  },
  "derived.ell_pct": {
    "source": "OSPI demographics 2023-24",
    "year": "2023-24"
  },
  "derived.sped_pct": {
    "source": "OSPI demographics 2023-24",
    "year": "2023-24"
  },
  "derived.migrant_pct": {
    "source": "OSPI demographics 2023-24",
    "year": "2023-24"
  },
  "derived.homelessness_pct": {
    "source": "OSPI demographics 2023-24",
    "year": "2023-24"
  },
  "derived.race_pct_non_white": {
    "source": "CCD enrollment 2023-24",
    "year": "2023-24"
  }
}
```

## Issues for builder review

- **`high_unreported_flag` triggered on 202 schools** (8.7% of those with computed averages). Renormalization assumption may be weaker for these; downstream methodology should review.
- **Chronic-absenteeism additional coverage gap: 509 schools.** These are schools with `chronic_absenteeism_pct=null` that are NOT on either exclusion list. The dominant grade_level_category and school-type buckets are listed in Task 5; many appear to be schools without tested grades (the null pattern from Phase 3R diagnostics).
- **432 HS-eligible schools have no graduation data** in the source. Likely small / new / closed schools or alternative programs. Stored as null with metadata.not_applicable_reason=null (reason is null because they ARE HS-eligible — the null is a coverage gap, not an inapplicability).
- **No 5-year cohort rates for some schools that have a 4-year rate (or vice versa).** 4yr non-null = 359, 5yr non-null = 347. Asymmetric coverage is expected because the 5-year cohort lags by one academic year.
- **Task 2 was dropped.** Methodology now has zero teacher-credential variables; only one teacher-tenure variable. `methodology_revisions_pending.md` R1 documents the v2 path (S-275 raw extracts).

## Production untouched

- Database written: `schooldaylight_experiment` (contains substring "experiment")
- Pre-write isolation guard: PASSED (asserted before each `bulk_write`)
- Production database (`schooldaylight`): NOT opened, NOT queried, NOT written.

Idempotency: every write was a `$set` on a specific dotted path. Rerunning this script will overwrite the same paths cleanly. No documents were created (`upsert=False` is the pymongo default; all UpdateOne ops match by `_id` against existing docs).
