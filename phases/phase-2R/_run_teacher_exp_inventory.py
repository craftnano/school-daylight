"""
_run_teacher_exp_inventory.py — Phase 2R audit diagnostic.

PURPOSE: Read-only side-by-side inventory of teacher_experience across
         both MongoDB databases for Fairhaven plus 4 spot-check schools
         spanning levels and regions. Also emits an orientation preamble
         for Fairhaven (peer_match, academic_flag, layer3_narrative,
         metadata.dataset_version presence). Prototype that established
         the three-section format (MongoDB / source / pipeline filter)
         before _run_full_inventory.py scaled it to the remaining 16
         variables.
INPUTS:  config.MONGO_URI, config.MONGO_URI_EXPERIMENT (read).
OUTPUTS: stdout only.
READ-ONLY: Yes.
SAMPLE SCHOOLS: 530042000104 Fairhaven Middle (Bellingham/Whatcom, NW WA);
                530423000670 Juanita HS (Kirkland/King, W WA);
                530927001579 Lewis and Clark HS (Spokane, E WA);
                530393000610 Washington Elementary (Mead/Spokane Co, E WA);
                530000102795 Thunder Mountain Middle (district 17216).
"""

import json
import sys

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

sys.path.insert(0, "/Users/oriandaleigh/school-daylight")
import config
from pymongo import MongoClient

# Five schools spanning levels and regions. Fairhaven first; the rest chosen
# from project artifacts (api_ingestion_2026-05-04.md validation table and
# sandbox_setup.md spot-checks) to ensure presence is guaranteed, with the
# four chosen for level + WA-region diversity.
SAMPLE = [
    "530042000104",  # Fairhaven Middle (Bellingham / Whatcom, NW WA) — golden
    "530423000670",  # Juanita HS (Kirkland / King, W WA Puget Sound metro)
    "530927001579",  # Lewis and Clark HS (Spokane / Spokane, E WA)
    "530393000610",  # Washington Elementary (Mead / Spokane Co, E WA)
    "530000102795",  # Thunder Mountain Middle (district reported in metadata)
]

FAIRHAVEN = "530042000104"


def pretty(v, indent=4):
    return json.dumps(v, indent=indent, default=str, sort_keys=True)


def open_db(uri, db_name):
    return MongoClient(uri, serverSelectionTimeoutMS=15000)[db_name]


def get_path(doc, dotted):
    if doc is None:
        return ("absent", None)
    parts = dotted.split(".")
    cur = doc
    for i, p in enumerate(parts):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return ("absent", None)
    return ("present", cur)


def compare(a_status, a_val, b_status, b_val):
    if a_status == "absent" and b_status == "absent":
        return "both absent"
    if a_status == "absent":
        return "absent in schooldaylight, present in schooldaylight_experiment"
    if b_status == "absent":
        return "present in schooldaylight, absent in schooldaylight_experiment"
    if a_val == b_val:
        return "same"
    return "different"


db_hist = open_db(config.MONGO_URI, config.DB_NAME)
db_exp = open_db(config.MONGO_URI_EXPERIMENT, config.DB_NAME_EXPERIMENT)

print("=" * 78)
print("ORIENTATION PREAMBLE — Fairhaven (_id=530042000104)")
print("=" * 78)

fair_hist = db_hist["schools"].find_one({"_id": FAIRHAVEN})
fair_exp = db_exp["schools"].find_one({"_id": FAIRHAVEN})


def report_orientation(label, doc):
    print(f"\n--- {label} ---")
    if doc is None:
        print("DOCUMENT NOT PRESENT")
        return

    for dotted in ("metadata.dataset_version",
                   "metadata.load_timestamp",
                   "metadata.phase_3r_ingestion_timestamp"):
        status, val = get_path(doc, dotted)
        if status == "absent":
            print(f"{dotted}: ABSENT")
        else:
            print(f"{dotted}: {val!r}")

    p3rdv = (doc.get("metadata") or {}).get("phase_3r_dataset_versions")
    if p3rdv is None:
        print("metadata.phase_3r_dataset_versions: ABSENT")
    else:
        print("metadata.phase_3r_dataset_versions: PRESENT, keys = "
              f"{sorted(p3rdv.keys())}")

    pm = doc.get("peer_match")
    if pm is None:
        print("peer_match: ABSENT")
    else:
        if isinstance(pm, dict):
            keys = sorted(pm.keys())
            cm = pm.get("cohort_members") or pm.get("members") or pm.get("cohort")
            n = len(cm) if isinstance(cm, list) else None
            print(f"peer_match: PRESENT — top-level keys={keys}, "
                  f"cohort_members list length={n}, status={pm.get('status')!r}")
        else:
            print(f"peer_match: PRESENT — non-dict type={type(pm).__name__}")

    for k in ("academic_flag", "academic_flags"):
        v = doc.get(k)
        print(f"{k}: {'ABSENT' if v is None else 'PRESENT'}")
    df = (doc.get("derived") or {}).get("flags") if isinstance(doc.get("derived"), dict) else None
    print(f"derived.flags: {'ABSENT' if df is None else f'PRESENT — keys={sorted(df.keys()) if isinstance(df, dict) else type(df).__name__}'}")

    ln = doc.get("layer3_narrative")
    if ln is None:
        print("layer3_narrative: ABSENT")
    elif isinstance(ln, str):
        print(f"layer3_narrative: PRESENT — string, length={len(ln)}")
    elif isinstance(ln, dict):
        print(f"layer3_narrative: PRESENT — dict, keys={sorted(ln.keys())}")
    else:
        print(f"layer3_narrative: PRESENT — type={type(ln).__name__}")


report_orientation("schooldaylight (historical)", fair_hist)
report_orientation("schooldaylight_experiment (operating)", fair_exp)


print("\n" + "=" * 78)
print("TASK 1 — teacher_experience side-by-side inventory")
print("=" * 78)

for nid in SAMPLE:
    print("\n" + "-" * 78)
    print(f"SCHOOL _id = {nid}")
    a = db_hist["schools"].find_one({"_id": nid},
                                     {"_id": 1, "name": 1,
                                      "metadata.ospi_district_code": 1,
                                      "derived.level_group": 1,
                                      "level": 1,
                                      "teacher_experience": 1,
                                      "metadata.phase_3r_dataset_versions.teacher_experience": 1,
                                      "metadata.dataset_version": 1,
                                      "metadata.load_timestamp": 1})
    b = db_exp["schools"].find_one({"_id": nid},
                                    {"_id": 1, "name": 1,
                                     "metadata.ospi_district_code": 1,
                                     "derived.level_group": 1,
                                     "level": 1,
                                     "teacher_experience": 1,
                                     "metadata.phase_3r_dataset_versions.teacher_experience": 1,
                                     "metadata.dataset_version": 1,
                                     "metadata.load_timestamp": 1})

    src = a if a is not None else b
    if src is not None:
        print(f"  name: {src.get('name')!r}")
        print(f"  level: {src.get('level')!r}  level_group: "
              f"{(src.get('derived') or {}).get('level_group')!r}  "
              f"ospi_district: {(src.get('metadata') or {}).get('ospi_district_code')!r}")

    a_status, a_te = get_path(a, "teacher_experience")
    b_status, b_te = get_path(b, "teacher_experience")

    print("\n  schooldaylight (historical):")
    if a_status == "absent":
        if a is None:
            print("    DOCUMENT NOT PRESENT (school missing from schooldaylight)")
        else:
            print("    teacher_experience: FIELD ABSENT")
    else:
        if a_te is None:
            print("    teacher_experience: null")
        else:
            print("    teacher_experience (literal):")
            print("      " + pretty(a_te, indent=6).replace("\n", "\n      "))

    print("\n  schooldaylight_experiment (operating):")
    if b_status == "absent":
        if b is None:
            print("    DOCUMENT NOT PRESENT (school missing from schooldaylight_experiment)")
        else:
            print("    teacher_experience: FIELD ABSENT")
    else:
        if b_te is None:
            print("    teacher_experience: null")
        else:
            print("    teacher_experience (literal):")
            print("      " + pretty(b_te, indent=6).replace("\n", "\n      "))

    print(f"\n  Comparison: {compare(a_status, a_te, b_status, b_te)}")

    a_v_status, a_v_val = get_path(a, "metadata.phase_3r_dataset_versions.teacher_experience")
    b_v_status, b_v_val = get_path(b, "metadata.phase_3r_dataset_versions.teacher_experience")
    print(f"  metadata.phase_3r_dataset_versions.teacher_experience:")
    print(f"    schooldaylight: {a_v_val if a_v_status == 'present' else 'ABSENT'}")
    print(f"    schooldaylight_experiment: {b_v_val if b_v_status == 'present' else 'ABSENT'}")
    print(f"    Comparison: {compare(a_v_status, a_v_val, b_v_status, b_v_val)}")

print("\nDONE.")
