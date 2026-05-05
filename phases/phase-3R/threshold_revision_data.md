# Phase 3R — Step 2: Threshold Revision Distributions

Read-only distributions of the two threshold-driven flag metrics. No data changes; counts here are what production *would* show under candidate thresholds.

## 2.1 Chronic absenteeism (`derived.chronic_absenteeism_pct`)

N (non-null) = **1961** schools

**Query**:
```python
schools.find({"derived.chronic_absenteeism_pct":{"$ne":None}},{"derived.chronic_absenteeism_pct":1})
```

### Distribution summary

| stat | value |
|---|---|
| min | 0.0013 |
| p10 | 0.0784 |
| p20 | 0.1380 |
| p25 | 0.1564 |
| p30 | 0.1765 |
| p40 | 0.2130 |
| p50 (median) | 0.2460 |
| p60 | 0.2769 |
| p70 | 0.3097 |
| p75 | 0.3303 |
| p80 | 0.3525 |
| p90 | 0.4197 |
| max | 0.9762 |
| mean | 0.2541 |
| SD | 0.1443 |

### Decile bin counts (sanity check — bins sum to N)

| bin | range (lower ≤ x < upper) | count |
|---|---|---|
| d1 | 0.0000 – 0.0784 | 196 |
| d2 | 0.0784 – 0.1380 | 196 |
| d3 | 0.1380 – 0.1765 | 196 |
| d4 | 0.1765 – 0.2130 | 196 |
| d5 | 0.2130 – 0.2460 | 196 |
| d6 | 0.2460 – 0.2769 | 194 |
| d7 | 0.2769 – 0.3097 | 198 |
| d8 | 0.3097 – 0.3525 | 196 |
| d9 | 0.3525 – 0.4197 | 196 |
| d10 | 0.4197 – 1.0000 | 197 |
| **sum** | — | 1961 |

### Schools that would trip yellow/red at candidate threshold pairs

Yellow: `value > yellow_threshold AND value ≤ red_threshold`. Red: `value > red_threshold`. (Mirrors `pipeline/15_regression_and_flags.py:308`.)

| (yellow, red) | note | green | yellow | red |
|---|---|---|---|---|
| (0.20, 0.30) | current | 708 (36.1%) | 613 (31.3%) | 640 (32.6%) |
| (0.25, 0.35) | candidate | 1004 (51.2%) | 557 (28.4%) | 400 (20.4%) |
| (0.30, 0.40) | candidate | 1321 (67.4%) | 396 (20.2%) | 244 (12.4%) |
| (0.30, 0.45) | candidate, decided 2026-02-22 | 1321 (67.4%) | 499 (25.4%) | 141 (7.2%) |
| (0.35, 0.50) | candidate | 1561 (79.6%) | 305 (15.6%) | 95 (4.8%) |

### Percentile-based threshold scenario (bottom-quartile yellow / bottom-decile red)

Lower attendance = worse, so 'bottom' here means HIGHEST chronic absenteeism. Yellow = top-25% of values; Red = top-10%.

| thresholds | yellow boundary (p75) | red boundary (p90) | green | yellow | red |
|---|---|---|---|---|---|
| percentile-based | 0.3303 | 0.4197 | 1471 (75.0%) | 295 (15.0%) | 195 (9.9%) |

## 2.2 Discipline disparity max (`derived.discipline_disparity_max`)

N (non-null) = **1300** schools

### Distribution summary

| stat | value |
|---|---|
| min | 0.0000 |
| p10 | 0.0000 |
| p20 | 0.6400 |
| p25 | 0.8800 |
| p30 | 1.1370 |
| p40 | 1.5520 |
| p50 (median) | 2.0100 |
| p60 | 2.4900 |
| p70 | 3.1700 |
| p75 | 3.7525 |
| p80 | 4.4400 |
| p90 | 6.7760 |
| max | 74.7300 |
| mean | 3.1927 |
| SD | 4.8345 |

### Decile bin counts

| bin | range | count |
|---|---|---|
| d1 | 0.00 – 0.00 | 0 |
| d2 | 0.00 – 0.64 | 259 |
| d3 | 0.64 – 1.14 | 131 |
| d4 | 1.14 – 1.55 | 130 |
| d5 | 1.55 – 2.01 | 127 |
| d6 | 2.01 – 2.49 | 131 |
| d7 | 2.49 – 3.17 | 130 |
| d8 | 3.17 – 4.44 | 131 |
| d9 | 4.44 – 6.78 | 131 |
| d10 | 6.78 – 74.73 | 130 |
| **sum** | — | 1300 |

### Yellow/red counts at current thresholds (2.0 / 3.0)

| thresholds | green | yellow | red |
|---|---|---|---|
| (2.0, 3.0) [current] | 647 (49.8%) | 236 (18.2%) | 417 (32.1%) |

## 2.3 Subgroup-size sensitivity for disparity

Recompute `discipline_disparity_max` from `discipline.crdc.*` and `enrollment.crdc_by_race` (race breakdowns) at varying minimum-N thresholds. Mirrors `pipeline/12_compute_ratios.py:77` (currently hard-coded to `>=10`).

**Query** (the source pull for this section):
```python
schools.find({}, {"_id":1,"discipline.crdc.iss":1,"discipline.crdc.oss_single":1,"discipline.crdc.oss_multiple":1,"enrollment.crdc_by_race":1,"derived.flags.discipline_disparity.color":1})
```

| min subgroup-N | schools with non-null disparity_max | currently-flagged schools that lose flag |
|---|---|---|
| 10 (current) | 1300 | 0 |
| 15 | 1266 | 71 |
| 20 | 1232 | 120 |
| 25 | 1201 | 164 |
| 30 | 1163 | 197 |
| 40 | 1084 | 270 |

> Currently flagged yellow OR red on `discipline_disparity`: **653** schools.
