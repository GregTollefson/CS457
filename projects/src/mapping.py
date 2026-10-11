"""Load and validate our research interpretation of external series."""

import json
from pathlib import Path


MAPPING_FILE = Path(__file__).resolve().parent.parent / "config/series_mapping.json"
REQUIRED_FIELDS = (
    "source", "category_code", "category_name", "metric_code", "metric_name"
)


def load_series_mapping(path=None):
    """Return mappings keyed by series ID; reject ambiguous research identifiers."""
    path = Path(path) if path is not None else MAPPING_FILE
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise FileNotFoundError(f"Series mapping file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed series mapping JSON at line {exc.lineno}, column {exc.colno}"
        ) from None
    if not isinstance(data, dict) or not isinstance(data.get("series"), dict):
        raise ValueError("Mapping must contain a 'series' object.")
    categories, names, metrics = {}, {}, {}
    for series_id, entry in data["series"].items():
        if not isinstance(series_id, str) or not series_id.strip():
            raise ValueError("Series IDs must be non-empty strings.")
        if not isinstance(entry, dict):
            raise ValueError(f"Mapping for {series_id} must be an object.")
        for field in REQUIRED_FIELDS:
            if field not in entry:
                raise ValueError(f"Mapping for {series_id} is missing '{field}'.")
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise ValueError(f"Mapping for {series_id}: '{field}' must be non-empty text.")
            if entry[field] != entry[field].strip():
                raise ValueError(f"Mapping for {series_id}: '{field}' has surrounding whitespace.")
        category, name = entry["category_code"], entry["category_name"]
        metric = entry["metric_code"]
        if category in categories and categories[category] != name:
            raise ValueError(f"Conflicting names for category code '{category}'.")
        if name in names and names[name] != category:
            raise ValueError(f"Category name '{name}' is assigned to multiple codes.")
        identity = (entry["metric_name"], category)
        if metric in metrics and metrics[metric] != identity:
            raise ValueError(f"Conflicting mappings for metric code '{metric}'.")
        categories[category], names[name], metrics[metric] = name, category, identity
    return data["series"]


def get_series_mapping(series_id, mappings=None):
    """Return one configured series or raise a useful error before external I/O."""
    mappings = load_series_mapping() if mappings is None else mappings
    if series_id not in mappings:
        raise ValueError(f"Unknown configured series ID: {series_id}")
    return mappings[series_id]
