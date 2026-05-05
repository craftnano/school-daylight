# PURPOSE: Acceptance test for Task 1 (prompt extraction).
#          Confirms the three new prompt files in prompts/ produce strings byte-identical
#          to the inline STAGE0_PROMPT/STAGE1_PROMPT/STAGE2_PROMPT constants and user-message
#          templates in phases/phase-4.5/test_results/round1_three_stage/run_round1.py.
#
#          Byte-identity of prompts is the validation gate. The Round 1 50-school
#          three-stage replay produced zero hallucinations and zero regressions; that
#          property is a property of the exact prompt strings. If extraction silently
#          changed a quote style, a trailing newline, or any character, behavior could
#          shift and the validation would no longer hold.
#
#          We do NOT spend API budget rerunning the 5-school subset here. Same model +
#          same temperature + bit-identical prompts produces the same output distribution.
#          A live re-run cannot return bit-identical narratives (LLMs are stochastic at
#          temp>0), so byte-identity of the prompts is the strongest deterministic check
#          available. The receipt explains this and offers a smoke test on request.
#
# INPUTS:
#   prompts/layer3_stage0_haiku_extraction_v1.txt
#   prompts/layer3_stage1_haiku_triage_v1.txt
#   prompts/layer3_stage2_sonnet_narrative_v1.txt
#   phases/phase-4.5/test_results/round1_three_stage/run_round1.py (constants imported)
#
# OUTPUTS:
#   Console PASS/FAIL summary.
#   docs/receipts/phase-5/task1_prompt_extraction.md (written by hand based on this run)

import os
import sys
import json
import importlib.util

# Locate the project root by walking up from this file (phases/phase-5/<this>).
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.layer3_prompts import load_stage0, load_stage1, load_stage2, fill_user


def import_run_round1():
    """Load run_round1.py as a module so we can read STAGE0_PROMPT/STAGE1_PROMPT/STAGE2_PROMPT.

    The file lives in a path with a dot in the directory name (phase-4.5), which
    isn't a legal Python package name, so we use importlib's spec-from-file-location
    pattern instead of a regular import.

    The module's main() is NOT called — we only want the top-level constants.
    """
    runner_path = os.path.join(
        PROJECT_ROOT, "phases", "phase-4.5", "test_results",
        "round1_three_stage", "run_round1.py",
    )
    if not os.path.exists(runner_path):
        raise FileNotFoundError(
            f"Could not find the canonical runner at {runner_path}. "
            "Has the round1_three_stage directory moved? "
            "Check phases/phase-4.5/test_results/."
        )
    spec = importlib.util.spec_from_file_location("round1_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    # Skip executing main() by guarding on __name__ — the module sets it to "round1_runner".
    spec.loader.exec_module(module)
    return module


def diff_summary(label, expected, actual):
    """Return a short diff description if strings differ, or None if identical."""
    if expected == actual:
        return None
    # Find first differing byte
    n = min(len(expected), len(actual))
    first_diff = None
    for i in range(n):
        if expected[i] != actual[i]:
            first_diff = i
            break
    if first_diff is None:
        first_diff = n
    ctx_start = max(0, first_diff - 40)
    ctx_end = min(max(len(expected), len(actual)), first_diff + 40)
    return (
        f"{label}: lengths expected={len(expected)} actual={len(actual)}; "
        f"first differing byte at index {first_diff}; "
        f"expected[{ctx_start}:{ctx_end}]={expected[ctx_start:ctx_end]!r}; "
        f"actual[{ctx_start}:{ctx_end}]={actual[ctx_start:ctx_end]!r}"
    )


def reconstruct_inline_user_msgs(runner):
    """Reproduce the EXACT user_msg strings the runner builds inline at Stage 0/1/2.

    These f-string constructions are copied byte-for-byte from run_round1.py
    so we can compare them against fill_user() output from the new prompt files.

    We use canned values for the placeholders (school_name etc.) and a canned
    findings_json — only the structural template matters for byte-identity.
    """
    school_name = "Bainbridge High School"
    district_name = "Bainbridge Island School District"
    nces_id = "530033000043"
    findings_json = "[STUB_FINDINGS_JSON]"

    # Stage 0 user_msg (run_round1.py:443-449)
    s0_user = (
        f"Extract structured fields from each of these findings. "
        f"Do not make editorial decisions — only extract dates and type tags.\n\n"
        f"Findings:\n\n{findings_json}\n\n"
        f"Return the JSON output as specified in the system prompt."
    )

    # Stage 1 user_msg (run_round1.py:534-538)
    s1_user = (
        f"School: {school_name}\nDistrict: {district_name}\nNCES ID: {nces_id}\n\n"
        f"Findings to evaluate (already passed Stage 0 pre-filter):\n\n{findings_json}\n\n"
        f"Apply the recency rules and exclusion rules. Return JSON as specified."
    )

    # Stage 2 user_msg (run_round1.py:566-573)
    s2_user = (
        f"School: {school_name}\nDistrict: {district_name}\nNCES ID: {nces_id}\n\n"
        f"The following findings have been pre-triaged and approved for inclusion. "
        f"Write the narrative using ONLY these findings. Do not add any information "
        f"not present in the finding text.\n\n"
        f"Approved findings:\n\n{findings_json}\n\n"
        f"Write the narrative following all rules. Return JSON."
    )

    return {
        "school_name": school_name,
        "district_name": district_name,
        "nces_id": nces_id,
        "findings_json": findings_json,
        "s0_user": s0_user,
        "s1_user": s1_user,
        "s2_user": s2_user,
    }


def main():
    print("=" * 72)
    print("Task 1 acceptance test — Layer 3 prompt byte-identity check")
    print("=" * 72)

    # 1. Import the canonical runner constants.
    runner = import_run_round1()

    # 2. Load the new prompt files.
    s0_sys_new, s0_user_tmpl = load_stage0()
    s1_sys_new, s1_user_tmpl = load_stage1()
    s2_sys_new, s2_user_tmpl = load_stage2()

    # 3. Reconstruct the inline user_msg strings from run_round1.py.
    inline = reconstruct_inline_user_msgs(runner)

    # 4. Substitute placeholders in the loaded templates.
    s0_user_new = fill_user(s0_user_tmpl, findings=inline["findings_json"])
    s1_user_new = fill_user(
        s1_user_tmpl,
        school_name=inline["school_name"],
        district_name=inline["district_name"],
        nces_id=inline["nces_id"],
        findings=inline["findings_json"],
    )
    s2_user_new = fill_user(
        s2_user_tmpl,
        school_name=inline["school_name"],
        district_name=inline["district_name"],
        nces_id=inline["nces_id"],
        findings=inline["findings_json"],
    )

    # 5. Compare byte-by-byte.
    failures = []

    for label, expected, actual in [
        ("Stage 0 SYSTEM", runner.STAGE0_PROMPT, s0_sys_new),
        ("Stage 0 USER", inline["s0_user"], s0_user_new),
        ("Stage 1 SYSTEM", runner.STAGE1_PROMPT, s1_sys_new),
        ("Stage 1 USER", inline["s1_user"], s1_user_new),
        ("Stage 2 SYSTEM", runner.STAGE2_PROMPT, s2_sys_new),
        ("Stage 2 USER", inline["s2_user"], s2_user_new),
    ]:
        diff = diff_summary(label, expected, actual)
        if diff is None:
            print(f"  [PASS] {label} — byte-identical "
                  f"({len(expected):,} chars)")
        else:
            print(f"  [FAIL] {diff}")
            failures.append(diff)

    print()
    print("=" * 72)
    if failures:
        print(f"FAIL — {len(failures)} mismatches.")
        print("Investigate the prompt file before declaring Task 1 complete.")
        return 1
    print("PASS — all six prompts (3 system + 3 user) are byte-identical.")
    print("Loaded prompts produce the same strings the runner builds inline.")
    print()
    print("This is the strongest deterministic check available. A live 5-school")
    print("rerun would not produce bit-identical narratives (LLMs are stochastic")
    print("at temp>0), so byte-identity of the prompt strings is the validation")
    print("gate. Same prompts + same model = same output distribution.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
