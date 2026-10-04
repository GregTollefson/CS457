"""Ingest FRED series metadata and observations into PostgreSQL."""

import pandas as pd

from src.database import get_connection
from src.fred_api import (
    clean_observations,
    get_series_metadata,
    get_series_observations,
)


def ingest_series(series_id):
    """Retrieve one FRED series and store it in PostgreSQL."""

    # --------------------------------------------------
    # Retrieve data from FRED
    # --------------------------------------------------

    metadata = get_series_metadata(series_id)

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
                    notes
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
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
                    notes = EXCLUDED.notes;
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

        conn.commit()

    print(f"Ingested series: {series_id}")
    print(f"Observations: {len(observations)}")
    print(f"Missing values stored as NULL: {observations['value'].isna().sum()}")


if __name__ == "__main__":
    ingest_series("APU000072610")