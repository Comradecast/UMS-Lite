import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Bot logged in as {self.bot.user}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        logger.error(f"Command Error: {error}")
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
        else:
            await ctx.send("An unexpected error occurred.")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
