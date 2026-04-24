import pytest
import sqlite3
import uuid
from datetime import datetime

from ums_lite.db.database import DatabaseSchema
from ums_lite.services.tournament_service import TournamentService
from ums_lite.core.exceptions import InvalidStateError
from ums_lite.db.models import TournamentState

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_missing_channels_block_progression(db_conn):
    t_service = TournamentService(db_conn)
    t = t_service.create_tournament("g1", "T1")

    # Opening registration without registration_channel_id should fail
    with pytest.raises(InvalidStateError, match="You must configure a Registration Channel"):
        t_service.open_registration(t.id)

    # Configure registration channel
    t_service.update_guild_channels("g1", "reg1", "", "")
    t_service.open_registration(t.id) # Should succeed now

    t = t_service.tournament_repo.get(t.id)
    assert t.state == TournamentState.REGISTRATION_OPEN

    # Try to close/generate bracket without match_channel_id
    t_service.join_tournament(t.id, "P1")
    t_service.join_tournament(t.id, "P2")

    t_service.close_registration(t.id)

    with pytest.raises(InvalidStateError, match="You must configure a Match Channel"):
        t_service.generate_bracket(t.id)

def test_metadata_persistence(db_conn):
    t_service = TournamentService(db_conn)
    t = t_service.create_tournament("g1", "T1")

    t_service.update_tournament_metadata(t.id, "Cool Tourney", "Friday 8PM", "USE")

    t = t_service.tournament_repo.get(t.id)
    assert t.name == "Cool Tourney"
    assert t.scheduled_start_time == "Friday 8PM"
    assert t.region == "USE"

def test_prevent_editing_after_start(db_conn):
    t_service = TournamentService(db_conn)
    t = t_service.create_tournament("g1", "T1")

    t_service.update_guild_channels("g1", "reg1", "match1", "")
    t_service.open_registration(t.id)
    t_service.join_tournament(t.id, "P1")
    t_service.join_tournament(t.id, "P2")
    t_service.close_registration(t.id)
    t_service.generate_bracket(t.id)

    # Tournament is IN_PROGRESS
    with pytest.raises(InvalidStateError, match="Cannot edit server routing channels"):
        t_service.update_guild_channels("g1", "reg2", "match2", "")

    with pytest.raises(InvalidStateError, match="Cannot edit metadata"):
        t_service.update_tournament_metadata(t.id, "New Name", None, None)
