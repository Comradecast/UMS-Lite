import discord
from discord.ext import commands
import logging
from typing import Any

from ums_lite.config import DISCORD_TOKEN, DB_PATH, SYNC_COMMANDS
from ums_lite.db.database import db_session, init_db
from ums_lite.ui.router import reconcile_active_messages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UMSLiteBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # needed to fetch member info for tournaments

        super().__init__(command_prefix="!", intents=intents)

        # Attach global app_command error handler
        self.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You do not have the required permissions to use this command.", ephemeral=True)
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"❌ The bot is missing required permissions to function: {missing}", ephemeral=True)
        else:
            logger.error(f"AppCommand Error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

    async def setup_hook(self):
        # Initialize DB Schema and connection provider
        logger.info("Initializing Database...")
        db_session.db_path = DB_PATH
        init_db(DB_PATH)

        # Load Cogs
        logger.info("Loading extensions...")
        await self.load_extension("ums_lite.cogs.ums_commands")
        await self.load_extension("ums_lite.cogs.events")

        # Sync slash commands
        if SYNC_COMMANDS:
            logger.info("Syncing slash commands...")
            await self.tree.sync()
            logger.info("Slash commands synced.")

        # Reconcile persistent UI
        logger.info("Starting UI reconciliation background task...")
        self.loop.create_task(self._run_reconciliation())

    async def _run_reconciliation(self):
        try:
            await reconcile_active_messages(self)
            logger.info("Startup UI reconciliation completed successfully.")
        except Exception as e:
            logger.error(f"Error during startup reconciliation: {e}")

def main():
    logger.info("Starting UMS Lite...")
    bot = UMSLiteBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
