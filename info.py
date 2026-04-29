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

# ========== LOG & BIN CHANNELS & OTHER CHANNELS ==========
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))
PREMIUM_LOGS = int(os.environ.get("PREMIUM_LOGS", 0))        # Added
VERIFIED_LOG = int(os.environ.get("VERIFIED_LOG", 0))        # Added
SUPPORT_GROUP = int(os.environ.get("SUPPORT_GROUP", 0))      # Added

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

# ========== OTHER OPTIONAL ==========
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
HOW_TO_VERIFY = os.environ.get("HOW_TO_VERIFY", "")
HOW_TO_OPEN = os.environ.get("HOW_TO_OPEN", "")
QR_CODE = os.environ.get("QR_CODE", "")
VERIFY_IMG = os.environ.get("VERIFY_IMG", "")
AUTH_PICS = os.environ.get("AUTH_PICS", "")
PICS = os.environ.get("PICS", "")
FILE_PIC = os.environ.get("FILE_PIC", "")
FILE_CAPTION = os.environ.get("FILE_CAPTION", script.CAPTION)
BATCH_FILE_CAPTION = os.environ.get("BATCH_FILE_CAPTION", script.CAPTION)
CHANNEL_FILE_CAPTION = os.environ.get("CHANNEL_FILE_CAPTION", script.CAPTION)
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", 1200))
SLEEP_THRESHOLD = int(os.environ.get("SLEEP_THRESHOLD", 60))
RATE_LIMIT_TIMEOUT = int(os.environ.get("RATE_LIMIT_TIMEOUT", 600))
MAX_FILES = int(os.environ.get("MAX_FILES", 50))
VERIFY_EXPIRE = int(os.environ.get("VERIFY_EXPIRE", 60))
WORKERS = int(os.environ.get("WORKERS", 10))
MULTI_CLIENT = False
NAME = os.environ.get("NAME", "FileLinkBot")

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
