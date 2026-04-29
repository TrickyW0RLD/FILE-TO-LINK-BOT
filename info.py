import os

# ========== RENDER ENVIRONMENT VARIABLES (set these in Render dashboard) ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
PORT = int(os.environ.get("PORT", 8080))

# ========== FORCE SUBSCRIBE CHANNEL(S) ==========
# AUTH_CHANNEL can be multiple channel IDs separated by space: "-100123 -100456"
AUTH_CHANNEL = [int(i) for i in os.environ.get("AUTH_CHANNEL", "").split() if i]

# ========== LOG & BIN CHANNEL ==========
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))   # for bot logs
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))   # to store files temporarily

# ========== SUPPORT LINKS ==========
CHANNEL = os.environ.get("CHANNEL", "https://t.me/Anime_Hindii_Flixx")
SUPPORT = os.environ.get("SUPPORT", "https://t.me/Anime_Hindii_Flixx")

# ========== DATABASE (optional) ==========
DB_URL = os.environ.get("DATABASE_URI", "")
DB_NAME = os.environ.get("DATABASE_NAME", "filelinkbot")

# ========== OTHER ==========
ON_HEROKU = False
ON_RENDER = True
WORKERS = 10

# Build base URL for Render
FQDN = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if FQDN:
    URL = f"https://{FQDN}"
else:
    URL = ""
