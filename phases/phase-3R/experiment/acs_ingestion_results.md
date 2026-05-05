# Phase 3R — ACS Ingestion Results (experiment database)

Run date (UTC): **2026-05-04T06:25:42Z**
Target database: **schooldaylight_experiment** (production untouched)
Data vintage: **acs5_2019_2023** (ACS 5-year, 2019-2023 estimates)

## API endpoints used

- ACS base tables (B19013, B19301, B19083, B01003): `https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,B19083_001E,B19083_001M,B01003_001E,B01003_001M&for=school+district+(unified):*&in=state:53`
- ACS subject tables (S1501, S2301): `https://api.census.gov/data/2023/acs/acs5/subject?get=NAME,S1501_C02_015E,S1501_C02_015M,S2301_C02_001E,S2301_C02_001M,S2301_C04_001E,S2301_C04_001M&for=school+district+(unified):*&in=state:53`
- TIGER 2023 Unified School District Gazetteer (ALAND_SQMI): `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip`

All three endpoints fetched once at run start. No per-school API calls.
Census API is free and public; no API key used (volume well under the 500 calls/day no-key threshold).

## Variable list with confirmed Census codes

| MongoDB key under `census_acs` | Source code | Description |
|---|---|---|
| median_household_income | B19013_001E | Median household income (past 12 months, 2023 dollars) |
| per_capita_income | B19301_001E | Per capita income (past 12 months, 2023 dollars) |
| gini_index | B19083_001E | Gini index of income inequality |
| total_population | B01003_001E | Total population |
| bachelors_or_higher_pct_25plus | S1501_C02_015E | % age 25+ with Bachelor's degree or higher |
| labor_force_participation_rate_16plus | S2301_C02_001E | Labor force participation rate, age 16+ |
| unemployment_rate_16plus | S2301_C04_001E | Unemployment rate, age 16+ |
| land_area_sq_miles | TIGER 2023 ALAND_SQMI | District land area, square miles |
| population_density_per_sq_mile | computed | total_population / land_area_sq_miles |

Each variable on every matched school is stored as `{value, moe, census_code}` (or `{value, source}` for TIGER, `{value, computed_from}` for the derived density). Suppressed ACS values (negative annotation codes) become `value: null` with `suppressed: true`.

## Schema written under `census_acs._meta`

- `vintage`: `"acs5_2019_2023"`
- `fetched_at`: ISO 8601 UTC timestamp of this run
- `acs_base_api_url`, `acs_subject_api_url`, `tiger_gazetteer_url`: provenance
- `district_geoid`: 7-char LEAID used for the join (null on SKIP schools)
- `district_geoid_source`: `"district.nces_id"`
- `unmatched_reason`: null on matched schools; one of the SKIP reason codes otherwise

## Coverage

| Outcome | Count | % of total |
|---|---|---|
| Matched USD → full Census payload written | 2484 | 98.1% |
| Skipped (with documented reason code) | 45 | 1.8% |
| Unrecognized (skipped with placeholder reason — needs review) | 3 | 0.1% |
| **Total schools in experiment db** | 2532 | 100.0% |

WA Unified School Districts pulled from ACS: **295** (286 of which actually appear as `district.nces_id` on a school in the experiment db; the other 9 are USDs with no enrolled schools in this dataset).

## Skip breakdown by reason code

| unmatched_reason | schools skipped | of those, also in school_exclusions.yaml |
|---|---|---|
| institutional_facility_not_comparable | 10 | 5 |
| regional_alternative_program_not_comparable | 11 | 1 |
| statewide_specialty_school_not_comparable | 6 | 0 |
| tribal_community_context_not_capturable_v1 | 1 | 0 |
| charter_pending_district_assignment | 17 | 0 |

**Total SKIP overlap with `school_exclusions.yaml`: 6 of 45 skipped schools (13%)** are already excluded from Phase 3 peer matching.

### Unrecognized skip schools (need builder follow-up)

These schools' `district.nces_id` doesn't match a WA USD geography AND their name didn't match any of the builder-supplied SKIP rules. They've been written with `unmatched_reason="unclassified_pending_review"` and null variable fields.

| _id | name | district.nces_id |
|---|---|---|
| 530001501016 | Washington State School for the Deaf | 5300015 |
| 530001203521 | Ugrad ESD123 Re-Engagement Program | 5300012 |
| 530031802385 | Washington State School for the Blind | 5300318 |

### `institutional_facility_not_comparable` (10 schools)

Already in `school_exclusions.yaml`: **5** of 10.

| _id | name | in school_exclusions.yaml? |
|---|---|---|
| 530000702914 | Clallam Co Juvenile Detention | yes |
| 530000503407 | Clark County Juvenile Detention School | no |
| 530000502917 | Cowlitz County Youth Services Center | no |
| 530000702927 | Kitsap Co Detention Ctr | yes |
| 530001002919 | Martin Hall Detention Ctr | no |
| 530000802921 | Skagit County Detention Center | yes |
| 530000802095 | Snohomish Detention Center | yes |
| 530001002930 | Spokane Juvenile Detention School | no |
| 530001002929 | Structural Alt Confinement School | no |
| 530000802923 | Whatcom Co Detention Center | yes |

### `regional_alternative_program_not_comparable` (11 schools)

Already in `school_exclusions.yaml`: **1** of 11.

| _id | name | in school_exclusions.yaml? |
|---|---|---|
| 530001403585 | Bates Technical College - Open Doors | no |
| 530000603748 | Dropout Prevention and Reengagement Academy | no |
| 530001303670 | ESD 105 Open Doors | no |
| 530000503538 | ESD 112 Open Doors Reengagement | no |
| 530001103422 | ESD 113 Consortium Reengagement Program | no |
| 530001603208 | Garrett Heyns High School | yes |
| 530001003583 | NEWESD 101 Open Doors | no |
| 530000803609 | Open Doors - Youth Reengagement Program | no |
| 530031303403 | Open Doors at LWIT | no |
| 530000802755 | Pass Program | no |
| 530032503687 | YouthSource and RTC | no |

### `statewide_specialty_school_not_comparable` (6 schools)

Already in `school_exclusions.yaml`: **0** of 6.

| _id | name | in school_exclusions.yaml? |
|---|---|---|
| 530001403082 | Bates Technical High School | no |
| 530034003593 | ESA 112 Special Ed Co-Op | no |
| 530031303265 | Lake Washington Technical Academy | no |
| 530001703209 | Northwest Career and Technical High School | no |
| 530032503695 | Renton Technical High School | no |
| 530032403412 | Washington Youth Academy | no |

### `tribal_community_context_not_capturable_v1` (1 schools)

Already in `school_exclusions.yaml`: **0** of 1.

| _id | name | in school_exclusions.yaml? |
|---|---|---|
| 530032803493 | Chief Kitsap Academy | no |

### `charter_pending_district_assignment` (17 schools)

Already in `school_exclusions.yaml`: **0** of 17.

| _id | name | in school_exclusions.yaml? |
|---|---|---|
| 530034903783 | Cascade Public Schools | no |
| 530034703723 | Catalyst Public Schools | no |
| 530035403782 | Impact Public Schools | no |
| 530034503653 | Impact Public Schools | no |
| 531017203905 | Impact | Black River Elementary | no |
| 530034803749 | Impact | Salish Sea Elementary | no |
| 530033903495 | Innovation High School | no |
| 530035103831 | Intergenerational High School | no |
| 530035003770 | Lumen High School | no |
| 530035203807 | Pinnacles Prep Charter School | no |
| 530033503533 | Rainier Prep | no |
| 530034203602 | Rainier Valley Leadership Academy | no |
| 531017103924 | Rooted School Washington | no |
| 530033703539 | Spokane International Academy | no |
| 530034303611 | Summit Public School: Atlas | no |
| 530033303541 | Summit Public School: Olympus | no |
| 530033403510 | Summit Public School: Sierra | no |

## Sanity check — 5 schools across WA

Reproducible via `random.seed(20260503)`. Picks intentionally span the income/density spectrum (Seattle metro, Eastside, Spokane, coastal Grays Harbor, NW WA / Bellingham) so values can be eyeballed for plausibility.

| School | District | Med HH inc | Per cap inc | Gini | Bach+ % | LFP % | Unemp % | Total pop | Land sqmi | Pop/sqmi |
|---|---|---|---|---|---|---|---|---|---|---|
| Cedar Park Elementary School | Seattle School District No. 1 | 121,962 | 82,491 | 0.4878 | 67.5 | 74.1 | 4.2 | 741,812 | 85.5 | 8,676.9 |
| Cherry Crest Elementary School | Bellevue School District | 160,669 | 97,133 | 0.4922 | 72.0 | 67.1 | 4.0 | 145,918 | 33.3 | 4,386.1 |
| Trentwood School | East Valley School District (Spokane) | 72,668 | 37,166 | 0.4073 | 20.4 | 64.4 | 3.7 | 29,207 | 91.4 | 319.6 |
| Robert Gray Elementary | Aberdeen School District | 58,872 | 30,389 | 0.4396 | 16.1 | 57.0 | 7.9 | 21,444 | 68.1 | 314.8 |
| Sunnyland Elementary School | Bellingham School District | 72,424 | 44,747 | 0.4710 | 47.4 | 65.2 | 5.3 | 113,215 | 90.9 | 1,245.4 |

## Issues encountered

- **Suppressed ACS values across all 295 districts × 7 ACS variables: 3 cells.** Stored as `value: null` with `suppressed: true` per the project's data-integrity rule (suppressed ≠ zero).
- **TIGER ALAND_SQMI missing for: 0 of 295 districts.** Population density null on those districts as a result.
- **No HTTP errors.** All three external fetches (2× ACS, 1× TIGER) succeeded on first attempt.
- **3 schools could not be auto-classified into a SKIP reason** — see table above.

## Production untouched

- Database written: `schooldaylight_experiment` (contains substring "experiment")
- Pre-write isolation guard: PASSED
- Production database (`schooldaylight`): NOT opened, NOT queried, NOT written.
