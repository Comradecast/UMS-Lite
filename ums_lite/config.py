import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "ums_lite.db")

# Optional config for sync / test behavior if needed
SYNC_COMMANDS = os.getenv("SYNC_COMMANDS", "true").lower() == "true"
