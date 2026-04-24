import pytest
import sqlite3
from ums_lite.db.database import DatabaseSchema
from ums_lite.db.repositories import GuildConfigRepo, MatchRepo, EntryRepo
from ums_lite.db.models import GuildConfig, Match, MatchStatus, Tournament, TournamentState, TournamentEntry
from ums_lite.services.tournament_service import TournamentService
import uuid
from datetime import datetime

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_guild_config_elo_policy(db_conn):
    repo = GuildConfigRepo(db_conn)
    config = GuildConfig(guild_id="123", elo_enabled=True)
    repo.save(config)

    fetched = repo.get("123")
    assert fetched.elo_enabled is True

    config.elo_enabled = False
    repo.save(config)
    fetched = repo.get("123")
    assert fetched.elo_enabled is False

def test_leave_tournament(db_conn):
    t_service = TournamentService(db_conn)
    guild_id = "g1"
    t = t_service.create_tournament(guild_id, "T1")
    t_service.update_guild_channels(guild_id, "reg1", "match1", "")
    t_service.open_registration(t.id)

    t_service.join_tournament(t.id, "P1")
    entries = t_service.entry_repo.get_by_tournament(t.id)
    assert len(entries) == 1

    t_service.leave_tournament(t.id, "P1")
    entries = t_service.entry_repo.get_by_tournament(t.id)
    assert len(entries) == 0

def test_get_active_match_by_player(db_conn):
    m_repo = MatchRepo(db_conn)
    t_id = uuid.uuid4()

    # Must create prerequisite records for FK
    db_conn.execute("INSERT INTO tournaments (id, guild_id, name, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(t_id), "g1", "T", TournamentState.IN_PROGRESS.value, datetime.now().isoformat()))
    db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES (?)", ("P1",))
    db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES (?)", ("P2",))

    m_id = uuid.uuid4()
    m = Match(id=m_id, tournament_id=t_id, round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)
    m_repo.save(m)

    # Check P1
    active = m_repo.get_active_by_player(t_id, "P1")
    assert active is not None
    assert active.id == m_id

    # Check P2
    active = m_repo.get_active_by_player(t_id, "P2")
    assert active is not None
    assert active.id == m_id

    # Check non-participant
    active = m_repo.get_active_by_player(t_id, "P3")
    assert active is None
