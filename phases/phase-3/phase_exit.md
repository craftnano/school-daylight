# Phase 3 — Phase Exit Document

**Date:** 2026-02-21
**Reviewed by:** Orianda Leigh (builder/project owner)
**Phase:** Comparison Engine — Percentiles, Peers, and Flags
**Verdict:** APPROVED TO PROCEED TO PHASE 4

---

## Human Review Log

- **Receipt reviewed:** All 13 Fairhaven checks PASS. Accepted.
- **Fairhaven test reviewed:** Outperforming z=1.37, chronic absenteeism red at 0.40, counselor green at 294, all expected. Accepted.
- **Decision log reviewed:** All deviations accepted (see below).
- **Sanity schools reviewed:** Schools across the spectrum all behave as designed. Accepted.

---

## Deviations Ratified

1. **Per-level regression instead of single statewide** — Empirically validated, educationally defensible, documented. Elementary R²=0.75, Middle R²=0.66, High R²=0.54. Different school levels have different FRL-proficiency curves; a single statewide model distorts comparisons.

2. **Peer groups use FRL band + enrollment band + school level instead of Title I and LOCALE** — Title I status and LOCALE were not available in the CCD extract. FRL is a stronger poverty proxy than Title I anyway, and school level partially captures the structural differences LOCALE would provide.

3. **flag_absent_reason added to the plan during review** — High-confidence reasons only for missing flags: `grade_span_not_tested`, `suppressed_n_lt_10`, `school_type_not_comparable`, `data_not_available`. No speculation beyond what the data directly supports.

4. **Virtual and online school exclusion discovered during sanity checks** — 468 total non-traditional schools excluded from the performance regression: 443 via CCD school type filter (Alternative School, Special Education School, Career and Technical School) plus 25 manual exclusions in `school_exclusions.yaml` (virtual/online schools coded as "Regular School" in CCD).

---

## Known Issues Carried Forward to Phase 4

1. **Virtual school list may not be complete.** Schools were identified by name keyword search (Online, Virtual, Digital, Distance, Remote, Home Education). Builder will cross-reference against OSPI published list of approved online providers to catch any that don't have these keywords in their names.

2. **Embedded alternative programs not separately identifiable.** Some traditional schools host embedded parent partnership or alternative learning experience programs that are not separately identifiable in the data. Methodology documentation should disclose this limitation.

3. **Discipline disparity uses white students as baseline.** This is a methodology choice (aligned with OCR guidance and ProPublica Miseducation methodology) that should be documented in `flag_thresholds.yaml` or methodology docs for transparency. Schools with no white baseline (white enrollment < 10 or zero white suspensions) receive null disparity ratios.

4. **Future consideration: virtual school peer cohort.** Virtual schools could form their own peer cohort for comparison against each other and against statewide brick-and-mortar averages. Not implemented in Phase 3 but worth considering in a future iteration.

---

## Ad-Hoc Addition

`school_exclusions.yaml` was created as a human-maintained override file for edge cases the pipeline cannot catch systematically. Schools on this list are excluded from the performance regression and receive `flag_absent_reason: "school_type_not_comparable"`. This is a permanent part of the maintenance workflow — the builder adds schools as they are identified during review.

---

## Go/No-Go

Phase 3: GO. Proceed to Phase 4.
