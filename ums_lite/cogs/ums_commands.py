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

async def setup(bot: commands.Bot):
    await bot.add_cog(UMSCommandsCog(bot))
