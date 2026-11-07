
import os
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql
from dotenv import load_dotenv

# Use the project's existing environment configuration.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

METRICS = {
    "Electricity Price": "electricity_price",
    "Utility Capacity": "utility_capacity",
    "Capacity Utilization": "capacity_utilization",
    "Total Power Construction": "total_power_construction",
    "Private Power Construction": "private_power_construction",
    "Public Power Construction": "public_power_construction",
    "Transmission / Distribution": "transmission_distribution_activity",
}

METRIC_UNITS = {
    "Electricity Price": "USD per kWh",
    "Utility Capacity": "Index (2017 = 100)",
    "Capacity Utilization": "Percent (%)",
    "Total Power Construction": "Millions of USD",
    "Private Power Construction": "Millions of USD",
    "Public Power Construction": "Millions of USD",
    "Transmission / Distribution": "Index (2017 = 100)",
}

def get_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME", "fred_db"),
        user=os.getenv("DB_USER", "fred_user"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


def get_observations(metric, start_date, end_date):
    if metric not in METRICS.values():
        raise ValueError("Unsupported metric")

    query = sql.SQL("""
        SELECT date, {metric} AS value
        FROM electricity_research_monthly
        WHERE date BETWEEN %s AND %s
        ORDER BY date
    """).format(metric=sql.Identifier(metric))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (start_date, end_date))
            rows = cur.fetchall()

    df = pd.DataFrame(rows, columns=["date", "value"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df
