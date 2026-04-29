import os, sys, asyncio, logging, re, json, time, random, string
from datetime import datetime
from urllib.parse import quote_plus

# Event loop fix for Python 3.10+
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from pyrogram.errors import UserNotParticipant
import pyrogram.utils
from aiohttp import web, ClientSession

from info import *
from Script import script
from web import web_server
from web.server import StreamBot
from utils import Temp
from web.server.clients import initialize_clients

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== DYNAMIC CONFIG ==========
CONFIG_FILE = "config.json"

def load_config():
    default = {
        "shortlink_enabled": IS_SHORTLINK,
        "shortlink_url": SHORTLINK_URL,
        "shortlink_api": SHORTLINK_API,
        "admins": ADMINS,
        "bin_channel": BIN_CHANNEL,
        "log_channel": LOG_CHANNEL,
        "support": SUPPORT,
        "channel": CHANNEL,
        "caption_prefix": "✨ **Shared by:** @Anime_Hindii_Flixx",
        "remove_links": True,
        "force_sub_channels": AUTH_CHANNEL,
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

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()

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

async def is_banned(user_id):
    return user_id in config.get("banned_users", [])

async def check_force_sub(user_id):
    if not config.get("force_sub_channels"):
        return True, None, None
    not_joined = []
    for cid in config["force_sub_channels"]:
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
                link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/{str(cid)[4:]}"
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
    except:
        return url

def fix_caption(original_caption, file_name):
    if original_caption is None:
        original_caption = ""
    if config.get("remove_links", True):
        caption = re.sub(r'\[.*?\]\(.*?\)', '', original_caption)
        caption = re.sub(r'https?://\S+', '', caption)
        caption = re.sub(r'@\w+', '', caption)
        caption = re.sub(r'\s+', ' ', caption).strip()
    else:
        caption = original_caption
    new_caption = f"📁 **{file_name}**\n\n{script.CAPTION}\n\n{config.get('caption_prefix', '')}"
    if caption:
        new_caption += f"\n\n📝 {caption}"
    return new_caption

async def forward_to_bin(message):
    bin_id = config.get("bin_channel", BIN_CHANNEL)
    if not bin_id:
        return None, None
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return None, None
    sent = await media.copy(chat_id=bin_id)
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

# ========== COMMAND HANDLERS ==========

@StreamBot.on_message(filters.command(["start"]))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ You are banned from using this bot.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    text = """**🤖 Available Commands:**

/start - Check I am alive
/genlink - Store a single message or file
/batch - Store multiple messages from a channel
/custom_batch - Store multiple random messages
/special_link - Store a message and get editable link (moderators only)
/broadcast - Broadcast a message to users (moderators only)
/settings - Customize your settings
/universal_link - Store multiple messages accessible from anywhere
/shortener - Shorten any shareable link
/ban - Ban a user (moderators only)
/unban - Unban a user (moderators only)

Send any file to get a download link (admin only)."""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support", url=config['support'])],
        [InlineKeyboardButton("📝 Channel", url=config['channel'])]
    ])
    await message.reply_text(text, reply_markup=buttons)

@StreamBot.on_message(filters.command(["genlink"]) & filters.user(config["admins"]))
async def genlink_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ Banned.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    await message.reply_text("Send me any file (photo, video, document, audio).")
    async for resp in client.listen(message.chat.id, timeout=60):
        if resp.media:
            fid, direct_link = await forward_to_bin(resp)
            if not direct_link:
                await resp.reply("❌ BIN_CHANNEL not set.")
                return
            if config["shortlink_enabled"]:
                short_url = await get_shortlink(direct_link)
                reply_text = f"🔗 [Click here to get file]({short_url})"
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]])
            else:
                reply_text = f"🔗 Direct Link:\n{direct_link}"
                reply_markup = None
            await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=reply_markup)
            return
        else:
            await resp.reply("Please send a valid file.")
    await message.reply("Timeout. /genlink cancelled.")

@StreamBot.on_message(filters.command(["batch"]) & filters.user(config["admins"]))
async def batch_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ Banned.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    await message.reply_text(
        "📌 **Batch Mode**\n\n"
        "**Forward** me the **first message** from your batch channel (with forward tag)\n"
        "– OR –\n"
        "Send me the **first message link**."
    )
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
    await message.reply_text("Now **forward** or **send link** of the **last message**.")
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
        await resp.reply("Please forward or send a valid link.")
    if not last_chat:
        await message.reply("Timeout.")
        return
    if first_chat != last_chat:
        await message.reply("Both messages must be from the same channel.")
        return
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    await message.reply(f"🔄 Collecting {first_id} → {last_id} ...")
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
    bin_ch = config.get("bin_channel", BIN_CHANNEL)
    if not bin_ch:
        await message.reply("BIN_CHANNEL not set.")
        return
    file_ids = []
    for m in collected:
        try:
            sent = await m.copy(chat_id=bin_ch)
            fid = sent.document.file_id if sent.document else sent.video.file_id if sent.video else sent.audio.file_id if sent.audio else sent.photo.file_id if sent.photo else None
            if fid:
                file_ids.append(fid)
        except:
            pass
    batch_id = str(int(time.time()))
    with open(f"batch_{batch_id}.json", "w") as f:
        json.dump({"file_ids": file_ids, "count": len(file_ids)}, f)
    await message.reply_text(f"✅ Batch created! {len(file_ids)} files. Batch ID: `{batch_id}`")

@StreamBot.on_message(filters.command(["custom_batch"]) & filters.user(config["admins"]))
async def custom_batch_cmd(client: Client, message: Message):
    await message.reply_text("Send me multiple message links (one per line). When done, send /done.")
    links = []
    while True:
        resp = await client.listen(message.chat.id, timeout=60)
        if resp.text and resp.text == "/done":
            break
        elif resp.text and "t.me/" in resp.text:
            links.append(resp.text)
            await resp.reply("✅ Added. Send more or /done")
        else:
            await resp.reply("Send a valid Telegram message link.")
    if not links:
        await message.reply("No links provided.")
        return
    collected = []
    for link in links:
        match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', link) or re.search(r't\.me/([^/]+)/(\d+)', link)
        if match:
            chat = match.group(1)
            msg_id = int(match.group(2))
            if chat.isdigit():
                chat_id = int("-100" + chat)
            else:
                chat_id = chat
            try:
                msg_obj = await client.get_messages(chat_id, msg_id)
                if msg_obj and msg_obj.media:
                    collected.append(msg_obj)
            except:
                pass
    if not collected:
        await message.reply("No media found.")
        return
    bin_ch = config.get("bin_channel", BIN_CHANNEL)
    if not bin_ch:
        await message.reply("BIN_CHANNEL not set.")
        return
    file_ids = []
    for m in collected:
        try:
            sent = await m.copy(chat_id=bin_ch)
            fid = sent.document.file_id if sent.document else sent.video.file_id if sent.video else sent.audio.file_id if sent.audio else sent.photo.file_id if sent.photo else None
            if fid:
                file_ids.append(fid)
        except:
            pass
    batch_id = str(int(time.time()))
    with open(f"custom_batch_{batch_id}.json", "w") as f:
        json.dump({"file_ids": file_ids, "count": len(file_ids)}, f)
    await message.reply_text(f"✅ Custom batch created! {len(file_ids)} files. Batch ID: `{batch_id}`")

@StreamBot.on_message(filters.command(["special_link"]) & filters.user(config["admins"]))
async def special_link_cmd(client: Client, message: Message):
    await message.reply_text("Forward me the file/message. I will give you an editable link.")
    async for resp in client.listen(message.chat.id, timeout=60):
        if resp.media:
            fid, direct_link = await forward_to_bin(resp)
            if not direct_link:
                await resp.reply("BIN_CHANNEL not set.")
                return
            edit_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            with open(f"edit_{edit_id}.json", "w") as f:
                json.dump({"fid": fid, "original_link": direct_link}, f)
            editable_link = f"{URL}/edit/{edit_id}"
            await message.reply_text(f"🔗 Editable link (moderators only):\n{editable_link}\n\nYou can change the caption etc. later.")
            return
        else:
            await resp.reply("Please send a file.")
    await message.reply("Timeout.")

@StreamBot.on_message(filters.command(["broadcast"]) & filters.user(config["admins"]))
async def broadcast_cmd(client: Client, message: Message):
    if message.reply_to_message:
        await message.reply_text("Broadcasting... (demo) Implement DB for full feature.")
        await message.reply_text("✅ Broadcast sent (demo).")
    else:
        await message.reply_text("Reply to a message with /broadcast.")

@StreamBot.on_message(filters.command(["settings"]))
async def settings_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("You are banned.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    if await is_admin(user_id):
        text = f"**Admin Settings**\n\nShortlink: {config['shortlink_enabled']}\nAdmins: {config['admins']}"
        await message.reply_text(text)
    else:
        await message.reply_text("User settings: Not implemented yet.")

@StreamBot.on_message(filters.command(["universal_link"]) & filters.user(config["admins"]))
async def universal_link_cmd(client: Client, message: Message):
    await message.reply_text("Send me multiple message links (one per line). Final /done.")
    links = []
    while True:
        resp = await client.listen(message.chat.id, timeout=60)
        if resp.text and resp.text == "/done":
            break
        elif resp.text and "t.me/" in resp.text:
            links.append(resp.text)
            await resp.reply("Added.")
        else:
            await resp.reply("Send a valid link.")
    if not links:
        await message.reply("No links.")
        return
    collected = []
    for link in links:
        match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', link) or re.search(r't\.me/([^/]+)/(\d+)', link)
        if match:
            chat = match.group(1)
            msg_id = int(match.group(2))
            if chat.isdigit():
                chat_id = int("-100" + chat)
            else:
                chat_id = chat
            try:
                msg_obj = await client.get_messages(chat_id, msg_id)
                if msg_obj and msg_obj.media:
                    collected.append(msg_obj)
            except:
                pass
    if not collected:
        await message.reply("No media.")
        return
    bin_ch = config.get("bin_channel", BIN_CHANNEL)
    if not bin_ch:
        await message.reply("BIN_CHANNEL not set.")
        return
    file_ids = []
    for m in collected:
        try:
            sent = await m.copy(chat_id=bin_ch)
            fid = sent.document.file_id if sent.document else sent.video.file_id if sent.video else sent.audio.file_id if sent.audio else sent.photo.file_id if sent.photo else None
            if fid:
                file_ids.append(fid)
        except:
            pass
    univ_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    with open(f"universal_{univ_id}.json", "w") as f:
        json.dump({"file_ids": file_ids, "count": len(file_ids)}, f)
    universal_link = f"{URL}/universal/{univ_id}"
    await message.reply_text(f"✅ Universal link created:\n{universal_link}\n(accessible from anywhere)")

@StreamBot.on_message(filters.command(["shortener"]))
async def shortener_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("You are banned.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply_text("Usage: /shortener <URL>")
        return
    url = args[1]
    short_url = await get_shortlink(url)
    await message.reply_text(f"🔗 Shortened link:\n{short_url}")

@StreamBot.on_message(filters.command(["ban"]) & filters.user(config["admins"]))
async def ban_cmd(client: Client, message: Message):
    try:
        user_id = int(message.text.split()[1])
        if user_id not in config["banned_users"]:
            config["banned_users"].append(user_id)
            save_config(config)
            await message.reply(f"✅ User {user_id} banned.")
        else:
            await message.reply("Already banned.")
    except:
        await message.reply("Usage: /ban <user_id>")

@StreamBot.on_message(filters.command(["unban"]) & filters.user(config["admins"]))
async def unban_cmd(client: Client, message: Message):
    try:
        user_id = int(message.text.split()[1])
        if user_id in config["banned_users"]:
            config["banned_users"].remove(user_id)
            save_config(config)
            await message.reply(f"✅ User {user_id} unbanned.")
        else:
            await message.reply("Not banned.")
    except:
        await message.reply("Usage: /unban <user_id>")

# ========== FILE HANDLER (admin only) ==========
@StreamBot.on_message(filters.document | filters.video | filters.audio | filters.photo | filters.animation)
async def file_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.reply("❌ You are banned.")
        return
    if not await is_admin(user_id):
        await message.reply_text("❌ **Only admins can upload files.**\nPublic file store is OFF.")
        return
    subscribed, msg, kb = await check_force_sub(user_id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    media = getattr(message, message.media.value) if message.media else None
    if not media:
        return
    try:
        fid, direct_link = await forward_to_bin(message)
        if not direct_link:
            await message.reply("❌ BIN_CHANNEL not set.")
            return
        if config["shortlink_enabled"]:
            short_url = await get_shortlink(direct_link)
            reply_text = f"🔗 [Click here to get file]({short_url})"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]])
        else:
            reply_text = f"🔗 Direct Link:\n{direct_link}"
            reply_markup = None
        fname = media.file_name if hasattr(media, 'file_name') else "file"
        await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=reply_markup)
        if config.get("log_channel"):
            await client.send_message(config["log_channel"], f"📁 Admin {message.from_user.mention} uploaded: {fname}")
    except Exception as e:
        logger.error(e)
        await message.reply("Error processing file.")

# ========== CALLBACK QUERY HANDLER ==========
@StreamBot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    if data == "refresh_sub":
        subscribed, msg, kb = await check_force_sub(query.from_user.id)
        if subscribed:
            await query.message.edit_text("✅ You are now subscribed! Use /start.")
        else:
            await query.message.edit_text(msg, reply_markup=kb)
    await query.answer()

# ========== SET TELEGRAM COMMANDS ==========
async def set_telegram_commands():
    cmds = [
        BotCommand("start", "Main menu"),
        BotCommand("genlink", "Store single file"),
        BotCommand("batch", "Batch from channel"),
        BotCommand("custom_batch", "Random messages batch"),
        BotCommand("special_link", "Editable link (moderators)"),
        BotCommand("broadcast", "Broadcast to users"),
        BotCommand("settings", "Settings"),
        BotCommand("universal_link", "Universal access link"),
        BotCommand("shortener", "Shorten any link"),
        BotCommand("ban", "Ban user"),
        BotCommand("unban", "Unban user"),
    ]
    await StreamBot.set_bot_commands(cmds)

# ========== KEEP ALIVE ==========
async def keep_alive():
    while True:
        await asyncio.sleep(120)
        try:
            me = await StreamBot.get_me()
            logger.info(f"Alive: @{me.username}")
        except:
            pass

# ========== MAIN START (with client start fix) ==========
async def start():
    print("🚀 Starting bot...")
    # IMPORTANT: Start the client first
    await StreamBot.start()
    logger.info("Client started successfully.")
    
    # Initialize additional clients (if any)
    await initialize_clients()
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())
    
    # Get bot info
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    
    # Set bot commands for Telegram menu
    await set_telegram_commands()
    
    # Start web server
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print(f"✅ @{me.username} is running!\nAll commands loaded.")
    await idle()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start())
    except Exception as e:
        logger.error(f"Fatal: {e}")
