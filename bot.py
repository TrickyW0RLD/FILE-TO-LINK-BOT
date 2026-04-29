import os, sys, asyncio, logging, re, json, time
from datetime import datetime
from urllib.parse import quote_plus

# Event loop fix
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import idle, filters, Client, enums
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

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== DYNAMIC CONFIG (no redeploy) ==========
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
        "force_sub_channels": AUTH_CHANNEL
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

# ========== PEER ID PATCH ==========
def get_peer_type_new(peer_id: int) -> str:
    s = str(peer_id)
    if not s.startswith("-"): return "user"
    elif s.startswith("-100"): return "channel"
    else: return "chat"
pyrogram.utils.get_peer_type = get_peer_type_new
pyrogram.utils.MIN_CHANNEL_ID = -1002822095763

# ========== HELPERS ==========
async def is_admin(user_id):
    return user_id in config["admins"]

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

# ========== BATCH COMMAND ==========
@StreamBot.on_message(filters.command(["batch"]) & filters.user(config["admins"]))
async def batch_cmd(client: Client, message: Message):
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    await message.reply_text("Send me the **first message link** (from a public channel).")
    first = None
    async for m in client.listen(message.chat.id, timeout=60):
        if m.text and ("t.me/" in m.text):
            first = m.text
            break
        else:
            await m.reply("Please send a valid Telegram message link.")
    if not first:
        await message.reply("Timeout.")
        return
    await message.reply_text("Now send the **last message link**.")
    last = None
    async for m in client.listen(message.chat.id, timeout=60):
        if m.text and ("t.me/" in m.text):
            last = m.text
            break
        else:
            await m.reply("Send a valid link.")
    if not last:
        await message.reply("Timeout.")
        return
    # Extract IDs
    def extract(link):
        match = re.search(r't\.me/(?:c/)?(\d+)/(\d+)', link) or re.search(r't\.me/([^/]+)/(\d+)', link)
        if match:
            chat = match.group(1)
            msg_id = int(match.group(2))
            if chat.isdigit():
                chat_id = int("-100" + chat)
            else:
                chat_id = chat
            return chat_id, msg_id
        return None, None
    first_chat, first_id = extract(first)
    last_chat, last_id = extract(last)
    if first_chat != last_chat or not first_chat:
        await message.reply("Both links must be from the same public channel.")
        return
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    await message.reply(f"Collecting {first_id} to {last_id} ...")
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
    await message.reply_text(f"✅ Batch created! {len(file_ids)} files.\nBatch ID: `{batch_id}` (admin use)")

# ========== FILE HANDLER (only admin upload) ==========
@StreamBot.on_message(filters.document | filters.video | filters.audio | filters.photo | filters.animation)
async def file_handler(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ **Only admins can upload files.**\nPublic file store is OFF.")
        return
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
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
            reply_text = f"🔗 [Click here to get file]({short_url})\n\nVisit the link and press Verify."
        else:
            reply_text = f"🔗 Direct Link:\n{direct_link}"
        # caption fix
        orig_cap = message.caption or ""
        fname = media.file_name if hasattr(media, 'file_name') else "file"
        # No thumbnail: we don't send any thumbnail
        await message.reply_text(reply_text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=short_url)]]) if config["shortlink_enabled"] else None)
        # log
        if config.get("log_channel"):
            await client.send_message(config["log_channel"], f"📁 Admin {message.from_user.mention} uploaded: {fname}")
    except Exception as e:
        logger.error(e)
        await message.reply("Error processing file.")

# ========== START / COMMANDS ==========
@StreamBot.on_message(filters.command(["start"]))
async def start_cmd(client: Client, message: Message):
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Commands", callback_data="help")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
        [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")] if await is_admin(message.from_user.id) else []
    ])
    await message.reply_text(f"**Welcome {message.from_user.mention}**\n\nSend any file (admin only) to get link.", reply_markup=buttons)

@StreamBot.on_message(filters.command(["help"]))
async def help_cmd(client: Client, message: Message):
    subscribed, msg, kb = await check_force_sub(message.from_user.id)
    if not subscribed:
        await message.reply_text(msg, reply_markup=kb)
        return
    await message.reply_text("Use /start for menu.\nAdmin commands: /batch, /set_shortlink, /add_admin, /settings")

@StreamBot.on_message(filters.command(["about"]))
async def about_cmd(client: Client, message: Message):
    await message.reply_text("**Advanced File Bot**\nDev: @Anime_Hindii_Flixx\nVersion: 5.0")

# ========== ADMIN TEXT COMMANDS ==========
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
        await message.reply("Usage:\n/set_shortlink on/off\n/set_shortlink <url> <api>")

@StreamBot.on_message(filters.command(["add_admin"]) & filters.user(config["admins"]))
async def add_admin_text(client: Client, message: Message):
    try:
        uid = int(message.text.split()[1])
        if uid not in config["admins"]:
            config["admins"].append(uid)
            save_config(config)
            await message.reply(f"✅ Admin {uid} added.")
        else:
            await message.reply("Already admin.")
    except:
        await message.reply("Usage: /add_admin <user_id>")

@StreamBot.on_message(filters.command(["remove_admin"]) & filters.user(config["admins"]))
async def remove_admin_text(client: Client, message: Message):
    try:
        uid = int(message.text.split()[1])
        if uid in config["admins"] and uid != config["admins"][0]:
            config["admins"].remove(uid)
            save_config(config)
            await message.reply(f"✅ Admin {uid} removed.")
        else:
            await message.reply("Cannot remove that admin.")
    except:
        await message.reply("Usage: /remove_admin <user_id>")

@StreamBot.on_message(filters.command(["settings"]) & filters.user(config["admins"]))
async def settings_text(client: Client, message: Message):
    await message.reply(f"Shortlink: {config['shortlink_enabled']}\nAdmins: {config['admins']}\nCaption: {config['caption_prefix'][:30]}...")

# ========== CALLBACK HANDLERS ==========
@StreamBot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    if data == "refresh_sub":
        subscribed, msg, kb = await check_force_sub(query.from_user.id)
        if subscribed:
            await query.message.edit_text("✅ You are now subscribed! Use /start.")
        else:
            await query.message.edit_text(msg, reply_markup=kb)
    elif data == "help":
        await query.message.edit_text("Use /start for menu.\nAdmin: /batch, /set_shortlink", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "about":
        me = await client.get_me()
        await query.message.edit_text(f"**Bot:** {me.first_name}\nDev: @Anime_Hindii_Flixx", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "support":
        await query.message.edit_text(f"**Support:** {config['support']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif data == "admin_panel":
        if await is_admin(query.from_user.id):
            await query.message.edit_text("Admin panel:\n/set_shortlink\n/add_admin\n/remove_admin\n/settings", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        else:
            await query.answer("Admin only", show_alert=True)
    elif data == "main_menu":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Commands", callback_data="help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📢 Support", callback_data="support")],
            [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")] if await is_admin(query.from_user.id) else []
        ])
        await query.message.edit_text("**Main Menu**", reply_markup=buttons)
    await query.answer()

# ========== SET TELEGRAM COMMANDS ==========
async def set_telegram_commands():
    cmds = [
        BotCommand("start", "Main menu"),
        BotCommand("help", "Help"),
        BotCommand("about", "Bot info"),
        BotCommand("batch", "Batch create (admin)"),
        BotCommand("set_shortlink", "Manage shortlink (admin)"),
        BotCommand("add_admin", "Add admin (admin)"),
        BotCommand("remove_admin", "Remove admin (admin)"),
        BotCommand("settings", "View settings (admin)"),
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

# ========== MAIN ==========
async def start():
    print("🚀 Starting bot...")
    await initialize_clients()
    asyncio.create_task(keep_alive())
    me = await StreamBot.get_me()
    Temp.BOT = StreamBot
    Temp.ME = me.id
    await set_telegram_commands()
    # web server
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"✅ @{me.username} is running!")
    await idle()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start())
    except Exception as e:
        logger.error(f"Fatal: {e}")
