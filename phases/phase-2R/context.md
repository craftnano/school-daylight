# Phase 2R — Context

Pointers for any CC session opening this phase. Read these before starting substantive work.

## Project-wide reading (read first)

- `CLAUDE.md` — Project conventions, critical rules, destructive-operation gating, pre-execution review protocol.
- `docs/foundation.md` — Product specification, mission, architecture, known risks. Note especially Risk 8 (Premise Rot) and Risk 9 (LLM Confidence-as-Evidence), which were named after the incident that scoped this phase.
- `docs/build-sequence.md` — Phase-by-phase build plan. Phase 2R is documented in the "Phase numbering note" cluster at the top of "How to Use This Document."
- `docs/build_log.md` — Chronological decision history. The 2026-05-11 entry scopes Phase 2R; the 2026-05-08 entry covers the Phase 3R work that immediately precedes it.

## Phase 2R documents (in this folder)

- `plan.md` — Phase 2R full plan, including controls, sequential steps, decisions already made, and integrated handoff knowledge from the outgoing CC session. **Read this before any work in this phase.** The plan file is the handoff — there is no separate handoff document.
- `tasks.md` — Sequential checklist derived from `plan.md`. Pre-CC builder work (Steps A, B, C) is separated from CC work (Steps 1–14). Check off as completed.

## Decisions already settled

The "Decisions already made" section in `plan.md` records decisions reached during the advisor session that scoped this phase. These are settled. They include: the migrate-with-refresh approach (rebuild-from-scratch and full-history-block migration were both scoped and rejected), the vintage manifest as a permanent control, the targeted re-ingest pattern (following the May 7 zfill remediation precedent), and the scope boundaries for what this phase does and does not cover.

**Do not relitigate these decisions.** If you believe a settled decision is wrong, surface the concern to the builder via the pre-execution review protocol before any work that depends on the decision. Do not silently work around it; do not re-open it on your own initiative.

## Conventions reminders

- **Pre-execution review** (CLAUDE.md) is required for substantive new work in this phase. Phase 2R touches the data layer, schema, and methodology brief — every substantive step warrants surfacing ambiguities first.
- **Destructive operations** (CLAUDE.md) require plain-English proposal and plain-English approval before the command is written. Phase 2R is destructive-adjacent throughout (re-ingestion, collection writes, schema modifications); operate with the gating discipline.
- **Verification receipts** (CLAUDE.md) are required at phase exit and at every step that writes to production data. Include SHA256 hashes for source input files (the convention from Phase 2+).
- **Golden school** (Fairhaven) must pass field-by-field verification after any data change. See `tests/golden_schools.yaml` for expected values. If Fairhaven is wrong, stop.
- **Build log** updates expected at end-of-session for substantive work, per the convention established 2026-05-08. Use `## YYYY-MM-DD — <title>` header style.
