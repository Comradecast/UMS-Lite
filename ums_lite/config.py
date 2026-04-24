import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
if not DISCORD_TOKEN:
    logger.error("CRITICAL: DISCORD_TOKEN environment variable is not set. Exiting.")
    sys.exit(1)

DB_PATH = os.getenv("DB_PATH", "data/ums_lite.db")

# Ensure the database directory exists
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to create database directory '{db_dir}': {e}")
        sys.exit(1)

# Optional config for sync / test behavior if needed
SYNC_COMMANDS = os.getenv("SYNC_COMMANDS", "true").lower() == "true"
