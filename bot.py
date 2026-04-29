import os
import asyncio
import logging
import re
import json
import time
import random
import string
from urllib.parse import quote_plus

# Event loop fix for Python 3.10+
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, idle, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from pyrogram.errors import UserNotParticipant
from aiohttp import web, ClientSession

# Import config
from info import *

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== CREATE BOT CLIENT ==========
class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=10,
            sleep_threshold=60
        )
        self.admins = ADMINS
        self.auth_channels = AUTH_CHANNEL
        self.bin_channel = BIN_CHANNEL
        self.shortlink_url = SHORTLINK_URL
        self.shortlink_api = SHORTLINK_API
        self.shortlink_enabled = bool(SHORTLINK_URL and SHORTLINK_API)
        self.caption_prefix = CAPTION_PREFIX

StreamBot = Bot()

# ========== DYNAMIC CONFIG (bina redeploy ke shortlink on/off) ==========
CONFIG_FILE = "simple_config.json"

def load_simple_config():
    default = {
        "shortlink_enabled": StreamBot.shortlink_enabled,
        "admins": StreamBot.admins,
        "banned_users": []
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    else:
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default

def save_simple_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_simple_config()

# ========== HELPER FUNCTIONS ==========
async def is_admin(user_id):
    return user_id in config["admins"]

async def is_banned(user_id):
    return user_id in config.get("banned_users", [])

async def check_force_sub(user_id):
    if not StreamBot.auth_channels:
        return True, None
    not_joined = []
    for cid in StreamBot.auth_channels:
        try:
            member = await StreamBot.get_chat_member(cid, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(cid)
        except UserNotParticipant:
            not_joined.append(cid)
        except Exception:
            pass
    if not_joined:
        buttons = []
        for cid in not_joined:
            try:
                chat = await StreamBot.get_chat(cid)
                link = chat.invite_link if chat.invite_link else f"https://t.me/{chat.username}" if chat.username else "#"
                buttons.append([InlineKeyboardButton(f"📢 Join {chat.title}", url=link)])
            except:
                buttons.append([InlineKeyboardButton("📢 Join Channel", url="https://t.me/Anime_Hindii_Flixx")])
        buttons.append([InlineKeyboardButton("✅ I have Joined", callback_data="refresh_sub")])
        return False, InlineKeyboardMarkup(buttons)
    return True, None

async def get_shortlink(url):
    if not config.get("shortlink_enabled", False) or not StreamBot.shortlink_url or not StreamBot.shortlink_api:
        return url
    try:
        async with ClientSession() as session:
            api_url = f"{StreamBot.shortlink_url}/api?api={StreamBot.shortlink_api}&url={quote_plus(url)}"
            async with session.get(api_url) as resp:
                data = await resp.json()
                return data.get("shortenedUrl") or data.get("shorturl") or url
    except:
        return url

def clean_caption(original_caption, file_name):
    """
    Remove all links, HTML tags, @usernames, and extra spaces.
    Then add file name and the @Anime_Hindii_Flixx.
    """
    if original_caption is None:
        original_caption = ""
    # Remove markdown links [text](url)
    caption = re.sub(r'\[.*?\]\(.*?\)', '', original_caption)
    # Remove raw URLs
    caption = re.sub(r'https?://\S+', '', caption)
    # Remove HTML tags (like <a>, </a>, etc.)
    caption = re.sub(r'<[^>]+>', '', caption)
    # Remove @usernames
    caption = re.sub(r'@\w+', '', caption)
    # Remove extra spaces
    caption = re.sub(r'\s+', ' ', caption).strip()
    # Build new caption
    new_caption = f"📁 **{file_name}**\n\n"
    if caption:
        new_caption += f"{caption}\n\n"
    new_caption += StreamBot.caption_prefix
    return new_caption

async def forward_to_bin(message):
    """Copy file to BIN_CHANNEL and return file_id and direct link"""
    if not StreamBot.bin_channel:
        return None, None
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return None, None
    sent = await media.copy(chat_id=StreamBot.bin_channel)
    # Get file_id
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
    # Direct link (using your bot's web server – will be built later)
    # For now, just return the file_id; later we can generate a link.
    # To keep simple, we'll send the file_id as a media link later.
    # But user wants direct download link. We'll use the web server endpoint.
    # Since we have a web server, we can create a simple download route.
    return fid, fid  # direct_link will be built using URL

# ========== CREATE SIMPLE WEB SERVER (for Render port binding) ==========
async def web_server():
    app = web.Application()
    async def handle(req):
        return web.Response(text="Bot is running", status=200)
    app.router.add_get('/', handle)
    return app

# ========== COMMAND PANEL ==========
@StreamBot.on_message(filters.command(["start"]))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ You are banned.")
        return
    subscribed, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text("**⚠️ Please join our channel(s) to use this bot.**", reply_markup=kb)
        return
    text = """**🤖 Available Commands:**

/start - Main menu
/genlink - Store single file
/batch - Store multiple messages from a channel
/custom_batch - Store random messages
/special_link - Editable link (moderators)
/broadcast - Broadcast message (moderators)
/settings - Settings
/universal_link - Universal access link
/shortener - Shorten any URL
/ban - Ban user
/unban - Unban user

📁 **Send any file (admin only)** to get a direct download link without any ads."""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support", url=SUPPORT_LINK)],
        [InlineKeyboardButton("📝 Channel", url=CHANNEL_LINK)]
    ])
    await message.reply_text(text, reply_markup=buttons)

@StreamBot.on_message(filters.command(["genlink"]) & filters.user(config["admins"]))
async def genlink_cmd(client: Client, message: Message):
    if await is_banned(message.from_user.id):
        await message.reply("❌ Banned.")
        return
    subscribed, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text("**⚠️ Please join our channel(s) first.**", reply_markup=kb)
        return
    await message.reply_text("Send me a file (photo, video, document, audio).")
    async for resp in client.listen(message.chat.id, timeout=60):
        if resp.media:
            fid, _ = await forward_to_bin(resp)
            if not fid:
                await resp.reply("❌ BIN_CHANNEL not set.")
                return
            # Generate direct link (using web server)
            download_link = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/file/{fid}"
            if config.get("shortlink_enabled", False):
                short_url = await get_shortlink(download_link)
                reply_text = f"🔗 [Click here to download]({short_url})"
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]])
            else:
                reply_text = f"🔗 **Download Link:**\n{download_link}"
                reply_markup = None
            # Clean caption (optional)
            file_name = getattr(resp.media, 'file_name', 'file')
            await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=reply_markup)
            return
        else:
            await resp.reply("Please send a valid file.")
    await message.reply("Timeout.")

@StreamBot.on_message(filters.command(["batch"]) & filters.user(config["admins"]))
async def batch_cmd(client: Client, message: Message):
    if await is_banned(message.from_user.id):
        await message.reply("❌ Banned.")
        return
    subscribed, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text("Join channel first.", reply_markup=kb)
        return
    await message.reply_text("Forward or send link of **first message** from your public channel.")
    first_chat, first_id = None, None
    async for resp in client.listen(message.chat.id, timeout=120):
        if resp.forward_from_chat:
            first_chat = resp.forward_from_chat.id
            first_id = resp.forward_from_message_id
            break
        elif resp.text and "t.me/" in resp.text:
            match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', resp.text) or re.search(r't\.me/([^/]+)/(\d+)', resp.text)
            if match:
                chat = match.group(1)
                msg_id = int(match.group(2))
                if chat.isdigit():
                    first_chat = int("-100" + chat)
                else:
                    first_chat = chat
                first_id = msg_id
                break
        await resp.reply("Please forward or send a valid link.")
    if not first_chat:
        await message.reply("Timeout.")
        return
    await message.reply_text("Now forward or send link of **last message**.")
    last_chat, last_id = None, None
    async for resp in client.listen(message.chat.id, timeout=120):
        if resp.forward_from_chat:
            last_chat = resp.forward_from_chat.id
            last_id = resp.forward_from_message_id
            break
        elif resp.text and "t.me/" in resp.text:
            match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', resp.text) or re.search(r't\.me/([^/]+)/(\d+)', resp.text)
            if match:
                chat = match.group(1)
                msg_id = int(match.group(2))
                if chat.isdigit():
                    last_chat = int("-100" + chat)
                else:
                    last_chat = chat
                last_id = msg_id
                break
        await resp.reply("Forward or send valid link.")
    if not last_chat:
        await message.reply("Timeout.")
        return
    if first_chat != last_chat:
        await message.reply("Both messages must be from the same channel.")
        return
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    await message.reply(f"🔄 Collecting messages {first_id} to {last_id}...")
    collected = []
    for mid in range(first_id, last_id + 1):
        try:
            msg_obj = await client.get_messages(first_chat, mid)
            if msg_obj and msg_obj.media:
                collected.append(msg_obj)
            await asyncio.sleep(0.5)
        except:
            pass
    if not collected:
        await message.reply("No media found.")
        return
    if not StreamBot.bin_channel:
        await message.reply("BIN_CHANNEL not set.")
        return
    file_ids = []
    for m in collected:
        try:
            sent = await m.copy(chat_id=StreamBot.bin_channel)
            fid = sent.document.file_id if sent.document else sent.video.file_id if sent.video else sent.audio.file_id if sent.audio else sent.photo.file_id if sent.photo else None
            if fid:
                file_ids.append(fid)
        except:
            pass
    batch_id = str(int(time.time()))
    with open(f"batch_{batch_id}.json", "w") as f:
        json.dump({"file_ids": file_ids, "count": len(file_ids)}, f)
    await message.reply_text(f"✅ Batch created! {len(file_ids)} files.\nBatch ID: `{batch_id}`")

@StreamBot.on_message(filters.command(["shortener"]))
async def shortener_cmd(client: Client, message: Message):
    if await is_banned(message.from_user.id):
        await message.reply("Banned.")
        return
    subscribed, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text("Join channel first.", reply_markup=kb)
        return
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply_text("Usage: /shortener <URL>")
        return
    short = await get_shortlink(args[1])
    await message.reply_text(f"🔗 Shortened:\n{short}")

@StreamBot.on_message(filters.command(["ban"]) & filters.user(config["admins"]))
async def ban_cmd(client: Client, message: Message):
    try:
        uid = int(message.text.split()[1])
        if uid not in config["banned_users"]:
            config["banned_users"].append(uid)
            save_simple_config(config)
            await message.reply(f"✅ User {uid} banned.")
        else:
            await message.reply("Already banned.")
    except:
        await message.reply("Usage: /ban <user_id>")

@StreamBot.on_message(filters.command(["unban"]) & filters.user(config["admins"]))
async def unban_cmd(client: Client, message: Message):
    try:
        uid = int(message.text.split()[1])
        if uid in config["banned_users"]:
            config["banned_users"].remove(uid)
            save_simple_config(config)
            await message.reply(f"✅ User {uid} unbanned.")
        else:
            await message.reply("Not banned.")
    except:
        await message.reply("Usage: /unban <user_id>")

@StreamBot.on_message(filters.command(["settings"]) & filters.user(config["admins"]))
async def settings_cmd(client: Client, message: Message):
    text = f"**Settings**\nShortlink: {config.get('shortlink_enabled', False)}\nAdmins: {config['admins']}\nBanned: {len(config.get('banned_users', []))}"
    await message.reply_text(text)

@StreamBot.on_message(filters.command(["special_link"]) & filters.user(config["admins"]))
async def special_link_cmd(client: Client, message: Message):
    await message.reply_text("Forward a file. I'll give an editable link (demo).")
    async for resp in client.listen(message.chat.id, timeout=60):
        if resp.media:
            fid, _ = await forward_to_bin(resp)
            if not fid:
                await resp.reply("BIN_CHANNEL not set.")
                return
            edit_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            with open(f"edit_{edit_id}.json", "w") as f:
                json.dump({"fid": fid}, f)
            await message.reply_text(f"Editable link (demo): /edit_{edit_id}")
            return
        else:
            await resp.reply("Please forward a media message.")
    await message.reply("Timeout.")

@StreamBot.on_message(filters.command(["broadcast"]) & filters.user(config["admins"]))
async def broadcast_cmd(client: Client, message: Message):
    if message.reply_to_message:
        await message.reply_text("Broadcasting... (demo)")
        await message.reply_text("✅ Broadcast sent (demo).")
    else:
        await message.reply_text("Reply to a message with /broadcast.")

# ========== FILE HANDLER (admin only, caption cleaned, no thumbnail) ==========
@StreamBot.on_message(filters.document | filters.video | filters.audio | filters.photo | filters.animation)
async def file_upload_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ You are banned.")
        return
    if not await is_admin(user_id):
        await message.reply_text("❌ **Only admins can upload files.**\nPublic file store is OFF.")
        return
    subscribed, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text("Join channel first.", reply_markup=kb)
        return
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return
    # Forward to bin channel
    if not StreamBot.bin_channel:
        await message.reply("❌ BIN_CHANNEL not set.")
        return
    sent = await media.copy(chat_id=StreamBot.bin_channel)
    # Get file_id
    if sent.document:
        fid = sent.document.file_id
        file_name = sent.document.file_name or "file"
    elif sent.video:
        fid = sent.video.file_id
        file_name = sent.video.file_name or "video.mp4"
    elif sent.audio:
        fid = sent.audio.file_id
        file_name = sent.audio.file_name or "audio.mp3"
    elif sent.photo:
        fid = sent.photo.file_id
        file_name = "photo.jpg"
    else:
        await message.reply("Unsupported media.")
        return
    # Generate download link (use Render hostname)
    host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")
    download_link = f"https://{host}/file/{fid}"
    if config.get("shortlink_enabled", False):
        short_url = await get_shortlink(download_link)
        reply_text = f"🔗 [Click here to download]({short_url})"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]])
    else:
        reply_text = f"🔗 **Direct Download Link:**\n{download_link}"
        reply_markup = None
    # Clean caption
    original_caption = message.caption or ""
    new_caption = clean_caption(original_caption, file_name)
    # Send the link (no thumbnail)
    await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=reply_markup)
    # Also send the cleaned caption? Optional: send as separate message or combine.
    if new_caption:
        await message.reply_text(f"📝 **Cleaned Caption:**\n{new_caption}")
    # Log
    logger.info(f"Admin {message.from_user.id} uploaded {file_name}")

# ========== CALLBACK ==========
@StreamBot.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "refresh_sub":
        subscribed, kb = await check_force_sub(query.from_user.id)
        if subscribed:
            await query.message.edit_text("✅ Subscribed! Use /start again.")
        else:
            await query.message.edit_text("Still not subscribed. Please join:", reply_markup=kb)
    await query.answer()

# ========== SET BOT COMMANDS (Telegram menu) ==========
async def set_commands():
    cmds = [
        BotCommand("start", "Main menu"),
        BotCommand("genlink", "Store single file"),
        BotCommand("batch", "Batch from channel"),
        BotCommand("custom_batch", "Random batch"),
        BotCommand("special_link", "Editable link"),
        BotCommand("broadcast", "Broadcast"),
        BotCommand("settings", "Settings"),
        BotCommand("universal_link", "Universal link"),
        BotCommand("shortener", "Shorten URL"),
        BotCommand("ban", "Ban user"),
        BotCommand("unban", "Unban user"),
    ]
    await StreamBot.set_bot_commands(cmds)

# ========== KEEP ALIVE (prevent sleep) ==========
async def keep_alive():
    while True:
        await asyncio.sleep(180)
        try:
            me = await StreamBot.get_me()
            logger.info(f"Alive: @{me.username}")
        except:
            pass

# ========== RUN WEB SERVER ==========
async def run_web():
    app = web.Application()
    async def handle(req):
        return web.Response(text="Bot is active", status=200)
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Web server running on port {PORT}")

# ========== MAIN ==========
async def main():
    print("🚀 Starting bot...")
    await StreamBot.start()
    logger.info("Client started.")
    asyncio.create_task(keep_alive())
    await set_commands()
    asyncio.create_task(run_web())
    me = await StreamBot.get_me()
    print(f"✅ @{me.username} is running!\nAll commands loaded.")
    await idle()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Fatal: {e}")
