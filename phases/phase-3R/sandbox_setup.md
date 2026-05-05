# Phase 3R — Experimental Sandbox Setup

Created 2026-05-03 to support upcoming Phase 3R ingestion experiments
without any risk to production data.

## Database

- **Name:** `schooldaylight_experiment`
- **Cluster:** same Atlas cluster as `schooldaylight` (no new infrastructure)
- **Created from:** clone of production `schooldaylight.schools` collection
- **Document count after clone:** **2,532** (matches production exactly)
- **Clone method:** `find({})` from production → `insert_many` into experiment,
  preserving every `_id` (12-char NCESSCH primary key) and every nested field.
  No transformations applied during the copy.

### Verification

| Check | Result |
|---|---|
| Pre-flight: `schooldaylight_experiment` did not exist before this task | PASS |
| Production count read at start | 2,532 |
| Experiment count after clone | 2,532 |
| 5 random docs deep-equal between prod and experiment | 5/5 PASS |

The 5 spot-checked schools (RNG seed `20260503`, reproducible):

| `_id` | Name |
|---|---|
| 530393000610 | Washington Elementary School |
| 530000102795 | Thunder Mountain Middle School |
| 530682000998 | Franklin Elementary |
| 530927001579 | Lewis and Clark High School |
| 530870001460 | Delong Elementary School |

## Isolation conventions for Phase 3R scripts

The convention going forward:

- **Production-touching scripts** read `config.MONGO_URI` and use database name
  `config.DB_NAME` (`"schooldaylight"`).
- **Experimental scripts** read `config.MONGO_URI_EXPERIMENT` and use database
  name `config.DB_NAME_EXPERIMENT` (`"schooldaylight_experiment"`).
- **Every experimental script must verify `db.name` contains the substring
  `"experiment"` before any write operation.** A one-line guard at the top of
  the script is the canonical pattern:

  ```python
  assert "experiment" in db.name, \
      f"Refusing to write — database name '{db.name}' is not an experiment db."
  ```

  This is a defence-in-depth check: even if `MONGO_URI_EXPERIMENT` is mis-set
  in `.env`, the assertion fails before any document is touched.

## .env addition required

`config.py` now reads `MONGO_URI_EXPERIMENT` (defaulting to empty string if
unset). Add the following line to `.env` (same connection string as `MONGO_URI`,
but with the database in the path replaced):

```
MONGO_URI_EXPERIMENT=mongodb+srv://<username>:<password>@<cluster-host>/schooldaylight_experiment?retryWrites=true&w=majority
```

The credentials and cluster host are identical to `MONGO_URI`; only the database
segment of the path changes from `/schooldaylight` to `/schooldaylight_experiment`.

## Production untouched

No write operation hit `schooldaylight` during this task. The clone was a
read-from-prod, write-to-experiment sequence; production's count and content
are unchanged. The cluster's `admin` and `local` databases were also untouched.

Databases on the cluster after this setup:
- `admin`
- `local`
- `schooldaylight` (production — unchanged)
- `schooldaylight_experiment` (new — 2,532-doc clone)

## Files changed by this task

- `config.py` — added `MONGO_URI_EXPERIMENT`, `DB_NAME`, `DB_NAME_EXPERIMENT` constants.
- `phases/phase-3R/sandbox_setup.md` — this file.
- `.env` — **builder must add `MONGO_URI_EXPERIMENT` line** (CC does not write to `.env`).
