# Phase 3R — District ID Audit (experiment database)

Read-only audit of `district.nces_id` on every school in `schooldaylight_experiment.schools`. Identifies which schools roll up to a non-USD geography that the ACS school-district API does not publish for, before any Census ingestion runs.

Authoritative WA district lists pulled live from the Census ACS API (2023 ACS 5-year, state FIPS 53). 'USD-matched' means the code literally appears in the ACS unified-district geography listing.

**Sources:**

- Unified districts: `https://api.census.gov/data/2023/acs/acs5?get=NAME&for=school+district+(unified):*&in=state:53`
- Elementary districts: same endpoint with `(elementary)` (returned empty for WA)
- Secondary districts: same endpoint with `(secondary)` (returned empty for WA)

## Headline counts

- Distinct `district.nces_id` values in experiment db: **330**
- WA Unified School Districts published by ACS: **295**
- WA Elementary districts published by ACS: **0**
- WA Secondary districts published by ACS: **0**

| Classification | distinct district codes | schools |
|---|---|---|
| USD (matches ACS unified district) | 295 | **2484** |
| Elementary district | 0 | 0 |
| Secondary district | 0 | 0 |
| Educational Service District (ESD — not ACS-published) | 8 | 18 |
| Other non-USD code (no ACS match, name doesn't read as ESD) | 27 | 30 |
| Missing `district.nces_id` entirely | — | 0 |
| **Total schools** | — | **2532** |

> 2484 schools (98.1%) will get Census data via the ACS unified-district endpoint without any methodology decision needed.

> The remaining 48 schools (1.9%) need a builder decision before ingestion proceeds.

## Schools rolled up to Educational Service District (ESD) codes

ESDs are regional service agencies, not operating school districts. ACS does NOT publish district-geography data for ESDs. The schools below are typically state-operated (juvenile detention, psychiatric hospitals) or specialized regional programs.

### `5300008` — Northwest Educational Service District 189 (5 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530000803609` | Open Doors - Youth Reengagement Program | Alternative School | 09-12 | 63 | 1601 R Avenue, Anacortes |
| `530000802755` | Pass Program | Alternative School | 06-12 | 0 | 2731 10th St. Suite 106, Everett |
| `530000802921` | Skagit County Detention Center | Regular School | 08-12 | 4 | 605 3RD ST, MOUNT VERNON |
| `530000802095` | Snohomish Detention Center | Regular School | 06-12 | 8 | 2801 10th Street, Everett |
| `530000802923` | Whatcom Co Detention Center | Regular School | 08-12 | 4 | 311 GRAND AVE 6TH FL, BELLINGHAM |

### `5300010` — Educational Service District 101 (4 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001002919` | Martin Hall Detention Ctr | Regular School | 08-12 | 8 | 201 S. Pine St., Medical Lake |
| `530001003583` | NEWESD 101 Open Doors | Alternative School | 11-12 | 127 | 901 E. 2nd Avenue Suite 100, Spokane |
| `530001002930` | Spokane Juvenile Detention School | Regular School | 06-12 | 19 | 1208 Mallen St., Spokane |
| `530001002929` | Structural Alt Confinement School | Alternative School | 08-12 | 14 | 1208 W. Mallen St., Spokane |

### `5300005` — Educational Service District 112 (3 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530000503407` | Clark County Juvenile Detention School | Regular School | 03-12 | 15 | 500 West 11th St, Vancouver |
| `530000502917` | Cowlitz County Youth Services Center | Regular School | 06-12 | 14 | 1725 1st Ave., Longview |
| `530000503538` | ESD 112 Open Doors Reengagement | Alternative School | 09-12 | 46 | 2500 NE 65th Avenue, Vancouver |

### `5300007` — Olympic Educational Service District 114 (2 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530000702914` | Clallam Co Juvenile Detention | Regular School | 07-12 | 0 | 1912 W 18TH ST, PORT ANGELES |
| `530000702927` | Kitsap Co Detention Ctr | Regular School | 08-12 | 2 | 1338 SW OLD CLIFTON RD, PORT ORCHARD |

### `5300006` — Puget Sound Educational Service District 121 (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530000603748` | Dropout Prevention and Reengagement Academy | Alternative School | 09-12 | 0 | 800 Oakesdale Ave SW, Renton |

### `5300011` — Capital Region ESD 113 (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001103422` | ESD 113 Consortium Reengagement Program | Alternative School | 11-12 | 344 | 6005 Tyee Dr. SW, Tumwater |

### `5300012` — Educational Service District 123 (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001203521` | Ugrad ESD123 Re-Engagement Program | Alternative School | 09-12 | 353 | 3918 West Court Street, Pasco |

### `5300013` — Educational Service District 105 (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001303670` | ESD 105 Open Doors | Alternative School | 09-12 | 120 | 33 S 2nd Ave, Yakima |

## Schools rolled up to other non-USD codes

These codes don't match any ACS school-district geography (unified, elementary, or secondary) and the district name does not contain 'Educational Service District' or 'ESD'. Likely tribal compact schools, charter authorizers, or state-operated facilities.

### `5300014` — Bates Technical College (2 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001403585` | Bates Technical College - Open Doors | Alternative School | 09-12 | 0 | 1101 South Yakima Ave., Tacoma |
| `530001403082` | Bates Technical High School | Regular School | 09-12 | 343 | 1101 South Yakima Avenue, Tacoma |

### `5300313` — Lake Washington Institute of Technology (2 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530031303265` | Lake Washington Technical Academy | Regular School | 11-12 | 138 | 11605 132nd Ave NE, Kirkland |
| `530031303403` | Open Doors at LWIT | Alternative School | 11-12 | 5 | 11605 132nd Ave NE, Kirkland |

### `5300325` — Renton Technical College (2 schools)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530032503695` | Renton Technical High School | Regular School | 11-12 | 66 | 3000 4th St NE, Renton |
| `530032503687` | YouthSource and RTC | Alternative School | 11-12 | 296 | 3000 NE 4TH ST, RENTON |

### `5300015` — Washington Center for Deaf and Hard of Hearing Youth (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001501016` | Washington State School for the Deaf | Regular School | PK-12 | 127 | 611 Grand Blvd, Vancouver |

### `5300016` — Centralia College (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001603208` | Garrett Heyns High School | Regular School | 08-12 | 0 | 2321 W Dayton Airport Rd, Shelton |

### `5300017` — Clover Park Technical College (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530001703209` | Northwest Career and Technical High School | Career and Technical School | 09-12 | 0 | 4500 Steilacoom Blvd SW, Lakewood |

### `5300318` — Office of the Governor (Sch for Blind) (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530031802385` | Washington State School for the Blind | Regular School | 06-12 | 50 | 2214 E. 13th St., Vancouver |

### `5300324` — Washington Military Department (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530032403412` | Washington Youth Academy | Regular School | 09-12 | 0 | 1207 Carver St, Bremerton |

### `5300328` — Suquamish Tribal Education Department (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530032803493` | Chief Kitsap Academy | Regular School | KG-12 | 74 | 15838 Sandy Hook Rd, Poulsbo |

### `5300333` — Summit Public School: Olympus (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530033303541` | Summit Public School: Olympus | Regular School (charter) | 09-12 | 110 | 409 Puyallup Ave, Tacoma |

### `5300334` — Summit Public School: Sierra (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530033403510` | Summit Public School: Sierra | Regular School (charter) | 09-12 | 214 | 1025 S King St, Seattle |

### `5300335` — Rainier Prep Charter School District (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530033503533` | Rainier Prep | Regular School (charter) | 05-08 | 359 | 10211 12th Ave S, Seattle |

### `5300337` — Spokane International Academy (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530033703539` | Spokane International Academy | Regular School (charter) | KG-12 | 824 | 777 E Magnesium Rd, Spokane |

### `5300339` — PRIDE Prep Charter School District (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530033903495` | Innovation High School | Regular School (charter) | 09-12 | 232 | 811 E. Sprague, Spokane |

### `5300340` — Educational Service Agency 112 (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034003593` | ESA 112 Special Ed Co-Op | Special Education School | PK-12 | 0 | 2500 NE 65th Avenue, Vancouver |

### `5300342` — Rainier Valley Leadership Academy (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034203602` | Rainier Valley Leadership Academy | Regular School (charter) | 06-12 | 121 | 6020 Rainier Avenue S, Seattle |

### `5300343` — Summit Public School: Atlas (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034303611` | Summit Public School: Atlas | Regular School (charter) | 06-12 | 566 | 9601 35th Avenue SW, Seattle |

### `5300345` — Impact | Puget Sound Elementary (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034503653` | Impact Public Schools | Regular School (charter) | KG-05 | 505 | 3438 S. 148th Street, Tukwila |

### `5300347` — Catalyst Public Schools (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034703723` | Catalyst Public Schools | Regular School (charter) | KG-09 | 504 | 1305 Ironsides Ave, Bremerton |

### `5300348` — Impact | Salish Sea Elementary (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034803749` | Impact | Salish Sea Elementary | Regular School (charter) | KG-05 | 385 | 3900 Holly Park Dr South, Seattle |

### `5300349` — Why Not You Academy (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530034903783` | Cascade Public Schools | Regular School (charter) | 09-12 | 126 | 22419 Pacific Highway South, Des Moines |

### `5300350` — Lumen Public School (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530035003770` | Lumen High School | Regular School (charter) | 09-12 | 32 | 718 W. Riverside Avenue, Spokane |

### `5300351` — Intergenerational High School (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530035103831` | Intergenerational High School | Regular School (charter) | 09-12 | 107 | 1 Bellis Fair Parkway, Bellingham |

### `5300352` — Pinnacles Prep Charter School (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530035203807` | Pinnacles Prep Charter School | Regular School (charter) | 06-10 | 234 | 504 S. Chelan Ave., Wenatchee |

### `5300354` — Impact | Commencement Bay Elementary (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `530035403782` | Impact Public Schools | Regular School (charter) | PK-05 | 232 | 1301 E 34th Street, Tacoma |

### `5310171` — Rooted School Washington (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `531017103924` | Rooted School Washington | Regular School (charter) | 09-12 | 58 | 10401 NE Fourth Plain Blvd, Vancouver |

### `5310172` — Impact | Black River Elementary (1 school)

| _id (NCESSCH) | School name | Type | Grade span | Enrollment | Location |
|---|---|---|---|---|---|
| `531017203905` | Impact | Black River Elementary | Regular School (charter) | KG-05 | 209 | 16950 116th Ave SE, Renton |

## Summary of decision needed

- **2484 schools** roll up to USD codes that match ACS — these will be ingested cleanly.
- **18 schools** roll up to ESDs — ACS has no district geography for ESDs. Options: (a) skip and document as unmatched; (b) substitute county-level ACS data; (c) substitute the geographic place the school physically sits in.
- **30 schools** under other non-USD codes — review list above and decide.
