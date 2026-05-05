# Phase 5 — Task 2 Verification Receipt: district_context Propagation + Production Query Function

**Date:** 2026-04-30
**Task:** Verify district_context is populated on Bellingham schools as expected, then write the production query function that pulls BOTH `context` and `district_context` for a school and feeds the deduped union into Stage 0.
**Result:** PASS

---

## Part A — Inspection: district_context on Bellingham Schools

### Method
Connected to MongoDB Atlas (`schooldaylight` database, `schools` collection, 2,532 total schools loaded). Queried all 25 Bellingham School District schools and inspected the structure and contents of both `context` and `district_context` fields.

### Findings

| Property | Value |
|----------|-------|
| Bellingham schools in MongoDB | 25 |
| Schools with `district_context` populated | **25 / 25** |
| Schools with `district_context.status = enriched` | 25 / 25 |
| Schools with `district_context.findings` (the 6 Bellingham district findings) | 25 / 25 |
| Schools missing ANY of the three Title IX-related district findings | **0** |

The three Title IX / sexual-assault-related district findings (the canonical Bellingham accountability story) appear on EVERY Bellingham school's `district_context`:

1. **2023-12-12** — Three Bellingham administrators resolved criminal charges (deferred prosecution agreement) for failure to report a 2021–2022 sexual assault at Squalicum HS.
   Source: cascadiadaily.com criminal-charges-... article.
2. **2025-03-24** — Federal lawsuit by a 15-year-old student over the district's response to sexual harassment, calling it "catastrophically broken."
   Source: cascadiadaily.com district-sued-... article.
3. **2026-02-05** — Bellingham Public Schools admitted liability for negligence in the school-bus sexual assault case.
   Source: cascadiadaily.com bus-sexual-assault-case article.

Plus three additional district findings on every school: a 2022 federal lawsuit, the 2022 bond passage, and the 2025 levy passage.

**Conclusion:** the data-layer wiring described in the Phase 4.5 exit document is correct and live in production. Pass 1's district enrichment writes `district_context` to every school in the district via `db.schools.update_many({"district.name": district_name}, {"$set": {"district_context": context_doc}})` (`pipeline/17_haiku_enrichment.py:632-635`). No data fix is needed.

### Sample Documents Inspected

8 Bellingham schools were inspected in detail (mix of high, middle, elementary, alternative):

| NCES ID | School | district_context.findings | context.findings |
|---------|--------|---------------------------|------------------|
| 530042000099 | Bellingham High School | 6 | 0 (no_findings) |
| 530042000113 | Sehome High School | 6 | 4 |
| 530042000104 | Fairhaven Middle (golden) | 6 | 1 |
| 530042000117 | Whatcom Middle School | 6 | 1 |
| 530042000098 | Alderwood Elementary | 6 | 1 |
| 530042000110 | Parkview Elementary | 6 | 1 |
| 530042001738 | Options High School | 6 | 1 |
| 530042003488 | Bellingham Re-Engagement | 6 | 0 (no_findings) |

---

## Part B — Production Query Function

### File
`pipeline/layer3_findings.py` — exposes `get_findings_for_stage0(db, nces_id) -> (findings, metadata)`.

### Signature
```python
def get_findings_for_stage0(db, nces_id):
    """Pull both context and district_context, dedup, return findings ready for Stage 0.

    Returns (findings_list, metadata_dict).
    """
```

### Dedup Strategy

Findings do not have a stable `id` field on disk. The dedup key is the composite tuple:

```
("url", source_url, date, category)            # when source_url is present
("nourl", date, category, sha256(summary[:200])[:16])  # fallback when source_url is missing
```

**Why composite, not source_url alone?** Inspection of Bellingham HS revealed that ONE Cascadia Daily News article (the 2023-12-12 piece) was correctly extracted into TWO distinct findings — one about the 2023 criminal-charges resolution, one about a separate 2022 federal lawsuit covered in the same article. Same source_url, different dates, different events. Source-url-only dedup would incorrectly drop one of these legitimate findings. The (url, date, category) composite preserves both because their dates differ.

**Why content-hash fallback?** Some findings may lack a source_url (rare but possible — e.g., user-submitted field reports in a future phase). Falling back to a hash of the summary text keeps genuinely distinct url-less findings from collapsing into one.

### Collision Priority

When the same composite key appears in BOTH `district_context` and `context` (i.e., the same article was independently extracted by both Pass 1 and Pass 2), the **district_context entry wins**. The school-level entry is dropped from the deduped output but recorded in `metadata.dedup_collisions` for traceability.

Rationale: district-level findings tend to use district-actor language ("Bellingham Public Schools admitted liability...") that aligns with Stage 2's Rule 7 district-attribution framing. The school-level version often re-frames the same event from the school's vantage and would conflict with the district-level framing if both were passed in.

---

## Part C — Acceptance Test

### File
`phases/phase-5/test_layer3_findings.py` — runs `get_findings_for_stage0()` against eight cases including the two known-interesting ones (Bellingham HS = district-only, Squalicum = real cross-context collision).

Full report: `phases/phase-5/layer3_findings_test_output/report.md`.

### Results

| NCES ID | School | school | district | total | deduped | collisions |
|---------|--------|-------:|---------:|------:|--------:|-----------:|
| 530042000099 | Bellingham HS | 0 | 6 | 6 | **6** | 0 |
| 530042000113 | Sehome HS | 4 | 6 | 10 | **10** | 0 |
| 530042002693 | Squalicum HS | 2 | 6 | 8 | **7** | **1** |
| 530042000104 | Fairhaven Middle (golden) | 1 | 6 | 7 | **7** | 0 |
| 530042000117 | Whatcom Middle | 1 | 6 | 7 | **7** | 0 |
| 530042001738 | Options HS | 1 | 6 | 7 | **7** | 0 |
| 530033000043 | Bainbridge HS (control) | 1 | 4 | 5 | **5** | 0 |
| 999999999999 | (bogus ID) | — | — | — | error path | — |

### Verifications

1. **Bellingham HS** — `context.status = no_findings` so Stage 0 input is the 6 district findings only. Function returned 6 findings with zero dedup. PASS.
2. **Sehome HS** — 4 school-level + 6 district-level findings, no source_url overlap. Function returned all 10. PASS.
3. **Squalicum HS** — the known collision case. The 2026 bus-assault liability article was independently extracted by both Pass 1 and Pass 2. Function dedups to 7, keeping the district_context version, recording the school-level version in `metadata.dedup_collisions`. The collision key is `("url", <bus-assault URL>, "2026-02-05", "investigations_ocr")` exactly as expected. PASS.
4. **Fairhaven (golden), Whatcom Middle, Options HS** — each has 6 district + 1 school finding, no collisions. Function returns 7. PASS.
5. **Bainbridge HS (non-Bellingham control)** — different district, smaller district_context (4 findings), 1 school finding, no collisions. Function returns 5. Confirms behavior is consistent across districts. PASS.
6. **Bogus NCES ID** — `find_one` returns None; function returns `([], metadata_with_error)` and the error message names what the user should check (12-char string, leading zeros, state loaded). PASS.

---

## What Was NOT Done

- No MongoDB writes. The function is read-only against the schools collection.
- No new findings were created. No findings were duplicated into separate MongoDB records (per the handoff: "Do NOT duplicate findings into separate MongoDB records. The dual-context model is already correct; just read both fields.")
- No production Stage 0/1/2 run was triggered. Phase 5 production is gated on the blockers listed in `phases/phase-4.5/exit.md` (Phase 3 rerun, sensitivity review completion, batch budget approval, builder sign-off on the 50-school report).

---

## Files Touched

- New: `pipeline/layer3_findings.py` — production query function with dedup logic.
- New: `phases/phase-5/test_layer3_findings.py` — exercises the function on 8 cases.
- New: `phases/phase-5/layer3_findings_test_output/<8 per-case JSONs>` — diagnostic dumps.
- New: `phases/phase-5/layer3_findings_test_output/report.md` — test report.
- New: `docs/receipts/phase-5/task2_district_context.md` (this file).

---

## Decision

**Task 2: PASS.**

district_context is populated on every Bellingham school (25 / 25), with all three Title IX-related district findings present on every school exactly as the Phase 4 Pass 1 design intended. The production query function `get_findings_for_stage0()` correctly reads both `context` and `district_context`, deduplicates by composite key, prefers district-level framing on collision, and records dedup decisions in metadata. The function passes all eight test cases including the canonical Squalicum cross-context collision and a bogus-ID error-path test.

Phase 5 production code can now build on this function without writing additional MongoDB queries. Stage 2's district-attribution rule (Rule 7) gets correct inputs.

**Approved by:** Claude Code (Phase 5 agent)
**Date:** 2026-04-30
