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

The current schema creates the following tables:

```text
series
observations
```

---

### `ingest.py`

Implements the FRED-to-PostgreSQL ingestion pipeline.

For a selected FRED series, the module:

1. Retrieves series metadata from FRED
2. Retrieves historical observations
3. Cleans and converts the observation data
4. Inserts or updates the metadata in the `series` table
5. Inserts or updates observations in the `observations` table
6. Converts missing pandas values to SQL `NULL`

The current test series is:

```text
APU000072610
```

which represents the average price of electricity per kilowatt-hour in the U.S. city average.

Run from the project root with:

```bash
.venv/bin/python -m src.ingest
```

The ingestion uses PostgreSQL `ON CONFLICT` clauses so the process is idempotent.

Running the ingestion multiple times updates existing rows instead of creating duplicate observations.

## Current Data Flow

```text
FRED API
    |
    v
fred_api.py
    |
    | retrieve and clean
    v
ingest.py
    |
    | database connection
    v
database.py
    |
    v
PostgreSQL
    |
    +---- series
    |
    +---- observations
```

## Related Project Files

The source code in this directory works with several files outside `src`.

```text
projects/
|
+-- .env
|   Project credentials and configuration
|
+-- docs/
|   Database UML and project documentation
|
+-- sql/
|   +-- schema.sql
|       PostgreSQL schema definition
|
+-- src/
    +-- README.md
    +-- __init__.py
    +-- config.py
    +-- database.py
    +-- fred_api.py
    +-- ingest.py
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

The current database relationship is:

```text
series
   1
   |
   | has
   |
   N
observations
```

The schema and ingestion pipeline will be expanded incrementally as additional energy datasets are added.