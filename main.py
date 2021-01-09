import os
import json
import logging
import asyncio
import threading
from telethon import TelegramClient, errors, events
from telethon.events import StopPropagation
from tg_exts.admin_conversation import AdminConversation
from tg_exts.user_conversation import UserConversation
from automators.torrentAutomator import TorrentAutomator
from queue import Queue
from utils.preSetup import setup
from utils.db import DB
from automators.megaAutomator import MegaAutomator
from automators.ytAutomator import YTAutomator
from utils.requests_tracker import Tracker

logger = logging.getLogger()
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
formator = logging.Formatter(
    '[%(asctime)s] - [%(name)s] - %(levelname)s - %(message)s')
consoleHandler.setFormatter(formator)
if not os.path.exists('./logs'):
    os.mkdir('logs')
fileHandler = logging.FileHandler('logs/app.log')
fileHandler.setLevel(logging.DEBUG)
fileHandler.setFormatter(formator)
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

setup()
f = open('config.json', 'r')
config = json.load(f)
API_ID = config.get('API_ID')
API_HASH = config.get('API_HASH')
PHONE_NUMBER = config.get('PHONE_NUMBER')
BOT_TOKEN = config.get('BOT_TOKEN')

client = TelegramClient('./sessionFiles/client', API_ID, API_HASH)
client.parse_mode = 'html'
bot = TelegramClient('./sessionFiles/bot', API_ID, API_HASH)
torrentsQueue = Queue()
megaQueue = Queue()
ytQueue = Queue()
db = DB()


async def startAdminConv(event):
    conversation = AdminConversation(bot, client,
                                     torrentsQueue, megaQueue, ytQueue)
    await conversation.start(event)
    raise StopPropagation


async def startUserConv(event):
    conversation = UserConversation(
        bot, client, torrentsQueue, ytQueue, megaQueue)
    await conversation.start(event)
    raise StopPropagation


def validUser(event):
    users = db.getAllUserIDs()
    return event.message.peer_id.user_id in users


bot.add_event_handler(startAdminConv, events.NewMessage(
    pattern='/start', chats=config.get("ADMINS")))
bot.add_event_handler(startUserConv, events.NewMessage(
    pattern='/start', func=validUser))

rtracker = Tracker()

for i in range(4):
    automator = TorrentAutomator(i+1, bot, client, torrentsQueue, rtracker)
    threading.Thread(target=automator.start,
                     name=f'Torrent Thread {i+1}').start()

for i in range(2):
    megaAutomator = MegaAutomator(i+1, bot, client, megaQueue, rtracker)
    threading.Thread(target=megaAutomator.start,
                     name=f'Mega Thread {i+1}').start()

for i in range(2):
    ytAutomator = YTAutomator(i+1, bot, client, ytQueue, rtracker)
    threading.Thread(target=ytAutomator.start,
                     name=f'Youtube Thread {i+1}').start()


bot.start(bot_token=BOT_TOKEN)
client.start(phone=PHONE_NUMBER)
print(' Bot is up!')
bot.run_until_disconnected()
