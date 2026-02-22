"""
run_pipeline.py — Run all pipeline steps in order.

Supports running all steps (default) or a single step with --step N.

Usage:
    python pipeline/run_pipeline.py           # Run all steps 01-10
    python pipeline/run_pipeline.py --step 05  # Run only step 05
"""

import os
import sys
import argparse
import importlib
import traceback
import time

sys.path.insert(0, os.path.dirname(__file__))
from helpers import setup_logging


# Pipeline steps in order — each entry is (module_name, description)
STEPS = [
    ("01_build_spine", "Build CCD spine from directory data"),
    ("02_load_enrollment", "Load CCD enrollment data"),
    ("03_load_ospi_enrollment", "Load OSPI enrollment demographics"),
    ("04_load_ospi_academics", "Load OSPI academics (assessment, growth, attendance)"),
    ("05_load_ospi_discipline", "Load OSPI discipline rates"),
    ("06_load_ospi_finance", "Load OSPI per-pupil expenditure"),
    ("07_load_crdc", "Load CRDC data from 13 files"),
    ("08_finalize", "Finalize metadata and compute join status"),
    ("09_write_to_atlas", "Write all documents to MongoDB Atlas"),
    ("10_verify", "Run verification checks and generate receipt"),
    ("11_load_crdc_enrollment", "Load CRDC enrollment by race for disparity ratios"),
    ("12_compute_ratios", "Compute derived ratios (S-T, counselor, absenteeism, disparity)"),
    ("13_assign_peer_groups", "Assign peer cohorts (level + enrollment + FRL bands)"),
    ("14_compute_percentiles", "Compute percentile ranks for 8 metrics"),
    ("15_regression_and_flags", "Run performance regression and apply climate/equity flags"),
    ("16_write_and_verify", "Write Phase 3 data to Atlas and verify"),
]


def run_step(module_name, description, logger):
    """Import and run a single pipeline step."""
    logger.info(f"--- Running {module_name}: {description} ---")
    start = time.time()

    try:
        # Import the module (or reload if already imported)
        module = importlib.import_module(module_name)
        module.main()
        elapsed = time.time() - start
        logger.info(f"--- {module_name} completed in {elapsed:.1f}s ---")
        return True
    except SystemExit as e:
        # Steps call sys.exit(1) on failure — catch it here
        if e.code != 0:
            elapsed = time.time() - start
            logger.error(
                f"--- {module_name} FAILED after {elapsed:.1f}s ---\n"
                f"Step {module_name} ({description}) exited with code {e.code}.\n"
                f"Check the log file for {module_name} for details.\n"
                f"To re-run from this step: python pipeline/run_pipeline.py --step {module_name.split('_')[0]}"
            )
            return False
        return True
    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            f"--- {module_name} FAILED after {elapsed:.1f}s ---\n"
            f"Error: {e}\n"
            f"Traceback:\n{traceback.format_exc()}\n"
            f"What to try:\n"
            f"  1. Read the error message above — it usually says what went wrong.\n"
            f"  2. Check the step's log file in logs/ for more details.\n"
            f"  3. Fix the issue and re-run: python pipeline/run_pipeline.py --step {module_name.split('_')[0]}"
        )
        return False


def main():
    parser = argparse.ArgumentParser(description="Run the School Daylight ETL pipeline.")
    parser.add_argument(
        "--step", type=str, default=None,
        help="Run a single step (e.g., --step 05 or --step 01)"
    )
    args = parser.parse_args()

    logger = setup_logging("run_pipeline")

    if args.step:
        # Run a single step
        step_num = args.step.zfill(2)
        found = False
        for module_name, description in STEPS:
            if module_name.startswith(step_num):
                found = True
                success = run_step(module_name, description, logger)
                if not success:
                    sys.exit(1)
                break
        if not found:
            logger.error(
                f"Step '{args.step}' not found. Valid steps: "
                f"{', '.join(m.split('_')[0] for m, _ in STEPS)}"
            )
            sys.exit(1)
    else:
        # Run all steps
        logger.info(f"Running full pipeline ({len(STEPS)} steps).")
        total_start = time.time()

        for module_name, description in STEPS:
            success = run_step(module_name, description, logger)
            if not success:
                logger.error(
                    f"Pipeline stopped at {module_name}. "
                    f"Fix the issue and re-run from this step with: "
                    f"python pipeline/run_pipeline.py --step {module_name.split('_')[0]}"
                )
                sys.exit(1)

        total_elapsed = time.time() - total_start
        logger.info(f"Full pipeline completed in {total_elapsed:.1f}s.")


if __name__ == "__main__":
    main()
