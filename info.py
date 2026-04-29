import os
from Script import script

# ========== RENDER ENVIRONMENT VARIABLES ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION = os.environ.get("SESSION", "FileLinkBot")
PORT = int(os.environ.get("PORT", 8080))

# ========== ADMINS ==========
ADMINS = [int(i) for i in os.environ.get("ADMINS", "").split() if i]

# ========== FORCE SUBSCRIBE CHANNELS ==========
AUTH_CHANNEL = [int(i) for i in os.environ.get("AUTH_CHANNEL", "").split() if i]

# ========== LOG & BIN CHANNELS ==========
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))

# ========== SUPPORT LINKS ==========
CHANNEL = os.environ.get("CHANNEL", "https://t.me/Anime_Hindii_Flixx")
SUPPORT = os.environ.get("SUPPORT", "https://t.me/Anime_Hindii_Flixx")

# ========== SHORTLINK ==========
IS_SHORTLINK = False
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "")

# ========== DATABASE ==========
DB_URL = os.environ.get("DATABASE_URI", "")
DB_NAME = os.environ.get("DATABASE_NAME", "filelinkbot")

# ========== FEATURES ==========
PUBLIC_FILE_STORE = False   # Only admin upload
FSUB = True if AUTH_CHANNEL else False
PROTECT_CONTENT = False
ENABLE_LIMIT = True

# ========== WEB SERVER (Render) ==========
ON_HEROKU = False
ON_RENDER = True
NO_PORT = os.environ.get("NO_PORT", "true").lower() in ("true", "1", "yes")
HAS_SSL = os.environ.get("HAS_SSL", "true").lower() in ("true", "1", "yes")

BIND_ADDRESS = os.environ.get("WEB_SERVER_BIND_ADDRESS", "")
FQDN = os.environ.get("FQDN", BIND_ADDRESS)

if ON_RENDER:
    FQDN = os.environ.get("RENDER_EXTERNAL_HOSTNAME", FQDN)

if not FQDN.startswith("http"):
    protocol = "https" if HAS_SSL else "http"
    port_segment = "" if NO_PORT else f":{PORT}"
    FQDN = FQDN.rstrip('/')
    URL = f"{protocol}://{FQDN}{port_segment}/"
else:
    URL = FQDN

WORKERS = 10
