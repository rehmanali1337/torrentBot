import os
from telethon.errors import rpcerrorlist
import threading
import asyncio
from glob import glob
import shutil
from tg_exts.TGUtils import MegaSender


class Mega:
    def __init__(self, url, targetChannel, userID,
                 bot, client, tracker):
        self.url = url
        self.bot = bot
        self.client = client
        self.status = None
        self.userID = userID
        self.tracker = tracker
        self.channelLink = targetChannel
        self.ts = asyncio.run_coroutine_threadsafe
        self.root = os.getcwd()
        self.downloadLocation = f'{self.root}/Downloads/MegaDownloads/{threading.get_ident()}'
        if not os.path.exists(self.downloadLocation):
            os.makedirs(self.downloadLocation)

    async def download(self):
        await self.setStatus('Downloading mega files ...')
        cmd = f'mega-get {self.url} {self.downloadLocation}'
        os.system(cmd)
        await self.setStatus('Downloading complete!')

    async def send(self):
        await self.download()
        downloaded = glob(f'{self.downloadLocation}/*')
        for p in downloaded:
            if os.path.isdir(p):
                print('Sending folder ..')
                await self.sendFolder(p)
                continue
            if os.path.isfile(p):
                print('Sending file ')
                await self.sendFile(p)
                continue
        await self.setStatus('Job complete!')
        shutil.rmtree(self.downloadLocation)

    async def sendFolder(self, folderLocation):
        files = glob(f'{folderLocation}/*')
        for p in files:
            if os.path.isdir(p):
                await self.sendFolder(p)
                continue
            if os.path.isfile(p):
                await self.sendFile(p)
                continue

    async def setStatus(self, message):
        if self.status == None:
            try:
                self.status = self.ts(
                    self.bot.send_message(self.userID, message), self.bot.loop).result()
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                await asyncio.sleep(int(e.seconds) + 1)
            return
        try:
            self.ts(self.status.edit(
                message), self.bot.loop)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
            await asyncio.sleep(int(e.seconds) + 1)

    async def sendFile(self, fileLocation):
        fileName = fileLocation.split('/')[-1]
        sender = MegaSender(self.bot, self.client,
                            fileLocation, fileName,
                            self.channelLink, self.status, title=fileName,
                            tracker=self.tracker, userID=self.userID)
        await sender.send()
