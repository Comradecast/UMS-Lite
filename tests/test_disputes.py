import pytest
import sqlite3
import uuid
import discord
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import Match, MatchStatus, MatchReport, Tournament, TournamentState, PlayerProfile
from ums_lite.ui.match_views import MatchCard
from ums_lite.ui.router import _build_admin_panel_embed, _build_public_panel
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

import asyncio

@pytest.mark.asyncio
async def test_match_card_admin_buttons():
    # Regular active match - no admin buttons
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)

    view = MatchCard(m, is_admin=True)
    assert len(view.children) == 2
    assert view.children[0].label == "I Won"

    # Disputed match, non-admin
    m.status = MatchStatus.DISPUTED
    view = MatchCard(m, is_admin=False)
    assert len(view.children) == 0 # no buttons for players on disputed

    # Disputed match, admin
    view = MatchCard(m, is_admin=True)
    assert len(view.children) == 2
    assert "Force P1" in view.children[0].label
    assert "Force P2" in view.children[1].label

def test_admin_panel_dispute_display(db_conn):
    t_service = TournamentService(db_conn)

    # Needs to be saved in DB to satisfy the entrant count lookup
    t = t_service.create_tournament("g1", "T1")
    t.state = TournamentState.IN_PROGRESS
    t_service.tournament_repo.save(t)

    m = Match(id=uuid.uuid4(), tournament_id=t.id, round_number=1, match_number=2, player1_id="P1", player2_id="P2", status=MatchStatus.DISPUTED)

    config = MagicMock()
    config.elo_enabled = False
    config.registration_channel_id = "c1"
    config.match_channel_id = "c2"

    embed = _build_admin_panel_embed(active_t=t, t_service=t_service, config=config, disputed_matches=[m])

    fields = {f.name: f.value for f in embed.fields}
    assert "⚠️ Disputed Matches" in fields
    assert "<@P1> vs <@P2>" in fields["⚠️ Disputed Matches"]
    assert "Diagnostics" in fields
    assert "⚠️ Disputed matches require attention" in fields["Diagnostics"]

@pytest.mark.asyncio
async def test_public_panel_winner_display(db_conn):
    t_service = TournamentService(db_conn)

    # Populate the DB to test the actual lookup
    t_id = uuid.uuid4()
    db_conn.execute("INSERT INTO tournaments (id, guild_id, name, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(t_id), "g1", "Finished T", TournamentState.COMPLETED.value, datetime.now().isoformat()))

    db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES (?)", ("WINNER",))
    db_conn.execute("INSERT INTO player_profiles (discord_id) VALUES (?)", ("P1",))

    # Insert final match resolved (needs player1_id and player2_id to exist in profiles due to strict FKs)
    db_conn.execute("INSERT INTO matches (id, tournament_id, round_number, match_number, player1_id, player2_id, winner_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), str(t_id), 2, 1, "P1", "WINNER", "WINNER", MatchStatus.RESOLVED.value))

    t = t_service.tournament_repo.get(t_id)

    embed, _ = _build_public_panel(t, t_service, None)

    fields = {f.name: f.value for f in embed.fields}
    assert "🏆 Tournament Winner" in fields
    assert "<@WINNER>" in fields["🏆 Tournament Winner"]
    assert "COMPLETE" in embed.description
