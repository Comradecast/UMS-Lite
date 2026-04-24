import pytest
import uuid
import sqlite3
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.models import Tournament, TournamentState, GuildConfig
from ums_lite.ui.router import handle_ums_command, sync_public_panel

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_no_sync_during_draft(mock_db_session):
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn

    mock_interaction = MagicMock()
    mock_interaction.guild_id = "g1"
    mock_interaction.user.id = "u1"
    mock_interaction.user.guild_permissions.manage_guild = True

    mock_response = AsyncMock()
    mock_interaction.response = mock_response

    # Active tournament in DRAFT
    draft_t = Tournament(
        id=uuid.uuid4(), guild_id="g1", name="Draft T", state=TournamentState.DRAFT, created_at=datetime.now()
    )
    config = GuildConfig(guild_id="g1", registration_channel_id="c1", match_channel_id="c2")

    with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=draft_t):
        with patch('ums_lite.services.tournament_service.TournamentService.get_guild_config', return_value=config):
            with patch('ums_lite.services.tournament_service.TournamentService.get_player_profile', return_value=None):
                with patch('ums_lite.ui.router.sync_public_panel', new_callable=AsyncMock) as mock_sync:
                    await handle_ums_command(mock_interaction)

                    # Should send the admin panel ephemerally
                    mock_response.send_message.assert_called_once()

                    # sync_public_panel should NOT be called because it's DRAFT
                    mock_sync.assert_not_called()

@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_sync_public_panel_exits_early_on_draft(mock_db_session):
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn
    mock_client = MagicMock()

    draft_t = Tournament(
        id=uuid.uuid4(), guild_id="g1", name="Draft T", state=TournamentState.DRAFT, created_at=datetime.now()
    )

    with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=draft_t):
        with patch('ums_lite.ui.router._build_public_panel') as mock_build:
            await sync_public_panel(mock_client, "g1")

            # _build_public_panel should never be called
            mock_build.assert_not_called()
