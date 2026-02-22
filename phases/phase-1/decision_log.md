# Phase 1 Decision Log

This document records every mapping and data-handling decision made during Phase 1 (data exploration and schema design). Each entry explains what was decided, why, and what the alternatives were.

If you need to change how data flows through the pipeline, start here. Understanding these decisions will tell you why things are set up the way they are.

---

## Data Source Decisions

### Decision 1: CCD Directory as the "spine"

**What:** CCD Directory 2024-25 is the canonical list of Washington State schools. It provides the master NCES ID for every school. Every other data source joins to this list. If a school is not in the CCD Directory, it does not exist in our system.

**Why:** The CCD Directory has the most schools (2,566), is the newest year available (2024-25), and contains the ST_SCHID field that maps directly to OSPI school codes. It is the only file that has both the federal ID (NCES) and the state ID (OSPI) in one place.

**Alternative considered:** Use OSPI enrollment as the base list of schools. Rejected because OSPI has fewer schools (2,465 vs. 2,566) and does not include NCES IDs directly, so we would still need the CCD to get federal IDs.

**Confidence:** high

---

### Decision 2: CCD IS the crosswalk

**What:** The ST_SCHID field in CCD Directory (format: WA-{DistrictCode}-{SchoolCode}) directly maps to OSPI's district and school codes. No separate crosswalk file is needed to connect federal (NCES) data to state (OSPI) data.

**Why:** Testing confirmed a 99.8% match rate when parsing ST_SCHID into district and school codes and joining to OSPI files. A separate crosswalk file would add complexity, another file to maintain, and another potential point of failure -- all for no improvement in match rate.

**Alternative considered:** Download a separate NCES-to-OSPI crosswalk file from NCES or OSPI. Not needed because the join already works at 99.8% using ST_SCHID.

**Confidence:** high

---

### Decision 3: FRL from OSPI, not CCD

**What:** Free and Reduced-Price Lunch (FRL) data comes from OSPI enrollment's "Low Income" column. It does NOT come from CCD.

**Why:** This was not obvious from the file names. CCD has a file called "Membership" that sounds like it might have income data, but it only contains race/ethnicity, sex, and grade breakdowns. OSPI enrollment is the only source that has an income-status column. This was verified by inspecting the actual columns in both files.

**Alternative considered:** Use CCD Membership for FRL. Not possible -- the data simply is not there.

**Confidence:** high

---

### Decision 4: Enrollment from CCD (primary) with OSPI (secondary)

**What:** CCD Membership 2024-25 is the primary enrollment source. OSPI enrollment 2023-24 is the secondary source. Both are kept in the schema.

**Why:** They serve different purposes. CCD provides the most recent total enrollment and race/ethnicity breakdown (2024-25 data). OSPI provides demographic subgroups that CCD does not have: FRL (low income), ELL (English language learners), and SPED (special education). Dropping either source would lose information.

**Alternative considered:** Use only one enrollment source. Rejected because no single source has all the demographic breakdowns we need.

**Confidence:** high

---

## Join and Matching Decisions

### Decision 5: CRDC join via COMBOKEY = NCESSCH

**What:** CRDC's COMBOKEY field is identical to CCD's NCESSCH field -- both are the same 12-character NCES ID string. The join between CRDC and CCD requires no transformation, no parsing, and no intermediate mapping.

**Why:** COMBOKEY is already the concatenation of LEAID (7-digit district ID) and SCHID (5-digit school ID within district). Since NCESSCH is the same concatenation, the fields match exactly.

**Alternative considered:** Join via LEAID and SCHID as separate fields, then concatenate. This would work but adds unnecessary complexity since COMBOKEY already does that concatenation.

**Confidence:** high

---

### Decision 6: Growth data -- prefer 2024-25 with 2023-24 fallback

**What:** When both 2024-25 and 2023-24 growth data are available for a school, use 2024-25. If a school is missing from 2024-25, fall back to 2023-24.

**Why:** 2024-25 is newer and has a comparable file structure. Using the newest available data gives the most current picture of student growth. The fallback ensures we do not lose schools that happen to be missing from the newer file.

**Alternative considered:** Use only one year. Rejected because some schools are only present in one year or the other, and we want maximum coverage.

**Confidence:** high

---

### Decision 7: OSPI discipline comma-cleaning rule

**What:** Before joining the OSPI discipline file to other data, strip commas from the DistrictCode and SchoolCode columns. This is done in the cleaning rules, not in ad-hoc code.

**Why:** The discipline file has commas embedded in numeric code fields (e.g., "1,234" instead of "1234"). No other OSPI file has this issue. Without stripping the commas, the join to other OSPI files fails because "1,234" does not match "1234". This is a formatting inconsistency in the source data, not an intentional feature.

**Alternative considered:** Leave the commas and adjust all join logic to account for them. Rejected because this would mean every join involving discipline data needs special handling. Cleaning the data once at load time is simpler and less error-prone.

**Confidence:** high

---

### Decision 8: Attendance from SQSS only

**What:** Regular Attendance data comes from the SQSS (School Quality and Student Success) file. There is no separate attendance CSV.

**Why:** Despite attendance being listed as a potential separate data source in early planning, no standalone attendance file exists in the OSPI downloads. Regular Attendance is a measure embedded within the SQSS file alongside other accountability indicators. One source, no overlap, no ambiguity.

**Alternative considered:** Look for a separate attendance file. None exists.

**Confidence:** high

---

## Suppression and Special Value Decisions

### Decision 9: CRDC suppression codes -- each negative number means something different

**What:** CRDC uses specific negative numbers as suppression codes, and each one has a distinct meaning:

| Code | Meaning | Frequency |
|------|---------|-----------|
| -9   | Not applicable (school does not serve this grade level, etc.) | 1.1 million occurrences |
| -5   | Small count (fewer than a threshold, suppressed to protect privacy) | Less common |
| -4   | Suppressed due to teacher sex (could identify individuals) | Rare |
| -3   | Secondary suppression (suppressed because another value was suppressed and this one could be back-calculated) | Less common |

Zero means zero incidents. This is critically different from any negative code.

**Why:** Treating all negative values the same would lose important context. A school with -9 for high school suspensions is a middle school -- that is not a data quality issue. A school with -5 has real suspension data that is hidden for privacy. The briefing needs to handle these differently.

**Alternative considered:** Treat all negative values as generic "suppressed." Rejected because -9 (not applicable) and -5 (small count) convey very different information about the school.

**Confidence:** high

---

### Decision 10: OSPI suppression -- "N<10" vs. "No Students" are different

**What:** In OSPI data, "N<10" means students exist in this category but the count is too small to disclose (privacy suppression). "No Students" means the school genuinely has zero students in that category.

**Why:** These are fundamentally different situations. "N<10" for FRL at a school means the school has some low-income students, but fewer than 10, so the exact count is hidden. "No Students" for 9th-grade-on-track at a middle school means the school has no 9th graders at all. Conflating them would misrepresent the school.

**Alternative considered:** Treat both as suppressed. Rejected because "No Students" is real information (zero students in that group), not hidden information.

**Confidence:** high

---

### Decision 11: CRDC -12 and -13 -- undocumented codes, flagged for investigation

**What:** CRDC data contains two negative codes not documented in the official CRDC manual:
- **-12** appears 1,664 times, only in enrollment fields
- **-13** appears 30 times, only in restraint/seclusion fields

Both are stored with an "unknown_negative" flag and treated as suppressed until their meaning can be confirmed.

**Why:** We cannot confidently interpret values that are not in the documentation. Treating them as suppressed is the safest default -- it prevents us from presenting data we do not understand as if we do understand it. The flag ensures they are easy to find and update later if the meaning is clarified.

**Alternative considered:** Ignore these values or treat them as zero. Rejected because -12 appears 1,664 times, which is too frequent to ignore, and treating undocumented codes as zero could misrepresent schools.

**Confidence:** medium

---

### Decision 12: Top/Bottom Range values in OSPI treated as suppressed

**What:** OSPI discipline rates sometimes show values like "<27.3%" instead of an exact percentage. These represent extreme values where the exact rate could identify individual students. These are stored as null with a suppressed flag.

**Why:** These range indicators exist for privacy protection. Parsing "<27.3%" and storing 0.273 would present an approximate value as if it were exact, which could mislead. The purpose of the range notation is to say "we cannot tell you the exact number," and our data should respect that.

**Alternative considered:** Parse the threshold value (e.g., extract 27.3 from "<27.3%") and store it as an approximate value. Rejected because the approximation could mislead readers into thinking it is a real measurement.

**Confidence:** high

---

### Decision 13: Grade level handling varies by file -- no universal label

**What:** Each OSPI file uses different conventions for grade labels:
- Discipline uses "All"
- Other files use "All Grades"
- Growth uses zero-padded grades ("06")
- SQSS uses unpadded grades ("6")

Each file gets its own filter logic in the pipeline. There is no attempt to create a universal grade label.

**Why:** Forcing all files into one format would require transformations that could silently break if OSPI changes their formatting. It is safer to filter each file using the conventions that file actually uses. The filter logic is explicit in the cleaning rules YAML, so it is easy to see what each file expects.

**Alternative considered:** Normalize all grade labels to a common format before filtering. Rejected because the normalization itself is fragile (what if a future file uses yet another format?) and the current approach is transparent and easy to debug.

**Confidence:** high

---

### Decision 14: OSPI growth DATReason='NULL' is NOT suppression

**What:** In the OSPI growth file, the DATReason column sometimes contains the literal string 'NULL'. This is the default value meaning "no special reason" -- the growth data for that row is valid and present. Only DATReason='N<10' or DATReason='Cross Group' indicate actual suppression.

**Why:** This was discovered by checking whether schools with DATReason='NULL' still have valid MedianSGP values. They do. If we had treated 'NULL' as suppression, we would have incorrectly discarded valid growth data for a large number of schools.

**Alternative considered:** Treat 'NULL' as missing data. Rejected because the growth scores are present and valid for these rows. The 'NULL' string is just an unfortunate default value in the source data.

**Confidence:** high

---

## Schema and Storage Decisions

### Decision 15: PPE enrollment is FTE-weighted, not headcount

**What:** The Per-Pupil Expenditure (PPE) file reports enrollment as a decimal (e.g., Fairhaven shows 574.38, not 588). This is an FTE (Full-Time Equivalent) weighted calculation, not a simple headcount.

**Why:** PPE enrollment weights students differently based on their enrollment status (part-time students count as less than 1.0). This number is correct for PPE calculations but would be misleading as a general enrollment figure. CCD reports 588 and OSPI reports 585 for Fairhaven -- those are headcounts and are the right numbers for general enrollment reporting.

**Alternative considered:** Use PPE enrollment as another enrollment source. Rejected because the FTE weighting makes it incompatible with headcount enrollment from other sources.

**Confidence:** high

---

### Decision 16: GAO caveat on restraint/seclusion data

**What:** CRDC restraint and seclusion data is stored in the schema, but any briefing that references it must include an explicit caveat about known data quality issues identified by the U.S. Government Accountability Office (GAO).

**Why:** The GAO has flagged concerns about the accuracy and completeness of restraint/seclusion reporting in CRDC data. Some schools may underreport. Presenting this data without a caveat would imply more confidence in it than is warranted.

**Alternative considered:** Exclude restraint/seclusion data entirely. Rejected because the data is still informative when presented with appropriate caveats, and excluding it would leave a gap in school safety information.

**Confidence:** medium (in the data quality; high confidence in the decision to include it with a caveat)

---

### Decision 17: WA corporal punishment -- all zeros expected

**What:** Washington State prohibits corporal punishment. All WA schools should show SCH_CORP_IND=No and zero counts for corporal punishment incidents in CRDC data.

**Why:** This is important context for data validation. If any WA school shows corporal punishment as "Yes" or has non-zero counts, that is a data quality error in the source, not a real finding. The pipeline should flag this as an anomaly rather than reporting it as fact.

**Alternative considered:** Report corporal punishment data at face value for all states. Rejected for WA because state law makes non-zero values impossible, so they would indicate bad data, not real events.

**Confidence:** high

---

### Decision 18: Schema uses one document per school, everything embedded

**What:** The MongoDB schema stores one document per school with all data embedded -- enrollment, demographics, discipline, growth, attendance, expenditure, CRDC data, and eventually the AI-generated briefing. No references to other collections. No joins at read time.

**Why:** This follows MongoDB best practice for the access pattern "give me everything about school X," which is the only query the frontend needs. Each document will be well under 1 MB (MongoDB's limit is 16 MB). Embedding means the frontend makes one database call per school, which keeps the Streamlit app simple and fast.

**Alternative considered:** Normalize into separate collections (one for enrollment, one for discipline, etc.) and join at query time. Rejected because normalization adds complexity to both the pipeline (maintaining multiple collections) and the frontend (joining at read time), with no benefit for our use case.

**Confidence:** high

---

### Decision 19: All percentages stored as 0.0-1.0 decimals

**What:** Every percentage in the schema is stored as a decimal between 0.0 and 1.0. For example, 64.9% is stored as 0.649. This applies regardless of how the source data formats it (OSPI uses strings like "64.90%", some fields use decimals like 0.6631).

**Why:** Mixing scales (some fields as 0-100, others as 0.0-1.0) is a common source of bugs that are hard to catch because a value like 48.2 could be either 48.2% (on the 0-100 scale) or 4,820% (on the 0.0-1.0 scale). Standardizing to one scale eliminates this ambiguity. The 0.0-1.0 scale was chosen because it is the mathematical convention and avoids confusion with raw counts.

**Alternative considered:** Store percentages as 0-100 values. Either convention works as long as it is consistent. 0.0-1.0 was chosen per the project-wide rule in CLAUDE.md.

**Confidence:** high

---

### Decision 20: NCES IDs always stored as strings

**What:** NCES IDs are 12-character strings (e.g., "530042000104") and are always stored and read as strings, never as integers. Every pandas read operation that touches NCES IDs uses `dtype=str` to prevent automatic type conversion.

**Why:** If an NCES ID is read as an integer, leading zeros are stripped. "530042000104" becomes 530042000104 (an 11-digit integer if the leading zero were significant, though in this case WA codes start with "53"). More importantly, some NCES IDs in other states DO have meaningful leading zeros, and allowing integer conversion anywhere in the pipeline creates a pattern that will eventually break joins. Enforcing string type everywhere eliminates this class of bug entirely.

**Alternative considered:** Read as integer and zero-pad back to 12 characters when needed. Rejected because this is fragile -- you have to remember to pad every time you use the ID, and forgetting once silently breaks the join with no error message.

**Confidence:** high

---

## Summary

These 20 decisions form the foundation of the data pipeline. The most important principles they reflect:

1. **Use the newest, most complete data source as the spine** (Decisions 1, 4, 6)
2. **Suppression is not the same as zero or missing** (Decisions 9, 10, 11, 12, 14)
3. **Clean data once at load time, not repeatedly at query time** (Decisions 2, 7, 13)
4. **Store data in a way that prevents misinterpretation** (Decisions 15, 16, 17, 19, 20)
5. **When in doubt, flag it and move on** (Decisions 11, 16)

If you are changing the pipeline and something breaks, check this log first. The answer to "why is it done this way?" is probably here.
