# Phase 5 — Task 1 Verification Receipt: Layer 3 Prompt Extraction

**Date:** 2026-04-30
**Task:** Extract the three Stage 0/1/2 prompts from `phases/phase-4.5/test_results/round1_three_stage/run_round1.py` into versioned plaintext files in `prompts/`.
**Result:** PASS

---

## What Was Done

Created three versioned prompt files following the CLAUDE.md convention (grep-able header block, named placeholders, no Python f-strings inside the prompt files):

- `prompts/layer3_stage0_haiku_extraction_v1.txt` — Stage 0 Haiku structured extraction
- `prompts/layer3_stage1_haiku_triage_v1.txt` — Stage 1 Haiku editorial triage
- `prompts/layer3_stage2_sonnet_narrative_v1.txt` — Stage 2 Sonnet 4.6 narrative writing

Each file contains a `# PURPOSE / # MODEL / # INPUTS / # OUTPUTS / # VERSION / # CHANGELOG` header followed by two clearly delimited sections:

```
===SYSTEM===
<the system prompt — verbatim from run_round1.py, no placeholders>
===USER===
<the user-message template — with named placeholders {school_name}, {district_name}, {nces_id}, {findings}>
```

The runner reads each file, splits on the `===SYSTEM===` and `===USER===` markers, and substitutes placeholders in the user template via `str.replace()`. `str.format()` is NOT used because the system prompts contain JSON examples with literal `{` and `}` characters that would break it. This matches the convention already used by `pipeline/17_haiku_enrichment.py` (lines 136-156).

A loader module was added: `pipeline/layer3_prompts.py`. It exposes `load_stage0()`, `load_stage1()`, `load_stage2()`, and `fill_user(template, **values)`.

## Source File Hashes (for provenance)

| File | SHA256 |
|------|--------|
| `prompts/layer3_stage0_haiku_extraction_v1.txt` | `ccff8c9368bebc6ec7d876b761336cc44ac5d6fb203cb3f9726a08d71bd02e8c` |
| `prompts/layer3_stage1_haiku_triage_v1.txt` | `9056253b2268e61ab9d8c8a10542ec71a4769c9b62373fc0af81b5f3c2319b9f` |
| `prompts/layer3_stage2_sonnet_narrative_v1.txt` | `c394721464331f0a941c9248e8a6dec3207c4b901fc9f3170ad74edb2cf6b01a` |
| `phases/phase-4.5/test_results/round1_three_stage/run_round1.py` (canonical source) | `d2c82a1534d4377b41d6b0607896b0e94f402fbca9b3cdc4b3e49c10d6cd2cc2` |

---

## Acceptance Test 1: Byte-Identity of Prompts

**Test:** `phases/phase-5/acceptance_test_prompt_extraction.py`

The script imports the canonical `STAGE0_PROMPT`, `STAGE1_PROMPT`, `STAGE2_PROMPT` constants from `run_round1.py`, loads the new prompt files via `pipeline/layer3_prompts.py`, substitutes the SAME placeholder values into both the inline f-string templates and the loaded user templates, and compares all six resulting strings (3 system + 3 user) byte-by-byte.

**Result:** **PASS — all 6 strings byte-identical.**

```
[PASS] Stage 0 SYSTEM — byte-identical (3,198 chars)
[PASS] Stage 0 USER   — byte-identical (214 chars)
[PASS] Stage 1 SYSTEM — byte-identical (3,585 chars)
[PASS] Stage 1 USER   — byte-identical (249 chars)
[PASS] Stage 2 SYSTEM — byte-identical (4,052 chars)
[PASS] Stage 2 USER   — byte-identical (374 chars)
```

This is the strongest possible deterministic check. The zero-hallucination property of the Round 1 50-school three-stage replay is a property of the exact prompt strings; this test confirms the prompts have not changed by even a single character. No quote style was altered, no trailing newline was lost, no placeholder substitution introduced any drift.

---

## Acceptance Test 2: 5-School Smoke Test (Live API Run)

**Test:** `phases/phase-5/smoke_test_5_schools.py` (live run) → `phases/phase-5/recompute_smoke_diff.py` (analysis)

The handoff explicitly asked for a live rerun on 5 schools using the extracted prompts. The smoke test was run with the LOADED prompts (not the inline constants) on five schools selected from the validated 50-school set:

| NCES ID | School | Why selected |
|---------|--------|--------------|
| 530033000043 | Bainbridge High School | Canonical Stage 0 drop case (1985 lawsuit) |
| 530033000044 | Halilts Elementary | District-attribution propagation test |
| 530375001773 | Echo Glen School | Most complex (6 included, 4 excluded) |
| 530267000391 | Cascade High School | Standard 3-incl / 3-excl mix |
| 530375000579 | Maywood Middle School | 3-incl / 6-excl mix; known false-positive locus |

**Cost:** $0.0953 ($0.0444 Haiku + $0.0509 Sonnet) across 5 schools.

### What can and cannot be compared

- **Cannot compare:** narrative text byte-for-byte. The Anthropic API is stochastic at temperature > 0 (the runner uses default temperature 1.0). Same prompts produce the same OUTPUT DISTRIBUTION, not the same string. A literal "bit-identical narrative" check is not possible with this architecture; it would only be achievable with a deterministic decoding mode that the project has chosen not to use.
- **Can compare deterministically:** the substituted prompt strings (covered by Acceptance Test 1 above), the Python rule application in Stage 0 (deterministic given Haiku's extraction), and the regression diff on auto-checks (defined in `run_round1.py:411-423` as new violation phrases that did not appear in cached).

### Results

| School | Stage 0 drops match cached | Auto-check regressions |
|--------|---------------------------|------------------------|
| Bainbridge High School | yes | none |
| Halilts Elementary | **no** (see below) | none |
| Echo Glen School | yes | none |
| Cascade High School | yes | none |
| Maywood Middle School | yes | none (one carryover false positive — see below) |

**Auto-check regressions across all 5 schools: ZERO.** No new violation phrases were introduced by the extracted-prompts run. The full per-school diff is in `phases/phase-5/smoke_test_output/regression_diff.md`.

### Two non-regression deltas to explain

#### 1. Halilts Elementary — Stage 0 drop count differs (cached: 1, new: 0)

Cached run: Haiku correctly inferred `conduct_date_latest = 1985` from the input phrase "approximately 40 years prior" relative to a 2024 lawsuit filing. The CONDUCT_DATE_ANCHOR rule then dropped the finding (it pre-dates the 20-year window).

New run: Haiku did not output a 1985 inference for the same finding on this run. With no `conduct_date_latest`, the Python rule had nothing to compare against and did not drop the finding. Stage 1 then included it; the new narrative includes a third paragraph about the 1985 abuse case.

This is **Haiku non-determinism on a date-inference task at temperature=1.0**. The Python rule is deterministic. The prompt strings are byte-identical (Acceptance Test 1). The variance lives entirely in the model's extraction output. This is the same architectural limitation the Phase 4.5 exit document anticipated and accepted ("a long sensitivity review is a feature, not a bug") — and it would be flagged for builder review by the production process exactly as designed.

This delta is **not introduced by Task 1**. The same finding could have flipped between drop and no-drop in the original Round 1 50-school replay just by re-running it.

#### 2. Maywood Middle School — `'at the school'` flagged in BOTH new and cached

The death-circumstance regex in `run_round1.py` includes the substring `at the school`, which produces a false positive whenever a narrative mentions "students at the school" or similar — a non-death context. The Phase 4.5 exit document calls this out explicitly ("Death-Circumstance Regex Stays Conservative — false positives are loud but harmless and human review catches the real cases").

Cached run for Maywood flagged exactly this phrase (`death_circ: ["'at the school'"]`). The new run flagged exactly this phrase. **Identical false positive in both runs — zero regression.**

---

## What Was NOT Modified

Per the handoff, the following were left untouched:
- `prompts/sonnet_layer3_prompt_test_v1.txt` and `prompts/sonnet_layer3_prompt_test_v2.txt` — the historical pre-pivot single-stage prompts.
- The five existing runner scripts under `phases/phase-4.5/test_results/` (validation lineage). The new prompt files are byte-identical to the embedded constants in those scripts; once Phase 5 production code is written, the duplicated inline prompts can be retired in favor of the loader.
- The 14 editorial rules. The three-stage architecture. Any MongoDB documents.

---

## Files Touched

- New: `prompts/layer3_stage0_haiku_extraction_v1.txt`
- New: `prompts/layer3_stage1_haiku_triage_v1.txt`
- New: `prompts/layer3_stage2_sonnet_narrative_v1.txt`
- New: `pipeline/layer3_prompts.py`
- New: `phases/phase-5/acceptance_test_prompt_extraction.py`
- New: `phases/phase-5/smoke_test_5_schools.py`
- New: `phases/phase-5/recompute_smoke_diff.py`
- New: `phases/phase-5/smoke_test_output/<5 per-school JSONs>` (~15 KB each)
- New: `phases/phase-5/smoke_test_output/diff_report_2026-04-30_115251.md`
- New: `phases/phase-5/smoke_test_output/regression_diff.md`
- New: `docs/receipts/phase-5/task1_prompt_extraction.md` (this file)

No production data was modified. No MongoDB writes. No changes to existing prompt files. No changes to the canonical runner.

---

## How a Future Caller Uses the New Files

```python
from pipeline.layer3_prompts import load_stage0, load_stage1, load_stage2, fill_user

s0_sys, s0_user_tmpl = load_stage0()
s1_sys, s1_user_tmpl = load_stage1()
s2_sys, s2_user_tmpl = load_stage2()

# Stage 0 — only {findings} placeholder
s0_user = fill_user(s0_user_tmpl, findings=findings_json_string)

# Stage 1 / Stage 2 — four placeholders
s1_user = fill_user(s1_user_tmpl,
                    school_name=name, district_name=district,
                    nces_id=nces_id, findings=findings_json_string)
```

The loader resolves paths relative to `pipeline/` so it works whether called from `pipeline/`, `phases/phase-5/`, `tests/`, or anywhere else under the project root.

---

## Decision

**Task 1: PASS.**

Prompts extracted to versioned plaintext files. Byte-identity to the canonical inline constants is proven (six strings, six matches). A live 5-school smoke test produced zero auto-check regressions; the one Stage 0 drop delta is Haiku non-determinism on date inference, not a prompt-extraction bug. The new files are ready for Phase 5 production code to consume.

**Approved by:** Claude Code (Phase 5 agent)
**Date:** 2026-04-30
