import pytest
import sqlite3
import uuid

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.repositories import PlayerRepo
from ums_lite.db.models import MatchStatus
from ums_lite.services.tournament_service import TournamentService
from ums_lite.services.match_service import MatchService

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_stats_update_on_resolution(db_conn):
    t_service = TournamentService(db_conn)
    m_service = MatchService(db_conn)
    p_repo = PlayerRepo(db_conn)

    guild_id = "g1"
    t = t_service.create_tournament(guild_id, "Stats Tourney")
    t_service.update_guild_channels(guild_id, "reg1", "match1", "")
    t_service.open_registration(t.id)

    # 3 players to ensure we have a standard match and a bye
    t_service.join_tournament(t.id, "P1")
    t_service.join_tournament(t.id, "P2")
    t_service.join_tournament(t.id, "P3")
    t_service.close_registration(t.id)

    matches = t_service.generate_bracket(t.id)

    p1 = p_repo.get("P1")
    p2 = p_repo.get("P2")
    p3 = p_repo.get("P3")

    # All should have tournaments_played = 1
    assert p1.tournaments_played == 1
    assert p2.tournaments_played == 1
    assert p3.tournaments_played == 1

    # Round 1 has P1 vs Bye (RESOLVED automatically) and P2 vs P3 (ACTIVE)
    active_match = next(m for m in matches if m.status == MatchStatus.ACTIVE)
    assert active_match.player1_id == "P2"
    assert active_match.player2_id == "P3"

    # Report P2 wins
    m_service.report_match(active_match.id, "P2", "P2")
    m_service.report_match(active_match.id, "P3", "P2") # Confirms P2

    # P2 wins, P3 loses
    p1 = p_repo.get("P1")
    p2 = p_repo.get("P2")
    p3 = p_repo.get("P3")

    # P1 had a bye, so matches_played = 0, wins = 0
    assert p1.matches_played == 0
    assert p1.wins == 0

    # P2 won
    assert p2.matches_played == 1
    assert p2.wins == 1
    assert p2.losses == 0

    # P3 lost
    assert p3.matches_played == 1
    assert p3.wins == 0
    assert p3.losses == 1

    # Round 2 Final: P1 vs P2
    final_match = m_service.match_repo.get_active_by_player(t.id, "P1")
    assert final_match is not None
    assert final_match.player2_id == "P2"

    # Report P1 wins
    m_service.report_match(final_match.id, "P1", "P1")
    m_service.report_match(final_match.id, "P2", "P1")

    p1 = p_repo.get("P1")
    p2 = p_repo.get("P2")

    assert p1.matches_played == 1
    assert p1.wins == 1

    assert p2.matches_played == 2
    assert p2.wins == 1
    assert p2.losses == 1

def test_admin_force_win_audit_and_stats(db_conn):
    t_service = TournamentService(db_conn)
    m_service = MatchService(db_conn)
    p_repo = PlayerRepo(db_conn)

    t = t_service.create_tournament("g1", "Dispute Tourney")
    t_service.update_guild_channels("g1", "reg1", "match1", "")
    t_service.open_registration(t.id)
    t_service.join_tournament(t.id, "A1")
    t_service.join_tournament(t.id, "A2")
    t_service.close_registration(t.id)
    matches = t_service.generate_bracket(t.id)

    m = matches[0]

    # Dispute happens
    m_service.report_match(m.id, "A1", "A1")
    m_service.report_match(m.id, "A2", "A2")

    m_reloaded = m_service.match_repo.get(m.id)
    assert m_reloaded.status == MatchStatus.DISPUTED

    # Admin forces A1 to win
    m_service.admin_force_win(m.id, "g1", "ADMIN1", "A1")

    a1 = p_repo.get("A1")
    a2 = p_repo.get("A2")

    assert a1.wins == 1
    assert a1.matches_played == 1
    assert a2.losses == 1

    # Check Audit Log
    rows = db_conn.execute("SELECT * FROM admin_action_logs").fetchall()
    assert len(rows) == 1
    assert rows[0]['admin_id'] == "ADMIN1"
    assert rows[0]['action_type'] == "FORCE_WIN"
    assert "A1" in rows[0]['details']
