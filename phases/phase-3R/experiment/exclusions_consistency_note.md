# Phase 3R — Exclusions Consistency Note

Generated: **2026-05-04T06:43:44Z**

## What this is

Phase 3R Census ingestion produced a SKIP list of schools where a district-level ACS join doesn't apply (charters, statewide specialty schools, institutional facilities, regional alternative programs, tribal community schools). The pre-existing `school_exclusions.yaml` list, used by the FRL-vs-proficiency regression to suppress the performance flag, was built incrementally for a different purpose.

This note inventories the schools that appear on the new SKIP list but NOT on `school_exclusions.yaml`, grouped by SKIP reason. It is a methodology question for follow-up — not a request to change either list.

**Scope:** experiment database only. `school_exclusions.yaml` is untouched. Production is untouched.

## Headline counts

| Bucket | Count |
|---|---|
| Total SKIP schools (post-patch) | 48 |
| Of those, already on `school_exclusions.yaml` | 6 |
| **Consistency gap (SKIP but NOT in school_exclusions.yaml)** | **42** |

## Per-category breakdown

| SKIP category | Total SKIP | Already in exclusions.yaml | Gap |
|---|---|---|---|
| Charters (pending district assignment) | 17 | 0 | 17 |
| Statewide specialty schools | 8 | 0 | 8 |
| Institutional facilities | 10 | 5 | 5 |
| Regional alternative / reengagement programs | 12 | 1 | 11 |
| Tribal community schools | 1 | 0 | 1 |

## The 39-school consistency gap, by category

Schools below are SKIPped from Census ingestion but currently flow through the FRL-vs-proficiency regression because they're not on `school_exclusions.yaml`.

### Charters (pending district assignment) (17 schools)

These charters will be reassigned to the operating district their physical address falls within in a follow-up step. They are not currently on `school_exclusions.yaml` because the existing list predates the methodology shift toward peer-cohort matching.

| _id | School name | Type | District | Grade span | Enrollment | City |
|---|---|---|---|---|---|---|
| `530034903783` | Cascade Public Schools | Regular School (charter) | Why Not You Academy | 09-12 | 126 | Des Moines |
| `530034703723` | Catalyst Public Schools | Regular School (charter) | Catalyst Public Schools | KG-09 | 504 | Bremerton |
| `530035403782` | Impact Public Schools | Regular School (charter) | Impact | Commencement Bay Elementary | PK-05 | 232 | Tacoma |
| `530034503653` | Impact Public Schools | Regular School (charter) | Impact | Puget Sound Elementary | KG-05 | 505 | Tukwila |
| `531017203905` | Impact | Black River Elementary | Regular School (charter) | Impact | Black River Elementary | KG-05 | 209 | Renton |
| `530034803749` | Impact | Salish Sea Elementary | Regular School (charter) | Impact | Salish Sea Elementary | KG-05 | 385 | Seattle |
| `530033903495` | Innovation High School | Regular School (charter) | PRIDE Prep Charter School District | 09-12 | 232 | Spokane |
| `530035103831` | Intergenerational High School | Regular School (charter) | Intergenerational High School | 09-12 | 107 | Bellingham |
| `530035003770` | Lumen High School | Regular School (charter) | Lumen Public School | 09-12 | 32 | Spokane |
| `530035203807` | Pinnacles Prep Charter School | Regular School (charter) | Pinnacles Prep Charter School | 06-10 | 234 | Wenatchee |
| `530033503533` | Rainier Prep | Regular School (charter) | Rainier Prep Charter School District | 05-08 | 359 | Seattle |
| `530034203602` | Rainier Valley Leadership Academy | Regular School (charter) | Rainier Valley Leadership Academy | 06-12 | 121 | Seattle |
| `531017103924` | Rooted School Washington | Regular School (charter) | Rooted School Washington | 09-12 | 58 | Vancouver |
| `530033703539` | Spokane International Academy | Regular School (charter) | Spokane International Academy | KG-12 | 824 | Spokane |
| `530034303611` | Summit Public School: Atlas | Regular School (charter) | Summit Public School: Atlas | 06-12 | 566 | Seattle |
| `530033303541` | Summit Public School: Olympus | Regular School (charter) | Summit Public School: Olympus | 09-12 | 110 | Tacoma |
| `530033403510` | Summit Public School: Sierra | Regular School (charter) | Summit Public School: Sierra | 09-12 | 214 | Seattle |

### Statewide specialty schools (8 schools)

Statewide-mission schools (Schools for the Deaf/Blind, Youth Academy, tech high schools) draw students from across WA and serve fundamentally different populations. None are currently on `school_exclusions.yaml`, but they would arguably distort any FRL-vs-proficiency regression they're included in.

| _id | School name | Type | District | Grade span | Enrollment | City |
|---|---|---|---|---|---|---|
| `530001403082` | Bates Technical High School | Regular School | Bates Technical College | 09-12 | 343 | Tacoma |
| `530034003593` | ESA 112 Special Ed Co-Op | Special Education School | Educational Service Agency 112 | PK-12 | 0 | Vancouver |
| `530031303265` | Lake Washington Technical Academy | Regular School | Lake Washington Institute of Technology | 11-12 | 138 | Kirkland |
| `530001703209` | Northwest Career and Technical High School | Career and Technical School | Clover Park Technical College | 09-12 | 0 | Lakewood |
| `530032503695` | Renton Technical High School | Regular School | Renton Technical College | 11-12 | 66 | Renton |
| `530031802385` | Washington State School for the Blind | Regular School | Office of the Governor (Sch for Blind) | 06-12 | 50 | Vancouver |
| `530001501016` | Washington State School for the Deaf | Regular School | Washington Center for Deaf and Hard of Hearing Youth | PK-12 | 127 | Vancouver |
| `530032403412` | Washington Youth Academy | Regular School | Washington Military Department | 09-12 | 0 | Bremerton |

### Institutional facilities (5 schools)

Juvenile detention and youth services facilities. Five of these are already on `school_exclusions.yaml`; five are not — likely an oversight from incremental list-building rather than a deliberate distinction.

| _id | School name | Type | District | Grade span | Enrollment | City |
|---|---|---|---|---|---|---|
| `530000503407` | Clark County Juvenile Detention School | Regular School | Educational Service District 112 | 03-12 | 15 | Vancouver |
| `530000502917` | Cowlitz County Youth Services Center | Regular School | Educational Service District 112 | 06-12 | 14 | Longview |
| `530001002919` | Martin Hall Detention Ctr | Regular School | Educational Service District 101 | 08-12 | 8 | Medical Lake |
| `530001002930` | Spokane Juvenile Detention School | Regular School | Educational Service District 101 | 06-12 | 19 | Spokane |
| `530001002929` | Structural Alt Confinement School | Alternative School | Educational Service District 101 | 08-12 | 14 | Spokane |

### Regional alternative / reengagement programs (11 schools)

ESD-run reengagement and alternative programs (Open Doors, dropout prevention, YouthSource, technical-college-affiliated programs). One school (Garrett Heyns) is on `school_exclusions.yaml`; the other ten are not, despite serving similar populations under similar models.

| _id | School name | Type | District | Grade span | Enrollment | City |
|---|---|---|---|---|---|---|
| `530001403585` | Bates Technical College - Open Doors | Alternative School | Bates Technical College | 09-12 | 0 | Tacoma |
| `530000603748` | Dropout Prevention and Reengagement Academy | Alternative School | Puget Sound Educational Service District 121 | 09-12 | 0 | Renton |
| `530001303670` | ESD 105 Open Doors | Alternative School | Educational Service District 105 | 09-12 | 120 | Yakima |
| `530000503538` | ESD 112 Open Doors Reengagement | Alternative School | Educational Service District 112 | 09-12 | 46 | Vancouver |
| `530001103422` | ESD 113 Consortium Reengagement Program | Alternative School | Capital Region ESD 113 | 11-12 | 344 | Tumwater |
| `530001003583` | NEWESD 101 Open Doors | Alternative School | Educational Service District 101 | 11-12 | 127 | Spokane |
| `530000803609` | Open Doors - Youth Reengagement Program | Alternative School | Northwest Educational Service District 189 | 09-12 | 63 | Anacortes |
| `530031303403` | Open Doors at LWIT | Alternative School | Lake Washington Institute of Technology | 11-12 | 5 | Kirkland |
| `530000802755` | Pass Program | Alternative School | Northwest Educational Service District 189 | 06-12 | 0 | Everett |
| `530001203521` | Ugrad ESD123 Re-Engagement Program | Alternative School | Educational Service District 123 | 09-12 | 353 | Pasco |
| `530032503687` | YouthSource and RTC | Alternative School | Renton Technical College | 11-12 | 296 | RENTON |

### Tribal community schools (1 schools)

Chief Kitsap Academy. Not currently on `school_exclusions.yaml`. ACS district geography cannot capture tribal community context for this single tribal compact school.

| _id | School name | Type | District | Grade span | Enrollment | City |
|---|---|---|---|---|---|---|
| `530032803493` | Chief Kitsap Academy | Regular School | Suquamish Tribal Education Department | KG-12 | 74 | Poulsbo |

## Methodology question for follow-up

**Should `school_exclusions.yaml` be aligned with the new SKIP classification, or are these schools appropriately treated differently?**

Three possible positions, none of which this note is taking:

1. **Align fully** — every school on the SKIP list should also be on `school_exclusions.yaml`, since both lists are answering essentially the same question ("is this school comparable to regular WA schools on standard metrics?"). The 39-school gap is an oversight to be corrected.

2. **Keep them separate by intent** — `school_exclusions.yaml` exists specifically for the FRL regression's edge cases (CCD miscoding of virtual/online schools as 'Regular School'). The SKIP list answers a different question ("can we attach district-level ACS data?"). Different methodologies, different exclusion criteria, no need to merge.

3. **Defer the question** — if the FRL regression is being retired in favour of peer-cohort matching, `school_exclusions.yaml` itself becomes legacy. The new methodology will have its own exclusion logic (likely the SKIP categories above plus more). Don't reconcile two lists where one is on its way out.

Position 3 is the most consistent with the architectural decision made today. Recommendation: revisit when the new peer-cohort methodology is being formalized, and design the new exclusion logic from first principles rather than patching the legacy list.
