import os
from Script import script

# ==================== BOT TOKEN & API ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")  # Telegram BotFather se lo
API_ID = int(os.environ.get("API_ID", ""))    # my.telegram.org se lo
API_HASH = os.environ.get("API_HASH", "")    # my.telegram.org se lo

# ==================== OWNER & ADMINS ====================
# ADMINS me apna Telegram user ID daalo (ek number, comma nahi)
ADMINS = [int(i) for i in os.environ.get("ADMINS", "").split() if i]
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "")  # Optional
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")      # Optional

# ==================== CHANNELS & SUPPORT ====================
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))        # Channel ID (negative, -100 se start)
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))        # Backup channel ID
PREMIUM_LOGS = int(os.environ.get("PREMIUM_LOGS", 0))      # Premium logs channel
VERIFIED_LOG = int(os.environ.get("VERIFIED_LOG", 0))      # Verification logs
SUPPORT_GROUP = int(os.environ.get("SUPPORT_GROUP", 0))    # Support group ID
AUTH_CHANNEL = [int(i) for i in os.environ.get("AUTH_CHANNEL", "").split() if i]

# Links for buttons
CHANNEL = os.environ.get("CHANNEL", "https://t.me/your_channel")
SUPPORT = os.environ.get("SUPPORT", "https://t.me/your_support")

# ==================== FEATURE TOGGLES ====================
VERIFY = False                      # User verification (True/False)
FSUB = os.environ.get("FSUB", "True").lower() == "true"   # Force subscribe
ENABLE_LIMIT = os.environ.get("ENABLE_LIMIT", "True").lower() == "true"
BATCH_VERIFY = False
IS_SHORTLINK = False                # Shortlink feature OFF (set True if you have shortlink API)
MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE", "False").lower() == "true"
PROTECT_CONTENT = os.environ.get("PROTECT_CONTENT", "False").lower() == "true"
PUBLIC_FILE_STORE = os.environ.get("PUBLIC_FILE_STORE", "True").lower() == "true"
BATCH_PROTECT_CONTENT = False

# ==================== SHORTLINK (if enabled) ====================
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "")

# ==================== DATABASE ====================
DB_URL = os.environ.get("DATABASE_URI", "")      # MongoDB URI
DB_NAME = os.environ.get("DATABASE_NAME", "filelinkbot")

# ==================== IMAGES & CAPTIONS ====================
QR_CODE = os.environ.get("QR_CODE", "https://graph.org/file/your_image.jpg")
VERIFY_IMG = os.environ.get("VERIFY_IMG", "https://graph.org/file/your_image.jpg")
AUTH_PICS = os.environ.get("AUTH_PICS", "https://graph.org/file/your_image.jpg")
PICS = os.environ.get("PICS", "https://graph.org/file/your_image.jpg")
FILE_PIC = os.environ.get("FILE_PIC", "https://graph.org/file/your_image.jpg")

FILE_CAPTION = os.environ.get("FILE_CAPTION", script.CAPTION)
BATCH_FILE_CAPTION = os.environ.get("BATCH_FILE_CAPTION", script.CAPTION)
CHANNEL_FILE_CAPTION = os.environ.get("CHANNEL_FILE_CAPTION", script.CAPTION)

# ==================== TIME & LIMITS ====================
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", 1200))
SLEEP_THRESHOLD = int(os.environ.get("SLEEP_THRESHOLD", 60))
RATE_LIMIT_TIMEOUT = int(os.environ.get("RATE_LIMIT_TIMEOUT", 600))
MAX_FILES = int(os.environ.get("MAX_FILES", 50))
VERIFY_EXPIRE = int(os.environ.get("VERIFY_EXPIRE", 60))   # Hours

# ==================== WORKERS ====================
WORKERS = int(os.environ.get("WORKERS", 10))
MULTI_CLIENT = False
NAME = os.environ.get("NAME", "FileLinkBot")

# ==================== WEB SERVER (RENDER SPECIFIC) ====================
ON_HEROKU = 'DYNO' in os.environ   # Heroku detect
ON_RENDER = 'RENDER' in os.environ  # Render detect

PORT = int(os.environ.get("PORT", 8080))
NO_PORT = os.environ.get("NO_PORT", "true").lower() in ("true", "1", "yes")
HAS_SSL = os.environ.get("HAS_SSL", "true").lower() in ("true", "1", "yes")

# Base URL for generating links
BIND_ADDRESS = os.environ.get("WEB_SERVER_BIND_ADDRESS", "")
FQDN = os.environ.get("FQDN", BIND_ADDRESS)

# For Render: automatically use the external hostname
if ON_RENDER:
    FQDN = os.environ.get("RENDER_EXTERNAL_HOSTNAME", FQDN)

if not FQDN.startswith("http"):
    protocol = "https" if HAS_SSL else "http"
    port_segment = "" if NO_PORT else f":{PORT}"
    FQDN = FQDN.rstrip('/')
    URL = f"{protocol}://{FQDN}{port_segment}/"
else:
    URL = FQDN
