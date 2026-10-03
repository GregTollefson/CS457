"""Integration test for the configured PostgreSQL connection.

Run from the project root with:
    .venv/bin/python -m unittest discover -s tests -p test_database.py
"""

import unittest

from src import config
from src.database import get_connection


class DatabaseConnectionTest(unittest.TestCase):
    def test_connection(self):
        # Suppress driver exception details, which may contain configuration.
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_database(), current_user;")
                    result = cursor.fetchone()
        except Exception:
            raise AssertionError(
                "Database connection or query failed; details withheld."
            ) from None

        self.assertTrue(connection.closed, "Connection was not closed.")
        self.assertIsNotNone(result, "The query returned no result.")
        self.assertTrue(
            result[0] == config.DB_NAME,
            "The current database does not match DB_NAME.",
        )
        self.assertTrue(
            result[1] == config.DB_USER,
            "The current user does not match DB_USER.",
        )


if __name__ == "__main__":
    unittest.main()
