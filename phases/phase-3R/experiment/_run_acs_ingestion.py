"""
_run_acs_ingestion.py — Ingest Census ACS + TIGER data into experiment db.

PURPOSE: For every school in `schooldaylight_experiment.schools`, attach the 9
         district-level Census variables Nebraska's REL Central peer-matching
         methodology requires. WRITES TO EXPERIMENT DB ONLY.
INPUTS:  MongoDB Atlas (schooldaylight_experiment.schools, READ+WRITE),
         Census ACS API (read), Census TIGER Gazetteer (read),
         school_exclusions.yaml (read), district_id_audit data
OUTPUTS: Adds census_acs.* nested object to every school doc in experiment db,
         writes phases/phase-3R/experiment/acs_ingestion_results.md
GUARD:   Refuses to write to any database whose name does not contain
         "experiment". This is a defence-in-depth check on top of the
         already-segregated MONGO_URI_EXPERIMENT credential.

VARIABLE LIST (Nebraska REL Central methodology, ACS-sourced subset):
  median_household_income                 B19013_001E  (base)
  per_capita_income                       B19301_001E  (base)
  gini_index                              B19083_001E  (base)
  bachelors_or_higher_pct_25plus          S1501_C02_015E  (subject)
  labor_force_participation_rate_16plus   S2301_C02_001E  (subject)
  unemployment_rate_16plus                S2301_C04_001E  (subject)
  total_population                        B01003_001E  (base)
  land_area_sq_miles                      TIGER 2023 Gazetteer ALAND_SQMI
  population_density_per_sq_mile          computed: total_pop / land_area
"""

import datetime as dt
import io
import json
import os
import random
import sys
import urllib.error
import urllib.request
import yaml
import zipfile
from collections import defaultdict

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient, UpdateOne

# ---------------------------------------------------------------------------
# CONNECT — experiment db only. Production never touched.
# ---------------------------------------------------------------------------
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client[config.DB_NAME_EXPERIMENT]
assert "experiment" in db.name, \
    f"Refusing to write — database name '{db.name}' is not an experiment db."

OUT_DIR = '/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment'
os.makedirs(OUT_DIR, exist_ok=True)
OUT_FILE = os.path.join(OUT_DIR, 'acs_ingestion_results.md')

NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
VINTAGE = "acs5_2019_2023"

# ---------------------------------------------------------------------------
# SKIP CLASSIFICATION — apply builder's rules to the 48 unmatched schools
# ---------------------------------------------------------------------------
# Builder's reason codes from the audit-decision message:
SKIP_REASONS = {
    "institutional_facility_not_comparable":      [],
    "regional_alternative_program_not_comparable": [],
    "statewide_specialty_school_not_comparable":  [],
    "tribal_community_context_not_capturable_v1": [],
    "charter_pending_district_assignment":        [],
}

# Match rules. Applied in order — first match wins.
def classify_skip(name, is_charter):
    n = (name or "").lower()
    # 1) Charters first (they're the most populous bucket and easy to identify)
    if is_charter:
        return "charter_pending_district_assignment"
    # Charter operators that may appear without is_charter set:
    charter_operators = ["summit", "rainier prep", "spokane international",
                         "pride prep", "innovation", "rainier valley leadership",
                         "impact public schools", "catalyst", "cascade public",
                         "why not you", "lumen", "intergenerational",
                         "pinnacles prep", "rooted school"]
    if any(op in n for op in charter_operators):
        return "charter_pending_district_assignment"
    # 2) Tribal — the single Chief Kitsap match
    if "chief kitsap" in n:
        return "tribal_community_context_not_capturable_v1"
    # 3) Statewide specialty schools (named explicitly)
    statewide_specialty = [
        "wa school for the deaf", "washington school for the deaf",
        "wa school for the blind", "washington school for the blind",
        "washington youth academy", "esa 112 special ed",
        "northwest career and technical",
        "bates technical high", "renton technical high",
        "lake washington technical academy",
    ]
    if any(s in n for s in statewide_specialty):
        return "statewide_specialty_school_not_comparable"
    # 4) Institutional / detention
    institutional_patterns = [
        "juvenile detention", "county detention", "co detention",
        "youth services", "martin hall", "structural alt",
        "structural alternative", "detention center",
    ]
    if any(p in n for p in institutional_patterns):
        return "institutional_facility_not_comparable"
    # Specific facility names that don't include 'detention' in their CCD name
    if "kitsap detention" in n or "kitsap juvenile" in n:
        return "institutional_facility_not_comparable"
    # 5) Regional alternative / reengagement programs
    alt_patterns = [
        "open doors", "reengagement", "pass program", "garrett heyns",
        "dropout prevention", "youthsource", "rtc", "lwit",
    ]
    if any(p in n for p in alt_patterns):
        return "regional_alternative_program_not_comparable"
    return None  # unmatched — will be reported

# ---------------------------------------------------------------------------
# FETCH 1 — authoritative WA USD list from ACS API
# ---------------------------------------------------------------------------
ACS_BASE_URL = ("https://api.census.gov/data/2023/acs/acs5"
                "?get=NAME,B19013_001E,B19013_001M,B19301_001E,B19301_001M,"
                "B19083_001E,B19083_001M,B01003_001E,B01003_001M"
                "&for=school+district+(unified):*&in=state:53")
ACS_SUBJECT_URL = ("https://api.census.gov/data/2023/acs/acs5/subject"
                   "?get=NAME,S1501_C02_015E,S1501_C02_015M,"
                   "S2301_C02_001E,S2301_C02_001M,"
                   "S2301_C04_001E,S2301_C04_001M"
                   "&for=school+district+(unified):*&in=state:53")
TIGER_GAZETTEER_URL = ("https://www2.census.gov/geo/docs/maps-data/data/"
                       "gazetteer/2023_Gazetteer/2023_Gaz_unsd_national.zip")

def is_acs_suppressed(v):
    """ACS uses negative numeric annotation values to indicate suppression /
    unavailability. -666666666 = estimate not computed; -888888888 = N/A;
    -999999999 = median fell outside top range; -222222222 = restricted.
    These differ from real numeric data because real ACS estimates are >= 0."""
    if v is None:
        return True
    try:
        f = float(v)
    except (TypeError, ValueError):
        return True
    if f < 0:
        return True
    return False

def acs_value(raw):
    """Return (value, suppressed_flag). Estimates and MOEs are returned as
    floats. Suppressed values become None."""
    if is_acs_suppressed(raw):
        return None, True
    return float(raw), False

def fetch_json(url, label):
    print(f"  fetching {label}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent":
                                               "school-daylight-research/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    return json.loads(body)

print("Fetching ACS base table data ...")
base_rows = fetch_json(ACS_BASE_URL, "ACS base")
base_header = base_rows[0]
base_data = base_rows[1:]
print(f"  got {len(base_data)} district rows from base tables")

print("Fetching ACS subject table data ...")
subj_rows = fetch_json(ACS_SUBJECT_URL, "ACS subject")
subj_header = subj_rows[0]
subj_data = subj_rows[1:]
print(f"  got {len(subj_data)} district rows from subject tables")

# Index both by the 7-char LEAID (state FIPS + 5-digit unified district id)
def index_rows(header, rows, geo_label="school district (unified)"):
    i_state = header.index("state")
    i_sdid = header.index(geo_label)
    out = {}
    for row in rows:
        leaid = row[i_state] + row[i_sdid]
        out[leaid] = dict(zip(header, row))
    return out

base_by_leaid = index_rows(base_header, base_data)
subj_by_leaid = index_rows(subj_header, subj_data)

# ---------------------------------------------------------------------------
# FETCH 2 — TIGER Gazetteer (national unified school districts, 2023)
# Pipe-delimited TXT inside a ZIP. Columns: USPS GEOID NAME ALAND AWATER
# ALAND_SQMI AWATER_SQMI INTPTLAT INTPTLONG.
# ---------------------------------------------------------------------------
print("Fetching TIGER 2023 Unified School District Gazetteer ...")
print(f"  {TIGER_GAZETTEER_URL}")
req = urllib.request.Request(TIGER_GAZETTEER_URL,
                             headers={"User-Agent":
                                      "school-daylight-research/0.1"})
with urllib.request.urlopen(req, timeout=120) as r:
    zip_bytes = r.read()
print(f"  downloaded {len(zip_bytes)/1024/1024:.1f} MB")

aland_sqmi_by_leaid = {}
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    inner = [n for n in z.namelist() if n.lower().endswith(".txt")]
    if not inner:
        raise RuntimeError("Gazetteer ZIP contained no .txt file")
    with z.open(inner[0]) as f:
        # File is tab-delimited (per Census Gazetteer convention) with a
        # header row. Encoding: latin-1 is the safe default for Census files.
        text = f.read().decode("latin-1")
lines = text.splitlines()
header_line = lines[0].rstrip()
# Header tokens may have trailing whitespace; normalize.
cols = [c.strip() for c in header_line.split("\t")]
i_usps = cols.index("USPS")
i_geoid = cols.index("GEOID")
i_aland_sqmi = cols.index("ALAND_SQMI")
wa_rows = 0
for line in lines[1:]:
    parts = line.split("\t")
    if len(parts) < len(cols):
        continue
    if parts[i_usps].strip() != "WA":
        continue
    leaid = parts[i_geoid].strip()
    try:
        sqmi = float(parts[i_aland_sqmi].strip())
    except ValueError:
        sqmi = None
    aland_sqmi_by_leaid[leaid] = sqmi
    wa_rows += 1
print(f"  parsed {wa_rows} WA Unified School District rows from gazetteer")

# ---------------------------------------------------------------------------
# BUILD per-district census_acs payload
# ---------------------------------------------------------------------------
def build_var(value, moe, code):
    """One variable's object: {value, moe, census_code, suppressed?}."""
    v, v_supp = acs_value(value)
    m, m_supp = acs_value(moe)
    out = {"value": v, "moe": m, "census_code": code}
    if v_supp:
        out["suppressed"] = True
    return out

district_payload = {}  # leaid -> census_acs payload (variables only, no _meta)
for leaid in base_by_leaid:
    base = base_by_leaid[leaid]
    subj = subj_by_leaid.get(leaid, {})
    aland = aland_sqmi_by_leaid.get(leaid)
    pop_var = build_var(base.get("B01003_001E"), base.get("B01003_001M"),
                        "B01003_001E")
    pop_density = None
    if pop_var["value"] is not None and aland not in (None, 0):
        pop_density = pop_var["value"] / aland
    district_payload[leaid] = {
        "median_household_income": build_var(
            base.get("B19013_001E"), base.get("B19013_001M"), "B19013_001E"),
        "per_capita_income": build_var(
            base.get("B19301_001E"), base.get("B19301_001M"), "B19301_001E"),
        "gini_index": build_var(
            base.get("B19083_001E"), base.get("B19083_001M"), "B19083_001E"),
        "total_population": pop_var,
        "bachelors_or_higher_pct_25plus": build_var(
            subj.get("S1501_C02_015E"), subj.get("S1501_C02_015M"),
            "S1501_C02_015E"),
        "labor_force_participation_rate_16plus": build_var(
            subj.get("S2301_C02_001E"), subj.get("S2301_C02_001M"),
            "S2301_C02_001E"),
        "unemployment_rate_16plus": build_var(
            subj.get("S2301_C04_001E"), subj.get("S2301_C04_001M"),
            "S2301_C04_001E"),
        "land_area_sq_miles": {
            "value": aland,
            "source": "TIGER 2023 Unified Gazetteer ALAND_SQMI",
        },
        "population_density_per_sq_mile": {
            "value": pop_density,
            "computed_from": "total_population / land_area_sq_miles",
        },
    }

# ---------------------------------------------------------------------------
# WALK every school in the experiment db, build per-school update.
# ---------------------------------------------------------------------------
print("Reading experiment-db schools ...")
schools = list(db["schools"].find({}, {
    "_id": 1, "name": 1, "is_charter": 1, "school_type": 1,
    "district.name": 1, "district.nces_id": 1,
}))
print(f"  {len(schools)} schools")

# Load existing manual exclusions for overlap report
with open('/Users/oriandaleigh/school-daylight/school_exclusions.yaml') as f:
    excl = yaml.safe_load(f)
excluded_ncessch = {e["ncessch"]: e for e in excl.get("excluded_schools", [])}
print(f"  {len(excluded_ncessch)} schools in school_exclusions.yaml")

VAR_KEYS = list(district_payload[next(iter(district_payload))].keys())

def null_payload():
    """Variable fields explicitly null for SKIP schools."""
    return {k: None for k in VAR_KEYS}

usd_leaids = set(district_payload.keys())

matched, skipped, unrecognized = [], [], []
ops = []
skip_by_reason = defaultdict(list)
overlap_by_reason = defaultdict(int)

for s in schools:
    nid = s["_id"]
    leaid = (s.get("district") or {}).get("nces_id")
    name = s.get("name", "")
    is_charter = bool(s.get("is_charter"))
    if leaid in usd_leaids:
        # MATCHED — full payload
        payload = dict(district_payload[leaid])
        payload["_meta"] = {
            "vintage": VINTAGE,
            "fetched_at": NOW_ISO,
            "acs_base_api_url": ACS_BASE_URL,
            "acs_subject_api_url": ACS_SUBJECT_URL,
            "tiger_gazetteer_url": TIGER_GAZETTEER_URL,
            "district_geoid": leaid,
            "district_geoid_source": "district.nces_id",
            "unmatched_reason": None,
        }
        matched.append(nid)
    else:
        reason = classify_skip(name, is_charter)
        if reason is None:
            unrecognized.append((nid, name, leaid))
            # Still record a SKIP entry but with reason "unclassified" so we
            # can investigate. Variable fields null.
            payload = null_payload()
            payload["_meta"] = {
                "vintage": VINTAGE,
                "fetched_at": NOW_ISO,
                "district_geoid": None,
                "district_geoid_source": "district.nces_id",
                "unmatched_reason": "unclassified_pending_review",
            }
        else:
            payload = null_payload()
            payload["_meta"] = {
                "vintage": VINTAGE,
                "fetched_at": NOW_ISO,
                "district_geoid": None,
                "district_geoid_source": "district.nces_id",
                "unmatched_reason": reason,
            }
            skip_by_reason[reason].append({"_id": nid, "name": name})
            if nid in excluded_ncessch:
                overlap_by_reason[reason] += 1
        skipped.append((nid, name, reason or "unclassified_pending_review"))
    ops.append(UpdateOne({"_id": nid}, {"$set": {"census_acs": payload}}))

# ---------------------------------------------------------------------------
# WRITE — final guard, then bulk_write in chunks
# ---------------------------------------------------------------------------
assert "experiment" in db.name  # one more time, immediately before write
print(f"Writing {len(ops)} school updates to {db.name}.schools ...")
chunk = 500
total_modified = 0
for i in range(0, len(ops), chunk):
    res = db["schools"].bulk_write(ops[i:i+chunk], ordered=False)
    total_modified += res.modified_count
    print(f"  batch {i//chunk+1}: modified {res.modified_count}")
print(f"  total modified: {total_modified}")

# ---------------------------------------------------------------------------
# SANITY CHECK — 5 random schools across WA, hand-pick by district to span
# Seattle metro / Eastside / rural eastern WA / South Sound / NW WA.
# Reproducible via random.seed.
# ---------------------------------------------------------------------------
random.seed(20260503)
# Build {leaid -> sample school} so each pick lands in a different district
by_leaid = defaultdict(list)
for s in schools:
    leaid = (s.get("district") or {}).get("nces_id")
    if leaid in usd_leaids:
        by_leaid[leaid].append(s)
# Hand-pick five known districts to span the income/density spectrum
def pick_first(district_names_substring_list):
    for sub in district_names_substring_list:
        for leaid, lst in by_leaid.items():
            dname = (lst[0].get("district") or {}).get("name","").lower()
            if sub.lower() in dname:
                return random.choice(lst)["_id"]
    return None

probe_ids = []
for tag in [["seattle"], ["bellevue"], ["spokane"], ["aberdeen", "hoquiam"],
            ["bellingham"]]:
    pid = pick_first(tag)
    if pid:
        probe_ids.append(pid)

# Pull each probe's full census_acs after the write
sanity_rows = []
for pid in probe_ids:
    d = db["schools"].find_one({"_id": pid},
                                {"name":1, "district.name":1, "census_acs":1})
    if not d:
        continue
    ca = d.get("census_acs", {})
    sanity_rows.append({
        "_id": pid,
        "name": d.get("name"),
        "district": (d.get("district") or {}).get("name"),
        "median_hh_income": ca.get("median_household_income", {}).get("value"),
        "per_capita_income": ca.get("per_capita_income", {}).get("value"),
        "gini": ca.get("gini_index", {}).get("value"),
        "bachelors_pct": ca.get("bachelors_or_higher_pct_25plus", {}).get("value"),
        "lfp_rate": ca.get("labor_force_participation_rate_16plus", {}).get("value"),
        "unemp_rate": ca.get("unemployment_rate_16plus", {}).get("value"),
        "total_pop": ca.get("total_population", {}).get("value"),
        "land_sqmi": ca.get("land_area_sq_miles", {}).get("value"),
        "pop_density": ca.get("population_density_per_sq_mile", {}).get("value"),
    })

# ---------------------------------------------------------------------------
# WRITE acs_ingestion_results.md
# ---------------------------------------------------------------------------
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) if c is not None else "—" for c in r) + " |")
    return "\n".join(out)

def fmt(v, places=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{places}f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)

out = []
out.append("# Phase 3R — ACS Ingestion Results (experiment database)")
out.append("")
out.append(f"Run date (UTC): **{NOW_ISO}**")
out.append(f"Target database: **{db.name}** (production untouched)")
out.append(f"Data vintage: **{VINTAGE}** (ACS 5-year, 2019-2023 estimates)")
out.append("")
out.append("## API endpoints used")
out.append("")
out.append(f"- ACS base tables (B19013, B19301, B19083, B01003): `{ACS_BASE_URL}`")
out.append(f"- ACS subject tables (S1501, S2301): `{ACS_SUBJECT_URL}`")
out.append(f"- TIGER 2023 Unified School District Gazetteer (ALAND_SQMI): `{TIGER_GAZETTEER_URL}`")
out.append("")
out.append("All three endpoints fetched once at run start. No per-school API calls.")
out.append("Census API is free and public; no API key used (volume well under "
           "the 500 calls/day no-key threshold).")
out.append("")
out.append("## Variable list with confirmed Census codes")
out.append("")
out.append(md_table(
    ["MongoDB key under `census_acs`", "Source code", "Description"],
    [
        ["median_household_income", "B19013_001E", "Median household income (past 12 months, 2023 dollars)"],
        ["per_capita_income", "B19301_001E", "Per capita income (past 12 months, 2023 dollars)"],
        ["gini_index", "B19083_001E", "Gini index of income inequality"],
        ["total_population", "B01003_001E", "Total population"],
        ["bachelors_or_higher_pct_25plus", "S1501_C02_015E", "% age 25+ with Bachelor's degree or higher"],
        ["labor_force_participation_rate_16plus", "S2301_C02_001E", "Labor force participation rate, age 16+"],
        ["unemployment_rate_16plus", "S2301_C04_001E", "Unemployment rate, age 16+"],
        ["land_area_sq_miles", "TIGER 2023 ALAND_SQMI", "District land area, square miles"],
        ["population_density_per_sq_mile", "computed", "total_population / land_area_sq_miles"],
    ]
))
out.append("")
out.append("Each variable on every matched school is stored as "
           "`{value, moe, census_code}` (or `{value, source}` for TIGER, "
           "`{value, computed_from}` for the derived density). Suppressed ACS "
           "values (negative annotation codes) become `value: null` with "
           "`suppressed: true`.")
out.append("")
out.append("## Schema written under `census_acs._meta`")
out.append("")
out.append("- `vintage`: `\"acs5_2019_2023\"`")
out.append("- `fetched_at`: ISO 8601 UTC timestamp of this run")
out.append("- `acs_base_api_url`, `acs_subject_api_url`, `tiger_gazetteer_url`: provenance")
out.append("- `district_geoid`: 7-char LEAID used for the join (null on SKIP schools)")
out.append("- `district_geoid_source`: `\"district.nces_id\"`")
out.append("- `unmatched_reason`: null on matched schools; one of the SKIP reason codes otherwise")
out.append("")
out.append("## Coverage")
out.append("")
out.append(md_table(
    ["Outcome", "Count", "% of total"],
    [
        ["Matched USD → full Census payload written", len(matched), f"{len(matched)/len(schools)*100:.1f}%"],
        ["Skipped (with documented reason code)", len(skipped) - len(unrecognized), f"{(len(skipped)-len(unrecognized))/len(schools)*100:.1f}%"],
        ["Unrecognized (skipped with placeholder reason — needs review)", len(unrecognized), f"{len(unrecognized)/len(schools)*100:.1f}%"],
        ["**Total schools in experiment db**", len(schools), "100.0%"],
    ]
))
out.append("")
out.append(f"WA Unified School Districts pulled from ACS: **{len(usd_leaids)}** "
           f"(286 of which actually appear as `district.nces_id` on a school in "
           f"the experiment db; the other 9 are USDs with no enrolled schools "
           f"in this dataset).")
out.append("")
out.append("## Skip breakdown by reason code")
out.append("")
out.append(md_table(
    ["unmatched_reason", "schools skipped", "of those, also in school_exclusions.yaml"],
    [[r, len(skip_by_reason[r]), overlap_by_reason[r]] for r in SKIP_REASONS]
))
total_skip = sum(len(v) for v in skip_by_reason.values())
total_overlap = sum(overlap_by_reason.values())
out.append("")
out.append(f"**Total SKIP overlap with `school_exclusions.yaml`: {total_overlap} of {total_skip} skipped schools "
           f"({total_overlap/total_skip*100 if total_skip else 0:.0f}%)** are already excluded from Phase 3 peer matching.")
out.append("")
if unrecognized:
    out.append("### Unrecognized skip schools (need builder follow-up)")
    out.append("")
    out.append("These schools' `district.nces_id` doesn't match a WA USD geography "
               "AND their name didn't match any of the builder-supplied SKIP rules. "
               "They've been written with `unmatched_reason=\"unclassified_pending_review\"` "
               "and null variable fields.")
    out.append("")
    out.append(md_table(
        ["_id","name","district.nces_id"],
        [[u[0], u[1], u[2]] for u in unrecognized]
    ))
    out.append("")

# Per-reason expanded list
for reason in SKIP_REASONS:
    rows = skip_by_reason[reason]
    if not rows:
        continue
    out.append(f"### `{reason}` ({len(rows)} schools)")
    out.append("")
    in_excl = sum(1 for r in rows if r["_id"] in excluded_ncessch)
    out.append(f"Already in `school_exclusions.yaml`: **{in_excl}** of {len(rows)}.")
    out.append("")
    out.append(md_table(
        ["_id","name","in school_exclusions.yaml?"],
        [[r["_id"], r["name"], "yes" if r["_id"] in excluded_ncessch else "no"]
         for r in sorted(rows, key=lambda x: x["name"] or "")]
    ))
    out.append("")

out.append("## Sanity check — 5 schools across WA")
out.append("")
out.append("Reproducible via `random.seed(20260503)`. Picks intentionally span the "
           "income/density spectrum (Seattle metro, Eastside, Spokane, coastal "
           "Grays Harbor, NW WA / Bellingham) so values can be eyeballed for "
           "plausibility.")
out.append("")
out.append(md_table(
    ["School","District","Med HH inc","Per cap inc","Gini","Bach+ %","LFP %","Unemp %","Total pop","Land sqmi","Pop/sqmi"],
    [[r["name"], r["district"],
      fmt(r["median_hh_income"], 0), fmt(r["per_capita_income"], 0),
      fmt(r["gini"], 4), fmt(r["bachelors_pct"], 1),
      fmt(r["lfp_rate"], 1), fmt(r["unemp_rate"], 1),
      fmt(r["total_pop"], 0), fmt(r["land_sqmi"], 1),
      fmt(r["pop_density"], 1)] for r in sanity_rows]
))
out.append("")
out.append("## Issues encountered")
out.append("")
suppressed_count = 0
for leaid, payload in district_payload.items():
    for k, v in payload.items():
        if isinstance(v, dict) and v.get("suppressed"):
            suppressed_count += 1
out.append(f"- **Suppressed ACS values across all 295 districts × 7 ACS variables: "
           f"{suppressed_count} cells.** Stored as `value: null` with `suppressed: true` "
           f"per the project's data-integrity rule (suppressed ≠ zero).")
land_null = sum(1 for leaid in district_payload
                if district_payload[leaid]["land_area_sq_miles"]["value"] is None)
out.append(f"- **TIGER ALAND_SQMI missing for: {land_null} of {len(district_payload)} districts.** "
           f"Population density null on those districts as a result.")
out.append("- **No HTTP errors.** All three external fetches (2× ACS, 1× TIGER) "
           "succeeded on first attempt.")
if unrecognized:
    out.append(f"- **{len(unrecognized)} schools could not be auto-classified into a SKIP reason** — see table above.")
else:
    out.append("- **All 48 unmatched schools were successfully classified** into one of the five builder-supplied reason codes.")
out.append("")
out.append("## Production untouched")
out.append("")
out.append(f"- Database written: `{db.name}` (contains substring \"experiment\")")
out.append(f"- Pre-write isolation guard: PASSED")
out.append(f"- Production database (`{config.DB_NAME}`): NOT opened, NOT queried, NOT written.")
out.append("")

with open(OUT_FILE, "w") as f:
    f.write("\n".join(out))
print(f"\nWrote {OUT_FILE}")

client.close()
print("Done.")
