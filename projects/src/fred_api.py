"""Functions for retrieving data from the FRED API."""

import pandas as pd
import requests

from src import config


FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def get_series_by_tag(tag_name, limit=25):
    """Return FRED series metadata matching a tag."""

    url = f"{FRED_BASE_URL}/tags/series"

    params = {
        "api_key": config.FRED_API_KEY,
        "tag_names": tag_name,
        "file_type": "json",
        "order_by": "popularity",
        "sort_order": "desc",
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    return pd.DataFrame(data["seriess"])

def get_series_observations(series_id):
    """Return observations for a FRED series."""

    url = f"{FRED_BASE_URL}/series/observations"

    params = {
        "api_key": config.FRED_API_KEY,
        "series_id": series_id,
        "file_type": "json",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    return pd.DataFrame(data["observations"])

def get_series_metadata(series_id):
    """Return metadata for one FRED series."""

    url = f"{FRED_BASE_URL}/series"

    params = {
        "api_key": config.FRED_API_KEY,
        "series_id": series_id,
        "file_type": "json",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    return data["seriess"][0]


def clean_observations(df, series_id):
    """Prepare FRED observations for database storage."""

    df = df.copy()

    df["series_id"] = series_id

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["realtime_start"] = pd.to_datetime(df["realtime_start"]).dt.date
    df["realtime_end"] = pd.to_datetime(df["realtime_end"]).dt.date

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df


if __name__ == "__main__":
    series_id = "APU000072610"

    df = get_series_observations(series_id)
    df = clean_observations(df, series_id)

    print(df.head(20).to_string(index=False))
    print()
    print(df.dtypes)
    print()
    print(f"Rows: {len(df)}")
    print(f"Missing values: {df['value'].isna().sum()}")
    print()
    print("Rows with missing values:")
    print(df[df["value"].isna()].to_string(index=False))