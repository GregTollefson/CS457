# `src` Directory

This directory contains the Python source code for the FRED Energy Database project.

The code in this directory is responsible for loading configuration, connecting to PostgreSQL, retrieving data from the FRED API, cleaning retrieved data, initializing the database schema, and ingesting FRED series into PostgreSQL.

## Files

### `__init__.py`

Marks the `src` directory as a Python package.

The file is currently empty, but it allows modules in this directory to be imported using package-style imports such as:

```python
from src import config
```

and:

```python
from src.database import get_connection
```

---

### `config.py`

Loads project configuration values from the `.env` file.

The module uses `python-dotenv` to load environment variables containing:

- FRED API key
- PostgreSQL database name
- PostgreSQL username
- PostgreSQL password
- PostgreSQL host
- PostgreSQL port

Example values exposed by this module include:

```python
FRED_API_KEY
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

Keeping these values in `.env` prevents credentials and API keys from being hard-coded into the source code.

---

### `database.py`

Provides the PostgreSQL database connection used by the rest of the application.

The primary function is:

```python
get_connection()
```

This function reads the database configuration from `config.py` and creates a PostgreSQL connection using `psycopg`.

Other modules use this function rather than creating their own database connections.

---

### `fred_api.py`

Contains functions used to communicate with the Federal Reserve Economic Data (FRED) API.

Current responsibilities include:

- Retrieving FRED series metadata
- Discovering series by tag
- Retrieving observations for a selected series
- Converting FRED data into pandas DataFrames
- Cleaning observation data before database insertion
- Converting FRED missing values into pandas `NaN`
- Converting date strings into Python date objects

Current functions include:

#### `get_series_by_tag()`

Retrieves FRED series associated with a tag such as:

```text
energy
```

This function is used to explore available FRED energy datasets.

#### `get_series_metadata()`

Retrieves metadata for a single FRED series.

Examples of metadata include:

- Series ID
- Title
- Frequency
- Units
- Seasonal adjustment
- Observation start date
- Observation end date
- Last update time
- Popularity
- Notes

#### `get_series_observations()`

Retrieves the historical observations for one FRED series.

The raw FRED response contains:

```text
realtime_start
realtime_end
date
value
```

#### `clean_observations()`

Prepares observations for database storage.

The cleaning step:

- Adds the FRED `series_id`
- Converts observation dates to Python date objects
- Converts real-time dates to Python date objects
- Converts observation values to numeric values
- Converts missing FRED values to pandas `NaN`

---

### `init_db.py`

Initializes the PostgreSQL database schema.

This module reads:

```text
sql/schema.sql
```

and executes the SQL statements using the database connection provided by `database.py`.

Run from the project root with:

```bash
.venv/bin/python -m src.init_db
```

For a **new database only**, the complete schema creates `category`, `metric`,
`source`, `series`, and `observations`. `CREATE TABLE IF NOT EXISTS` does not
upgrade an existing table. Existing databases must use the reviewed incremental
SQL files in `sql/migrations/`; do not use `init_db` as a migration runner.

---

### `ingest.py`

Implements the FRED-to-PostgreSQL ingestion pipeline.

For a selected configured FRED series, the module:

1. Loads and validates our research mapping.
2. Upserts category by `category_code`, metric by `metric_code`, and source by
   `source_name`, obtaining their primary keys.
3. Retrieves authoritative series metadata and observations from FRED.
4. Cleans observation dates and values using `fred_api.clean_observations`.
5. Upserts `series`, retaining its FRED metadata and linking metric and source.
6. Upserts `observations` on `(series_id, date)`, converting pandas `NaN` to
   SQL `NULL`.

Each series is loaded in one transaction. Any error rolls back its research
rows, metadata, and observation changes. Repeated ingestion updates existing
rows rather than duplicating them. The migration must be applied before using
this enhanced pipeline. Series IDs must be explicitly selected:

```bash
.venv/bin/python -m src.ingest --series CAPG2211S
# Or, after reviewing the effects on every configured series:
.venv/bin/python -m src.ingest --all
```

### `mapping.py` and `config/series_mapping.json`

`load_series_mapping()` loads the JSON relative to the project root and returns
entries keyed by series ID. `get_series_mapping()` rejects unknown IDs before
external I/O. The loader checks required text fields, stable identifiers, and
conflicting category/metric definitions.

The initial mapping contains `APU000072610` (Price / Electricity Price, the
U.S. city average electricity price per kilowatt-hour) and
`CAPG2211S` (Capacity / Utility Capacity), both from FRED. Adding another FRED
research variable requires a JSON entry rather than new ingestion code. Do not
put FRED titles, units, dates, popularity, or notes in this file. Those continue
to come from FRED. The current adapter supports FRED only; other data sources
would require their own adapter.

### Research schema and 3NF

- `category`: stable unique `category_code`, unique display `category_name`,
  optional description, and integer `category_id` primary key.
- `metric`: stable unique `metric_code`, display name, optional description,
  and integer primary key; `category_id` references its category.
- `source`: unique `source_name`, optional description, and integer primary key.
- `series`: FRED ID primary key and FRED metadata, plus nullable foreign keys
  `metric_id` and `source_id`.
- `observations`: `(series_id, date)` composite primary key with value and
  real-time dates; `series_id` references `series`.

Each table stores attributes of its own key. Category and source attributes
are not copied into series; category attributes are not copied into metric.
The natural codes remain unique even though surrogate IDs are used. This
separates our research taxonomy from FRED's organization and keeps the model
in 3NF. The existing 574 price observations already exceed the 500-row rubric
threshold; the new schema supplies five core tables.

Existing series retain NULL metric/source links after migration. To populate
those links later, explicitly ingest the configured series; doing so also
refreshes its FRED metadata and observations. No automatic backfill occurs.

### `validate_db.py`

Run `.venv/bin/python -m src.validate_db` after manually applying the migration.
The validator uses `database.get_connection()`, enables a read-only transaction,
and executes only SELECT queries. It reports every table, primary key, foreign
key, uniqueness constraint, orphan/duplicate check, and preservation check.
It requires exactly 574 `APU000072610` observations and two SQL NULL values,
and returns exit status 1 on any failure. These are the current preservation
baseline, not a permanent expected count after future FRED refreshes. Before
migration, missing research tables/columns are reported as failures without
changing anything. Relations use the connection's current schema, matching
normal project initialization and ingestion.

## Current Data Flow

```text
series_mapping.json = our research interpretation
        |
        v
mapping.py --> ingest.py <--> fred_api.py <--> FRED
                   |
                   v
               database.py
                   |
                   v
 category --> metric --> series <-- source
                            |
                            v
                       observations
```

`fred_api.py` communicates with FRED; `ingest.py` coordinates transformation
and loading; `database.py` supplies PostgreSQL connections. `sql/schema.sql`
is the complete current schema for new installations; `sql/migrations/`
contains incremental upgrades to existing databases.

## Review and manual upgrade

From the project root, review `git diff` and
`sql/migrations/001_add_research_model.sql`. The migration creates the three
research tables and adds nullable foreign keys to `series` inside a transaction.
It neither replaces nor updates existing series/observations. It is a one-time
migration: repeating it fails safely rather than silently masking schema drift.

Use a configured `psql` connection (for example a libpq service), without
embedding passwords in commands or copying `.env` into shell output:

```bash
git diff
git diff --no-index -- /dev/null sql/migrations/001_add_research_model.sql
# Configure the project database in a local libpq service named cs457 first.
psql 'service=cs457' -X -v ON_ERROR_STOP=1 -f sql/migrations/001_add_research_model.sql
.venv/bin/python -m src.validate_db
.venv/bin/python -m src.ingest --series CAPG2211S
.venv/bin/python -m src.validate_db
psql 'service=cs457' -X -c '\dt' -c 'SELECT * FROM category;' -c 'SELECT * FROM metric;' -c 'SELECT * FROM source;' -c 'SELECT series_id, metric_id, source_id FROM series;' -c 'SELECT series_id, count(*) AS observations, count(*) FILTER (WHERE value IS NULL) AS missing FROM observations GROUP BY series_id;'
```

The service is an example, not supplied by this repository. Alternatively,
apply the migration in your existing PostgreSQL client. The Python validator
and ingestion commands use the existing `.env` and `.venv`.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

The original connection test performs only a SELECT on the configured database.
Mapping and HTTP tests avoid network calls. The PostgreSQL integration tests
start a disposable local cluster under a temporary directory, with a Unix
socket and TCP disabled. They test the clean schema, incremental migration,
574-row/two-NULL preservation fixture, stable-code upserts, repeated ingestion,
transaction rollback, SQL NULL storage, and validator outcomes. They never
use `.env` to select their database. PostgreSQL server binaries (`initdb`,
`pg_ctl`, `postgres`) are required; those tests are skipped if unavailable.

## Related Project Files

The source code in this directory works with several files outside `src`.

```text
projects/
|
+-- .env
|   Project credentials and configuration
|
+-- config/
|   +-- series_mapping.json
|       Our research interpretation of external series
|
+-- docs/
|   Database UML and project documentation
|
+-- sql/
|   +-- schema.sql
|       Complete current PostgreSQL schema
|   +-- migrations/
|       Incremental upgrades for existing databases
|
+-- src/
    +-- README.md
    +-- __init__.py
    +-- config.py
    +-- database.py
    +-- fred_api.py
    +-- ingest.py
    +-- mapping.py
    +-- validate_db.py
    +-- init_db.py
```

## Current Status

The initial ingestion pipeline has been tested successfully using FRED series:

```text
APU000072610
```

The pipeline currently stores:

- One FRED series metadata record
- 574 historical observations
- Two missing observations stored as PostgreSQL `NULL`

The original database relationship was:

```text
series
   1
   |
   | has
   |
   N
observations
```

The research schema extends this relationship with category, metric, and source.
The live upgrade and first capacity ingestion are manual steps after review.
