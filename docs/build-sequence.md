# School Daylight
### Build Sequence v0.1
### February 2026

---

## How to Use This Document

This is the step-by-step build plan. Each phase has: what we're building, who does the work (human or agent), what the output is, and what has to be true before moving to the next phase. Phases are sequential — each depends on the one before it.

**Three roles throughout:**

1. **You (the builder):** Download files from government portals. Make design decisions. Review agent output. Read briefings and iterate on quality. ~8-12 total hours of human time for WA launch.
2. **Claude Code (the agent):** Build the data dictionary, ETL pipeline, comparison engine, AI enrichment, narrative generation, frontend, and testing utility. Does the coding, the column mapping, the data cleaning, the computation.
3. **The testing utility (the quality gate):** Runs after every phase. Catches wrong data, bad joins, fabricated claims, forbidden language. The thing that lets you trust agent output without reading every line of code.

**Phase numbering note.** Phase 6 has been split into 6A (design), 6B (mockup), and 6C (build) following the precedent of Phase 3R (the R suffix marked a structural expansion of an original phase). Existing phase receipts, build log entries, and `phases/` directories referencing earlier phase numbers remain valid. Phases 7 (testing) and 8 (iterate and harden) keep their original numbers.

**Two-stage launch.** The frontend launches in two stages. Phase 6C deploys a soft launch at beta.schooldaylight.com with no public promotion, used as the artifact for reviewer outreach and parent comprehension feedback. Public launch at schooldaylight.com follows methodology review. Public launch is a configuration flip, not a separate phase.

---

## Claude Code Session Rules

These rules are based on Anthropic's official best practices and hard-won lessons from developers using Claude Code in production. They're translated here for a non-coder directing an agent — you won't write code, but you need to set up the environment that makes the agent reliable.

### Before the First Line of Code: The CLAUDE.md File

Claude Code reads a special file called `CLAUDE.md` at the root of your project every time it starts a session. Think of it as the onboarding document you'd give a new hire on their first day. Without it, the agent starts every session with no memory of your project's decisions, conventions, or architecture.

**Create this file before Phase 1.** It should contain:

```markdown
# School Daylight

## What This Is
Civic data tool generating school briefings from public federal and state data.
One-person build. All code written by Claude Code. Builder reviews output, not code.

## Architecture
- Python ETL pipeline → MongoDB Atlas → Streamlit frontend
- NCES ID is the universal primary key for all school data
- One document per school, everything embedded (not separate collections)
- All credentials in config.py reading from .env — NEVER hardcode secrets

## Critical Rules
- Suppressed values: store as null with {"suppressed": true} — NEVER as zero
- Zero means "zero incidents." Null-suppressed means "can't tell you." These are different.
- Pipeline must be idempotent: safe to run twice, identical results
- Cleaning rules go in cleaning_rules.yaml, not buried in Python
- Prompts go in prompts/ as versioned plaintext files
- Every script logs: how many matched, how many failed, how many suppressed
- Commit after each completed step with a clear message

## Commands
- Run pipeline: python run_pipeline.py
- Run tests: python run_tests.py
- Run single golden school check: python run_tests.py --school fairhaven

## Project Files
- Foundation document: docs/foundation.md (product decisions, mission, architecture)
- Data dictionary: data/data_dictionary.yaml (column mappings, schema)
- Build log: docs/build_log.md (chronological decision record)
- Cleaning rules: pipeline/cleaning_rules.yaml

## Testing
- Golden school: Fairhaven Middle School, Bellingham WA
- Every phase ends with verification receipt (see docs/testing-utility.md)
- No phase proceeds until previous phase receipt is green
```

**Keep it under 150 lines.** The research is clear: bloated CLAUDE.md files degrade output quality. If Claude Code keeps getting something wrong, add a rule. Don't preemptively document everything.

### The Three-File Pattern (Per Session)

Developers report that Claude Code works dramatically better when each work session has three short files tracking state. For you, this means each phase gets:

```
phases/phase-1/
├── plan.md        ← What we're doing and how (from this build sequence)
├── context.md     ← Key files to read, decisions made so far, where we left off
└── tasks.md       ← Checklist of steps, checked off as completed
```

When starting a new Claude Code session, point it at these files: *"Read phases/phase-1/plan.md, context.md, and tasks.md, then continue from where we left off."* This is how you survive the fact that Claude Code has no memory between sessions.

### Commit After Every Completed Step

Tell Claude Code in every prompt: *"Commit your work after each completed step with a clear message explaining what you did."*

This is your undo button. If Step 4 breaks something that worked in Step 3, you can revert to the Step 3 commit and try again. Without commits, you're debugging a mystery. With commits, you're reverting to a known-good state. Git is your safety net — use it aggressively.

### Start Fresh Between Phases

Claude Code accumulates context during a session — every file it reads, every command it runs, every error it encounters. After ~60,000 tokens (roughly 30-45 minutes of intensive work), the quality degrades. The agent starts "forgetting" rules from the CLAUDE.md, making inconsistent decisions, or repeating mistakes.

**The fix:** Use `/clear` between phases and when starting new tasks. Don't let context from Phase 1's data dictionary work bleed into Phase 2's pipeline building. Each phase is a fresh session that reads the CLAUDE.md and the phase's three files.

### Plan Before Code

Every phase prompt should start with: *"Before writing any code, read [files] and create a plan. Show me the plan. Do not implement until I approve."*

Community consensus across 12 independent sources: the single biggest predictor of code quality is whether the agent planned before coding. "Vibe coding" (just letting it go) works for throwaway experiments. For a civic tool that makes claims about schools, planning is non-negotiable. You already know this — it's why the foundation document exists.

### When the Agent Gets Stuck

If Claude Code produces something wrong, the instinct is to keep prompting in the same session — "no, that's wrong, try again." Developers report this rarely works well. The agent digs deeper into its wrong approach rather than reconsidering.

**Better pattern:** Copy the error or wrong output into a new session. Start fresh. *"I was trying to do X. Here's what happened: [paste error/problem]. The plan is in phases/phase-2/plan.md. Try a different approach."*

Fresh context with a clear problem statement beats iterating in a polluted session almost every time.

### The Verification Receipt Is the Session's Final Act

Every Claude Code session for this project must end with the agent producing a verification receipt. Add this to every phase prompt:

*"After completing all steps, produce a verification receipt in plain English showing: what you built, what you tested, what passed, what failed, and any items that need human review. Save it as phases/phase-N/receipt.md."*

The agent should never declare a phase complete without this receipt. It's the equivalent of a developer saying "it works on my machine" — the receipt forces the agent to prove it.

---

## Phase 0: Download Source Files (Human, ~1 Hour)

**What:** You find and download the actual data files from federal and state portals. This is the one step that requires a human navigating government websites — the portals are messy, files are buried behind menus, and naming conventions are unpredictable. This is 20 years of navigating bureaucratic systems put to work.

**Files to download:**

| Source | Where to Find It | What to Download |
|--------|------------------|-----------------|
| **CRDC 2021-22** | ocrdata.ed.gov → Downloads | Public-use flat file (CSV), file layout documentation (PDF) |
| **NCES CCD** | nces.ed.gov/ccd → Data Files | Public school universe file (CSV), file layout documentation |
| **OSPI Report Card** | data.wa.gov or OSPI data portal | Academics (proficiency, growth), discipline, chronic absenteeism, demographics |
| **OSPI School Directory** | OSPI data portal | School directory with NCES ID crosswalk (maps state codes to federal IDs) |
| **OSPI Finance** | OSPI SAFS files | Per-pupil expenditure data |

Also download any data dictionaries, file layout PDFs, or documentation published alongside these files. These are what tell the agent what each column means.

**Drop everything in a folder:** `/states/WA/raw/`

**Gate:** You have the actual CSV/Excel files and their documentation. Don't worry about opening or understanding them — that's the agent's job.

---

## Phase 1: Data Dictionary, Exploration, and Schema (Claude Code Agent, Review by Human)

**What:** Hand the downloaded files and the foundation document to Claude Code. The agent reads the files, reads the documentation, builds the complete data dictionary, designs the MongoDB schema, and tests that everything joins on a known school.

**This replaces what was originally scoped as two separate human-intensive phases** (data dictionary and data exploration). The agent does both simultaneously because it needs to look at the actual data to build the mapping.

**The prompt to Claude Code:**

*"Here is the School Daylight foundation document — it describes every field the briefing needs, which sources provide which data, and the design decisions already made (NCES ID as primary key, one document per school, embedded structure). Here are the raw data files and their documentation from /states/WA/raw/. Do the following:*

*1. Read every file — row counts, column names, sample rows, data types*
*2. Read the documentation PDFs to understand what each column means*
*3. Build a complete data dictionary: every source column we need, what it means in plain English, what field it maps to in our MongoDB schema, and your confidence level in the mapping*
*4. Identify all suppression markers in each source (non-numeric values in numeric columns, special codes like -9, *, <5, N/A)*
*5. Design the MongoDB document schema — one document per school, everything embedded*
*6. Test the join: find Fairhaven Middle School (Bellingham, WA) across all sources using NCES ID. Confirm the IDs match and the join works.*
*7. Output: completed data dictionary YAML, MongoDB schema definition, exploration report noting any surprises or problems, and a decision log explaining every mapping choice*
*8. Flag any mappings where you're less than 80% confident and explain why"*

**What the agent will produce:**

- `data_dictionary.yaml` — Every source column mapped to the schema
- `schema.yaml` — The MongoDB document structure
- `exploration_report.md` — File shapes, surprises, data quality issues found
- `decision_log.md` — Why each mapping was made, with confidence scores
- `fairhaven_test.md` — Proof that Fairhaven joins across all sources
- `verification_receipt.md` — **The self-check report (see below)**

**Built-in self-verification (how you know it worked):**

The agent doesn't just build the mapping — it runs a verification protocol on its own output and produces a receipt. This is not optional. The agent is prompted to do this as the final step before declaring the phase complete.

The verification receipt contains:

*Join test — did the data actually stitch together?*
- "Fairhaven Middle School (Bellingham, WA): Found in NCES CCD ✓ | Found in CRDC ✓ | Found in OSPI ✓ | NCES IDs match across all sources ✓"
- If any source fails to match: "CRDC: NO MATCH FOUND. Attempted COMBOKEY [value], NCES ID [value]. Possible causes: [list]." This is a hard stop — the agent reports the failure and does not proceed.

*Sample value cross-check — did the mapping put numbers in the right fields?*
- The agent picks 5 values for Fairhaven from the raw source files (e.g., enrollment from row 1,847 of CCD, column `TOTAL`) and shows them next to what the mapping produced:
  - "Enrollment: Source file says 587 (CCD row 1847, column TOTAL) → Mapped to schema field `enrollment.total` = 587 ✓"
  - "FRL count: Source file says 274 (CCD row 1847, column FRELCH) → Mapped to schema field `demographics.frl_count` = 274 ✓"
- If any value doesn't match, the receipt shows the mismatch: "Counselor FTE: Source file says 2.0 (CRDC, column `SCH_FTECOUNSELORS`) → Mapped to schema field `staffing.counselor_fte` = 0. ✗ MISMATCH — possible suppression marker treated as value."

*Suppression marker audit — are we handling missing data correctly?*
- "CRDC suppression markers found: -9 (appears 14,302 times across all WA columns), -2 (appears 3,411 times). Handling rule: both treated as null with suppressed flag."
- "OSPI suppression markers found: * (appears 891 times), N/A (appears 2,103 times). Handling rule: * = null/suppressed, N/A = null/not_applicable."
- "Zero verification: Confirmed that zero values in discipline columns are preserved as zero (meaning 'zero incidents'), not converted to null. Schools with 0 suspensions: 342. Schools with suppressed suspension data: 89. These are different and handled differently. ✓"

*Confidence summary — where should the human look?*
- "43 column mappings completed. 38 high confidence (>90%). 4 medium confidence (70-90%). 1 low confidence (<70%)."
- "LOW CONFIDENCE: OSPI column `GrowthIndex` — unclear whether this is a percentile (0-100) or a z-score (-3 to +3). Mapped as percentile based on value range in data (values between 20-80 observed). Human should verify."

*Completeness check — did we get everything we need?*
- "Foundation document requires 47 data fields across 12 briefing sections. Mapping covers 43. Missing 4: [list with explanation for each — e.g., 'DonorsChoose data not included in this phase, handled in Phase 4']."

**Why this matters:** You don't read the YAML. You don't read the Python. You read the verification receipt. It's a 1-2 page document in plain English that either says "everything checks out, here's proof" or "these specific things are wrong, here's what I found." Your review time drops from "understand the mapping" to "read the receipt and check the flagged items."

**If the receipt shows failures:** The agent does not proceed. It reports what failed, what it tried, and what it thinks went wrong. You look at the failures, make a decision (or ask me), and the agent tries again. The receipt for the second attempt shows what changed.

**Key decisions already made (the agent doesn't need to figure these out):**

- *School identity:* NCES ID is the universal primary key. CRDC joins via COMBOKEY (LEAID+SCHID). OSPI joins via the crosswalk file. The agent implements this, it doesn't decide it.
- *Document structure:* One MongoDB document per school, everything embedded. Briefing is one read, one fetch.
- *Suppression handling:* Suppressed values stored as `null` with `"suppressed": true` metadata flag. Not zero, not blank. Zero means "didn't happen." Null-suppressed means "can't tell you."
- *Scope:* The CRDC file has hundreds of columns. We need the subset defined in the foundation document (discipline by race/disability, restraint/seclusion, counselor/SRO counts, teacher cert, AP/IB access, SPED inclusion). The agent identifies the right columns for this subset, it doesn't decide what to include.

**Your review (~1-2 hours):**

The agent will get 85-90% of mappings right. Your job:

1. Read the decision log. Does the reasoning make sense?
2. Check every low-confidence mapping. Is the agent's best guess right?
3. Look at the Fairhaven test. Do the joined values look plausible? (You've already researched Fairhaven — you have intuition about what the numbers should look like.)
4. Approve the schema. This is the contract everything else builds on. Worth 30 minutes of careful reading.

**Gate:** You've reviewed and approved the data dictionary and schema. Any corrections have been made. The Fairhaven join test passes.

---

## Phase 2: ETL Pipeline and MongoDB Load (Claude Code Agent, Verified by Testing Utility)

**What:** Claude Code builds and runs the pipeline that cleans the raw files, joins them, and loads structured documents into MongoDB Atlas.

**The prompt to Claude Code:**

*"Here is the approved data dictionary and schema from Phase 1. Here are the raw data files. Build a Python ETL pipeline that:*

*1. Reads NCES CCD → extracts WA schools → creates base documents with NCES ID, name, address, district, locale, enrollment, demographics, FRL%*
*2. Reads OSPI crosswalk → maps state school codes to NCES IDs*
*3. Reads CRDC → filters to WA → joins on NCES ID → adds discipline, restraint/seclusion, staffing, course access, SPED fields*
*4. Reads OSPI academics → joins via crosswalk → adds proficiency, growth, chronic absenteeism*
*5. Reads OSPI finance → joins → adds per-pupil expenditure*
*6. Applies suppression handling rules: [markers from Phase 1] → null with suppressed flag*
*7. Writes all documents to MongoDB Atlas*
*8. The pipeline must be idempotent — safe to run twice, producing identical results (drop and recreate collection on each run)*
*9. Log at each step: how many schools matched, how many failed to join (and why), how many fields were suppressed*
*10. After loading, run the data integrity tests from the testing utility against Fairhaven and reference schools"*

**Technical requirements (already decided):**

- *Single config source of truth.* All credentials (MongoDB connection string, Anthropic API key, DonorsChoose key) are read from one file (`config.py` that loads from `.env`). Every script imports from `config.py` — credentials are never referenced any other way. This makes key rotation a one-file change instead of a scavenger hunt across six scripts.
- *Secrets management.* `.env` file holds actual keys locally (never committed). `.env.example` in the repo shows what's needed without real values. `.gitignore` includes `.env` so secrets can't accidentally reach GitHub. For Streamlit deployment, secrets go in their dashboard and the app reads from `st.secrets`.
- *Idempotent pipeline:* Drop and recreate on each full load. No incremental-update bugs. For ~2,300 schools this takes seconds.
- *Atlas free tier:* M0 cluster, 512MB storage, more than enough for WA. Connection string via environment variable, never hardcoded.
- *Python packages:* `pandas`, `pymongo`, `scikit-learn` (for Phase 3). Standard, well-documented.
- *Open source from day one:* No secrets in code. All API keys and connection strings as environment variables. `.env.example` file in repo showing what's needed without actual values.

**What the agent builds:**

```
pipeline/
├── 01_load_nces.py
├── 02_load_crosswalk.py
├── 03_load_crdc.py
├── 04_load_ospi_academics.py
├── 05_load_ospi_finance.py
├── 06_write_to_atlas.py
├── run_pipeline.py          # Runs all steps in order
├── cleaning_rules.yaml      # Every transformation, documented
└── pipeline_log.md          # Auto-generated: match/fail/suppression counts
```

Plus the cleaning rules in readable YAML — not buried in Python. A researcher can open `cleaning_rules.yaml` and understand every transformation without reading code.

**Verification (testing utility + self-check receipt):**

The agent runs Layer 1 of the testing utility after loading AND produces a verification receipt — same pattern as Phase 1. You read the receipt, not the code.

The Phase 2 verification receipt contains:

*Load summary — what went in?*
- "WA schools in NCES CCD: 2,312. Schools loaded to MongoDB: 2,312. ✓"
- "Schools with CRDC data joined: 2,198 of 2,312 (95.1%). 114 schools missing CRDC data. Reasons: 87 are new schools opened after 2021-22 CRDC collection year. 19 are alternative/online programs not in CRDC scope. 8 have NCES ID mismatches — logged in `join_failures.csv` for review."
- If join rate drops below 90%: "⚠️ JOIN RATE BELOW THRESHOLD. Only 84% of schools matched CRDC data. This indicates a systemic problem — likely an ID format mismatch, not individual school issues. DO NOT PROCEED. Investigate."

*Golden school field-by-field check — is Fairhaven right?*
- "Fairhaven Middle School (NCES ID: 530327003456)"
  - "Enrollment: Source 587, MongoDB 587 ✓"
  - "FRL %: Source 48.2%, MongoDB 0.482 ✓ (stored as decimal)"
  - "Total suspensions: Source 23, MongoDB 23 ✓"
  - "Counselor FTE: Source 2.0, MongoDB 2.0 ✓"
  - "Chronic absenteeism: Source 24.1%, MongoDB 0.241 ✓"
- Any mismatch is a hard stop with explanation.

*Suppression integrity check — is missing data handled right?*
- "Total suppressed cells across all WA schools: 18,442 (7.3% of all data cells)"
- "Verified: 0 suppressed values stored as zero ✓"
- "Verified: 0 suppressed values stored as empty string ✓"
- "Verified: all 18,442 stored as null with `suppressed: true` flag ✓"
- "Spot check: School [name] has null/suppressed for discipline_by_race fields — school enrollment is 47 students, consistent with small-n suppression ✓"

*Type consistency check — are numbers actually numbers?*
- "All enrollment fields: integer ✓ (no floats, no strings)"
- "All percentage fields: float between 0.0 and 1.0 ✓ (no mixed scales)"
- "All NCES IDs: 12-character string ✓ (no truncated IDs, no numeric conversion)"
- If a check fails: "⚠️ 14 schools have FRL percentage stored as 48.2 instead of 0.482. Inconsistent scale. Source file uses whole numbers. Cleaning rule needs to divide by 100."

*Duplicate check — is every school unique?*
- "Unique NCES IDs in MongoDB: 2,312. Total documents: 2,312. No duplicates. ✓"

*The three numbers that matter most:*
- "Schools loaded: 2,312 / 2,312 (100%)"
- "CRDC join rate: 2,198 / 2,312 (95.1%) — above 95% threshold ✓"
- "Fairhaven fields verified: 5 / 5 (100%)"

If all three are green, proceed. If any is red, stop and fix.

**Your review (~30 minutes):**

Read the verification receipt. If it's green, you're done. Check the join failure file if you're curious why 114 schools didn't match CRDC — the reasons should make sense (new schools, alternative programs). If anything is red, the agent has already told you what went wrong and what it thinks the fix is.

**If the agent can't fix a problem itself:** The receipt says so explicitly. "Unable to resolve: 8 schools have NCES IDs in CCD that don't match any CRDC COMBOKEY. Possible causes: NCES ID reassignment, district reorganization, data entry error in CRDC. Recommend: manual lookup of these 8 schools or exclude with documentation." Then you decide.

**Gate:** Testing utility Layer 1 passes. Fairhaven document contains correct values for enrollment, FRL%, suspension rate, proficiency, and counselor count. Pipeline log shows < 5% join failures with explanations for each.

**Output:** MongoDB Atlas collection with ~2,300 WA school documents containing clean, joined, properly typed data from all sources. Ready for Phase 3 (comparison engine).

---

## Phase 3: Comparison Engine — Percentiles, Peers, and Flags

**What:** A script that runs after data loading and computes all derived fields: percentiles, peer group assignments, the demographic-adjusted regression, and flag colors. These get written back into each school's document.

**Computations:**

*Percentiles.* For every numeric metric, calculate where the school ranks within: (a) its district, (b) Washington state, (c) schools with similar demographics. Store as percentile values (0-100) alongside the raw numbers.

*Peer group assignment.* Each school gets assigned to a peer cohort based on: Title I status, enrollment band (small/medium/large), locale (city/suburb/town/rural), and FRL percentage band. A rural Title I school with 200 students is compared to similar schools, not to suburban Bellevue.

*Demographic-adjusted performance regression.* This is the key innovation and it's genuinely simple:

```python
from sklearn.linear_model import LinearRegression

# X = FRL percentage for each school
# y = proficiency score (math + ELA composite or whatever OSPI publishes)
model = LinearRegression().fit(X, y)

# For each school:
predicted = model.predict(school_frl)
residual = actual_score - predicted
# residual > threshold = outperforming (green)
# residual < -threshold = underperforming (red)
# else = performing as expected (yellow)
```

**Decision: state-specific regression, not national.** State tests differ in difficulty, cut scores, and reporting. A WA proficiency rate can't be compared to a Texas proficiency rate. Run the regression within WA only. When we go national, run one per state.

**Decision: threshold for green/red flags.** Needs to be meaningful but not hair-trigger. Starting point: ±1 standard deviation of residuals. Schools more than 1 SD above predicted = green. More than 1 SD below = red. This means roughly 15% of schools get green, 15% get red, 70% get yellow. Adjust after reviewing output — this is where advisory reviewers help.

*Climate/equity flags.* Apply thresholds from the foundation document:
- Discipline disparity ratio > 2.0 = yellow, > 3.0 = red
- Counselor ratio > 1:400 = yellow, > 1:500 = red
- Chronic absenteeism > 20% = yellow, > 30% = red

*Flag metadata.* Every flag stored with: raw value, threshold, threshold source (citation), what it might mean, what it might not mean, suggested question for parent. This metadata is structured data, not AI-generated — it's the same for every school that trips the same flag. The AI narrative layer uses this metadata but doesn't invent it.

**Output:** Every school document now contains computed percentiles, peer group assignment, regression residual, and flag colors with metadata.

**Gate:** Fairhaven's flags make sense. Green on demographic-adjusted performance (high scores + high FRL = outperforming). Check 5-10 other schools across the spectrum for sanity.

---

## Phase 4: AI Layer — Haiku Context Enrichment

**What:** For each school, Haiku searches for contextual signals (news, recognition, DonorsChoose, investigations) and returns structured findings that get stored in the school document.

**This is the most AI-intensive phase and where costs accumulate.** Each school gets one Haiku call (or a small batch). For WA's ~2,300 schools, this is the big batch job.

**Prompt design matters here.** The Haiku prompt needs to:
- Search for the specific school and district by name + city + state
- Look for both risk signals (investigations, lawsuits, leadership turnover, OCR complaints) and strength signals (awards, grants, programs, DonorsChoose)
- Return structured JSON, not prose
- Include confidence scores for each finding
- Cite sources

**Decision: prompt versioning.** Store the prompt template with a version number. Every school document records which prompt version generated its context findings. When we improve the prompt, we can regenerate selectively or in batch, and we know which briefings are current.

**Decision: Haiku, not Sonnet, for this phase.** This is pattern-matching and information retrieval, not nuanced narrative. Haiku is 10-20x cheaper and fast enough. Sonnet is reserved for the narrative generation (Phase 5).

**Decision: web search integration.** Haiku calls need web search enabled to find local news and reputation signals. This is where the Claude API's tool use matters — the prompt instructs Haiku to search for "[school name] [district] [city]" and look for specific categories of information.

**Validation pass.** After Haiku returns findings for a school, a second Haiku call (different prompt) reviews the findings as an LLM-as-judge: Are sources credible? Is the school name correct (not a similarly-named school in another state)? Are claims supported by the cited sources? Returns a cleaned set with confidence scores.

**Output:** Each school document now contains AI-sourced contextual findings (news, reputation, strengths) with confidence scores and source citations.

**Gate:** Fairhaven's context findings include the Bellingham district assault case, the criminal charges against administrators, and any recognition/strengths. No hallucinated incidents. Sources check out.

---

## Phase 5: AI Layer — Sonnet Narrative Generation

**What:** For each school, Sonnet generates the parent-facing briefing narrative using the structured data and context already in the document.

**This is not a creative writing exercise.** Sonnet receives:
- All raw data fields
- All computed percentiles and flags with metadata
- All Haiku context findings with confidence scores
- A detailed system prompt defining tone, structure, caveat language, and the 12-section briefing format

And returns: a structured briefing in the 12-section format defined in the foundation document.

**Prompt design is the product.** This prompt is the single most important artifact we build. It defines:
- Tone: trustworthy, not alarmist. Honest, not overwhelming.
- Language discipline: "stands out" not "warning." "Differs from peers" not "failing." "Worth asking about" not "red flag." CRDC counts are reported data, not findings of wrongdoing.
- Legal awareness: consider whether competing legal mandates (IDEA, Section 504, due process) may constrain school options before implying negligence.
- What's Missing: explicit disclosure of every unavailable, suppressed, or outdated data point.
- Balance: strengths and concerns presented together. A school with discipline disparities AND PBIS implementation tells a richer story than either alone.
- Caveat language on restraint/seclusion: lower confidence, explicit GAO quality findings disclosed.

**Decision: cache the full briefing text in the document.** The generated briefing is stored as a field in the school document. At lookup time, no AI call happens — the app just reads and renders the cached briefing. AI only re-fires on data refresh or new parent field reports.

**Decision: Batch API for bulk generation.** Claude's Batch API offers 50% discount for non-time-sensitive workloads. Generating 2,300 briefings overnight is the definition of non-time-sensitive. Estimated cost: ~$115-184 at full price, ~$58-92 via Batch API.

**Decision: prompt caching.** The system prompt (tone, structure, language rules) is identical across all 2,300 calls. Claude's prompt caching charges 90% less for repeated system prompts. Combined with Batch API, per-briefing cost drops substantially.

**Output:** Every school document now contains a complete, cached briefing narrative ready to display.

**Gate:** Read 10 briefings cover to cover. Do they sound like what we designed? Are flags explained, not just listed? Are caveats present? Does the tone feel trustworthy? Does Fairhaven's briefing match the prototype we wrote by hand?

---

## Phase 6A: Design

**What:** The frontend's design phase. Information architecture, content model, parent-facing language framework, visual identity direction, and a register of methodology-derived display decisions.

**Why split out:** After Phase 3R the project has 17 similarity variables, three subjects of academic flag, a cohort denominator rule that produces three classes of insufficient data, and a descriptive-only/excluded-school treatment with five reason codes. The original Phase 6 framing assumed the frontend was a mechanical wrap-up of narrative rendering; the methodology now requires design decisions that the original phase did not anticipate.

**Dependencies:** Phase 3R methodology brief complete. Reviewer feedback not required.

---

## Phase 6B: Mockup

**What:** High-fidelity rendering of two reference school briefings end-to-end against Phase 6A. Mockup format is builder's choice (Figma, HTML/CSS, polished doc). Not committed code in the build platform.

**Why a mockup phase:** Forces decisions the design phase can leave ambiguous. Surfaces what is broken, what reads as jargon, what is missing, before code commits to a structure that becomes expensive to change.

**Dependencies:** Phase 6A complete.

---

## Phase 6C: Build

**What:** Streamlit implementation that turns the Phase 6B mockup into a working frontend across all 2,532 Washington schools, deployed to beta.schooldaylight.com as a soft launch.

**Why deferred:** Cannot start until 6A and 6B are complete.

**Implementation:**

*Search.* Fuzzy text search on school name, city, and district. MongoDB Atlas Search index.

*Display.* Briefing structure rendered per Phase 6A content model and Phase 6B mockup. Streamlit components chosen to match the mockup.

*Soft-launch deployment.* Tool deployed to beta.schooldaylight.com. Hosting platform decided in implementation (Streamlit Community Cloud paid tier, Railway, Render, or Cloudflare-fronted alternative). The root domain schooldaylight.com is not configured to point at the tool during soft launch. Soft-launch deployment is not indexed by search engines (robots.txt, no canonical link tags pointing at the root domain) until public launch.

*Public-launch transition.* Phase 6C produces a tool whose soft-to-public transition is a single configuration flip rather than a content rewrite or infrastructure migration. Active language version (soft-launch or public-launch) controlled by a configuration variable. Both versions built and in place.

*Carried over from original Phase 6.* No authentication, mobile responsive, source-available repo from day one (PolyForm Noncommercial 1.0.0 for code; CC BY-NC 4.0 for documentation, methodology, and data interpretation). Commercial use requires permission. Updated from the original Phase 6, which used MIT plus CC BY 4.0.

*Methodology disclosure page.* New work the original Phase 6 did not anticipate. Drawn from Phase 6A's parent-facing language framework. Soft-launch and public-launch versions both built; active version controlled by the same configuration variable.

*License setup.* LICENSE at repo root containing the full PolyForm Noncommercial 1.0.0 license text from https://polyformproject.org/licenses/noncommercial/1.0.0/; LICENSE-DOCS at repo root containing the full CC BY-NC 4.0 license text from https://creativecommons.org/licenses/by-nc/4.0/legalcode.en; README section explaining the split licensing structure in human-readable terms with a commercial-licensing contact path; methodology disclosure page note on how the methodology is licensed (one sentence).

**Dependencies:** Phase 6A complete, Phase 6B complete. Methodology reviewer feedback received and reconciled before public-launch flip, but not required for soft-launch deployment.

---

## Phase 7: Testing Utility (Parallel Track)

See separate document: **School Daylight Testing Utility Spec**.

The testing utility runs at every phase and is the quality gate before anything goes live. It is not an afterthought — it's built alongside the pipeline and catches the mistakes that make civic tools lose credibility.

---

## Phase 8: Iterate and Harden (Post-Launch)

**What comes after WA launch:**

- Collect feedback from real parents using the tool
- Refine Sonnet prompt based on briefings that don't read well
- Add DonorsChoose API integration (real-time, enriches strength signals)
- Add school board meeting dates (scrape or manual for WA districts)
- Monitor for new CRDC release (2023-24 expected late 2025) — when it drops, re-run pipeline
- Begin scoping Phase 2 states (which state data portals are accessible, which have compelling stories)
- Design parent field report submission (Phase 1 launches without this)

---

## Dependencies and Environment

**What Claude Code needs to have available:**

- Python 3.10+
- `pandas`, `pymongo`, `scikit-learn`, `streamlit`
- `anthropic` Python SDK (for Claude API calls in Phases 4-5)
- MongoDB Atlas account (free tier, M0 cluster)
- Anthropic API key with access to Haiku and Sonnet
- GitHub account (for Streamlit deployment)

**What the builder needs to provide:**

- MongoDB Atlas connection string (create account, create free cluster, get connection string — Claude Code can walk through this)
- Anthropic API key (from console.anthropic.com)
- Downloaded source files in `/states/WA/raw/`
- Decision-making on any design questions the agent escalates
- A dev friend available for deployment and DevOps questions (getting the app live with a domain, SSL, CI/CD — the one area where Claude Code is less reliable)

---

## Estimated Timeline

This is not a startup sprint. This is one person building between parenting, law school, consulting, and life. Most of the execution is done by Claude Code agents — the builder's role is downloading files, making design decisions, and reviewing output.

| Phase | Your Time | Agent Time | Depends On |
|-------|-----------|------------|------------|
| Phase 0: Download files | ~1 hour | — | Nothing |
| Phase 1: Data dictionary + exploration | ~1-2 hours (review) | 1 Claude Code session | Phase 0 |
| Phase 2: ETL pipeline + MongoDB | ~30 min (review) | 1-2 Claude Code sessions | Phase 1 |
| Phase 3: Comparison engine | ~30 min (review) | 1 Claude Code session | Phase 2 |
| Phase 4: Haiku enrichment | ~1 hour (review) | 1-2 Claude Code sessions + batch run | Phase 2 |
| Phase 5: Sonnet narratives | ~2-3 hours (prompt iteration + reading briefings) | 1-2 Claude Code sessions + batch run | Phases 3 + 4 |
| Phase 6A: Frontend design | — | — | Phase 5, Phase 3R brief |
| Phase 6B: Frontend mockup | — | — | Phase 6A |
| Phase 6C: Frontend build + soft launch | — | — | Phase 6A, 6B |
| Phase 7: Testing | Continuous from Phase 1 onward | Built into each phase | Each phase |

**Total human time: roughly 8-12 hours** spread over 2-3 weeks. The bulk of that is Phase 5 — reading generated briefings and iterating on the Sonnet prompt until the tone and accuracy are right. That's editorial work, not technical work, and it's the part that matters most.

The longest calendar-time items are the Haiku and Sonnet batch runs (Phases 4-5), which run overnight. The pipeline itself can be built and loaded in a day. The narrative quality is what takes iteration.

### Scaling to 50 States

Once WA is complete, the state expansion workflow for each additional state:

| Step | Who | Time |
|------|-----|------|
| Find and download state data files + documentation | You | 15-20 min |
| Agent builds state mapping YAML using WA as template | Claude Code | 30-45 min |
| Review mapping, check low-confidence items | You | 15-20 min |
| Agent runs pipeline for new state, testing utility validates | Claude Code | 30 min |

**~45 minutes of your time per state.** After building WA + 2-3 additional states by hand as training examples (CA, TX recommended — large, well-documented, different conventions), the agent can handle the mapping work with high confidence. All 50 states in roughly 40 hours of part-time work over a few weeks.

The federal data (CRDC, NCES) is already national. No additional mapping needed — it loaded once. Only state-specific report card data requires per-state harmonization, and that's exactly the part the agent handles well given examples.

---

*This document is the build plan. It pairs with: the Foundation Document (what and why), the Data Dictionary (field-level blueprint), and the Testing Utility Spec (how we know it's right).*
