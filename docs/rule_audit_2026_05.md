# Phase 5 Prompt Rule Audit — 2026-05-02

**Scope:** Editorial rules across the three current canonical Layer 3 prompt files. Reviewed for coherence with `docs/foundation.md` and `docs/harm_register.md`.

**Files audited:**
- `prompts/layer3_stage0_haiku_extraction_v1.txt` (canonical)
- `prompts/layer3_stage1_haiku_triage_v2.txt` (canonical as of 2026-05-02; v1 retired)
- `prompts/layer3_stage2_sonnet_narrative_v3.txt` (canonical)

**Out of scope:** Phase 4 enrichment prompts, Phase 4 validation prompts, Stage 0 Python rule application code (`pipeline/18_layer3_production.py:244-294`), `layer3_findings.py` dedup logic. The Phase 4 prompts and the Python rules live editorial logic too — flagged in Part 4 as a follow-up.

**Process:** Documentation only. No prompts modified. No rewordings proposed.

---

## PART 1 — Rule Inventory

### Stage 0 — Haiku structured extraction
File: `prompts/layer3_stage0_haiku_extraction_v1.txt`

| ID | Rule (verbatim, abbreviated where long) | Lines | Type |
|----|----------------------------------------|-------|------|
| R001 | "Your ONLY job is to extract dates and a type tag from each finding. Do NOT make inclusion or exclusion decisions. Do NOT apply editorial rules. The downstream code applies the rules; you only report what the text says." | 16 | architectural separation (other) |
| R002 | "conduct_date_earliest: Earliest date the underlying conduct/behavior occurred. The conduct is the alleged or actual behavior the finding is about — the abuse, the bullying, the cyber attack, the misconduct — NOT the lawsuit or settlement." Format YYYY/YYYY-MM/YYYY-MM-DD; null if not stated; if approximate (e.g., "approximately four decades ago") compute the implied year and note in rationale. | 20 | source fidelity |
| R003 | "conduct_date_latest: Latest date the underlying conduct occurred. Same format. If conduct was a single event, equal to earliest. Output null if not stated." | 22 | source fidelity |
| R004 | "response_date: Date of the institutional response — the lawsuit filing, settlement, verdict, investigation start, dismissal, or other formal action by the school/district/legal system. This is distinct from when the conduct occurred. If multiple response actions are mentioned, use the most recent. Output null if not stated." | 24 | source fidelity / temporal anchor |
| R005 | response_type controlled vocabulary: lawsuit_filing, settlement, verdict, investigation, dismissal, withdrawal, resolution_without_finding, conviction, policy_change, other, unclear. | 26-37 | formatting / source fidelity |
| R006 | finding_type_tag: short snake_case slug from a fixed vocabulary (sexual_abuse_by_staff, racial_discrimination, cybersecurity_breach, leadership_misconduct, financial_emergency, gun_on_premises, student_death_negligence, civil_rights_complaint, staff_misconduct_other, positive_recognition, routine_governance, etc.). Used by Python pattern detection across findings within a school. | 39-54 | formatting / pattern key |
| R007 | "rationale: One sentence describing how you extracted these fields. If you inferred a date from approximate language, say so." | 56 | source fidelity (transparency) |

### Stage 1 — Haiku editorial triage
File: `prompts/layer3_stage1_haiku_triage_v2.txt`

| ID | Rule (verbatim, abbreviated where long) | Lines | Type |
|----|----------------------------------------|-------|------|
| R008 | "Adverse outcomes (settlements, convictions, sustained investigations): include only if within 10 years" | 32 | inclusion threshold / temporal anchor |
| R009 | "Allegations, dismissals, unresolved matters: include only if within 5 years" | 33 | inclusion threshold / temporal anchor |
| R010 | "PATTERN EXCEPTION: If 2+ findings of the same type (e.g., sexual abuse settlements, failure-to-report cases) exist within a 20-year window, ALL findings in the pattern stay. The pattern is the finding." | 34 | inclusion threshold (exception) |
| R011 | "SEVERITY EXCEPTION: If a finding involves credible allegations of sexual violence against students AND institutional suppression of reporting or investigation (e.g., administrators discouraging police involvement, failure to notify authorities), the finding may be included beyond the standard 10-year window even without a pattern match. The combination of severity and institutional complicity makes these findings relevant to current school culture regardless of age." | 35 | inclusion threshold (exception) |
| R012 | "Private citizens (candidates, volunteers, parents, former students with no institutional role): exclude" | 41 | categorical exclusion |
| R013 | "Events with no institutional connection (geographic proximity only): exclude" | 42 | categorical exclusion |
| R014 | "Exonerated findings (cleared, charges dropped, acquitted): exclude entirely" | 43 | categorical exclusion |
| R015 | "Individual student conduct (unless it triggered institutional response): exclude" | 44 | categorical exclusion |
| R016 | "Awards, recognitions, formal program designations, civil-rights or equity recognitions, sustained measurable improvements, and positive achievements: INCLUDE when they meet the recency rules above and have high source confidence. These findings carry parent-relevant signal about what a school is doing well — they belong in the briefing. Stage 2 handles the writing; Stage 1 should pass them through." | 48 | inclusion threshold (positive) |
| R017 | "Routine leadership appointments, board governance, policy announcements: exclude. These are noise, not achievement." | 49 | categorical exclusion |
| R018 | Theme-tag controlled vocabulary for included findings: safety / legal / governance / academic / community_investment. | 53-56 | formatting |
| R019 | "Do NOT add any outcome, resolution, or disposition that is not explicitly stated in the finding text." | 61 | source fidelity |
| R020 | "If a finding describes an allegation but does not state a resolution, pass it through WITHOUT a resolution." | 62 | source fidelity |
| R021 | "Do NOT infer, assume, or add what happened after the events described." | 63 | source fidelity |
| R022 | "Do NOT add context from your own knowledge about the case, the people involved, or the outcome." | 64 | source fidelity |
| R023 | "The original finding text must be passed through UNCHANGED." | 65 | source fidelity |
| R024 | "ALWAYS emit the finding's `date` from the input metadata in your output, even if the date is not mentioned in the summary text. If the input date is missing or 'undated,' output 'undated.' The downstream narrative writer needs the date to lead every finding with a year — do not drop it." | 66 | formatting / temporal anchor |

### Stage 2 — Sonnet narrative writing
File: `prompts/layer3_stage2_sonnet_narrative_v3.txt`

| ID | Rule (verbatim, abbreviated where long) | Lines | Type |
|----|----------------------------------------|-------|------|
| R025 | Rule 1 — "Date-first: Every finding must lead with the year. 'In 2024, ...' or 'In an undated report, ...'" | 34 | formatting / temporal anchor |
| R026 | Rule 2 — "No individual names: Use role descriptions only. 'a teacher,' 'the principal,' 'the superintendent.' Never output any person's name." | 35 | redaction |
| R027 | Rule 3 — "No student names or identifiers: Students are 'a student,' 'a freshman,' 'several students.' Nothing more specific. Do not include age, disability status, or any combination of descriptors that could identify a specific student." | 36 | redaction |
| R028 | Rule 4 (strengthened in v3) — "Death-related institutional responses: reference ONLY the institutional response. Suppress all manner of death (gunfire, drive-by shooting, vehicle accident, drowning, hanging, suicide, self-harm method, medical event, drug overdose, starvation) and all location of death — both specific and general. Suppress physical circumstances. Forbidden phrasings: 'died following a [manner],' 'fatal [event],' 'killed in a [event],' '[manner]-related death.' Required: 'a student died' or 'the death of a student' followed by institutional response." | 37 | suppression |
| R029 | Rule 5 — "Consolidate related findings: Multiple findings from the same incident or ongoing story should be woven into one paragraph, in chronological order. Do not list as separate items." | 38 | formatting |
| R030 | Rule 6 — "Neutral tone: No evaluative language ('controversial,' 'divisive,' 'progressive,' 'conservative'). Pure factual reporting." | 39 | other (tone) |
| R031 | Rule 7 — "District-level vs. building-specific attribution: Lawsuits, settlements, and investigations against the district appear on all schools in the district, framed with 'at the district level' or equivalent. Building-specific incidents appear only on that school's briefing. Treat as district-level if the finding names the district as actor or defendant; building-specific only if it names a specific school as the locus of the incident." | 40 | attribution |
| R032 | Rule 8 — "Vary transitions: Use different opening phrases across paragraphs." | 41 | formatting |
| R033 | Rule 9 — "Gender-neutral student references: Neutralize gendered language whenever it refers to a student. Replace 'his daughter,' 'her son,' 'she,' 'he' with gender-neutral forms ('the student,' 'their child,' 'they'). Source text often retains gendered pronouns; do not pass them through. This prevents identification through demographic narrowing. Gendered pronouns for adults in institutional roles are also disallowed under Rule 2." | 42 | redaction |
| R034 | Rule 15 — "Timeless past-tense framing: Forbidden — 'remain allegations,' 'remains unresolved,' 'is currently under investigation,' 'is ongoing,' 'as of [year], law firms are investigating,' 'no resolution has been reported.' Required — '[Year] [event] did not, in available sources, indicate any resolution,' 'The cited records do not reflect a resolution,' 'As reported in [year], the investigation was underway,' 'Available records as of [generation date] show no resolution.' Every sentence should remain truthful at any future date the narrative is read." | 44-57 | temporal anchor / source fidelity |
| R035 | Rule 16 — "Source-fidelity verbs for individual conduct: Use only the verbs the source uses. Do not substitute 'was fired,' 'was terminated,' 'resigned,' 'was dismissed,' 'was demoted,' 'was reassigned,' 'was disciplined,' 'was let go,' 'received a warning' unless those exact verbs appear in the Stage 1 source. If disposition is unclear, use past-anchored framing ('available records do not reflect a disposition'). Applies whenever the subject is an individual identifiable by name, role, or triangulation of role + institution + date." | 59-63 | source fidelity |
| R036 | Rule 17 — "Grade-level identifier redaction: Replace 'senior year,' 'junior year,' 'sophomore year,' 'freshman year,' 'eighth grader,' 'fifth grader,' 'in [N]th grade,' 'a [N]th grade student' with general references ('while a student,' 'during the student's enrollment,' 'as a student,' 'a student at the school'). Applies even when grade-level language appears in the Stage 1 source text." | 65-67 | redaction |
| R037 | Critical no-fabrication block — "Write ONLY using facts present in the provided findings. Do NOT add any outcomes, resolutions, consequences, or follow-up actions not stated. If a finding describes an allegation with no stated resolution, present it as such. Do not invent what happened next. You have no knowledge beyond what is provided." | 71-75 | source fidelity |
| R038 | Per-paragraph citations — "Each paragraph ends with [Sources: URL1; URL2; URL3] — plain-text, semicolon-separated, no markdown. URLs from each finding's source_url. If a finding has no source_url, render '[Sources: URL1; URL2; (one source unavailable)]' — make the gap explicit." | 79-87 | formatting / attribution / transparency |
| R039 | Citation integrity — "Do not invent URLs. Do not summarize multiple sources into a single fictional citation. Each URL must come from a real finding's source_url field for that school." | 91 | source fidelity |

**Total: 39 rules** across the three prompts. Note that the Stage 2 prompt internally numbers its rules 1–9 then jumps to 15–17 (the gap reflects the project's master 14-rule editorial framework — rules 10–14 live elsewhere in the architecture, primarily in Stage 1 triage and the Phase 4 enrichment prompts).

---

## PART 2 — Foundation & Harm-Register Alignment

### Per-rule alignment

| ID | Disposition | Citation |
|----|-------------|----------|
| R001 | IMPLEMENTS | foundation.md "Three-stage pipeline" — Stage 0 separation of mechanical extraction from editorial judgment. harm_register.md three-stage pipeline entry (Phase 4.5). |
| R002 | IMPLEMENTS | harm_register.md "Conduct-date anchor" (mentioned implicitly via the Phase 4.5 architecture that produced this rule). The conduct-vs-response distinction is what enables the conduct-date anchor downstream. |
| R003 | IMPLEMENTS | Same as R002. |
| R004 | IMPLEMENTS | Same as R002 — distinguishes institutional response date for the dismissed-case rule downstream. |
| R005 | IMPLEMENTS | foundation.md "AI Ethics by Design" three-stage architecture — controlled vocabulary supports Python rule application. |
| R006 | IMPLEMENTS | harm_register.md "pattern detection" (Phase 4.5 architecture); foundation.md AI Ethics by Design. |
| R007 | IMPLEMENTS | foundation.md "Default to transparency" — rationale field is auditable. |
| R008 | IMPLEMENTS | foundation.md "Use AI to contextualize" — recency calibration. Implicit in the project's 10-year window choice for adverse outcomes. **No explicit harm-register rationale for the 10-year number itself.** |
| R009 | IMPLEMENTS | Same as R008 — 5-year window for allegations. **No explicit harm-register rationale for the 5-year number.** |
| R010 | IMPLEMENTS | harm_register.md Phase 4.5 entries on pattern detection and the Bainbridge multi-finding test cases. |
| R011 | IMPLEMENTS | harm_register.md "Sensitivity flagging for high-impact findings" — sexual violence + institutional suppression is precisely the case the severity exception was built for. |
| R012 | IMPLEMENTS | harm_register.md "Individual names stripped from findings" (private-citizen liability concern) and "Phase 4 sensitivity flagging." |
| R013 | IMPLEMENTS | harm_register.md "School name disambiguation / wrong-school contamination" — geographic-proximity findings are the mirror failure mode. |
| R014 | IMPLEMENTS | foundation.md "no editorialization" implicit; legal exposure for republishing exoneration-irrelevant accusations. **Not explicitly in harm register.** |
| R015 | IMPLEMENTS | harm_register.md "Student names never appear" — individual student conduct is precisely the case where naming a minor would harm them. |
| R016 | IMPLEMENTS | foundation.md Principle 3 — "Recognize real achievement and surface real concerns. Showcase gains that current ratings miss, especially where educators outperform demographic expectations." Added as v2 on 2026-05-02. |
| R017 | IMPLEMENTS | foundation.md Principle 1 ("Inform, don't rank") and Goal 5 ("Generate concrete next steps") — routine governance is parent-irrelevant noise. |
| R018 | IMPLEMENTS | foundation.md "Output: The Briefing" — theme tagging supports the briefing's structured sections (Climate and discipline / Reputation and news / Strengths and recognition). |
| R019 | IMPLEMENTS | foundation.md "Use AI to contextualize, not to judge" — Stage 1 must not assert outcomes the source did not. harm_register.md "LLM hallucination in web-sourced findings." |
| R020 | IMPLEMENTS | Same as R019. |
| R021 | IMPLEMENTS | Same as R019. |
| R022 | IMPLEMENTS | Same as R019. |
| R023 | IMPLEMENTS | foundation.md "Default to transparency" — verbatim pass-through preserves auditability. |
| R024 | IMPLEMENTS | foundation.md "Default to transparency" — every claim must be date-anchored, traceable. |
| R025 | IMPLEMENTS | Same as R024 — Stage 2 enforces the date-first surface rendering. |
| R026 | IMPLEMENTS | harm_register.md "Individual names stripped from findings" — direct implementation. |
| R027 | IMPLEMENTS | harm_register.md "Student names never appear in briefings" — direct implementation. |
| R028 | IMPLEMENTS | harm_register.md "Student deaths excluded from enrichment findings" + Phase 4.5 narrative-fix entries (Bainbridge wooded-area location leak). The strengthened v3 form addresses the Frontier MS gun-violence case specifically. |
| R029 | IMPLEMENTS | foundation.md "Output: The Briefing" — consolidation supports readability for the parent-target audience. |
| R030 | IMPLEMENTS | foundation.md Principle 4 ("Use AI to contextualize, not to judge") and Risk 6 ("Political Sensitivity Around Civil Rights Data" — language discipline matters). |
| R031 | IMPLEMENTS | harm_register.md Phase 4.5 entry "District-attribution rule encoded (Stage 2 Rule 7)." |
| R032 | IMPLEMENTS | foundation.md "Output: The Briefing" — varied prose supports parent readability. **Marginal — this is craft guidance, not a harm-driven rule.** |
| R033 | IMPLEMENTS | harm_register.md "Student names never appear" + Phase 4.5 entry "Gender-neutral student pronouns" (gendered pronouns combined with narrowing details can identify a student). |
| R034 | IMPLEMENTS | foundation.md "Default to transparency" + the briefing being a long-cached document. The principle of "every sentence remains truthful at any future date" maps to the cached / batch-refresh briefing model in foundation.md "Caching and Cost Strategy." |
| R035 | IMPLEMENTS | harm_register.md "LLM hallucination in web-sourced findings" — verb fabrication was the canonical failure (Juanita HS "placed on leave but later cleared"). |
| R036 | IMPLEMENTS | harm_register.md "Student names never appear in briefings" — grade-level identifiers are forbidden student-identifying details by Rule 3. |
| R037 | IMPLEMENTS | harm_register.md "LLM hallucination" — this is the no-fabrication backstop. foundation.md "Use AI to contextualize, not to judge." |
| R038 | IMPLEMENTS | foundation.md "Default to transparency" — every claim is sourced. **Note: the harm-register entry "Three-layer trust model" (Phase 5 Planned) calls for clear distinction between verified data, narrative interpretation, and web-sourced findings; per-paragraph citations on Layer 3 narrative are part of that model.** |
| R039 | IMPLEMENTS | harm_register.md "LLM hallucination" — applied to URLs specifically. |

**Counts: 39 IMPLEMENTS, 0 ORPHANED, 0 CONTRADICTS** (line-37 v1 contradiction was already corrected in v2 retirement on 2026-05-02). Two rules (R014, R032) have weak/marginal harm-register linkage and could benefit from explicit documentation.

### Coverage gaps — foundation principles / harm-register entries with NO implementing rule

These are present in `foundation.md` or `harm_register.md` but have no corresponding rule across the three Stage prompts. Many are intentionally implemented elsewhere (Phase 4 enrichment, Stage 0 Python, frontend) — flagged as gaps relative to *this audit's scope* (Stage 0/1/2 prompts), not as architectural gaps overall.

1. **Three-layer trust model (harm_register.md, Phase 5 entry).** The harm register specifies "(1) verified data presented visually, (2) narrative interpretation of verified data only, (3) web-sourced findings clearly labeled with LLM/web disclaimer." Per-paragraph citations (R038) partially implement this for Layer 3, but there is no rule that produces or enforces an LLM/web disclaimer on the narrative output. **Belongs in Stage 2 prompt as a structural footer or in the frontend.**
2. **Non-traditional school narrative framing (harm_register.md, Phase 5 entry).** The harm register names this as Phase 5 to-implement: juvenile detention, homeschool partnerships, virtual schools, alternative programs should branch on `school_type` and apply different narrative framing. **No rule in the three Stage prompts implements school-type branching.** The dry-run-v2 Echo Glen narrative was flagged in the build log as exhibiting this gap.
3. **Extreme outlier without explanation (harm_register.md, Phase 5 entry).** "Mode 1 explain this anomaly / Mode 2 notice this signal" framing for metrics ≥3 SD from peers. **No rule in Stage prompts implements this** — it lives in the briefing's Layer 2 design which has not begun. Out of scope for Layer 3 prompts but worth noting the gap.
4. ~~**Legal-constraint context for discipline / safety (foundation.md).**~~ **RESOLVED 2026-05-02.** The Coverage Gap 4 hypothesis was diagnosed against 261 status=ok narratives matching disability/restraint/seclusion/special-ed keywords (see `phases/phase-5/discipline_legal_context_sample.md`). Finding: source-language framing already carries legal context for substantive disability-rights enforcement (DOJ settlements, state AG investigations, OCR resolutions describe violations using legal terminology like "inappropriately and repeatedly secluded and restrained students with disabilities outside of emergency situations as required by law"). Imposing additional structural framing would be grafted onto findings about clear violations and off-topic on incidentally-matched narratives. **Decision: do not add IDEA/504/FAPE legal-context rule to Stage 2.** `docs/foundation.md` has been updated (Section "Interpreting Discipline and Safety Data: Legal Constraints as Context") to reflect this finding. This Coverage Gap is removed from the Phase 5 audit.
5. **Statewide context / "what's missing" disclosure (foundation.md, Output: The Briefing).** The briefing template names "Statewide context: pandemic recovery, policy changes, anything that affects how to read this year's numbers" and "What's missing: explicit disclosure of every data point the briefing couldn't access." **No rule in Layer 3 Stage 2 produces or signals this** — also a Layer 2 / frontend concern.
6. **Caveat language for restraint/seclusion data (foundation.md, Risk 3).** "Restraint/seclusion flags get extra caveat language, lower confidence presentation, and explicit disclosure of the GAO findings." **No Stage 2 rule directs special handling of restraint/seclusion findings** beyond the general death-circumstance suppression (R028). If a Phase 4 finding mentions restraint/seclusion, Stage 2 treats it like any other safety-themed finding.
7. **Discipline disparity baseline disclosure (harm_register.md).** "Using white students as the baseline for discipline disparity ratios... must disclose and explain the baseline choice." **Out of Layer 3 scope** — belongs to Layer 2 and the frontend — but flagged because the harm register says "The briefing must disclose."
8. **Suppressed-data communication (harm_register.md "Suppression integrity").** Suppressed values stored as null + flag, never zero. **Out of Layer 3 scope** — belongs to data-layer pipeline. Mentioned to confirm it's not a Layer 3 concern.

---

## PART 3 — Internal Consistency

### Direct contradictions

**None.** The 2026-05-02 retirement of v1 line 37 ("Awards, recognitions, and positive achievements: exclude") removed the only documented direct contradiction (between that rule and foundation.md Principle 3). v2 R016 inverts the rule cleanly.

### Calibration asymmetries

**A1. Recency-window asymmetry: positive vs. adverse content (R008/R009 vs R016).**
R008 / R009 set 10-year and 5-year windows respectively for adverse content. R016 applies *the same windows* to positive content ("INCLUDE when they meet the recency rules above"). The relevance horizons may legitimately differ: a 2009 administrator-misconduct allegation has decayed parent-relevance, but a 2009 National Blue Ribbon designation is an enduring quality signal. The Stage 1 v2 dry run produced emergent stretching ("exceeds 10-year recency window but represents sustained measurable quality indicator") — Haiku is correctly identifying the asymmetry the rules don't formalize. **Concern:** the symmetric application produces 92 schools where Stage 1 v2 still excluded positive findings under the adverse-content recency rule. This is the open audit item flagged in the 2026-05-02 build log.

**A2. Individual name stripping vs. institutional name retention (R026, R027 vs implicit handling of organizations).**
R026 forbids individual names; R027 forbids student names. Neither rule speaks to organizational complainants (e.g., "StandWithUs," "Council on American–Islamic Relations"). The build-log "Inglewood Middle School" observation flagged that Sonnet genericized "StandWithUs" to "a nonprofit legal team" while in another v2-dry-run narrative it preserved "StandWithUs" by name. **Concern:** Stage 2 has no rule on organizational names, so behavior is inconsistent across narratives.

**A3. Death-suppression scope vs. other harm types (R028).**
R028 applies imperative suppression to manner / location / physical circumstances of student deaths. Other categories of student harm — sexual assault, restraint/seclusion injuries, medical events that didn't result in death — get only the general redaction rules (R026, R027). **Concern:** A serious eye injury described in the Lake Washington / Shrub Oak narrative ("permanent eye injury to the student") is rendered with detail about the injury; analogous detail about a death would be suppressed. This may be intentional (deaths are categorically more sensitive) but is not documented as a deliberate calibration.

**A4. R030 evaluative-language list is closed and short.**
R030 forbids "controversial," "divisive," "progressive," "conservative." Four words. There is no general "no editorial framing that takes a side" backstop in v3 (there was in v1 / v2; let me re-check — yes, the surrounding language reads "Pure factual reporting"). **Concern:** Closed lists fail open. Adjacent terms ("contentious," "polarizing," "radical," "extreme," "woke," "anti-woke" — actually "woke" IS in the test runner's auto-check phrase list at `dry_run_v3.py:EVALUATIVE_PHRASES`, but NOT in the Stage 2 prompt itself) are not enforced by the prompt.

### Redundancies

**D1. R019 / R020 / R021 / R022 / R023 (Stage 1 factual-pass-through block) overlap heavily with R037 (Stage 2 no-fabrication block).** Both stages forbid: (a) adding outcomes/resolutions, (b) inferring what happened next, (c) bringing in outside knowledge. Stage 1 is the upstream guard; Stage 2 is the downstream guard. The redundancy is defense-in-depth and is probably load-bearing — but the two blocks could be referenced as a single rule with stage-specific application notes.

**D2. R026 (Stage 2 Rule 2 "no individual names") and R033 (Stage 2 Rule 9 "gendered pronouns for adults are also disallowed under Rule 2") overlap.** Rule 9 explicitly says it's restating Rule 2's scope. This is fine but means Rule 9 is doing two things at once (student-pronoun neutralization + reminder of Rule 2 scope). Could be split for clarity.

**D3. R024 (Stage 1 date pass-through) and R025 (Stage 2 date-first formatting) are coordinated rules.** R024 ensures date arrives at Stage 2; R025 ensures Stage 2 leads with it. Not redundant — sequenced — but the coupling is implicit (R024's rationale says "the downstream narrative writer needs the date to lead every finding with a year"). Worth surfacing the coupling so future prompt edits don't desync them.

### Implicit dependencies

**E1. Stage 1 assumes Stage 0 has run (R008–R024 all assume conduct-date anchor + dismissed-case have been pre-applied).** The v2 prompt acknowledges this on line 37: *"NOTE: The conduct-date anchor and dismissed-case rules have already been applied by an upstream pre-filter. You do not need to re-apply them."* Documented. Good.

**E2. Stage 2 assumes Stage 1 has run (R025–R039 operate on findings that have passed Stage 1 triage).** Stage 2 prompt says *"You will receive pre-triaged findings that have already passed editorial review. Your ONLY job is to write the narrative. Do not re-evaluate inclusion decisions."* Documented. Good.

**E3. R036 (grade-level redaction) depends on R023 (Stage 1's verbatim-pass-through).** R036 must rewrite grade-level language even when present in source. But Stage 1 R023 says "the original finding text must be passed through UNCHANGED." So Stage 2 sees `original_text` containing "senior year"; Stage 2 must redact in narrative output while leaving Stage 1's `original_text` field alone. **The dependency is implicit:** the rules assume Stage 2's narrative is a separate field from Stage 1's preserved original_text, and that downstream consumers don't render `original_text` to parents. Worth documenting.

**E4. R038 (per-paragraph citations) depends on `source_url` being present in each Stage 1 included finding's input JSON.** Stage 1's output schema does NOT carry `source_url` (R023 passes through `original_text` only). The current production runner injects `source_url` at Stage 2 build time by re-querying MongoDB — this dependency is documented in `pipeline/19_layer3_stage2_v3_batch.py` but is invisible from the Stage 2 prompt itself. A future caller that sends Stage 1 output directly to Stage 2 without enrichment would render every paragraph as `[Sources: (one source unavailable)]` and not realize why.

**E5. R028 death-suppression depends on Phase 4 enrichment having already excluded student-death findings without institutional response.** The harm register entry "Student deaths excluded from enrichment findings" makes this exclusion at the *enrichment* layer; Stage 2's R028 is the *backstop* for findings that did surface (because they had institutional response). If Phase 4 enrichment ever surfaces a no-institutional-response death finding, Stage 2's R028 would still apply death-circumstance suppression but the finding would have nothing else to say. **Dependency on Phase 4 prompt behavior is not documented in Stage 2.**

---

## PART 4 — Summary and Prioritized Items

### Overall assessment

The three Stage prompts are internally well-formed: 39 active editorial rules, all 39 trace to a foundation.md principle or harm_register.md entry (after the 2026-05-02 v2 line-37 retirement removed the one prior contradiction). Coverage gaps in this audit are predominantly *out of Layer 3 scope* — they belong to Phase 4 enrichment, Layer 2 design, the frontend, or the Stage 0 Python rule code. The two material in-scope gaps are positive-content recency calibration (Asymmetry A1) and the absence of school-type branching for non-traditional schools (Coverage Gap 2). The Stage 2 prompt also has no rule covering organizational-name handling (Asymmetry A2) or legal-constraint context for discipline findings (Coverage Gap 4) — both of which the foundation document explicitly calls out as project commitments.

### Must-fix (production-affecting)

1. **Asymmetry A1 — positive-content recency calibration.** The 10-year/5-year windows from R008/R009 apply symmetrically to positive content under R016, producing 92 schools in the regen run where Stage 1 v2 still excluded positive findings under adverse-content recency rules. Foundation Principle 3 ("recognize real achievement... showcase gains that current ratings miss") is partially blocked by this calibration. *Production impact: ~92 schools have less positive content than the rule revision intended.*
2. **Coverage Gap 2 — non-traditional school narrative framing.** Echo Glen (juvenile detention), virtual schools, homeschool cooperatives, and alternative programs all currently receive standard narrative framing. The harm register names this as a Phase 5 to-implement. *Production impact: every non-traditional school in MongoDB is a candidate for misleading narrative — Echo Glen specifically flagged in the build log.*
3. **Coverage Gap 1 — three-layer trust model footer / disclaimer.** The harm register specifies that Layer 3 (web-sourced findings) must be clearly labeled with an LLM/web disclaimer. R038 per-paragraph citations partially implement source-traceability; no rule produces a disclaimer that says "this section is AI-generated narrative based on web search." *Production impact: 1,885 narratives currently rendered without a structural disclaimer.*
4. **Asymmetry A2 — organizational name handling.** R026 forbids individual names; nothing covers organizational complainants. Behavior is inconsistent across narratives ("StandWithUs" preserved in some, generalized to "a nonprofit legal team" in others). *Production impact: parents see the same organization treated differently across schools in the same district.*
5. ~~**Coverage Gap 4 — legal-constraint context for discipline / safety findings.**~~ **RESOLVED 2026-05-02 via foundation.md update.** See Coverage Gaps section above. Source-language framing already carries the legal context for substantive disability-rights enforcement findings; no Stage 2 rule needed. Foundation document section "Interpreting Discipline and Safety Data: Legal Constraints as Context" rewritten to reflect this finding.

### Should-fix (calibration / redundancies)

6. **Asymmetry A3 — death-suppression scope.** R028 imperative suppression applies only to deaths. Analogous physical-harm details (eye injury, restraint injury, medical event short of death) get only general redaction. This may be intentional but is undocumented. Worth deciding: tier the suppression, or document the exception.
7. **Coverage Gap 6 — restraint/seclusion caveat language.** Foundation Risk 3 says these findings need "extra caveat language, lower confidence presentation, and explicit disclosure of the GAO findings." No Stage 2 rule covers this. CRDC restraint/seclusion data flows through Layer 3 like any other finding right now.
8. **Asymmetry A4 — R030 evaluative-language list is closed.** Four banned words; no general backstop. Adjacent terms ("contentious," "polarizing") not enforced.
9. **Implicit Dependency E5 — Stage 2 R028 depends on Phase 4 enrichment having pre-excluded no-institutional-response deaths.** Worth documenting in the Stage 2 prompt comment block.
10. **Implicit Dependency E4 — R038 citations depend on `source_url` injection that happens outside the prompt.** Worth a comment in the Stage 2 prompt header pointing to where the enrichment happens.

### Nice-to-fix (cleanup)

11. **Redundancy D1 — Stage 1 factual-pass-through block (R019–R023) and Stage 2 no-fabrication block (R037) overlap.** Five sub-rules at one stage, four at the other. Could be unified.
12. **Redundancy D2 — R033 (Rule 9) explicitly says it's restating R026 (Rule 2) scope. Could be split for clarity.**
13. **R032 (vary transitions) is craft guidance rather than harm-driven.** Worth documenting why it's a numbered rule rather than style guidance.
14. **R014 (exonerated findings) has weak harm-register linkage.** Currently traces to "no editorialization" implicit; explicit harm-register entry would make the rationale durable.
15. **Implicit Dependency E3 — R036 grade-level redaction acts on Stage 1's preserved `original_text`.** The dependency that downstream consumers don't render `original_text` to parents is implicit.

### Out of scope but flagged for tracking

- Stage 0 Python rules (`pipeline/18_layer3_production.py:244-294`) implement the conduct-date anchor and dismissed-case rule. These are editorial rules in code, not prompt — the audit document above does not enumerate them but they should be on the next-pass list.
- Phase 4 enrichment prompts (`prompts/context_enrichment_v1.txt`, `district_enrichment_v1.txt`) carry their own editorial rules (search categories, sensitivity flagging, confidence scoring, no-fabrication). The build log already flagged that these prompts do not actively name positive-content vocabulary — the diagnostic on 2026-05-02 documented the resulting under-coverage.
- Phase 4 validation prompts (`context_validation_v1.txt`, `district_validation_v1.txt`) carry editorial rules around wrong-school / wrong-state contamination. Not reviewed here.
- The dedup logic (`pipeline/layer3_findings.py:_dedup_key`) implements an editorial choice (district_context wins over context on collision). Not reviewed here.

---

*Documentation only. No prompts modified. No rule rewordings proposed. Builder works through findings and decides on revisions.*
