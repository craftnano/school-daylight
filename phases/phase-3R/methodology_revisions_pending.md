# Methodology Revisions Pending

**Purpose:** Track methodology decisions made or surfaced during Phase 3R execution that require updates to `methodology_review_brief.md` (including Appendix A) and `variable_decision_matrix.md`. These are accumulated here rather than applied piecemeal so that a single revision pass can incorporate all findings after Prompts 2 and 3 complete.

**Status convention:**
- `LOCKED` — decision made, brief revision needed
- `PENDING` — depends on output not yet available; revisit after the named milestone
- `OPEN` — decision not yet made

---

## LOCKED

### R1. Teacher qualification (master's degree percentage) dropped from v1

**Decision:** Drop teacher master's degree percentage from v1 entirely. Document v2 path.

**Reasoning:** No school-level masters-degree or highest-degree data is queryable on data.wa.gov. Investigation by CC during Prompt 2 pre-execution review found three retired Educator * Level datasets (returning HTTP 404), the OSPI Personnel Summary XLSX (39 sheets, none with credential data), and no S-275-derived dataset on data.wa.gov.

Substituting percent-experienced from `wc8d-kv9u` (Path B in the Blocker 2 investigation) was rejected because percent-experienced and Blocker 1's derived average years are both tenure measures; using both creates redundancy that double-counts tenure while still failing to capture the credential dimension.

**v2 path documented:** S-275 raw personnel extracts are published outside data.wa.gov (annual CSV/XLSX) and include a Highest_Degree column at the personnel level. Aggregating to school level is a v2 candidate.

**Brief revisions required:**
- Appendix A row 12 (Teachers With Masters Percent): Status changes from `Include` to `Exclude`. Reasoning column updated: "Data not available at school level on data.wa.gov; three Educator * Level datasets retired (HTTP 404), OSPI Personnel Summary XLSX does not break down by credential. v2 candidate: parse S-275 raw personnel extracts and aggregate to school level."
- Section 1.2 variable count: 21 → 20.
- Section 1.2 narrative paragraph adjusted to reflect 20 variables: "10 NDE-sourced demographic and structural variables → 9" and updated total accordingly.

**Reviewer question implications:** No new question required. This is a documented data-availability constraint, not a methodology dispute. Worth noting in the cover note to the reviewer: "Master's degree percentage is unavailable in v1 due to data availability; v2 candidate path identified."

---

### R2. Teacher experience derivation method

**Decision:** Average years experience is computed from OSPI's binned distribution rather than ported as a published average. Top bin (open-ended 25+ years) capped at 25 for midpoint averaging.

**Reasoning:** OSPI publishes teacher experience as binned distribution at school level (`bdjb-hg6t` dataset), not as a published average. Computing average from bin midpoints is a documented derivation, not a direct port. The 25-year cap on the open-ended top bin is a reasonable estimate for the upper tail of teacher career length in WA.

**Brief revisions required:**
- Appendix A row 13 (Average Years Teaching Experience): Reasoning column changes from "Direct port. Year vintage one year older than other variables; precedent in Nebraska's own data-vintage handling" to: "Derived from OSPI's binned experience distribution (`bdjb-hg6t`); average computed as bin-midpoint weighted by teacher percent. Open-ended top bin (25+ years) capped at 25 for midpoint. Documented derivation, not a direct port of Nebraska's published-average variable."
- Appendix A row 13 dataset year: 2022-23 → 2024-25 (current dataset extends through 2024-25).
- Year-vintage caveat ("one year older than other variables") removed from row 13; no longer applies.

**Reviewer question implications:** Could warrant a brief mention in Q2a (variable selection refinements) but does not require a new numbered question. The derivation is transparent and replicable; the methodology brief language is sufficient defense.

---

### R3. Endpoint correction for teacher experience

**Decision:** Use `bdjb-hg6t` for teacher experience, not `vn5q-nnph` (which the original methodology brief and ingestion plan referenced).

**Reasoning:** Original endpoint returned HTTP 404. CC catalog search confirmed `bdjb-hg6t` as the current dataset.

**Brief revisions required:**
- Appendix A row 13 implementation column: "data.wa.gov Report Card Teacher Experience Distribution 2022-23, school-level" → "data.wa.gov bdjb-hg6t (Report Card Teacher Experience Distribution School Years 2017-18 to 2024-25), school-level, filtered to 2024-25."

---

## PENDING

### R4. Race composition: vintage-matched white count

**Status:** Pending Blocker 3 resolution.

**Likely decision:** Use CCD 2023-24 white count (`enrollment.by_race.white`) divided by `enrollment.total`, rather than CRDC 2021-22 white count which mixes vintages.

**Brief revisions required (if confirmed):** Appendix A row 5 implementation column updated to specify CCD 2023-24 source. Probably a one-line change.

---

### R5. Chronic absenteeism null rate (22.6%)

**Status:** Pending Prompt 2 Task 5 diagnostic output.

**Issue:** 571 of 2,532 schools (22.6%) have null `derived.chronic_absenteeism_pct`. This is materially higher than the brief implicitly assumed. Methodology brief doesn't currently address how schools with null similarity variables are handled.

**Decision branches:**
- If Task 5 finds most nulls overlap with the existing 120-school exclusion union: no brief change needed. The variable is null mostly for schools the methodology already excludes.
- If many nulls are net-new coverage gaps (schools the methodology would otherwise include): brief needs an explicit null-handling section and possibly a new exclusion category. Could affect coverage statistics meaningfully.

**Revisit after:** Prompt 2 completes and Task 5 diagnostic is reviewed.

---

### R6. Exclusion logic for v1 methodology computation

**Status:** Pending Prompt 3 design.

**Issue:** The current exclusion union is 78 (manual list) ∪ 48 (Phase 3R reason codes) = 120 schools, with overlap of only 6. The 120 figure is correct but the underlying logic is "inherit from two legacy lists" rather than methodology-derived.

**Decision branches:** Prompt 3 will define exclusion logic from first principles (does the school have enough variables to compute a similarity vector; is the school in a category where peer matching is meaningful). The methodology brief should reference this derived logic, not the legacy union.

**Revisit after:** Prompt 3 methodology computation lands and the exclusion logic is locked.

---

### R7. Redundancy audit findings

**Status:** Pending Prompt 3 redundancy audit output.

**Possible outcomes:**
- No pairs above 0.70: Euclidean distance retained, brief unchanged on this point.
- One or more pairs above 0.70: builder decision required between consolidation and Mahalanobis. Brief revision will reflect whichever is chosen, including the empirical correlation values that drove the decision.

**Revisit after:** Prompt 3 methodology computation lands.

---

### R8. K sensitivity findings

**Status:** Pending Prompt 3 K sensitivity output.

**Possible outcomes:**
- Stable across K=10/20/30: K=20 retained, brief mentions stability finding as additional defense.
- Unstable: K choice matters more than triangulation argument suggests; brief revision needed to address.

**Revisit after:** Prompt 3 methodology computation lands.

---

### R9. Achievement sensitivity (Texas vs Nebraska) findings

**Status:** Pending Prompt 3 achievement sensitivity output.

**Brief impact:** Section 1.3 already commits to Texas-style exclusion with a sensitivity analysis as the empirical test. The section will gain a paragraph reporting the sensitivity findings (attenuation magnitude, schools that flip flags) when Prompt 3 completes. Q2b language already anticipates this.

**Revisit after:** Prompt 3 methodology computation lands.

---

## OPEN

### R10. Personnel Summary Report year vintage

**Status:** Open.

**Decision needed:** The OSPI Personnel Summary XLSX downloaded into the ingestion folder is the 2025-26 preliminary report. Earlier discussion suggested using most-recent-available data and accepting the vintage mismatch. Methodology brief currently states "OSPI Personnel Summary Reports 2023-24, Table 1" in Appendix A row A2, which doesn't match the file in the directory.

**Decision branches:**
- Confirm 2025-26 preliminary as the v1 commit, update the brief.
- Switch to 2023-24 final or 2024-25 final to better match other vintages.

**Action required:** Builder confirms which year is the v1 commit before Prompt 3 (which uses the salary data) executes. Methodology brief Appendix A row A2 updated to match.

---

## Notes for the eventual revision pass

When this list is processed into brief revisions:

1. The variable count change (21 → 20) cascades through Section 1.2's narrative paragraph and probably the count summary at the bottom of Appendix A. Worth a careful read of those passages, not just an in-place number swap.

2. R1 and R2 together change two of Nebraska's "borrowing" rows into one Exclude and one Documented Derivation. The brief's framing ("19 ported from Nebraska") needs adjustment to reflect that we're now porting 18 with 1 derivation and 4 exclusions (achievement excluded, suspensions excluded, expulsions excluded, masters excluded).

3. Reviewer questions log doesn't need any new numbered questions from R1-R3, but the Q2 cluster could gain a brief sub-question about teacher-variable derivation if it feels material. Probably not worth a new number.

4. Cover note to the reviewer should mention R1 explicitly: "v1 excludes teacher master's degree percentage due to data availability; v2 path is identified." Worth surfacing because the reviewer might assume the variable's exclusion was a deliberate methodology choice rather than a data constraint, and the difference matters.
