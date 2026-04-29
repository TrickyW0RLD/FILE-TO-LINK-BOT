import os, sys, glob, pytz, asyncio, logging, importlib
from pathlib import Path
from datetime import date, datetime, timedelta

# ========== EVENT LOOP FIX ==========
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters, Client
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, BotCommand
)
import pyrogram.utils

# ========== PEER ID PATCH ==========
def get_peer_type_new(peer_id: int) -> str:
    s = str(peer_id)
    if not s.startswith("-"): return "user"
    elif s.startswith("-100"): return "channel"
    else: return "chat"
pyrogram.utils.get_peer_type = get_peer_type_new
pyrogram.utils.MIN_CHANNEL_ID = -1002822095763

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== IMPORTS ==========
from info import *
from Script import script
from aiohttp import web
from web import web_server, check_expired_premium
from web.server import StreamBot
from utils import Temp, ping_server
from web.server.clients import initialize_clients

# ========== KEEP ALIVE ==========
async def keep_alive():
    while True:
        await asyncio.sleep(120)
        try:
            me = await StreamBot.get_me()
            logger.info(f"Alive: @{me.username}")
        except:
            pass

# ========== COMMAND PANEL (ADVANCED) ==========
@StreamBot.on_message(filters.command(["start"]))
async def start_cmd(client: Client, message: Message):
    # Main menu with buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Commands", callback_data="show_commands")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")] if message.from_user.id in ADMINS else [],
        [InlineKeyboardButton("🗂️ My Files", callback_data="my_files"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])
    await message.reply_text(
        f"**Welcome {message.from_user.mention}**\n\nI'm a advanced file-to-link bot.\nSend me any file to get a direct download link.\nUse buttons below for help.",
        reply_markup=buttons
    )

@StreamBot.on_message(filters.command(["help"]))
async def help_cmd(client: Client, message: Message):
    await show_commands_panel(message)

async def show_commands_panel(message: Message):
    text = """**📌 Available Commands:**

🔹 **User Commands:**
/start - Start bot and main menu
/help - Show this panel
/about - Bot info
/status - Check bot status

🔹 **File Commands:**
Send any file → receive direct link
/batch - Create batch links (if enabled)

🔹 **Admin Commands:**
/broadcast - Message to all users
/stats - Bot statistics
/users - List all users
/premium - Manage premium users

🔹 **Others:**
/settings - User settings
/myfiles - Your uploaded files"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ])
    await message.reply_text(text, reply_markup=buttons)

@StreamBot.on_message(filters.command(["about"]))
async def about_cmd(client: Client, message: Message):
    me = await client.get_me()
    text = f"""**🤖 About Bot**

**Name:** {me.first_name}
**Version:** 3.0 (Pro)
**Language:** Python 3.10 + Pyrogram
**Server:** Render

**Features:**
✅ Instant file links
✅ No size limit (≤2GB)
✅ User verification
✅ Premium support
✅ Batch processing

**Developer:** @{OWNER_USERNAME if OWNER_USERNAME else 'YourName'}"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ])
    await message.reply_text(text, reply_markup=buttons)

@StreamBot.on_message(filters.command(["broadcast"]) & filters.user(ADMINS))
async def broadcast_cmd(client: Client, message: Message):
    # Simple broadcast example
    if message.reply_to_message:
        msg = message.reply_to_message
        await message.reply_text("Broadcasting...")
        # Add your broadcast logic here
        await message.reply_text("✅ Broadcast sent!")
    else:
        await message.reply_text("Reply to a message with /broadcast to send to all users.")

@StreamBot.on_message(filters.command(["stats"]) & filters.user(ADMINS))
async def stats_cmd(client: Client, message: Message):
    # Add your stats gathering logic
    await message.reply_text("📊 **Bot Statistics**\n\nTotal Users: Fetching...\nFiles Stored: Fetching...")

# ========== CALLBACK HANDLERS ==========
@StreamBot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    if data == "show_commands":
        await show_commands_panel(query.message)
    elif data == "about":
        me = await client.get_me()
        text = f"**Bot:** {me.first_name}\n**Version:** 3.0 Pro\n**Developer:** @{OWNER_USERNAME}" if OWNER_USERNAME else "Developer: YourName"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "support":
        await query.message.edit_text(f"**Support:** {SUPPORT}\n**Channel:** {CHANNEL}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "admin_panel":
        if query.from_user.id in ADMINS:
            panel = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
            await query.message.edit_text("**Admin Panel**", reply_markup=panel)
        else:
            await query.answer("You are not admin!", show_alert=True)
    elif data == "main_menu":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Commands", callback_data="show_commands")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")] if query.from_user.id in ADMINS else [],
            [InlineKeyboardButton("🗂️ My Files", callback_data="my_files"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ])
        await query.message.edit_text("**Main Menu**\nChoose an option:", reply_markup=buttons)
    elif data == "my_files":
        await query.answer("Coming soon!", show_alert=True)
    elif data == "settings":
        await query.answer("Coming soon!", show_alert=True)
    elif data.startswith("admin_"):
        await query.answer("Feature in development", show_alert=True)

# ========== SET BOT COMMANDS (so Telegram shows them) ==========
async def set_bot_commands():
    commands = [
        BotCommand("start", "Start the bot & show menu"),
        BotCommand("help", "Show all commands"),
        BotCommand("about", "About this bot"),
        BotCommand("status", "Check bot status"),
    ]
    if ADMINS:
        commands.append(BotCommand("broadcast", "Send message to all users (admin)"))
        commands.append(BotCommand("stats", "View bot statistics (admin)"))
        commands.append(BotCommand("users", "List all users (admin)"))
    await StreamBot.set_bot_commands(commands)

# ========== MAIN START ==========
async def start():
    print("\n🚀 Starting Advanced Bot...")
    asyncio.create_task(keep_alive())
    await initialize_clients()
    
    # Load plugins
    for file in glob.glob("plugins/*.py"):
        plugin = Path(file).stem
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin}", file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[f"plugins.{plugin}"] = mod
        print(f"Loaded: {plugin}")
    
    if ON_HEROKU:
        asyncio.create_task(ping_server())
    
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    Temp.U_NAME = me.username
    Temp.B_NAME = me.first_name
    
    # Set commands for Telegram menu
    await set_bot_commands()
    
    # Start web server
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print(f"✅ @{me.username} is running with Command Panel!")
    await idle()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start())
    except Exception as e:
        logger.error(f"Fatal: {e}")
