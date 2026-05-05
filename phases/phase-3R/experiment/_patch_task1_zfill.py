"""
_patch_task1_zfill.py — Fix the Task 1 graduation-rate join bug.

PURPOSE: Re-ingest 76iv-8ed4 with zfill(5) on the source `districtcode`. The
         original Task 1 ingestion missed ~170 source rows whose districtcode
         was 4-char (e.g. '3017' for Kennewick) because the experiment db's
         `metadata.ospi_district_code` is uniformly 5-char zero-padded.
         Verified 2026-05-04 against three flagship HS schools (Kennewick,
         Camas, Hanford) which all have rich source data but lost the join.
GUARD:   Refuses to write to any database whose name does not contain
         "experiment". $set on `graduation_rate.*` and the
         `patched_at` provenance field only — every other field is untouched.
IDEMPOTENT: Rerunning produces identical final state. Field-level $set only.
"""

import datetime as dt
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from statistics import mean, median

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient, UpdateOne

# ---------------------------------------------------------------------------
# Logging — timestamped file in logs/, complete English sentences.
# ---------------------------------------------------------------------------
TS = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = "/Users/oriandaleigh/school-daylight/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"phase3r_task1_zfill_patch_{TS}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("p3r_zfill")

NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
OUT_DIR = "/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment"

# ---------------------------------------------------------------------------
# Connect — experiment db only.
# ---------------------------------------------------------------------------
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client.get_default_database()
assert "experiment" in db.name, \
    f"Refusing to write — '{db.name}' is not an experiment db."
log.info(f"Connected to '{db.name}'.")

doc_count = db["schools"].count_documents({})
log.info(f"Document count: {doc_count}.")

# ---------------------------------------------------------------------------
# Pull the same projected fields as the original Task 1 run.
# ---------------------------------------------------------------------------
PROJ = {
    "_id": 1, "name": 1, "is_charter": 1, "school_type": 1,
    "level": 1, "derived.level_group": 1,
    "grade_span.low": 1, "grade_span.high": 1,
    "metadata.ospi_district_code": 1, "metadata.ospi_school_code": 1,
    "graduation_rate.cohort_4yr": 1, "graduation_rate.cohort_5yr": 1,
    "graduation_rate.metadata.not_applicable_reason": 1,
    "address.city": 1, "district.name": 1,
    "enrollment.total": 1,
    "census_acs._meta.unmatched_reason": 1,
}
schools = list(db["schools"].find({}, PROJ))
log.info(f"Loaded {len(schools)} school docs.")

def is_high_school(d):
    lg = (d.get("derived") or {}).get("level_group")
    gh = (d.get("grade_span") or {}).get("high")
    return lg == "High" or gh == "12"

def to_float(v):
    if v is None: return None
    s = str(v).strip()
    if s == "" or s.upper() == "NULL": return None
    s = s.rstrip("%")
    try: return float(s)
    except ValueError: return None

# ---------------------------------------------------------------------------
# Capture pre-patch state for the impact report.
# ---------------------------------------------------------------------------
pre_patch_with_4yr = sum(1 for d in schools
                         if (d.get("graduation_rate") or {}).get("cohort_4yr") is not None)
pre_patch_with_5yr = sum(1 for d in schools
                         if (d.get("graduation_rate") or {}).get("cohort_5yr") is not None)
pre_patch_hs_with_data = sum(
    1 for d in schools
    if is_high_school(d) and (
        (d.get("graduation_rate") or {}).get("cohort_4yr") is not None or
        (d.get("graduation_rate") or {}).get("cohort_5yr") is not None))
pre_patch_hs_no_data = sum(
    1 for d in schools
    if is_high_school(d) and
        (d.get("graduation_rate") or {}).get("cohort_4yr") is None and
        (d.get("graduation_rate") or {}).get("cohort_5yr") is None and
        (((d.get("graduation_rate") or {}).get("metadata") or {}).get("not_applicable_reason") is None))
log.info(f"Pre-patch: HS with at least one cohort rate = {pre_patch_hs_with_data}, "
         f"HS with no grad data = {pre_patch_hs_no_data}")

# ---------------------------------------------------------------------------
# Re-fetch source with the same filter and build the corrected join map.
# ---------------------------------------------------------------------------
log.info("Re-fetching 76iv-8ed4 source ...")
GRAD_BASE = "https://data.wa.gov/resource/76iv-8ed4.json"
all_rows = []
offset = 0
while True:
    qp = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in {
        "organizationlevel": "School",
        "schoolyear": "2023-24",
        "studentgroup": "All Students",
    }.items())
    url = f"{GRAD_BASE}?{qp}&$limit=10000&$offset={offset}"
    req = urllib.request.Request(url, headers={"User-Agent":
                                  "school-daylight-research/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = json.loads(r.read())
    if not rows: break
    all_rows.extend(rows)
    if len(rows) < 10000: break
    offset += 10000
log.info(f"Fetched {len(all_rows)} graduation source rows.")

# Build OSPI key map from db (same as before — uniformly 5-char dist, 4-char school)
def ospi_key(doc):
    md = doc.get("metadata", {}) or {}
    dc = md.get("ospi_district_code")
    sc = md.get("ospi_school_code")
    if dc and sc:
        return (dc.strip(), sc.strip())
    return None

ospi_to_id = {}
for d in schools:
    k = ospi_key(d)
    if k: ospi_to_id[k] = d["_id"]
log.info(f"DB OSPI key map size: {len(ospi_to_id)}.")

# THE FIX: zfill(5) on src districtcode before building the join key.
grad_by_key = defaultdict(dict)
unjoined_rows = 0
zfill_applied = 0  # count of rows whose key needed padding to match
for row in all_rows:
    raw_dc = (row.get("districtcode") or "").strip()
    # 76iv-8ed4 publishes districtcode as variable-width (4 or 5 chars depending
    # on district). The experiment db's metadata.ospi_district_code is always
    # 5-char zero-padded. Pad src to match. Verified 2026-05-04: 126/821 src
    # district codes are 4-char and were silently failing the join.
    dc = raw_dc.zfill(5)
    if len(raw_dc) != len(dc):
        zfill_applied += 1
    sc = (row.get("schoolcode") or "").strip()
    cohort = (row.get("cohort") or "").strip()
    rate = to_float(row.get("graduationrate"))
    if rate is not None and rate > 1.0:
        rate = rate / 100.0  # defensive
    if cohort == "Four Year":
        grad_by_key[(dc, sc)]["4yr"] = rate
    elif cohort == "Five Year":
        grad_by_key[(dc, sc)]["5yr"] = rate
    if (dc, sc) not in ospi_to_id:
        unjoined_rows += 1
log.info(f"Source rows with zfill-padding applied: {zfill_applied}")
log.info(f"Source-row keys joined: {len(grad_by_key)} unique (district, school).")
log.info(f"Source rows still unmatched after fix: {unjoined_rows}")

# ---------------------------------------------------------------------------
# Rebuild graduation_rate payload for every school, $set in bulk.
# ---------------------------------------------------------------------------
ops = []
hs_count = 0
hs_with_data = 0
non_hs_count = 0
v4_vals = []
v5_vals = []
newly_populated_ids = []  # schools that gained data this run
lost_data_ids = []        # safety check: should be empty

for d in schools:
    nid = d["_id"]
    is_hs = is_high_school(d)
    prev = d.get("graduation_rate") or {}
    prev_4 = prev.get("cohort_4yr")
    prev_5 = prev.get("cohort_5yr")
    prev_had_data = (prev_4 is not None or prev_5 is not None)

    if not is_hs:
        payload = {
            "cohort_4yr": None,
            "cohort_5yr": None,
            "metadata": {
                "source": "data.wa.gov 76iv-8ed4",
                "dataset_year": "2023-24",
                "fetch_timestamp": NOW_ISO,
                "patched_at": NOW_ISO,
                "patch_note": "zfill(5) on src districtcode",
                "not_applicable_reason": "grade_span_not_high_school",
            },
        }
        non_hs_count += 1
    else:
        hs_count += 1
        k = ospi_key(d)
        rates = grad_by_key.get(k, {})
        v4 = rates.get("4yr")
        v5 = rates.get("5yr")
        if v4 is not None or v5 is not None:
            hs_with_data += 1
            if v4 is not None: v4_vals.append(v4)
            if v5 is not None: v5_vals.append(v5)
        new_had_data = (v4 is not None or v5 is not None)
        if new_had_data and not prev_had_data:
            newly_populated_ids.append(nid)
        if prev_had_data and not new_had_data:
            lost_data_ids.append(nid)
        payload = {
            "cohort_4yr": v4,
            "cohort_5yr": v5,
            "metadata": {
                "source": "data.wa.gov 76iv-8ed4",
                "dataset_year": "2023-24",
                "fetch_timestamp": NOW_ISO,
                "patched_at": NOW_ISO,
                "patch_note": "zfill(5) on src districtcode",
                "not_applicable_reason": None,
            },
        }
    ops.append(UpdateOne(
        {"_id": nid},
        {"$set": {
            "graduation_rate": payload,
            "metadata.phase_3r_dataset_versions.graduation_rate.patched_at": NOW_ISO,
            "metadata.phase_3r_dataset_versions.graduation_rate.patch_note":
                "zfill(5) on src districtcode",
        }}))

log.info(f"Post-patch counts (in-memory): HS-eligible={hs_count}, "
         f"HS with cohort rate={hs_with_data}, non-HS={non_hs_count}")
log.info(f"Schools that GAINED data via fix: {len(newly_populated_ids)}")
if lost_data_ids:
    log.error(f"Schools that LOST data after patch: {len(lost_data_ids)} — "
              f"this should be zero. Sample: {lost_data_ids[:5]}")

# ---------------------------------------------------------------------------
# Sanity check: confirm Kennewick / Camas / Hanford resolve before writing.
# ---------------------------------------------------------------------------
spot_names = {"Kennewick High School", "Camas High School", "Hanford High School"}
spot_results = {}
for d in schools:
    if d.get("name") in spot_names:
        k = ospi_key(d)
        rates = grad_by_key.get(k, {})
        spot_results[d.get("name")] = (k, rates)
log.info("Spot check (pre-write):")
for name, (k, rates) in spot_results.items():
    log.info(f"  {name}: key={k}  rates={rates}")
if not all((r["4yr"] is not None) for _, r in spot_results.values()):
    log.error("ABORT: at least one flagship spot-check school still has null 4yr "
              "after the fix. Investigate before any write.")
    raise SystemExit(2)

# ---------------------------------------------------------------------------
# Final guard, then bulk write in chunks of 500.
# ---------------------------------------------------------------------------
assert "experiment" in db.name
log.info(f"Writing {len(ops)} bulk_write ops in chunks of 500 ...")
total_modified = 0
chunk = 500
for i in range(0, len(ops), chunk):
    res = db["schools"].bulk_write(ops[i:i+chunk], ordered=False)
    total_modified += res.modified_count
    log.info(f"  batch {i//chunk+1}: modified={res.modified_count}")
log.info(f"Total modified: {total_modified}")

# ---------------------------------------------------------------------------
# Post-fix 432 diagnostic.
# ---------------------------------------------------------------------------
log.info("=== Post-fix 432 diagnostic ===")
post_docs = list(db["schools"].find(
    {"graduation_rate.cohort_4yr": None,
     "graduation_rate.cohort_5yr": None,
     "graduation_rate.metadata.not_applicable_reason": None},
    {"_id":1,"name":1,"is_charter":1,"school_type":1,
     "derived.level_group":1,"district.name":1,
     "address.city":1,"enrollment.total":1,
     "metadata.ospi_school_code":1,
     "census_acs._meta.unmatched_reason":1}))
log.info(f"Post-fix HS-eligible-with-no-grad-data count: {len(post_docs)}")

def classify_flag(d):
    name = (d.get("name") or "").lower()
    if d.get("is_charter"): return "charter"
    sk = (((d.get("census_acs") or {}).get("_meta") or {}).get("unmatched_reason"))
    if sk == "institutional_facility_not_comparable":
        return "institutional (juvenile detention / youth services)"
    if sk == "regional_alternative_program_not_comparable":
        return "regional alt / reengagement (Phase 3R SKIP)"
    if sk == "statewide_specialty_school_not_comparable":
        return "statewide specialty (Phase 3R SKIP)"
    if sk == "tribal_community_context_not_capturable_v1":
        return "tribal community (Phase 3R SKIP)"
    if "virtual" in name or "online" in name or "digital" in name:
        return "virtual/online (by name)"
    if "homeschool" in name or "home school" in name:
        return "homeschool partnership"
    if "open doors" in name or "reengagement" in name or "re-engagement" in name:
        return "reengagement (by name)"
    st = d.get("school_type") or "(unknown)"
    if st == "Alternative School": return "Alternative School (CCD)"
    if st == "Special Education School": return "Special Education School (CCD)"
    if st == "Career and Technical School": return "Career and Technical School (CCD)"
    return "Regular School (CCD)"

post_by_level = Counter((d.get("derived") or {}).get("level_group") or "(unknown)"
                         for d in post_docs)
post_by_flag = Counter(classify_flag(d) for d in post_docs)

log.info(f"Post-fix breakdown by level_group: {dict(post_by_level)}")
log.info(f"Post-fix breakdown by flag: {dict(post_by_flag)}")

# Persist a one-off post-fix summary alongside the prior CSV
post_csv = os.path.join(OUT_DIR, "hs_no_grad_data_postfix.csv")
import csv
post_docs_sorted = sorted(post_docs,
                          key=lambda d: ((d.get("district") or {}).get("name") or "",
                                         d.get("name") or ""))
with open(post_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["school_name","district","city","level_group",
                "school_type_or_flag","ospi_school_code","nces_id","enrollment_total"])
    for d in post_docs_sorted:
        w.writerow([
            d.get("name") or "",
            (d.get("district") or {}).get("name") or "",
            (d.get("address") or {}).get("city") or "",
            (d.get("derived") or {}).get("level_group") or "",
            classify_flag(d),
            (d.get("metadata") or {}).get("ospi_school_code") or "",
            d["_id"],
            (d.get("enrollment") or {}).get("total") if d.get("enrollment") else "",
        ])
log.info(f"Wrote post-fix CSV: {post_csv} ({len(post_docs_sorted)} rows)")

# Spot-check the three flagships post-write
log.info("=== Post-write spot check (flagships) ===")
for nid_name in [("530393000605","Kennewick High School"),
                  ("530081003152","Camas High School"),
                  ("530732001095","Hanford High School")]:
    nid, name = nid_name
    d = db["schools"].find_one({"_id": nid},
                                {"graduation_rate.cohort_4yr":1,
                                 "graduation_rate.cohort_5yr":1,
                                 "graduation_rate.metadata.patched_at":1})
    g = d.get("graduation_rate") or {}
    log.info(f"  {name} ({nid}): 4yr={g.get('cohort_4yr')} "
             f"5yr={g.get('cohort_5yr')} "
             f"patched_at={(g.get('metadata') or {}).get('patched_at')}")

client.close()
print(f"\nDONE. Schools that gained data: {len(newly_populated_ids)}. "
      f"Post-fix HS-no-grad: {len(post_docs)} (was {pre_patch_hs_no_data}).")
print(f"CSV: {post_csv}")
print(f"Log: {LOG_PATH}")
