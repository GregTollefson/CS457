# FRED Database Prototype — Implementation Status - 09/Oct

## Project Root

The project is currently organized under:

```text
~/fal2026/CS457/projects
```

Current high-level structure:

```text
projects/
├── .env
├── .venv/
├── FredPOC/
├── app/
├── requirements.txt
├── config/
├── docs/
├── sql/
├── src/
└── tests/
```

`FredPOC/` contains the earlier exploratory FRED proof-of-concept work, including the existing notebook and project plan. The new application code is being developed in `src/`, `sql/`, `app/`, and `tests/`.

## Software Installed

The development environment is running under Ubuntu in WSL.

Installed and verified:

- Python virtual environment: `.venv`
- PostgreSQL 16.15
- Psycopg 3.3.6
- Streamlit 1.65.0
- pandas
- requests
- python-dotenv
- JupyterLab
- Codex CLI 0.160.0

Python package consistency was checked with:

```bash
python -m pip check
```

Result:

```text
No broken requirements found.
```

## PostgreSQL Setup

A dedicated PostgreSQL user and database were created for the prototype:

```text
Database: fred_db
User:     fred_user
```

The PostgreSQL service is installed and running under WSL.

The application configuration is stored in the project `.env` file. The file contains the existing FRED API key and PostgreSQL connection settings.

The `.env` file is excluded from Git through `.gitignore`.

Relevant configuration variables are:

```text
FRED_API_KEY
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

Secrets are not printed or committed to the repository.

## Implemented Python Components

### `src/config.py`

Implemented configuration loading with `python-dotenv`.

The module:

- Loads the FRED API key.
- Locates the `.env` file at the project root.
- Loads the PostgreSQL configuration values.
- Exposes:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT`

### `src/database.py`

Implemented the initial PostgreSQL connection layer using Psycopg 3.

The module provides:

```python
get_connection()
```

The function:

- Reads the database configuration from `src.config`.
- Verifies that all five required database settings are present.
- Opens and returns a Psycopg connection.
- Leaves connection cleanup to the caller.

At the initial connection milestone, no tables had been created. The existing
`fred_db` now contains `series` and `observations`, including 574 observations
for `APU000072610` with two missing values stored as SQL `NULL`. The research
model migration has **not yet been applied to `fred_db`**.

### `src/fred_api.py`

Implemented FRED metadata and observation retrieval, pandas DataFrame handling,
observation date conversion, and missing-value cleaning. FRED is an external
data source rather than the organizing structure of the research database.

### `src/mapping.py` and `config/series_mapping.json`

Research classifications are maintained in `config/series_mapping.json`.
`src/mapping.py` loads and validates the mapping, including required fields,
stable codes, conflicting definitions, and unknown requested series IDs.
Mapping validation occurs before FRED or database I/O.

Current configured series:

| Series | Category | Metric | Source |
|---|---|---|---|
| `APU000072610` | Price (`price`) | Electricity Price (`electricity_price`) | FRED |
| `CAPG2211S` | Capacity (`capacity`) | Utility Capacity (`utility_capacity`) | FRED |

Stable codes identify research categories and metrics; names are display values.
FRED metadata such as title, units, frequency, dates, popularity, and notes
continues to come from FRED rather than the mapping.

### `src/ingest.py`

Ingestion is now mapping/configuration driven. Supported commands, run from the
project root using the existing virtual environment, include:

```bash
.venv/bin/python -m src.ingest --series <SERIES_ID> [...]
.venv/bin/python -m src.ingest --all
```

For each selected series, ingestion:

1. Reads and validates the mapping and confirms the source is FRED.
2. Retrieves FRED metadata and checks that its ID matches the requested series.
3. Retrieves and cleans observations, and prepares metadata dates/timestamps.
4. Only then opens the PostgreSQL connection/transaction.
5. Upserts category, metric, source, series, and observations within one transaction.

Successful connection context exit commits; failures roll back database writes.
Stable identifiers, uniqueness constraints, and `ON CONFLICT` upserts make
repeated ingestion idempotent. Missing FRED values continue to pass through
pandas `NaN` and are stored as SQL `NULL`.

### `src/init_db.py`

Installs `sql/schema.sql` for a clean database. Existing databases use the
incremental migration instead; clean-schema initialization is not a substitute
for upgrading existing tables.

### `src/validate_db.py`

Provides read-only validation of:

- Required tables
- Primary keys
- Foreign keys
- Uniqueness constraints
- Orphan references
- Duplicate research identifiers
- Preservation of `APU000072610`, its 574 observations, and two SQL `NULL` values

PostgreSQL read-only transaction mode provides an additional safeguard. The
validator reports PASS/FAIL results and returns a non-zero exit status on failure.

## Research Model and Schema

The implemented research model uses five core tables:

```text
category
metric
source
series
observations
```

Relationships:

```text
category 1 -> many metric
metric   1 -> many series
source   1 -> many series
series   1 -> many observations
```

The model organizes electricity-system research variables independently of
FRED's organizational structure. Category and metric express our interpretation;
source identifies where each series originates. Natural identifiers have UNIQUE
constraints alongside surrogate primary keys, and the model remains in 3NF.

Schema and migration work completed:

- `sql/schema.sql` defines the full five-table schema for clean installations.
- `sql/migrations/001_add_research_model.sql` incrementally upgrades an existing database.
- The migration creates `category`, `metric`, and `source`.
- It adds `metric_id` and `source_id` foreign keys to `series`.
- These columns are intentionally nullable during the migration transition so
  existing series rows are preserved.
- Existing series and observation rows are not reset, truncated, or replaced.

The existing production/development `fred_db` has **not yet had this migration
applied**. Its current two-table data remains the preservation baseline.

## Database Integration Test — Initial Milestone

Created:

```text
tests/test_database.py
```

The test:

1. Obtains a PostgreSQL connection using `get_connection()`.
2. Creates a cursor.
3. Executes:

```sql
SELECT current_database(), current_user;
```

4. Verifies that a result is returned.
5. Verifies that the returned database matches `DB_NAME`.
6. Verifies that the returned PostgreSQL user matches `DB_USER`.
7. Verifies that the connection closes cleanly.

The test is run from the project root with:

```bash
.venv/bin/python -m unittest discover -s tests -p test_database.py
```

Observed result:

```text
Ran 1 test in 0.009s

OK
```

This confirms that the following path is working end-to-end:

```text
.env
  ↓
python-dotenv
  ↓
src/config.py
  ↓
src/database.py
  ↓
Psycopg 3
  ↓
PostgreSQL
  ↓
fred_db / fred_user
```

## Automated Testing

The research-model implementation reached a passing **23-test** suite. The
subsequent transaction-ordering improvement added one focused test; the current
automated suite contains **24 tests**.

Coverage includes:

- Mapping validation and malformed/missing mappings
- Mocked FRED API handling and missing-value cleaning
- FRED retrieval/cleaning and metadata preparation before database connection
- Migration preservation and clean schema installation
- Validator behavior
- Stable category, metric, and source upserts
- Idempotent repeated ingestion
- Transaction rollback on database write failures
- Shared FRED source behavior across series
- Metadata/value revisions

Run the full suite from the project root:

```bash
.venv/bin/python -m unittest discover -s tests
```

Latest observed result after the ordering improvement:

```text
Ran 24 tests in 1.263s

OK
```

No failures, errors, or skips were reported. Database write tests use a
disposable local PostgreSQL cluster; external FRED HTTP responses are mocked.
The original connection test performs only a SELECT against the configured
database.

## Real Vertical-Slice Test

A disposable PostgreSQL database named `fred_slice_test` was used so the
existing `fred_db` was not modified. The clean five-table schema installed
successfully, and real FRED ingestion was performed for `CAPG2211S`.

Observed results:

| Item | Result |
|---|---|
| Category | `capacity` / Capacity |
| Metric | `utility_capacity` / Utility Capacity |
| Source | FRED |
| Series | `CAPG2211S` |
| Title | Industrial Capacity: Utilities: Electric Power Generation, Transmission, and Distribution (NAICS = 2211) |
| Frequency | Monthly |
| Units | Index 2017=100 |
| Observations | 716 |
| Missing/NULL observations | 0 |
| First observation | 1967-01-01 |
| Last observation | 2026-08-01 |

The relationship chain was verified in PostgreSQL:

```text
Capacity -> Utility Capacity -> CAPG2211S -> observations
CAPG2211S -> FRED
```

The same ingestion was run a second time. Row counts remained:

| Table | Rows |
|---|---:|
| category | 1 |
| metric | 1 |
| source | 1 |
| series | 1 |
| observations | 716 |

This confirms real end-to-end idempotence. These results belong to the
disposable vertical-slice database, not the existing `fred_db`.

## Codex Workflow

Codex CLI is installed in WSL and is being run directly from the project root:

```bash
cd ~/fal2026/CS457/projects
codex
```

The first Codex task was intentionally limited to the PostgreSQL connection layer.

Codex:

- Inspected the project structure without reading `.env`.
- Modified `src/config.py`.
- Modified `src/database.py`.
- Created `tests/test_database.py`.
- Did not modify `.env`.
- Did not modify the Streamlit application.
- Did not modify the existing FRED proof-of-concept notebook.
- Did not create database tables.

The database integration test initially could not run inside the Codex network-restricted sandbox, so the same test was approved to run in the local WSL environment. It then passed successfully.

## Current Status

Completed and tested:

- [x] Project directory structure
- [x] Python virtual environment
- [x] FRED API key stored in `.env`
- [x] PostgreSQL installed
- [x] PostgreSQL service running
- [x] Dedicated PostgreSQL user created
- [x] Dedicated PostgreSQL database created
- [x] Psycopg installed
- [x] Streamlit installed
- [x] `.env` excluded from Git
- [x] Configuration loading implemented
- [x] PostgreSQL connection function implemented
- [x] Python-to-PostgreSQL integration test implemented
- [x] Integration test passed

- [x] Five-table research schema defined
- [x] Incremental research-model migration written and tested
- [x] FRED API module and observation cleaning implemented
- [x] Research series mapping and validation implemented
- [x] Configuration-driven transactional ingestion implemented
- [x] External FRED I/O moved before the PostgreSQL transaction
- [x] Read-only database validator implemented
- [x] Full automated suite passed (24 tests)
- [x] Real CAPG2211S vertical-slice ingestion passed in `fred_slice_test`
- [x] Real end-to-end idempotence verified

Not yet completed:

- [ ] Back up and migrate the existing `fred_db`
- [ ] Validate the migrated `fred_db`
- [ ] Populate existing APU000072610 metric/source relationships
- [ ] Add remaining research series
- [ ] Application query layer
- [ ] Streamlit user interface
- [ ] End-to-end FRED → PostgreSQL → Streamlit workflow

The new architecture has been implemented and tested, and the disposable
vertical-slice test passed. **The existing `fred_db` has not yet been migrated.**

## Next Planned Steps

1. Back up `fred_db`.
2. Apply `sql/migrations/001_add_research_model.sql` to `fred_db` after review.
3. Run `src/validate_db.py` against the migrated database:

   ```bash
   .venv/bin/python -m src.validate_db
   ```

4. Reingest `APU000072610` so its new `metric_id` and `source_id` relationships
   are populated:

   ```bash
   .venv/bin/python -m src.ingest --series APU000072610
   ```

5. Verify preservation of its existing observations and SQL `NULL` values.
   Reingestion refreshes data from FRED, so compare against the backed-up
   baseline as well as running the validator.
6. Continue adding the remaining research series through the mapping configuration.

The validator currently checks the exact 574-observation/two-NULL baseline.
Any change after a FRED refresh must be investigated rather than silently
accepted as preservation.

## Project Timeline

| Date | Target |
|---|---|
| **Now–Oct 11** | **Milestone 2:** Schema and isolated database tests completed; back up and migrate existing `fred_db` |
| **Oct 12–18** | **Milestone 3:** Real CAPG2211S vertical slice completed; validate live migration and expand research ingestion |
| **Oct 19–25** | Finish Project Design document: architecture, schema, tech stack, infrastructure, and planned UI |
| **Oct 26** | **Project Design Due** |
| **Oct 27–Nov 8** | Expand ingestion, add query layer, joins, and date-range queries |
| **Nov 9–20** | Build Streamlit UI and complete the end-to-end workflow |
| **Nov 21–26** | Testing, cleanup, README, `requirements.txt`, and database setup/reset scripts |
| **Nov 27–29** | Final regression testing and submission packaging |
| **Nov 30** | **Completed Project Due** |
| **Dec 1–5** | Prepare demo script, screenshots, and presentation talking points |
| **Dec 6** | Record and edit YouTube demo |
| **Dec 7** | **Project Demo Due** |

### Target State by Project Design Deadline

By **Oct 26**, the goal is to have a working vertical slice that demonstrates the feasibility of the design:

- PostgreSQL connection working
- Relational schema defined
- Tables created successfully
- At least one FRED series loaded into PostgreSQL
- One or more SQL queries working against the stored data

### Target State by Project Completion Deadline

By **Nov 30**, the complete application should support the full workflow:

```text
FRED API
   ↓
Python / pandas
   ↓
PostgreSQL
   ↓
Psycopg query layer
   ↓
Streamlit
   ↓
User interaction
```
