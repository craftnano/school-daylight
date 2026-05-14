# Architecture Overview — Parking Note

**Status:** Parked for execution after Phase 2R completes. Drafted 2026-05-13 during Phase 2R scoping conversation.

**Purpose:** Capture the scope and reasoning for a future `docs/architecture.md` document. The Phase 2R audit and the academic_flag scoping work surfaced enough structural ambiguity in the codebase that a deliberate architecture pass is worth doing before academic_flag implementation begins.

## Why this is worth doing

The Phase 2R audit revealed multiple structural ambiguities that are individually small but collectively create real friction:

- Production-pipeline scripts live in `pipeline/` with numbered prefixes; Phase 3R scripts that produce live data live in `phases/phase-3R/experiment/`. The two are functionally equivalent but live in different places, with no documented convention for whether or when phase-experimental scripts get promoted to `pipeline/`.
- CLAUDE.md says "config over code" but K=20 (cohort size) and ≥15 (cohort-mean denominator rule) are hard-coded inline literals. Not parameterized anywhere.
- Schema fields are inconsistently nested: `enrollment.total` (flat-ish), `derived.race_pct_non_white` (one level under derived), `academics.assessment.ela_proficiency_pct` (three levels), `teacher_experience.average_years_derived` (compound name).
- Metadata lives in multiple places with overlapping purposes: `_meta` blocks per field, `metadata.dataset_version` at document root, `metadata.phase_3r_dataset_versions`, vintage stamps inside per-field blocks like `census_acs._meta.vintage`.
- The school document schema is implicit in the scripts that write to it. The audit had to reconstruct it by reading code.

Without an explicit architecture, the next phase (academic_flag implementation) will land somewhere by default rather than by design. Doing the overview before that work begins means academic_flag gets built into a clear structure.

## What the overview should cover

### 1. Directory layout and the compute-render-enrich split

The project has three functional layers that should be named explicitly:

- **Compute** — pipeline scripts that read sources and write to MongoDB
- **Enrich** — AI layer that reads MongoDB and writes narratives back (Layer 3)
- **Render** — code that reads MongoDB and produces parent-facing output (eventually Streamlit; currently not built)

Each layer lives in a specific directory. The overview maps directories to layers and names the conventions for what lives where.

### 2. Pipeline/ versus phases/phase-N/experiment/

The two directories serve different purposes today but the boundary is fuzzy. Either:

- Formalize as intentional pattern: phase-experimental scripts get promoted to `pipeline/` when stable, with a documented promotion criterion
- Recognize as technical debt: the experimental scripts that became operational (Phase 3R API ingestion, cohort computation) need to move to `pipeline/` as part of cleanup

Architecture overview names which path is being taken.

### 3. Schema as a first-class artifact

Right now the school document schema is reconstructed by reading scripts. The overview should include (or point to) a canonical schema reference document covering:

- Every field that exists in production
- Which script writes it
- Which downstream code reads it
- Its provenance pattern (file-sourced, API-no-cache, API-with-cache, derived)
- Its vintage policy category (similarity-vector, outcome, context, derived)

This becomes the document future sessions consult before adding new fields.

### 4. Schema naming conventions

Existing inconsistencies in nesting depth and naming style need a principled resolution. Either codify the current pattern as intentional or identify what to clean up. Academic_flag's eventual location in the schema (`academic_flag` vs `derived.academic_flag` vs `academic.flag`) is a question that needs a principled answer rather than a per-developer guess.

### 5. Configuration conventions

Where do thresholds, parameters, and tuning values live? The "config over code" principle in CLAUDE.md needs operationalizing:

- What categories of values belong in YAML (thresholds, suppression markers, group definitions)
- What stays in Python (algorithms, control flow, schema structure)
- Where the YAML files live (`config.py`, `cleaning_rules.yaml`, `flag_thresholds.yaml`, and any others)
- How configuration values are loaded and used at runtime

The K=20 and ≥15 hard-coding gets resolved as part of writing this section.

### 6. Metadata and provenance conventions

The Phase 2R vintage manifest establishes provenance patterns for ingestion. The architecture overview generalizes:

- What metadata lives at document root (`metadata.dataset_version`, `metadata.load_timestamp`, etc.)
- What metadata lives in per-field `_meta` blocks (vintage, source URL, fetch timestamp, filter parameters)
- How the vintage manifest relates to in-document metadata
- The API ingestion convention (every API-sourced variable carries endpoint, vintage, fetch_timestamp, source identifier, filter parameters)
- The file ingestion convention (source filename, SHA256, mtime, year string, year-from-column assertion where applicable)

### 7. Similarity vector, outcomes, and flags

The methodology brief distinguishes:

- **Similarity-vector variables** — used to compute peer cohorts; require vintage alignment within the vector
- **Outcome variables** — what gets flagged against cohorts; vintage policy is per-variable, most recent published
- **Flag fields** — categorical assignments derived from comparing outcomes against cohort statistics

The codebase doesn't yet mark these distinctions. The overview names them as a schema concept and identifies which fields belong to which category. This makes the per-variable vintage policy enforceable mechanically rather than by memory.

## Format and audience

Plain English. Readable by the builder (non-developer) and by future CC sessions. Cites code paths inline the way CC's audit reports do. Not formal UML, not just a directory tree — the *why* of where things live, not just the *what*.

Probably lives at `docs/architecture.md`. Probably 5-10 pages. Section structure roughly matches the seven sections above.

## Sequencing

Write after Phase 2R execution completes. Phase 2R itself will surface a few more architectural decisions:

- Where the database rename leaves metadata stamps
- What the vintage manifest's exact format looks like
- Where the manifest lives in the repo
- What happens to `phases/phase-3R/experiment/` scripts after Phase 2R rename consolidates the database

Those decisions land in the architecture overview as part of writing it.

Write before academic_flag implementation begins. The implementation work then uses the architecture overview as its design guide rather than building on assumed conventions.

## Working approach when this picks up

1. Advisor session: walk through the seven sections, decide what each says, identify any architectural decisions still open
2. CC drafts `docs/architecture.md` against the codebase, cross-referencing actual file paths and field names
3. Builder reviews, edits, approves
4. The schema reference document (Section 3) may be its own artifact (`docs/schema_reference.md`) referenced from the overview, depending on length

## Linked artifacts to consider folding in

- The Phase 2R vintage manifest (lives in the manifest's own location, referenced from architecture overview Section 6)
- CLAUDE.md (the architecture overview is consistent with CLAUDE.md; if they conflict, one of them needs updating)
- The `docs/conventions.md` and `docs/commands.md` files proposed during the CLAUDE.md slimming discussion (these may or may not get created; architecture overview can stand alone or reference them)
- The methodology brief's Section 2 (the similarity-vector vs outcome distinction in Section 7 of the overview should align with how the brief frames it)

## What this is not

- Not a refactor of the codebase. The overview documents what exists and names conventions for new work. It identifies technical debt but doesn't necessarily pay it down in one pass.
- Not a methodology document. It describes where methodology lives in the code, not what the methodology is.
- Not a guide to using the tool. It's an internal architecture document for the builder, advisors, and future CC sessions.
