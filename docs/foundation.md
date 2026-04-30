# School Daylight
### Foundation Document v0.4
### April 2026
### Orianda Guilfoyle

---

## Mission

School Daylight exists to give parents and community members what they've never had: a clear, honest, and comprehensive picture of their public schools, built from data that already belongs to them.

Today's school rating systems reward wealth. A GreatSchools 9 or a Niche A tells you more about a neighborhood's income than its classrooms. Research consistently shows that these scores correlate with parent affluence, not teaching quality, and that families chasing high ratings drive residential segregation, concentrating advantage in communities that already have it while overlooking schools where educators are doing extraordinary work with fewer resources. (See Hasan & Kumar, 2019; Reardon, Stanford Educational Opportunity Project; Schneider, UMass Beyond Test Scores Project.)

School Daylight rejects the premise that a school can be reduced to a number. Instead, it provides context. Where a school is genuinely outperforming what its demographics would predict, the briefing surfaces that, because those educators deserve recognition that the current system denies them. Where data reveals patterns that warrant attention (discipline disparities, staffing gaps, chronic absenteeism, or access inequities), the briefing surfaces those too, with specific questions parents can bring to their schools and school boards.

School Daylight also does something no existing rating system attempts: it uses AI to systematically ingest and analyze public news, court records, and investigative reporting about schools and districts, surfacing lawsuits, settlements, investigations, and institutional accountability patterns that no parent could reasonably discover on their own. A GreatSchools 9 tells you nothing about a district that paid $1.3 million to settle a wrongful-death lawsuit, or a school where administrators discouraged police involvement in a sexual assault, or a pattern of Title IX failures spanning a decade. This information is public, scattered across local news archives, court filings, and government enforcement actions. Before AI, assembling it at scale across thousands of schools was a newsroom-level effort that no one sustained (ProPublica tried once and stopped updating). School Daylight automates this assembly, but automation introduces its own risks: AI can hallucinate facts, fabricate outcomes, and associate the wrong finding with the wrong school. The project addresses these risks through a three-stage pipeline architecture that separates editorial judgment from narrative writing, with zero hallucinations validated across 50 test schools (see AI Ethics by Design, below).

The tool uses AI responsibly. Not to generate data, but to interpret it, contextualizing numbers against the real-world circumstances that shape them. A spike in absenteeism during a hurricane year isn't a failing school. A low suspension rate at a school operating under competing federal disability mandates isn't necessarily a safe school. The briefing accounts for these realities because a number without context is worse than no number at all.

Everything about this tool is transparent. The data comes from public federal and state sources. The code is open source. The methodology is published. Every limitation is disclosed. Every threshold is documented and challengeable. When the tool is wrong, it gets corrected publicly. The goal is not to be definitive; it's to be useful, honest, and continuously improving.

A civic tool that surfaces sensitive information about schools (lawsuits, investigations, discipline disparities, student deaths) can cause real harm if built carelessly. School Daylight maintains a living harm register (`docs/harm_register.md`) that documents every potential harm identified during development and the specific architectural decision made in response. The harm register is not documentation after the fact. It drives design: when the sensitivity review surfaced findings about student suicides, the harm register entry produced the three-stage narrative pipeline and the death-suppression rules that now govern what AI can and cannot say about a school. When discipline disparity ratios proved unreliable at small subgroup sizes, the harm register entry produced the minimum-N threshold. This is deliberate. In a project where AI interprets sensitive public data about children, the ethics are not a layer applied on top of the architecture. They are the architecture.

Five principles guide every design decision:

1. **Inform, don't rank.** Rich data and context for parents and community members, not scores that flatten complexity.
2. **Expose what ratings hide.** Acknowledge and counteract the ways existing systems reward income, obscure inequity, and inadvertently drive segregation.
3. **Recognize real achievement and surface real concerns.** Showcase gains that current ratings miss, especially where educators outperform demographic expectations, while flagging areas parents should raise with their schools.
4. **Use AI to contextualize, not to judge.** Apply AI responsibly to interpret data within real-world constraints: legal mandates, natural disasters, policy changes. Schools operate in contexts that numbers alone cannot capture.
5. **Default to transparency.** Open source code, published methodology, disclosed limitations, public corrections, and a commitment to getting better over time.

---

## Problem Statement

Millions of American parents make school decisions using rating systems that collapse complex realities into a single number: GreatSchools (9/10), Niche (A−), U.S. News (#103). These scores are embedded in Zillow, Redfin, and Realtor.com. They drive home purchases, neighborhood selection, and school choice.

These ratings are misleading in two ways:

**They measure demographics, not quality.** A 2019 study by Hasan and Kumar at Duke and the University of Florida ("Digitization and Divergence: Online School Ratings and Segregation in America") found that the staged rollout of GreatSchools ratings from 2006 to 2015 accelerated divergence in housing values, income distributions, and racial composition across communities. Affluent families leveraged the ratings to sort into neighborhoods with higher-scoring schools, concentrating advantage further. As the researchers put it: "Knowledge was indeed power, but only for the powerful." Stanford's Sean Reardon and the Educational Opportunity Project have separately documented that standardized test scores, the primary input to these ratings, measure family and neighborhood resources far more than school quality. Education professor Jack Schneider at UMass Amherst (director of the Beyond Test Scores Project) has been equally direct: school rating systems "are ostensibly telling us about the quality of schools when they are really telling us about the privilege of neighborhoods." The result is a feedback loop: ratings drive residential choices, residential choices deepen segregation, and segregation widens the achievement gaps that ratings claim to measure.

**They hide what actually matters.** A GreatSchools 9 tells a parent nothing about whether Black students are suspended at five times the rate of white students, whether the district failed to report a sexual assault, whether the school has a counselor or only a police officer, whether 30% of students are chronically absent, or whether teachers are leaving faster than they're hired.

All of this data is public. The federal Civil Rights Data Collection (CRDC) publishes school-level discipline, restraint and seclusion, staffing, course access, and special education data for virtually every public school in the country. State agencies publish test scores, growth data, chronic absenteeism, and financials.

No parent-facing tool makes this data accessible, interpretable, or actionable.

The data exists. The interpretation layer does not.

---

## Why Can't a Parent Just Ask Claude?

This is the right question. If the data is public and AI can interpret it, why build a product? Why not tell parents to paste their school name into ChatGPT or Claude and ask?

I tested this. The answer is: **LLMs cannot do this on the fly.**

School data has a fundamental problem that no amount of AI intelligence can solve at inference time:

**The critical data isn't in any LLM's training set in queryable form.** The CRDC public-use file is a massive CSV archive: 98,000+ schools, hundreds of columns, disaggregated by race, sex, disability, and English learner status. It's not indexed by Google. It's not in a format any LLM can retrieve at inference time. Ask Claude right now for Fairhaven Middle School's discipline disparity ratio by race. It can't give you one. Not because it's not smart enough, but because the data isn't available to it.

**State data lives behind JavaScript dashboards.** Washington's OSPI Report Card publishes school-level chronic absenteeism, discipline rates, and student growth scores — but embedded in interactive visualizations that can't be scraped by an LLM or read from a URL. The underlying CSVs exist on a separate data portal. A parent would need to know the portal exists, find it, download the right file, identify their school's ID, and interpret the columns.

**Context requires structured comparison.** A school's 4.2% discipline rate means nothing without knowing the district average (3.1%), the state average (3.8%), and the average among demographic peers (2.9%). That comparison requires pre-calculated percentiles stored in a database — not a single-shot LLM inference.

**News and reputation signals require search and validation.** My prototype briefing for Fairhaven Middle School surfaced that three Bellingham district administrators were criminally charged for failing to report sexual assault, that the district's Title IX policies were out of compliance for seven years, and that the district admitted liability in an assault case two weeks ago. An LLM with web search might find some of this. It might also hallucinate incidents that never happened. The product validates, caches, and updates this layer systematically rather than generating it fresh — and unreliably — each time.

**The bottom line:** A parent asking an LLM about their school will get a cheerful summary of whatever GreatSchools and Niche say, possibly with hallucinated statistics. They will not get CRDC discipline data, peer-normed comparisons, contextual flags, or the questions they didn't know to ask. The product exists because the data pipeline has to exist first. The AI interprets structured data; it cannot conjure it.

---

## Goals

**Primary:** Give any parent in the United States the ability to look up their child's public school and receive a briefing that tells them what the data says, what it doesn't say, what stands out, and what questions to ask. For free.

**Secondary:**

1. Surface CRDC data (discipline disparities, restraint/seclusion, staffing, course access, special education inclusion) in a format no parent-facing tool currently provides.
2. Present test scores in context — against district, state, and demographic peers — with growth data alongside proficiency, so parents understand the difference.
3. Flag anomalies and concerns using research-informed thresholds, with caveat language that explains what each flag might mean and might not mean.
4. Identify what's missing — which data points are unavailable, outdated, or suppressed — so parents know where the picture is incomplete.
5. Generate concrete next steps: what to ask, who to ask, when the next school board meeting is, and how to request records.
6. Build a compounding data asset through moderated parent field reports that fill gaps between federal data collection cycles.

**Non-goals:**

- Producing a score or ranking.
- Competing with Zillow, Redfin, or real estate platforms.
- Replacing GreatSchools or Niche (they have enterprise sales teams and a decade head start on SEO).
- Building a social platform, review site, or parent community forum.
- Monetizing parent usage in any way.

---

## What It Is / What It Isn't

**It is** an interpretation layer for public education data. A briefing that treats parents as adults who can handle complexity.

**It is open source.** The code, the data pipeline, the cleaning rules, the prompts, the methodology: all public on GitHub. Public data interpreted by public code. A parent, journalist, or researcher can trace any number in any briefing back to a source row in a federal dataset through a documented, auditable pipeline. This isn't a transparency gesture; it's a design requirement. A civic tool funded by no one and accountable to everyone has no business hiding how it works.

**It is not** a rating system. No scores, no letter grades, no rankings. Collapsing complexity into a single number is the problem this exists to solve.

**The analogy:** Preparing a client for a compliance audit. Here's what the data says. Here's what's normal. Here's what stands out. Here's what I don't know. Here's what to ask next.

---

## High-Level Architecture

### Data Layer (Batch, Not Real-Time)

The foundation is pre-ingested federal and state data, refreshed on the publication cycle of each source. Nothing is queried live at the moment a parent looks up a school — it's already in the database.

| Source | What It Provides | Format | Refresh |
|--------|-----------------|--------|---------|
| **CRDC** (Civil Rights Data Collection) | Discipline by race/disability, restraint/seclusion, counselor/SRO counts, teacher cert and experience, AP/IB access and enrollment gaps, SPED inclusion rates | CSV flat files, school-level | Every 2 years (2021-22 current; 2023-24 expected late 2025) |
| **NCES Common Core Data** | Enrollment, demographics, FTE teachers, locale, grade span, free/reduced lunch eligibility | CSV, school and district level | Annual |
| **EdFacts / State Report Cards** | Test proficiency, student growth, chronic absenteeism, discipline rates | CSV downloads from state data portals (OSPI for WA) | Annual |
| **State Financial Data** | Per-pupil expenditure, revenue sources, staffing budgets | CSV (OSPI SAFS files for WA) | Annual |
| **DonorsChoose** | Teacher-initiated funding requests by school, revealing resource gaps and teacher engagement | Public API, school-level | Real-time |
| **US DOE Recognition Programs** | Blue Ribbon, Green Ribbon, NBCT counts | Published lists, searchable | Annual |
| **Local Election Data** | School levy/bond passage rates, a community investment signal | County auditor records, state databases | Per election cycle |

All data is stored in **MongoDB Atlas** with pre-calculated percentiles (school vs. district, state, national, and demographic peers) so that comparisons are instant at lookup time.

**State-specific supplementary streams:** Where CRDC data is stale or unreliable (notably restraint/seclusion, where GAO found significant quality issues), state-level datasets may be more current and granular. California's DOE publishes downloadable restraint/seclusion files disaggregated by subgroup, collected annually via CALPADS at the student level — differing from CRDC's biennial self-reported survey. Washington's OSPI maintains a public data portal with downloadable report-card datasets covering discipline, absenteeism, and related disaggregations. Strategy: prefer state datasets where they exist and are more current than CRDC, clearly disclose methodological differences between sources.

### Comparison Engine

For every metric, the system calculates where a school sits relative to four benchmarks:

1. Its own district
2. Its state
3. The national average
4. Schools with similar demographics (Title I status, enrollment size, locale, FRL percentage)

The fourth comparison is critical. A Title I school in rural Arkansas should not be benchmarked raw against suburban Bellevue. Peer-normed comparison is what makes flags meaningful.

### Flag Layer

Green / yellow / red indicators based on research-informed thresholds, not arbitrary cutoffs.

**Climate and equity flags:**
- Discipline disparity ratio (any race vs. white) > 2.0 = yellow, > 3.0 = red
- Counselor-to-student ratio > 1:400 = yellow, > 1:500 = red
- Chronic absenteeism > 20% = yellow, > 30% = red

**Demographic-adjusted performance flags: the most important insight the tool produces.**

A GreatSchools 9 at a Bellevue school with 10% free/reduced lunch is demographics working as predicted. A GreatSchools 9 at Fairhaven with 45-50% economically disadvantaged students is educators outperforming what poverty rates would predict. These are fundamentally different achievements, and no existing tool distinguishes between them.

The briefing compares each school's academic performance against what its demographic profile would predict, and flags the result:

- 🟢 **Outperforming demographics:** Scores significantly exceed what poverty rate, FRL percentage, and demographic composition would predict. Translation for parents: "The educators in this building are doing something right. This school is punching above its weight."
- 🟡 **Performing as expected:** Scores track with the school's demographic profile. Neither a positive nor a negative signal; it's the baseline.
- 🔴 **Underperforming demographics:** Scores fall significantly below what the school's resources and demographics would predict. A school in an affluent area with high per-pupil spending and low poverty that still scores mediocre is a red flag the current rating systems actively hide. Those kids should be thriving given the advantages they arrive with.

This flips the segregation argument into something actionable. Instead of just proving that ratings reflect wealth (the critique), the tool shows parents where ratings *don't* reflect wealth — and those schools are where the strongest teaching is happening. It's the SchoolSparrow insight operationalized: the schools that deserve recognition are the ones beating expectations, not the ones coasting on zip code.

This flag requires comparing each school's proficiency/growth scores against a predicted score based on FRL percentage, locale, and enrollment demographics. The prediction model doesn't need to be complex — a regression against FRL percentage alone explains 70-80% of variance in test scores nationwide (the same research that indicts GreatSchools). Schools significantly above that regression line are outperforming. Schools significantly below it are underperforming.

Every flag includes:
- What the number is
- What the threshold is and where it comes from
- What it might mean (and what it might not)
- A specific question the parent can ask the school

### Interpreting Discipline and Safety Data: Legal Constraints as Context

A critical design principle: **the tool must account for the legal limitations schools face when flagging discipline or safety concerns.**

Schools operate under overlapping and sometimes conflicting legal mandates. When a briefing surfaces a concerning pattern — a student with documented aggression remaining in a setting, low suspension rates despite reported incidents, or a discipline rate that seems inconsistent with parent experience — the explanation may not be negligence. It may be structural.

**Illustrative example: Bellingham School District bus assault case (2024-2026)**

The district admitted liability after a 9-year-old student with a "documented history of assaulting students on the school bus" sexually assaulted another child. A parent reading this flag would reasonably ask: why was a known aggressor still on the bus?

But consider the legal constraints:
- If the aggressor has an IEP, transportation may be a **related service under IDEA**. Removing bus access could constitute a change of placement, triggering due process protections and requiring a manifestation determination.
- Even without an IEP, removing a child's transportation effectively removes school access — a due process issue for any student.
- The district may have been legally unable to remove the child without violating federal disability law, while simultaneously being unable to prevent harm to other students.
- What the district clearly *did* fail to do was report the assault — a separate, unambiguous legal obligation under RCW 26.44.030.

**Design implication:** When the AI generates narrative around discipline or safety flags, the prompt instructs it to consider whether the school or district may have been operating under competing legal mandates — IDEA, Section 504, due process, FAPE requirements — that constrained its options. The briefing presents this context rather than assuming negligence. It distinguishes between failures of *compliance* (not reporting, not following policy) and situations where the institution was caught between conflicting legal obligations.

This does not excuse harm. It does not minimize the experience of the child who was assaulted. It gives parents the structural understanding they need to ask the right questions: not "why didn't you remove that kid?" but "what is your protocol for managing known safety risks when removal isn't legally available? Do you have bus aides? Alternative transport arrangements? A safety plan?"

This principle applies beyond transportation — to in-school discipline, restraint and seclusion, suspension disparities, and any situation where a school's apparent inaction may reflect legal constraints rather than indifference.

### AI Layer

AI does not generate data. It interprets, contextualizes, and narrates structured data already in the database.

**Haiku (workhorse, ~80% of AI calls):**

*Risk signals:*
- Searches for local news and events that explain data anomalies (natural disasters, strikes, leadership turnover, COVID policies)
- Scans for reputation concerns (superintendent investigations, OCR complaints, Title IX lawsuits, state interventions)
- Summarizes recent school board meeting coverage

*Strength signals:*
- DonorsChoose projects (what teachers are requesting reveals both engagement and resource gaps — a school where every project asks for basic supplies sends a different signal than one requesting robotics kits)
- Educator recognition: state Teacher of the Year nominees, National Board Certified teachers, Milken Awards, Presidential Awards for Excellence
- School-level recognition: Blue Ribbon, Green Ribbon, PBIS implementation awards, AP Honor Roll, state distinguished school designations
- Grant wins: Title IV-A, 21st Century Community Learning Centers, state innovation grants, Magnet School Assistance
- Program signals: dual language/immersion, restorative justice adoption, community school designation, college/employer partnerships
- Community investment: local bond/levy passage rates (public record — a community that passes school levies is invested in its schools)
- ESSER spending choices: did the district invest in tutoring and mental health, or plug budget holes?

*The balance matters.* A briefing that only surfaces problems is a fear machine. A school might get a red flag on discipline disparities AND a strength signal for PBIS implementation — which together tell a richer story than either alone. It means the school knows it has a problem and is actively working on it. The briefing must surface what's working alongside what's concerning, or parents will stop trusting it.

*Validation and moderation:*
- Screens parent field report submissions for quality and categorization
- Validates its own outputs via LLM-as-judge second pass (different prompt reviews findings, flags lack of credible sources, catches wrong-school confusion, returns cleaned set with confidence scores)

**Sonnet (narrative, ~20% of AI calls):**
- Generates the parent-facing briefing narrative: what this data means, what to ask, what's missing
- Requires better judgment on tone: trustworthy, not alarmist; honest, not overwhelming
- Handles caveat language and the "What's Missing" disclosure section

**No AI call is made at lookup time for cached schools.** First parent to look up a school triggers briefing generation (~$0.05-0.08 in API cost). Every subsequent lookup serves the cached briefing. AI only re-fires on data refresh or new parent field reports crossing the corroboration threshold.

### AI Ethics by Design

A civic tool that surfaces sensitive information about schools — lawsuits, investigations, discipline disparities, student deaths — can cause real harm if built carelessly. School Daylight treats ethics as architecture, not afterthought.

The project maintains a living **harm register** (`docs/harm_register.md`) that documents every potential harm identified during development and the specific design decision made in response. The harm register is not documentation after the fact. It drives design: when the sensitivity review surfaced findings about student suicides, the harm register entry produced the death-suppression rules. When discipline disparity ratios proved unreliable at small subgroup sizes, the harm register entry produced the minimum-N threshold. When Sonnet hallucinated an outcome that never happened (fabricating "placed on leave but later cleared" for a school where no such resolution existed in the data), the harm register entry produced the three-stage pipeline architecture that separates editorial judgment from narrative writing.

The **three-stage pipeline** is the result of this process:

1. **Stage 0 (code pre-filter):** Mechanical rule enforcement: conduct-date anchoring, dismissed-case exclusion. Rules that models consistently failed to apply are enforced in Python, not prompts. The model never sees findings that fail these checks.
2. **Stage 1 (Haiku triage):** Editorial judgment: recency windows, severity exceptions, pattern detection, parent relevance filtering. Haiku passes through only facts explicitly stated in each finding. No outcomes, resolutions, or dispositions are added.
3. **Stage 2 (Sonnet narrative):** Writing only. Sonnet receives pre-filtered, pre-triaged findings and writes the parent-facing narrative. It cannot add facts not present in the input. Names are stripped, death details are suppressed, politically sensitive topics are presented neutrally.

Each stage does what it is best at. Code enforces mechanical rules. Haiku handles structured judgment. Sonnet handles prose. The separation is deliberate: hallucination risk lives in the generative writing layer, so editorial judgment is removed from that layer entirely.

Fourteen editorial rules govern what appears in a school briefing and how. Each rule originated from a specific harm identified during manual sensitivity review of web-sourced findings. Every rule is tested, with pass/fail criteria, against specific schools. The rules and their test results are documented in the Phase 4.5 test plan and exit document.

In a project where AI interprets sensitive public data about children, the ethics are not a layer applied on top of the architecture. They are the architecture.

### Caching and Cost Strategy

| Scenario | AI Cost |
|----------|---------|
| First lookup of a school | ~$0.05-0.08 |
| Subsequent lookups (cached) | $0.00 |
| 1,000 unique schools | ~$50-80 total |
| 10,000 lookups of those 1,000 schools | ~$50-80 total (same) |
| Data refresh (batch, overnight) | 50% discount via Batch API |
| Prompt caching (system prompt reuse) | 90% cheaper on repeated boilerplate |

This is how the app stays free. The cache fills, the per-lookup cost approaches zero, and the only ongoing spend is periodic refresh cycles.

### Parent Field Reports (Feedback Loop)

Not a public forum. A moderated intelligence layer.

Parents can submit updates after visiting a school or attending a board meeting: "Principal changed September 2025." "New inclusion coordinator hired." "Class sizes are actually 35, not the 18:1 ratio reported."

- Haiku screens submissions for quality and categorizes them (leadership change, staffing update, program change, climate observation)
- Single reports are stored but not surfaced in briefings
- When 2-3 independent reports corroborate the same finding, the briefing incorporates the pattern — never quoting submissions directly
- No public visibility, no comment wall, no audience — removes the incentive structure that makes Yelp and Niche reviews toxic
- Over time, this becomes a unique compounding dataset: human-verified, parent-sourced ground truth layered on federal data

### Output: The Briefing

A single document (web page, optionally downloadable) using **progressive disclosure**: a 2-3 sentence headline summary at the top ("Here's what stands out"), with expandable detail sections below. Modeled on the CMS hospital comparison pattern — show methodology, let users drill down, be explicit about update cadence and peer grouping. Contains:

1. **Rating context:** What GreatSchools/Niche/U.S. News say, what those numbers measure, and where they diverge from each other
2. **Academics in context:** Proficiency and growth scores benchmarked against district, state, and demographic peers. Includes the demographic-adjusted performance flag: is this school outperforming, meeting, or underperforming what its poverty rate would predict? This is the single most important insight in the briefing, separating schools where educators are genuinely strong from schools where high scores simply reflect affluent zip codes.
3. **Demographics:** Who attends, how that's changed, and how it compares to the area
4. **Staffing and resources:** Student-teacher ratio, counselor ratio, teacher certification, per-pupil spending, flagged against meaningful benchmarks
5. **Strengths and recognition:** Grants funded, educator awards, program designations (Blue Ribbon, PBIS, restorative justice), DonorsChoose activity, community investment signals like levy passage. What's working.
6. **Climate and discipline:** Suspension rates by race and disability, restraint/seclusion, law enforcement referrals: the CRDC data nobody surfaces
7. **Reputation and news:** District leadership issues, investigations, lawsuits, OSPI/OCR actions, school board coverage
8. **Statewide context:** Pandemic recovery, policy changes, anything that affects how to read this year's numbers
9. **What's missing:** Explicit disclosure of every data point the briefing couldn't access or that doesn't exist
10. **Peer schools:** 3-5 schools serving similar populations, with the same metrics, for meaningful comparison
11. **Did You Know?:** Notable alumni, fun historical facts about the school, memorable moments. Light, human, clearly separated from data sections. Not a quality indicator, just a reason to smile during a dense briefing. Designed to include local stories (teacher who returned to teach at her own school, state science fair winner) alongside any widely known names. Haiku-sourced, lightly validated.
12. **Action layer:** What to ask, who to ask, next school board meeting date, how to request public records, relevant advocacy organizations

---

## Launch Scope

**Phase 1: Washington State**
- ~2,300 public schools
- CRDC + NCES + OSPI data pipeline
- Single-school lookup
- Cached briefing generation
- No parent field reports yet

**Why Washington:**
- The builder lives here and has a child in the system
- OSPI has relatively strong public data infrastructure
- Bellingham district (prototype school) has a compelling story with data the ratings miss
- Small enough to validate on Atlas free tier, large enough to demonstrate the concept

**Phase 2: Expand to states with stories to tell**
- States with strong CRDC disparities, active advocacy communities, or ongoing controversies
- Each state requires mapping its specific report card data portal

**Phase 3: National**
- Full CRDC national file (~98,000 schools)
- Peer comparison engine across states
- Parent field report system

---

## What This Costs

| Item | Cost | Notes |
|------|------|-------|
| Data | $0 | All federal and state sources are free |
| MongoDB Atlas | $0-60/month | Free tier for WA-only; M10 at ~$50-60/month for national |
| AI (briefing generation) | ~$50-80 per 1,000 unique schools | Cached after first generation |
| AI (refresh cycles) | ~$25-40 per batch cycle | 50% Batch API discount |
| Hosting | ~$0-20/month | Streamlit Community Cloud or equivalent |
| Domain | ~$12/year | |
| **Total for WA launch** | **< $100** | |
| **Total for national at scale** | **~$100-200/month** | Dominated by MongoDB, not AI |

No VC funding required. No enterprise sales. No paywalled features. The app is free because it costs almost nothing to run. The code is open source because public data interpreted by hidden code isn't civic infrastructure — it's a black box.

---

## Competitive Landscape

| Competitor | What They Do | What They Don't Do |
|-----------|-------------|-------------------|
| **GreatSchools** | 1-10 score based on test scores, growth, equity. Embedded in every major real estate site. | Doesn't surface CRDC data. Score still correlates heavily with income. Enterprise-licensed. |
| **Niche** | A-F grades based on test scores, demographics, and 3M user reviews. | No CRDC discipline/equity data. Reviews are unmoderated Yelp-style. No public API. |
| **SchoolSparrow** | Controls for parent income impact on test scores. Anti-segregation positioning. | Still a rating system, still a number. Founded 2012, still niche. Real estate broker, not educator. |
| **State dashboards** (OSPI, CA DataQuest, etc.) | Publish CRDC and state data through compliance portals. | Built for researchers, not parents. Government-grade interfaces. |
| **Schoolytics** | Internal dashboards for educators: attendance, behavior, SEL. | Sold to districts. Parents can't access. |

**The gap:** No consumer-facing tool pulls CRDC data, combines it with state metrics, contextualizes it against meaningful peers, flags anomalies with research-backed thresholds, checks local news for reputation signals, and presents it all to a parent in plain language with specific questions to ask. And critically: no tool tells a parent whether their school's scores reflect good teaching or just a wealthy zip code — the demographic-adjusted performance flag that separates genuine quality from demographic gravity. That is what School Daylight does.

### Prior Art: What's Been Built and What Died

The closest existing precedent is **ProPublica's Miseducation** — a searchable database covering ~96,000 schools and ~17,000 districts, presenting discipline and opportunity gaps with derived disparity measures (risk ratios) and side-by-side comparisons against district and state averages. It included a real statistical interpretation layer, not just raw data access. It was framed as investigative accountability journalism, not parent utility — but it proved the concept matters.

Critically: **Miseducation stopped updating after the 2015-16 CRDC cycle.** OCR has published two full cycles since (2020-21 in November 2023, 2021-22 in January 2025). ProPublica built it, proved it was important, and couldn't sustain it because newsrooms aren't software companies. The gap has been open for a decade.

ProPublica also built **"Has Your School Been Investigated for Civil Rights Violations?"** — a lookup tool identifying OCR investigations and allegation categories from federal case-status data (FOIA-obtained resolved cases). This is exactly the reputation/investigations layer in the briefing. It already exists as a concept — I should pull from it rather than recreate it.

Other stalled or dead projects:

- **Advancement Project's SafeQualitySchools** — Web presence tied to "Ending the Schoolhouse-to-Jailhouse Track" with interactive data components. Domain now returns errors. Consistent with the nonprofit pattern: software is expensive to maintain relative to policy work.
- **CRDC API** — GSA's federal APIs inventory lists a "Civil Rights Data Collection API" pointing to a usedgov.github.io page. The page returns 404. Suggests deprecation or a non-authoritative listing never maintained. I plan on bulk-file ingestion and my own stable interfaces, not a reliable official API that doesn't exist.
- **Arizona, Kentucky, and Texas** have experimented with embedding CRDC data in state report cards — but with masking/suppression challenges and no interpretive layer beyond what the state compliance portal requires.

### Why This Hasn't Been Built (Until Now)

ProPublica needed a team of data journalists, developers, editors, and fact-checkers. They wrote custom code to parse CRDC flat files, built a web application, designed statistical methodology, wrote narrative framing, and maintained it across data cycles. This represented hundreds of thousands of dollars in salary and infrastructure. They did it once, for one CRDC cycle, and couldn't justify doing it again.

The economics have changed. School Daylight is being built by one person using:

- Claude Code to build the data pipeline
- Claude API at ~$0.05/briefing to generate narrative interpretations
- MongoDB Atlas free tier to store structured data
- Public CSVs that download for nothing
- A $100/month AI subscription to design the whole thing in conversation

The cost structure that killed ProPublica's version no longer exists. The team they needed is a conversation with an LLM. The maintenance burden that made them stop updating — re-ingesting new CRDC cycles, regenerating briefings, updating narratives — is a batch job running overnight for under $50.

Through April 2026, the total project spend on AI API costs is approximately $120 — covering data enrichment of 1,630 schools, editorial rule testing across 50 schools, and iterative prompt development. An additional $100 in API credits covers the Phase 5 production run. The entire project, from pipeline to production, will cost under $250 in AI.

A civic tool that previously required newsroom-scale investment can now be built and maintained by one person. That's the thesis.

---

## Known Risks and Design Responses

These risks were identified through competitive research and stress-testing the concept against prior failures in this space.

### 1. Statistical Methodology Requires Independent Review

The builder is not a statistician. The comparison engine uses a per-level linear regression (elementary, middle, high) against free/reduced lunch percentage to predict academic performance and flag schools as outperforming, meeting, or underperforming demographic expectations. This is the single most consequential calculation in the product: a school labeled "underperforming demographics" when the model is miscalibrated suffers reputational harm based on a math error, not a real failing. Similarly, discipline disparity ratios, chronic absenteeism thresholds, and peer cohort matching all involve statistical choices with real-world consequences for schools and communities.

A concrete example: the per-level regression treats all elementary schools as one population. But a K-2 school and a K-6 school face structurally different testing populations. If the model doesn't account for grade-span differences within the "elementary" category, it could systematically misclassify certain schools. The builder wouldn't catch this because it requires statistical expertise to recognize and correct.

**Design response:** A qualified statistician will review the regression methodology, threshold calibrations, peer cohort definitions, and disparity ratio calculations before launch. An academic sociologist with quantitative methods expertise has agreed to review. The review will cover: whether the FRL-only regression is sufficient or needs additional covariates, whether the per-level split adequately controls for grade-span variation, whether the minimum-N threshold for disparity ratios is appropriately set, and whether the chronic absenteeism thresholds reflect the post-COVID distribution. No briefings will be published until this review is complete. The tool's credibility depends on the statistical layer being defensible to researchers, not just plausible to a general audience.

### 2. CRDC Data Is Structurally Late and Noisy

OCR describes the CRDC as a mandatory survey with self-reported data and an evolving quality pipeline. Districts submit, OCR runs quality checks and applies suppressions and privacy protections before publishing. Reported counts can differ from other ED sources due to methodological and population differences. The 2020-21 cycle comparisons are complicated by pandemic impacts. If the briefing flags "anomalies," some will be reporting artifacts, definitional misunderstandings, or suppression artifacts — not real behavioral differences.

**Design response:** Already architected for this. The "What's Missing" section discloses data vintage and known limitations. State-level data fills gaps between CRDC cycles. Every flag includes caveat language about what it might and might not mean. The tool never presents CRDC counts as findings of fact — they are reported indicators that may warrant questions.

### 3. Restraint/Seclusion Data Is a Landmine

GAO concluded that the Department of Education needed to address "significant quality issues" in CRDC restraint/seclusion data, including ineffective quality controls and inconsistent interpretation of definitions across districts and state agencies (e.g., the meaning of "alone" in seclusion). Risk: defaming a school with bad data, or giving a false clean signal where underreporting is happening.

**Design response:** Restraint/seclusion flags get extra caveat language, lower confidence presentation, and explicit disclosure of the GAO findings. Where state-level restraint/seclusion data exists (e.g., California's CALPADS-sourced files), prefer it over CRDC and disclose the difference. Never present restraint/seclusion counts with the same confidence as enrollment or test score data.

### 4. Suppression and Small-N Make School-Level Equity Comparisons Unstable

CRDC suppresses small cell sizes for privacy. ProPublica's methodology shows how often cells are "not available" or statistically non-significant for subgroup comparisons — especially race-by-program or race-by-discipline at smaller schools. Many parents will see a lot of "missing / not reported / too small to display," which could undercut the "comprehensive briefing" promise.

**Design response:** Real but not fatal. The briefing already has a "What's Missing" section that discloses suppressions explicitly. District-level data often survives suppression when school-level doesn't — use district as fallback with clear labeling. Show what I can, disclose what I can't, explain why. The briefing's value isn't that every cell is populated — it's that parents know which cells are empty and why.

### 5. Parents Might Not Want Complexity

Rankings drive sharing. "My school is 8/10" is shareable; a nuanced briefing isn't. State report card practitioners note stakeholder preference for simple summaries over dense tables. Without a summary hook, the product may need alternative engagement loops — shareable question cards, printable one-page summaries, time-to-read estimates — to get adoption.

**Design response:** This assumes I need viral growth. I don't. I need a tool useful to the parent who finds it. The product will also serve journalists, advocates, school board members, and policy staff as power users — ProPublica explicitly designed Miseducation for this dual audience. That said, the briefing should offer progressive disclosure: a headline summary at the top (2-3 sentences, what stands out), expandable detail sections below. The CMS hospital comparison model — show methodology, let users drill down, be explicit about update cadence and peer grouping — is the right design pattern.

### 6. Political Sensitivity Around Civil Rights Data

Surfacing race-disaggregated discipline disparity data during a period of contested civil-rights enforcement is politically sensitive. Recent changes in OCR enforcement capacity and priorities could affect both data availability and the perceived legitimacy of civil-rights investigations as context. Even presenting "just public data" may be treated as partisan or as an enforcement mechanism.

**Design response:** The most important structural risk, not because it stops me from building, but because it affects framing. The tool presents public federal data with context. It doesn't editorialize. The legal constraints design principle (presenting competing mandates rather than assuming negligence) is exactly the kind of choice that insulates against political framing. Language discipline matters: CRDC counts are not findings of wrongdoing. Reported indicators may warrant questions. The EPA EJSCREEN precedent (removed from EPA website, mirrored by third parties) reinforces the case for bulk-ingested, locally-cached data rather than dependence on federal hosting, but also increases the need for transparent sourcing and careful claims.

### 7. Parent Field Reports Create Liability Risk

Even without public reviews, inviting allegations (bullying, discrimination, unsafe practices) is reputationally sensitive for schools and districts. If reports are published or algorithmically surfaced, legal threats and backlash may follow regardless of truth: harm from dissemination is immediate while adjudication is slow.

**Design response:** Already designed around this: no public visibility, corroboration threshold required, AI synthesizes patterns not quotes, no publish-immediately dopamine loop. But language matters. Terms like "flag," "warning," and "anomaly" imply wrongdoing. The briefing should use softer framing: "stands out," "differs from peers," "worth asking about." The police-accountability data model is instructive: NYC's civilian complaint review board data carefully separates "allegation," "finding," and "outcome" to avoid implying guilt. CRDC counts are reported data, not adjudicated findings.

---

## Potential Validators and Partners

Organizations shaping the CRDC ecosystem whose methodological norms and interpretive frameworks should inform the tool's thresholds, language, and credibility:

- **The Education Trust:** Publishes CRDC-focused analyses engaging interpretive questions (how to interpret discipline disparities, what to watch for in new releases, where CRDC data is strong vs. questionable). A parent-facing tool flagging disciplinary disproportionality will be evaluated against their existing advocacy narratives and methodological norms.

- **Civil Rights Project at UCLA:** Center of the literature on exclusionary discipline and disparate impact, leveraging CRDC definitions. Has warned that relative measures like risk ratios can be misleading without absolute-rate context. Directly supports the "no score, explain complexity" thesis.

- **Learning Policy Institute:** Research-heavy, publishes on suspension and discipline, bridges research to policy and practice audiences. Can anchor "research-informed thresholds" and the "what questions should a parent ask" framing.

- **Brookings Institution:** Interpretive work on chronic absenteeism metrics including cautions about measurement accuracy and standardization across states.

- **End Zero Tolerance:** Focuses on national datasets (often CRDC) while warning data can be incomplete or inaccurate. Authority to cite when disclosing limitations.

- **Leadership Conference on Civil and Human Rights:** Submits detailed public comments on CRDC content choices, indicating sustained stakeholder engagement with what gets collected and how.

Getting 2-3 reviewers from these organizations to spend 30 minutes reviewing flag thresholds and language before launch would materially improve credibility and catch blind spots.

---

## Open Questions

1. **Advisory review:** Thresholds for green/yellow/red flags need validation from education researchers and/or school administrators before launch. See Potential Validators section above for target organizations.

2. **CRDC data freshness:** The 2021-22 CRDC reflects a school year still heavily affected by COVID. The 2023-24 data was submitted through April 2025 and was expected to be published by end of 2025. Is it available yet? If not, how prominently do I caveat the COVID-era data?

3. **Suppression communication:** CRDC suppresses small cell sizes for privacy. The briefing discloses these gaps in "What's Missing" — but the format and language need testing with actual parents to see if "suppressed for privacy (fewer than X students)" is clear or alienating.

4. **Growth data availability:** Washington publishes student growth percentiles through OSPI, but accessibility varies. Can I reliably get school-level growth scores for the WA launch?

5. **Legal review:** Does surfacing CRDC discipline disparity data alongside school names create any liability exposure? (Likely no — it's public federal data — but worth confirming.) Separate question: does the parent field report system create liability even with corroboration thresholds and no direct publication?

6. **~~Name:~~** ~~"School Briefing" is a working title. Does it communicate what the product actually does?~~ **Resolved.** School Daylight. Domains secured: schooldaylight.com and schooldaylight.org.

7. **Language calibration:** Terms like "flag," "warning," and "anomaly" imply wrongdoing. Need to develop and test a vocabulary that conveys "this stands out and is worth understanding" without implying "this school did something wrong." Police-accountability and healthcare public-reporting language patterns are instructive models.

8. **Political durability:** If federal CRDC collection or publication is disrupted (as happened with EPA's EJSCREEN), how quickly can I pivot to state-only data sources? What's the minimum viable briefing without CRDC?

9. **ProPublica data reuse:** Can I incorporate or reference ProPublica's OCR investigations lookup data and Miseducation's historical disparity calculations, or do I need to build from primary sources? What licensing applies to their published datasets?

---

## Key References

- **Hasan, S. & Kumar, A. (2019).** "Digitization and Divergence: Online School Ratings and Segregation in America." Working paper, Duke University / University of Florida. Found that the staged rollout of GreatSchools ratings from 2006-2015 accelerated divergence in housing values, income distributions, and racial composition across communities.

- **Schneider, J. (2021).** "Ratings, Rankings, and Segregation: The Failure of Measurement and Accountability in Education." Poverty & Race Research Action Council. Analyzes how school ratings embedded in real estate websites act as steering mechanisms that direct families toward whiter, more affluent schools regardless of quality.

- **Reardon, S.F. et al.** Stanford Educational Opportunity Project (edopportunity.org). Multiple studies documenting that standardized test score gaps correlate with family socioeconomic factors and residential segregation, not differences in school quality or student ability.

- **Schneider, J. & Noonan, J. (2024).** "Beyond 'Good' and 'Bad': Disrupting Narratives about School Quality." Phi Delta Kappan. Argues that narrow measurement systems correlated with student demographics undermine racial justice and economic equality.

---

*This document describes what I'm building and why. The next documents are: data dictionary (mapping source columns to briefing fields), briefing template (structured schema for repeatable generation), and user flow (one parent, one school, one briefing).*
