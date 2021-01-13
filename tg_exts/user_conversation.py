
from utils.Utils import Utils
from utils.db import DB
from telethon import events
import asyncio
from telethon.tl.custom import Button
from queue import Queue
from models.ytube import getAllFormats
from models.seedr import Seedr


class UserConversation:
    def __init__(self, bot, client,
                 torrentsQueue: Queue, ytQueue, megaQueue):
        self.bot = bot
        self.client = client
        self.ytQueue = ytQueue
        self.megaQueue = megaQueue
        self.torrentsQueue = torrentsQueue
        self.utils = Utils()
        self.db = DB()

    async def start(self, event):
        async with self.bot.conversation(event.peer_id, timeout=-1) as conv:
            self.conv = conv
            await self.conv.send_message(
                'Welcome to the bot!')
            await self.home()

    async def getEntity(self, channelLink):
        try:
            en = await self.client.get_entity(channelLink)
            return True, en
        except:
            return False, None

    async def home(self):
        try:
            btns = [
                [
                    self.utils.createButton('Send Torrents'),
                    self.utils.createButton('Send from Mega.nz'),
                    self.utils.createButton('Send from Youtube')
                ],
                [
                    self.utils.createButton('Exit')
                ]
            ]
            q = await self.conv.send_message('Main Menu', buttons=btns)
            checkList = ['Send Torrents',
                         'Exit', 'Send from Mega.nz', 'Send from Youtube']
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton(checkList)))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Send Torrents':
                await self.sendTorrent()
                return
            if resp == 'Send from Mega.nz':
                await self.getMega()
                return
            if resp == 'Send from Youtube':
                await self.getYT()
                return
            if resp == 'Exit':
                await self.exit()

        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.home()

    async def sendTorrent(self):
        try:
            btns = [
                [
                    self.utils.createButton('Torrent File'),
                    self.utils.createButton('Magnet Link')
                ],
                [
                    self.utils.createButton('Delete torrent from seedr')
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Please select the torrent download method!', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(
                func=self.utils.checkButton(['Torrent File',
                                             'Magnet Link', 'Delete torrent from seedr', 'Back'])))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Torrent File':
                await self.torrentFileUpload()
                return
            if resp == 'Magnet Link':
                await self.magnetLinkUpload()
                return
            if resp == 'Delete torrent from seedr':
                await self.deleteRunningTorrent()
                return
            if resp == 'Back':
                await self.home()
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.sendTorrent()

    async def deleteRunningTorrent(self):
        try:
            btns = [
                [
                    self.utils.createButton('Cancel')
                ]
            ]
            q = await self.conv.send_message('Enter torrent ID?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage)
            resp = r.message.message
            if resp == 'Cancel':
                await self.home()
                return
            torrentID = resp
            torrent = Seedr(self.bot, self.client)
            await torrent.deleteTorrent(torrentID)
            btns = [
                [
                    self.utils.createButton('Add New Torrent'),
                    self.utils.createButton('Remove Another Torrent')
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Torrent deleted!', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton([
                'Back', 'Add New Torrent', 'Remove Another Torrent'
            ])))
            resp = r.message.message
            await self.utils.rm([q, r])
            if resp == 'Back' or '/start':
                await self.home()
                return
            if resp == 'Add New Torrent':
                await self.sendTorrent()
                return
            if resp == 'Remove Another Torrent':
                await self.deleteRunningTorrent()
                return
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.deleteRunningTorrent()

    async def exit(self):
        self.conv.cancel()

    async def convTimeout(self):
        await self.conv.send_message('Response Timeout!')
        self.conv.cancel()

    async def torrentFileUpload(self):
        try:
            btns = [
                [
                    self.utils.createButton('Cancel')
                ]
            ]
            q = await self.conv.send_message('Please send the target .torrent file?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkFileOrButton(['Cancel'])))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Cancel':
                await self.home()
                return
            uploadedTorrentFile = await r.download_media('./Downloads')
            channelLink = await self.selectChannel()
            job = {
                'userID': self.conv.chat_id,
                'targetChannelLink': channelLink,
                'downloadType': 'file',
                'fileLocation': uploadedTorrentFile
            }
            self.torrentsQueue.put(job)
            await self.askAgainForTorrent()
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.torrentFileUpload()

    async def magnetLinkUpload(self):
        try:
            btns = [
                [
                    self.utils.createButton('Cancel')
                ]
            ]
            q = await self.conv.send_message('Send the target torrent link?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage)
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Cancel':
                await self.home()
                return
            self.torrentFile = None
            self.magnetLink = resp
            channelLink = await self.selectChannel()
            job = {
                'userID': self.conv.chat_id,
                'targetChannelLink': channelLink,
                'downloadType': 'magnet',
                'magnet': self.magnetLink
            }
            self.torrentsQueue.put(job)
            await self.askAgainForTorrent()
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.magnetLinkUpload()

    async def selectChannel(self):
        try:
            channelsList = await self.db.getChannelsList()
            if not channelsList:
                btns = [
                    [
                        self.utils.createButton('Add Channel')
                    ],
                    [
                        self.utils.createButton('Back')
                    ]
                ]
                q = await self.conv.send_message('There are no channels in the database! Add some channels first!',
                                                 buttons=btns)
                r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton(['Back'
                                                                                              ])))
                await self.utils.rm([q, r])
                resp = r.message.message
                if resp == 'Back' or resp == '/start':
                    await self.home()
                    return
            btns = []
            temp = []
            if len(channelsList) == 1:
                btns = [
                    [
                        self.utils.createDataButton(
                            channelsList[0]['title'], f'{channelsList[0]["id"]}')
                    ]
                ]
            else:
                for channel in channelsList:
                    btn = self.utils.createDataButton(
                        channel['title'], f'{channel["id"]}')
                    temp.append(btn)
                    if channelsList.index(channel) % 2 == 0:
                        continue
                    btns.append(temp)
                    temp = []
            dataList = []
            for ch in channelsList:
                dataList.append(str(ch["id"]))
            q = await self.conv.send_message('Please select a channel from the list?', buttons=btns)
            r = await self.conv.wait_event(events.CallbackQuery(func=self.utils.checkDataButton(dataList)))
            await self.utils.rm([q, r])
            channelID = int(r.data.decode())
            channelLink = await self.db.getChannelLinkByID(channelID)
            return channelLink
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.selectChannel()

    async def askAgainForTorrent(self):
        try:
            btns = [
                [
                    self.utils.createButton('Add Another Torrent'),
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Torrent added to the queue!', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton(['Add Another Torrent', 'Back'])))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Add Another Torrent':
                await self.sendTorrent()
                return
            if resp == 'Back' or resp == '/start':
                await self.home()
                return
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.askAgainForTorrent()

    async def getMega(self):
        try:
            btns = [
                [self.utils.createButton('Cancel')]
            ]
            q = await self.conv.send_message('Enter the mega link?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage)
            await self.utils.rm([q, r])
            if r.message.message == 'Cancel':
                await self.home()
                return
            megaLink = r.message.message
            channelLink = await self.selectChannel()
            job = {
                'megaLink': megaLink,
                'channelLink': channelLink,
                'userID': self.conv.chat_id
            }
            self.megaQueue.put(job)
            btns = [
                [
                    self.utils.createButton('Add Another Mega.nz')
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Job added to bot queue!', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton([
                'Add Another Mega.nz', 'Back'
            ])))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Back' or resp == '/start':
                await self.home()
                return
            if resp == 'Add Another Mega.nz':
                await self.getMega()
                return

        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.getMega()

    async def getYT(self):
        try:
            btns = [
                [
                    self.utils.createButton('Playlist Link'),
                    self.utils.createButton('Video Link')
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Select Link Type?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton([
                'Playlist Link', 'Video Link', 'Back'
            ])))
            resp = r.message.message
            if resp == 'Back' or resp == '/start':
                await self.home()
                return
            if resp == 'Playlist Link':
                linkType = 'playlist'
            if resp == 'Video Link':
                linkType = 'video'
            q = await self.conv.send_message(f'Enter youtube {linkType} link?')
            r = await self.conv.wait_event(events.NewMessage)
            link = r.message.message
            await self.utils.rm([q, r])
            if linkType == 'playlist':
                channel = await self.selectChannel()
                job = {
                    'URL': link,
                    'channel': channel,
                    'userID': self.conv.chat_id,
                    'linkType': linkType
                }
                self.ytQueue.put(job)
                await self.utils.rm([q])
                btns = [
                    [
                        self.utils.createButton('Back')
                    ]
                ]
                await self.conv.send_message('Playlist job added to the queue!', buttons=btns)
                await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton(['Back'])))
                await self.home()
            q = await self.conv.send_message('Please while fetching available video formats ..')
            formats = getAllFormats(link)
            filteredFormats = self.utils.filterFormats(formats)
            btns = []
            tmp = []
            for b in filteredFormats:
                btn = self.utils.createButton(b)
                tmp.append(btn)
                if len(tmp) == 2 or len(filteredFormats)-1 == filteredFormats.index(b):
                    btns.append(tmp)
                    tmp = []
                    continue
            await self.utils.rm([q])
            q = await self.conv.send_message('Choose a format?', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton(filteredFormats)))
            selectedResolution = r.message.message
            await self.utils.rm([q, r])
            channel = await self.selectChannel()
            job = {
                'URL': link,
                'channel': channel,
                'resolution': selectedResolution,
                'userID': self.conv.chat_id,
                'linkType': linkType
            }
            self.ytQueue.put(job)
            btn1 = 'Add Another Youtube Link'
            btns = [
                [
                    self.utils.createButton(btn1)
                ],
                [
                    self.utils.createButton('Back')
                ]
            ]
            q = await self.conv.send_message('Job added!', buttons=btns)
            r = await self.conv.wait_event(events.NewMessage(func=self.utils.checkButton([
                'Back', btn1
            ])))
            await self.utils.rm([q, r])
            resp = r.message.message
            if resp == 'Back' or resp == '/start':
                await self.home()
                return
            if resp == btn1:
                await self.getYT()
                return
        except asyncio.TimeoutError:
            await self.convTimeout()
        except asyncio.CancelledError:
            await self.getYT()
