"""Initialize the PostgreSQL database schema."""

from pathlib import Path

from src.database import get_connection


SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def create_tables():
    """Create the project database tables from schema.sql."""

    schema_sql = SCHEMA_FILE.read_text()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

        conn.commit()


if __name__ == "__main__":
    create_tables()
    print("Database schema created successfully.")