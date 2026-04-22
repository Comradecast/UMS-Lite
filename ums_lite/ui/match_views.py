import discord
from discord.ui import View, Button
import uuid

from ums_lite.db.database import db_session
from ums_lite.services.match_service import MatchService
from ums_lite.core.exceptions import UMSCoreException

def _re_render(interaction):
    from ums_lite.ui.router import render_ui
    return render_ui(interaction)

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
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        service = self._get_service()

        try:
            service.report_match(self.match_id, user_id, claimed_winner_id)
        except UMSCoreException as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

        await _re_render(interaction)

    async def won_callback(self, interaction: discord.Interaction):
        # Claim they won
        user_id = str(interaction.user.id)
        await self._handle_report(interaction, user_id)

    async def lost_callback(self, interaction: discord.Interaction):
        # Claim opponent won. We don't have opponent ID easily in view,
        # but the service layer can deduce it or we can pass a special marker.
        # For our service layer, claimed_winner_id needs to be the actual ID.
        # Since we don't have the opponent ID here easily without a DB call,
        # let's do the DB call.
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)

        conn = db_session.get_connection()
        service = MatchService(conn)

        match = service.match_repo.get(self.match_id)
        if not match:
            await interaction.followup.send("❌ Match not found.", ephemeral=True)
            return

        opponent_id = match.player2_id if match.player1_id == user_id else match.player1_id

        try:
            service.report_match(self.match_id, user_id, opponent_id)
        except UMSCoreException as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

        await _re_render(interaction)
