# CVSCraft Discord Bot

A Discord bot built for the CVSCraft community server. Allows members to upload images and rendered Minecraft skins directly to the community's Miraheze wiki through Discord commands.

---

## Features

- Upload images to the CVSCraft Miraheze wiki directly from Discord
- Upload raw Minecraft skin PNGs and have them automatically rendered before upload
- Validates skin dimensions before rendering
- Console-to-Discord relay for bot operator messages

---

## Tech Stack

- **[Discord.py](https://discordpy.readthedocs.io/)** — Discord bot framework
- **[minepi](https://github.com/benno1237/MinePI)** — Minecraft skin rendering
- **[Pillow](https://pypi.org/project/pillow/)** — Image processing
- **[MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)** — Wiki upload via HTTP requests
- **Python 3.11**

---

## Commands

| Command | Description |
|---|---|
| `!upload [type] [name] [descriptor]` | Upload an image to the wiki. Optional fields build the filename. |
| `!uploadskin [type] [name] [descriptor]` | Upload a raw Minecraft skin PNG. The bot renders it before uploading. |
| `!shutdown` | Shuts down the bot (owner only). |
| `!whoami` | Identifies who you are if you're a recognized member. |
| `!evaluateme` | Totally accurate self-evaluation. |

---

## Setup

### Prerequisites

- Python 3.11
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- A Miraheze wiki with a bot password set up ([instructions](https://meta.miraheze.org/wiki/Bot_passwords))

### Installation

1. Clone the repository:
    ```bash
    git clone [your-repo-url]
    cd cvs-image-bot
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory with the following:
    ```
    BOT_TOKEN=your_discord_bot_token
    CLOSET_ID=your_main_channel_id
    OWNER_ID=your_discord_user_id
    UPLOAD_CHANNEL_ID=your_upload_channel_id
    WIKI_API=your_wiki_api_endpoint
    WIKI_USER=your_wiki_username
    WIKI_PASS=your_wiki_bot_password
    WIKI_UA=CVSCraftDiscordBot/0.1
    ```

4. Run the bot:
    ```bash
    python bot.py
    ```

---

## How It Works

### Image Upload (`!upload`)
The bot accepts an image attachment, saves the image locally,
and uploads it to the wiki under the desired filename.

### Skin Upload (`!uploadskin`)
The bot accepts a raw Minecraft skin PNG (must be 64x64 or 64x32 pixels), renders it into a 3D isometric view using minepi, saves the rendered image locally, and uploads it to the wiki under a `_rendered` filename.

### Wiki Authentication
Authentication is handled in `wiki_client.py` using the MediaWiki API. Each upload request fetches a fresh login token, authenticates with a bot password, verifies the session, and retrieves a CSRF token before uploading.

---

## Notes

- The bot uses a dedicated bot password on Miraheze rather than the main account password for security.
- The MediaWiki API endpoint for this wiki is `https://cvscraft.miraheze.org/w/api.php`.
- All sensitive credentials are stored in `.env` and never committed to the repository.

---

## License

[MIT](LICENSE)
