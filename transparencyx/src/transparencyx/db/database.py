"""
Database connection and initialization utilities.
"""
import sqlite3
from pathlib import Path

from transparencyx.db.schema import get_schema_sql


def get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Returns a configured SQLite connection.
    Enables foreign keys and sets the row_factory.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Path) -> None:
    """
    Initializes the database by executing the schema SQL.
    Creates the database file if it does not exist.
    """
    # Ensure the parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        schema_sql = get_schema_sql()
        conn.executescript(schema_sql)
