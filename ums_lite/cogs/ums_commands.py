import discord
from discord import app_commands
from discord.ext import commands

from ums_lite.ui.router import get_ums_ui
from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.core.exceptions import UMSCoreException

class UMSCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ums", description="Open the UMS Lite panel")
    async def ums_panel(self, interaction: discord.Interaction):
        # We process everything ephemerally to keep channels clean
        # The stateless router determines exactly what panel this user should see right now.
        embed, view = get_ums_ui(interaction)

        if view:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Read-only view of the current tournament status")
    async def ums_status(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message("Must be run in a server.", ephemeral=True)
            return

        conn = db_session.get_connection()
        t_service = TournamentService(conn)

        active_t = t_service.get_active_tournament(str(interaction.guild_id))
        if not active_t:
            await interaction.response.send_message("ℹ️ No active tournament running right now.", ephemeral=True)
            return

        await interaction.response.send_message(f"🏆 **{active_t.name}** is currently: **{active_t.state.value}**", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UMSCommandsCog(bot))
