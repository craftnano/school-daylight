# Build Log

Chronological record of decisions, findings, and changes with reasoning.

---

## 2026-02-22 — Echo Glen School added to exclusions

**Context:** During pre-Phase 4 FRL data review, Echo Glen School (NCES 530375001773, Issaquah School District) appeared on the list of schools with FRL >= 95% (97.1%). Echo Glen is a DSHS juvenile detention facility. CCD codes it as "Regular School" — the same misclassification pattern discovered for virtual/online schools in Phase 3.

**Finding:** Echo Glen's 97.1% FRL reflects its institutional population, not community poverty. Issaquah School District provides educational services at the facility, but enrollment is involuntary and transient. Comparing it against traditional schools on a FRL-vs-proficiency curve is misleading for the same reasons documented in Phase 3 decision log #2.

**Action:** Added to `school_exclusions.yaml` under a new "Institutional facilities" category. Performance flag was already null (reason: `data_not_available`) — will be reclassified to `school_type_not_comparable` on next pipeline run.

**Impact:** No change to regression pool (Echo Glen was already excluded from regression due to missing proficiency data). The reason code change is more accurate documentation.

---

## 2026-02-22 — 49 non-traditional schools added to exclusions (null-FRL review)

**Context:** Investigated all 152 schools with null FRL percentage. Of the 60 coded as "Regular School" in CCD, most are clearly not traditional schools: jails, group homes, preschools, homeschool partnerships, youth services, alternative programs, and zero-enrollment entries. These schools have null FRL because OSPI doesn't report demographics for them, confirming they operate outside the normal K-12 system.

**Schools added by category:**
- **Jails and detention centers (16):** Benton County Jail, Clallam Co Juvenile Detention, Echo Glen School (already added earlier), Island County Corrections, Island Juvenile Detention, Kitsap Co Detention, Lewis County Jail, Mason County Detention, Okanogan Co Juvenile Detention, Skagit County Detention, Sno Co Jail, Snohomish Detention, Spokane County Jail, Walla Walla County Juvenile Detention, Whatcom Co Detention, Yakima Adult Jail
- **Group homes and treatment (6):** Canyon View, Fircrest Residential, Oakridge, Parke Creek Treatment, Ridgeview, Twin Rivers
- **Preschool / early childhood (10):** Cape Flattery Preschool, ECEAP, Federal Way Headstart, Head Start (Highline), Hoyt Early Learning, Manson Early Learning, Oakville Preschool, Ready Start Preschool, Spokane Regional Health District, West Central Community Center
- **Homeschool partnerships (2):** Northshore Family Partnership, White River Homeschool
- **Community-based / youth services (4):** Southwest Youth and Family Services, The Healing Lodge, Touchstone, Woodinville Community Center
- **Alternative / reengagement miscoded (6):** Alternative Tamarack School, Garrett Heyns (Centralia College), Morgan Center School, Ocosta ALE, Tacoma Pierce County Education Center, Vancouver Contracted Programs
- **Special education / specialized miscoded (3):** Arlington Special Educ School, Kalispel Language Immersion School (tribal — culturally significant but zero enrollment), North Bell Learning Center
- **Zero-enrollment / likely closed (5):** Bear Creek Elementary, Choice, Southern Heights Elementary, Coulee City Middle School, Star Elem School (both verified as zero enrollment, no staffing/academics)

**Not excluded (preserved as real schools):**
- Decatur Elementary (3 students, Lopez Island — tiny but real)
- Holden Village Community School (4 students, remote mining village — tiny but real)
- Point Roberts Primary (5 students, geographic exclave — tiny but real)
- Waldron Island School (5 students, San Juan Islands — tiny but real)
- Nespelem High School (19 students, tribal community — FRL likely suppressed, not absent)

**Impact:** `school_exclusions.yaml` now has 76 entries (25 virtual + 51 institutional/other). All 49 new schools already had null performance flags due to missing data — the change reclassifies their reason codes from `data_not_available` to the more accurate `school_type_not_comparable`. No regression results change.
