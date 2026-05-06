# Methodology Review Brief

**Audience:** Independent statistical reviewer (academic sociologist or quantitative methods researcher).

**Project context:** School Daylight is a non-commercial civic transparency project that publishes multidimensional briefings about Washington state K-12 public schools. Briefings do not produce a single rating; they present structured data across academic, climate/safety, resource, access, and demographic dimensions. The methodology decisions documented here govern how comparisons between schools are constructed.

**Status:** Draft for reviewer evaluation. Open questions Q1 through Q6 are embedded inline in the relevant sections (Q2d is retired and superseded by Q6). Sections 1 and the inline question sections are complete. Sections 2 through 4 carry placeholder content for downstream methodology work and are flagged as not yet ready for review.

**Notes for the reviewer.** Three items reflect implementation decisions made between the original framework commit and the methodology computation that warrant explicit framing rather than discovery in the appendix:

1. *Teacher master's degree percentage is excluded due to data availability, not methodological choice.* No school-level master's-degree or highest-degree data is queryable on data.wa.gov. Three candidate Educator By Level datasets returned HTTP 404 (retired or migrated to Tableau portal). The OSPI teacher qualification dataset publishes only Inexperienced and Experienced status, and the OSPI Personnel Summary XLSX has no credential breakdown across its 39 sheets. The variable would be included if available; a v2 path parsing S-275 raw personnel extracts (published outside data.wa.gov) is identified.

2. *Three Census ACS variables are consolidated out after the redundancy audit (Path C).* Per capita income, bachelor's degree percentage of the population aged 25 and over, and total population were dropped following empirical correlations of r > 0.85 within their clusters. Section 1.5.1 documents the consolidation reasoning. Section 1.5.2 documents the residual correlations that remain after consolidation and identifies Mahalanobis distance as a v2 escalation path under three explicit trigger conditions, rather than as a parallel alternative to consolidation.

3. *Two residual correlations remain after consolidation and are documented as known WA-specific limitations.* Race composition correlates with English-learner percentage at r ≈ +0.78 to +0.80, a structural feature of WA's Hispanic agricultural-worker and refugee resettlement geography rather than methodological double-counting. FRL correlates with median household income at r ≈ -0.76 at the Middle level only, partly a smaller-n artifact and partly genuine catchment-district economic geography overlap. Both are retained rather than driving further consolidation; Section 1.5.2 documents the reasoning.

4. *Average teacher salary is committed at the OSPI Personnel Summary 2023-24 final vintage (Table 19, district-level Average Base Salary per 1.0 FTE).* Salary was re-ingested between the original framework commit and the methodology computation to align the variable's vintage with the rest of the v1 set; references to "Table 1" in earlier draft language are superseded.

**Reading guide:** Each section presents the v1 methodology decision with reasoning, alternatives considered, and (where applicable) an empirical sensitivity analysis plan or finding. Open questions for the reviewer appear inline at the end of each relevant subsection, marked with a callout. The variable decision matrix is included as Appendix A.

---

## 1. Peer School Identification

### 1.1 Decision and framework

For v1, School Daylight identifies peer schools using nearest-neighbor matching with Euclidean distance on standardized variables, per-level segmentation, and a fixed cohort size of K=20. Geographic distance is not incorporated into the similarity calculation.

The framework is adopted from the IES / REL Central guide *A Guide to Identifying Similar Schools to Support School Improvement* (2021), with the specific implementation drawing from the Nebraska Department of Education's published methodology (2019). The procedure: schools are first segmented by level (Elementary, Middle, High, Other); within each level, a similarity vector is constructed from a set of standardized variables; each variable is z-score standardized; Euclidean distance is computed between every pair of schools at the same level; for each school, the K=20 closest schools constitute its peer cohort.

**Alternatives considered.** Cluster-based grouping (NYSED) was rejected for the boundary-effect problem that Nebraska explicitly cites and NYSED itself acknowledges. Hard-bin matching (the previous School Daylight implementation) was rejected for inconsistent cohort sizes and the same boundary-effect problem.

### 1.2 Variable selection

The v1 variable set is a leaner adaptation of Nebraska's 27-variable methodology, with deliberate deviations documented in Appendix A (Variable Decision Matrix). The set comprises 17 variables in total: 15 drawn from Nebraska's set (9 NDE-sourced demographic and structural variables, of which graduation rate is restricted to High School per Nebraska's own treatment, plus 6 Census ACS community variables) and 2 additions (SPED percentage from Texas's seven-variable approach, district-level average teacher salary as the v1 finance variable). The per-level used count is 16 for Elementary, Middle, and Other level groups and 17 for High School (graduation rate added).

Three Nebraska finance variables are substituted (Section 1.4). Nine Nebraska variables are excluded: three achievement variables on methodological grounds (Section 1.3); two discipline variables on policy-variation and low-variability grounds; teacher master's degree percentage on data-availability grounds (data not available at school level on data.wa.gov; v2 candidate path is parsing S-275 raw personnel extracts); and three Census ACS community variables (per capita income, bachelor's degree percentage, total population) consolidated out after the redundancy audit (Section 1.5.1).

The leaner-than-Nebraska set is motivated by transparency (parents can understand why two schools are peers), parsimony (fewer questionable variables is more defensible), and replicability. The rationale for each deviation is documented in Appendix A.

> **Reviewer Question Q2a (variable selection refinements):** Are there variables we should add or remove from the v1 set? Specifically: should race/ethnicity composition be a single percent-non-white variable or a multi-component vector? Should mobility rate (Texas includes it; we have not committed) be added if data is available? Should we drop migrant percentage given likely correlation with FRL in WA?

### 1.3 Achievement variables: excluded

Nebraska includes ELA, Math, and Science proficiency in the similarity calculation. Texas does not. We are following Texas: achievement variables are excluded from similarity in the v1 commit.

Three reasons support exclusion. First, including achievement creates circularity that systematically attenuates the academic flag toward zero: schools that underperform their structural peers get matched partly to other underperformers, and schools that outperform get matched partly to other outperformers, compressing the comparison in both directions. Second, the named-peers display in each briefing shows the variables used for matching alongside the academic comparison; if achievement is among the matching variables, the comparison becomes incoherent on its face to parents who see "your school is matched to schools that perform similarly" next to "and here is how your school's performance compares." Third, excluding achievement from similarity is what enables peer comparison to do substantive work: the peer cohort becomes "schools like yours structurally," and the comparison reveals the academic differential rather than residual variance after a partial match.

To test this commitment empirically, the methodology computation produced parallel peer cohorts using a Nebraska-style variable set with achievement included alongside the v1 cohorts. Mean Jaccard overlap between the two specifications was 0.399 across the eligible set: with K=20 in each cohort, this corresponds to approximately 11 schools shared on average and approximately 9 schools that change. Including achievement in similarity therefore reassigns roughly 45 percent of each cohort. The cohort-level finding alone establishes that the variable choice is not inconsequential and would propagate into materially different academic flag assignments downstream. The flag-level effect (which schools flip flags, magnitude of attenuation) will be reported once Section 2 is locked and the academic flag is computed. The sensitivity analysis is presented as a test of the v1 commit, not as a co-equal candidate methodology.

> **Reviewer Question Q2b (achievement variable treatment):** Is the theoretical reasoning for exclusion correct? Are there circumstances under which Nebraska's inclusion is preferable despite the attenuation concern? Does the empirical sensitivity analysis adequately address the question?

### 1.4 Finance variables: substituted

Nebraska's published methodology includes three district-level finance variables in similarity (land valuation, per pupil cost by ADM, grand total of receipts) but provides no theoretical or empirical justification for their inclusion; each is defined in a single sentence in their Table 1. A plausible (though unstated) rationale is the structural role of property-tax-based school finance in Nebraska, where local property tax is the largest single source of district revenue and the state aid equalization formula uses adjusted property valuation as a direct input.

Washington's school finance structure differs materially from Nebraska's, particularly post-McCleary. Following the 2012 McCleary Supreme Court decision and the 2017 HB 2242 implementation, the state assumed primary responsibility for funding basic education. State sources now provide approximately 73 percent of district revenue. Local enrichment levies are capped at the lesser of $2,606 per pupil (indexed) or $2.50 per $1,000 assessed valuation, creating a structural distinction between revenue-capped districts (high property value, hit the per-pupil cap) and rate-capped districts (low property value, max out on rate before reaching the per-pupil cap). Regionalization factors phased in starting 2018-19 adjust state allocations upward for higher-cost-of-living areas, compounding the levy capacity gap. Recent research (Knight et al. 2023, 2024) argues that McCleary increased rather than decreased some inequities through these mechanisms.

Direct WA analogues to Nebraska's finance variables exist but are difficult to ingest cleanly: F-196 financial data is published primarily as PDF tables or as a Microsoft Access database; assessed valuation per pupil is not the same conceptual variable as Nebraska's land valuation given the post-McCleary capped levy structure; school-level per-pupil expenditure under ESSA is not available as a clean state-wide CSV.

The v1 substitution replaces Nebraska's three finance variables with a single variable: district-level average base teacher salary per 1.0 FTE, sourced from the OSPI Personnel Summary Reports 2023-24, Table 19 (S-275-derived data). Reasoning: teacher salary is the largest expenditure category in any district budget; post-McCleary regionalization factors flow most directly into salary differentials, and local levies are heavily used to supplement state-funded salaries especially in higher-cost-of-living areas (Knight et al.); marginal data engineering cost is near zero (same OSPI Personnel Summary Reports already pulled for teacher characteristics); including additional finance variables (per-pupil expenditure, assessed valuation, total revenue) would likely be highly correlated with teacher salary and would over-weight the finance dimension under Euclidean distance.

> **Reviewer Question Q5 (finance variable substitution):** Is the substitution defensible given post-McCleary structural differences? Is teacher salary the right single finance variable, or would another better capture the funding-structure dimension? Should the lean-set principle be relaxed to include multiple finance variables despite correlation concerns? Are there published methodologies addressing finance-variable selection in state-funded education systems comparable to WA?

### 1.5 Distance metric and variable redundancy

Euclidean distance after z-score standardization is the v1 commit, following all four nearest-neighbor implementations reviewed (Nebraska, Ohio, Texas, IES/REL Central). The IES guide appendix discusses Mahalanobis distance as an alternative that weights distance by the covariance structure of the variables, addressing redundancy where multiple variables capture similar underlying dimensions. None of the reviewed state methodologies use Mahalanobis in production.

The redundancy concern is real for the v1 set. Section 1.5.1 reports the empirical correlation structure observed in the methodology computation and the consolidation decision applied. Section 1.5.2 documents the residual correlations that remain after consolidation and the conditions under which a v2 escalation to Mahalanobis would be warranted.

#### 1.5.1 Empirical correlation structure and consolidation

The methodology computation reported the pairwise correlation matrix across the standardized similarity variables, both pooled and segmented by level group. Four clusters of correlated variables were identified.

*Cluster 1 (income and education, three-way):* per_capita_income and bachelors_pct_25plus correlated at r = +0.93; median_household_income and per_capita_income at r = +0.89; median_household_income and bachelors_pct_25plus at r = +0.77.

*Cluster 2 (population):* total_population and population_density correlated at r = +0.85 to +0.91 across levels. The pairing is partly tautological at WA scale: population_density is total_population divided by land_area, and land_area is dominated by district geography rather than school-level variation.

*Cluster 3 (race and English-language status):* race_pct_non_white and ell correlated at r = +0.78 to +0.80 across pooled and per-level estimates.

*Cluster 4 (FRL with income at the Middle level):* frl correlated with median_household_income at r = -0.76 (Middle level only); with per_capita_income at r = -0.74; with bachelors_pct_25plus at r = -0.72.

The v1 commit applies consolidation rather than a metric switch (Path C). Cluster 1 is resolved by retaining median_household_income as the parent-intuitive economic variable and dropping per_capita_income and bachelors_pct_25plus, which are highly redundant with median_household_income individually and tautologically redundant in combination at r = 0.93. Cluster 2 is resolved by retaining population_density (the urban-rural gradient that affects school context) and dropping total_population, which is largely captured by population_density once land_area is held in the variable set. Clusters 3 and 4 are not consolidated and are retained as documented residuals (Section 1.5.2).

The post-consolidation set is 17 variables in total (16 used at Elementary, Middle, and Other level groups; 17 used at High School). Euclidean distance is retained.

#### 1.5.2 Residual correlations and the v2 Mahalanobis escalation path

Two correlations remain in the consolidated set that the audit flagged but consolidation did not address.

First, race_pct_non_white and ell correlate at r = +0.78 to +0.80 across pooled and per-level estimates. This residual is a WA-specific structural feature: Hispanic agricultural-worker communities in central and eastern Washington, and refugee resettlement areas in King and Snohomish counties, generate populations where non-white ethnicity and English-learner status are jointly elevated by demographic composition rather than by methodological double-counting. Dropping ELL would lose a variable that captures language-instructional context distinct from race. Dropping race composition would lose a variable that captures community context distinct from language status. Both are retained with the residual correlation documented as a known limitation rather than methodologically driven.

Second, FRL correlates with median_household_income at r = -0.76 at the Middle school level only (n = 309). The Middle-level estimate is partly a smaller-n artifact and partly a genuine overlap between school-catchment FRL and district-level economic geography at the level group where catchment-district correspondence is tightest. The residual is accepted as a documented WA-specific limitation rather than driving further consolidation.

Mahalanobis distance is documented as a v2 escalation path under three explicit trigger conditions:

(a) Future variable additions produce structural redundancy that consolidation cannot cleanly resolve. The most likely trigger is a multi-component race composition vector (per Q2a), where individual race-percentage variables are mutually correlated by construction and consolidation back to a single non-white percentage defeats the reviewer's interest in the multi-component structure.

(b) Reviewer pushback specifically on the consolidation strategy that warrants revisiting Section 1.5.1. If the reviewer's response to Q6 argues that the dropped variables carry methodological weight that consolidation discards, Mahalanobis on the original 19/20-variable set (pre-consolidation, post-R1) is the alternative.

(c) A future Mahalanobis sensitivity variant produces low Jaccard against the consolidated cohorts, indicating the consolidation choice matters empirically rather than being an inconsequential simplification. Threshold for "low Jaccard" to be set when the sensitivity is run; tentative cutoff is mean Jaccard below 0.6 across the eligible intersection.

The decision-tree framing (consolidate first, escalate to Mahalanobis if triggers fire) is methodologically tighter than presenting consolidation and Mahalanobis as parallel alternatives. Consolidation handles the cleanest cases (the three-way income/education redundancy at r = 0.93; the tautological population/density relationship at WA scale) better than Mahalanobis would, while Mahalanobis preserves variable transparency where consolidation would impose a methodological choice that future variable additions or reviewer input might want re-litigated.

> **Reviewer Question Q6 (residual correlations and the v2 escalation framing):** Was consolidation the right call at the magnitudes observed, or do the dropped variables (per_capita_income, bachelors_pct_25plus, total_population) carry methodological weight that consolidation discards? Are the residual correlations (race_pct_non_white ~ ell ~+0.78; frl ~ median_household_income ~-0.76 Middle-only) acceptable as documented WA-specific limitations? Are the three Mahalanobis v2 trigger conditions methodologically tight? Should the redundancy audit report higher-order structure (principal components, variance inflation factors) in addition to pairwise correlations going forward?

### 1.6 Cohort size (K=20)

K=20 was chosen by triangulation across Nebraska (K=12 with ~330 schools per level after splits), Ohio (K up to 20 with ~1,000 schools per level), and Texas (K=40 with 2,000-3,000 schools per level). Washington has approximately 1,000 elementary schools, 400 middle schools, and 500 high schools after per-level segmentation. K=20 represents 2 to 5 percent of the relevant pool, comparable proportionally to Nebraska's K=12 against its smaller pool.

To test stability, the methodology computation produced parallel cohorts at K=10 and K=30 alongside the K=20 commit. Mean cohort containment was 1.000 for K=10 within K=20 and 1.000 for K=20 within K=30. Strict nesting is what nearest-neighbor matching with deterministic Euclidean distance predicts mathematically; the result confirms the implementation produces the expected structure rather than constituting a substantive empirical finding. The methodologically substantive K sensitivity test (how often a school's flag status changes across K = 10, 20, 30) requires the academic flag from Section 2 and will be reported once that section is locked and the flag is computed.

> **Reviewer Question Q2c (choice of K):** Is K=20 appropriate, or should it differ by level (smaller K for less-populous level groups, larger K for elementary)? Does the K sensitivity analysis adequately address the question?

### 1.7 Geographic constraint

No geographic constraint is applied in v1. All four nearest-neighbor implementations reviewed handle geography either separately from similarity or not at all. Nebraska computes Haversine geographic distance as a separate optional view; Texas explicitly allows comparison group members "from anywhere in Texas." Washington's geographic structure (urban corridor, rural east, tribal communities, border communities, island schools) means geographically proximate schools are often less structurally similar than statewide-similar schools.

> **Reviewer Question Q2e (geographic constraint):** Should v1 add a geographic constraint, or is the consensus practice (similarity is similarity, geography is geography, keep them separate) correct?

### 1.8 Named-peers similarity threshold

Each briefing surfaces 3 named peer schools. For schools whose 3rd-nearest peer falls beyond a similarity threshold (i.e., schools that are structurally unusual), the named-peers display falls back to a notice that no closely-matched peers exist. The threshold is determined empirically once the nearest-neighbor distance distribution is computed. The default is a percentile-based threshold set so approximately 5% of schools fall back to "no close peers."

> **Reviewer Question Q2f (similarity threshold):** What is an appropriate way to set this threshold? Hard cutoff on raw Euclidean distance? Percentile-based (the v1 default)? Relative threshold tied to within-cohort variance?

### 1.9 Special populations: schools where the methodology does not apply cleanly

The Phase 3R Census ingestion audit surfaced two categories of schools where the standard peer-matching methodology does not work well. Each is handled transparently, naming the limitation rather than allowing these schools to disappear from the project's coverage.

#### 1.9.1 Schools serving primarily tribal communities

Washington has multiple schools serving primarily tribal communities. Some are coded under tribal education department authorities; others under regular public school districts but serving predominantly Native American student populations. The standard methodology was not designed for tribal community context: Census ACS does not produce tribally specific community variables, and the demographic similarity variables we use do not capture dimensions that may matter most for these schools (tribal language program participation, sovereignty arrangements, culturally specific curricula, BIE funding status).

We considered creating a separate "tribal schools" peer category and rejected it for v1: small sample size precludes meaningful K=20 nearest-neighbor matching; heterogeneity across distinct tribal communities (Suquamish, Yakama, Quinault, others operate in materially different contexts that a single category would obscure); lack of tribal-education research expertise within the project team. For v1, schools coded under tribal education department authorities are excluded from Census peer matching with reason code `tribal_community_context_not_capturable_v1`. Schools serving primarily tribal communities but coded under regular districts receive default treatment, with a documented limitation that tribal community context is not adequately captured.

> **Reviewer Question Q3 (tribal-serving schools):** Is the v1 approach methodologically defensible? Pointers to relevant tribal-education research that could inform v2 methodology improvements? Should we seek out tribal-education research expertise (and from whom) before launch?

#### 1.9.2 Institutional and specialty schools

Washington's K-12 system includes a meaningful number of institutional and specialty schools that do not fit the standard peer-matching framework: juvenile detention centers and county youth services facilities (~12 schools); regional alternative and reengagement programs operated by Educational Service Districts and technical colleges (~9 schools); state-operated specialty schools including Washington School for the Deaf, Washington School for the Blind, and Washington Youth Academy (~3-4 schools).

We considered a separate "institutional facilities" peer category and deferred it to potential v2 work. The case against: small sample size limits statistical power; heterogeneity within the category (a 4-student detention center and a 350-student reengagement program serve materially different populations); standard comparative metrics like chronic absenteeism, discipline, and achievement do not apply cleanly when the entire population has documented justice-system involvement and programming is constrained; required similarity variables (length of stay, capacity, security classification, programming type) are not in the database; and education research on incarcerated youth is its own subfield with methodologies distinct from general K-12 measurement.

For v1, these schools are flagged as not comparable to traditional schools with appropriate reason codes. School-level data still appears in briefings; comparative claims do not. The students attending these schools are among the least likely to have parent advocates engaged with school-quality data; the methodology limitation is named explicitly rather than allowing the schools to disappear from coverage.

> **Reviewer Question Q4 (institutional schools):** Is v1's non-comparative treatment methodologically defensible? Pointers to existing methodology in the education research literature for comparing detention educational programs or regional alternative programs at a scale appropriate to Washington? Should detention-school comparison be pursued as a v2 extension or treated as a separate project with its own methodology?

### 1.10 Use of peer cohort in the briefing

The peer cohort is used in three downstream calculations:

1. **Peer-cohort percentiles for individual metrics.** A school's chronic absenteeism rate is reported alongside the median rate for its 20 nearest peers, with the school's percentile within that cohort.
2. **Standout signals.** A school that is 3 or more standard deviations from the peer cohort mean on any metric triggers a standout signal (alarming or noteworthy depending on direction).
3. **Named peer schools displayed in the briefing.** Each briefing surfaces the 3 nearest peer schools by name, alongside the variables used to construct the similarity match. Display is preceded by a brief framing sentence indicating which variables were used and explicitly noting that geography is not part of the similarity calculation. This serves as a transparency mechanism: domain experts (district researchers, school administrators, journalists, the reviewer) can audit peer assignments by inspection. We do not solicit user feedback on peer accuracy from parents (who typically lack the underlying variable data to evaluate matches), but the visible cohort and underlying variables make systematic auditing possible for anyone with the relevant data.

### 1.11 Limitations and disclosures

Following the practice of the source methodologies, the public methodology document will openly state:

- Peer cohort comparison is one reference point among several; state averages and district averages are also surfaced.
- Some schools are more "unique" than others. For schools without 20 genuinely close neighbors, the K=20 cohort will include matches that are progressively less similar.
- Variables not included in the cohort calculation (geography, school type beyond level, charter status) may matter for some comparisons.
- The methodology cannot capture intangible school characteristics that affect student outcomes.

---

## 2. Demographic-Adjusted Academic Performance Flag

*To be drafted. The previous FRL-only regression is being retired and replaced with peer-cohort comparison: each school's academic performance is compared to its 20 nearest peers (per the methodology in Section 1). The methodology will be validated by domain-expert inspection of output for known WA schools rather than by statistical comparison against the previous methodology. The Section 1 methodology computation has been completed and the per-school peer cohorts are populated; this section will be written once the threshold structure is locked and the academic flag is computed against those cohorts.*

*Methodology questions to be addressed in this section include the threshold structure, whether to include growth (SGP) as a separate construct, whether to include science proficiency separately or in the composite, and the K-8 grade-span ambiguity. The threshold structure has at least three axes: what is being standardized (composite, or differential from cohort), against what reference distribution (cohort, state, or eligible set), and what the threshold cuts (z-score, percentile, or absolute SD distance). The v1 choice will be made deliberately rather than defaulting to a single framing.*

> **Reviewer Question Q1 (wealth proxy in the demographic-adjusted performance methodology):** The original methodology used FRL alone as the wealth proxy in a single-variable linear regression. We replaced this with peer-cohort comparison using a multi-variable similarity index that includes FRL plus 6 Census ACS community variables (median household income, Gini index, labor force participation, unemployment, land area, population density) plus other demographic indicators. This change addresses the most acute FRL weaknesses: post-COVID waiver-related signal degradation, stigma-driven underreporting at higher grade levels, and CEP distortion are partially mitigated. The remaining question is whether the v1 variable set captures wealth and community context adequately, or whether further refinement is warranted before launch. Possible refinements include block-group ACS with school attendance zone overlay (v2 candidate, requires inconsistently published WA shapefiles), a composite socioeconomic index (Stanford EOP approach), and additional Nebraska variables (the finance substitution in Section 1.4 partially addresses this). Default without reviewer input: ship v1 with the current variable set, document limitations explicitly, plan block-group ACS as v2.

---

## 3. Threshold-Based Flags

*To be drafted. Three production thresholds require revision based on current distribution analysis: chronic absenteeism (currently 20%/30% for yellow/red, candidate revision to ~30%/45% pending diagnostics); discipline disparity ratio minimum subgroup size (currently 10, candidate revision to 30); other absolute-threshold flags TBD as elements are confirmed.*

---

## 4. Disparity Ratio Methodology

*To be drafted. The current discipline disparity calculation surfaces the maximum race-vs-white-baseline suspension ratio. Methodology questions: should absolute rate context be surfaced alongside the ratio (UCLA Civil Rights Project caution); should the white-baseline default be disclosed and alternative baselines offered; should access disparity ratios (AP, dual enrollment, gifted) be added using the same statistical machinery; minimum subgroup size threshold.*

---

## Sources

- **IES / REL Central.** *A Guide to Identifying Similar Schools to Support School Improvement.* 2021. https://files.eric.ed.gov/fulltext/ED613435.pdf
- **Nebraska Department of Education.** *Methodology to Compare Districts and Schools: A Technical Report.* January 2019. https://www.education.ne.gov/wp-content/uploads/2019/02/Methodology-to-compare-similar-peer-school-districts.pdf
- **Ohio Department of Education and Workforce.** Similar District Methodology. https://education.ohio.gov/Topics/Data/Report-Card-Resources/Supplemental-Information/Similar-District-Methodology
- **Texas Education Agency.** Campus Comparison Group methodology, 2024 Accountability Ratings. https://rptsvr1.tea.texas.gov/perfreport/account/2024/group.srch.html
- **New York State Education Department.** What is a Similar School. https://www.p12.nysed.gov/repcrd2003/information/similar-schools/guide.html
- **Washington Citizen's Guide to K-12 Finance 2024.** https://leg.wa.gov/media/jyxir1tw/citizens-guide-to-k-12-financing-2024.pdf
- **Knight, D.S. et al.** "Post McCleary, WA school funding doesn't add up." Seattle Times, April 14, 2023.
- **Fujioka, K. & Knight, D.S.** *McCleary at Twelve: Examining Policy Designs Following Court-Mandated School Finance Reform in Washington State.* 2024.
- **Augustine, C.H. et al.** *Can Restorative Practices Improve School Climate and Curb Suspensions?* RAND Corporation, 2018. (Cited in WSIPP benefit-cost analysis of restorative justice in schools.)
- **NCES State Finance Profiles.** Nebraska. https://nces.ed.gov/edfin/pdf/StFinance/Nebraska.pdf

---

## Appendix A: Variable Decision Matrix

The v1 similarity variable set is documented as deviations from the Nebraska Department of Education's 27-variable reference methodology (NDE 2019, Table 1).

### Nebraska variables (27)

| # | Nebraska Variable | Status | WA Implementation | Reasoning | Reviewer Q |
|---|---|---|---|---|---|
| 1 | Membership (enrollment) | Include | Total enrollment, OSPI Report Card 2023-24 | Direct port. | — |
| 2 | Attendance Rate | Include | Chronic absenteeism rate, OSPI Report Card 2023-24, school-level | Substituted variable form: chronic absenteeism rate replaces attendance rate. Already in WA data schema and briefing layer; using it keeps the methodology consistent with the existing flag system. Z-score standardization handles post-COVID level shift; the redundancy audit confirmed independent signal (chronic_absenteeism is not in any of the four high-correlation clusters in Section 1.5.1). | — |
| 3 | Graduation Rate (4-year) | Include | data.wa.gov Report Card Graduation 2023-24, school-level all-students | Direct port. HS-only per Nebraska's own treatment. | — |
| 4 | FRL Rate | Include | OSPI 2023-24 | Direct port. Limitations documented in harm register; WA distribution shows no widespread CEP distortion. | Q1 |
| 5 | Minority Rate (% non-white) | Include | OSPI 2023-24, single percent non-white | Direct port. Single-variable form matches Nebraska and Texas; multi-component vector deferred to v2. | Q2a |
| 6 | Homeless Rate | Include | OSPI Report Card 2023-24, school-level (availability confirmed during ingestion) | Direct port. WA-specific judgment that urban housing dynamics make this an independent signal beyond FRL: low-income but stably housed families and doubled-up homeless families have materially different educational stability profiles. | — |
| 7 | LEP Rate | Include | OSPI 2023-24; WA term is EL/ML, same variable | Direct port. | — |
| 8 | Migrant Rate | Include | OSPI 2023-24 | Direct port. The redundancy audit did not surface a high migrant ~ FRL correlation cluster in WA; migrant is retained in the v1 set. | Q2a |
| 9 | ELA Percent Proficient | Exclude | — | Excluded from similarity to avoid systematic attenuation of the academic flag. Aligned with Texas methodology. Empirically tested in achievement sensitivity analysis. | Q2b |
| 10 | Math Percent Proficient | Exclude | — | Same as row 9. | Q2b |
| 11 | Science Percent Proficient | Exclude | — | Same as row 9. | Q2b |
| 12 | Teachers With Masters Percent | Exclude | — | Data not available at school level on data.wa.gov. Three Educator * Level datasets (`t9ya-d7ak`, `3543-y5sg`, `wsha-faww`) returned HTTP 404 (retired or migrated to Tableau portal). The OSPI teacher qualification dataset (`wc8d-kv9u`) publishes only Inexperienced/Experienced status, not credential level. The OSPI Personnel Summary XLSX has no credential breakdown across its 39 sheets. v2 candidate: parse S-275 raw personnel extracts (published outside data.wa.gov as annual CSV/XLSX) and aggregate Highest_Degree to school level. | — |
| 13 | Average Years Teaching Experience | Include | data.wa.gov `bdjb-hg6t` (Report Card Teacher Experience Distribution School Years 2017-18 to 2024-25), school-level, filtered to 2024-25 | Derived from OSPI's binned experience distribution; average computed as bin-midpoint weighted by teacher percent, using each bin's published range (e.g., 25.0-29.9 → 27.45). Not Reported percentages are excluded from both numerator and denominator; the weighted sum is renormalized to the sum of reported-bin weights, assuming unreported teachers follow the same experience distribution as reported teachers. Schools with Not Reported above 10% carry a high_unreported_flag in metadata for downstream caution. Documented derivation, not a direct port of Nebraska's published-average variable. | — |
| 14 | Unduplicated Suspensions | Exclude | — | Excluded from similarity. WA discipline policies are partly standardized at the state level (RCW 28A.345.090, WAC 392-400) but implementation varies meaningfully across districts, particularly around restorative practices adoption. Published evidence (Augustine et al. 2018) shows policy choice produces measurable suspension differences after controlling for context. Matching on suspension count partly matches on policy implementation rather than structural similarity. Surfaced descriptively in briefing. | — |
| 15 | Unduplicated Expulsions | Exclude | — | Nebraska themselves dropped this from school-level files for low variability. Same expected in WA; empirical confirmation reported in methodology output. Suspension-level arguments apply with greater force. | — |
| 16 | Land Valuation | Substitute | Replaced by Average Teacher Salary | See row 17. | Q5 |
| 17 | Per Pupil Cost by ADM | Substitute | Replaced by Average Teacher Salary | Post-McCleary WA finance structure differs materially from Nebraska's. Average teacher salary captures the substantive post-McCleary mechanism (largest expenditure category, where regionalization and levy supplementation flow most directly), is intuitively meaningful to parents, and is available at no marginal data engineering cost. References: Knight et al. (2023, 2024); WA Citizen's Guide to K-12 Finance 2024. Full reasoning in Section 1.4. | Q5 |
| 18 | Grand Total of All Receipts | Substitute | Replaced by Average Teacher Salary | See row 17. | Q5 |
| 19 | Median Household Income | Include | Census ACS B19013_001E at district geography | Direct port. | — |
| 20 | Per Capita Income | Exclude | Census ACS B19301_001E (not used in v1) | Consolidated out after the redundancy audit (Section 1.5.1). Correlated with median_household_income at r = +0.89 and with bachelors_pct_25plus at r = +0.93. Cluster 1 (income and education three-way) resolved by retaining median_household_income as the parent-intuitive economic variable and dropping the two redundant variables. | Q6 |
| 21 | Gini Index | Include | Census ACS B19083_001E | Direct port. | — |
| 22 | Bachelor's Degree % (25+) | Exclude | Census ACS S1501_C02_015E (not used in v1) | Consolidated out after the redundancy audit (Section 1.5.1). Correlated with per_capita_income at r = +0.93 and with median_household_income at r = +0.77. Cluster 1 (income and education three-way) resolved by retaining median_household_income. | Q6 |
| 23 | Labor Force Participation Rate | Include | Census ACS S2301 | Direct port. | — |
| 24 | Unemployment Rate | Include | Census ACS S2301 | Direct port. | — |
| 25 | Total Population | Exclude | Census ACS B01003_001E (not used in v1; population_density retained as the urban-rural gradient variable) | Consolidated out after the redundancy audit (Section 1.5.1). Correlated with population_density at r = +0.85 to +0.91 across levels; the pairing is partly tautological at WA scale (population_density is total_population divided by land_area, and land_area is dominated by district geography). Cluster 2 resolved by retaining population_density. | Q6 |
| 26 | Land Area | Include | TIGER Gazetteer ALAND | Direct port. | — |
| 27 | Population Density | Include | Computed B01003 / ALAND | Direct port. | — |

### Additions beyond Nebraska (2)

| # | Variable | Source | Reasoning | Reviewer Q |
|---|---|---|---|---|
| A1 | SPED Percentage | OSPI 2023-24 | Borrowed from Texas's seven-variable approach. Standard demographic variable capturing disability service intensity. | — |
| A2 | Average Teacher Salary | OSPI Personnel Summary Reports 2023-24, Table 19 (Average Base Salary per 1.0 FTE), district-level (S-275-derived) | Substitutes for rows 16-18. Full reasoning in Section 1.4. District-level applied identically to all schools in district, consistent with Nebraska's own treatment of district-level finance variables and with Census ACS variables. | Q5 |

### v1 Variable Count

Total set after Path C consolidation: 17 variables (15 from Nebraska's set, 2 additions). Per-level used count: 16 for Elementary, Middle, and Other level groups; 17 for High School (graduation rate adds at HS, restricted per Nebraska's own treatment).

Three Nebraska finance variables are substituted (rows 16-18). Nine Nebraska variables are excluded: three achievement variables (ELA, Math, Science proficiency) on methodological grounds; two discipline variables (suspensions, expulsions) on policy-variation and low-variability grounds; teacher master's degree percentage on data-availability grounds (v2 path identified); and three Census ACS community variables (per capita income, bachelor's degree percentage, total population) consolidated out after the redundancy audit.
