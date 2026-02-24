# Build Log

Chronological record of decisions, findings, and changes with reasoning.

---

## 2026-02-22 — Echo Glen School added to exclusions

**Context:** During pre-Phase 4 FRL data review, Echo Glen School (NCES 530375001773, Issaquah School District) appeared on the list of schools with FRL >= 95% (97.1%). Echo Glen is a DSHS juvenile detention facility. CCD codes it as "Regular School" — the same misclassification pattern discovered for virtual/online schools in Phase 3.

**Finding:** Echo Glen's 97.1% FRL reflects its institutional population, not community poverty. Issaquah School District provides educational services at the facility, but enrollment is involuntary and transient. Comparing it against traditional schools on a FRL-vs-proficiency curve is misleading for the same reasons documented in Phase 3 decision log #2.

**Action:** Added to `school_exclusions.yaml` under a new "Institutional facilities" category. Performance flag was already null (reason: `data_not_available`) — will be reclassified to `school_type_not_comparable` on next pipeline run.

**Impact:** No change to regression pool (Echo Glen was already excluded from regression due to missing proficiency data). The reason code change is more accurate documentation.

---

## 2026-02-22 — 49 non-traditional schools added to exclusions (null-FRL review)

**Context:** Investigated all 152 schools with null FRL percentage. Of the 60 coded as "Regular School" in CCD, most are clearly not traditional schools: jails, group homes, preschools, homeschool partnerships, youth services, alternative programs, and zero-enrollment entries. These schools have null FRL because OSPI doesn't report demographics for them, confirming they operate outside the normal K-12 system.

**Schools added by category:**
- **Jails and detention centers (16):** Benton County Jail, Clallam Co Juvenile Detention, Echo Glen School (already added earlier), Island County Corrections, Island Juvenile Detention, Kitsap Co Detention, Lewis County Jail, Mason County Detention, Okanogan Co Juvenile Detention, Skagit County Detention, Sno Co Jail, Snohomish Detention, Spokane County Jail, Walla Walla County Juvenile Detention, Whatcom Co Detention, Yakima Adult Jail
- **Group homes and treatment (6):** Canyon View, Fircrest Residential, Oakridge, Parke Creek Treatment, Ridgeview, Twin Rivers
- **Preschool / early childhood (10):** Cape Flattery Preschool, ECEAP, Federal Way Headstart, Head Start (Highline), Hoyt Early Learning, Manson Early Learning, Oakville Preschool, Ready Start Preschool, Spokane Regional Health District, West Central Community Center
- **Homeschool partnerships (2):** Northshore Family Partnership, White River Homeschool
- **Community-based / youth services (4):** Southwest Youth and Family Services, The Healing Lodge, Touchstone, Woodinville Community Center
- **Alternative / reengagement miscoded (6):** Alternative Tamarack School, Garrett Heyns (Centralia College), Morgan Center School, Ocosta ALE, Tacoma Pierce County Education Center, Vancouver Contracted Programs
- **Special education / specialized miscoded (3):** Arlington Special Educ School, Kalispel Language Immersion School (tribal — culturally significant but zero enrollment), North Bell Learning Center
- **Zero-enrollment / likely closed (5):** Bear Creek Elementary, Choice, Southern Heights Elementary, Coulee City Middle School, Star Elem School (both verified as zero enrollment, no staffing/academics)

**Not excluded (preserved as real schools):**
- Decatur Elementary (3 students, Lopez Island — tiny but real)
- Holden Village Community School (4 students, remote mining village — tiny but real)
- Point Roberts Primary (5 students, geographic exclave — tiny but real)
- Waldron Island School (5 students, San Juan Islands — tiny but real)
- Nespelem High School (19 students, tribal community — FRL likely suppressed, not absent)

**Impact:** `school_exclusions.yaml` now has 76 entries (25 virtual + 51 institutional/other). All 49 new schools already had null performance flags due to missing data — the change reclassifies their reason codes from `data_not_available` to the more accurate `school_type_not_comparable`. No regression results change.

---

## 2026-02-22 — Summary

Null-FRL investigation revealed 60 Regular School entries that are non-traditional. 43 added to exclusions. 6 tiny rural schools retained. Triggered by CEP/COVID concern during Phase 4 advisory planning. See `phases/phase-3/decision_log.md` entry #4 for details.

---

## 2026-02-22 — Discipline disparity small-N analysis

Discipline disparity small-N analysis. 29 of 65 schools with 10x+ ratios have fewer than 20 students in the triggering subgroup. Current minimum-N threshold of 10 is too low — produces statistically meaningless extreme ratios. Decision: raise floor to 30 before Phase 5. Schools with subgroups of 10-29 will get ratio suppressed with reason code `suppressed_subgroup_lt_30`. Requires Phase 3 comparison engine rerun before Phase 5. Does not affect Phase 4.

---

## 2026-02-22 — Chronic absenteeism threshold audit

Chronic absenteeism threshold audit. 64% of schools trip yellow or red at current 20%/30% thresholds — flag is miscalibrated for post-COVID distribution. Decision: raise thresholds to approximately 30%/45% before Phase 5. Exact values TBD after reviewing adjusted distribution. Requires Phase 3 rerun. Does not affect Phase 4.

---

## 2026-02-23 — Phase 4 complete: Haiku Context Enrichment

### Two-pass design

Phase 4 uses a two-pass architecture for web search context enrichment:

- **Pass 1 (District):** 330 districts searched for investigations, lawsuits, leadership changes, bonds/levies, and awards. Results written to `district_context` field on all schools in each district.
- **Pass 2 (School):** 1,185 schools (in 32 districts with >18 schools) searched for school-specific news, awards, programs, and incidents. Results written to `context` field on each school.

The two passes are independent. School-level Haiku does not see district-level findings. Deduplication is Phase 5's (Sonnet narrative) responsibility.

### Final numbers

| Metric | District Pass | School Pass | Total |
|---|---|---|---|
| Entities processed | 330 | 1,185 | — |
| Enriched (has findings) | 234 (70.9%) | 779 (65.7%) | — |
| No findings | 96 (29.1%) | 406 (34.3%) | — |
| Failed | 0 | 0 | 0 |
| Total findings | 755 | 1,320 | 2,075 |
| High-sensitivity findings | 291 | 149 | 440 |
| Cost | $11.88 | $43.47 | **$55.34** |
| MongoDB coverage | 2,532/2,532 | 1,185/2,532 | — |

### Sensitivity review

442 high-sensitivity findings exported to `phases/phase-4/sensitivity_review.md` for manual review. Builder reviewed findings for:

- Death/violence keywords (31 matches, 25 correctly flagged HIGH)
- Non-institutional subjects — board candidates, former students, community members (27 matches)
- Immigration/ICE-related content (8 matches)
- Sexual violence content (78 matches, 63 naming individuals)

**Findings removed during review (9 total):**
1. Beverly Elementary — student death, no institutional connection
2. Blaine SD — board candidate personal criminal charges, private citizen
3. South Pines Elementary — nearby shooting before dawn, no school connection
4. Coupeville SD (2 findings) — superintendent investigation, cleared/exonerated
5. Liberty Sr High — individual student conduct (racist video)
6. Issaquah High School — routine discipline incident
7. Cashmere SD — duplicate finding (610 KONA source removed, Cascade PBS kept)
8. Cascade HS / Everett — dismissed lawsuit about 2003 conduct

**ICE-related findings removed (6 total, prior to sensitivity review):**
Student political walkouts and protest activity at Auburn HS, Meadowdale MS, Edmonds-Woodway HS, Highline SD/Sylvester MS, Aki Kurose MS (shelter-in-place), Denny MS (false alarm). Kept: Cowlitz County/ICE contract termination (institutional action) and Wahluke SD migrant program funding (budget fact).

### Model and validation

- All calls confirmed as `claude-haiku-4-5-20251001` via `actual_model` hallucination safeguard
- Validation pass (second Haiku call) checked every finding for wrong-school contamination, source credibility, and claim support
- "Washington state" used in all search queries to avoid D.C. contamination

### Phase 4.5 — Sonnet Editorial Rule Testing (unplanned addition)

An unplanned Phase 4.5 has been added between Phase 4 and Phase 5. Phase 4.5 tests Sonnet's ability to apply editorial rules (name stripping, recency filtering, sensitivity handling, deduplication) before full narrative generation begins. This phase has its own plan and Claude Code session. See `phases/phase-4.5/` for details.

---

## 2026-02-23 — Decision: District-level enrichment pass added

**Context:** Initial Phase 4 pilot (25 schools, school-name-only search) revealed that school-level web searches do not surface district-level events. Fairhaven Middle School returned only a U.S. News recognition — none of the Bellingham School District's well-documented investigations, lawsuits, or criminal charges appeared.

**Decision:** Add a district-level enrichment pass that runs before the school-level pass. ~330 districts searched for "investigations lawsuits scandals leadership changes." Results stored in `district_context` field on all schools in each district.

**Rationale:** District-level events (superintendent actions, board decisions, OCR investigations, lawsuit settlements) are critical context for understanding any school in that district. A school briefing without district context is incomplete. Two independent passes with Phase 5 deduplication is simpler and more robust than trying to merge concerns in a single search.

---

## 2026-02-23 — Decision: "Washington state" disambiguation fix

**Context:** Search queries using `"{state}"` (which resolves to "WA" or "Washington") risk returning results about Washington, D.C. schools and districts. Multiple same-name districts exist in WA and D.C.

**Decision:** All search prompts now use the literal string "Washington state" instead of the state variable. Applied to all four prompt files (district enrichment, district validation, school enrichment, school validation).

---

## 2026-02-23 — Decision: School pass limited to districts with >18 schools

**Context:** Full school-level enrichment of all 2,532 schools would cost ~$86 and take ~21 hours. Many small/rural districts have 1-3 schools that are unlikely to surface school-specific web results (district-level pass already covers them). Need to balance cost and coverage.

**Decision:** School pass limited to the 32 districts with more than 18 schools (1,174 schools, 46.3% of dataset). This covers all major urban, suburban, and mid-size districts where school-specific context is most likely to exist and most useful. Small/rural schools still have district-level context from Pass 1.

**Alternatives considered:**
- All 2,532 schools (~$86, ~21h) — excessive for diminishing returns on small schools
- Districts with >15 schools (42 districts, 1,345 schools, ~$46, ~11h) — reasonable but slightly over budget comfort
- Districts with >10 schools (70 districts, 1,684 schools, ~$57, ~14h) — too many hours for marginal gain

**Trade-off:** 1,358 schools in smaller districts do not have school-level context. They still have district-level context. This is acceptable for v1.
