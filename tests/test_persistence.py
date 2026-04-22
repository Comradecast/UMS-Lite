import pytest
import sqlite3
import uuid
from datetime import datetime, timezone

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import PlayerProfile, Tournament, TournamentState, TournamentEntry, Match, MatchStatus
from ums_lite.db.repositories import PlayerRepo, TournamentRepo, EntryRepo, MatchRepo
from ums_lite.core.exceptions import DuplicateEntityError

@pytest.fixture
def db_conn():
    """Provides an in-memory database connection with schema loaded and foreign keys enforced."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_create_and_get_player(db_conn):
    repo = PlayerRepo(db_conn)
    player = PlayerProfile(discord_id="12345", username="TestUser")

    repo.save(player)

    fetched = repo.get("12345")
    assert fetched is not None
    assert fetched.discord_id == "12345"
    assert fetched.username == "TestUser"
    assert fetched.global_ums_id is None

def test_create_tournament(db_conn):
    repo = TournamentRepo(db_conn)
    t_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    tournament = Tournament(
        id=t_id,
        guild_id="999",
        name="Weekly Cup",
        state=TournamentState.DRAFT,
        created_at=now
    )

    repo.save(tournament)

    fetched = repo.get(t_id)
    assert fetched is not None
    assert fetched.id == t_id
    assert fetched.name == "Weekly Cup"
    assert fetched.state == TournamentState.DRAFT
    # sqlite datetimes drop tzinfo by default parsing, so we just compare isoformat
    assert fetched.created_at.isoformat() == now.isoformat()

def test_join_tournament_and_duplicate_prevention(db_conn):
    t_repo = TournamentRepo(db_conn)
    p_repo = PlayerRepo(db_conn)
    e_repo = EntryRepo(db_conn)

    t_id = uuid.uuid4()
    discord_id = "user_1"

    t_repo.save(Tournament(id=t_id, guild_id="g1", name="T1", state=TournamentState.REGISTRATION_OPEN, created_at=datetime.now()))
    p_repo.save(PlayerProfile(discord_id=discord_id, username="U1"))

    entry = TournamentEntry(
        id=uuid.uuid4(),
        tournament_id=t_id,
        player_id=discord_id,
        joined_at=datetime.now()
    )

    # Should create fine
    e_repo.create(entry)

    # Attempt duplicate join
    duplicate_entry = TournamentEntry(
        id=uuid.uuid4(),
        tournament_id=t_id,
        player_id=discord_id,
        joined_at=datetime.now()
    )

    with pytest.raises(DuplicateEntityError):
        e_repo.create(duplicate_entry)

def test_foreign_key_enforcement(db_conn):
    e_repo = EntryRepo(db_conn)

    # Trying to create an entry for a tournament/player that doesn't exist
    entry = TournamentEntry(
        id=uuid.uuid4(),
        tournament_id=uuid.uuid4(),
        player_id="nonexistent_user",
        joined_at=datetime.now()
    )

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        e_repo.create(entry)

def test_create_match_with_link(db_conn):
    t_repo = TournamentRepo(db_conn)
    m_repo = MatchRepo(db_conn)

    t_id = uuid.uuid4()
    t_repo.save(Tournament(id=t_id, guild_id="g1", name="T1", state=TournamentState.IN_PROGRESS, created_at=datetime.now()))

    m_id_1 = uuid.uuid4()
    m_id_2 = uuid.uuid4()

    # Create final match
    match_2 = Match(
        id=m_id_2,
        tournament_id=t_id,
        round_number=2,
        match_number=1,
        status=MatchStatus.PENDING
    )
    m_repo.save(match_2)

    # Create semi-final match pointing to final match slot 1
    match_1 = Match(
        id=m_id_1,
        tournament_id=t_id,
        round_number=1,
        match_number=1,
        status=MatchStatus.PENDING,
        next_match_id=m_id_2,
        next_match_slot=1
    )
    m_repo.save(match_1)

    fetched = m_repo.get(m_id_1)
    assert fetched is not None
    assert fetched.next_match_id == m_id_2
    assert fetched.next_match_slot == 1
