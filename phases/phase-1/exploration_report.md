# Phase 1 Data Exploration Report

**Date:** 2026-02-21
**Purpose:** Document everything we learned about the raw data files before building the pipeline. This report is the single reference for what data we have, how it fits together, and what surprises to watch for.

---

## What We Explored

We opened every raw data file, counted rows and columns, checked how schools are identified, found every suppression marker (codes that mean "we can't show you this number for privacy reasons"), and tested whether the files can be linked together. This report captures all of that so we never have to re-discover it.

---

## File Inventory

### Federal Data: CCD Directory (2024-25)

**File:** `ccd_sch_029_2425_w_1a_073025.csv` (extracted from a ZIP, 41 MB)

This is the federal government's master list of every school in the country. Think of it as the "phone book" for schools.

- **102,178 schools nationally**, 2,566 in Washington state
- **65 columns** covering: school IDs, names, addresses, school type, grade levels served, charter status
- Of the 2,566 WA schools: 2,532 are open, 21 are closed, 11 are new, 1 is planned for the future, and 1 is inactive

**Why this matters:** This file is the backbone. Every other file gets linked to it. If a school isn't in this file, it doesn't exist in our system.

---

### Federal Data: CCD Membership (2024-25)

**File:** `ccd_sch_052_2425_l_1a_073025.csv` (extracted from a ZIP, 2.3 GB)

This is the federal enrollment data, broken down by grade, race, and sex.

- **11,172,292 rows nationally**, 282,381 rows for WA, covering 2,543 unique WA schools
- **"Long format"** means one row per school/grade/race/sex combination (so a single school might have dozens of rows). 18 columns total.
- **103 schools show 0 enrollment** (likely closed schools or schools that haven't reported yet)
- Data quality flags (DMS_FLAG) show: 141,823 rows are directly reported, 73,738 were manually adjusted, 60,284 were derived (calculated from other numbers), and 6,536 were not reported
- **Important:** This file does NOT contain free/reduced lunch (FRL) data. That comes from OSPI instead.

---

### Federal Data: CRDC (2021-22)

**File:** `2021-22-crdc-data.zip` (794 MB, contains 35 CSV files inside)

The Civil Rights Data Collection. This is the only source for discipline, harassment, and equity data broken down by race, sex, and disability status. It comes from the U.S. Department of Education.

- **98,010 schools nationally**, 2,438 in WA
- **13 school-level files** were read, covering: enrollment, suspensions, expulsions, restraint and seclusion, referrals and arrests, harassment, school support, AP courses, dual enrollment, gifted programs, offenses, corporal punishment, and school characteristics
- Column counts range from 19 (school support) to 233 (enrollment)
- **This data is 3+ years old** (2021-22 school year). It is the most outdated source, but it's the only one with the disaggregated breakdowns (by race, sex, disability) that matter for civil rights analysis.

---

### State Data: OSPI Report Card

Washington state's own education data, published by the Office of Superintendent of Public Instruction (OSPI).

| File | Year | Total Rows | School-Level Rows | Columns |
|------|------|------------|-------------------|---------|
| Enrollment | 2023-24 | 20,565 | 2,465 | 46 |
| Assessment | 2023-24 | 761,859 | 596,782 | 34 |
| Discipline | 2023-24 | 459,850 | 359,002 | 29 |
| Growth | 2023-24 | 407,846 | 321,407 | 26 |
| Growth | 2024-25 | 406,365 | 320,223 | 26 |
| SQSS | 2024-25 | 769,933 | 607,905 | 35 |
| Per Pupil Expenditure (PPE) | 2019-2025 | 16,523 (multi-year) | -- | 16 |

"School-level rows" means rows where the data is about a specific school, not a district or state total. The pipeline filters to school-level only.

---

## How the Files Link Together (The Crosswalk)

A "crosswalk" is a mapping between different ID systems. Each data source uses its own way of identifying schools, and we need to connect them.

**Good news: no separate crosswalk file is needed.** The CCD Directory itself serves as the crosswalk.

### How It Works

- **CCD to OSPI:** The CCD Directory has a field called `ST_SCHID` with the format `WA-{DistrictCode}-{SchoolCode}`. This maps directly to OSPI's `DistrictCode` and `SchoolCode` fields. We just parse the CCD field to extract the codes.
- **CCD to CRDC:** The CRDC's `COMBOKEY` field is identical to the CCD's `NCESSCH` field. Both are 12-character strings. Direct match, no transformation needed.

### Match Rates

| Link | Matched | Total | Rate |
|------|---------|-------|------|
| OSPI to CCD | 2,459 | 2,465 | **99.8%** (6 unmatched) |
| CCD to CRDC | 2,373 | 2,566 | **92.5%** (193 unmatched) |
| Full chain: OSPI to CCD to CRDC | 2,342 | 2,465 | **95.0%** |

The 193 CCD schools missing from CRDC are schools that opened after the 2021-22 school year. This is expected -- those schools didn't exist when CRDC was collected.

---

## Suppression Markers

"Suppression" means the government hid a number to protect student privacy. For example, if only 3 students in a school are Native American, reporting their test scores could identify them. So the data says "suppressed" instead of showing the number.

**This is critical:** A suppressed value is NOT zero. "We can't tell you" is fundamentally different from "zero incidents." The pipeline must never confuse the two.

### CRDC Suppression Codes

| Code | Meaning | Count (WA) | How We Handle It |
|------|---------|------------|------------------|
| **-9** | Not applicable / skipped | 1,132,661 | Store as `null`. School doesn't serve those grades or programs. |
| **-5** | Small count suppression (fewer than 5 students) | 2,744 | Store as `null` with `"suppressed": true`. |
| **-4** | Teacher sex count suppression | 1,004 | Store as `null` with `"suppressed": true`. |
| **-3** | Secondary suppression (hidden to prevent back-calculating a suppressed cell) | 809 | Store as `null` with `"suppressed": true`. |
| **-12** | Unclear meaning, appears only in enrollment fields | 1,664 | Store as `null`. Needs further investigation during pipeline testing. |
| **-13** | Unclear meaning, appears only in restraint/seclusion | 30 | Store as `null`. Needs further investigation during pipeline testing. |
| **Genuine zero** | Zero incidents reported | 1,354,574 | Store as `0`. This is real data. |

### OSPI Suppression Markers

| Marker | Meaning | Approximate Count (WA) | How We Handle It |
|--------|---------|------------------------|------------------|
| **N<10** | Fewer than 10 students in category | ~550,000+ | Store as `null` with `"suppressed": true`. |
| **\*** | Masked numeric value (accompanies N<10) | ~323,000 | Store as `null` with `"suppressed": true`. |
| **No Students** | No students exist in this category | 109,154 | Store as `null`. Different from suppressed -- means "category doesn't apply." |
| **Top/Bottom Range** | Extreme values shown as inequalities (like "<27.3%") | ~170,000 | Parse the inequality. Store the boundary value with a flag. |
| **Cross Student Group - N<10** | Complementary suppression (hidden to prevent back-calculation) | ~70,000 | Store as `null` with `"suppressed": true`. |

### CCD Suppression Markers

| Marker | Meaning | Count (WA) |
|--------|---------|------------|
| **-1** | Data not available | Unknown count |
| **DMS_FLAG "Not reported"** | School did not submit data | 6,536 rows |

---

## Data Quality Surprises

These are things that weren't obvious from the documentation and could cause bugs if we don't handle them.

### 1. Commas Inside ID Numbers (OSPI Discipline)

**The problem:** In the OSPI discipline file only, the SchoolCode and DistrictCode fields contain embedded commas. For example, school code "2066" appears as "2,066".

**Why it matters:** If we try to match "2,066" against "2066" in the CCD file, the join will fail silently -- we'll just get no match and lose the data.

**The fix:** Strip commas from these fields before joining. This only affects the discipline file; all other OSPI files use plain numbers.

### 2. No Separate Attendance File

**The problem:** We expected a standalone "Attendance 2023-24" CSV file. It does not exist.

**What we found:** Attendance data lives inside the SQSS file (`Report_Card_SQSS_for_2024-25.csv`) under the measure called "Regular Attendance." The SQSS file contains three measures:
- Regular Attendance (389,725 school-level rows) -- this IS the attendance data
- Dual Credit (135,529 school-level rows)
- Ninth Grade on Track (82,651 school-level rows)

Also, the "Attendance DataNotes" Excel file is actually a duplicate of the Assessment DataNotes file. It does not contain attendance-specific documentation.

### 3. Grade Level Labels Are Inconsistent Across OSPI Files

Different OSPI files use different labels for the same thing:

| File | "All grades" label | Individual grade format |
|------|--------------------|----------------------|
| Enrollment | "All Grades" | -- |
| Assessment | "All Grades" | -- |
| Discipline | "All" | -- |
| Growth | "All Grades" | "06", "07", "08" (zero-padded) |
| SQSS | "All Grades" | "6", "7", "8" (not zero-padded) |

**The fix:** The pipeline must handle each file's conventions separately. We cannot assume a single filter value works across all files.

### 4. Growth DATReason='NULL' Is NOT Suppression

**The problem:** 146,117 school-level rows in the 2023-24 growth file have `DATReason='NULL'`. This looks like missing data but it isn't.

**What it actually means:** "No special reason." The actual data fields (MedianSGP, StudentCount) are present and valid in these rows. 'NULL' here means "this is a normal data row with no special data adjustment reason."

### 5. Free/Reduced Lunch Data Comes from OSPI, Not CCD

**The problem:** You might expect the federal enrollment file (CCD Membership) to include poverty data like free/reduced lunch (FRL) eligibility. It doesn't.

**Where to find it:** OSPI's enrollment file has a "Low Income" column. That's our FRL data source.

### 6. Mysterious -12 Values in CRDC Enrollment

1,664 instances of the value -12 appear in CRDC enrollment fields. This is not a documented suppression code. It appears only in derived/calculated enrollment columns.

**Confidence level:** Medium. We don't know exactly what -12 means. For now, we'll treat it as null and investigate further during pipeline testing.

### 7. Enrollment Numbers Differ Across Sources (This Is Normal)

For our reference school, Fairhaven Middle School:
- CCD (2024-25): **588 students**
- OSPI (2023-24): **585 students**

The 3-student difference is expected because these are different school years. The briefing must always disclose which year each number comes from so readers aren't confused by small differences.

### 8. PPE Enrollment Uses a Different Calculation

OSPI's Per Pupil Expenditure file shows Fairhaven's enrollment as **574.38** -- a decimal, not a whole number. This is because PPE uses FTE-weighted, annualized enrollment (full-time equivalent), which accounts for part-time students and mid-year transfers. It's a different concept from headcount enrollment.

---

## Data Vintage Summary

"Vintage" means what school year the data comes from. Not all sources are from the same year.

| Source | School Year | How Fresh? |
|--------|-------------|------------|
| CCD Directory and Membership | 2024-25 | Newest available |
| OSPI Growth, SQSS | 2024-25 | Newest available |
| OSPI Enrollment, Assessment, Discipline | 2023-24 | One year old |
| OSPI Per Pupil Expenditure | 2019-2025 | Multi-year trend data |
| CRDC | 2021-22 | **3+ years old** |

### What This Means for Briefings

- **~128 schools** exist in CCD but not CRDC. These are schools that opened after 2021-22. They will have CCD and OSPI data but no CRDC data. The briefing must note this gap.
- **CRDC discipline data is stale** (3+ years old) but is the **only source** for discipline data broken down by race, sex, and disability status. OSPI discipline data is newer (2023-24) but only provides aggregate rates without those breakdowns.
- **Every number in a briefing must cite its source year.** Readers need to know when "enrollment is 588" means 2024-25 CCD data and "48% low income" means 2023-24 OSPI data.

---

## Zero vs. Null: The Most Important Distinction

This is worth repeating because getting it wrong would be misleading.

- **Zero means zero.** Zero corporal punishment incidents at Fairhaven means Washington state doesn't allow corporal punishment and Fairhaven reported zero incidents. That's a real data point.
- **Null (suppressed) means "we can't tell you."** If a school has fewer than 5 Native American students suspended, the number is suppressed to protect their identity. We don't know if it's 1, 2, 3, or 4.
- **Not applicable means "doesn't apply."** Fairhaven's preschool enrollment is -9 in CRDC because Fairhaven is a middle school (grades 6-8). There's no preschool to count.

**In the database:**
- Zero is stored as `0`
- Suppressed is stored as `null` with `"suppressed": true`
- Not applicable is stored as `null` (no suppressed flag)
- **Never store a suppressed value as zero or empty string.**

---

## Summary of Key Decisions for Pipeline Design

1. **CCD is the backbone and the crosswalk.** Every school gets its identity from CCD. Other sources link to it.
2. **NCES ID is always a 12-character string.** Never convert to integer (leading zeros would be stripped).
3. **Strip commas from OSPI discipline IDs** before joining.
4. **Handle grade labels per-file** -- no universal filter value works across all OSPI files.
5. **Attendance data comes from the SQSS file**, not a separate attendance file.
6. **FRL/low-income data comes from OSPI enrollment**, not CCD.
7. **Every suppression code gets mapped to null** with appropriate flags. Zero stays zero.
8. **Every briefing number must cite its source and year.**
9. **CRDC -12 values are stored as null** pending further investigation.
10. **PPE enrollment (FTE-weighted) is kept separate** from headcount enrollment.
