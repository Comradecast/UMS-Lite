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
        logger.info("Reconciling active persistent UI messages...")
        self.loop.create_task(reconcile_active_messages(self))

def main():
    if not DISCORD_TOKEN:
        logger.error("No DISCORD_TOKEN found in environment. Exiting.")
        return

    bot = UMSLiteBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
