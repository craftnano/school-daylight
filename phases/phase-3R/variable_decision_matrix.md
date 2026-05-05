# v1 Variable Decision Matrix

**Purpose:** Document the v1 similarity variable set as deviations from the Nebraska Department of Education's reference methodology. Each row records a Nebraska variable and the v1 disposition (Include, Exclude, Substitute), with reasoning concentrated on the deviations.

**Status:** Locked for v1 commit. Empirical confirmations (homelessness availability, expulsion variability, redundancy structure) reported in `methodology_inspection.md` after methodology computation.

**Reference:** Nebraska Department of Education. *Methodology to Compare Districts and Schools: A Technical Report.* January 18, 2019. Variable set drawn from Table 1, p. 5.

---

## Nebraska variables (27)

| # | Nebraska Variable | Status | WA Implementation | Reasoning | Reviewer Q |
|---|---|---|---|---|---|
| 1 | Membership (enrollment) | Include | Total enrollment, OSPI Report Card 2023-24 (already ingested) — `enrollment.total` | Direct port. | — |
| 2 | Attendance Rate | Include | Chronic absenteeism rate, OSPI Report Card 2023-24, school-level — `derived.chronic_absenteeism_pct` | Substituted variable form: chronic absenteeism rate replaces attendance rate. Chronic absenteeism is the federal accountability measure already in the WA data schema and briefing layer; using it keeps the methodology consistent with the existing flag system. Z-score standardization handles post-COVID level shift; redundancy audit will determine whether the variable adds independent signal beyond FRL and demographics. | — |
| 3 | Graduation Rate (4-year) | Include | data.wa.gov Report Card Graduation 2023-24, school-level all-students — `graduation_rate.cohort_4yr` | Direct port. HS-only per Nebraska's own treatment; excluded from elementary and middle school similarity calculations. | — |
| 4 | FRL Rate | Include | OSPI 2023-24 (already ingested) — `demographics.frl_pct` | Direct port. Limitations documented in harm register (CEP, post-COVID waivers); WA distribution reviewed and shows no widespread CEP distortion. | Q1 |
| 5 | Minority Rate (% non-white) | Include | OSPI 2023-24 (already ingested), single percent non-white — `derived.race_pct_non_white` (computed as `1 − enrollment.by_race.white / enrollment.total`) | Direct port. Single-variable form matches Nebraska and Texas; multi-component vector deferred to v2 pending reviewer input. | Q2a |
| 6 | Homeless Rate | Include | OSPI Report Card 2023-24, school-level (availability to be confirmed during ingestion) — `derived.homelessness_pct` (computed as `homeless_count / ospi_total`) | Direct port. WA-specific judgment that urban housing dynamics make this an independent signal beyond FRL: low-income but stably housed families and doubled-up homeless families have materially different educational stability profiles, especially in King and Pierce counties. If field is not available at school level, drops to district level or excluded with reason code. | — |
| 7 | LEP Rate | Include | OSPI 2023-24 (already ingested); WA term is EL/ML, same variable — `derived.ell_pct` (computed as `ell_count / ospi_total`) | Direct port. | — |
| 8 | Migrant Rate | Include | OSPI 2023-24 (already ingested) — `derived.migrant_pct` (computed as `migrant_count / ospi_total`) | Direct port. Possible high correlation with FRL in WA agricultural areas; redundancy audit will determine retention. | Q2a |
| 9 | ELA Percent Proficient | Exclude | — | Excluded from similarity to avoid systematic attenuation of the academic flag (matching schools partly by achievement and then comparing achievement to peers compresses the comparison in both directions). Aligned with Texas methodology. Empirically tested in achievement sensitivity analysis. | Q2b |
| 10 | Math Percent Proficient | Exclude | — | Same as row 9. | Q2b |
| 11 | Science Percent Proficient | Exclude | — | Same as row 9. | Q2b |
| 12 | Teachers With Masters Percent | Include | data.wa.gov Report Card Teacher Qualification Summary 2024-25, school-level | Direct port. | — |
| 13 | Average Years Teaching Experience | Include | data.wa.gov Report Card Teacher Experience Distribution 2022-23 (most recent available), school-level — `teacher_experience.average_years_derived` (actual ingestion: 2024-25 from `bdjb-hg6t` with bin-midpoint derivation; brief wording preserved as-is per `methodology_revisions_pending.md`) | Direct port. Year vintage one year older than other variables; precedent in Nebraska's own data-vintage handling (Census 2010 alongside NDE 2016-17 data). | — |
| 14 | Unduplicated Suspensions | Exclude | — | Excluded from similarity. WA discipline policies are partly standardized at the state level (RCW 28A.345.090, WAC 392-400) but implementation varies meaningfully across districts, particularly around restorative practices adoption. Published evidence (Augustine et al. 2018 RAND; cited in WSIPP) shows policy choice produces measurable suspension rate differences after controlling for school context. Matching on suspension count partly matches on policy implementation rather than structural similarity. Surfaced descriptively in briefing; not in similarity. | — |
| 15 | Unduplicated Expulsions | Exclude | — | Nebraska themselves dropped this from school-level files for low variability ("many zero values"). Same expected in WA; empirical confirmation of variability reported in methodology output. Suspension-level arguments (policy variation) apply to expulsions with greater force. | — |
| 16 | Land Valuation | Substitute | Replaced by Average Teacher Salary (see additions table) — `teacher_salary.average_base_per_fte` | See row 17. | Q5 |
| 17 | Per Pupil Cost by ADM | Substitute | Replaced by Average Teacher Salary — `teacher_salary.average_base_per_fte` | Post-McCleary WA finance structure differs materially from Nebraska's. State funds approximately 73% of district revenue; local levies are capped at the lesser of $2,606 per pupil or $2.50 per $1,000 assessed valuation, creating a structural distinction between revenue-capped and rate-capped districts; regionalization factors compound capacity differences. Average teacher salary captures the substantive post-McCleary mechanism (largest expenditure category, where regionalization and levy supplementation flow most directly), is intuitively meaningful to parents, and is available at no marginal data engineering cost from the OSPI Personnel Summary Reports already pulled for teacher characteristics. References: Knight et al. (2023, 2024); WA Citizen's Guide to K-12 Finance 2024. | Q5 |
| 18 | Grand Total of All Receipts | Substitute | Replaced by Average Teacher Salary — `teacher_salary.average_base_per_fte` | See row 17. | Q5 |
| 19 | Median Household Income | Include | Census ACS B19013_001E at district geography (already ingested) — `census_acs.median_household_income.value` | Direct port. | — |
| 20 | Per Capita Income | Include | Census ACS B19301_001E (already ingested) — `census_acs.per_capita_income.value` | Direct port. Likely high correlation with row 19; redundancy audit will determine retention or consolidation. | — |
| 21 | Gini Index | Include | Census ACS B19083_001E (already ingested) — `census_acs.gini_index.value` | Direct port. | — |
| 22 | Bachelor's Degree % (25+) | Include | Census ACS S1501_C02_015E (already ingested) — `census_acs.bachelors_or_higher_pct_25plus.value` | Direct port. | — |
| 23 | Labor Force Participation Rate | Include | Census ACS S2301 (already ingested) — `census_acs.labor_force_participation_rate_16plus.value` | Direct port. | — |
| 24 | Unemployment Rate | Include | Census ACS S2301 (already ingested) — `census_acs.unemployment_rate_16plus.value` | Direct port. | — |
| 25 | Total Population | Include | Census ACS B01003_001E (already ingested; using ACS rather than Census 2010 as more current) — `census_acs.total_population.value` | Direct port. | — |
| 26 | Land Area | Include | TIGER Gazetteer ALAND (already ingested) — `census_acs.land_area_sq_miles.value` | Direct port. | — |
| 27 | Population Density | Include | Computed B01003 / ALAND (already ingested) — `census_acs.population_density_per_sq_mile.value` | Direct port. | — |

## Additions beyond Nebraska (2)

| # | Variable | Source | Reasoning | Reviewer Q |
|---|---|---|---|---|
| A1 | SPED Percentage | OSPI 2023-24 (already ingested) — `derived.sped_pct` (computed as `sped_count / ospi_total`) | Borrowed from Texas's seven-variable approach. Nebraska does not include SPED separately. Standard demographic variable capturing disability service intensity; relevant for similarity in WA where SPED concentration varies materially across schools. | — |
| A2 | Average Teacher Salary | OSPI Personnel Summary Reports 2023-24, Table 1 (Average Base Salaries per 1.0 FTE), district-level — `teacher_salary.average_base_per_fte` (actual ingestion: 2025-26 preliminary, Table 19; brief wording preserved as-is per `methodology_revisions_pending.md`) | Substitutes for rows 16-18. See row 17 reasoning. District-level applied identically to all schools in district, consistent with Nebraska's own treatment of district-level finance variables and with Census ACS variables already in the methodology. | Q5 |

## v1 Variable Count

21 variables total: 19 Nebraska variables ported (10 NDE-sourced plus 9 Census ACS) plus 2 additions (SPED, average teacher salary). Three Nebraska variables substituted, five excluded.

This is a leaner Nebraska adaptation rather than a Texas-style minimal set. Original Phase 3R methodology brief committed to 15-16 variables; the growth comes from explicit additions (homelessness, attendance/chronic absenteeism, teacher master's, teacher experience, graduation, teacher salary) each documented above.
