# PURPOSE: Production query function that pulls BOTH school-level (`context.findings`)
#          and district-level (`district_context.findings`) findings for a school and
#          returns a single deduplicated list ready to pass into Layer 3 Stage 0.
#          The dual-context model is already correct in MongoDB (Pass 1 writes
#          district_context to every school in the district; Pass 2 writes context
#          per school). This function does the read + dedup, nothing more.
#
# INPUTS:  pymongo Database object, NCES ID string.
# OUTPUTS: (findings_list, metadata_dict).
#          - findings_list: list of finding dicts in the same shape as the cached
#            `findings_in` arrays under phases/phase-4.5/test_results/raw_responses/,
#            ready to feed into Layer 3 Stage 0.
#          - metadata_dict: provenance and dedup stats for the receipt/log.
# JOIN KEYS: schools._id (NCES ID, 12-char string)
# SUPPRESSION HANDLING: n/a — operates on Phase 4 enriched findings only.
# RECEIPT: docs/receipts/phase-5/task2_district_context.md
# FAILURE MODES:
#   - School not found in MongoDB → returns ([], metadata with error).
#   - School has no `context` field → treats as no school-level findings (status=missing).
#   - School has no `district_context` field → treats as no district-level findings.
#   - Finding missing source_url / date / category → falls back to a content-based
#     dedup key built from a hash of the summary text.
#
# DEDUP STRATEGY:
#   Findings are grouped by composite key (source_url, date, category). Two real
#   cases this handles correctly:
#     (a) Bellingham HS district_context has TWO findings citing the same URL
#         (a 2023 Cascadia article that covers the 2023 criminal-charges
#         resolution AND a separate 2022 federal lawsuit). The dates differ, so
#         the composite key distinguishes them and BOTH are retained.
#     (b) Squalicum HS has the SAME 2026 bus-assault liability article in both
#         district_context (district-side framing) and context (school-side
#         framing). Same URL, same date, same category — the composite key
#         dedups to ONE entry, preferring the district_context version (which
#         describes institutional accountability the way Stage 2 frames it).
#   When source_url is missing/empty, the dedup key falls back to
#   ("nourl", date, category, hash(summary[:200])) so genuinely distinct
#   url-less findings are not collapsed into one.
#
# PRIORITY ON COLLISION: when a (url, date, category) collision happens between
#   district_context and context, the district_context entry wins. Rationale:
#   district-level findings are written by Pass 1 (the broader, district-focused
#   search) and tend to use district-actor language ("Bellingham Public Schools
#   admitted liability...") that aligns with Stage 2's district-attribution rule.
#   The school-level version is dropped from the deduped list but its existence
#   is recorded in metadata.dedup_collisions for transparency.

import hashlib


def _dedup_key(finding):
    """Build a composite dedup key for a finding.

    Composite of (source_url, date, category). When source_url is missing,
    falls back to a content hash so genuinely distinct findings are not
    collapsed.
    """
    url = (finding.get("source_url") or "").strip()
    date = (finding.get("date") or "").strip()
    category = (finding.get("category") or "").strip()
    if url:
        return ("url", url, date, category)
    # Fallback: content-hashed key. Use the first 200 chars of summary to keep
    # the key stable even if downstream code adds whitespace.
    summary = (finding.get("summary") or "").strip()[:200]
    h = hashlib.sha256(summary.encode("utf-8")).hexdigest()[:16]
    return ("nourl", date, category, h)


def get_findings_for_stage0(db, nces_id):
    """Pull both context and district_context for a school, dedup, return Stage 0 input.

    Args:
        db: pymongo Database object (e.g. MongoClient(MONGO_URI).get_default_database()).
        nces_id: 12-character NCES school ID string. NEVER pass an integer — leading
                 zeros matter.

    Returns:
        (findings, metadata) tuple.
        findings: list of finding dicts ready to feed into Layer 3 Stage 0. Each
                  dict matches the schema of cached `findings_in` arrays under
                  phases/phase-4.5/test_results/raw_responses/.
        metadata: dict with school identity, source counts, dedup stats, and the
                  list of any cross-context collisions for traceability.

    Example:
        from pymongo import MongoClient
        import config
        from pipeline.layer3_findings import get_findings_for_stage0

        client = MongoClient(config.MONGO_URI)
        db = client.get_default_database()
        findings, meta = get_findings_for_stage0(db, "530042000099")
        print(f"Stage 0 input: {len(findings)} findings "
              f"(school={meta['n_school']}, district={meta['n_district']}, "
              f"deduped={meta['n_deduped']})")
    """
    doc = db.schools.find_one(
        {"_id": nces_id},
        {"name": 1, "district.name": 1, "context": 1, "district_context": 1},
    )
    if doc is None:
        return [], {
            "nces_id": nces_id, "school_name": None, "district_name": None,
            "error": (
                f"School with NCES ID '{nces_id}' not found in MongoDB. "
                "Confirm the ID is the 12-character string (leading zeros preserved) "
                "and that the schools collection has been loaded for this state."
            ),
            "n_school": 0, "n_district": 0, "n_deduped": 0,
            "dedup_collisions": [],
        }

    school_findings = (doc.get("context") or {}).get("findings") or []
    district_findings = (doc.get("district_context") or {}).get("findings") or []

    # Walk district_context FIRST so its entries win on collision (per design note above).
    seen = {}  # dedup_key -> finding
    collisions = []

    for f in district_findings:
        key = _dedup_key(f)
        if key in seen:
            # Two district-level findings collided. Rare (one was observed in
            # Bellingham HS where a single article was extracted into two
            # findings with different dates — the date is part of the key, so
            # those did NOT collide). When this DOES happen, keep the first
            # entry and record the collision.
            collisions.append({"layer": "district", "key": key, "kept_layer": "district"})
            continue
        seen[key] = f

    for f in school_findings:
        key = _dedup_key(f)
        if key in seen:
            # School-level finding describes an event the district pass already
            # surfaced. Drop the school-level copy in favor of the district-level
            # framing. Record the collision so the receipt can show what was deduped.
            collisions.append({
                "layer": "school", "key": key, "kept_layer": "district",
                "school_summary_preview": (f.get("summary") or "")[:120],
            })
            continue
        seen[key] = f

    deduped = list(seen.values())

    metadata = {
        "nces_id": nces_id,
        "school_name": doc.get("name"),
        "district_name": (doc.get("district") or {}).get("name"),
        "n_school": len(school_findings),
        "n_district": len(district_findings),
        "n_total_before_dedup": len(school_findings) + len(district_findings),
        "n_deduped": len(deduped),
        "n_dropped_by_dedup": (len(school_findings) + len(district_findings)) - len(deduped),
        "dedup_collisions": collisions,
        "school_context_status": (doc.get("context") or {}).get("status"),
        "district_context_status": (doc.get("district_context") or {}).get("status"),
    }
    return deduped, metadata
