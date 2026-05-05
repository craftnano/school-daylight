# PURPOSE: Layer 3 prompt loader for the three-stage web-context narrative pipeline.
#          Reads the versioned plaintext prompt files in prompts/ and returns
#          (system_prompt, user_template) pairs ready for placeholder substitution.
# INPUTS: prompts/layer3_stage0_haiku_extraction_v1.txt
#         prompts/layer3_stage1_haiku_triage_v1.txt
#         prompts/layer3_stage2_sonnet_narrative_v1.txt
# OUTPUTS: Python tuples (system, user_template). Callers run str.replace() on the
#          user template to fill {school_name}, {district_name}, {nces_id}, {findings}.
# JOIN KEYS: n/a
# SUPPRESSION HANDLING: n/a
# RECEIPT: docs/receipts/phase-5/task1_prompt_extraction.md
# FAILURE MODES:
#   - Prompt file missing → FileNotFoundError with a plain-English message naming the path.
#   - Section markers missing → ValueError naming which marker is absent.
#   - Two markers reversed → ValueError, since SYSTEM must precede USER.
#
# WHY str.replace AND NOT str.format:
#   The system prompts contain JSON examples with literal `{` and `}` characters.
#   str.format() would crash on these. str.replace() is forgiving and matches the
#   convention already used in pipeline/17_haiku_enrichment.py.

import os

# Section markers — must match the prompt files byte-for-byte.
SYSTEM_MARKER = "===SYSTEM==="
USER_MARKER = "===USER==="

# Canonical filenames. Anchored to PROJECT_ROOT/prompts/ so callers don't need to
# pass paths around.
STAGE0_FILE = "layer3_stage0_haiku_extraction_v1.txt"

# Stage 1: v2 promoted to canonical 2026-05-02 after the positive-content
# diagnostic showed the v1 line-37 categorical exclusion of awards / recognitions
# / programs filtered out 184 of 185 schools' positive findings — directly
# contradicting foundation.md's mission to "recognize real achievement."
# v1 stays in prompts/ as the historical record of what the production batch
# (1,862 narratives) was generated against.
STAGE1_FILE = "layer3_stage1_haiku_triage_v2.txt"
STAGE1_FILE_V1 = "layer3_stage1_haiku_triage_v1.txt"
STAGE1_FILE_V2 = "layer3_stage1_haiku_triage_v2.txt"

STAGE2_FILE = "layer3_stage2_sonnet_narrative_v1.txt"
STAGE2_FILE_V2 = "layer3_stage2_sonnet_narrative_v2.txt"
STAGE2_FILE_V3 = "layer3_stage2_sonnet_narrative_v3.txt"


def _prompts_dir():
    """Return the absolute path to the prompts/ directory.

    Resolves relative to this file's location so the loader works whether it is
    imported from pipeline/, phases/phase-5/, tests/, or anywhere else.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "prompts")


def load_prompt(filename):
    """Load a Layer 3 prompt file and split it into (system, user_template).

    Strips leading/trailing newlines from each section so the returned strings
    match the inline constants in run_round1.py byte-for-byte. Comment lines
    starting with '#' before the SYSTEM marker are metadata, not prompt content,
    and are discarded.
    """
    path = os.path.join(_prompts_dir(), filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Layer 3 prompt file not found at {path}. "
            "This usually means the file was moved or renamed. "
            "Confirm the prompts/ directory contains all three Layer 3 files: "
            f"{STAGE0_FILE}, {STAGE1_FILE}, {STAGE2_FILE}."
        )
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    sys_idx = text.find(SYSTEM_MARKER)
    usr_idx = text.find(USER_MARKER)
    if sys_idx == -1:
        raise ValueError(
            f"Prompt file {filename} is missing the {SYSTEM_MARKER} section marker. "
            "Each Layer 3 prompt file must contain ===SYSTEM=== and ===USER=== markers "
            "on their own lines, in that order."
        )
    if usr_idx == -1:
        raise ValueError(
            f"Prompt file {filename} is missing the {USER_MARKER} section marker. "
            "Each Layer 3 prompt file must contain ===SYSTEM=== and ===USER=== markers "
            "on their own lines, in that order."
        )
    if usr_idx < sys_idx:
        raise ValueError(
            f"Prompt file {filename} has {USER_MARKER} before {SYSTEM_MARKER}. "
            "The SYSTEM section must come first."
        )

    # Slice out the two sections. Skip the marker line (including its trailing newline).
    system_section = text[sys_idx + len(SYSTEM_MARKER):usr_idx]
    user_section = text[usr_idx + len(USER_MARKER):]

    # Strip exactly the leading and trailing newlines that the file format introduces
    # around section content. Preserves any internal whitespace.
    system_prompt = system_section.strip("\n")
    user_template = user_section.strip("\n")

    return system_prompt, user_template


def load_stage0():
    """Return (system_prompt, user_template) for Stage 0 Haiku extraction."""
    return load_prompt(STAGE0_FILE)


def load_stage1():
    """Return (system_prompt, user_template) for Stage 1 Haiku triage.

    Returns v2 as of 2026-05-02. v2 removed the categorical "awards, recognitions,
    and positive achievements: exclude" rule from v1 line 37 after a diagnostic
    showed the rule filtered out 184 of 185 schools' positive findings,
    contradicting foundation.md's mission to recognize real achievement. Routine
    leadership appointments, board governance, and policy announcements remain
    excluded.
    """
    return load_prompt(STAGE1_FILE)


def load_stage1_v1():
    """Return Stage 1 v1 — historical only.

    Kept for reproducing the original 2026-05-02 production batch outputs. Do
    not use for new generation work; use load_stage1() instead.
    """
    return load_prompt(STAGE1_FILE_V1)


def load_stage1_v2():
    """Alias for load_stage1() — preserved so existing callers (e.g. dry-run
    scripts that explicitly named v2) keep working. Functionally identical."""
    return load_prompt(STAGE1_FILE_V2)


def load_stage2():
    """Return (system_prompt, user_template) for Stage 2 Sonnet narrative (v1).

    v1 is the version validated in the Phase 4.5 50-school replay. Keep this as
    the default load function so the production runner stays bit-identical to
    the validated baseline. New rule revisions live in numbered v2/v3 files.
    """
    return load_prompt(STAGE2_FILE)


def load_stage2_v2():
    """Return (system_prompt, user_template) for Stage 2 Sonnet narrative v2.

    v2 adds Rules 15 (timeless past-tense), 16 (source-fidelity verbs), 17
    (grade-level redaction), and the per-paragraph citations format. v2 expects
    each finding in the input JSON to carry a `source_url` field — Stage 1 does
    not pass this through, so callers must enrich the Stage 1 included list
    with source URLs from MongoDB before sending the Stage 2 batch.
    """
    return load_prompt(STAGE2_FILE_V2)


def load_stage2_v3():
    """Return (system_prompt, user_template) for Stage 2 Sonnet narrative v3.

    v3 strengthens Rule 4 with explicit manner-of-death and location-of-death
    suppression and required phrasings. Same input contract as v2 (each finding
    must carry source_url, enriched at Stage 2 build time).
    """
    return load_prompt(STAGE2_FILE_V3)


def fill_user(template, **values):
    """Substitute named placeholders in a user template using str.replace.

    Example:
        sys, tmpl = load_stage1()
        user_msg = fill_user(tmpl,
                             school_name="Fairhaven Middle School",
                             district_name="Bellingham SD",
                             nces_id="530042000104",
                             findings=findings_json)

    Only the placeholders that appear in `values` are replaced. Extra keys are
    ignored. Missing keys leave the placeholder literal — callers should grep for
    leftover `{name}` strings if they want a strict mode.
    """
    result = template
    for key, val in values.items():
        result = result.replace("{" + key + "}", str(val))
    return result
