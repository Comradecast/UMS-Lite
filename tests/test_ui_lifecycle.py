import pytest
import sqlite3
import uuid
from datetime import datetime

from ums_lite.db.database import DatabaseSchema
from ums_lite.db.repositories import TournamentRepo, MatchRepo
from ums_lite.db.models import Tournament, TournamentState, Match, MatchStatus

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DatabaseSchema.SCHEMA)
    conn.commit()
    yield conn
    conn.close()

def test_tournament_message_persistence(db_conn):
    t_repo = TournamentRepo(db_conn)
    t_id = uuid.uuid4()

    # Save a tournament with message metadata
    t = Tournament(
        id=t_id,
        guild_id="g1",
        name="T1",
        state=TournamentState.REGISTRATION_OPEN,
        created_at=datetime.now(),
        panel_channel_id="c1",
        panel_message_id="m1"
    )
    t_repo.save(t)

    # Reload and verify
    fetched = t_repo.get(t_id)
    assert fetched.panel_channel_id == "c1"
    assert fetched.panel_message_id == "m1"

    # Update message ID
    fetched.panel_message_id = "m2"
    t_repo.save(fetched)

    fetched2 = t_repo.get(t_id)
    assert fetched2.panel_message_id == "m2"

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ums_lite.ui.router import handle_ums_command

@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_router_ephemeral_enforcement(mock_db_session):
    # Mocking interaction and db dependencies
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn

    mock_interaction = MagicMock()
    mock_interaction.guild_id = "g1"
    mock_interaction.user.id = "u1"
    mock_interaction.user.guild_permissions.manage_guild = False

    mock_response = AsyncMock()
    mock_interaction.response = mock_response

    from ums_lite.db.models import GuildConfig
    config = GuildConfig(guild_id="g1", registration_channel_id="c1", match_channel_id="c2")

    # Priority 3: Fallback Public Panel
    with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=None):
        with patch('ums_lite.services.tournament_service.TournamentService.get_player_profile', return_value=None):
            with patch('ums_lite.services.tournament_service.TournamentService.get_guild_config', return_value=config):
                with patch('ums_lite.ui.router.sync_public_panel', new_callable=AsyncMock) as mock_sync:
                    await handle_ums_command(mock_interaction)
                    mock_response.send_message.assert_called_once()
                    _, kwargs = mock_response.send_message.call_args
                    assert kwargs.get('ephemeral') is True
                    mock_sync.assert_awaited_once()

def test_match_message_persistence(db_conn):
    t_repo = TournamentRepo(db_conn)
    m_repo = MatchRepo(db_conn)
    t_id = uuid.uuid4()

    # Create required tournament constraint
    t = Tournament(
        id=t_id,
        guild_id="g1",
        name="T1",
        state=TournamentState.IN_PROGRESS,
        created_at=datetime.now()
    )
    t_repo.save(t)

    m_id = uuid.uuid4()
    m = Match(
        id=m_id,
        tournament_id=t_id,
        round_number=1,
        match_number=1,
        status=MatchStatus.ACTIVE,
        message_channel_id="mc1",
        message_id="mm1"
    )
    m_repo.save(m)

    fetched = m_repo.get(m_id)
    assert fetched.message_channel_id == "mc1"
    assert fetched.message_id == "mm1"
