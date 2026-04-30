# Phase 4.5 — Sonnet Editorial Rule Testing

**Date:** 2026-02-23
**Phase:** 4.5 — Sonnet Narrative Testing (between Phase 4 Enrichment and Phase 5 Production)
**Depends on:** Phase 4 (COMPLETE)
**Does NOT depend on:** Phase 3 rerun (that blocks Phase 5, not 4.5)

---

## What This Phase Does

Test whether Sonnet correctly applies the editorial rules established during the Phase 4 sensitivity review before committing to full-batch narrative generation. Run Sonnet on ~40 hand-picked schools that exercise every editorial rule. Review output for compliance. Fix the prompt. Repeat until clean.

This is a test phase, not a production phase. No production narratives are generated. No briefing content is published. The output is a test report showing which rules Sonnet followed and which it violated.

---

## Why This Phase Exists

During Phase 4 sensitivity review, the builder established 14 editorial rules governing how findings should appear in parent-facing briefings:
1. No individual names in output
2. No student names ever
3. No student death details
4. Date-first formatting
5. Recency policy (10yr/5yr/20yr pattern)
6. Exoneration exclusion
7. No institutional connection = exclude
8. Private citizen exclusion
9. Individual student conduct exclusion
10. Parent relevance filter
11. Politically sensitive neutrality
12. Community action at scale framing
13. Consolidate related findings
14. Source quality awareness

Each rule has specific test cases with pass/fail criteria. These rules need to be validated against Sonnet before Phase 5 designs its production pipeline.

---

## Key Documents

- `phases/phase-4.5/sonnet_test_plan.md` — The full test plan with all 14 tests, specific schools, and pass criteria. THIS IS YOUR PRIMARY REFERENCE.
- `prompts/sonnet_layer3_test_v1.txt` — The draft Sonnet prompt encoding all editorial rules. To be refined based on test results.
- `phases/phase-4/sensitivity_review.md` — The 442 high-sensitivity findings. Test schools are drawn from this list.
- `docs/harm_register.md` — Living harm consideration document. Multiple entries inform the editorial rules.
- `CLAUDE.md` — Your operating instructions. Read it.

---

## Architecture

### One Test Script: `tests/sonnet_narrative_test.py`

This script:
1. Reads a list of test school NCES IDs from a config file
2. For each school, pulls context findings from MongoDB
3. Calls Sonnet with the Layer 3 prompt + the school's findings
4. Saves Sonnet's JSON response (narrative + transparency fields)
5. Generates a test report comparing output against pass criteria

This script lives in `tests/`, NOT in `pipeline/`. It does not modify MongoDB. It does not modify any pipeline output. It is read-only against the database.

### Output: `phases/phase-4.5/test_results/`

Each test run produces:
- `test_run_YYYY-MM-DD_HHMMSS.md` — Human-readable test report
- `raw_responses/` — Raw Sonnet JSON responses per school

### Cost Controls

| Control | Limit |
|---------|-------|
| Model | Sonnet (standard, not Batch API — we need real-time responses for review) |
| Max schools per run | 40 |
| Max output tokens per call | 2,000 |
| Extended thinking | Disabled |
| Estimated cost | $3-5 per run |

---

## Test Schools

The specific test schools are listed in `phases/phase-5/sonnet_test_plan.md` under each of the 14 tests. Approximately 40 unique schools across all tests. Some schools appear in multiple tests.

CC should:
1. Extract the unique set of NCES IDs from the test plan
2. Create a test config file listing them with which tests they exercise
3. Run all of them in one batch
4. Generate the test report organized by test number (1-14)

---

## Test Report Format

For each test:
```
## Test 1: Death/Suicide Suppression
### Beverly Elementary (530240000330) — REMOVED FROM PIPELINE
Not tested — finding removed during sensitivity review.

### Bainbridge Island SD (530033000043) — TEST
INPUT: $1.325M settlement related to student suicide
OUTPUT: [Sonnet's actual text]
PASS/FAIL: [Did it say "suicide"? Did it include death details? Did it lead with year?]
NOTES: [Any observations]

### Evergreen Public Schools (530270000412) — TEST
INPUT: Staff failed to report abuse, child died of starvation
OUTPUT: [Sonnet's actual text]
PASS/FAIL: [Did it include "starvation"? Did it frame around institutional failure?]
NOTES: [Any observations]
```

---

## Sequence of Work

1. Read `CLAUDE.md`
2. Read `phases/phase-4.5/sonnet_test_plan.md` thoroughly
3. Read `prompts/sonnet_layer3_test_v1.txt`
4. Build the test script (`tests/sonnet_narrative_test.py`)
5. Extract test schools from the test plan into a config file
6. Run the test batch
7. Generate test report → **HUMAN REVIEW GATE**
8. (After builder review, iterate on prompt if needed)
9. When all 14 tests pass, phase exits clean

**Full Phase 5 does NOT start until:**
- All 14 tests pass
- Phase 3 rerun complete (absenteeism thresholds + discipline minimum-N)
- Remaining sensitivity review complete (442 findings)
- Builder approves Phase 4.5 exit

---

## What NOT to Do

- Do NOT write to MongoDB
- Do NOT modify anything in `pipeline/`
- Do NOT run Sonnet on schools not in the test plan
- Do NOT create production narratives
- Do NOT modify the Phase 4 enrichment script or prompts
- Do NOT start Phase 5 design work

---

## Builder Context

The builder is not a developer. All editorial rules in the test plan came from the builder's manual review of 442 high-sensitivity findings. These rules reflect real harm considerations — dead children, sexual abuse, political flashpoints, reputational damage. The test is whether Sonnet can follow these rules consistently. If it can't, the prompt needs revision, not the rules.

The builder will review the test report line by line. Make it readable. Plain English. Show the input, show the output, show pass/fail.
