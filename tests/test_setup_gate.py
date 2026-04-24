import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ums_lite.ui.router import handle_ums_command
from ums_lite.db.models import GuildConfig

@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_router_setup_gate_admin(mock_db_session):
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn

    mock_interaction = MagicMock()
    mock_interaction.guild_id = "g1"
    mock_interaction.user.id = "u1"
    mock_interaction.user.guild_permissions.manage_guild = True
    mock_response = AsyncMock()
    mock_interaction.response = mock_response

    # Empty Config (Missing required channels)
    empty_config = GuildConfig(guild_id="g1")

    with patch('ums_lite.services.tournament_service.TournamentService.get_guild_config', return_value=empty_config):
        with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=None):
            with patch('ums_lite.services.tournament_service.TournamentService.get_player_profile', return_value=None):
                await handle_ums_command(mock_interaction)

                # Should send the setup gate embed ephemerally
                mock_response.send_message.assert_called_once()
                _, kwargs = mock_response.send_message.call_args
                embed = kwargs.get('embed')
                assert embed.title == "⚠️ Setup Required"
                assert kwargs.get('ephemeral') is True

@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_router_setup_gate_player(mock_db_session):
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn

    mock_interaction = MagicMock()
    mock_interaction.guild_id = "g1"
    mock_interaction.user.id = "u1"
    mock_interaction.user.guild_permissions.manage_guild = False # Not an admin
    mock_response = AsyncMock()
    mock_interaction.response = mock_response

    # Empty Config
    empty_config = GuildConfig(guild_id="g1")

    with patch('ums_lite.services.tournament_service.TournamentService.get_guild_config', return_value=empty_config):
        with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=None):
            with patch('ums_lite.services.tournament_service.TournamentService.get_player_profile', return_value=None):
                await handle_ums_command(mock_interaction)

                # Should send the ephemeral error string, not the setup UI
                mock_response.send_message.assert_called_once()
                args, kwargs = mock_response.send_message.call_args
                assert "not finished configuring" in args[0]
                assert kwargs.get('ephemeral') is True
