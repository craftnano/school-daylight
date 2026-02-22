# Schema Preflight Check

**Date:** 2026-02-21
**Purpose:** Verify MongoDB document sizes are well within the 16 MB limit.

---

## Target School Documents

| School | NCESSCH | Enrollment | JSON Bytes | KB |
|--------|---------|-----------|------------|-----|
| Fairhaven Middle School | 530042000104 | 588 | 5,799 | 5.7 |
| Chiawana Senior High School | 530657003292 | 3127 | 6,142 | 6.0 |
| Tahoma Senior High School | 530876001519 | 2919 | 5,852 | 5.7 |
| Insight School of Washington | 530702003078 | 2841 | 5,399 | 5.3 |
| Pasco Senior High School | 530657000969 | 2590 | 6,137 | 6.0 |
| Eastlake High School | 530423001141 | 2481 | 6,181 | 6.0 |

## Section Size Breakdown (Fairhaven)

| Section | Bytes | % of Total |
|---------|-------|-----------|
| discipline | 1,561 | 28.2% |
| safety | 1,391 | 25.1% |
| academics | 642 | 11.6% |
| course_access | 522 | 9.4% |
| metadata | 339 | 6.1% |
| staffing | 262 | 4.7% |
| enrollment | 205 | 3.7% |
| demographics | 182 | 3.3% |
| finance | 133 | 2.4% |
| address | 84 | 1.5% |
| district | 60 | 1.1% |
| website | 41 | 0.7% |
| grade_span | 27 | 0.5% |
| name | 25 | 0.5% |
| school_type | 16 | 0.3% |
| phone | 15 | 0.3% |
| _id | 14 | 0.3% |
| level | 8 | 0.1% |
| is_charter | 5 | 0.1% |
| **TOTAL** | **5,532** | **100%** |

## Section Size Breakdown (Largest: Bethel Virtual Academy)

| Section | Bytes | % of Total |
|---------|-------|-----------|
| discipline | 1,564 | 25.4% |
| safety | 1,416 | 23.0% |
| course_access | 1,141 | 18.6% |
| academics | 646 | 10.5% |
| metadata | 339 | 5.5% |
| staffing | 264 | 4.3% |
| enrollment | 206 | 3.4% |
| demographics | 181 | 2.9% |
| finance | 135 | 2.2% |
| address | 84 | 1.4% |
| district | 56 | 0.9% |
| grade_span | 27 | 0.4% |
| name | 24 | 0.4% |
| school_type | 20 | 0.3% |
| phone | 15 | 0.2% |
| _id | 14 | 0.2% |
| level | 7 | 0.1% |
| is_charter | 5 | 0.1% |
| website | 2 | 0.0% |
| **TOTAL** | **6,146** | **100%** |

## Size Distribution (All WA Schools)

| Metric | Value |
|--------|-------|
| Schools with documents | 2,566 |
| Maximum | 6,413 bytes (6.3 KB) |
| 95th percentile | 6,134 bytes (6.0 KB) |
| Median | 5,737 bytes (5.6 KB) |
| Minimum | 1,183 bytes (1.2 KB) |
| Schools > 1 MB | 0 |
| Schools > 16 MB | 0 |

## Verdict

The largest document is **6.3 KB** — well under the 1 MB concern threshold
and nowhere near the 16 MB MongoDB limit.

Even after Phase 4 adds AI context (estimated ~2-5 KB of news/reputation findings)
and Phase 5 adds the cached briefing narrative (estimated ~5-10 KB of text),
the largest documents would still be under **21 KB** — about
**2.1%** of the 1 MB soft target.

**No schema redesign needed.** ✓