# Phase 3R: Statistical Reviewer Questions Log

**Purpose:** A living log of statistical methodology questions that will be sent to the independent reviewer (academic sociologist with quantitative methods expertise) for evaluation before launch. Each question is generated during the Phase 3R product spec and methodology brief workstream.

**Audience:** The independent reviewer. The product spec (`phases/phase-3R/product_spec.md`, in progress) describes *what* the briefing measures and surfaces; this document describes *how* it's measured and asks for evaluation of those choices.

**Format:** Each question carries a stable number so it can be referenced from the spec. Questions move from `open` → `answered` (with reviewer's response logged) or `parked-pending-data` (waiting on diagnostics) or `withdrawn` (decision made without reviewer input, with reasoning logged).

**Status counts (current):** 6 open, 0 answered, 0 parked, 0 withdrawn.

---

## Q1. Wealth proxy in the demographic-adjusted performance methodology

**Topic:** Whether multi-variable similarity (FRL plus Census ACS variables plus other demographic indicators) provides adequate demographic adjustment, or whether additional refinement of the wealth-proxy variables specifically is needed.

**Context:** The original methodology used FRL alone as the wealth proxy in a single-variable linear regression. We replaced this with peer-cohort comparison using a multi-variable similarity index that includes FRL plus 9 Census ACS community variables (median household income, per capita income, Gini index, percent with bachelor's degree, labor force participation, unemployment, total population, land area, population density) plus other demographic indicators.

This change addresses the most acute FRL weaknesses: the new methodology no longer depends on FRL alone, so post-COVID waiver-related FRL signal degradation, stigma-driven underreporting at higher grade levels, and CEP distortion are partially mitigated by the additional variables.

The remaining question is whether the v1 variable set captures wealth and community context adequately, or whether further refinement is warranted before launch.

**Possible refinements:**

1. **Block-group ACS with school attendance zone overlay.** District-level ACS (current) loses within-district variation; a more accurate join would use Census block groups overlaid with school attendance zones. Requires attendance zone shapefiles which Washington publishes inconsistently. v2 candidate.

2. **Composite socioeconomic index.** Combine ACS variables into a composite index rather than including them separately. Stanford EOP uses this approach.

3. **Additional Nebraska variables not yet ingested.** Teacher experience, teacher education level, district financial data are part of Nebraska's full 27-variable set and are not yet in our methodology.

**Default without reviewer input:** Ship v1 with the current variable set. Document the limitations explicitly. Plan block-group ACS as v2.

**Stakes:** The wealth proxy question is the project's central methodology choice. The move from single-variable FRL regression to multi-variable peer-cohort comparison was the largest improvement. Further refinements have diminishing returns but real value if the reviewer recommends them.

**Status:** Open.

---

## Q2. Peer school identification methodology

**Topic:** Variable selection, cohort size, distance metric, and treatment of achievement variables in the nearest-neighbor matching used to identify peer schools.

**Context:** School Daylight uses peer school identification as the basis for cohort-based percentile comparisons, standout signal detection, and a named-peers display in each briefing. Phase 3R adopted nearest-neighbor matching with Euclidean distance after standardization, per-level segmentation, and a fixed cohort size of K=20 for v1. This framework was selected based on review of five research-grade methodologies: the IES/REL Central guide (federal, 2021), Nebraska Department of Education (2019, co-developed with REL Central), Ohio Department of Education and Workforce, Texas Education Agency, and New York State Education Department.

The framework decision (nearest-neighbor matching over cluster-based grouping) is settled. Several specific implementation choices remain genuinely open and would benefit from reviewer evaluation.

**Open sub-questions:**

**Q2a. Variable selection.** The proposed v1 variable set is closer to Texas's seven-variable approach than to Nebraska's 27-variable set:
- Total enrollment
- Grade levels served
- Free/reduced lunch percentage
- English language learner percentage
- Special education percentage
- Race/ethnicity composition (currently planned as percent non-white; alternative is multi-component vector)
- Migrant student percentage

Are there variables we should add or remove? Specifically: should race/ethnicity composition be a single percent-non-white variable or a multi-component vector capturing the racial composition more fully? Should mobility rate (Texas includes it; we have not committed) be added if the data is available? Should we drop migrant percentage given that it correlates with FRL in WA?

**Q2b. Treatment of achievement variables.** Nebraska includes ELA, Math, and Science proficiency in the similarity calculation. Texas does not. We are following Texas: achievement variables are excluded from similarity in the v1 commit.

Three reasons support exclusion. First, including achievement creates circularity that systematically attenuates the academic flag toward zero: schools that underperform their structural peers get matched partly to other underperformers, and schools that outperform get matched partly to other outperformers, compressing the comparison in both directions. Second, the named-peers display in each briefing shows the variables used for matching alongside the academic comparison; if achievement is among the matching variables, the comparison becomes incoherent on its face to parents who see "your school is matched to schools that perform similarly" next to "and here is how your school's performance compares." Third, excluding achievement from similarity is what enables peer comparison to do substantive work: the peer cohort becomes "schools like yours structurally," and the comparison reveals the academic differential rather than residual variance after a partial achievement match.

To test this commitment empirically, the methodology computation will run a parallel sensitivity analysis using the Nebraska-style variable set (achievement included). Results will show how flag distributions differ between the two approaches, which schools flip flags, and the magnitude of attenuation. The sensitivity analysis is presented as a test of the v1 commit, not as a co-equal candidate methodology.

The question for the reviewer is whether the theoretical reasoning is correct, whether there are circumstances under which Nebraska's inclusion is preferable despite the attenuation concern, and whether the empirical sensitivity analysis adequately addresses the question or whether additional examination is warranted.

**Q2c. Choice of K.** K=20 was chosen by triangulation across Nebraska (K=12), Ohio (up to K=20), and Texas (K=40), accounting for Washington's school count of approximately 1,000 elementary schools, 400 middle schools, and 500 high schools after per-level segmentation. K=20 represents 2 to 5 percent of the relevant pool. Is K=20 appropriate, or should it differ by level (smaller K for less-populous level groups, larger K for elementary)?

**Q2d. Distance metric.** Euclidean distance after standardization is the v1 commitment, following Nebraska's published methodology. Mahalanobis distance, which weights distance by the covariance structure of the variables, is referenced in the IES guide appendix as an alternative. Mahalanobis is more sophisticated for correlated variables but harder to explain and implement. Is Euclidean adequate, or does the variable correlation structure in our chosen set warrant Mahalanobis? *Note: Q6 develops this question further and supersedes Q2d as the more developed treatment.*

**Q2e. Geographic constraint.** No geographic constraint is applied in v1. All four nearest-neighbor implementations we reviewed (Nebraska, Ohio, Texas, federal guide) handle geography either separately from similarity or not at all. Nebraska computes Haversine geographic distance as a separate optional view. Texas explicitly allows comparison group members "from anywhere in Texas." Should v1 add a geographic constraint, or is the consensus practice (similarity is similarity, geography is geography, keep them separate) correct for our case?

**Q2f. Similarity threshold for the named-peers display.** The briefing surfaces 3 named peer schools per school. For schools whose 3rd-nearest peer falls beyond a similarity threshold (i.e., schools that are structurally unusual), the named-peers display falls back to a notice that no closely-matched peers exist. The threshold is currently TBD; it depends on the actual distribution of distances in the nearest-neighbor matrix once computed. What's an appropriate way to set this threshold? Options include: a hard cutoff on raw Euclidean distance, a percentile-based threshold (e.g., schools whose 3rd-nearest peer is in the worst 10% of nearest-neighbor distances), or a relative threshold tied to the within-cohort variance.

**Default without reviewer input:** Ship v1 with the variable set, K=20, Euclidean distance, no geographic constraint, and a percentile-based similarity threshold (initially set so approximately 5% of schools fall back to "no close peers").

**Stakes:** The peer cohort definition is now load-bearing for the headline academic performance methodology (peer-cohort comparison replaces the previous FRL regression). It also affects every other cohort-based output (percentile context for non-flag metrics, standout signals, named peers display). The variable selection choices in Q2a are the highest-leverage; choices on K and distance metric are lower-leverage tuning decisions.

**Related questions:** Q2 and Q1 are linked. Q1 (wealth proxy adequacy) is partially answered by the multi-variable peer cohort approach in Q2. Specific Q2 sub-questions about variable selection (Q2a) are where remaining wealth-proxy refinement decisions get made.

**Status:** Open.

---

## Q3. Treatment of schools serving primarily tribal communities

**Topic:** How should the peer-matching methodology handle schools serving primarily tribal communities, given that the standard similarity variables and Census ACS data are not designed to capture tribal community context?

**Context:** Washington has multiple schools serving primarily tribal communities. Some are coded under tribal education department authorities (e.g., Suquamish Tribal Education Department) and were surfaced in our Phase 3R district audit because their district codes do not match ACS-published geographies. Others are coded under regular public school districts but serve predominantly Native American student populations.

The standard methodology adopted for v1 (nearest-neighbor matching on demographic and structural variables, supplemented with district-level Census ACS variables) was not designed for tribal community context. The Census ACS does not produce tribally specific community variables, and the demographic similarity variables we use (FRL, ELL, SPED, race composition) do not capture dimensions that may matter most for these schools (tribal language program participation, sovereignty arrangements, culturally specific curricula, Bureau of Indian Education funding status where applicable).

**Alternatives considered:**

1. **Create a separate "tribal schools" peer category with its own matching pool.** Rejected for v1 due to small sample size (Washington has too few tribal-serving schools for K=20 nearest-neighbor matching to provide meaningful statistical power), heterogeneity across distinct tribal communities (schools serving Suquamish, Yakama, Quinault, and other tribal nations operate in materially different contexts that a single category would obscure), and lack of tribal-education research expertise within the project team.

2. **Apply default methodology treatment without modification.** Workable but produces peer matches for tribal-serving schools that are based on community context the methodology cannot adequately characterize.

3. **Identify schools serving primarily tribal communities and exclude them from peer-cohort analysis, presenting their data non-comparatively in briefings.** Partial implementation adopted: schools coded under tribal education department authorities are excluded with reason code `tribal_community_context_not_capturable_v1`. Schools serving primarily tribal communities but coded under regular districts receive default treatment because we do not currently have a reliable way to identify them programmatically.

**Default for v1 without reviewer input:** Schools under tribal education department authorities are excluded from Census peer matching with explicit reason code. Schools serving primarily tribal communities but coded under regular districts receive default treatment, with a documented limitation that tribal community context is not adequately captured by the methodology.

**What we'd want from the reviewer:** Guidance on whether the v1 approach is methodologically defensible. Pointers to relevant tribal-education research that could inform v2 methodology improvements. Guidance on whether to seek out tribal-education research expertise (and from whom) before launch.

**Stakes:** Low for the immediate ingestion task (the methodology proceeds either way). Higher for the project's overall defensibility on equity grounds. Tribal-serving schools represent a small fraction of Washington schools but a population for which mainstream educational data products have historically failed.

**Status:** Open.

---

## Q4. Treatment of detention facilities, alternative reengagement programs, and other institutional schools

**Topic:** How should the peer-matching methodology handle schools serving institutionalized or specialized populations (juvenile detention centers, regional reengagement programs, state-operated specialty schools for deaf/blind/military youth) that are structurally non-comparable to traditional residential schools?

**Context:** Washington's K-12 system includes a meaningful number of institutional and specialty schools that do not fit the standard peer-matching framework:

- Juvenile detention centers and county youth services facilities (~12 schools)
- Regional alternative and reengagement programs (Open Doors, Pass Programs) operated by Educational Service Districts and technical colleges (~9 schools)
- State-operated specialty schools (Washington School for the Deaf, Washington School for the Blind, Washington Youth Academy) (~3-4 schools)

The Phase 3 manual exclusions list already excludes most of these schools from peer-matching analysis on the grounds that they are not comparable to traditional schools. The Phase 3R Census ingestion extended this treatment by excluding them from Census-data peer matching with appropriate reason codes.

**Project values consideration:** These schools serve students who are among the least likely to have parent advocates engaged with school-quality data. The project does not exclude them from briefings entirely, even though no parent is "choosing" these schools in the way parents choose neighborhood schools. The students attending these schools are entitled to the same transparency the project provides for all other schools. The methodology limitation (peer matching does not work for these schools) is named explicitly rather than allowing the schools to disappear from the project's coverage.

**Alternatives considered:**

1. **Create a separate "institutional facilities" peer category with detention-specific or alternative-program-specific peer matching.** Considered seriously and deferred to potential v2 work. The case for: detention schools share structural features that distinguish them from traditional schools (involuntary enrollment, transient population, justice-system context, constrained programming), and comparing detention schools to each other could produce meaningful signal. The case against: small sample size (about 10-12 detention facilities in Washington) limits statistical power; heterogeneity within the category (a 4-student detention center vs. a 350-student reengagement program serve materially different populations); standard comparative metrics (chronic absenteeism, discipline, achievement) do not apply cleanly when the entire population has documented justice-system involvement and programming is constrained by detention rules; required similarity variables (length of stay, capacity, security classification, programming type) are not in the database; and education research on incarcerated youth is its own subfield with methodologies distinct from general K-12 comparative measurement.

2. **Apply default methodology to a smaller pool.** Considered and rejected. Running standard peer matching on a candidate pool of about 10 schools effectively returns the entire pool as the peer cohort, defeating the purpose of nearest-neighbor matching.

3. **Skip all peer-cohort analysis for institutional facilities, present data non-comparatively in briefings, document the methodology limit.** Adopted for v1. School-level data still appears in briefings; comparative claims do not.

**Default for v1 without reviewer input:** Institutional facilities are flagged as not comparable to traditional schools (consistent with existing Phase 3 exclusions list treatment). Briefings present these schools' data descriptively, with explicit narrative explaining that comparative methodology does not apply. Detention-specific or alternative-program-specific peer matching is documented as a v2 candidate that would require dedicated methodology research, additional data ingestion (length of stay, capacity, programming characteristics), and likely a different audience focus (policy researchers and oversight bodies rather than parents).

**What we'd want from the reviewer:** Guidance on whether v1's non-comparative treatment is methodologically defensible. Pointers to existing methodology in the education research literature for comparing detention educational programs or regional alternative programs, if any exists at a scale appropriate to Washington. Assessment of whether detention-school comparison should be pursued as a v2 extension of School Daylight or treated as a separate project with its own methodology.

**Stakes:** Low for the immediate ingestion task. Moderate for the project's coverage of vulnerable student populations. Schools serving institutionalized youth are precisely the schools whose students have the least parental advocacy supporting them; the methodology should not silently lose them from the project's scope, even when comparative claims are not possible.

**Status:** Open.

---

## Q5. Substitution of average teacher salary for Nebraska's three finance variables

**Topic:** Whether replacing Nebraska's three district-level finance variables (land valuation, per pupil cost by average daily membership, grand total of all receipts) with a single district-level average teacher salary variable is methodologically defensible given post-McCleary Washington school finance structure.

**Context:** Nebraska's published methodology document (NDE 2019) includes three finance variables in its similarity calculation but provides no theoretical or empirical justification for their inclusion. Each variable is defined in a single sentence in their Table 1; the general criterion stated for variable selection is "relevance, availability, and persistence," and acknowledgments credit "Subject Matter Experts at the Nebraska Department of Education for sharing their knowledge on the appropriateness of specific data elements."

A plausible (though unstated) rationale for Nebraska's choices is the structural role of property-tax-based school finance in Nebraska. Per the NCES Nebraska state finance profile, local property tax is the largest single source of school district revenue, and the state aid equalization formula uses adjusted property valuation as a direct input to determine local fiscal capacity. Land valuation in this context is not just a wealth proxy; it is the school finance base.

Washington's school finance structure differs materially from Nebraska's, particularly post-McCleary. Following the 2012 McCleary Supreme Court decision and the 2017 HB 2242 implementation, the state assumed primary responsibility for funding basic education. State sources now provide approximately 73 percent of district revenue (WA Citizen's Guide to K-12 Finance 2024). Local enrichment levies are capped at the lesser of $2,606 per pupil (indexed) or $2.50 per $1,000 assessed valuation, creating a structural distinction between revenue-capped districts (high property value, hit the per-pupil cap) and rate-capped districts (low property value, max out on rate before reaching the per-pupil cap). Regionalization factors phased in starting 2018-19 adjust state allocations upward for higher-cost-of-living areas, which compounds the levy capacity gap. Recent research (Knight et al. 2023, 2024) argues that McCleary increased rather than decreased some inequities through these mechanisms.

Direct WA analogues to Nebraska's three finance variables exist but are difficult to ingest cleanly. Total district revenue is published in the OSPI F-196 Financial Reporting Summary primarily as PDF tables; the underlying data is available as a Microsoft Access database for "knowledgeable users." Assessed valuation per pupil is published through OSPI's Fiscal Levy dashboard but is not the same conceptual variable as Nebraska's "land valuation" given the post-McCleary capped levy structure. Per-pupil expenditure is required to be published at school level under federal ESSA reporting but does not appear to be available as a clean state-wide CSV download.

**v1 substitution decision:** Replace Nebraska's three finance variables with a single variable, district-level average base teacher salary per 1.0 FTE, sourced from OSPI Personnel Summary Reports Table 1 (S-275 data). Reasoning:

1. Teacher salary is the largest expenditure category in any district budget. It captures the substantive way the post-McCleary funding structure affects the educational environment a student experiences, in a way that aggregated revenue or expenditure variables do not.

2. Post-McCleary regionalization factors flow most directly into salary differentials, and Knight's research is explicit that local levies are heavily used to supplement state-funded salaries especially in higher-cost-of-living areas. Teacher salary captures the mechanism through which structural inequity propagates into school-level conditions.

3. Marginal data engineering cost is near zero. The variable is published as XLSX from the same OSPI Personnel Summary Reports already used for teacher characteristics (master's degree percentage, average years experience).

4. Including additional finance variables (per-pupil expenditure, assessed valuation, total revenue) would likely be highly correlated with teacher salary in WA given how the McCleary funding structure channels resources, and would over-weight the finance dimension under Euclidean distance. One well-chosen finance variable is methodologically stronger than three correlated ones.

**Alternatives considered:**

1. **Drop finance variables entirely.** Census ACS variables already in the v1 set (median household income, per capita income, Gini index, education attainment, employment, population density) capture community wealth context. Adding any finance variable could be argued as incremental. Rejected because the post-McCleary research suggests property-value-driven funding differences are real and not fully captured by Census ACS.

2. **Port one of Nebraska's three variables directly.** District total revenue per pupil from F-196 is the closest analogue to "grand total of receipts." Rejected because of ingestion complexity (Access database parsing) and because total revenue does not capture the regionalization mechanism as directly as teacher salary.

3. **Multi-variable finance set.** Include teacher salary plus per-pupil expenditure plus assessed valuation. Rejected because the variables would be highly correlated in WA, would over-weight the finance dimension under Euclidean distance, and would move further from the leaner-is-defensible principle motivating the broader variable set.

**Default for v1 without reviewer input:** Single district-level average teacher salary variable, applied identically to all schools within a district (consistent with Nebraska's own treatment of district-level finance variables and with our treatment of Census ACS variables).

**What we'd want from the reviewer:** Assessment of whether the substitution is defensible given the post-McCleary structural differences. Whether teacher salary is the right single finance variable or whether another single variable would better capture the funding-structure dimension. Whether the lean-set principle should be relaxed to include multiple finance variables despite the correlation concerns. Pointers to published methodologies addressing finance-variable selection in state-funded education systems comparable to WA.

**Stakes:** Moderate. The finance dimension is one of several similarity inputs and is unlikely to dominate cohort composition. But the substitution is the most substantive deviation from Nebraska in the v1 variable set and the one most exposed to reviewer pushback on methodological grounds.

**Status:** Open.

---

## Q6. Distance metric decision rule and treatment of variable redundancy

**Topic:** Whether the v1 commit to Euclidean distance is appropriate given the variable set's likely correlation structure, and whether the decision rule for switching to Mahalanobis distance is methodologically sound.

**Context:** Euclidean distance after z-score standardization is the default in all four nearest-neighbor implementations reviewed (Nebraska 2019, Ohio, Texas, IES/REL Central 2021). The IES guide appendix discusses Mahalanobis distance as an alternative that weights distance by the covariance structure of the variables, addressing redundancy where multiple variables capture similar underlying dimensions. None of the reviewed state methodologies use Mahalanobis in production.

The variable redundancy concern is real for the v1 set. Several pairs are likely highly correlated: median household income with per capita income (both measure community economic level), FRL with race composition (correlated demographically in WA), homelessness with FRL (same correlation), total population with population density (related but not identical), and possibly attendance/chronic absenteeism with FRL. Under Euclidean distance, correlated variables effectively double-count: the underlying dimension they share is implicitly weighted more heavily than uncorrelated dimensions, which means the methodology is making a weighting choice we have not deliberately decided.

Mahalanobis distance addresses this by computing distance in a covariance-adjusted space, so correlated variables share weight rather than each contributing independently. The trade-off is interpretability: Euclidean distance is easier to explain to parents and to a reviewer; Mahalanobis is mathematically more sophisticated but harder to defend without statistical training.

Nebraska's published methodology does not address redundancy. Their 27-variable set includes several likely-correlated pairs (median household income and per capita income; total population and population density; FRL rate and other demographic measures), and their use of Euclidean distance implicitly accepts the resulting weighting without acknowledgment. This is a documented gap in their methodology that we inherit if we port their approach without modification.

**v1 commit:** Euclidean distance with a documented decision rule for switching to Mahalanobis based on observed redundancy.

**Decision rule for v1:** During methodology computation, the redundancy audit reports the correlation matrix across the standardized similarity variables. If no variable pair correlates above 0.70, Euclidean distance is retained for v1. If one or more pairs correlate above 0.70, two remediation paths are considered: (1) consolidate the redundant variables (e.g., drop per capita income if it correlates above 0.70 with median household income), or (2) switch to Mahalanobis distance for v1. The choice between consolidation and metric switch depends on how many pairs exceed the threshold and whether consolidation produces a cleaner methodology than introducing a more sophisticated distance metric.

**Default for v1 without reviewer input:** Euclidean distance with the redundancy audit and decision rule as specified above. Both the redundancy correlation matrix and the resulting decision are reported in `methodology_inspection.md`.

**What we'd want from the reviewer:** Whether the 0.70 correlation threshold is appropriate, whether the decision criteria between consolidation and Mahalanobis are sound, whether Mahalanobis should be the default rather than the conditional alternative, and whether there are published methodologies that handle variable redundancy more rigorously than the four state implementations we reviewed. Also: whether the redundancy audit should report higher-order structure (principal components, variance inflation factors) in addition to pairwise correlations.

**Stakes:** Moderate to high. The distance metric affects every cohort assignment and downstream comparison. If redundancy is meaningful and unaddressed, certain dimensions (likely the economic/demographic dimension given the variable set) are implicitly over-weighted, which biases peer cohorts toward economic-demographic similarity at the expense of other structural dimensions. The 0.70 threshold is a defensible starting point but not theoretically derived; the reviewer's input here directly affects the methodology's robustness.

**Related questions:** Q6 is closely related to Q2a (variable selection) and Q2d (distance metric in Q2's original framing). Q6 supersedes Q2d as the more developed treatment.

**Status:** Open.

---

*New questions appended below as the workstream proceeds. Each question gets a stable number; questions are not renumbered when reordered.*
