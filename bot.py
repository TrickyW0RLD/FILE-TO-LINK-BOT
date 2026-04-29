# Don't Remove Credit @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot @Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle
import logging
import logging.config

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import LOG_CHANNEL, CLONE_MODE, PORT
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from datetime import date, datetime 
import pytz
from aiohttp import web
from Anime_Hindii_Flixx.server import web_server

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

import asyncio
from pyrogram import idle
from plugins.clone import restart_bots
from Anime_Hindii_Flixx.bot import StreamBot
from Anime_Hindii_Flixx.utils.keepalive import ping_server
from Anime_Hindii_Flixx.bot.clients import initialize_clients

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

ppath = "plugins/*.py"
files = glob.glob(ppath)
StreamBot.start()
loop = asyncio.get_event_loop()

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

async def start():
    print('\n')
    print('Initalizing Anime_Hindii_Flixx Bot')
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    await initialize_clients()
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
            print("Anime_Hindii_Flixx Imported => " + plugin_name)
    # Heroku wala ping_server hata diya (Render ke liye zaroori nahi)
    me = await StreamBot.get_me()
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    app = web.AppRunner(await web_server())
    await StreamBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    if CLONE_MODE == True:
        await restart_bots()
    print("Bot Started Powered By @Anime_Hindii_Flixx")
    await idle()

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx

if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')

# Don't Remove Credit Tg - @Anime_Hindii_Flixx
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Anime_Hindii_Flixx
# Ask Doubt on telegram @Anime_Hindii_Flixx
