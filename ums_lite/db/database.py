import sqlite3
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseSchema:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS guild_configs (
        guild_id TEXT PRIMARY KEY,
        admin_role_id TEXT,
        participant_role_id TEXT,
        elo_enabled BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS player_profiles (
        discord_id TEXT PRIMARY KEY,
        global_ums_id TEXT, -- UUID
        username TEXT,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        matches_played INTEGER DEFAULT 0,
        tournaments_played INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS tournaments (
        id TEXT PRIMARY KEY, -- UUID
        guild_id TEXT NOT NULL,
        name TEXT NOT NULL,
        state TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        panel_channel_id TEXT,
        panel_message_id TEXT,
        scheduled_start_time TEXT,
        region TEXT,
        format TEXT DEFAULT '1v1',
        registration_channel_id TEXT,
        match_channel_id TEXT,
        results_channel_id TEXT
    );

    CREATE TABLE IF NOT EXISTS tournament_entries (
        id TEXT PRIMARY KEY, -- UUID
        tournament_id TEXT NOT NULL,
        player_id TEXT NOT NULL,
        joined_at TIMESTAMP NOT NULL,
        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
        FOREIGN KEY (player_id) REFERENCES player_profiles (discord_id),
        UNIQUE(tournament_id, player_id)
    );

    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY, -- UUID
        tournament_id TEXT NOT NULL,
        round_number INTEGER NOT NULL,
        match_number INTEGER NOT NULL,
        player1_id TEXT,
        player2_id TEXT,
        winner_id TEXT,
        status TEXT NOT NULL,
        next_match_id TEXT,
        next_match_slot INTEGER,
        message_channel_id TEXT,
        message_id TEXT,
        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
        FOREIGN KEY (player1_id) REFERENCES player_profiles (discord_id),
        FOREIGN KEY (player2_id) REFERENCES player_profiles (discord_id),
        FOREIGN KEY (winner_id) REFERENCES player_profiles (discord_id),
        FOREIGN KEY (next_match_id) REFERENCES matches (id)
    );

    CREATE TABLE IF NOT EXISTS match_reports (
        id TEXT PRIMARY KEY, -- UUID
        match_id TEXT NOT NULL,
        reporter_id TEXT NOT NULL,
        claimed_winner_id TEXT NOT NULL,
        reported_at TIMESTAMP NOT NULL,
        FOREIGN KEY (match_id) REFERENCES matches (id),
        FOREIGN KEY (reporter_id) REFERENCES player_profiles (discord_id),
        FOREIGN KEY (claimed_winner_id) REFERENCES player_profiles (discord_id)
    );

    CREATE TABLE IF NOT EXISTS admin_action_logs (
        id TEXT PRIMARY KEY, -- UUID
        guild_id TEXT NOT NULL,
        admin_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        target_entity_id TEXT,
        details TEXT,
        timestamp TIMESTAMP NOT NULL
    );
    """

class DatabaseSession:
    """A simple session manager for SQLite connections."""

    def __init__(self, db_path: str = "ums_lite.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish the database connection and enable foreign keys."""
        if not self._conn:
            # We omit PARSE_DECLTYPES because it uses deprecated converters in Python 3.12+ that conflict with isoformat.
            # We handle datetime conversions manually in the repository layer using `_parse_datetime` and `_format_datetime`.
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row

            # Enable foreign key constraints
            self._conn.execute("PRAGMA foreign_keys = ON;")
            logger.info(f"Connected to database at {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        if not self._conn:
            self.connect()
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")

def init_db(db_path: str = "ums_lite.db"):
    """Initialize the database schema."""
    session = DatabaseSession(db_path)
    conn = session.get_connection()
    try:
        conn.executescript(DatabaseSchema.SCHEMA)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database schema: {e}")
        conn.rollback()
        raise
    finally:
        session.close()

# Dependency provider for easier testing and connection pooling later
db_session = DatabaseSession()
