# Phase 3R — Step 3: Cohort and Grade-Span Diagnostics

Read-only dump of peer cohort sizes and grade-span composition.

## 3.1 Peer cohort size histogram (current hard-bin approach)

Total cohorts: **35**
Total schools assigned to a cohort: **2323**
Schools in cohorts with < 5 members: **0** (0.0% of assigned schools)

**Query**:
```python
schools.aggregate([{"$match":{"derived.peer_cohort":{"$ne":None}}},{"$group":{"_id":"$derived.peer_cohort","n":{"$sum":1}}}])
```

| cohort size bucket | # of cohorts | # schools in those cohorts |
|---|---|---|
| 1 | 0 | 0 |
| 2 | 0 | 0 |
| 3-4 | 0 | 0 |
| 5-9 | 3 | 21 |
| 10-19 | 5 | 67 |
| 20-49 | 11 | 385 |
| 50+ | 16 | 1850 |

## 3.2 Grade-span breakdown by CCD level group

Grade strings as stored in MongoDB (CCD codes: PK, KG, 01–12, UG).

### 3.2.1 Common patterns the prompt asked for

Rows show the count of schools for each (low–high) → level_group combination.

| grade span (low-high) | level_group | count |
|---|---|---|
| KG-02 | Elementary | 7 |
| KG-03 | (no schools with this exact span) | 0 |
| KG-05 | Elementary | 380 |
| KG-06 | Elementary | 101 |
| KG-08 | Elementary | 65 |
| 06-08 | Middle | 318 |
| 07-08 | Middle | 23 |
| 06-12 | High | 65 |
| 06-12 | Other | 1 |
| 07-12 | High | 45 |
| 09-12 | High | 466 |

### 3.2.2 All other grade spans (count ≥ 1)

| grade span | level_group | count |
|---|---|---|
| 01-02 | Elementary | 1 |
| 01-03 | Elementary | 3 |
| 01-05 | Elementary | 7 |
| 01-08 | Elementary | 2 |
| 02-05 | Elementary | 3 |
| 02-06 | Elementary | 1 |
| 03-05 | Elementary | 17 |
| 03-06 | Elementary | 2 |
| 03-12 | Other | 6 |
| 04-05 | Elementary | 2 |
| 04-06 | Middle | 1 |
| 04-08 | Middle | 1 |
| 04-12 | Other | 1 |
| 05-06 | Middle | 6 |
| 05-07 | Middle | 2 |
| 05-08 | Middle | 18 |
| 05-12 | High | 5 |
| 06-07 | Middle | 3 |
| 06-09 | Middle | 1 |
| 06-10 | Middle | 4 |
| 07-09 | Middle | 7 |
| 07-10 | High | 1 |
| 08-09 | High | 3 |
| 08-12 | High | 18 |
| 09-10 | High | 1 |
| 10-11 | High | 1 |
| 10-12 | High | 26 |
| 11-12 | High | 19 |
| 12-12 | High | 6 |
| KG-04 | Elementary | 18 |
| KG-07 | Elementary | 3 |
| KG-09 | Other | 1 |
| KG-12 | Other | 112 |
| KG-KG | Elementary | 2 |
| PK-01 | Elementary | 4 |
| PK-02 | Elementary | 14 |
| PK-03 | Elementary | 5 |
| PK-04 | Elementary | 24 |
| PK-05 | Elementary | 488 |
| PK-06 | Elementary | 47 |
| PK-08 | Elementary | 24 |
| PK-09 | Other | 2 |
| PK-11 | Other | 1 |
| PK-12 | Other | 53 |
| PK-KG | Elementary | 14 |
| PK-PK | Other | 81 |

## 3.3 'Other' level group

- Total schools mapped to `level_group="Other"`: **258**
- Of those, regression-ready (have FRL + composite, not excluded): **20**
- Min group size for own model: 30
- 'Other' uses statewide fallback when n < min_group_size.

### Grade spans of schools mapped to 'Other'

| grade span | count |
|---|---|
| KG-12 | 112 |
| PK-PK | 81 |
| PK-12 | 53 |
| 03-12 | 6 |
| PK-09 | 2 |
| 04-12 | 1 |
| KG-09 | 1 |
| 06-12 | 1 |
| PK-11 | 1 |
