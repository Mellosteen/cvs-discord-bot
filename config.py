from dotenv import load_dotenv
import os

load_dotenv()

# config for wiki_client.py
WIKI_API = os.getenv("WIKI_API")
WIKI_UA = os.getenv("WIKI_UA", "CVSCraftDiscordBot/0.1")
WIKI_USER = os.getenv("WIKI_USER")
WIKI_PASS = os.getenv("WIKI_PASS")

# config for bot.py
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CLOSET_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))
UPLOAD_CH_ID = int(os.getenv("UPLOAD_CHANNEL_ID"))