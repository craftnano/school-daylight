# How to Find Anything in This Repo

This is your operational cheat sheet. You don't need to read Python to navigate this codebase — you need to search for tags.

---

## Find Where a Field Comes From

Every schema field (like `discipline.ospi.rate` or `demographics.frl_count`) is tagged with a `LINEAGE` comment wherever it's computed or written.

```bash
rg "LINEAGE: discipline.ospi.rate"
```

This shows you every file that touches that field — where it's read from raw data, where it's transformed, and where it's written to MongoDB.

---

## Find Where a Raw Column Is Used

Every place a raw CSV column is read is tagged with a `SOURCE` comment.

```bash
rg "SOURCE: OSPI_Discipline"        # everything from the discipline file
rg "SOURCE: CRDC"                    # everything from any CRDC file
rg "SOURCE:.*FRL"                    # anything related to free/reduced lunch
```

---

## Find How Suppression Is Handled

Every suppression rule is tagged with a `RULE: SUPPRESSION_` prefix.

```bash
rg "RULE: SUPPRESSION"               # all suppression handlers
rg "RULE: SUPPRESSION_CRDC"          # CRDC-specific (-9, -5, -3, etc.)
rg "RULE: SUPPRESSION_OSPI"          # OSPI-specific (N<10, *, No Students, etc.)
```

---

## Find a Join Between Data Sources

Every join operation is documented in the module header under `JOIN KEYS`.

```bash
rg "JOIN KEYS:"                      # every join in the pipeline
```

The crosswalk logic (how OSPI codes connect to NCES IDs) is in the module that loads CCD data. Search:

```bash
rg "ST_SCHID"                        # the CCD field that IS the crosswalk
rg "COMBOKEY"                        # the CRDC field that matches NCES ID
```

---

## Find Golden School Checks

Fairhaven Middle School is verified everywhere with a `TEST: GOLDEN_SCHOOL_FAIRHAVEN` tag.

```bash
rg "TEST: GOLDEN"                    # every golden school verification
rg "GOLDEN_SCHOOL_FAIRHAVEN"         # Fairhaven specifically
```

---

## Find What a Pipeline Step Does

Every script has a header block starting with `PURPOSE:`.

```bash
rg "PURPOSE:"                        # one-line summary of every module
rg "INPUTS:"                         # what files each module reads
rg "OUTPUTS:"                        # what each module produces
rg "FAILURE MODES:"                  # known gotchas per module
```

---

## Find Receipts and Verification

Receipts prove the pipeline did what it claims. They live in predictable places.

```bash
rg "RECEIPT:"                        # which receipt each module writes to
ls phases/phase-*/receipt.md         # all phase receipts
ls docs/receipts/                    # all verification receipts
```

---

## Re-run a Single Pipeline Step

Scripts are numbered. Run them individually:

```bash
python pipeline/01_load_nces.py      # just the CCD/NCES step
python pipeline/02_load_ospi.py      # just the OSPI step
```

List them to see the order:

```bash
ls pipeline/*.py
```

---

## Quick Reference: Tag Glossary

| Tag | Meaning | Search example |
|-----|---------|---------------|
| `PURPOSE:` | What this module does | `rg "PURPOSE:"` |
| `INPUTS:` | Files this module reads | `rg "INPUTS:"` |
| `OUTPUTS:` | Files/collections this module writes | `rg "OUTPUTS:"` |
| `JOIN KEYS:` | How this module connects data sources | `rg "JOIN KEYS:"` |
| `SUPPRESSION HANDLING:` | How suppressed values are treated | `rg "SUPPRESSION HANDLING:"` |
| `RECEIPT:` | Where this module's verification lives | `rg "RECEIPT:"` |
| `FAILURE MODES:` | Known gotchas and edge cases | `rg "FAILURE MODES:"` |
| `LINEAGE: field.name` | Where a schema field is computed | `rg "LINEAGE: field.name"` |
| `SOURCE: file:column` | Where a raw column is read | `rg "SOURCE: file"` |
| `RULE: RULE_NAME` | Where a cleaning/suppression rule is applied | `rg "RULE: RULE_NAME"` |
| `TEST: TEST_NAME` | Where a test or verification happens | `rg "TEST: TEST_NAME"` |

---

## The One Command That Tells You Everything

If you're lost, start here:

```bash
rg "PURPOSE:" pipeline/
```

That gives you one sentence per module — the entire pipeline in plain English.
