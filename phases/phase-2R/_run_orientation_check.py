"""
_run_orientation_check.py — Phase 2R audit diagnostic preamble.

PURPOSE: Read-only orientation check across both MongoDB databases to
         resolve which one carries Phase 3R / Phase 5 artifacts. Reports
         presence/absence per database for peer_match, academic_flag,
         derived.flags, layer3_narrative, teacher_experience, plus the
         document-root vintage stamps (metadata.dataset_version,
         metadata.load_timestamp, metadata.phase_3r_*).
INPUTS:  config.MONGO_URI, config.MONGO_URI_EXPERIMENT (read).
OUTPUTS: stdout only.
READ-ONLY: Yes. No MongoDB writes, no filesystem writes.
FAILURE MODES: The FAIRHAVEN constant ("530219000370") is the incorrect
               NCESSCH from the audit prompt and returns "DOCUMENT NOT
               PRESENT" in both databases — that result was the audit
               finding that triggered _run_fairhaven_id_check.py. The
               canonical Fairhaven _id is "530042000104"
               (pipeline/helpers.py:FAIRHAVEN_NCESSCH). The wrong constant
               is preserved as a historical record of what was actually
               run on 2026-05-13.
"""

import sys

# DNS bypass — Phase 3R+ convention (local router DNS issue).
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

sys.path.insert(0, "/Users/oriandaleigh/school-daylight")
import config
from pymongo import MongoClient

FAIRHAVEN = "530219000370"

if not config.MONGO_URI or not config.MONGO_URI_EXPERIMENT:
    raise SystemExit(
        "Missing credential. config.MONGO_URI and/or "
        "config.MONGO_URI_EXPERIMENT is empty. This usually means: "
        "(1) .env is not present, or (2) one of the URI vars is not set. "
        "Add the missing variable to .env and rerun."
    )

PROJ = {
    "_id": 1,
    "name": 1,
    "metadata.dataset_version": 1,
    "metadata.load_timestamp": 1,
    "metadata.phase_3r_ingestion_timestamp": 1,
    "metadata.phase_3r_dataset_versions": 1,
    "peer_match": 1,
    "academic_flag": 1,
    "academic_flags": 1,
    "derived.flags": 1,
    "layer3_narrative": 1,
    "teacher_experience": 1,
}


def summarize(label, uri, db_name):
    print(f"\n=== {label} (db: {db_name}) ===")
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    coll = db["schools"]
    doc_count = coll.count_documents({})
    print(f"schools count: {doc_count}")
    d = coll.find_one({"_id": FAIRHAVEN}, PROJ)
    if d is None:
        print(f"Fairhaven ({FAIRHAVEN}): NOT PRESENT in this database.")
        client.close()
        return
    print(f"Fairhaven ({FAIRHAVEN}) name: {d.get('name')}")

    md = d.get("metadata") or {}
    print(f"metadata.dataset_version: {md.get('dataset_version')!r}")
    print(f"metadata.load_timestamp:  {md.get('load_timestamp')!r}")
    print(f"metadata.phase_3r_ingestion_timestamp: "
          f"{md.get('phase_3r_ingestion_timestamp')!r}")
    p3r = md.get("phase_3r_dataset_versions")
    if p3r is None:
        print("metadata.phase_3r_dataset_versions: ABSENT")
    else:
        print(f"metadata.phase_3r_dataset_versions present, keys: "
              f"{sorted(p3r.keys())}")

    pm = d.get("peer_match")
    if pm is None:
        print("peer_match: ABSENT")
    else:
        pm_keys = sorted(pm.keys()) if isinstance(pm, dict) else type(pm).__name__
        n_cohort = None
        if isinstance(pm, dict):
            cm = pm.get("cohort_members") or pm.get("members") or pm.get("cohort")
            if isinstance(cm, list):
                n_cohort = len(cm)
        print(f"peer_match: PRESENT, top-level keys={pm_keys}, "
              f"cohort_members list length={n_cohort}")

    af = d.get("academic_flag")
    afs = d.get("academic_flags")
    df = (d.get("derived") or {}).get("flags") if isinstance(d.get("derived"), dict) else None
    print(f"academic_flag: {'PRESENT' if af is not None else 'ABSENT'}")
    print(f"academic_flags: {'PRESENT' if afs is not None else 'ABSENT'}")
    print(f"derived.flags: {'PRESENT' if df is not None else 'ABSENT'}")

    ln = d.get("layer3_narrative")
    if ln is None:
        print("layer3_narrative: ABSENT")
    else:
        if isinstance(ln, str):
            print(f"layer3_narrative: PRESENT (string, length={len(ln)})")
        elif isinstance(ln, dict):
            print(f"layer3_narrative: PRESENT (dict, keys={sorted(ln.keys())})")
        else:
            print(f"layer3_narrative: PRESENT (type={type(ln).__name__})")

    te = d.get("teacher_experience")
    print(f"teacher_experience: {'PRESENT' if te is not None else 'ABSENT'}")

    client.close()


summarize("schooldaylight (historical / production-named)",
          config.MONGO_URI, config.DB_NAME)
summarize("schooldaylight_experiment (operating)",
          config.MONGO_URI_EXPERIMENT, config.DB_NAME_EXPERIMENT)

print("\nDONE.")
