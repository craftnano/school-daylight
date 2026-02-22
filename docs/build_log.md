# Build Log

Chronological record of decisions, findings, and changes with reasoning.

---

## 2026-02-22 — Echo Glen School added to exclusions

**Context:** During pre-Phase 4 FRL data review, Echo Glen School (NCES 530375001773, Issaquah School District) appeared on the list of schools with FRL >= 95% (97.1%). Echo Glen is a DSHS juvenile detention facility. CCD codes it as "Regular School" — the same misclassification pattern discovered for virtual/online schools in Phase 3.

**Finding:** Echo Glen's 97.1% FRL reflects its institutional population, not community poverty. Issaquah School District provides educational services at the facility, but enrollment is involuntary and transient. Comparing it against traditional schools on a FRL-vs-proficiency curve is misleading for the same reasons documented in Phase 3 decision log #2.

**Action:** Added to `school_exclusions.yaml` under a new "Institutional facilities" category. Performance flag was already null (reason: `data_not_available`) — will be reclassified to `school_type_not_comparable` on next pipeline run.

**Impact:** No change to regression pool (Echo Glen was already excluded from regression due to missing proficiency data). The reason code change is more accurate documentation.
