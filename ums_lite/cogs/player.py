import discord
from discord import app_commands
from discord.ext import commands

from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.core.exceptions import UMSCoreException, DuplicateEntityError

class PlayerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_service(self) -> TournamentService:
        return TournamentService(db_session.get_connection())

    player_group = app_commands.Group(name="player", description="UMS Player Commands")

    @player_group.command(name="join", description="Join the currently open tournament")
    async def join(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message("This command must be run in a server.", ephemeral=True)
            return

        service = self._get_service()
        try:
            t = service.get_active_tournament(str(interaction.guild_id))
            if not t:
                await interaction.response.send_message("❌ No active tournament to join.", ephemeral=True)
                return

            service.join_tournament(t.id, str(interaction.user.id))
            await interaction.response.send_message(f"✅ You have joined **{t.name}**!", ephemeral=True)
        except DuplicateEntityError:
            await interaction.response.send_message("❌ You have already joined this tournament.", ephemeral=True)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @player_group.command(name="status", description="Check the status of the current tournament")
    async def status(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            return

        service = self._get_service()
        try:
            t = service.get_active_tournament(str(interaction.guild_id))
            if not t:
                await interaction.response.send_message("ℹ️ No active tournament running right now.", ephemeral=True)
                return

            await interaction.response.send_message(f"🏆 **{t.name}** is currently: **{t.state.value}**", ephemeral=True)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PlayerCog(bot))
