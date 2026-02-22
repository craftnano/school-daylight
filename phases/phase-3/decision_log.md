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
