"""
_patch_unclassified.py — Targeted re-classification of the 3 schools the
initial classifier missed, plus produce the exclusions consistency note.

GUARD: writes to experiment db only, and only to the 3 specific _ids that
       were tagged 'unclassified_pending_review' in the prior run.
"""

import datetime as dt
import os
import re
import string
import sys
import yaml
from collections import defaultdict

sys.path.insert(0, '/Users/oriandaleigh/school-daylight')
import config
from pymongo import MongoClient

client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client[config.DB_NAME_EXPERIMENT]
assert "experiment" in db.name, \
    f"Refusing to write — '{db.name}' is not an experiment db."

OUT_DIR = '/Users/oriandaleigh/school-daylight/phases/phase-3R/experiment'
NOW_ISO = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# ---------------------------------------------------------------------------
# Tightened classifier: case-insensitive, punctuation-stripped, whole-string
# substring match. Replaces the prior pattern-list classifier.
# ---------------------------------------------------------------------------
def normalize(s):
    """Lowercase, drop punctuation, collapse whitespace."""
    if not s:
        return ""
    s = s.lower()
    s = s.translate(str.maketrans("", "", string.punctuation))
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Builder-supplied substrings (already normalized — case/punct-stripped)
STATEWIDE_SPECIALTY = [
    normalize("Washington State School for the Deaf"),
    normalize("WA School for the Deaf"),
    normalize("Washington State School for the Blind"),
    normalize("WA School for the Blind"),
    normalize("Washington Youth Academy"),
    normalize("ESA 112 Special Ed Co-Op"),
    normalize("Northwest Career and Technical"),
    normalize("Bates Technical High School"),
    normalize("Renton Technical High School"),
    normalize("Lake Washington Technical Academy"),
]
REGIONAL_ALT = [
    normalize("Open Doors"),
    normalize("Re-Engagement"),  # normalizes to 'reengagement'
    normalize("Reengagement"),
    normalize("Pass Program"),
    normalize("Garrett Heyns"),
    normalize("Dropout Prevention"),
    normalize("YouthSource"),
    normalize("LWIT"),
    normalize("RTC"),
]
INSTITUTIONAL = [
    normalize("juvenile detention"),
    normalize("county detention"),
    normalize("co detention"),
    normalize("youth services center"),
    normalize("Martin Hall"),
    normalize("Structural Alt"),
    normalize("detention center"),
    normalize("Kitsap Detention"),
    normalize("Kitsap juvenile"),
]
TRIBAL = [normalize("Chief Kitsap")]
CHARTER_OPS = [normalize(x) for x in [
    "Summit", "Rainier Prep", "Spokane International", "PRIDE Prep",
    "Innovation", "Rainier Valley Leadership", "Impact Public Schools",
    "Catalyst", "Cascade Public", "Why Not You", "Lumen",
    "Intergenerational", "Pinnacles Prep", "Rooted School",
]]

def classify(name, is_charter):
    n = normalize(name)
    if is_charter:
        return "charter_pending_district_assignment"
    if any(op in n for op in CHARTER_OPS):
        return "charter_pending_district_assignment"
    if any(s in n for s in TRIBAL):
        return "tribal_community_context_not_capturable_v1"
    if any(s in n for s in STATEWIDE_SPECIALTY):
        return "statewide_specialty_school_not_comparable"
    if any(s in n for s in INSTITUTIONAL):
        return "institutional_facility_not_comparable"
    if any(s in n for s in REGIONAL_ALT):
        return "regional_alternative_program_not_comparable"
    return None

# ---------------------------------------------------------------------------
# 1) Find the schools currently flagged unclassified, verify the new
#    classifier resolves them, then update those _ids only.
# ---------------------------------------------------------------------------
unclassified = list(db["schools"].find(
    {"census_acs._meta.unmatched_reason": "unclassified_pending_review"},
    {"_id": 1, "name": 1, "is_charter": 1}))
print(f"Currently unclassified: {len(unclassified)} schools")
for u in unclassified:
    print(f"  {u['_id']}  {u.get('name')}")

resolved = []
for u in unclassified:
    new_reason = classify(u.get("name"), bool(u.get("is_charter")))
    if new_reason is None:
        print(f"  STILL UNCLASSIFIED: {u['_id']} {u.get('name')}")
        continue
    print(f"  {u['_id']} -> {new_reason}")
    resolved.append((u["_id"], new_reason))

if len(resolved) != len(unclassified):
    print("ABORT: not all previously-unclassified docs reclassified. No writes.")
    client.close()
    raise SystemExit(2)

# Targeted writes: one $set per resolved _id, only the two _meta fields.
print(f"Writing {len(resolved)} targeted updates ...")
for nid, reason in resolved:
    res = db["schools"].update_one(
        {"_id": nid,
         "census_acs._meta.unmatched_reason": "unclassified_pending_review"},
        {"$set": {
            "census_acs._meta.unmatched_reason": reason,
            "census_acs._meta.reclassified_at": NOW_ISO,
        }}
    )
    print(f"  {nid}: matched={res.matched_count} modified={res.modified_count}")

# Confirm zero remain unclassified
remaining = db["schools"].count_documents(
    {"census_acs._meta.unmatched_reason": "unclassified_pending_review"})
print(f"Unclassified remaining after patch: {remaining}")
assert remaining == 0, "Patch did not clear all unclassified docs."

# ---------------------------------------------------------------------------
# 2) Build the consistency note: every SKIP school NOT in school_exclusions.yaml
# ---------------------------------------------------------------------------
with open('/Users/oriandaleigh/school-daylight/school_exclusions.yaml') as f:
    excl_yaml = yaml.safe_load(f)
excluded_ncessch = {e["ncessch"] for e in excl_yaml.get("excluded_schools", [])}

# Pull all SKIP schools (any non-null unmatched_reason) and group by reason
cursor = db["schools"].find(
    {"census_acs._meta.unmatched_reason": {"$ne": None}},
    {"_id": 1, "name": 1, "school_type": 1, "is_charter": 1,
     "district.name": 1, "district.nces_id": 1,
     "grade_span.low": 1, "grade_span.high": 1,
     "enrollment.total": 1, "address.city": 1,
     "census_acs._meta.unmatched_reason": 1})

skip_by_reason = defaultdict(list)
for s in cursor:
    reason = s["census_acs"]["_meta"]["unmatched_reason"]
    skip_by_reason[reason].append(s)

# Coverage summary across all skip categories
print()
print("Post-patch SKIP breakdown:")
for r in sorted(skip_by_reason):
    n = len(skip_by_reason[r])
    in_excl = sum(1 for s in skip_by_reason[r] if s["_id"] in excluded_ncessch)
    print(f"  {r}: {n} schools ({in_excl} also in school_exclusions.yaml, "
          f"{n - in_excl} NOT in school_exclusions.yaml)")

# Build the consistency note
def fmt_grade(s):
    gs = s.get("grade_span") or {}
    lo, hi = gs.get("low"), gs.get("high")
    return f"{lo}-{hi}" if (lo and hi) else "—"
def fmt_enr(s):
    t = (s.get("enrollment") or {}).get("total")
    return str(t) if t is not None else "—"
def fmt_city(s):
    return (s.get("address") or {}).get("city") or "—"
def fmt_type(s):
    st = s.get("school_type", "—") or "—"
    return f"{st} (charter)" if s.get("is_charter") else st

REASON_LABELS = {
    "charter_pending_district_assignment":
        "Charters (pending district assignment)",
    "statewide_specialty_school_not_comparable":
        "Statewide specialty schools",
    "institutional_facility_not_comparable":
        "Institutional facilities",
    "regional_alternative_program_not_comparable":
        "Regional alternative / reengagement programs",
    "tribal_community_context_not_capturable_v1":
        "Tribal community schools",
}
REASON_NOTES = {
    "charter_pending_district_assignment":
        "These charters will be reassigned to the operating district their "
        "physical address falls within in a follow-up step. They are not "
        "currently on `school_exclusions.yaml` because the existing list "
        "predates the methodology shift toward peer-cohort matching.",
    "statewide_specialty_school_not_comparable":
        "Statewide-mission schools (Schools for the Deaf/Blind, Youth Academy, "
        "tech high schools) draw students from across WA and serve fundamentally "
        "different populations. None are currently on `school_exclusions.yaml`, "
        "but they would arguably distort any FRL-vs-proficiency regression they're "
        "included in.",
    "institutional_facility_not_comparable":
        "Juvenile detention and youth services facilities. Five of these are "
        "already on `school_exclusions.yaml`; five are not — likely an oversight "
        "from incremental list-building rather than a deliberate distinction.",
    "regional_alternative_program_not_comparable":
        "ESD-run reengagement and alternative programs (Open Doors, dropout "
        "prevention, YouthSource, technical-college-affiliated programs). One "
        "school (Garrett Heyns) is on `school_exclusions.yaml`; the other ten are "
        "not, despite serving similar populations under similar models.",
    "tribal_community_context_not_capturable_v1":
        "Chief Kitsap Academy. Not currently on `school_exclusions.yaml`. "
        "ACS district geography cannot capture tribal community context for "
        "this single tribal compact school.",
}
REASON_ORDER = [
    "charter_pending_district_assignment",
    "statewide_specialty_school_not_comparable",
    "institutional_facility_not_comparable",
    "regional_alternative_program_not_comparable",
    "tribal_community_context_not_capturable_v1",
]

out = []
out.append("# Phase 3R — Exclusions Consistency Note")
out.append("")
out.append(f"Generated: **{NOW_ISO}**")
out.append("")
out.append("## What this is")
out.append("")
out.append("Phase 3R Census ingestion produced a SKIP list of schools where a "
           "district-level ACS join doesn't apply (charters, statewide specialty "
           "schools, institutional facilities, regional alternative programs, "
           "tribal community schools). The pre-existing `school_exclusions.yaml` "
           "list, used by the FRL-vs-proficiency regression to suppress the "
           "performance flag, was built incrementally for a different purpose.")
out.append("")
out.append("This note inventories the schools that appear on the new SKIP list "
           "but NOT on `school_exclusions.yaml`, grouped by SKIP reason. It is "
           "a methodology question for follow-up — not a request to change "
           "either list.")
out.append("")
out.append("**Scope:** experiment database only. `school_exclusions.yaml` is "
           "untouched. Production is untouched.")
out.append("")

# Headline counts
total_skip = sum(len(v) for v in skip_by_reason.values())
total_overlap = sum(1 for r in skip_by_reason for s in skip_by_reason[r]
                    if s["_id"] in excluded_ncessch)
gap = total_skip - total_overlap
out.append("## Headline counts")
out.append("")
out.append("| Bucket | Count |")
out.append("|---|---|")
out.append(f"| Total SKIP schools (post-patch) | {total_skip} |")
out.append(f"| Of those, already on `school_exclusions.yaml` | {total_overlap} |")
out.append(f"| **Consistency gap (SKIP but NOT in school_exclusions.yaml)** | **{gap}** |")
out.append("")

# Breakdown by category
out.append("## Per-category breakdown")
out.append("")
out.append("| SKIP category | Total SKIP | Already in exclusions.yaml | Gap |")
out.append("|---|---|---|---|")
for r in REASON_ORDER:
    if r not in skip_by_reason:
        continue
    rows = skip_by_reason[r]
    in_excl = sum(1 for s in rows if s["_id"] in excluded_ncessch)
    out.append(f"| {REASON_LABELS[r]} | {len(rows)} | {in_excl} | {len(rows) - in_excl} |")
out.append("")

# Each gap section
out.append("## The 39-school consistency gap, by category")
out.append("")
out.append("Schools below are SKIPped from Census ingestion but currently flow "
           "through the FRL-vs-proficiency regression because they're not on "
           "`school_exclusions.yaml`.")
out.append("")
for r in REASON_ORDER:
    if r not in skip_by_reason:
        continue
    rows = [s for s in skip_by_reason[r] if s["_id"] not in excluded_ncessch]
    if not rows:
        continue
    out.append(f"### {REASON_LABELS[r]} ({len(rows)} schools)")
    out.append("")
    out.append(REASON_NOTES[r])
    out.append("")
    out.append("| _id | School name | Type | District | Grade span | Enrollment | City |")
    out.append("|---|---|---|---|---|---|---|")
    for s in sorted(rows, key=lambda x: x.get("name") or ""):
        dname = (s.get("district") or {}).get("name", "—")
        out.append(f"| `{s['_id']}` | {s.get('name','(no name)')} | "
                   f"{fmt_type(s)} | {dname} | {fmt_grade(s)} | "
                   f"{fmt_enr(s)} | {fmt_city(s)} |")
    out.append("")

# Methodology question
out.append("## Methodology question for follow-up")
out.append("")
out.append("**Should `school_exclusions.yaml` be aligned with the new SKIP "
           "classification, or are these schools appropriately treated "
           "differently?**")
out.append("")
out.append("Three possible positions, none of which this note is taking:")
out.append("")
out.append("1. **Align fully** — every school on the SKIP list should also be "
           "on `school_exclusions.yaml`, since both lists are answering "
           "essentially the same question (\"is this school comparable to "
           "regular WA schools on standard metrics?\"). The 39-school gap is "
           "an oversight to be corrected.")
out.append("")
out.append("2. **Keep them separate by intent** — `school_exclusions.yaml` "
           "exists specifically for the FRL regression's edge cases (CCD "
           "miscoding of virtual/online schools as 'Regular School'). The SKIP "
           "list answers a different question (\"can we attach district-level "
           "ACS data?\"). Different methodologies, different exclusion criteria, "
           "no need to merge.")
out.append("")
out.append("3. **Defer the question** — if the FRL regression is being retired "
           "in favour of peer-cohort matching, `school_exclusions.yaml` itself "
           "becomes legacy. The new methodology will have its own exclusion "
           "logic (likely the SKIP categories above plus more). Don't reconcile "
           "two lists where one is on its way out.")
out.append("")
out.append("Position 3 is the most consistent with the architectural decision "
           "made today. Recommendation: revisit when the new peer-cohort "
           "methodology is being formalized, and design the new exclusion logic "
           "from first principles rather than patching the legacy list.")
out.append("")

with open(os.path.join(OUT_DIR, "exclusions_consistency_note.md"), "w") as f:
    f.write("\n".join(out))
print(f"\nWrote {os.path.join(OUT_DIR, 'exclusions_consistency_note.md')}")

# ---------------------------------------------------------------------------
# Re-emit final coverage breakdown for the chat reply
# ---------------------------------------------------------------------------
print()
print("=== Final coverage (post-patch) ===")
matched = db["schools"].count_documents({"census_acs._meta.unmatched_reason": None})
total = db["schools"].count_documents({})
print(f"Matched: {matched} / {total} ({matched/total*100:.1f}%)")
print(f"Skipped: {total - matched} / {total} ({(total-matched)/total*100:.1f}%)")
print(f"Unclassified placeholders remaining: {remaining}")
for r in REASON_ORDER:
    if r in skip_by_reason:
        n = len(skip_by_reason[r])
        in_excl = sum(1 for s in skip_by_reason[r] if s["_id"] in excluded_ncessch)
        print(f"  {r}: {n} (in excl.yaml: {in_excl}, gap: {n - in_excl})")

client.close()
print("Done.")
