import pytest
import sqlite3
import uuid

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import TournamentState, MatchStatus
from ums_lite.services.tournament_service import TournamentService
from ums_lite.services.match_service import MatchService
from ums_lite.db.repositories import TournamentRepo, MatchRepo

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_full_tournament_lifecycle(db_conn):
    t_service = TournamentService(db_conn)
    m_service = MatchService(db_conn)

    guild_id = "guild123"

    # 1. Create Tournament
    t = t_service.create_tournament(guild_id, "Test Tourney")
    assert t.state == TournamentState.DRAFT

    # Fetch active to verify `get_active_by_guild` works via service
    active_t = t_service.get_active_tournament(guild_id)
    assert active_t is not None
    assert active_t.id == t.id

    # 2. Open Registration
    t_service.update_tournament_channels(t.id, "reg1", "match1", "")
    t_service.open_registration(t.id)

    active_t = t_service.get_active_tournament(guild_id)
    assert active_t.state == TournamentState.REGISTRATION_OPEN

    # 3. Join Tournament (3 Players to test bye logic too)
    t_service.join_tournament(t.id, "P1")
    t_service.join_tournament(t.id, "P2")
    t_service.join_tournament(t.id, "P3")

    # 4. Close Registration
    t_service.close_registration(t.id)

    # 5. Generate Bracket
    matches = t_service.generate_bracket(t.id)
    assert len(matches) == 3 # 2 semis (1 is a bye), 1 final

    # Reload tournament to verify state
    t_repo = TournamentRepo(db_conn)
    m_repo = MatchRepo(db_conn)

    active_t = t_repo.get(t.id)
    assert active_t.state == TournamentState.IN_PROGRESS

    # Find active match (P2 vs P3)
    active_match = next(m for m in matches if m.status == MatchStatus.ACTIVE)
    assert active_match.player1_id == "P2"
    assert active_match.player2_id == "P3"

    # 6. Report Match
    m_service.report_match(active_match.id, "P2", claimed_winner_id="P2") # P2 claims win

    m_reloaded = m_repo.get(active_match.id)
    assert m_reloaded.status == MatchStatus.AWAITING_CONFIRMATION

    m_service.report_match(active_match.id, "P3", claimed_winner_id="P2") # P3 confirms P2 win

    # 7. Match Resolves, advances P2, Final match becomes Active
    m_reloaded = m_repo.get(active_match.id)
    assert m_reloaded.status == MatchStatus.RESOLVED
    assert m_reloaded.winner_id == "P2"

    # Find final match
    final_match = next(m for m in m_repo.get_by_tournament(t.id) if m.round_number == 2)
    assert final_match.status == MatchStatus.ACTIVE
    assert final_match.player1_id == "P1" # Came from bye
    assert final_match.player2_id == "P2" # Advanced from semi

    # 8. Report Final Match
    m_service.report_match(final_match.id, "P1", "P1")
    m_service.report_match(final_match.id, "P2", "P1")

    # 9. Tournament Completes automatically
    f_reloaded = m_repo.get(final_match.id)
    assert f_reloaded.status == MatchStatus.RESOLVED
    assert f_reloaded.winner_id == "P1"

    t_reloaded = t_repo.get(t.id)
    assert t_reloaded.state == TournamentState.COMPLETED
