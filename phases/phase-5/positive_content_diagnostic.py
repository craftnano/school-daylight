# PURPOSE: Diagnostic — scan all 2,532 schools' raw Phase 4 findings (context.findings
#          + district_context.findings, pre-Stage 0/1) for matches against a positive-
#          content vocabulary, then trace each match's pipeline disposition (Stage 0
#          drop / Stage 1 exclude / Stage 1 include / appears in final narrative).
#
# READ-ONLY. No MongoDB writes.

import os, sys, json, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
import config
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
from pymongo import MongoClient
from pipeline.layer3_findings import get_findings_for_stage0

OUT_PATH = os.path.join(PROJECT_ROOT, "phases", "phase-5", "positive_content_diagnostic.md")

# Vocabulary patterns. Each entry: (label, regex). Case-insensitive.
PATTERNS = [
    # --- Academic recognitions ---
    ("Washington Achievement Award", r"washington achievement award"),
    ("Achievement Award (general)", r"\bachievement award"),
    ("Blue Ribbon", r"blue ribbon"),
    ("Schools of Distinction", r"schools? of distinction"),
    ("OSPI recognition", r"ospi (?:has )?recogn"),
    ("ESSA Distinguished", r"essa distinguished"),
    ("Title I Distinguished", r"title i distinguished"),
    ("Civil Rights Project recognition", r"civil rights project"),
    ("Green Ribbon", r"green ribbon"),
    ("National Blue Ribbon", r"national blue ribbon"),
    ("Milken Award", r"milken (?:award|educator)"),
    ("Presidential Award", r"presidential award"),
    ("National Board Certified", r"national board (?:certified|certification|teacher)"),
    ("Teacher of the Year", r"teacher of the year"),
    # --- Academic competitions ---
    ("State champion", r"\bstate champion"),
    ("State finalists", r"state finalist"),
    ("National champion", r"\bnational champion"),
    ("Knowledge Bowl state+", r"knowledge bowl[^.]{0,80}(?:state|national|regional)"),
    ("Science Olympiad state+", r"science olympiad[^.]{0,80}(?:state|national|regional)"),
    ("Math Counts", r"math\s*counts"),
    ("Math Olympiad state+", r"math olympiad[^.]{0,80}(?:state|national|regional)"),
    ("Spelling Bee state+", r"spelling bee[^.]{0,80}(?:state|national|regional)"),
    ("Robotics championship", r"robotics championship"),
    ("FIRST competition", r"\bfirst (?:robotics|competition|tech challenge|lego league)"),
    ("Future Problem Solving", r"future problem solving"),
    ("DECA state+", r"\bdeca\b[^.]{0,80}(?:state|national|regional)"),
    ("FBLA state+", r"\bfbla\b[^.]{0,80}(?:state|national|regional)"),
    ("Quiz Bowl", r"quiz bowl"),
    # --- Substantive programs ---
    ("Dual immersion / dual language", r"dual (?:immersion|language)"),
    ("International Baccalaureate", r"international baccalaureate|\bib (?:program|diploma|world school)"),
    ("AP Capstone", r"ap capstone"),
    ("Magnet school", r"magnet school"),
    ("Career pathway", r"career pathway"),
    ("STEM/STEAM designation", r"\bstem\b[^.]{0,40}(?:designation|certified|recognition)|steam[^.]{0,40}(?:designation|certified|recognition)"),
    # --- Sustained measurable improvements ---
    ("Graduation rate (positive)", r"graduation rate[^.]{0,80}(?:highest|record|improv|gain|rise|rose|increased|all[- ]time)"),
    ("Achievement gap closed/narrowed", r"achievement gap[^.]{0,80}(?:closed|narrowed|reduc|shrank)"),
    ("Proficiency multi-year improvement", r"proficiency[^.]{0,120}(?:year[- ]over[- ]year|multi[- ]year|sustained|consistent|three years|five years)"),
]
COMPILED = [(label, re.compile(pat, re.IGNORECASE)) for label, pat in PATTERNS]


def find_matches(text):
    """Return list of (label, snippet) for every pattern that fires in text."""
    if not text:
        return []
    hits = []
    for label, rx in COMPILED:
        m = rx.search(text)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            hits.append((label, text[start:end].replace("\n", " ")))
    return hits


def main():
    db = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=15000).get_default_database()

    # Index Stage 1 results by NCES for disposition lookup.
    stage1_by_nid = {}
    with open(os.path.join(PROJECT_ROOT, "phases", "phase-5", "production_run",
                           "stage1_results.jsonl")) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            stage1_by_nid[r["nces_id"]] = r

    # Index Stage 0 drops + Stage 1 included by NCES.
    # stage0_dropped: list of {finding_index, rule, extraction}
    # stage1_included: list of {finding_index, original_text, ...}
    # stage1_excluded: only present when stage1 had ≥1 included; rationales lost otherwise.

    # ---- Walk every school ----
    all_schools = list(db.schools.find(
        {}, {"_id": 1, "name": 1, "district.name": 1,
             "context": 1, "district_context": 1,
             "layer3_narrative": 1}
    ))
    print(f"Scanning {len(all_schools)} schools...")

    schools_with_positive = []  # list of dicts with full diagnostic per school
    label_counts = Counter()
    category_counts = Counter()
    disposition_counts = Counter()

    for school in all_schools:
        nid = school["_id"]
        name = school.get("name", "?")
        district = (school.get("district") or {}).get("name", "?")
        narrative_text = ((school.get("layer3_narrative") or {}).get("text") or "")
        narrative_status = ((school.get("layer3_narrative") or {}).get("status") or "?")

        s1 = stage1_by_nid.get(nid, {})
        stage0_dropped_indices = {d.get("finding_index") for d in s1.get("stage0_dropped", [])}
        stage1_included_texts = [(f.get("finding_index"), (f.get("original_text") or "").strip())
                                 for f in s1.get("stage1_included", [])]
        stage1_included_index_set = {i for i, _ in stage1_included_texts}

        # Pull deduped findings (the same set Stage 0 would see).
        try:
            deduped, _meta = get_findings_for_stage0(db, nid)
        except Exception:
            deduped = []

        for idx, f in enumerate(deduped):
            summary = (f.get("summary") or "")
            cat = f.get("category", "?")
            url = f.get("source_url", "")
            hits = find_matches(summary)
            if not hits:
                continue

            # Disposition: 1-indexed since Phase A built findings_for_prompt with index = j+1
            finding_index = idx + 1

            if finding_index in stage0_dropped_indices:
                disp = "stage0_dropped"
                # Find the rule
                rule = next((d.get("rule") for d in s1.get("stage0_dropped", [])
                             if d.get("finding_index") == finding_index), "?")
                disp_detail = f"stage0:{rule}"
            elif finding_index in stage1_included_index_set:
                # Survived Stage 1. Did it reach the final narrative?
                # Match by URL or summary fragment.
                in_narrative = False
                if url and url in narrative_text:
                    in_narrative = True
                else:
                    # Fallback: check first 60 chars of summary
                    snippet = re.sub(r"</?cite[^>]*>", "", summary).strip()[:60]
                    if snippet and snippet in narrative_text:
                        in_narrative = True
                disp = "in_final_narrative" if in_narrative else "stage1_included_but_not_in_narrative"
                disp_detail = disp
            elif s1:
                # Stage 1 ran (we have a record) but this finding wasn't in included.
                # Either it was Stage 0-dropped without being recorded (unlikely) or
                # Stage 1 excluded it (rationales not persisted unless ≥1 included).
                disp = "stage1_excluded"
                disp_detail = "stage1_excluded (rationale not persisted)"
            elif narrative_status == "no_findings":
                disp = "no_findings_path"
                disp_detail = "no_findings (entire school had no Phase 4 enrichment to triage)"
            elif narrative_status == "stage1_filtered_to_zero":
                # We have a checkpoint status but no stage1_results entry — Stage 1
                # ran with included=0, so the runner skipped persisting.
                disp = "stage1_filtered_to_zero (no included)"
                disp_detail = "stage1_filtered_to_zero (rationales not persisted)"
            else:
                disp = "unknown"
                disp_detail = f"unknown (narrative_status={narrative_status})"

            for label, snippet in hits:
                label_counts[label] += 1
                category_counts[cat] += 1
                disposition_counts[disp] += 1
                schools_with_positive.append({
                    "nces_id": nid, "name": name, "district": district,
                    "label": label, "category": cat, "snippet": snippet,
                    "disposition": disp, "disposition_detail": disp_detail,
                    "narrative_status": narrative_status,
                    "url": url,
                })

    # ---- Roll up unique schools ----
    schools_with_any_positive = {x["nces_id"] for x in schools_with_positive}
    schools_with_positive_in_final = {
        x["nces_id"] for x in schools_with_positive if x["disposition"] == "in_final_narrative"
    }

    # Cross-table: school × any-disposition for narrative
    schools_disp_summary = defaultdict(set)
    for x in schools_with_positive:
        schools_disp_summary[x["disposition"]].add(x["nces_id"])

    # ---- Write report ----
    lines = []
    lines.append("# Positive-Content Surfacing Diagnostic — full 2,532-school population")
    lines.append("")
    lines.append("Read-only scan of raw Phase 4 findings (`context.findings` + "
                 "`district_context.findings`, pre-Stage 0/1) against a positive-content "
                 "vocabulary, with pipeline-disposition trace per match.")
    lines.append("")
    lines.append("## What the Phase 4 prompts ask for")
    lines.append("")
    lines.append("`prompts/context_enrichment_v1.txt` line 16 names "
                 "**`awards_recognition`** as a category to search: "
                 "*\"Awards, grants, recognitions, honors, Blue Ribbon, Green Ribbon, or "
                 "other formal recognition.\"* Line 18 names **`programs`**: "
                 "*\"Notable programs, initiatives, partnerships, or curriculum changes.\"*")
    lines.append("")
    lines.append("`prompts/district_enrichment_v1.txt` mirrors this at district scope.")
    lines.append("")
    lines.append("**The categories exist in the schema and are named in the search "
                 "instructions, but the prompts do NOT actively target the specific "
                 "positive-content vocabulary in the diagnostic list.** Haiku is told "
                 "*recognition is one category to search for* alongside news, "
                 "investigations, leadership, programs, community investment, and other. "
                 "It is not given examples like 'Washington Achievement Award' or "
                 "'Knowledge Bowl state finalists' or 'Math Counts champions' to anchor "
                 "the search. Coverage is whatever Haiku surfaces unprompted.")
    lines.append("")
    lines.append("## Stage 1 explicitly excludes positive findings")
    lines.append("")
    lines.append("`prompts/layer3_stage1_haiku_triage_v1.txt` line 37: "
                 "*\"Awards, recognitions, and positive achievements: exclude unless "
                 "directly relevant to an adverse finding (e.g., an award that was later "
                 "revoked, a program cited in a lawsuit).\"* This is a categorical "
                 "exclusion in the editorial-triage stage. Even if Phase 4 captures "
                 "positive content, Stage 1 systematically removes it from the parent-"
                 "facing narrative unless tied to an adverse signal.")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- **Schools with at least one positive-content match in raw Phase 4 "
                 f"findings:** {len(schools_with_any_positive)} / {len(all_schools)} "
                 f"({100*len(schools_with_any_positive)/len(all_schools):.1f}%)")
    lines.append(f"- **Schools whose final `layer3_narrative` text contains at least one "
                 f"positive-content match:** {len(schools_with_positive_in_final)} / "
                 f"{len(all_schools)} ({100*len(schools_with_positive_in_final)/len(all_schools):.1f}%)")
    lines.append(f"- **Total positive-content matches across all raw findings:** "
                 f"{sum(label_counts.values()):,}")
    lines.append("")
    lines.append("## Pipeline disposition of matches")
    lines.append("")
    lines.append("| Disposition | Match count | Unique schools |")
    lines.append("|---|---:|---:|")
    for d, c in disposition_counts.most_common():
        n_schools = len(schools_disp_summary.get(d, set()))
        lines.append(f"| {d} | {c} | {n_schools} |")
    lines.append("")
    lines.append("## Distribution by Phase 4 category assignment")
    lines.append("")
    lines.append("| Category | Match count |")
    lines.append("|---|---:|")
    for c, n in category_counts.most_common():
        lines.append(f"| {c} | {n} |")
    lines.append("")
    lines.append("## Top vocabulary matches by frequency")
    lines.append("")
    lines.append("| Vocabulary label | Hits |")
    lines.append("|---|---:|")
    for label, n in label_counts.most_common():
        lines.append(f"| {label} | {n} |")
    lines.append("")
    lines.append("## Per-school detail (every match)")
    lines.append("")
    lines.append("| NCES | School | District | Vocabulary | Phase 4 category | Disposition | Snippet |")
    lines.append("|------|--------|----------|------------|------------------|-------------|---------|")
    schools_with_positive.sort(key=lambda x: (x["district"], x["name"], x["label"]))
    for x in schools_with_positive:
        snip = x["snippet"][:80].replace("|", "\\|")
        lines.append(f"| `{x['nces_id']}` | {x['name']} | {x['district']} | "
                     f"{x['label']} | {x['category']} | {x['disposition']} | {snip}... |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Diagnostic only. No data modified. No prompts modified. No further "
                 "pipeline runs triggered.")

    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote: {OUT_PATH}")
    print(f"Schools with raw positive-content match: {len(schools_with_any_positive)}")
    print(f"Schools where positive content reached final narrative: {len(schools_with_positive_in_final)}")
    print(f"Total matches: {sum(label_counts.values())}")
    print(f"Disposition distribution: {dict(disposition_counts.most_common())}")


if __name__ == "__main__":
    main()
