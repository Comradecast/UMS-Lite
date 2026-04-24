# UMS Lite

UMS Lite is a stripped-down, single-server Discord tournament management bot. It is designed to handle 1v1 single-elimination formats natively entirely within Discord using a modern, stateless, button-heavy UX.

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- A Discord Bot Application with the necessary intents enabled.

### 1. Configure the Environment
Clone the repository and create your `.env` file based on the provided example:

```bash
cp .env.example .env
```

Edit `.env` and fill in your `DISCORD_TOKEN`.

### 2. Discord Bot Privileges & Intents
When inviting the bot to your server, ensure it has the following standard permissions:
- `Send Messages`
- `Read Message History`
- `Embed Links`
- `Use Application Commands`

**Required Intents:**
In the Discord Developer Portal, you **must** enable the `Server Members Intent` and `Message Content Intent` so the bot can securely track user participation and fetch historical sync data.

### 3. Run Locally

Install the required dependencies:
```bash
pip install -r requirements.txt
```

Start the bot:
```bash
python3 -m ums_lite.bot
```
*Note: The bot will automatically create its SQLite database file inside the `data/` directory.*

## 🏆 How to Start a Test Tournament

1. Provide an admin the `Manage Server` permission in Discord.
2. The admin types `/ums` in a designated tournament channel.
3. The private **Admin Control Panel** will appear. Click **Create Tournament**.
4. Click **Open Registration**. This will spawn a public panel for users.
5. Have users type `/ums` or click the **Join** button on the public panel to enter.
6. As the Admin, click **Generate & Start** in your `/ums` console.
7. The bracket will generate and interactive Match Cards will immediately render in the channel.

## ⚠️ Known Limitations (MVP)
- **Format:** Supports 1v1 Single Elimination only.
- **Federation/Web:** Strictly offline and localized to a single Discord server. No web dashboards.
- **Seeding:** Generates brackets deterministically via join-order. Complex algorithmic seeding is not included in the MVP.
- **Elo:** Plumbed into the database schema but currently inactive.
