# Phase 3 — Decision Log

Deviations from the implementation plan, with reasoning.

---

## 1. Per-level regression instead of single statewide regression

**Date:** 2026-02-21
**Context:** The build sequence (docs/build_sequence.md) specifies a single statewide FRL-vs-proficiency regression. During planning, we tested both approaches against Fairhaven Middle School (the golden reference).

**Empirical findings:**
- **Statewide regression:** R²=0.65, Fairhaven z-score=0.89 → "as_expected" (YELLOW)
- **Per-level regression (Middle only):** R²=0.69, Fairhaven z-score=1.33 → "outperforming" (GREEN)

The statewide regression is distorted because elementary schools dominate the sample (~773 of 1,249 regression-ready schools) and have a steeper FRL-proficiency slope than middle or high schools. This pulls the regression line in a way that makes middle schools appear closer to "expected" than they truly are within their peer group.

**Per-level R² values:** Elementary=0.72, Middle=0.69, High=0.56. All three levels have sufficiently strong fits to justify separate models. The different slopes confirm that the FRL-proficiency relationship varies meaningfully by school level.

**Flag distribution for Middle schools at ±1.0 SD:** 12.3% green, 78.4% yellow, 9.3% red — close to the 15/70/15 target distribution.

**Decision:** Use per-level regression (grouped by level_group: Elementary, Middle, High, Other). For groups with fewer than 30 schools, fall back to the statewide all-levels regression.

**Impact:** Fairhaven correctly receives "outperforming" (green) flag. The gate check passes. Schools are compared against peers at the same educational level, which is more educationally defensible.

---

## 2. Exclude non-traditional school types from performance regression

**Date:** 2026-02-21
**Context:** During builder review, Mosaic Home Education Partnership (NCESSCH 530033002802, frl=0.14, composite=0.273) was flagged as "underperforming." The regression math is correct — a low-FRL school with low proficiency genuinely is below the predicted curve. But Mosaic is a homeschool cooperative, not a traditional school underperforming. The same issue applies to juvenile detention facilities, virtual schools, and alternative programs. These schools serve fundamentally different populations or operate under different instructional models, so comparing them on a FRL-vs-proficiency curve is misleading.

**Decision:** Exclude three CCD school types from the performance regression:
- "Alternative School" (341 schools)
- "Special Education School" (82 schools)
- "Career and Technical School" (20 schools)

Schools excluded by type receive `performance_flag = null` with `performance_flag_absent_reason = "school_type_not_comparable"`. They still get all other derived fields (ratios, percentiles, climate flags) — only the FRL-vs-proficiency regression comparison is suppressed.

Additionally, a `school_exclusions.yaml` file at the project root provides a manual override list for edge cases where CCD codes a non-traditional school as "Regular School." The pipeline reads this list and applies the same exclusion. Mosaic is the first entry (though it's already caught by the CCD type filter as an "Alternative School").

**Impact:** Regression pool drops from 1,249 to ~1,060 schools. Only "Regular School" types participate in the regression. The remaining flag distribution stays close to the 15/70/15 target because non-traditional schools were mostly in the tails (disproportionately "underperforming" due to their different mission, not genuine underperformance).

---

## 3. Virtual and online schools require manual exclusion from performance regression

**Date:** 2026-02-21
**Context:** After excluding non-traditional CCD school types (deviation #2), builder review found that virtual/online schools coded as "Regular School" in CCD were still receiving misleading performance flags. Bellevue Digital Discovery (frl=0.13, composite=0.23, flag=underperforming) and Boistfort Online School (frl=0.01, composite=0.18, flag=underperforming) were both correctly identified as below their FRL-predicted proficiency, but the comparison is invalid because virtual schools draw from statewide self-selected enrollment pools that break the geographic peer comparison model.

**Scope of the problem:** A name-based search for "Online", "Virtual", "Digital", "Distance", "Remote", and "Home Education" found 58 schools. Of these, 35 are already "Alternative School" in CCD (caught by the type filter). The remaining 23 are coded "Regular School" — among those, 6 had active performance flags (5 underperforming, 1 as_expected) that are potentially misleading.

**Decision:** Virtual and online schools are a known category requiring manual exclusion via `school_exclusions.yaml`. The CCD school_type field does not reliably distinguish virtual from brick-and-mortar schools. The builder reviews the full list and adds confirmed virtual schools to the exclusion list on a case-by-case basis.

**Impact:** Each excluded school receives `performance_flag = null` with `flag_absent_reason = "school_type_not_comparable"`. The exclusion list is expected to grow as the builder reviews the 23 "Regular School" virtual programs.

---

## 4. Batch exclusion of non-traditional schools identified through null-FRL review

**Date:** 2026-02-22

**Context:** During Phase 4 advisory planning, builder investigated the 152 schools with null FRL values to assess whether CEP (Community Eligibility Provision) was distorting the FRL distribution used in the performance regression. The FRL distribution was found to be healthy (no unnatural spike at 100%, source is OSPI 2023-24 post-COVID waiver expiration). However, the investigation revealed that 60 of the 152 null-FRL schools are coded as "Regular School" in CCD but are clearly non-traditional: jails, juvenile detention centers, group homes, residential treatment facilities, preschool/ECEAP/Head Start programs, homeschool partnerships, youth services nonprofits, alternative/reengagement programs, and zero-enrollment schools that are likely closed.

These schools were invisible to the Phase 3 exclusion logic because the CCD type filter only catches Alternative, Special Education, and Career/Technical types, and the Phase 3 virtual school name search targeted online/virtual keywords. Jails, group homes, and preschools coded as "Regular School" passed through both filters.

**Decision:** Add 43 schools to `school_exclusions.yaml` across the following categories: Jails & detention centers (15) including Echo Glen School identified separately through builder's local knowledge during FRL distribution review. Group homes & residential treatment (6). Preschool / ECEAP / Head Start (10). Homeschool partnerships (2). Community-based / youth services (4). Alternative / reengagement miscoded as Regular (6). Special ed / tribal language programs miscoded as Regular (3) — note: Kalispel Language Immersion School is culturally significant, excluded from regression only, not from briefing generation. Zero enrollment / likely closed (3).

Six schools with null FRL were deliberately NOT excluded: Point Roberts Primary (5 students, geographic exclave), Decatur Elementary (3 students, San Juan Islands), Holden Village Community School (4 students, remote mining village), Waldron Island School (5 students, San Juan Islands), Coulee City Middle School (0 students — verify if closed), Star Elem School (0 students — verify if closed), Nespelem High School (19 students, Colville Reservation — FRL likely suppressed, not absent). These are real schools serving real children in geographically unique situations. They should receive briefings with narrative framing appropriate to their context (Phase 5 design consideration).

**Impact:** Manual exclusion list grows from 26 to approximately 69. Combined with the 443 CCD type-filtered exclusions, approximately 511 of 2,532 schools (20%) are excluded from the performance regression. All excluded schools retain full data documents and all non-regression derived fields. Regression pool integrity improves — no jails or preschools influencing the FRL-vs-proficiency curve.

---

## 5. Discipline disparity minimum-N threshold raised from 10 to 30

**Date:** 2026-02-22

**Context:** Builder requested analysis of schools with discipline disparity ratios above 10x. Of 1,300 schools with computable disparity ratios, 65 exceeded 10x. Investigation of the triggering subgroup enrollment revealed a clear small-number problem:

- 29 of 65 (45%) have fewer than 20 students in the triggering subgroup
- 38 of 65 (58%) have fewer than 30 students in the triggering subgroup
- 27 of 65 (42%) have 30+ students — these represent real signal

Examples of small-N artifacts: North Star Elementary (10 Black students, 32.8x), Chief Kanim Middle School (11 Black students, 36.3x), Salem Woods Elementary (11 Asian students, 29.9x). A single suspension against 10 students produces a 10% rate, which easily generates extreme ratios when divided by a lower white suspension rate.

Examples of real signal at 30+ students: Ballard High School (47 Black students, 51.6x), Washington Middle School (191 Black students, 10.6x), Garfield High School (449 Black students, 10.2x). These ratios reflect genuine disciplinary patterns, not statistical noise.

**Decision:** Raise the minimum subgroup enrollment threshold from 10 to 30 for discipline disparity ratio computation. Schools with subgroups of 10-29 students will have their disparity ratio suppressed with a new reason code: `suppressed_subgroup_lt_30`. Schools with subgroups below 10 continue to be excluded entirely (as before).

**Implementation:** Deferred. Requires a Phase 3 comparison engine rerun before Phase 5 (narrative generation). Does not affect Phase 4 (AI context enrichment), which does not consume disparity ratios directly. The change will be applied to `pipeline/12_compute_ratios.py` and `flag_thresholds.yaml` during the pre-Phase 5 rerun.

**Impact:** Approximately 200-300 schools currently receiving disparity ratios based on subgroups of 10-29 students will have those ratios suppressed. The discipline disparity flag distribution will shift — fewer yellow and red flags, more nulls with the `suppressed_subgroup_lt_30` reason. Schools with 30+ students in the subgroup retain their ratios and flags unchanged.
