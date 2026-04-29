import os
import sys
import glob
import pytz
import asyncio
import logging
import importlib
from pathlib import Path
from datetime import date, datetime

# ========== EVENT LOOP FIX (Python 3.10+) ==========
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pyrogram.utils

# ========== PEER ID PATCH ==========
def get_peer_type_new(peer_id: int) -> str:
    s = str(peer_id)
    if not s.startswith("-"):
        return "user"
    elif s.startswith("-100"):
        return "channel"
    else:
        return "chat"
pyrogram.utils.get_peer_type = get_peer_type_new
pyrogram.utils.MIN_CHANNEL_ID = -1002822095763

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# ========== IMPORTS FROM YOUR PROJECT ==========
from info import *
from Script import script
from aiohttp import web
from web import web_server, check_expired_premium
from web.server import StreamBot
from utils import Temp, ping_server
from web.server.clients import initialize_clients

# ========== KEEP ALIVE FUNCTION (prevents bot from sleeping) ==========
async def keep_alive():
    while True:
        await asyncio.sleep(180)  # Har 3 minute
        try:
            me = await StreamBot.get_me()
            logger.info(f"Keep-alive: @{me.username} is alive")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
            try:
                await StreamBot.restart()
            except:
                pass

# ========== COMMANDS (so that /start shows menu) ==========
@StreamBot.on_message(filters.command(["start", "help"]))
async def show_commands(client, message):
    text = """**🤖 Bot Commands:**

/start - Start the bot
/help - Show this help
/about - About bot

**📁 How to use:**
Just send me any file (photo, video, document, audio) and I will give you a direct download link.

**🔗 Features:**
- Instant links
- No size limit (up to 2GB due to Telegram)
- Works in groups (admin required)"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support", url="https://t.me/your_support")]
    ])
    await message.reply_text(text, reply_markup=buttons)

@StreamBot.on_message(filters.command("about"))
async def about_bot(client, message):
    await message.reply_text("**File to Link Bot**\nVersion 2.0\nMade with Pyrogram\nHosted on Render")

# ========== MAIN START FUNCTION ==========
async def start():
    print("\n🚀 Initializing Bot...")
    
    # Start keep-alive task (important for Render)
    asyncio.create_task(keep_alive())
    
    # Initialize clients
    await initialize_clients()
    
    # Load all plugins from plugins/ folder
    ppath = "plugins/*.py"
    files = glob.glob(ppath)
    for name in files:
        with open(name) as f:
            plugin_name = Path(f.name).stem
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules[import_path] = mod
            print(f"✅ Imported plugin: {plugin_name}")
    
    if ON_HEROKU:
        asyncio.create_task(ping_server())
    
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    Temp.U_NAME = me.username
    Temp.B_NAME = me.first_name
    
    # Send startup notification (optional)
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S %p")
    try:
        await StreamBot.send_message(LOG_CHANNEL, f"✅ Bot restarted at {time_str}")
    except:
        pass
    
    # Start web server (required for Render to keep alive)
    app_runner = web.AppRunner(await web_server())
    await app_runner.setup()
    bind_address = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(app_runner, bind_address, port).start()
    logger.info(f"🌐 Web server started on port {port}")
    
    print(f"✅ Bot is running! Username: @{me.username}")
    await idle()

# ========== RUN WITH AUTO-RECONNECT ==========
async def run_with_reconnect():
    while True:
        try:
            await start()
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            logger.info("Restarting in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        loop.run_until_complete(run_with_reconnect())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
