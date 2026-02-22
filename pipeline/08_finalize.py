"""
08_finalize.py — Add metadata and compute join status for every document.

PURPOSE: Add provenance metadata (dataset_version, load_timestamp, data_vintage)
         and compute join_status based on which data sources are present for
         each school.
INPUTS: data/schools_pipeline.json
OUTPUTS: Updates schools_pipeline.json with completed metadata section
JOIN KEYS: None (reads from accumulated document)
SUPPRESSION HANDLING: None
RECEIPT: phases/phase-2/receipt.md — metadata section
FAILURE MODES: None expected
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from helpers import (
    setup_logging, load_schools, save_schools, FAIRHAVEN_NCESSCH
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def finalize(logger):
    """Add metadata and join status to every school document."""

    schools = load_schools()

    timestamp = datetime.now(timezone.utc).isoformat()
    dataset_version = "2026-02-v1"

    # Data vintage — which year each source covers
    data_vintage = {
        "ccd_directory": "2023-24",
        "ccd_membership": "2023-24",
        "ospi_enrollment": "2023-24",
        "ospi_assessment": "2023-24",
        "ospi_growth": "2024-25",
        "ospi_sqss": "2024-25",
        "ospi_discipline": "2023-24",
        "ospi_ppe": "2023-24",
        "crdc": "2021-22",
    }

    # Counters for join status summary
    status_counts = {}

    for ncessch, doc in schools.items():
        # Add provenance metadata
        meta = doc.get("metadata", {})
        meta["dataset_version"] = dataset_version
        meta["load_timestamp"] = timestamp
        meta["data_vintage"] = data_vintage
        doc["metadata"] = meta

        # Compute join status based on which sections are present
        has_ospi = any(
            key in doc for key in ["demographics", "finance"]
        ) or "academics" in doc
        has_crdc = meta.get("crdc_combokey") is not None

        if has_ospi and has_crdc:
            join_status = "all_sources"
        elif has_ospi and not has_crdc:
            join_status = "missing_crdc"
        elif not has_ospi and has_crdc:
            join_status = "missing_ospi"
        else:
            join_status = "ccd_only"

        meta["join_status"] = join_status

        status_counts[join_status] = status_counts.get(join_status, 0) + 1

    save_schools(schools)

    # Log summary
    logger.info("Join status summary:")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  {status}: {count} schools")

    # Fairhaven check
    if FAIRHAVEN_NCESSCH in schools:
        fh_meta = schools[FAIRHAVEN_NCESSCH].get("metadata", {})
        logger.info(
            f"Fairhaven metadata: version={fh_meta.get('dataset_version')}, "
            f"join_status={fh_meta.get('join_status')}."
        )

    return True


def main():
    logger = setup_logging("08_finalize")
    logger.info("Step 08: Finalizing metadata and computing join status.")

    success = finalize(logger)

    if success:
        logger.info("Step 08 complete.")
    else:
        logger.error("Step 08 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
