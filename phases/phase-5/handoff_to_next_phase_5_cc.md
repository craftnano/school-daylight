# Phase 5 Handoff — to next Claude Code instance

**Date written:** 2026-05-02 (evening)
**Written for:** the next Claude Code session, opening this project tomorrow without conversation context from today.
**Phase 5 status:** RE-OPENED pending Stage 2 v4 work. Production output is shipped and stable; the editorial layer needs five more rule revisions before Phase 5 closes.

You will not have the conversation history from 2026-05-02. Read this document, then the canonical artifacts it references (build log, audit, receipt). Do not re-litigate decisions captured here. Do not re-run the production batch.

---

## 1. Phase 5 status summary

**Current state:** RE-OPENED pending Stage 2 v4 work. Phase 5 was previously declared closed on 2026-05-02 morning after full WA-state coverage was achieved; it was re-opened that afternoon when the editorial-rule audit surfaced four must-fix items, and one additional editorial decision (OCR-trans-policy coordinated-investigation framing) was made the same day. Five items now block Phase 5 close.

**Final coverage in MongoDB (verified end of day 2026-05-02):**

| Bucket | Count |
|---|---:|
| Total schools | 2,532 |
| `layer3_narrative.status = ok` (full Sonnet narratives with citations) | **1,885** |
| — Of those, regenerated 2026-05-02 under Stage 1 v2 | 185 (with `stage1_prompt_version = layer3_v2`, `regenerated_2026_05_02 = true`) |
| — Of those, original Stage 1 v1 batch (unchanged) | 1,700 (no `stage1_prompt_version` field — implicit v1) |
| `status = stage1_filtered_to_zero` (canonical fallback text) | 415 |
| `status = no_findings` (canonical fallback text) | 232 |
| Schools without `layer3_narrative` field | 0 |

**Note on the 187-vs-185 split:** the affected pool re-derived from a full-population scan was 187 schools; 185 succeeded under Stage 1 v2 + Stage 2 v3; 2 schools had Stage 1 v2 zero-include (their only positive content was collateral-dropped at Stage 0 by the conduct-date or dismissed-case rule, which v2 doesn't change) and retain their prior production state in MongoDB.

**Total Phase 5 spend to date: ~$36.24.** Hard cap is $50; **~$13.76 headroom remains.** Composition:

| Phase | What | Cost |
|---|---|---:|
| Phase A initial | Stage 0 + Stage 1 Haiku across 2,427 schools (corrected $1/$5 Haiku 4.5 pricing) | $19.15 |
| Phase A resume | Stage 0 + Stage 1 Haiku across the remaining 105 schools | $0.71 |
| Dry runs v1–v5 | Sonnet 4.6 batches on 70 distinct schools (5+5+50+8+2) | $0.46 |
| Full Stage 2 batch | Sonnet 4.6 batch on 1,792 schools, prompt v3 | $12.69 |
| Final Stage 2 batch | Sonnet 4.6 batch on 68 newly-queued schools after Phase A resume | $0.47 |
| Positive-content diagnostic | full population scan, no API spend | $0 |
| 10-school v2 test | Stage 1 v2 + Stage 2 v3 random sample | $0.16 |
| Stage 1 v2 regeneration | 185 schools across affected pool | $2.60 |
| Discipline / legal-context diagnostic | 261 narratives scanned; 10-narrative sample | $0 |
| **Total** | | **~$36.24** |

---

## 2. What was completed today (2026-05-02)

This is what the conversation context from 2026-05-02 actually delivered. Use this section to orient before reading the latest build_log.md entries (which are denser and chronological).

### 2a. Positive-content diagnostic and Stage 1 line-37 retirement

A full-population scan of the 2,532-school MongoDB collection found 185 schools with positive-content vocabulary (Washington Achievement Award, Blue Ribbon, Schools of Distinction, dual-language program designations, Teacher of the Year, FIRST robotics, Title I Distinguished, etc.) in their raw Phase 4 findings. Of those 185, **only 1 had positive content in its final layer3_narrative** — the other 184 had been filtered out almost entirely by a single Stage 1 prompt rule on `prompts/layer3_stage1_haiku_triage_v1.txt:37`:

> "Awards, recognitions, and positive achievements: exclude unless directly relevant to an adverse finding (e.g., an award that was later revoked, a program cited in a lawsuit)."

The rule directly contradicted foundation.md's Principle 3 ("Recognize real achievement and surface real concerns. Showcase gains that current ratings miss, especially where educators outperform demographic expectations"). It was retired permanently after a 10-school dry-run-v2 test confirmed v2 produced acceptable mixed adverse/positive narratives.

Diagnostic at `phases/phase-5/positive_content_diagnostic.md`. 10-school test at `phases/phase-5/positive_content_test_v1.md`. Builder approved scaling to the full 184-school affected pool.

### 2b. Stage 1 v2 promoted to canonical, v1 preserved as historical

`prompts/layer3_stage1_haiku_triage_v2.txt` is now the canonical Stage 1 prompt. v1 is preserved in `prompts/layer3_stage1_haiku_triage_v1.txt` as the historical record of what produced the original 1,700-school production batch.

`pipeline/layer3_prompts.py` updated:
- `STAGE1_FILE` constant now points to v2.
- `load_stage1()` returns v2 by default.
- `load_stage1_v1()` added for historical reproduction.
- `load_stage1_v2()` retained as alias (functionally identical to `load_stage1()` now).

The line-37 v1 categorical exclusion of "awards, recognitions, and positive achievements" is **retired permanently**. The new POSITIVE FINDINGS block in v2 reads: "Awards, recognitions, formal program designations, civil-rights or equity recognitions, sustained measurable improvements, and positive achievements: INCLUDE when they meet the recency rules above and have high source confidence." Routine leadership appointments / board governance / policy announcements remain excluded as noise.

### 2c. 185-school regeneration under Stage 1 v2

`pipeline/19_layer3_stage2_v3_batch.py` was supplemented by `phases/phase-5/regenerate_184_with_stage1_v2.py`. The script re-derived the affected pool (187 schools), ran Stage 1 v2 + Stage 2 v3 unchanged, and wrote the new narratives to MongoDB with the version-tracking fields described above. 185/187 succeeded. 0 errors. 93 of the 185 regenerated narratives now contain positive content directly; 92 had positive findings in raw Phase 4 but Stage 1 v2 still excluded them under the symmetric recency rules. Cost: $2.60.

The 92-narrative residual is the entry point to **audit Asymmetry A1 (positive-content recency calibration)** — the Stage 2 v4 must-fix item below.

### 2d. Editorial rule audit produced

`docs/rule_audit_2026_05.md`. Inventoried 39 active editorial rules across the three Stage prompts (Stage 0, Stage 1 v2, Stage 2 v3). Confirmed 39 IMPLEMENTS / 0 ORPHANED / 0 CONTRADICTS after the line-37 retirement removed the only documented direct contradiction.

Found four calibration asymmetries (A1–A4), three redundancies (D1–D3), five implicit dependencies (E1–E5), and eight coverage gaps (most out-of-Layer-3-scope; in-scope ones become must-fix items below).

### 2e. Legal-context (IDEA / 504 / FAPE) diagnostic — resolved, no rule needed

The audit's Coverage Gap 4 hypothesis was that Stage 2 needed an explicit rule directing Sonnet to layer in IDEA / 504 / FAPE / due-process framing on discipline findings, per a foundation.md commitment. **Diagnostic across 261 status=ok narratives matching disability/restraint/seclusion/special-ed/IEP/Section 504/FAPE/IDEA/due-process keywords (`phases/phase-5/discipline_legal_context_sample.md`) found that source language already carries the relevant legal context for substantive disability-rights enforcement findings.** DOJ settlements, state AG investigation findings, OCR resolutions describe violations using legal terminology that anchors the framework directly (e.g., "inappropriately and repeatedly secluded and restrained students with disabilities outside of emergency situations as required by law").

**Decision: no IDEA/504/FAPE legal-context rule added to Stage 2.**

**Foundation.md was updated TODAY** (2026-05-02). Section "Interpreting Discipline and Safety Data: Legal Constraints as Context" — the "Design implication" paragraph was rewritten to reflect that source language carries legal context implicitly and the platform reports findings using the source's legal characterization rather than imposing structural framing. A timestamped revision note marks the 2026-05-02 update. The Bellingham bus-assault illustrative example is preserved as motivating context.

`docs/rule_audit_2026_05.md` Coverage Gap 4 and the corresponding Must-fix item #5 are both marked RESOLVED. Build log entry was written.

### 2f. OCR-trans-policy editorial decision — captured in build log today

The U.S. Department of Education's Office for Civil Rights opened Title IX investigations into multiple WA districts (Sultan, Vancouver, Tacoma, Lake Washington, others) in 2025-2026 over policies allowing trans students to compete on sports teams aligned with their gender identity. These are politically-motivated coordinated multi-district enforcement actions, not substantive Title IX accountability findings.

**Decision: investigations stay in narratives with neutral institutional-investigation framing.** Suppressing politically-motivated federal investigations would itself be a political act and would conceal documented public-record information from parents. Neutral reporting serves parents across the values spectrum.

**Stage 2 v4 candidate rule (separate from the decision-to-keep-them-in):** when a source describes the school or district as one of multiple entities subject to a coordinated investigation or enforcement action, narrative should surface coordination context explicitly (e.g., "one of N educational entities subject to this investigation"). Applies to OCR trans-policy investigations and to any future coordinated actions. Captures coordination as structurally relevant context without editorializing on the political character of any specific action.

Build log entry written today. This becomes the **fifth Stage 2 v4 must-fix item** alongside the four from the audit.

---

## 3. Stage 2 v4 work — the immediate next phase

Five items must be addressed before Phase 5 closes. Four come from the editorial rule audit (`docs/rule_audit_2026_05.md`); one comes from today's OCR-trans-policy editorial decision (build log entry).

**Process discipline that applies to every item:** *diagnostic before rule design.* The line-37 retirement and the IDEA/504/FAPE non-decision both followed the same pattern — query data, sample output, then design (or decline to design) the rule. Each must-fix below gets a diagnostic-then-design pass: query the relevant data layer, sample output, decide whether the rule is needed, draft prompt revision if yes, dry-run, builder editorial review, then scale. Do not draft a rule for a hypothesized failure mode without first confirming the failure occurs in production output.

### 3a. Audit Asymmetry A1 — positive-content recency calibration

**Source case.** The 185-school Stage 1 v2 regeneration (today) showed 93 narratives now carry positive content but **92 do not** despite having positive findings in raw Phase 4. Almost all 92 are cases where Stage 1 v2 applied the symmetric 10-year / 5-year recency rules from R008 / R009 to positive findings, excluding things like a 2009 National Blue Ribbon designation under the same window that decays a 2009 administrator-misconduct allegation. Haiku v2 demonstrated emergent stretching during the dry-run with rationales like "exceeds 10-year recency window but represents sustained measurable quality indicator" — Haiku is correctly identifying an asymmetry the rules don't formalize.

**What stage the rule lives in.** Stage 1 v3 (this is a triage rule, not a writing rule). Stage 2 doesn't need to change for A1.

**Expected scope of regeneration impact.** ~92 schools (the residual from today's 185-school regen). Diagnostic should confirm — the 92 number is from the auto-regex check that may have false positives (Sonnet rephrasing positive content past the keyword scan). The actual regeneration count after rule revision could be lower or higher.

### 3b. Audit Coverage Gap 2 — non-traditional school narrative framing

**Source case.** The harm register Phase 5 entry "Non-traditional school narrative framing" calls for Stage 2 to branch on `school_type` for juvenile detention, homeschool partnerships, virtual schools, and alternative programs. The dry-run v2 Echo Glen narrative (juvenile detention) was flagged in the build log as exhibiting this gap — applying standard narrative framing to a juvenile detention facility is misleading.

**What stage the rule lives in.** Most likely Stage 2 v4 (a new writing rule with school-type branching). Possibly also Stage 1 if certain finding categories should be filtered differently for non-traditional schools, but I'd default to Stage 2 to keep Stage 1's "factual pass-through" load-bearing simplicity.

**Expected scope of regeneration impact.** Up to ~520 schools nominally affected (auto-excluded from regression by school_type: 341 Alternative + 82 Special Education + 20 Career and Technical, plus 78 manual exclusions in `school_exclusions.yaml`). Many are status=stage1_filtered_to_zero or no_findings already and won't change under regeneration. The actual narrative-regeneration count is smaller — **a diagnostic must run first** to count schools with `school_type ≠ "Regular School"` AND `layer3_narrative.status = ok`. That subset is the one whose narratives change.

### 3c. Audit Coverage Gap 1 — three-layer trust model disclaimer

**Source case.** The harm register Phase 5 entry "Three-layer trust model" specifies Layer 3 (web-sourced findings) must be clearly labeled with an LLM/web disclaimer. The current Stage 2 prompt produces per-paragraph citations (Rule 38 in the audit) but no structural disclaimer that says "this section is AI-generated narrative based on web search of public records." There is no rule that produces or enforces a section-level disclaimer.

**What stage the rule lives in.** This is partially a Stage 2 question (if the disclaimer is rendered into the narrative text) and partially a frontend question (if the disclaimer is rendered around the narrative section as part of the briefing layout). The decision belongs to the builder; the next CC should not assume one or the other without explicit direction.

**Expected scope of regeneration impact.** **All 1,885 status=ok narratives if the disclaimer is rendered into the narrative text.** Zero regeneration if rendered at the frontend layer. This is the largest-blast-radius item of the five and worth deciding the rendering layer before any rule drafting.

### 3d. Audit Asymmetry A2 — organizational name handling

**Source case.** Stage 2 Rule 2 (R026) forbids individual names. Nothing in the prompt covers organizational complainants. The Inglewood Middle School narrative (in the v3 production batch) genericized "StandWithUs" to "a nonprofit legal team" while the Juanita HS narrative (also v3) preserved "StandWithUs" by name. Behavior is inconsistent across narratives. Same treatment question applies to "Council on American–Islamic Relations," advocacy organizations, named law firms representing plaintiffs, etc.

**What stage the rule lives in.** Stage 2 v4 (a redaction rule alongside Rule 2 / Rule 3 / Rule 9).

**Expected scope of regeneration impact.** Probably <50 schools. **Diagnostic must run first** — query `layer3_narrative.text` for occurrences of common advocacy-organization names (StandWithUs, ACLU, Lambda Legal, etc.) and law firm names already known to appear in findings. The diagnostic count tells you whether the regeneration is worth its API spend.

### 3e. OCR-coordinated-investigation framing (from today's editorial decision)

**Source case.** Build log entry "2026-05-02 — Editorial decision: OCR investigations into trans-athlete policies remain in narratives." The decision-to-keep-them-in does not need a rule; the **coordination-context surfacing** does. When source describes the school or district as one of N entities subject to a coordinated action, narrative should explicitly surface that coordination ("one of N educational entities subject to this investigation"). Applies beyond OCR trans-policy actions to any coordinated multi-entity investigation or enforcement.

**What stage the rule lives in.** Stage 2 v4 (a writing rule about coordination context, alongside Rule 7 attribution).

**Expected scope of regeneration impact.** **Diagnostic must run first** — count districts whose Stage 1 included findings already mention "one of [number]" or coordinated-action language. The 18-school OCR Title IX investigations from January 2026 affected at least 4 WA districts (Sultan, Vancouver, Tacoma, Lake Washington) per the build log entry; the actual regeneration count depends on how many narratives across those districts surface the investigation finding and how many already render the coordination context implicitly.

### Audit "should-fix" items tractable in the same Stage 2 v4 pass

The audit lists five should-fix items (A3 / A4 / E3 / E4 / E5 plus restraint-seclusion caveat language and closed evaluative-language list expansion). These can ride along with the must-fix work without needing separate diagnostics:

- **Death-suppression scope tiering or documentation** (audit A3). Rule 4 (R028) imperative-suppresses manner / location / physical circumstances of student deaths only. Analogous physical-harm details (eye injury, restraint injury, medical event short of death) get only general redaction. Decide: tier the suppression, or document the exception.
- **Restraint/seclusion caveat language** (audit Coverage Gap 6). Foundation Risk 3 says these findings need extra caveat language and lower confidence presentation. No Stage 2 rule covers this. The 2,247 schools with `safety.restraint_seclusion` data ingested are not directly affected (the data isn't in narrative anyway), but where a finding mentions restraint or seclusion in source text, Sonnet currently has no rule directing extra caveat framing.
- **Closed evaluative-language list expansion** (audit A4). Rule 6 (R030) bans four words: controversial, divisive, progressive, conservative. Adjacent terms (contentious, polarizing, woke, anti-woke, radical, extreme) are not enforced.
- **Implicit dependency documentation** (audit E3, E4, E5). Stage 2 prompt header should document: (E3) R036 grade-level redaction acts on Stage 1's preserved `original_text` and downstream consumers must not render that field to parents; (E4) R038 citations depend on `source_url` injection happening outside the prompt at Stage 2 build time; (E5) R028 death suppression depends on Phase 4 enrichment having pre-excluded no-institutional-response deaths.

Group these with the must-fix work to avoid running multiple regeneration cycles.

---

## 4. Architectural commitments — DO NOT re-litigate these

These are load-bearing project commitments. Treat them as fixed. **Do not propose changes without explicit builder approval.**

1. **Three-stage pipeline is load-bearing.** Stage 0 is Haiku structured extraction followed by Python rule application (conduct-date anchor + dismissed-case rule). Stage 1 is Haiku editorial triage. Stage 2 is Sonnet 4.6 narrative writing. **Stage 0's code pre-filter is non-negotiable** — the conduct-date anchor and dismissed-case rules failed when expressed in prompts (Sonnet 4.5, Sonnet 4.6, and Haiku 4.5 all interpreted SEVERITY EXCEPTION as overriding CONDUCT-DATE ANCHOR for ancient sexual-abuse conduct). Do not propose collapsing Stage 0 back into a prompt.

2. **Stage 1's "factual pass-through only" rule is load-bearing.** Stage 1 outputs `original_text` unchanged (R023). Do not expand Stage 1's scope into rewriting work. Redaction belongs in Stage 2 (e.g., grade-level redaction R036 acts at Stage 2 even though the source text contains the grade-level language).

3. **Per-paragraph citation format is fixed.** `[Sources: URL1; URL2; URL3]` plain text at the end of each paragraph; semicolon-separated; "(one source unavailable)" fallback when source_url is missing. No markdown link formatting. No numbered footnotes. No inline citation markers within sentences. The citation block is structurally part of the narrative output stored in `layer3_narrative.text`.

4. **Dual-context district propagation is fixed.** Pass 1 (Phase 4 enrichment) writes `district_context` to every school in the district via `db.schools.update_many({"district.name": ...}, {"$set": {"district_context": ...}})` at `pipeline/17_haiku_enrichment.py:632-635`. Pass 2 writes per-school `context`. Stage 2 reads both via `pipeline/layer3_findings.get_findings_for_stage0()` which dedups by composite key `(source_url, date, category)` with district-context winning on cross-context collision. **Do not duplicate findings into separate MongoDB records.** Do not add a `_source_layer` tag to findings (the existing dedup logic infers attribution from finding text per Stage 2 Rule 7).

5. **Pipeline as authorship process.** Editorial framing changes happen through prompt revisions and regeneration, not through manual MongoDB edits to specific narratives. If a narrative needs different framing, the path is: (a) revise the prompt, (b) dry-run on a small sample, (c) builder editorial review, (d) regenerate the affected school cohort. **Do not edit `layer3_narrative.text` directly in MongoDB.** This commitment is what makes the auditability promise in foundation.md ("Default to transparency... a parent, journalist, or researcher can trace any number in any briefing back to a source row") hold.

6. **Stage 1 v2 with positive-content inclusion is canonical.** The line-37 categorical exclusion ("Awards, recognitions, and positive achievements: exclude unless directly relevant to an adverse finding") was retired permanently 2026-05-02. **Do not re-add it.** The retirement was supported by a 185-school full-population diagnostic and a 10-school dry-run editorial review. Routine leadership appointments / board governance / policy announcements remain excluded — they are noise, not achievement. Awards / recognitions / formal program designations / civil-rights or equity recognitions / sustained measurable improvements pass through Stage 1.

7. **Editorial rule retirement is reversible only with explicit builder approval AND a documented diagnostic equivalent to the line-37 retirement.** The standard is: full-population scan, 10-school dry-run review, builder editorial sign-off. This guards against future agents quietly re-adding categorical exclusions or analogous rules without the diagnostic discipline. If you find yourself reasoning "well this rule should obviously include / exclude X," stop. Run the diagnostic. Sample the output. Then design.

---

## 5. Documentation work also pending

These items were started or partially completed today and need to be checked / completed by the next CC.

1. **Build log entries.** Today's build_log.md should already contain:
   - The positive-content rule retirement entry (definitely written).
   - The audit / Coverage Gap 4 resolution entry (definitely written).
   - The OCR-trans-policy editorial decision entry (written today as a prerequisite to this handoff — verify it's there before writing Stage 2 v4 entries).
   
   Read the latest entries to confirm. If anything is missing from the day's work, complete it before Stage 2 v4 work begins.

2. **`docs/foundation.md` IDEA/504/FAPE update is COMPLETED.** Section "Interpreting Discipline and Safety Data: Legal Constraints as Context" was rewritten 2026-05-02 with a timestamped revision note. **Do not re-edit this section.** The original "the prompt instructs the AI to consider competing legal mandates" wording has been replaced with "Findings involving disability-rights enforcement typically surface through source language that carries legal context implicitly. The platform reports these findings using the source's legal characterization. No additional structural framing required at the narrative level." The Bellingham bus-assault illustrative example is preserved.

3. **`docs/build_sequence.md` state needs assessment.** The original v0.1 build plan was written before the Phase 4.5 architecture pivot, before Phase 5 production, and before the Stage 1 v2 / Stage 2 v3 prompt revisions. The next CC should read it and determine whether it is fully superseded by the current build_log + receipts + audit + handoff stack, or whether parts remain load-bearing as planning anchors. **Do not modify it without that assessment.** A full retirement marker ("SUPERSEDED 2026-05-02 — see build_log.md") may be the right move; or selective annotation may be better.

4. **`docs/roadmap.md` does not currently exist — create new file.** Three sections recommended:
   - **Where We Are.** Current Phase 5 status, coverage numbers, pending Stage 2 v4 work.
   - **Path to Launch.** Phase 3R (formalize comparison engine spec — first artifact at `phases/phase-3R/data_element_inventory.md` already exists), Layer 2 narrative design (regression-flag interpretation), frontend / Streamlit app, statistical-methodology external review, license decision (the harm register pre-launch entry on derivative-works restrictions), launch.
   - **Post-Launch Features.** Notable alumni feature, parent field reports / corroboration system, expansion to additional WA-state data sources, expansion to other states, "schools in this district" cross-link, mobile responsive frontend.
   
   Roadmap should be a living document; first version captures the current state and known sequencing.

---

## 6. Process discipline carried forward

Habits that have served the project well and should be preserved.

1. **Diagnostics before rules.** Query data, sample output, then design the rule (or decide it isn't needed). The line-37 retirement and the IDEA/504/FAPE non-decision both followed this pattern. The OCR-trans-policy decision required a foundational editorial choice but the *rule* (coordination-context surfacing) still needs a diagnostic before drafting.

2. **Validation samples vs. discovery samples serve different purposes.** A validation sample (e.g., 50-school three-stage replay against cached output) confirms a known property of an existing pipeline. A discovery sample (e.g., 10-school dry-run on a new prompt revision) is exploratory — looking for failure modes the auto-checks won't catch. Both are required at major phase transitions. Don't substitute one for the other.

3. **Editorial gates must be enforced explicitly, not assumed.** The original Phase A run launched without builder editorial review of the 5-school dry-run-v1 narratives. The omission was caught downstream and captured as a process learning in the build log. For every prompt revision: (a) dry-run on the smallest reasonable test set, (b) builder reads the narratives, (c) builder approves before scaling, (d) full batch.

4. **Cost projections from small samples extrapolate poorly across heterogeneous populations.** Use median + p90, not mean. A 5-school sample's mean cost can be 3x off from the actual median across 1,800 schools because of the long-tail of high-output narratives. The 50-school dry-run-v3 produced the right projection method (median $0.0041/school × 1,739 = $7.10; p90 $0.0082 × 1,739 = $14.19); the actual full-batch cost was $12.69, between those two anchors.

5. **Watch the Anthropic console alongside self-reported telemetry during scale runs.** Telemetry can undercount in subtle ways. The Phase A pricing-constants bug (Haiku 3.5 prices $0.80/$4 vs Haiku 4.5 prices $1/$5) underreported Haiku spend by 25% across the full Phase A batch. The bug wasn't caught from telemetry — it was caught from the gap between self-reported $15 and console-reported $39.

6. **When MongoDB schema includes flags like `stage1_prompt_version` or `regenerated_<date>`, set them on every write so future audits can distinguish prompt-version cohorts.** Today's regen run sets these on the 185 affected schools; future runs should follow the pattern. Every Stage 2 v4 regeneration write should set both `stage1_prompt_version` and a `regenerated_<date>` flag to mark the cohort. This makes audits like "show me every narrative still on Stage 1 v1" trivially queryable.

7. **Open data-hygiene question for next CC.** The 1,700 unchanged-from-original-batch narratives currently have no `stage1_prompt_version` field at all (it's implicit v1). Whether to backfill `stage1_prompt_version = layer3_v1` on those 1,700 documents for schema consistency, or leave it implicit, is an open decision. No immediate action required; flag for builder direction when Stage 2 v4 regeneration plans are being scoped.

---

## 7. Key files and their canonical status

| Path | What it is | Current status |
|---|---|---|
| `CLAUDE.md` | Project operating instructions | active — read first every session |
| `docs/foundation.md` | Product specification, mission, architecture, known risks | active; v0.4; revised 2026-05-02 (IDEA/504/FAPE section) |
| `docs/harm_register.md` | Living harm-driven design decisions | active |
| `docs/build_log.md` | Chronological record of decisions and reasoning | active — primary source of truth for "what happened when and why" |
| `docs/build_sequence.md` | Original v0.1 phase plan | **uncertain status** — assess for retirement; see §5 above |
| `docs/rule_audit_2026_05.md` | Phase 5 editorial-rule audit | active reference; Coverage Gap 4 marked RESOLVED |
| `docs/receipts/phase-5/task1_prompt_extraction.md` | Phase 5 Task 1 receipt | historical (Layer 3 prompt extraction) |
| `docs/receipts/phase-5/task2_district_context.md` | Phase 5 Task 2 receipt | historical (district_context propagation) |
| `docs/receipts/phase-5/task3_layer3_production.md` | Phase 5 Task 3 receipt | active — final coverage numbers; updated post-regen |
| `docs/roadmap.md` | Where we are / path to launch / post-launch | **does not exist yet** — create per §5 above |
| `prompts/layer3_stage0_haiku_extraction_v1.txt` | Stage 0 prompt (Haiku extraction) | canonical |
| `prompts/layer3_stage1_haiku_triage_v1.txt` | Stage 1 prompt v1 | **historical** — preserved as record of original 1,700-narrative batch |
| `prompts/layer3_stage1_haiku_triage_v2.txt` | Stage 1 prompt v2 | **canonical** — line 37 categorical exclusion retired |
| `prompts/layer3_stage2_sonnet_narrative_v1.txt` | Stage 2 prompt v1 | historical (validated 50-school replay) |
| `prompts/layer3_stage2_sonnet_narrative_v2.txt` | Stage 2 prompt v2 | historical (Rules 15/16/17 + citations added) |
| `prompts/layer3_stage2_sonnet_narrative_v3.txt` | Stage 2 prompt v3 | **canonical** — Rule 4 strengthened with manner/location-of-death suppression |
| `prompts/sonnet_layer3_prompt_test_v1.txt` and `_v2.txt` | Pre-pivot single-stage Sonnet prompts | historical (architecture lineage) |
| `prompts/context_enrichment_v1.txt`, `district_enrichment_v1.txt`, `*_validation_v1.txt` | Phase 4 enrichment + validation prompts | active |
| `pipeline/layer3_prompts.py` | Prompt loader | active; `load_stage1()` returns v2 |
| `pipeline/layer3_findings.py` | Dedup query function | active; (source_url, date, category) composite key with district-context priority |
| `pipeline/18_layer3_production.py` | Phase A runner (Stage 0+1) | active; pricing constants corrected to Haiku 4.5 ($1/$5) |
| `pipeline/19_layer3_stage2_v3_batch.py` | Phase B / Stage 2 v3 batch runner | active |
| `phases/phase-5/regenerate_184_with_stage1_v2.py` | Stage 1 v2 regeneration script | one-off; preserved as audit record |
| `phases/phase-5/positive_content_diagnostic.py` and `.md` | Full-population positive-content scan | historical reference |
| `phases/phase-5/positive_content_test_v1.md` | 10-school Stage 1 v2 dry-run results | historical reference |
| `phases/phase-5/discipline_legal_context_sample.md` | 10-narrative IDEA/504/FAPE diagnostic sample | historical reference |
| `phases/phase-5/dry_run_narratives_v1.md` through `_v5.md` | Phase 5 dry-run editorial reviews | historical reference |
| `phases/phase-5/spot_check_sample.md` | 25-school stratified spot-check (builder approved) | historical reference |
| `phases/phase-5/production_run/` | Phase A checkpoint, stage1 results, batch IDs, run logs | preserved for resume / audit |
| `phases/phase-3R/data_element_inventory.md` | Phase 3R formalization — first artifact | active reference |
| `flag_thresholds.yaml` | Phase 3 comparison engine config | active |
| `school_exclusions.yaml` | 78 manually excluded schools (regression eligibility) | active |
| `config.py` | Single source of truth for credentials and paths | active |

---

## 8. Files modified or created today (2026-05-02)

- **`prompts/layer3_stage1_haiku_triage_v2.txt`** — created. New canonical Stage 1 prompt with line-37 retirement and inverted POSITIVE FINDINGS rule.
- **`prompts/layer3_stage1_haiku_triage_v1.txt`** — preserved unchanged (historical). Line 37 contains the retired categorical-exclusion rule for reference.
- **`pipeline/layer3_prompts.py`** — modified. `STAGE1_FILE` now points to v2; `load_stage1()` returns v2; `load_stage1_v1()` added; `load_stage1_v2()` retained as alias.
- **`docs/rule_audit_2026_05.md`** — created. 39-rule inventory + foundation/harm-register alignment + internal-consistency checks + must-fix/should-fix/nice-to-fix prioritization. Coverage Gap 4 and Must-fix #5 marked RESOLVED later in the day.
- **`docs/foundation.md`** — modified. Section "Interpreting Discipline and Safety Data: Legal Constraints as Context" rewritten with 2026-05-02 timestamped revision note.
- **`docs/build_log.md`** — multiple new entries today: positive-content diagnostic, line-37 retirement, Stage 1 v2 promotion, 185-school regeneration, audit production, audit Coverage Gap 4 resolution, OCR-trans-policy editorial decision.
- **`docs/receipts/phase-5/task3_layer3_production.md`** — modified. Headline numbers updated to reflect 1,885 ok / 415 stage1_filtered_to_zero / 232 no_findings post-regen.
- **`phases/phase-5/positive_content_diagnostic.py`** and **`.md`** — created. Full-population scan + report.
- **`phases/phase-5/positive_content_test_v1.py`** and **`.md`** — created. 10-school Stage 1 v2 dry-run.
- **`phases/phase-5/regenerate_184_with_stage1_v2.py`** — created. 187-school regen runner.
- **`phases/phase-5/regen_184_run_log.txt`** and **`regen_184_results.jsonl`** — created. Run telemetry.
- **`phases/phase-5/positive_content_test_v1.md`** — created. 10-narrative editorial review document.
- **`phases/phase-5/discipline_legal_context_sample.md`** — created. 10-narrative IDEA/504/FAPE diagnostic.
- **`phases/phase-3R/data_element_inventory.md`** — created. Phase 3R first artifact (read-only inventory).
- **MongoDB `schools` collection** — 185 documents updated. `layer3_narrative.text` regenerated with `stage1_prompt_version=layer3_v2` and `regenerated_2026_05_02=true`. The other 2,347 documents are unchanged from the prior production state.

---

## 9. Where to start (recommended sequence for the next CC)

1. **Read `CLAUDE.md`** — operating instructions. Non-negotiable rules.
2. **Read this handoff document** in full.
3. **Read `docs/build_log.md`** — focus on the latest entries (everything dated 2026-05-02 onwards).
4. **Read `docs/rule_audit_2026_05.md`** — particularly the Must-fix / Should-fix sections in Part 4.
5. **Optionally, skim `docs/receipts/phase-5/task3_layer3_production.md`** for current production state.
6. **Wait for builder direction** on which Stage 2 v4 must-fix to start drafting. Do not begin Stage 2 v4 work without explicit selection.
7. **Recommended starting candidate:** Coverage Gap 2 (non-traditional school narrative framing). It has the clearest diagnostic shape — query `school_type ≠ "Regular School" AND layer3_narrative.status = ok`, sample 5-10 narratives across the four non-Regular categories (Alternative / Special Education / Career and Technical / manual exclusions), assess whether standard narrative framing is misleading on those schools, design a school-type branch in Stage 2 if the diagnostic confirms the gap is material. Echo Glen (juvenile detention) is a known case to anchor the diagnostic.
8. **Apply the diagnostic-first principle to whichever item is selected.** Do not draft a rule until the diagnostic confirms the failure mode is occurring in production output. The IDEA/504/FAPE non-decision is the canonical reference for "diagnostic ran, rule not needed" — that pattern applies to every must-fix item until disproven.
9. **For each Stage 2 v4 rule revision: dry-run on a small sample, builder editorial review, then scale.** Group multiple v4 revisions into one prompt-version bump where practical to avoid running multiple full regenerations.
10. **When scaling: set `stage1_prompt_version` and `regenerated_<date>` on every write.** Today's regen pattern is `stage1_prompt_version=layer3_v2` and `regenerated_2026_05_02=true`. Future regenerations should follow the same shape.

---

## Open questions to surface to the builder when work resumes

- Which Stage 2 v4 must-fix to start with? (Recommendation above is Coverage Gap 2 / non-traditional school framing.)
- For Coverage Gap 1 (trust-model disclaimer): rendered into narrative text, or rendered at frontend? Decide before drafting.
- Backfill `stage1_prompt_version=layer3_v1` on the 1,700 unchanged narratives, or leave implicit?
- `docs/build_sequence.md` retire-or-keep decision.
- Statistical methodology external review (foundation Risk 1) — is this still on the path-to-launch sequence, and what triggers it?
- Pre-launch license decision (harm register entry "Derivative works that recontextualize data as rankings or recommendations") — what's the current thinking?

---

*Phase 5 is close to closing. Five Stage 2 v4 rule revisions, each with diagnostic-then-design discipline, plus the documentation work in §5, plus builder review at each gate. Past that, Phase 3R formalization (the comparison engine spec) and Layer 2 narrative design are the next major workstreams.*

*Welcome, next CC. Read carefully and don't break what's working.*
