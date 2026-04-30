# School Daylight — Harm Register
## Living document tracking potential harms considered and design responses across all phases

This file records every decision made specifically to prevent, mitigate, or address potential harm to students, families, schools, or communities. It is maintained alongside the build process and is intended to inform the published methodology documentation before launch.

---

## Phase 2-3 (ETL + Comparison Engine)

### Suppression integrity
**Concern:** If suppressed data (small cell sizes hidden for student privacy) is stored as zero, the briefing would tell parents "zero incidents" when the truth is "we can't tell you." This directly harms families who rely on the data.
**Response:** Suppressed values stored as null with suppressed: true flag. Zero means zero. Null means unknown. Pipeline enforces this distinction at every step. (CLAUDE.md critical rule)

### Non-traditional school misclassification
**Concern:** Virtual schools, homeschool partnerships, and alternative programs coded as "Regular" in CCD get run through the performance regression and flagged as "underperforming" — a misleading label that could damage a school's reputation when the regression model simply doesn't apply.
**Response:** 468 non-traditional schools excluded from regression. 443 caught by CCD school type filter, 25 identified manually through name keyword search and added to school_exclusions.yaml. Virtual schools get their own exclusion rationale. (Phase 3 decision)

### Per-level regression
**Concern:** A single statewide regression treats elementary, middle, and high schools as one population. Different grade levels have structurally different proficiency-FRL relationships. A school could be misclassified as outperforming or underperforming because the wrong baseline was applied.
**Response:** Empirically validated that per-level regression (elementary/middle/high) produces more accurate flags. Fairhaven moved from yellow (z=0.89) to green (z=1.33) with per-level model. Documented as deviation from original build sequence. (Phase 3 decision)

### Flag absent reason codes
**Concern:** A missing flag with no explanation could be interpreted as "nothing to see here" when the real reason is data suppression, grade span mismatch, or school type exclusion. Parents deserve to know why a flag is absent, not just that it's absent.
**Response:** Every missing flag carries a flag_absent_reason code: grade_span_not_tested, suppressed_n_lt_10, school_type_not_comparable, data_not_available. High confidence reasons only, no speculation. (Phase 3 decision)

### Discipline disparity baseline disclosure
**Concern:** Using white students as the baseline for discipline disparity ratios is a methodology choice, not a self-evident truth. Without disclosure, the tool could be perceived as making a political rather than statistical choice.
**Response:** Flagged for methodology documentation before launch. The briefing must disclose and explain the baseline choice. (Phase 3 exit, open item)

### Embedded parent partnership programs
**Concern:** Some traditional schools host homeschool or alternative learning experience programs not separately identifiable in the data. Their enrollment, demographics, and outcomes data may be blended with the host school's data, distorting the picture.
**Response:** Known limitation (Blaine School District identified). Flagged for methodology disclosure. Haiku web search in Phase 4 may surface additional examples. (Phase 3 exit, open item)

### CEP-inflated FRL percentages
**Concern:** Community Eligibility Provision allows high-poverty schools to offer free meals to all students without individual applications. CEP schools may report FRL at or near 100% regardless of actual household income levels. Since FRL is the primary input to the performance regression, inflated FRL could systematically misclassify schools — making them appear to "outperform demographics" when they're actually performing normally for their real poverty level.
**Finding:** Investigated during Phase 4 advisory session. FRL source is OSPI 2023-24 (post-COVID waiver expiration). Distribution shows no unnatural spike at 100% — only 15 schools above 95%, all in genuinely high-poverty communities. CEP cannot be distinguished in the OSPI data but does not appear to cause widespread distortion in Washington.
**Response:** Disclose as methodology limitation before launch. No pipeline changes needed. Monitor if expanding to states with higher CEP adoption. (Phase 4 advisory session, resolved)

### Echo Glen School misclassified as regular school
**Concern:** Echo Glen School (Issaquah School District) is a juvenile detention facility that appears in the data as a regular school with 97.1% FRL and 104 enrollment. Running it through the performance regression produces misleading results — a detention facility's academic outcomes cannot be meaningfully compared to traditional schools. Surfaced during FRL data review.
**Response:** Added to school_exclusions.yaml as category: institutional. Excluded from performance regression. Manual exclusions now at 26. Identified through builder's direct local knowledge and confirmed by data review. (Phase 4 advisory session)

### Chronic absenteeism thresholds miscalibrated for post-COVID era
**Concern:** The 20%/30% flag thresholds for chronic absenteeism were derived from pre-COVID research. Post-pandemic, the entire distribution has shifted upward. 64% of Washington schools now trip yellow or red. When two-thirds of schools are flagged, a parent seeing a red flag thinks "this school has a problem" when the reality is "this is a statewide crisis." The flag creates a false impression of school-specific failure when the issue is systemic.
**Response:** Two changes before Phase 5: raise thresholds (candidate 30%/45%) to identify schools that stand out even within the elevated baseline, and add mandatory narrative context disclosing the statewide post-pandemic shift. Both changes require Phase 3 comparison engine rerun. Does not affect Phase 4. (Phase 4 advisory session, to be implemented pre-Phase 5)

### Discipline disparity ratios unreliable at small subgroup sizes
**Concern:** Schools with fewer than 30 students in a minority subgroup produce statistically meaningless extreme disparity ratios. A single suspension on 10 students creates a 10% rate that generates ratios of 30x+ against typical white baselines. 29 of 65 schools with 10x+ ratios have fewer than 20 students in the triggering subgroup. Presenting these ratios to parents as meaningful disparity findings could unfairly damage a school's reputation based on arithmetic artifacts rather than systemic patterns.
**Response:** Raise minimum-N threshold from 10 to 30. Schools with subgroups of 10-29 get ratio suppressed with new reason code suppressed_subgroup_lt_30. Suppressed schools still get a narrative note explaining that data exists but the subgroup is too small for reliable calculation — silence would imply the data doesn't exist. Validated that schools with 30+ students and extreme ratios (Garfield HS at 449 Black students/10.2x, Washington Middle at 191/10.6x) represent real signal worth surfacing. Requires Phase 3 rerun. Does not affect Phase 4. (Phase 4 advisory session, to be implemented pre-Phase 5)

---

## Phase 4 (Haiku Context Enrichment)

### School name disambiguation / wrong-school contamination
**Concern:** Common school names (Lincoln Elementary, Washington Middle School) exist in multiple districts and states. Haiku could attribute findings from the wrong school — an investigation at Lincoln Elementary in Tacoma attributed to Lincoln Elementary in Spokane. This is reputational harm based on hallucinated or misattributed information.
**Response:** Enrichment prompt passes school name + district + city + state. Haiku instructed to reject results that don't match on at least district AND city. Validation pass (second Haiku call, different prompt) specifically checks for wrong-school contamination. (Phase 4 design decision)

### Sensitivity flagging for high-impact findings
**Concern:** Findings involving active investigations, lawsuits, criminal charges, or abuse allegations could flow automatically into Phase 5 narrative generation and appear in parent-facing briefings without human review. Even if factually accurate, the framing matters enormously and should not be delegated entirely to an LLM.
**Response:** Findings in these categories get sensitivity: "high" flag. They are excluded from Phase 5 auto-generation until the builder manually reviews and approves them. (Phase 4 design decision)

### LLM hallucination in web-sourced findings
**Concern:** Haiku could fabricate incidents, investigations, or awards that never happened — or accurately find real information but misattribute it to the wrong school. Either outcome harms the school's reputation.
**Response:** Two-pass architecture (enrichment + validation). Source URLs and content summaries stored with every finding. Pilot batch of 25 schools with manual human verification before full batch runs. Predefined output categories constrain what Haiku can report. Confidence scores on every finding. (Phase 4 design decision)

### Cost runaway risk
**Concern:** An infinite loop or misconfigured script could run up API charges far beyond budget, creating financial harm to the builder.
**Response:** Tier 1 hard spend cap ($70/month). No credit card on file (cannot exceed balance). Email notification at $20. Haiku only (cheapest model). No extended thinking. Capped web searches per call (2 enrichment, 1 validation). Capped retries (3 with exponential backoff). Pilot batch before full run. (Phase 4 design decision)

### Student deaths excluded from enrichment findings
**Concern:** Web searches for schools may surface news stories about student deaths — suicides, accidents, violence, medical emergencies. Including these in school briefings retraumatizes families and communities, serves no civic transparency purpose, and could be discovered by the family of the child. A parent researching a school does not benefit from learning that a student died there. This applies regardless of how the death occurred or whether the school bears any institutional responsibility.
**Response:** Explicit exclusion added to both enrichment and validation prompts. Haiku instructed to never return findings about student deaths of any kind. Validation prompt instructed to reject any that slip through. If institutional negligence contributed to a death and resulted in a formal institutional response — an investigation, OCR complaint, lawsuit, settlement, or policy change — that institutional response may be surfaced under investigations_ocr. But the death itself is never named, no identifying details about the student are included, and the finding is framed around what the institution did or failed to do, never around what happened to a child. In cases where news coverage links a death to school conditions (e.g., bullying) but no formal institutional response exists, the finding is excluded entirely. A school briefing is not the right vehicle to hold an institution accountable for a child's death when no formal mechanism has done so. (Phase 4, triggered by builder encountering a child suicide news story in this phase, not part of pilot review)

### Individual names stripped from findings
**Concern:** Findings that name specific individuals — suspects, convicted offenders, volunteers, candidates, or other private citizens — create defamation liability risk for the platform even when the underlying reporting is accurate. Reprinting a name in a school briefing recontextualizes it from journalism (protected) to a civic data product (less clearly protected). The name adds no value to the parent's decision-making: "a teaching assistant was arrested for sexual misconduct" serves the same civic transparency purpose as naming the person. Additionally, naming individuals who were accused but not convicted, or whose cases were resolved through deferred prosecution, compounds the liability.
**Response:** Phase 5 Sonnet prompt must strip all individual names from context findings and replace with role descriptions (e.g., "a former wrestling coach," "a substitute teacher," "the superintendent," "a school board member"). No exceptions — this includes superintendents, principals, and other public officials. Institutional names (school districts, agencies, courts) are retained. If the person's role is relevant, describe the role. If their tenure matters, say "former." The name itself never appears. (Phase 4 review, triggered by liability analysis of sensitivity findings)


### Student names never appear in briefings
**Concern:** Any student named in a finding — whether as victim, perpetrator, complainant, or witness — is or was a minor. Reprinting their name in a school briefing creates a permanent, searchable association between a child and an incident they may have no control over. Victims are retraumatized. Juvenile offenders lose rehabilitation prospects. Even positive mentions (award winners, athletes) create indexable profiles of minors without parental consent. This is a categorical prohibition, not a judgment call.
**Response:** Sonnet must never include student names in any briefing content. Students are referenced only by role ("a student," "a freshman," "the victim," "several students"). This applies to all findings regardless of category, sensitivity level, or whether the student is now an adult. The sole future exception: a potential "notable alumni" feature referencing public figures whose association with a school is already widely known and who are adults — but this feature does not exist yet and would require its own review before implementation. (Phase 4 review, triggered by sensitivity findings containing student identifiers)
---

## Phase 5 (Planned — Not Yet Implemented)

### Three-layer trust model
**Concern:** If web-sourced findings (Phase 4) are blended into data-driven narrative without distinction, parents cannot tell the difference between "the federal data shows X" and "an LLM found Y on the internet." This undermines trust in the verified data and could expose parents to LLM-sourced errors without their knowledge.
**Response:** Briefing structured into three distinct layers with different trust profiles: (1) verified data presented visually, (2) narrative interpretation of verified data only, (3) web-sourced findings clearly labeled with LLM/web disclaimer. Implementation may involve two separate Sonnet calls with different system prompts to make cross-contamination structurally impossible. (Phase 4 advisory session decision, to be implemented in Phase 5)

### Non-traditional school narrative framing
**Concern:** Applying standard narrative framing to juvenile detention facilities, homeschool cooperatives, virtual schools, or alternative programs is misleading. Telling a parent that a juvenile detention facility "underperforms peers" or that a homeschool partnership has "low enrollment compared to district average" misrepresents reality and could cause reputational harm.
**Response:** Phase 5 Sonnet prompt branches on school type and applies different narrative instructions per category: traditional (full treatment), virtual (virtual model framing), homeschool/partnership (comparisons only to similar programs), juvenile detention/institutional (minimal comparison, heavy caveats), alternative (context-dependent). School type already on each document. (Phase 4 advisory session decision, to be implemented in Phase 5)

### Extreme outlier without explanation
**Concern:** When a metric like per-pupil expenditure is many standard deviations from the norm (e.g., Skykomish at $110k), presenting the number without comment leaves parents confused. But fabricating an explanation is worse. And flagging every extreme value across all metrics would produce noise.
**Response:** Two distinct narrative modes for outliers. Mode 1 ("explain this anomaly"): structurally alarming metrics like per-pupil spending, chronic absenteeism, discipline rate — narrative offers explanation from Phase 4 context or acknowledges no explanation found. Mode 2 ("notice this signal"): surprising values a parent would never discover, like unusually high AP enrollment at a high-poverty school or zero AP at an otherwise excellent school — narrative frames as strength, question, or distinctive feature without alarm. Both use same statistical detection (3+ SD from peers), different framing. Candidate taxonomies defined for both modes, to be refined through Phase 5 pilot iteration. (Phase 4 advisory session decision, to be implemented in Phase 5)

---

*Add new entries as they arise. Each entry: date/phase, the concern, the design response. Tag with phase for searchability. This document informs the published methodology page before launch.*

---

## Pre-Launch (Licensing and Governance)

### Derivative works that recontextualize data as rankings or recommendations
**Concern:** An open-source repo could be forked and used to build a "find the right school for my kid" recommendation engine that uses School Daylight's data pipeline but strips the contextual caveats and reduces schools to scores or match percentages. This reintroduces the exact harm the project exists to counter — and does it with a veneer of credibility borrowed from the underlying data quality. The harm is recontextualization, not commerce: a free tool that ranks schools is just as harmful as a paid one.
**Response:** Foundation doc originally specified MIT license for code, CC BY 4.0 for docs. This needs to be revisited before launch. The license must prevent derivative works that reduce school data to scores, rankings, or recommendations directed at individual families. Options to research: CC BY-NC-SA 4.0 (blocks commercial use but not the free scenario), custom license with specific use restriction, AGPL with ethical use clause. Separate research task, possibly informed by law school coursework. Decision required before repo goes public. (Phase 4 advisory session, to be resolved pre-launch)


