"""PostgreSQL connection creation using Psycopg 3."""

import psycopg

from src import config


def get_connection() -> psycopg.Connection:
    """Return a connection; the caller is responsible for closing it."""
    settings = {
        "dbname": config.DB_NAME,
        "user": config.DB_USER,
        "password": config.DB_PASSWORD,
        "host": config.DB_HOST,
        "port": config.DB_PORT,
    }
    if any(value is None or value == "" for value in settings.values()):
        raise ValueError("All five database configuration variables are required.")
    return psycopg.connect(**settings)
