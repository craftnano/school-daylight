# Task 2 Test — get_findings_for_stage0() across canonical cases

Function under test: `pipeline.layer3_findings.get_findings_for_stage0(db, nces_id)`

Test runs the production query function against MongoDB Atlas, prints the
source counts, deduped count, and any collisions detected. The receipt
`docs/receipts/phase-5/task2_district_context.md` reads from this report.

## Bellingham HS — district_context only
**NCES ID:** `530042000099`
- School: Bellingham High School — district: Bellingham School District
- Source counts: school_context.findings=0, district_context.findings=6 (total before dedup: 6)
- Deduped findings to feed Stage 0: **6** (dropped by dedup: 0)
- school_context status: no_findings, district_context status: enriched

## Sehome HS — district + school, no URL overlap
**NCES ID:** `530042000113`
- School: Sehome High School — district: Bellingham School District
- Source counts: school_context.findings=4, district_context.findings=6 (total before dedup: 10)
- Deduped findings to feed Stage 0: **10** (dropped by dedup: 0)
- school_context status: enriched, district_context status: enriched

## Squalicum HS — district + school, KNOWN URL overlap on bus-assault article
**NCES ID:** `530042002693`
- School: Squalicum High School — district: Bellingham School District
- Source counts: school_context.findings=2, district_context.findings=6 (total before dedup: 8)
- Deduped findings to feed Stage 0: **7** (dropped by dedup: 1)
- school_context status: enriched, district_context status: enriched
- Dedup collisions:
  - `school -> district` key=(url | https://www.cascadiadaily.com/2026/feb/05/bellingham-public-schools-admits-liability-in-school-bus-sexual-assault-case/ | 2026-02-05 | investigations_ocr)
    school summary preview: Three administrators faced criminal charges for failing to report a sexual assault of a Squalicum High School student on...

## Fairhaven Middle (golden school)
**NCES ID:** `530042000104`
- School: Fairhaven Middle School — district: Bellingham School District
- Source counts: school_context.findings=1, district_context.findings=6 (total before dedup: 7)
- Deduped findings to feed Stage 0: **7** (dropped by dedup: 0)
- school_context status: enriched, district_context status: enriched

## Whatcom Middle
**NCES ID:** `530042000117`
- School: Whatcom Middle School — district: Bellingham School District
- Source counts: school_context.findings=1, district_context.findings=6 (total before dedup: 7)
- Deduped findings to feed Stage 0: **7** (dropped by dedup: 0)
- school_context status: enriched, district_context status: enriched

## Options HS (alternative)
**NCES ID:** `530042001738`
- School: Options High School — district: Bellingham School District
- Source counts: school_context.findings=1, district_context.findings=6 (total before dedup: 7)
- Deduped findings to feed Stage 0: **7** (dropped by dedup: 0)
- school_context status: enriched, district_context status: enriched

## Bainbridge HS (non-Bellingham control)
**NCES ID:** `530033000043`
- School: Bainbridge High School — district: Bainbridge Island School District
- Source counts: school_context.findings=1, district_context.findings=4 (total before dedup: 5)
- Deduped findings to feed Stage 0: **5** (dropped by dedup: 0)
- school_context status: enriched, district_context status: enriched

## Bogus ID — error path test
**NCES ID:** `999999999999`
**Error path:** School with NCES ID '999999999999' not found in MongoDB. Confirm the ID is the 12-character string (leading zeros preserved) and that the schools collection has been loaded for this state.
