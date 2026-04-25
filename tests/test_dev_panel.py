import pytest
import sqlite3
import uuid
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import Tournament, TournamentState, GuildConfig
from ums_lite.services.tournament_service import TournamentService
from ums_lite.ui.router import _get_dev_health_state, _build_dev_health_embed, _build_debug_snapshot_text
from ums_lite.ui.panels import DevHealthPanel

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

@patch.dict(os.environ, {"DISCORD_TOKEN": "mock_token"})
def test_dev_health_state_generation(db_conn):
    # Need to patch the config fetch because DB_PATH might not be set in test env
    with patch('ums_lite.ui.router.db_session') as mock_db:
        mock_db.get_connection.return_value = db_conn

        t_service = TournamentService(db_conn)
        t = t_service.create_tournament("g1", "Dev T")
        t_service.update_guild_channels("g1", "c1", "c2", "c3")
        t_service.open_registration(t.id)

        with patch('ums_lite.ui.router.DB_PATH', "test.db", create=True):
            state = _get_dev_health_state("g1")

        assert state["db_reachable"] is True
        assert state["guild_id"] == "g1"
        assert state["setup_complete"] is True
        assert state["active_t"].name == "Dev T"
        assert state["entrant_count"] == 0
        assert state["active_match_count"] == 0
        assert state["disputed_match_count"] == 0

def test_dev_health_embed_render():
    config = GuildConfig("g1", registration_channel_id="c1", match_channel_id="c2")
    active_t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Dev T", state=TournamentState.IN_PROGRESS, created_at=datetime.now())

    state = {
        "db_path": "/test/ums.db",
        "db_reachable": True,
        "guild_id": "g1",
        "config": config,
        "active_t": active_t,
        "recent_t": [],
        "entrant_count": 5,
        "active_match_count": 2,
        "disputed_match_count": 1,
        "setup_complete": True
    }

    embed = _build_dev_health_embed(state)
    fields = {f.name: f.value for f in embed.fields}

    assert "System Health" in fields
    assert "✅ Yes" in fields["System Health"]

    assert "Guild Config" in fields
    assert "c1" in fields["Guild Config"]

    assert "Tournament State" in fields
    assert "Dev T" in fields["Tournament State"]
    assert "IN_PROGRESS" in fields["Tournament State"]
    assert "5" in fields["Tournament State"] # Entrants

def test_debug_snapshot_render():
    config = GuildConfig("g1", registration_channel_id="c1", match_channel_id="c2")
    active_t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Dev T", state=TournamentState.IN_PROGRESS, created_at=datetime.now())

    state = {
        "db_path": "/test/ums.db",
        "db_reachable": True,
        "guild_id": "g1",
        "config": config,
        "active_t": active_t,
        "recent_t": [],
        "entrant_count": 5,
        "active_match_count": 2,
        "disputed_match_count": 1,
        "setup_complete": True
    }

    text = _build_debug_snapshot_text(state)
    assert "--- UMS LITE DEBUG SNAPSHOT ---" in text
    assert "Guild ID: g1" in text
    assert "Setup Complete: True" in text
    assert "Active Matches: 2" in text
    assert "Disputed Matches: 1" in text

import asyncio
import pytest

@pytest.mark.asyncio
async def test_dev_panel_view_init():
    view = DevHealthPanel("g1", None)
    btn_ids = [c.custom_id for c in view.children]

    assert "dev_sync_pub" in btn_ids
    assert "dev_sync_matches" in btn_ids
    assert "dev_reconcile" in btn_ids
    assert "dev_refresh" in btn_ids
    assert "dev_snapshot" in btn_ids
