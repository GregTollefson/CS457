"""Read-only checks of the current research schema and preserved price data."""

from src.database import get_connection


PRIMARY_KEYS = {
    "category": ("category_id",),
    "metric": ("metric_id",),
    "source": ("source_id",),
    "series": ("series_id",),
    "observations": ("series_id", "date"),
}
FOREIGN_KEYS = (
    ("metric", "category_id", "category", "category_id"),
    ("series", "metric_id", "metric", "metric_id"),
    ("series", "source_id", "source", "source_id"),
    ("observations", "series_id", "series", "series_id"),
)
UNIQUES = (
    ("category", "category_code"), ("category", "category_name"),
    ("metric", "metric_code"), ("source", "source_name"),
)


def validate_connection(conn, report=print):
    """Execute only SELECT statements; return whether all checks pass.

    Relations are resolved using the connection's current schema, matching the
    unqualified table names used by ingestion and schema initialization.
    """
    outcomes = []

    def check(ok, message):
        outcomes.append(bool(ok))
        report(f"{'PASS' if ok else 'FAIL'}: {message}")

    with conn.cursor() as cur:
        cur.execute("""SELECT tablename FROM pg_catalog.pg_tables
                       WHERE schemaname = current_schema()""")
        tables = {row[0] for row in cur.fetchall()}
        for table in PRIMARY_KEYS:
            check(table in tables, f"{table} table exists")

        cur.execute("""
            SELECT t.relname, c.contype,
                   ARRAY(SELECT a.attname::text
                         FROM unnest(c.conkey) WITH ORDINALITY k(num, ord)
                         JOIN pg_attribute a ON a.attrelid = c.conrelid
                                             AND a.attnum = k.num
                         ORDER BY k.ord),
                   r.relname,
                   ARRAY(SELECT a.attname::text
                         FROM unnest(c.confkey) WITH ORDINALITY k(num, ord)
                         JOIN pg_attribute a ON a.attrelid = c.confrelid
                                             AND a.attnum = k.num
                         ORDER BY k.ord),
                   rn.nspname, c.convalidated
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            LEFT JOIN pg_class r ON r.oid = c.confrelid
            LEFT JOIN pg_namespace rn ON rn.oid = r.relnamespace
            WHERE n.nspname = current_schema()
        """)
        constraints = cur.fetchall()
        cur.execute("SELECT current_schema()")
        schema = cur.fetchone()[0]
        for table, columns in PRIMARY_KEYS.items():
            check(any(t == table and kind == "p" and tuple(cols) == columns
                      for t, kind, cols, _, _, _, _ in constraints),
                  f"{table} primary key is ({', '.join(columns)})")
        for table, column, target, target_column in FOREIGN_KEYS:
            check(any(t == table and kind == "f" and cols == [column]
                      and ref == target and refcols == [target_column]
                      and namespace == schema and valid
                      for t, kind, cols, ref, refcols, namespace, valid in constraints),
                  f"{table}.{column} FK exists to {target}.{target_column}")
        for table, column in UNIQUES:
            check(any(t == table and kind in ("u", "p") and cols == [column]
                      for t, kind, cols, _, _, _, _ in constraints),
                  f"{table}.{column} has a uniqueness constraint")

        # Avoid querying absent columns on an unmigrated database.
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema = current_schema()""")
        columns = set(cur.fetchall())

        def count_check(query, required, expected, label):
            if not all(pair in columns for pair in required):
                check(False, f"{label}; required table or column missing")
                return
            cur.execute(query)
            count = cur.fetchone()[0]
            check(count == expected, f"{label} (found {count})")

        count_check("SELECT count(*) FROM series WHERE series_id = 'APU000072610'",
                    [("series", "series_id")], 1, "APU000072610 series exists")
        count_check("SELECT count(*) FROM observations WHERE series_id = 'APU000072610'",
                    [("observations", "series_id")], 574,
                    "APU000072610 has 574 observations")
        count_check("""SELECT count(*) FROM observations
                       WHERE series_id = 'APU000072610' AND value IS NULL""",
                    [("observations", "series_id"), ("observations", "value")], 2,
                    "APU000072610 has two SQL NULL observations")
        for table, column, target, target_column in FOREIGN_KEYS:
            count_check(
                f"SELECT count(*) FROM {table} child LEFT JOIN {target} parent "
                f"ON child.{column} = parent.{target_column} "
                f"WHERE child.{column} IS NOT NULL AND parent.{target_column} IS NULL",
                [(table, column), (target, target_column)], 0,
                f"no orphan references from {table}.{column}",
            )
        for table, column in UNIQUES:
            count_check(
                f"SELECT count(*) FROM (SELECT {column} FROM {table} "
                f"GROUP BY {column} HAVING count(*) > 1) duplicates",
                [(table, column)], 0, f"no duplicate {table}.{column} values",
            )
    return all(outcomes)


def main():
    try:
        with get_connection() as conn:
            # Psycopg sets transaction characteristics before the first SELECT.
            # PostgreSQL enforces read-only access as an additional safeguard.
            conn.read_only = True
            return 0 if validate_connection(conn) else 1
    except Exception:
        print("FAIL: validation could not finish; check connectivity, permissions, and schema. "
              "Driver details withheld to protect configuration.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
