# School Daylight

## About This Project

Civic transparency tool generating school briefings from public education data. Batch ETL pipeline → MongoDB → AI enrichment → cached briefings → Streamlit frontend. NOT a rating site. An interpretation layer.

The builder is not a developer. All code is written by Claude Code agents (referred to as "CC" throughout this file). Code must be understandable, maintainable, and debuggable by someone who reads Python but doesn't write it — whether the builder, a future contributor, or future Claude instances.

## Architecture

```
pipeline/           # ETL scripts, run in numbered order (01_, 02_, etc.)
config.py           # SINGLE source of truth for all credentials and settings
cleaning_rules.yaml # Every data transformation, readable without code
prompts/            # AI prompts, versioned plaintext, never embedded in code
tests/              # Testing utility scripts
app/                # Streamlit frontend
docs/               # Methodology, data governance, build log
```

- **Database:** MongoDB Atlas (free M0 tier). One document per school, everything embedded.
- **Primary key:** NCES ID (12-char string, never convert to integer).
- **AI stack:** Haiku for context enrichment, Sonnet for narrative generation. Batch API for bulk runs.
- **Frontend:** Streamlit. No auth, no tracking.

## Critical Rules

### Credentials
- ALL credentials in `config.py` which reads from `.env`. No exceptions.
- NEVER hardcode connection strings, API keys, or secrets anywhere else.
- `.env` is in `.gitignore`. Always. Check before every commit.
- `.env.example` shows required variables without real values.

### Data Integrity
- Suppressed values → `null` with `"suppressed": true`. NEVER store as zero or empty string.
- Zero means "zero incidents." Null-suppressed means "can't tell you." These are different.
- NCES IDs are 12-character strings. Never let pandas convert them to integers (leading zeros get stripped).
- All percentages stored as decimals (0.0–1.0). Never mix scales.
- Pipeline is idempotent. Drop and recreate collection on each full load. Safe to run twice.
- Every MongoDB document must include `metadata.dataset_version` (e.g., `"2026-02-v1"`) and `metadata.load_timestamp` (ISO 8601) at the document root. These enable provenance tracking across pipeline runs.

### Code Conventions

**Logging:** Every script logs to both console and a timestamped log file in `logs/`. Log messages are complete English sentences, not codes.

**Error messages:** Every error must say three things: what went wrong, why it probably happened, and what to try. Example: `Could not connect to MongoDB Atlas. This usually means: (1) your internet connection is down, (2) the connection string in .env is wrong, or (3) Atlas IP whitelist doesn't include your current IP. Check .env MONGO_URI and try again.`

**Config over code:** Anything that might need to change lives in YAML or .env, not in Python. Cleaning rules, flag thresholds, suppression markers, prompt templates, comparison group definitions. If it's a number or a string that affects output, it's config.

**File naming:** Scripts are numbered for run order: `01_load_nces.py`, `02_load_crosswalk.py`. The sequence is visible from the directory listing.

**Comments:** Comments explain WHY, not WHAT. One-line docstring per function. Comment any non-obvious choice.

**Dependency pinning:** `requirements.txt` with exact versions (`pandas==2.2.1`, not `pandas>=2.0`). A `pip install` today must produce the same result six months from now.

**Git commits:** Every commit message explains what changed AND why.

### Repo Navigation Conventions

Every pipeline script and major module starts with a grep-able header block. Searchable across the entire repo.

```python
# PURPOSE: Load OSPI discipline data and join to CCD spine
# INPUTS: WA-raw/ospi/Report_Card_Discipline_2023-24.csv, data/ccd_wa_directory.csv
# OUTPUTS: Writes discipline fields into MongoDB documents
# JOIN KEYS: DistrictCode + SchoolCode → ST_SCHID → NCESSCH
# SUPPRESSION HANDLING: "N<10" → null + suppressed; "*" → null + suppressed; "No Students" → null
# RECEIPT: phases/phase-2/receipt.md — discipline section
# FAILURE MODES: Comma-in-IDs (strip before join); grade label "All" not "All Grades"
```

Use these standardized trace tags inline so any field, rule, or test can be found with a single search.

```python
# LINEAGE: discipline.ospi.rate           — marks where a schema field is computed
# SOURCE: OSPI_Discipline_2023.csv:DisciplineRate  — marks where a raw column is read
# RULE: SUPPRESSION_OSPI_N_LT_10         — marks where a cleaning/suppression rule is applied
# TEST: GOLDEN_SCHOOL_FAIRHAVEN          — marks where golden school verification happens
```

Search examples: `rg "LINEAGE: discipline"` finds every place discipline fields are touched. `rg "RULE: SUPPRESSION"` finds every suppression handler. `rg "TEST: GOLDEN"` finds every golden school check.

## When Expected Behavior Doesn't Match Reality

The following situations all trigger STOP AND REPORT:

- A credential, API key, file path, or environment variable that was expected does not work or is not present
- A database query, API call, or file operation returns an unexpected error or unexpected results
- Data CC needs is not where CC expected it to be
- An instruction CC is following references something CC cannot find
- CC's own action produces a result CC did not anticipate
- A retry of an operation produces different results than the first attempt

In any of these situations, CC's default action is to stop, report what was expected versus what happened, and wait for builder direction.

## Destructive Operations

Operations that delete, drop, or overwrite production data require explicit builder approval before CC writes the command. Propose in plain English, get plain-English approval, then write and execute.

Includes: drop_collection, deleteMany without _id filter, drop_database, update_many touching critical fields (layer3_narrative, metadata, source data), schema modifications, and any ad-hoc destructive operation outside approved pipeline scripts.

## Commands

```bash
# Run the full pipeline
python pipeline/run_pipeline.py

# Run a single step
python pipeline/01_load_nces.py

# Run the testing utility
python tests/run_tests.py

# Run tests for a specific layer
python tests/run_tests.py --layer data_integrity

# Check the health of everything
python scripts/health_check.py

# Launch the frontend locally
streamlit run app/main.py
```

## Verification Receipts

Every phase produces a `verification_receipt.md` in `docs/receipts/`. The receipt is a plain-English document showing what was tested, expected vs. actual results, pass/fail for each check, plain-English explanation of any failures, and suggested fixes. The builder reads the receipt, not the code. If green, proceed. If red, the agent stops and reports.

Every Phase 2+ receipt must include SHA256 hashes for all source input files. This makes idempotent reruns provable, not just aspirational.

## Golden School

Fairhaven Middle School (Bellingham, WA) is the hand-verified reference school. After any data load or pipeline change, Fairhaven must pass field-by-field verification. If Fairhaven is wrong, nothing ships. See `tests/golden_schools.yaml` for expected values.

## File Boundaries

- **Safe to edit:** everything in `pipeline/`, `app/`, `tests/`, `prompts/`, `docs/`
- **Edit with caution:** `config.py`, `cleaning_rules.yaml`, `requirements.txt`
- **Never touch:** `.env` (contains real secrets), `.git/`, `node_modules/`, `__pycache__/`
- **Never delete:** `docs/receipts/`, `docs/build_log.md`, `logs/`

## Health Check Script

`scripts/health_check.py` tests all external dependencies and reports in plain English. If any check fails, it says why and what to do about it.

## Key Design Documents

For detailed architecture and methodology, see these docs (read them, don't embed them in context):
- `docs/foundation.md` — Full product specification, mission, architecture, known risks
- `docs/build_sequence.md` — Phase-by-phase build plan with prompts and verification gates
- `docs/testing_utility.md` — 5-layer test specification, golden school pattern
- `docs/data_dictionary.yaml` — Every source column mapped to schema (created in Phase 1)
- `docs/build_log.md` — Chronological record of every decision with reasoning
- `docs/how_to_find_anything.md` — Builder's cheat sheet for navigating the repo with grep
