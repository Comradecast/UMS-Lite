import discord
from discord.ui import View, Button
import uuid

from ums_lite.db.database import db_session
from ums_lite.services.match_service import MatchService
from ums_lite.services.tournament_service import TournamentService
from ums_lite.db.models import MatchStatus, TournamentState
from ums_lite.core.exceptions import UMSCoreException

class MatchCard(View):
    def __init__(self, match, is_admin=False):
        super().__init__(timeout=None)
        self.match_id = match.id
        self.tournament_id = match.tournament_id
        self.p1_id = match.player1_id
        self.p2_id = match.player2_id

        if match.status in [MatchStatus.ACTIVE, MatchStatus.AWAITING_CONFIRMATION]:
            btn_won = Button(label="I Won", style=discord.ButtonStyle.success, custom_id=f"match_won_{self.match_id}")
            btn_won.callback = self.won_callback
            self.add_item(btn_won)

            btn_lost = Button(label="I Lost", style=discord.ButtonStyle.danger, custom_id=f"match_lost_{self.match_id}")
            btn_lost.callback = self.lost_callback
            self.add_item(btn_lost)

        if match.status == MatchStatus.DISPUTED and is_admin:
            btn_force_p1 = Button(label="🛡️ Force P1 Win", style=discord.ButtonStyle.danger, custom_id=f"force_p1_{self.match_id}")
            btn_force_p1.callback = self.force_p1_callback
            self.add_item(btn_force_p1)

            btn_force_p2 = Button(label="🛡️ Force P2 Win", style=discord.ButtonStyle.danger, custom_id=f"force_p2_{self.match_id}")
            btn_force_p2.callback = self.force_p2_callback
            self.add_item(btn_force_p2)

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

        match = service.match_repo.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Match not found.", ephemeral=True)
            return

        from ums_lite.ui.router import sync_match_card, sync_public_panel, _build_match_card_embed

        is_admin = interaction.user.guild_permissions.manage_guild
        # First, if the interaction was on an ephemeral panel, edit it in place
        if interaction.message and interaction.message.flags.ephemeral:
            reports = service.report_repo.get_by_match(match.id)
            embed = _build_match_card_embed(match, reports)

            # Recreate view with updated status so buttons disappear when resolved
            view = MatchCard(match, is_admin) if match.status != MatchStatus.RESOLVED else None

            # Inject stats for the ephemeral view
            profile = service.player_repo.get(user_id)
            if profile:
                desc = embed.description or ""
                embed.description = f"📊 **Your Stats:** {profile.wins}W - {profile.losses}L ({profile.matches_played} Matches)\n\n" + desc

            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.defer()

        # Next, always update the persistent, shared match card for all viewers.
        await sync_match_card(interaction.client, match.id)

        # Finally, handle tournament completion or next match syncing
        if match.status == MatchStatus.RESOLVED:
            if match.next_match_id:
                # The winner advanced, we need to sync the downstream match card so it appears
                await sync_match_card(interaction.client, match.next_match_id)
            else:
                # Tournament complete, sync the public panel
                t_service = TournamentService(service.conn)
                t = t_service.tournament_repo.get(match.tournament_id)
                if t and t.state == TournamentState.COMPLETED:
                    from ums_lite.ui.router import announce_tournament_results
                    await sync_public_panel(interaction.client, t.guild_id, tournament_id=t.id)
                    await announce_tournament_results(interaction.client, t.id)

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

    async def _handle_admin_force(self, interaction: discord.Interaction, winner_id: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You do not have permission to force match outcomes.", ephemeral=True)
            return

        admin_id = str(interaction.user.id)
        guild_id = str(interaction.guild_id)
        service = self._get_service()

        try:
            service.admin_force_win(self.match_id, guild_id, admin_id, winner_id)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        # Re-fetch match after force
        match = service.match_repo.get(self.match_id)
        if not match:
            return

        from ums_lite.ui.router import sync_match_card, sync_public_panel, _build_match_card_embed

        # Admin is on an ephemeral router `/ums` panel, edit it
        if interaction.message and interaction.message.flags.ephemeral:
            reports = service.report_repo.get_by_match(match.id)
            embed = _build_match_card_embed(match, reports)
            view = None # Resolved, buttons disappear

            # Admins usually get the admin panel when they type /ums, but if they had a match card open, we respect the edit.
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.defer()

        # Always update the persistent, shared match card for all viewers.
        await sync_match_card(interaction.client, match.id)

        # Finally, handle tournament completion or next match syncing
        if match.status == MatchStatus.RESOLVED:
            if match.next_match_id:
                # The winner advanced, we need to sync the downstream match card so it appears
                await sync_match_card(interaction.client, match.next_match_id)
            else:
                # Tournament complete, sync the public panel
                t_service = TournamentService(service.conn)
                t = t_service.tournament_repo.get(match.tournament_id)
                if t and t.state == TournamentState.COMPLETED:
                    from ums_lite.ui.router import announce_tournament_results
                    await sync_public_panel(interaction.client, t.guild_id, tournament_id=t.id)
                    await announce_tournament_results(interaction.client, t.id)

    async def force_p1_callback(self, interaction: discord.Interaction):
        if self.p1_id:
            await self._handle_admin_force(interaction, self.p1_id)

    async def force_p2_callback(self, interaction: discord.Interaction):
        if self.p2_id:
            await self._handle_admin_force(interaction, self.p2_id)
