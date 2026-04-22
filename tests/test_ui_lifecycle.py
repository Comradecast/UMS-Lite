import pytest
import sqlite3
import uuid
from datetime import datetime

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.repositories import TournamentRepo, MatchRepo
from ums_lite.db.models import Tournament, TournamentState, Match, MatchStatus

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_tournament_message_persistence(db_conn):
    t_repo = TournamentRepo(db_conn)
    t_id = uuid.uuid4()

    # Save a tournament with message metadata
    t = Tournament(
        id=t_id,
        guild_id="g1",
        name="T1",
        state=TournamentState.REGISTRATION_OPEN,
        created_at=datetime.now(),
        panel_channel_id="c1",
        panel_message_id="m1"
    )
    t_repo.save(t)

    # Reload and verify
    fetched = t_repo.get(t_id)
    assert fetched.panel_channel_id == "c1"
    assert fetched.panel_message_id == "m1"

    # Update message ID
    fetched.panel_message_id = "m2"
    t_repo.save(fetched)

    fetched2 = t_repo.get(t_id)
    assert fetched2.panel_message_id == "m2"

def test_match_message_persistence(db_conn):
    t_repo = TournamentRepo(db_conn)
    m_repo = MatchRepo(db_conn)
    t_id = uuid.uuid4()

    # Create required tournament constraint
    t = Tournament(
        id=t_id,
        guild_id="g1",
        name="T1",
        state=TournamentState.IN_PROGRESS,
        created_at=datetime.now()
    )
    t_repo.save(t)

    m_id = uuid.uuid4()
    m = Match(
        id=m_id,
        tournament_id=t_id,
        round_number=1,
        match_number=1,
        status=MatchStatus.ACTIVE,
        message_channel_id="mc1",
        message_id="mm1"
    )
    m_repo.save(m)

    fetched = m_repo.get(m_id)
    assert fetched.message_channel_id == "mc1"
    assert fetched.message_id == "mm1"
