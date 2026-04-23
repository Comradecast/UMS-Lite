import pytest
import sqlite3
import uuid
from datetime import datetime

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import PlayerProfile, Tournament, TournamentState, GuildConfig
from ums_lite.ui.router import _build_public_panel, _build_admin_panel_embed
from ums_lite.services.tournament_service import TournamentService

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_admin_panel_history_rendering(db_conn):
    t_service = TournamentService(db_conn)
    config = GuildConfig(guild_id="g1", elo_enabled=False)
    profile = PlayerProfile(discord_id="A1", wins=10, losses=0, matches_played=10, tournaments_played=3)

    recent_tourneys = [
        Tournament(id=uuid.uuid4(), guild_id="g1", name="Old T1", state=TournamentState.COMPLETED, created_at=datetime.now()),
        Tournament(id=uuid.uuid4(), guild_id="g1", name="Old T2", state=TournamentState.CANCELLED, created_at=datetime.now())
    ]

    embed = _build_admin_panel_embed(active_t=None, t_service=t_service, config=config, profile=profile, recent=recent_tourneys)

    # Stats check
    assert "10W - 0L" in embed.description
    assert "10 Matches" in embed.description
    assert "3 Tourneys" in embed.description

    # Recent history check
    assert "Recent History" in [f.name for f in embed.fields]
    history_val = next(f.value for f in embed.fields if f.name == "Recent History")
    assert "Old T1" in history_val
    assert "COMPLETED" in history_val
    assert "Old T2" in history_val
    assert "CANCELLED" in history_val

    # Active tournament default
    assert "None running." in next(f.value for f in embed.fields if f.name == "Active Tournament")

def test_get_recent_tournaments(db_conn):
    t_service = TournamentService(db_conn)
    guild_id = "g1"

    # Create an active one (should not be returned)
    db_conn.execute("INSERT INTO tournaments (id, guild_id, name, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), guild_id, "Active", TournamentState.IN_PROGRESS.value, datetime.now().isoformat()))

    # Create 4 completed/cancelled
    for i in range(4):
        db_conn.execute("INSERT INTO tournaments (id, guild_id, name, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), guild_id, f"Done {i}", TournamentState.COMPLETED.value, datetime.now().isoformat()))
    db_conn.commit()

    # Fetch recent (default limit 3)
    recent = t_service.get_recent_tournaments(guild_id)
    assert len(recent) == 3
    for t in recent:
        assert "Done" in t.name
        assert t.state == TournamentState.COMPLETED
