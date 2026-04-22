import discord
from discord import app_commands
from discord.ext import commands

from ums_lite.ui.router import handle_ums_command

class UMSCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ums", description="Open the UMS Lite panel")
    async def ums_panel(self, interaction: discord.Interaction):
        # We process everything ephemerally to keep channels clean
        # The stateless router determines exactly what panel this user should see right now.
        await handle_ums_command(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(UMSCommandsCog(bot))
