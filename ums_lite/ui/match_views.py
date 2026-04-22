import discord
from discord.ui import View, Button
import uuid

from ums_lite.db.database import db_session
from ums_lite.services.match_service import MatchService
from ums_lite.services.tournament_service import TournamentService
from ums_lite.db.models import MatchStatus, TournamentState
from ums_lite.core.exceptions import UMSCoreException

class MatchCard(View):
    def __init__(self, match_id: uuid.UUID):
        super().__init__(timeout=None)
        self.match_id = match_id

        btn_won = Button(label="I Won", style=discord.ButtonStyle.success, custom_id=f"match_won_{match_id}")
        btn_won.callback = self.won_callback
        self.add_item(btn_won)

        btn_lost = Button(label="I Lost", style=discord.ButtonStyle.danger, custom_id=f"match_lost_{match_id}")
        btn_lost.callback = self.lost_callback
        self.add_item(btn_lost)

    def _get_service(self):
        return MatchService(db_session.get_connection())

    async def _handle_report(self, interaction: discord.Interaction, claimed_winner_id: str):
        user_id = str(interaction.user.id)
        service = self._get_service()

        try:
            service.report_match(self.match_id, user_id, claimed_winner_id)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        # We need to re-render the shared match card, not just respond ephemerally to the click.
        match = service.match_repo.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Match not found.", ephemeral=True)
            return

        from ums_lite.ui.router import _render_persistent_match_card, _build_match_card_embed
        embed = _build_match_card_embed(match)

        view = self if match.status not in [MatchStatus.RESOLVED, MatchStatus.DISPUTED] else None

        # `_render_persistent_match_card` handles looking up the shared message and editing it.
        # It also handles deferring/acknowledging the current interaction.
        await _render_persistent_match_card(interaction, match, embed, view, service)

        # If the tournament is complete, sync public panel
        if match.status == MatchStatus.RESOLVED:
            t_service = TournamentService(service.conn)
            t = t_service.tournament_repo.get(match.tournament_id)
            if t and t.state == TournamentState.COMPLETED:
                from ums_lite.ui.router import sync_public_panel
                await sync_public_panel(interaction.client, t.guild_id)

    async def won_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self._handle_report(interaction, user_id)

    async def lost_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        service = self._get_service()

        match = service.match_repo.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Match not found.", ephemeral=True)
            return

        opponent_id = match.player2_id if match.player1_id == user_id else match.player1_id
        await self._handle_report(interaction, opponent_id)
