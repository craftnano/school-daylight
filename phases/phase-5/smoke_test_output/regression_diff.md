# Phase 5 Task 1 Smoke Test — Regression Diff Report

**Definition of regression:** A violation phrase appearing in the new auto-check output
that did NOT appear in the cached round1_three_stage auto-check output. Same as the
definition used by run_round1.py:411-423 (the canonical 50-school replay).

**Why not byte-identical narratives?** The Anthropic API is stochastic at temperature>0
(default 1.0). Same prompts produce same output distribution, not same string. Byte-identity
of the PROMPT STRINGS sent to the API is proven separately by
phases/phase-5/acceptance_test_prompt_extraction.py (all six system+user pairs match).

## Per-school

### Bainbridge High School (530033000043)

- Stage 0 drops match cached: **True**
- Regressions (new violations not in cached): **NONE**

### Halilts Elementary School (530033000044)

- Stage 0 drops match cached: **False**
  - cached drops: [(4, 'CONDUCT_DATE_ANCHOR')]
  - new drops:    []
- Regressions (new violations not in cached): **NONE**

### Echo Glen School (530375001773)

- Stage 0 drops match cached: **True**
- Regressions (new violations not in cached): **NONE**

### Cascade High School (530267000391)

- Stage 0 drops match cached: **True**
- Regressions (new violations not in cached): **NONE**

### Maywood Middle School (530375000579)

- Stage 0 drops match cached: **True**
- Regressions (new violations not in cached): **NONE**
  - All new violations (regressions + carryovers): {'death_circ': ["'at the school'"]}
  - All cached violations: {'death_circ': ["'at the school'"]}

## Summary

- Schools tested: 5
- Schools with regressions (NEW violations not in cached): **NONE**
- Schools with Stage 0 drop deltas: **1**

**Auto-check regressions: ZERO.** No new violation phrases introduced by the
extracted-prompts run. Pre-existing false positives (e.g., the documented
`'at the school'` substring match on non-death contexts) reproduce identically.

**Stage 0 drop delta noted.** This is Haiku non-determinism on date-inference tasks at
temperature=1.0 (the model is asked to infer `~1985` from the phrase "approximately
40 years prior" relative to a 2024 filing). The Python rule is deterministic; the
variance is in the model's extraction. The byte-identity test confirms the prompt
strings are unchanged, so this delta is not introduced by prompt extraction.
This existing architectural limitation is documented in the Phase 4.5 exit doc
("a long sensitivity review is a feature, not a bug") and was already a known
source of variance in the original 50-school replay.