"""
_run_fairhaven_field_probe.py — Phase 2R audit diagnostic.

PURPOSE: Read-only field-presence probe on Fairhaven's document in
         schooldaylight_experiment. Enumerates every top-level field,
         every key under derived.*, the full peer_match.* block, and
         explicitly tests for academic_flag / academic_flags /
         academic_performance_flag at document root. Written for the
         2026-05-13 academic_flag verification request.
INPUTS:  config.MONGO_URI_EXPERIMENT (read).
OUTPUTS: stdout only.
READ-ONLY: Yes.
RESULT (recorded for future sessions): academic_flag is ABSENT at
       document root and under derived.*. derived.performance_flag (the
       regression-era flag) is present. peer_match.* is fully populated
       with K=20 cohort metadata stamped 2026-05-08T17:26:35Z.
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

FAIRHAVEN = "530042000104"
client = MongoClient(config.MONGO_URI_EXPERIMENT, serverSelectionTimeoutMS=15000)
db = client[config.DB_NAME_EXPERIMENT]
d = db["schools"].find_one({"_id": FAIRHAVEN})
client.close()

if d is None:
    print("Fairhaven NOT PRESENT")
    raise SystemExit(0)

print("Top-level keys in Fairhaven doc:")
for k in sorted(d.keys()):
    print(f"  {k}")
print()

print("=== academic_flag-like fields ===")
candidates = []
for k in d.keys():
    if "academic" in k.lower() or "flag" in k.lower():
        candidates.append(k)

# Also walk derived.*
derived = d.get("derived") or {}
for k in derived.keys():
    if "academic" in k.lower() or "flag" in k.lower() or "perform" in k.lower():
        candidates.append(f"derived.{k}")

# peer_match top-level keys
pm = d.get("peer_match") or {}
print(f"peer_match top-level keys: {sorted(pm.keys()) if isinstance(pm, dict) else type(pm).__name__}")

print(f"\nCandidates found: {candidates}")
print()

for path in ["academic_flag", "academic_flags", "academic_performance_flag"]:
    v = d.get(path)
    print(f"d[{path!r}]: {v!r}")

print()
print("=== derived block detail ===")
for k, v in (d.get("derived") or {}).items():
    if isinstance(v, (dict, list)):
        print(f"  derived.{k}: <{type(v).__name__}> keys/len={sorted(v.keys()) if isinstance(v, dict) else len(v)}")
    else:
        print(f"  derived.{k}: {v!r}")

print()
print("=== peer_match block detail ===")
print(json.dumps(d.get("peer_match"), indent=2, default=str, sort_keys=True)[:3500])
