
from models.seedr import Seedr
import threading
import time
import os
import requests
from dotenv import load_dotenv
import os
import asyncio
from telethon import TelegramClient, errors, events
from telethon.tl.custom import Button
from telethon.tl.types import KeyboardButtonCallback
from telethon.tl.types import KeyboardButton
from telethon.tl.types import DocumentAttributeAudio
from telethon.tl.types import DocumentAttributeVideo
from operator import itemgetter
import logging
import blacklist
from torrentool.api import Torrent
from datetime import datetime as dt
from moviepy.editor import VideoFileClip
from hurry.filesize import size
import shelve
import audio_metadata
from tg_exts.fast_streams import upload_file
from queue import Empty
from telethon.errors import rpcerrorlist

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.ERROR)


class TorrentAutomator:
    def __init__(self, threadName, bot, client, queue):
        self.threadName = threadName
        self.bot = bot
        self.queue = queue
        self.client = client
        self.loop = asyncio.new_event_loop()
        self.ts = asyncio.run_coroutine_threadsafe

    def start(self):
        self.loop.run_until_complete(self.main())

    async def main(self):
        while True:
            try:
                print(
                    f'Torrent Thread {self.threadName} waiting for torrent ...')
                job = self.queue.get()
                self.job = job
                self.status = None
                self.userID = job.get('userID')
                self.seedr = Seedr(self.bot, self.client)
                self.targetChannelLink = job.get("targetChannelLink")
                downloadType = job.get('downloadType')
                if downloadType == 'file':
                    await self.handleTorrentFile()
                    try:
                        os.remove(job.get('fileLocation'))
                    except FileNotFoundError:
                        pass
                    self.queue.task_done()
                    continue
                if downloadType == 'magnet':
                    await self.handleMagnetLink()
                    self.queue.task_done()
                    continue
            except:
                pass

    async def handleMagnetLink(self):
        magnetLink = self.job.get('magnet')
        targetChannelLink = self.job.get('targetChannelLink')
        targetUser = self.job.get('userID')
        await self.sendFolderContent(targetUser, targetChannelLink, magnet=magnetLink)

    async def handleTorrentFile(self):
        fileLocation = self.job.get('fileLocation')
        targetChannelLink = self.job.get('targetChannelLink')
        targetUser = self.job.get('userID')
        await self.sendFolderContent(targetUser, targetChannelLink, uploadedTorrentFile=fileLocation)

    async def sendFolderContent(self, user, targetChannelLink, uploadedTorrentFile=None, magnet=None):
        if uploadedTorrentFile == None and magnet == None:
            return
        if uploadedTorrentFile != None:
            addedTorrent = await self.seedr.downloadUsingTorrentFile(uploadedTorrentFile)
            os.remove(uploadedTorrentFile)
        if magnet != None:
            addedTorrent = await self.seedr.downloadUsingMagnet(magnet)
        try:
            await self.setStatus(
                f'Downloading the torrent : {addedTorrent["title"]}')
        except KeyError:
            await self.setStatus(
                f'Could not download torrent for some reason!\nPlease Try again!')
            return
        while True:
            downloadedTorrent = await self.seedr.getTorrentData(addedTorrent['user_torrent_id'])
            if downloadedTorrent['code'] == 403:
                await self.setStatus('Deleted!')
                return
            await self.torrentToSeedrPCB(downloadedTorrent, addedTorrent['user_torrent_id'])
            if downloadedTorrent.get('progress') != 101:
                await asyncio.sleep(1)
                continue
            break
        createdFolderId = downloadedTorrent['folder_created']
        self.ts(self.sendToTarget(createdFolderId,
                                  targetChannelLink, self.status), self.client.loop).result()
        await asyncio.sleep(0.8)
        await self.setStatus('Deleting torrent from seedr.cc ...')
        await self.seedr.deleteFolder(createdFolderId)
        await asyncio.sleep(0.8)
        await self.setStatus('Torrent deleted from seedr.cc!')
        await asyncio.sleep(0.8)
        await self.setStatus('All files have been sent successfully!')
        await asyncio.sleep(15)
        self.ts(self.status.delete(), self.bot.loop).result()

    async def torrentToSeedrPCB(self, data, torrentID):
        if data.get('code') == 200:
            percent = int(data.get('progress')) - 1
            if percent < 0:
                percent = 0
            print(percent)
            if percent < 100:
                torrentSize = size(int(data.get('size')))
                name = data.get('name')
                speed = data.get('speed')
                filledBar = ''.center(int(percent/2), ':')
                emptyBar = ''.center(int(50-(percent)/2), ' ')
                bar = f'[{filledBar}{emptyBar}] {percent}%'
                message = f'Torrent ID : {torrentID}\nTitle : {name}\n{bar}\n Downloading Speed : {size(speed)} Total Size : {torrentSize}'
                await self.setStatus(message)
            if percent == 100:
                torrentSize = size(int(data.get('size')))
                name = data.get('name')
                speed = data.get('speed')
                filledBar = ''.center(int(percent/2), ':')
                emptyBar = ''.center(int(50-(percent)/2), ' ')
                bar = f'[{filledBar}{emptyBar}] Complete!'
                message = f'Title : {name}\n{bar}\n Downloading Speed : {size(speed)} Total Size : {torrentSize}'
                await self.setStatus(message)

    async def sendToTarget(self, folderId, targetChannelLink, status):
        await self.seedr.filterDownloadedContent(folderId)
        cover_extensions = ['jpg', 'JPG', 'jpeg', 'JPEG', 'PNG', 'png']
        folderContent = await self.seedr.getFolderContent(folderID=folderId)
        for f in folderContent['files']:
            extension = f.get('name').split('.')[-1].lower()
            if extension in cover_extensions:
                await asyncio.sleep(0.8)
                await self.setStatus('Sending the cover image ...')
                fileDownloadLink = await self.seedr.getDownloadLink(f['id'])
                try:
                    self.ts(self.client.send_file(targetChannelLink,
                                                  fileDownloadLink), self.client.loop)
                except errors.rpcerrorlist.WebpageCurlFailedError:
                    if not os.path.exists('./Downloads'):
                        os.mkdir(
                            './Downloads'
                        )
                    downloadedFile = await self.seedr.downloadFile(f.get('id'), f'Downloads/{f.get("name")}')
                    toSend = open(downloadedFile, 'rb')
                    self.ts(self.client.send_file(
                        targetChannelLink, toSend), self.client.loop)
                    os.remove(downloadedFile)
                await asyncio.sleep(0.8)
                await self.setStatus('Cover image sent!')
        if len(folderContent['folders']) != 0:
            for folder in folderContent['folders']:
                await self.sendToTarget(folder['id'], targetChannelLink, status)
        files = sorted(folderContent['files'], key=itemgetter('name'))
        for f in files:
            self.fileName = f.get("name")
            voicePlayable = ['flac', 'mp3', 'MP3']
            streamableFiles = ['mp4', 'MP4', 'Mp4', 'mP4']
            await asyncio.sleep(0.8)
            await self.setStatus(f'Sending file : {f.get("name")}')
            extension = f.get('name').split('.')[-1]
            if extension in cover_extensions:
                continue
            try:
                fileDownloadLink = await self.seedr.getDownloadLink(f['id'])
                while True:
                    try:
                        if extension in voicePlayable:
                            self.ts(self.client.send_file(targetChannelLink, fileDownloadLink,
                                                          supports_streaming=True, voice_note=True),
                                    self.client.loop)
                        elif extension in streamableFiles:
                            self.ts(self.client.send_file(targetChannelLink,
                                                          fileDownloadLink, supports_streaming=True),
                                    self.client.loop)
                        else:
                            self.ts(self.client.send_file(
                                targetChannelLink, fileDownloadLink), self.client.loop)
                        break
                    except errors.rpcerrorlist.FloodWaitError as e:
                        await asyncio.sleep(int(e.seconds) + 5)
                        continue

            except errors.rpcerrorlist.WebpageCurlFailedError:
                if not os.path.exists('./Downloads'):
                    os.mkdir('./Downloads')
                downloadedFile = await self.seedr.downloadFile(f.get('id'), f'./Downloads/{f.get("name")}')
                if not self.validSize(downloadedFile):
                    continue
                toSend = open(downloadedFile, 'rb')
                try:
                    fastFile = self.ts(upload_file(self.client, toSend, fileName=f.get("name"),
                                                   progress_callback=self.uploadPcb),
                                       self.client.loop).result()
                except ValueError:
                    await asyncio.sleep(0.8)
                    await self.setStatus(
                        f'The file {f.get("name")} is too large to upload!')
                    continue
                while True:
                    try:
                        if extension in voicePlayable:
                            metadata = self.getMetadata(downloadedFile)
                            attributes = [
                                DocumentAttributeAudio(
                                    int(metadata.streaminfo.duration), performer=metadata.tags.artist[0], voice=False, title=metadata.tags.title[0],)
                            ]
                            self.ts(self.client.send_file(targetChannelLink, fastFile,
                                                          attributes=attributes, supports_streaming=True),
                                    self.client.loop)
                        elif extension in streamableFiles:
                            duration, width, height = self.getVideoMetadata(
                                downloadedFile)
                            attributes = [DocumentAttributeVideo(
                                duration, width, height, supports_streaming=True)]
                            self.ts(self.client.send_file(targetChannelLink, fastFile,
                                                          supports_streaming=True, attributes=attributes),
                                    self.client.loop)
                        else:
                            self.ts(self.client.send_file(targetChannelLink, fastFile),
                                    self.client.loop)
                        break
                    except errors.rpcerrorlist.FloodWaitError as e:
                        await asyncio.sleep(int(e.seconds) + 5)
                        continue

                os.remove(downloadedFile)

    async def setStatus(self, message):
        if not self.status:
            try:
                self.status = self.ts(self.bot.send_message(self.userID, message),
                                      self.bot.loop).result()
                await asyncio.sleep(1)
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                print(f'Flood wait for {e.seconds}')
                await asyncio.sleep(int(e.seconds) + 1)
            return
        try:
            self.ts(self.status.edit(
                message), self.bot.loop)
            await asyncio.sleep(1)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
            print(f'Flood wait for {e.seconds}')
            await asyncio.sleep(int(e.seconds) + 1)

    async def uploadPcb(self, uploaded, total):
        if uploaded == total:
            await asyncio.sleep(1)
            await self.setStatus('Upload Complete!')
            return
        percent = int((uploaded/total) * 100)
        if not hasattr(self, 'prevPercent'):
            self.prevPercent = 0
        if not percent > self.prevPercent:
            return
        self.prevPercent = percent
        spaces = int(int(100 - percent)/2)
        spacesBar = ''.center(spaces, ' ')
        bar = ''.center(int(percent/2), ':')
        bar = f'{bar}'
        finalBar = f'[{bar}{spacesBar}]   {percent}%'
        message = f'Filename : {self.fileName}\n{finalBar}\nTotal Size : {size(total)}\n\
Uploaded : {size(uploaded)}'
        await self.setStatus(message)

    @staticmethod
    def getVideoMetadata(videoLocation):
        video = VideoFileClip(videoLocation)
        duration = video.duration
        width = video.size[0]
        height = video.size[1]
        return int(duration), int(width), int(height)

    @staticmethod
    def getMetadata(fileName):
        metadata = audio_metadata.load(fileName)
        return metadata

    @staticmethod
    def validSize(filePath):
        stat = os.stat(filePath)
        sizeInGB = stat.st_size >> 30
        return sizeInGB <= 2

    @staticmethod
    def purifyName(oldName):
        newNameChars = [c for c in oldName if c.isalnum() or c ==
                        '-' or c == '.' or c == ' ']
        newName = ''.join(newNameChars)
        return newName
