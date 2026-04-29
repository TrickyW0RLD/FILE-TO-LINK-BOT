import os
import sys
import glob
import pytz
import asyncio
import logging
import importlib
from pathlib import Path
from datetime import date, datetime
from typing import Union, Optional, AsyncGenerator

# ======================== EVENT LOOP FIX FOR PYTHON 3.10+ ========================
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import pyrogram.utils

# ======================== PEER ID PATCH ========================
def get_peer_type_new(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

pyrogram.utils.get_peer_type = get_peer_type_new
pyrogram.utils.MIN_CHANNEL_ID = -1002822095763

# ======================== LOGGING SETUP ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

# ======================== IMPORTS FROM OTHER FILES ========================
from info import *
from Script import script
from aiohttp import web
from web import web_server, check_expired_premium
from web.server import StreamBot
from utils import Temp, ping_server
from web.server.clients import initialize_clients

# ======================== LOAD PLUGINS ========================
ppath = "plugins/*.py"
files = glob.glob(ppath)

# Start bot client
StreamBot.start()
bot_info = loop.run_until_complete(StreamBot.get_me())

# ======================== COMMAND HANDLER FOR /start AND /help ========================
@StreamBot.on_message(filters.command(["start", "help"]))
async def show_commands(client: Client, message: Message):
    """Send a list of available commands to the user"""
    commands_text = """
**🤖 Available Commands:**

/start - Start the bot and show welcome message
/help - Show this help message with all commands
/about - About this bot
/status - Check bot status (for admins)

**📁 File Upload:**
Simply send me any file/document/video/photo and I'll give you a direct download link!

**🔗 Features:**
- Generate instant download links from files
- No size limit (Telegram's 2GB limit applies)
- Works in groups and channels (if admin)
- Premium user support with expiry

**👨‍💻 Admin Commands:**
/broadcast - Send message to all users
/stats - Get bot statistics
/users - List all users
/premium - Manage premium users
"""
    # Buttons for better UI (optional)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support Group", url="https://t.me/your_support_group")],
        [InlineKeyboardButton("📝 Source Code", url="https://github.com/TrickyW0RLD/FILE-TO-LINK-BOT")]
    ])
    await message.reply_text(commands_text, reply_markup=buttons, disable_web_page_preview=True)

# Optional: /about command
@StreamBot.on_message(filters.command("about"))
async def about_bot(client: Client, message: Message):
    about_text = """
**📌 About This Bot**

🤖 **Name:** File to Link Bot
📦 **Version:** 2.0
👨‍💻 **Developer:** TrickyW0RLD
⚙️ **Language:** Python 3.10+ with Pyrogram
🌐 **Hosted on:** Render

**What it does:**
Send me any file and I'll generate a permanent direct download link for you.

**Privacy:**
We don't store any files. Links are generated on the fly.
"""
    await message.reply_text(about_text)

# ======================== MAIN START FUNCTION ========================
async def start():
    print('\n')
    print('🤖 Initializing Your Bot...')
    bot_info = await StreamBot.get_me()
    await initialize_clients()
    
    # Load all plugins
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("✅ Imported => " + plugin_name)
    
    if ON_HEROKU:
        asyncio.create_task(ping_server())
    
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    Temp.U_NAME = me.username
    Temp.B_NAME = me.first_name
    
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    
    StreamBot.loop.create_task(check_expired_premium(StreamBot))
    
    # Send startup messages to log channel and admins
    try:
        await StreamBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
    except Exception as e:
        logging.error(f"Could not send to LOG_CHANNEL: {e}")
    
    try:
        await StreamBot.send_message(chat_id=ADMINS[0], text='✅ <b>Bot Restarted Successfully!</b>')
    except Exception as e:
        logging.error(f"Could not send to ADMINS: {e}")
    
    try:
        await StreamBot.send_message(chat_id=SUPPORT_GROUP, text=f"<b>{me.mention} is Alive 🎉</b>")
    except Exception as e:
        logging.error(f"Could not send to SUPPORT_GROUP: {e}")
    
    # Start web server
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    
    print(f"🚀 Bot is running! Username: @{me.username}")
    await idle()

# ======================== RUN THE BOT ========================
if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('🛑 Service Stopped')
    except Exception as e:
        logging.error(f"❌ Fatal Error: {e}")
