# Phase 3R — Step 1: Per-Level Regression Diagnostics

Read-only diagnostic dump of the current per-level FRL→proficiency_composite regression.
Re-fits regressions in-process from the same MongoDB inputs production uses,
rather than reading the cached `regression_*` fields, so methodology questions
(R², slopes, residual SDs) trace to live data.

Source script: `pipeline/15_regression_and_flags.py`
Source config: `flag_thresholds.yaml` (regression block, line 51)

- regression min_group_size: **30**
- regression threshold_sd: **±1.0**
- excluded school types: **['Alternative School', 'Career and Technical School', 'Special Education School']**
- manual exclusions (school_exclusions.yaml): **78**

Total documents scanned from MongoDB: **2532**

**Example query** (the document scan above):
```python
schools.find({}, {"_id":1,"demographics.frl_pct":1,"derived.proficiency_composite":1,"derived.level_group":1,"derived.performance_flag":1,"derived.performance_flag_absent_reason":1,"school_type":1})
```

- regression-ready schools (have FRL + composite + level_group, not excluded): **1145**
- excluded by school_type: **96**
- excluded by manual list: **8**

## 1.1 Per-level regression statistics

| Level group | n | R² | Residual SD | Intercept | Slope (FRL coef) | Model used |
|---|---|---|---|---|---|---|
| Elementary | 747 | 0.747 | 0.0918 | 0.826 | -0.671 | per-level |
| High | 179 | 0.543 | 0.1005 | 0.712 | -0.545 | per-level |
| Middle | 199 | 0.663 | 0.0970 | 0.735 | -0.612 | per-level |
| Other | 20 | 0.685 (statewide) | 0.0998 (statewide) | 0.793 (statewide) | -0.647 (statewide) | statewide fallback |
| **Statewide (fallback model)** | 1145 | 0.685 | 0.0998 | 0.793 | -0.647 | — |

## 1.2 Performance-flag distribution within each level group

Flag is computed against the model that level group actually uses (per-level if n ≥ 30, otherwise statewide).

| Level group | n flagged | outperforming | as_expected | underperforming |
|---|---|---|---|---|
| Elementary | 747 | 106 (14.2%) | 529 (70.8%) | 112 (15.0%) |
| High | 179 | 24 (13.4%) | 137 (76.5%) | 18 (10.1%) |
| Middle | 199 | 21 (10.6%) | 157 (78.9%) | 21 (10.6%) |
| Other | 20 | 1 (5.0%) | 8 (40.0%) | 11 (55.0%) |

## 1.3 FRL_pct and proficiency_composite ranges within each level group's regression set

| Level group | Var | min | p25 | p50 | p75 | max |
|---|---|---|---|---|---|---|
| Elementary | FRL_pct | 0.0000 | 0.3226 | 0.5234 | 0.6891 | 0.9575 |
| Elementary | proficiency_composite | 0.0815 | 0.3500 | 0.4720 | 0.6222 | 0.9345 |
| High | FRL_pct | 0.0000 | 0.3416 | 0.4801 | 0.6275 | 0.9519 |
| High | proficiency_composite | 0.0450 | 0.3442 | 0.4475 | 0.5315 | 0.8245 |
| Middle | FRL_pct | 0.0000 | 0.3491 | 0.5508 | 0.6778 | 0.9702 |
| Middle | proficiency_composite | 0.0520 | 0.3030 | 0.4015 | 0.5250 | 0.8135 |
| Other | FRL_pct | 0.0000 | 0.5277 | 0.6178 | 0.7087 | 0.8689 |
| Other | proficiency_composite | 0.1250 | 0.2014 | 0.2850 | 0.3730 | 0.5590 |

## 1.4 Null performance_flag breakdown by absent reason

Reads `derived.performance_flag` and `derived.performance_flag_absent_reason` from MongoDB exactly as production wrote them — does not recompute.

Total schools with `performance_flag = null`: **1387**

**Query**:
```python
schools.aggregate([{"$match":{"derived.performance_flag":None}},{"$group":{"_id":"$derived.performance_flag_absent_reason","n":{"$sum":1}}}])
```

| absent reason | count | % of nulls |
|---|---|---|
| data_not_available | 832 | 60.0% |
| school_type_not_comparable | 468 | 33.7% |
| grade_span_not_tested | 87 | 6.3% |
