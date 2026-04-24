import pytest
import sqlite3
import uuid
import discord
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import Match, MatchStatus, Tournament, TournamentState, GuildConfig
from ums_lite.ui.router import _build_admin_panel_embed, _build_match_card_embed
from ums_lite.ui.panels import AdminControlPanel
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

def test_next_step_guidance_and_diagnostics(db_conn):
    t_service = TournamentService(db_conn)
    config = GuildConfig(guild_id="g1") # Missing channels explicitly

    t = Tournament(id=uuid.uuid4(), guild_id="g1", name="T1", state=TournamentState.DRAFT, created_at=datetime.now())

    # 1. Draft state, missing channels, no entrants
    embed = _build_admin_panel_embed(t, t_service, config)

    fields = {f.name: f.value for f in embed.fields}
    assert "Diagnostics" in fields
    assert "❌ Registration channel not set" in fields["Diagnostics"]
    assert "❌ No players registered" in fields["Diagnostics"]

    assert "Next Step" in fields
    assert "→ Set Channels" in fields["Next Step"]
    assert "→ Open Registration" in fields["Next Step"]

    # 2. Registration Open state
    t.state = TournamentState.REGISTRATION_OPEN
    embed = _build_admin_panel_embed(t, t_service, config)
    fields = {f.name: f.value for f in embed.fields}
    assert "→ Wait for players" in fields["Next Step"]

    # 3. Completed
    t.state = TournamentState.COMPLETED
    embed = _build_admin_panel_embed(t, t_service, config)
    fields = {f.name: f.value for f in embed.fields}
    assert "→ Review results" in fields["Next Step"]

import asyncio

@pytest.mark.asyncio
async def test_admin_start_button_disabled_guard(db_conn):
    # Verify that the AdminControlPanel explicitly disables the start button if < 2 entrants
    t_service = TournamentService(db_conn)
    t_id = uuid.uuid4()
    db_conn.execute("INSERT INTO tournaments (id, guild_id, name, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(t_id), "g1", "T1", TournamentState.REGISTRATION_CLOSED.value, datetime.now().isoformat()))

    t = t_service.tournament_repo.get(t_id)

    # Needs a mock db session locally since the view pulls its own connection
    with patch('ums_lite.ui.panels.db_session') as mock_db:
        mock_db.get_connection.return_value = db_conn
        view = AdminControlPanel("g1", t)

        # Find start button
        start_btn = next((c for c in view.children if c.custom_id == "admin_start"), None)
        assert start_btn is not None
        assert start_btn.disabled is True

        # Now add 2 entrants
        db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES ('P1')")
        db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES ('P2')")
        db_conn.execute("INSERT INTO tournament_entries (id, tournament_id, player_id, joined_at) VALUES (?, ?, ?, ?)",
                        (str(uuid.uuid4()), str(t_id), "P1", datetime.now().isoformat()))
        db_conn.execute("INSERT INTO tournament_entries (id, tournament_id, player_id, joined_at) VALUES (?, ?, ?, ?)",
                        (str(uuid.uuid4()), str(t_id), "P2", datetime.now().isoformat()))

        # Reload view
        view2 = AdminControlPanel("g1", t)
        start_btn2 = next((c for c in view2.children if c.custom_id == "admin_start"), None)
        assert start_btn2.disabled is False

def test_match_guidance_render():
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)
    embed = _build_match_card_embed(m, [])
    fields = {f.name: f.value for f in embed.fields}

    assert "Guidance" in fields
    assert "Report your match result below." in fields["Guidance"]

    m.status = MatchStatus.AWAITING_CONFIRMATION
    embed = _build_match_card_embed(m, [])
    fields = {f.name: f.value for f in embed.fields}
    assert "Waiting for opponent to confirm" in fields["Guidance"]
