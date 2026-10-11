"""Ingest FRED series metadata and observations into PostgreSQL."""

import argparse

import pandas as pd

from src.mapping import get_series_mapping, load_series_mapping
from src.database import get_connection
from src.fred_api import (
    clean_observations,
    get_series_metadata,
    get_series_observations,
)


def upsert_category(cur, entry):
    """Resolve a category by its stable code, updating its display name."""
    cur.execute(
        """INSERT INTO category (category_code, category_name)
        VALUES (%s, %s) ON CONFLICT (category_code)
        DO UPDATE SET category_name = EXCLUDED.category_name
        RETURNING category_id""",
        (entry["category_code"], entry["category_name"]),
    )
    return cur.fetchone()[0]


def upsert_metric(cur, entry, category_id):
    """Resolve a metric by stable code and associate its category."""
    cur.execute(
        """INSERT INTO metric (metric_code, metric_name, category_id)
        VALUES (%s, %s, %s) ON CONFLICT (metric_code)
        DO UPDATE SET metric_name = EXCLUDED.metric_name,
                      category_id = EXCLUDED.category_id
        RETURNING metric_id""",
        (entry["metric_code"], entry["metric_name"], category_id),
    )
    return cur.fetchone()[0]


def upsert_source(cur, entry):
    """Resolve a source by its stable source name."""
    cur.execute(
        """INSERT INTO source (source_name) VALUES (%s)
        ON CONFLICT (source_name)
        DO UPDATE SET source_name = EXCLUDED.source_name
        RETURNING source_id""",
        (entry["source"],),
    )
    return cur.fetchone()[0]


def ingest_series(series_id, mappings=None):
    """Retrieve one FRED series and store it in PostgreSQL."""

    entry = get_series_mapping(series_id, mappings)
    if entry["source"] != "FRED":
        raise ValueError("This ingestion adapter only supports source FRED.")

    # --------------------------------------------------
    # Retrieve data from FRED
    # --------------------------------------------------

    metadata = get_series_metadata(series_id)

    if metadata["id"] != series_id:
        raise ValueError("FRED metadata ID does not match the requested series.")

    observations = get_series_observations(series_id)
    observations = clean_observations(observations, series_id)

    # --------------------------------------------------
    # Prepare metadata values
    # --------------------------------------------------

    observation_start = pd.to_datetime(
        metadata["observation_start"]
    ).date()

    observation_end = pd.to_datetime(
        metadata["observation_end"]
    ).date()

    last_updated = pd.to_datetime(
        metadata["last_updated"]
    ).to_pydatetime()

    # --------------------------------------------------
    # Connect to PostgreSQL
    # --------------------------------------------------

    with get_connection() as conn:
        with conn.cursor() as cur:
            category_id = upsert_category(cur, entry)
            metric_id = upsert_metric(cur, entry, category_id)
            source_id = upsert_source(cur, entry)

            # ------------------------------------------
            # Insert/update series metadata
            # ------------------------------------------

            cur.execute(
                """
                INSERT INTO series (
                    series_id,
                    title,
                    frequency,
                    units,
                    seasonal_adjustment,
                    observation_start,
                    observation_end,
                    last_updated,
                    popularity,
                    notes,
                    metric_id,
                    source_id
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (series_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    frequency = EXCLUDED.frequency,
                    units = EXCLUDED.units,
                    seasonal_adjustment = EXCLUDED.seasonal_adjustment,
                    observation_start = EXCLUDED.observation_start,
                    observation_end = EXCLUDED.observation_end,
                    last_updated = EXCLUDED.last_updated,
                    popularity = EXCLUDED.popularity,
                    notes = EXCLUDED.notes,
                    metric_id = EXCLUDED.metric_id,
                    source_id = EXCLUDED.source_id;
                """,
                (
                    metadata["id"],
                    metadata["title"],
                    metadata["frequency"],
                    metadata["units"],
                    metadata["seasonal_adjustment"],
                    observation_start,
                    observation_end,
                    last_updated,
                    metadata["popularity"],
                    metadata.get("notes"),
                    metric_id,
                    source_id,
                ),
            )

            # ------------------------------------------
            # Insert/update observations
            # ------------------------------------------

            observation_rows = []

            for row in observations.itertuples(index=False):

                value = None if pd.isna(row.value) else float(row.value)

                observation_rows.append(
                    (
                        row.series_id,
                        row.date,
                        value,
                        row.realtime_start,
                        row.realtime_end,
                    )
                )

            cur.executemany(
                """
                INSERT INTO observations (
                    series_id,
                    date,
                    value,
                    realtime_start,
                    realtime_end
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (series_id, date)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    realtime_start = EXCLUDED.realtime_start,
                    realtime_end = EXCLUDED.realtime_end;
                """,
                observation_rows,
            )

    print(f"Ingested series: {series_id}")
    print(f"Observations: {len(observations)}")
    print(f"Missing values stored as NULL: {observations['value'].isna().sum()}")


def main():
    """Ingest selected configured IDs, or every mapping with --all."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--series", nargs="+", metavar="ID")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    mappings = load_series_mapping()
    series_ids = list(mappings) if args.all else args.series
    for series_id in series_ids:
        get_series_mapping(series_id, mappings)
    for series_id in series_ids:
        ingest_series(series_id, mappings)


if __name__ == "__main__":
    main()
