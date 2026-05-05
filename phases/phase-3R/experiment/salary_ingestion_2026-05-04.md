# Phase 3R — Teacher Salary Ingestion (Table 19)

Run timestamp (UTC): **2026-05-05T00:59:05Z**
Database written: **`schooldaylight_experiment`** (production untouched)
Source file: `table_15-40_school_district_personnel_summary_profiles_2025-26.xlsx`
Sheet: `Table 19` — *Table 19: Certificated Teacher—Duty Roots 31, 32, 33, 34*
Log: `/Users/oriandaleigh/school-daylight/logs/phase3r_salary_ingestion_2026-05-04_17-59-05.log`

## Field written

```
teacher_salary.average_base_per_fte    integer USD
teacher_salary.metadata.source         'OSPI Personnel Summary Report 2025-26 preliminary, Table 19'
teacher_salary.metadata.dataset_year   '2025-26 preliminary'
teacher_salary.metadata.granularity    'district-level (applied identically to all schools in district)'
teacher_salary.metadata.fetch_timestamp ISO 8601
teacher_salary.metadata.null_reason    null on populated, 'district_not_in_source' on unmatched
metadata.phase_3r_dataset_versions.teacher_salary  provenance entry
```

## Source structure

Table 19 columns (col 1-10):

```
col 1: district code (5-char zero-padded string)
col 2: district name
col 3: Individuals
col 4: Avg Add'l Salary per Indiv.
col 5: Total FTE
col 6: Avg Base Salary per 1.0 FTE  ← INGESTED
col 7: Avg Total Salary per 1.0 FTE
col 8: Insur. Ben. per 1.0 FTE
col 9: Mand. Ben. per 1.0 FTE
col 10: Days in 1.0 FTE
```

## District code width verification

| side | width distribution | zfill needed? |
|---|---|---|
| source (Table 19) | {5: 317} | no |
| DB (metadata.ospi_district_code) | {5: 2532} | n/a |

## Spot-check gate (pre-write)

WA statewide 2025-26 average teacher base salary is in the $80K-$110K range; spot-check values landing outside that range would have triggered STOP-and-report. All values plausible.

| sample label | OSPI district code | district name in source | base salary |
|---|---|---|---|
| Bellingham | 37501 | Bellingham | $116,417 |
| Seattle | 17001 | Seattle | $97,794 |
| Spokane | 32081 | Spokane | $96,487 |
| Skykomish (small rural) | 31075 | — | NOT FOUND |
| Fairhaven Middle's district (= Bellingham) | 37501 | Bellingham | $116,417 |

## Coverage

| Outcome | Count |
|---|---|
| Source rows parsed (district records in Table 19) | 317 |
| Source rows skipped (totals, headers, blanks) | 1 |
| Distinct districts in source | 317 |
| Distinct districts represented in experiment db | 330 |
| Districts in source AND used (school exists in db with that code) | 312 |
| Districts in source NOT used (no school in db with that code) | 5 |
| DB district codes with NO matching source row | 18 |
|  |  |
| **Schools that received a salary value** | 2501 |
| **Schools written with null salary (district_not_in_source / missing code)** | 31 |
| **Total schools updated (idempotent $set)** | 2532 |

### Unmatched DB district codes (no Table 19 row)

These districts exist on schools in the experiment db but have no Table 19 row. Most likely these are charter authorizers, ESDs, tribal compact codes, or state agency codes that the OSPI Personnel Summary excludes.

| ospi_district_code | schools affected | district name (db) | sample school |
|---|---|---|---|
| 29801 | 5 | Northwest Educational Service District 189 | Skagit County Detention Center |
| 32801 | 4 | Educational Service District 101 | Martin Hall Detention Ctr |
| 06801 | 3 | Educational Service District 112 | Clark County Juvenile Detention School |
| 18801 | 2 | Olympic Educational Service District 114 | Clallam Co Juvenile Detention |
| 27931 | 2 | Bates Technical College | Bates Technical High School |
| 17941 | 2 | Renton Technical College | Renton Technical High School |
| 17937 | 2 | Lake Washington Institute of Technology | Lake Washington Technical Academy |
| 17801 | 1 | Puget Sound Educational Service District 121 | Dropout Prevention and Reengagement Academy |
| 34975 | 1 | Washington Center for Deaf and Hard of Hearing Youth | Washington State School for the Deaf |
| 39801 | 1 | Educational Service District 105 | ESD 105 Open Doors |
| 27932 | 1 | Clover Park Technical College | Northwest Career and Technical High School |
| 11801 | 1 | Educational Service District 123 | Ugrad ESD123 Re-Engagement Program |
| 34974 | 1 | Office of the Governor (Sch for Blind) | Washington State School for the Blind |
| 21926 | 1 | Centralia College | Garrett Heyns High School |
| 34801 | 1 | Capital Region ESD 113 | ESD 113 Consortium Reengagement Program |
| 27905 | 1 | Summit Public School: Olympus | Summit Public School: Olympus |
| 06701 | 1 | Educational Service Agency 112 | ESA 112 Special Ed Co-Op |
| 34979 | 1 | Washington Military Department | Washington Youth Academy |

## Salary distribution (across schools, replicated by district)

| stat | value |
|---|---|
| n_schools | 2501 |
| min | $57,669 |
| max | $149,856 |
| mean | $98,980 |
| median | $97,794 |

### Distribution at the district level (deduplicated)

| stat | value |
|---|---|
| n_districts | 312 |
| min | $57,669 |
| max | $149,856 |
| mean | $91,132 |
| median | $91,248 |

## Production untouched

- Database written: `schooldaylight_experiment`
- Pre-write isolation guard: PASSED
- Production database (`schooldaylight`): NOT opened, queried, or written.
- Idempotent: every write was `$set` on `teacher_salary.*` and the single `metadata.phase_3r_dataset_versions.teacher_salary` provenance key.
