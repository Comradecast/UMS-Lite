import pytest
import uuid
import discord
from unittest.mock import AsyncMock, MagicMock, patch

from ums_lite.db.models import Match, MatchStatus, MatchReport, Tournament, TournamentState
from ums_lite.ui.router import _build_match_card_embed, sync_public_panel, sync_match_card

def test_build_match_card_embed_states():
    # Test Active
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)
    embed = _build_match_card_embed(m, [])
    assert embed.color == discord.Color.blue()

    # Test Awaiting Confirmation
    m.status = MatchStatus.AWAITING_CONFIRMATION
    r1 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P1", claimed_winner_id="P1", reported_at=None) # type: ignore
    embed = _build_match_card_embed(m, [r1])
    assert embed.color == discord.Color.orange()
    assert "Reports" in [f.name for f in embed.fields]
    reports_value = next(f.value for f in embed.fields if f.name == "Reports")
    assert "<@P1> claimed <@P1> won." in reports_value

    # Test Disputed
    m.status = MatchStatus.DISPUTED
    r2 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P2", claimed_winner_id="P2", reported_at=None) # type: ignore
    embed = _build_match_card_embed(m, [r1, r2])
    assert embed.color == discord.Color.red()
    reports_value = next(f.value for f in embed.fields if f.name == "Reports")
    assert "<@P2> claimed <@P2> won." in reports_value

    # Test Resolved
    m.status = MatchStatus.RESOLVED
    m.winner_id = "P1"
    embed = _build_match_card_embed(m, [r1])
    assert embed.color == discord.Color.green()
    assert "👑 Winner" in [f.name for f in embed.fields]
    winner_value = next(f.value for f in embed.fields if f.name == "👑 Winner")
    assert "<@P1>" in winner_value


@pytest.mark.asyncio
@patch('ums_lite.ui.router.db_session')
async def test_sync_public_panel_recovery(mock_db_session):
    # Setup mock service/repo
    mock_conn = MagicMock()
    mock_db_session.get_connection.return_value = mock_conn

    t_id = uuid.uuid4()
    mock_tournament = Tournament(
        id=t_id, guild_id="g1", name="T1", state=TournamentState.REGISTRATION_OPEN, created_at=None, # type: ignore
        panel_channel_id="111", panel_message_id="222"
    )

    # Since router initializes TournamentService internally, we patch its get_active_tournament
    with patch('ums_lite.services.tournament_service.TournamentService.get_active_tournament', return_value=mock_tournament):
        with patch('ums_lite.services.tournament_service.EntryRepo.get_by_tournament', return_value=[]):
            with patch('ums_lite.services.tournament_service.TournamentRepo.save') as mock_save:

                # Mock Discord Client
                mock_client = MagicMock()
                mock_channel = AsyncMock()
                mock_client.get_channel.return_value = mock_channel

                # Simulate the message fetch failing because it was deleted
                mock_channel.fetch_message.side_effect = discord.NotFound(response=MagicMock(), message="Not Found")

                # Simulate channel.send creating a new message
                mock_new_msg = MagicMock()
                mock_new_msg.id = 999
                mock_channel.send.return_value = mock_new_msg

                await sync_public_panel(mock_client, "g1")

                # Verify that it tried to fetch the old one
                mock_channel.fetch_message.assert_called_once_with(222)

                # Verify that it recovered by sending a new one
                mock_channel.send.assert_called_once()

                # Verify that it saved the newly recovered message ID
                assert mock_tournament.panel_message_id == "999"
                mock_save.assert_called_once_with(mock_tournament)
