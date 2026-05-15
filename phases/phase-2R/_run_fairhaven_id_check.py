"""
_run_fairhaven_id_check.py — Phase 2R audit diagnostic.

PURPOSE: Resolve Fairhaven's canonical NCESSCH by evidence rather than
         assumption. Probes two candidate _id strings (the one from the
         audit prompt and pipeline/helpers.py:FAIRHAVEN_NCESSCH) against
         both MongoDB databases, plus a name-regex match for /Fairhaven/i
         in both databases.
INPUTS:  config.MONGO_URI, config.MONGO_URI_EXPERIMENT (read).
OUTPUTS: stdout only.
READ-ONLY: Yes.
RESULT (recorded for future sessions): Fairhaven Middle School is _id
        "530042000104" in both databases (OSPI district 37501, OSPI
        school 2066). The other candidate ("530219000370") exists in
        neither database and matches no project artifact.
"""

import sys
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
dns.resolver.default_resolver.timeout = 5
dns.resolver.default_resolver.lifetime = 15

sys.path.insert(0, "/Users/oriandaleigh/school-daylight")
import config
from pymongo import MongoClient

CANDIDATES = ["530219000370", "530042000104"]


def probe(label, uri, db_name):
    print(f"\n=== {label} (db: {db_name}) ===")
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    coll = client[db_name]["schools"]
    for nid in CANDIDATES:
        d = coll.find_one({"_id": nid}, {"_id": 1, "name": 1,
                                          "metadata.ospi_district_code": 1,
                                          "metadata.ospi_school_code": 1})
        if d is None:
            print(f"  _id={nid}: NOT PRESENT")
        else:
            print(f"  _id={nid}: PRESENT, name={d.get('name')!r}, "
                  f"ospi_district={(d.get('metadata') or {}).get('ospi_district_code')}, "
                  f"ospi_school={(d.get('metadata') or {}).get('ospi_school_code')}")

    print("  --- name search: regex /Fairhaven/i ---")
    for d in coll.find({"name": {"$regex": "Fairhaven", "$options": "i"}},
                       {"_id": 1, "name": 1}):
        print(f"  match: _id={d['_id']} name={d.get('name')!r}")
    client.close()


probe("schooldaylight", config.MONGO_URI, config.DB_NAME)
probe("schooldaylight_experiment", config.MONGO_URI_EXPERIMENT,
      config.DB_NAME_EXPERIMENT)
print("\nDONE.")
