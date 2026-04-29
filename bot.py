import os, sys, asyncio, logging, re, json, time
from datetime import datetime
from urllib.parse import quote_plus

# Event loop fix for Python 3.10+ ok
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters, Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from pyrogram.errors import FloodWait, UserNotParticipant
import pyrogram.utils
from aiohttp import web, ClientSession

# Import project modules
from info import *
from Script import script
from web import web_server, check_expired_premium
from web.server import StreamBot
from utils import Temp
from web.server.clients import initialize_clients

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== DYNAMIC CONFIG FILE (no redeploy for shortlink, admins, caption) ==========
CONFIG_FILE = "config.json"

def load_config():
    default = {
        "shortlink_enabled": False,
        "shortlink_url": "",
        "shortlink_api": "",
        "admins": [],  # will be filled from ADMINS env later
        "bin_channel": BIN_CHANNEL,
        "log_channel": LOG_CHANNEL,
        "support": SUPPORT,
        "channel": CHANNEL,
        "caption_prefix": "✨ **Shared by:** @Anime_Hindii_Flixx",
        "remove_links": True,
        "force_sub_channels": AUTH_CHANNEL  # from env
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            # merge with default for new keys
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    else:
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()

# If ADMINS env exists, override config admins (so first admin can set others via command)
if ADMINS:
    config["admins"] = ADMINS
    save_config(config)

# ========== PEER ID PATCH (for newer Pyrogram) ==========
def get_peer_type_new(peer_id: int) -> str:
    s = str(peer_id)
    if not s.startswith("-"): return "user"
    elif s.startswith("-100"): return "channel"
    else: return "chat"
pyrogram.utils.get_peer_type = get_peer_type_new
pyrogram.utils.MIN_CHANNEL_ID = -1002822095763

# ========== HELPER FUNCTIONS ==========
async def is_admin(user_id):
    return user_id in config["admins"]

async def check_force_sub(user_id):
    """Check if user is member of all AUTH_CHANNELs. Returns (status, msg, keyboard)"""
    if not config.get("force_sub_channels"):
        return True, None, None
    not_joined = []
    for channel_id in config["force_sub_channels"]:
        try:
            member = await StreamBot.get_chat_member(channel_id, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(channel_id)
        except UserNotParticipant:
            not_joined.append(channel_id)
        except Exception as e:
            logger.error(f"Force sub check error for {channel_id}: {e}")
    if not_joined:
        # Build invite links (if channel has username)
        buttons = []
        for cid in not_joined:
            try:
                chat = await StreamBot.get_chat(cid)
                if chat.username:
                    link = f"https://t.me/{chat.username}"
                else:
                    link = f"https://t.me/{str(cid)[4:]}" if str(cid).startswith("-100") else "#"
                buttons.append([InlineKeyboardButton(f"📢 Join {chat.title}", url=link)])
            except:
                buttons.append([InlineKeyboardButton("📢 Join Channel", url="https://t.me/Anime_Hindii_Flixx")])
        buttons.append([InlineKeyboardButton("✅ I have Joined", callback_data="refresh_sub")])
        return False, "**⚠️ Please join our channel(s) to use this bot.**", InlineKeyboardMarkup(buttons)
    return True, None, None

async def get_shortlink(url):
    if not config["shortlink_enabled"] or not config["shortlink_url"] or not config["shortlink_api"]:
        return url
    try:
        async with ClientSession() as session:
            api_url = f"{config['shortlink_url']}/api?api={config['shortlink_api']}&url={quote_plus(url)}"
            async with session.get(api_url) as resp:
                data = await resp.json()
                return data.get("shortenedUrl") or data.get("shorturl") or url
    except Exception as e:
        logger.error(f"Shortlink error: {e}")
        return url

def fix_caption(original_caption: str, file_name: str) -> str:
    if original_caption is None:
        original_caption = ""
    if config.get("remove_links", True):
        # Remove markdown links [text](url)
        caption = re.sub(r'\[.*?\]\(.*?\)', '', original_caption)
        # Remove raw URLs
        caption = re.sub(r'https?://\S+', '', caption)
        # Remove @usernames
        caption = re.sub(r'@\w+', '', caption)
        # Remove extra spaces
        caption = re.sub(r'\s+', ' ', caption).strip()
    else:
        caption = original_caption
    # Build new caption
    new_caption = f"📁 **{file_name}**\n\n{script.CAPTION}\n\n{config.get('caption_prefix', '')}"
    if caption:
        new_caption += f"\n\n📝 {caption}"
    return new_caption

async def forward_to_bin(message, file_id=None):
    """Forward file to BIN_CHANNEL and return file_id and direct link"""
    bin_id = config.get("bin_channel", BIN_CHANNEL)
    if not bin_id:
        return None, None
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return None, None
    sent = await media.copy(chat_id=bin_id)
    # Get file_id based on type
    if sent.document:
        fid = sent.document.file_id
    elif sent.video:
        fid = sent.video.file_id
    elif sent.audio:
        fid = sent.audio.file_id
    elif sent.photo:
        fid = sent.photo.file_id
    else:
        fid = None
    direct_link = f"{URL}/watch/{fid}" if fid and URL else None
    return fid, direct_link

# ========== BATCH COMMAND ==========
@StreamBot.on_message(filters.command(["batch"]))
async def batch_cmd(client: Client, message: Message):
    # Force sub check
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Only admins can use /batch.")
        return
    
    await message.reply_text("📌 **Batch Mode**\n\nSend me the **link of first message** from a **public channel** (forward that message to me). Then send the **last message link**. I will collect all messages in between and generate a batch link.")
    
    # Wait for first message link
    first_msg = None
    async for msg in client.listen(message.chat.id, timeout=60):
        if msg.text and ("t.me/" in msg.text or "telegram.me/" in msg.text):
            first_msg = msg.text
            break
        else:
            await msg.reply("Please send a valid Telegram message link.")
    if not first_msg:
        await message.reply("Timeout. /batch cancelled.")
        return
    
    await message.reply("Now send the **last message link**.")
    last_msg = None
    async for msg in client.listen(message.chat.id, timeout=60):
        if msg.text and ("t.me/" in msg.text or "telegram.me/" in msg.text):
            last_msg = msg.text
            break
        else:
            await msg.reply("Please send a valid link.")
    if not last_msg:
        await message.reply("Timeout. /batch cancelled.")
        return
    
    # Parse links to get channel id and message ids
    import re
    def extract_ids(link):
        # pattern: https://t.me/c/1234567890/123 or https://t.me/username/123
        match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', link)
        if match:
            chat_id = int("-100" + match.group(1)) if match.group(1).isdigit() else match.group(1)
            msg_id = int(match.group(2))
            return chat_id, msg_id
        # username style
        match2 = re.search(r't\.me/([^/]+)/(\d+)', link)
        if match2:
            username = match2.group(1)
            msg_id = int(match2.group(2))
            return username, msg_id
        return None, None
    
    first_chat, first_id = extract_ids(first_msg)
    last_chat, last_id = extract_ids(last_msg)
    if first_chat != last_chat:
        await message.reply("Both links must be from the same channel.")
        return
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    
    await message.reply(f"🔄 Collecting messages from {first_id} to {last_id}... This may take a while.")
    
    # Collect messages
    collected = []
    for mid in range(first_id, last_id + 1):
        try:
            msg_obj = await client.get_messages(first_chat, mid)
            if msg_obj and msg_obj.media:
                collected.append(msg_obj)
            await asyncio.sleep(0.5)  # avoid flood
        except Exception as e:
            logger.error(f"Failed to get {mid}: {e}")
    
    if not collected:
        await message.reply("No media messages found in range.")
        return
    
    # Store each in BIN_CHANNEL and collect file_ids
    bin_ch = config.get("bin_channel", BIN_CHANNEL)
    if not bin_ch:
        await message.reply("❌ BIN_CHANNEL not set. Set it in environment or config.")
        return
    
    file_ids = []
    for m in collected:
        try:
            sent = await m.copy(chat_id=bin_ch)
            fid = sent.document.file_id if sent.document else sent.video.file_id if sent.video else sent.audio.file_id if sent.audio else sent.photo.file_id if sent.photo else None
            if fid:
                file_ids.append(fid)
        except Exception as e:
            logger.error(f"Copy error: {e}")
    
    # Generate batch link
    batch_id = str(int(time.time()))
    # Store mapping in a simple file (for demo)
    batch_data = {"file_ids": file_ids, "count": len(file_ids)}
    with open(f"batch_{batch_id}.json", "w") as f:
        json.dump(batch_data, f)
    
    batch_link = f"{URL}/batch/{batch_id}"  # you need to implement a web handler for batch
    # For now, just send the list as a message
    await message.reply_text(f"✅ **Batch created!**\nTotal files: {len(file_ids)}\n\n🔗 Batch link (visit to get all files):\n`{batch_link}`\n\n⚠️ This is a demo; full batch download requires web endpoint implementation.")
    # Note: Full batch download endpoint would need to be added in web.py – but user can use /batch to store and then forward one by one.

# ========== FORCE SUB HANDLER (callback) ==========
@StreamBot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    if data == "refresh_sub":
        subscribed, msg, kb = await check_force_sub(query.from_user.id)
        if subscribed:
            await query.message.edit_text("✅ You are now subscribed! You can use the bot.", reply_markup=None)
        else:
            await query.message.edit_text(msg, reply_markup=kb)
    elif data == "help":
        text = """**Commands:**\n/start - Main menu\n/help - This\n/about - Bot info\n/batch - Create batch (admin)\n/settings - Config (admin)\n/set_shortlink - Manage shortlink (admin)"""
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "about":
        me = await client.get_me()
        text = f"**Bot:** {me.first_name}\n**Dev:** @Anime_Hindii_Flixx\n**Shortlink:** {config['shortlink_enabled']}"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "support":
        await query.message.edit_text(f"**Support:** {config['support']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "admin_panel":
        if await is_admin(query.from_user.id):
            admin_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Settings", callback_data="settings")],
                [InlineKeyboardButton("🔗 Shortlink", callback_data="shortlink_menu")],
                [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin_panel")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
            await query.message.edit_text("**Admin Panel**", reply_markup=admin_buttons)
        else:
            await query.answer("Admin only", show_alert=True)
    elif data == "shortlink_menu":
        if await is_admin(query.from_user.id):
            text = f"Shortlink enabled: {config['shortlink_enabled']}\nURL: {config['shortlink_url']}\nAPI: {config['shortlink_api'][:10]}..."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Enable", callback_data="shortlink_on"), InlineKeyboardButton("Disable", callback_data="shortlink_off")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
            ])
            await query.message.edit_text(text, reply_markup=buttons)
    elif data.startswith("shortlink_"):
        if data == "shortlink_on":
            config["shortlink_enabled"] = True
            save_config(config)
            await query.answer("Shortlink enabled", show_alert=True)
        elif data == "shortlink_off":
            config["shortlink_enabled"] = False
            save_config(config)
            await query.answer("Shortlink disabled", show_alert=True)
        # Re-apply same menu
        await callback_handler(client, query)  # refresh
    elif data == "main_menu":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Commands", callback_data="help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
            [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")] if await is_admin(query.from_user.id) else []
        ])
        await query.message.edit_text("**Main Menu**\nChoose an option:", reply_markup=buttons)
    elif data == "settings":
        if await is_admin(query.from_user.id):
            text = f"**Current Settings**\n\nShortlink: {config['shortlink_enabled']}\nAdmins: {config['admins']}\nCaption: {config['caption_prefix'][:40]}..."
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
    else:
        await query.answer()

# ========== FILE HANDLER (with FSUB and shortlink) ==========
@StreamBot.on_message(filters.document | filters.video | filters.audio | filters.photo | filters.animation)
async def file_handler(client: Client, message: Message):
    # Force sub check
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    
    # Process file
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return
    
    try:
        # Forward to bin channel to get file_id and link
        file_id, direct_link = await forward_to_bin(message)
        if not direct_link:
            await message.reply("❌ Failed to generate link. BIN_CHANNEL not set?")
            return
        
        # Generate shortlink if enabled
        if config["shortlink_enabled"]:
            short_url = await get_shortlink(direct_link)
            reply_text = f"🔗 **Your file is ready**\n\n👉 [Click here to get file]({short_url})\n\nYou must visit the above link and press 'Verify' to get your file."
        else:
            reply_text = f"🔗 **Direct Link:**\n{direct_link}"
        
        # Fix caption
        original_caption = message.caption or ""
        file_name = media.file_name if hasattr(media, 'file_name') else "file"
        new_caption = fix_caption(original_caption, file_name)
        
        # Send reply with link (no thumbnail)
        await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]]) if config["shortlink_enabled"] else None)
        
        # Optionally log
        log_ch = config.get("log_channel", LOG_CHANNEL)
        if log_ch:
            await client.send_message(log_ch, f"📁 New file from {message.from_user.mention}\nName: {file_name}\nLink: {direct_link[:50]}...")
    except Exception as e:
        logger.error(f"File handler error: {e}")
        await message.reply("❌ Error processing file. Please try again later.")

# ========== START COMMAND WITH MENU ==========
@StreamBot.on_message(filters.command(["start"]))
async def start_cmd(client: Client, message: Message):
    # Force sub check (only for start? usually yes)
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Commands", callback_data="help")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
        [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")] if await is_admin(message.from_user.id) else []
    ])
    await message.reply_text(
        f"**Welcome {message.from_user.mention}**\n\nSend any file to get a shortlink (if enabled).\nUse /help for commands.",
        reply_markup=buttons
    )

@StreamBot.on_message(filters.command(["help"]))
async def help_cmd(client: Client, message: Message):
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    await message.reply_text("Send /start for menu or any file to get link.")

@StreamBot.on_message(filters.command(["about"]))
async def about_cmd(client: Client, message: Message):
    await message.reply_text("**Advanced File Bot**\nDev: @Anime_Hindii_Flixx\nVersion: 5.0")

# ========== ADMIN TEXT COMMANDS (dynamic) ==========
@StreamBot.on_message(filters.command(["set_shortlink"]) & filters.user(config["admins"]))
async def set_shortlink_text(client: Client, message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) == 2 and args[1].lower() == "on":
        config["shortlink_enabled"] = True
        save_config(config)
        await message.reply("✅ Shortlink enabled.")
    elif len(args) == 2 and args[1].lower() == "off":
        config["shortlink_enabled"] = False
        save_config(config)
        await message.reply("❌ Shortlink disabled.")
    elif len(args) == 3:
        url, api = args[1], args[2]
        config["shortlink_url"] = url
        config["shortlink_api"] = api
        config["shortlink_enabled"] = True
        save_config(config)
        await message.reply(f"✅ Shortlink API set.\nURL: {url}\nAPI: {api[:10]}...")
    else:
        await message.reply("Usage: /set_shortlink on/off\n/set_shortlink <url> <api>")

@StreamBot.on_message(filters.command(["add_admin"]) & filters.user(config["admins"]))
async def add_admin_text(client: Client, message: Message):
    try:
        user_id = int(message.text.split()[1])
        if user_id not in config["admins"]:
            config["admins"].append(user_id)
            save_config(config)
            await message.reply(f"✅ Admin {user_id} added.")
        else:
            await message.reply("Already admin.")
    except:
        await message.reply("Usage: /add_admin <user_id>")

@StreamBot.on_message(filters.command(["remove_admin"]) & filters.user(config["admins"]))
async def remove_admin_text(client: Client, message: Message):
    try:
        user_id = int(message.text.split()[1])
        if user_id in config["admins"] and user_id != config["admins"][0]:  # don't remove first admin
            config["admins"].remove(user_id)
            save_config(config)
            await message.reply(f"✅ Admin {user_id} removed.")
        else:
            await message.reply("Cannot remove that admin.")
    except:
        await message.reply("Usage: /remove_admin <user_id>")

@StreamBot.on_message(filters.command(["set_caption"]) & filters.user(config["admins"]))
async def set_caption_text(client: Client, message: Message):
    new_caption = message.text.replace("/set_caption", "", 1).strip()
    if new_caption:
        config["caption_prefix"] = new_caption
        save_config(config)
        await message.reply(f"✅ Caption prefix updated to:\n{new_caption}")
    else:
        await message.reply("Usage: /set_caption <your text>")

# ========== SET TELEGRAM COMMAND MENU ==========
async def set_telegram_commands():
    commands = [
        BotCommand("start", "Main menu"),
        BotCommand("help", "Help"),
        BotCommand("about", "Bot info"),
        BotCommand("batch", "Batch create (admin)"),
        BotCommand("settings", "View settings (admin)"),
        BotCommand("set_shortlink", "Manage shortlink"),
        BotCommand("add_admin", "Add admin"),
        BotCommand("remove_admin", "Remove admin"),
        BotCommand("set_caption", "Change caption prefix"),
    ]
    await StreamBot.set_bot_commands(commands)

# ========== MAIN START FUNCTION ==========
async def start():
    print("\n🚀 Starting Advanced Bot with Force Sub & Batch...")
    await initialize_clients()
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    # Start keep-alive (simple ping)
    asyncio.create_task(keep_alive())
    # Set commands
    await set_telegram_commands()
    # Start web server
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"✅ @{me.username} is running! Force Sub: {bool(config['force_sub_channels'])}")
    await idle()

async def keep_alive():
    while True:
        await asyncio.sleep(120)
        try:
            me = await StreamBot.get_me()
            logger.info(f"Keep-alive: @{me.username}")
        except:
            pass

if __name__ == "__main__":
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")
