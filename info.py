import os

# ========== TELEGRAM API ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION = os.environ.get("SESSION", "SimpleBot")
PORT = int(os.environ.get("PORT", 8080))

# ========== ADMINS (space separated IDs) ==========
ADMINS = [int(i) for i in os.environ.get("ADMINS", "").split() if i]

# ========== FORCE SUBSCRIBE CHANNELS (space separated IDs) ==========
AUTH_CHANNEL = [int(i) for i in os.environ.get("AUTH_CHANNEL", "").split() if i]

# ========== BIN CHANNEL (to store files) ==========
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))

# ========== SHORTLINK (optional) ==========
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "")

# ========== LINKS FOR BUTTONS ==========
CHANNEL_LINK = os.environ.get("CHANNEL", "https://t.me/Anime_Hindii_Flixx")
SUPPORT_LINK = os.environ.get("SUPPORT", "https://t.me/Anime_Hindii_Flixx")

# ========== CAPTION PREFIX (your username) ==========
CAPTION_PREFIX = "✨ **Shared by:** @Anime_Hindii_Flixx"
