import asyncio
import os
import threading
from models.seedr import Seedr
from operator import itemgetter
from tg_exts.fast_streams import upload_file
from telethon.tl.types import DocumentAttributeAudio
from telethon.tl.types import DocumentAttributeVideo
from telethon.errors import rpcerrorlist
from moviepy.editor import VideoFileClip
import audio_metadata
from telethon import TelegramClient, errors, events
from hurry.filesize import size
import logging
from datetime import datetime as dt


class Torrenter:
    def __init__(self, client, bot,
                 magnet=None, userID=None,
                 fileLocation=None, targetChannelLink=None, tracker=None):
        self.client = client
        self.bot = bot
        self.targetChannelLink = targetChannelLink
        self.userID = userID
        self.tracker = tracker
        self.magnet = magnet
        self.fileLocation = fileLocation
        self.seedr = Seedr()
        self.logger = logging.getLogger(' Torrent Model ')
        self.ts = asyncio.run_coroutine_threadsafe
        self.rootLocation = os.getcwd()
        self.downloadLocation = f'{self.rootLocation}/Downloads/TorrentDownloads/{threading.get_ident()}'
        if not os.path.exists(self.downloadLocation):
            os.makedirs(self.downloadLocation)

    async def handleMagnetLink(self):
        magnetLink = self.magnet
        targetChannelLink = self.targetChannelLink
        targetUser = self.userID
        self.logger.info('Using magnet link ..')
        await self.sendFolderContent(targetUser, targetChannelLink, magnet=magnetLink)

    async def handleTorrentFile(self):
        fileLocation = self.fileLocation
        targetChannelLink = self.targetChannelLink
        targetUser = self.userID
        self.logger.info('Using torrent file ..')
        await self.sendFolderContent(targetUser, targetChannelLink, uploadedTorrentFile=fileLocation)

    async def sendFolderContent(self, user, targetChannelLink, uploadedTorrentFile=None, magnet=None):
        await self.setStatus('Starting transfer from torrent to seedr ...')
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
        folder_id = None
        while True:
            downloadedTorrent = await self.seedr.getTorrentData(addedTorrent['user_torrent_id'])
            try:
                if downloadedTorrent['folder_created'] != 0:
                    if folder_id is None:
                        folder_id = downloadedTorrent['folder_created']
            except KeyError:
                await self.setStatus(
                    f'Could not download torrent for some reason!\nPlease Try again!')
                return
            if downloadedTorrent['code'] == 403:
                await self.setStatus('Deleted!')
                return
            await self.torrentToSeedrPCB(downloadedTorrent, addedTorrent['user_torrent_id'])
            if downloadedTorrent.get('progress') != 101:
                await asyncio.sleep(1)
                continue
            if folder_id is None:
                await asyncio.sleep(1)
                continue
            break
        self.logger.info('Download complete')
        await self.sendToTarget(folder_id,
                                targetChannelLink, self.status)
        await asyncio.sleep(0.8)
        self.logger.info('Deleting torrent from seedr ...')
        await self.setStatus('Deleting torrent from seedr.cc ...')
        await self.seedr.deleteFolder(folder_id)
        await asyncio.sleep(0.8)
        await self.setStatus('Torrent deleted from seedr.cc!')
        await asyncio.sleep(0.8)
        await self.setStatus('All files have been sent successfully!')
        await asyncio.sleep(15)
        self.ts(self.status.delete(), self.bot.loop).result()

    async def torrentToSeedrPCB(self, data, torrentID):
        if not self.tracker.request_allowed(self.userID):
            return
        if data.get('code') == 200:
            percent = int(data.get('progress')) - 1
            if percent < 0:
                percent = 0
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
            self.logger.info(f'Sending file : {f.get("name")}')
            extension = f.get('name').split('.')[-1].lower()
            if extension in cover_extensions:
                await asyncio.sleep(0.8)
                await self.setStatus('Sending the cover image ...')
                fileDownloadLink = await self.seedr.getDownloadLink(f['id'])
                try:
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    self.ts(self.client.send_file(targetChannelLink,
                                                  fileDownloadLink), self.client.loop)
                except errors.rpcerrorlist.WebpageCurlFailedError:
                    downloadedFile = await self.seedr.downloadFile(f.get('id'),
                                                                   f'{self.downloadLocation}/{f.get("name")}')
                    toSend = open(downloadedFile, 'rb')
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    self.ts(self.client.send_file(
                        targetChannelLink, toSend), self.client.loop).result()
                    os.remove(downloadedFile)
                await asyncio.sleep(0.8)
                self.logger.info(f'File sent : {f.get("name")}')
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
                try:
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    await self.direct_sender(targetChannelLink, fileDownloadLink,
                                             extension, voicePlayable, streamableFiles, f)
                except errors.rpcerrorlist.FloodWaitError as e:
                    self.logger.info(
                        f'Flood wait error!\nWaiting for {e.seconds} seconds before retry!')
                    await asyncio.sleep(int(e.seconds) + 5)
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    await self.direct_sender(targetChannelLink, fileDownloadLink,
                                             extension, voicePlayable, streamableFiles, f)

            except (errors.rpcerrorlist.WebpageCurlFailedError, errors.rpcerrorlist.ExternalUrlInvalidError):
                downloadedFile = await self.seedr.downloadFile(f.get('id'),
                                                               f'{self.downloadLocation}/{f.get("name")}')
                if not self.validSize(downloadedFile):
                    self.logger.info('File size is not valid ...')
                    continue
                toSend = open(downloadedFile, 'rb')
                try:
                    fastFile = self.ts(upload_file(self.client, toSend, fileName=f.get("name"),
                                                   progress_callback=self.uploadPcb),
                                       self.client.loop).result()
                    self.logger.info('Fast file created!')
                except ValueError:
                    await asyncio.sleep(0.8)
                    await self.setStatus(
                        f'The file {f.get("name")} is too large to upload!')
                    self.logger.info(
                        f'File is too larget to upload:  {self.fileName}')
                    continue
                try:
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    await self.local_sender(extension, voicePlayable, streamableFiles,
                                            downloadedFile, targetChannelLink, fastFile)
                except errors.rpcerrorlist.FloodWaitError as e:
                    self.logger.info(
                        f'Flood wait error! \nWaiting for {e.seconds} seconds before retry!')
                    await asyncio.sleep(int(e.seconds) + 5)
                    while not self.tracker.request_allowed(targetChannelLink):
                        await asyncio.sleep(1)
                    await self.local_sender(extension, voicePlayable, streamableFiles,
                                            downloadedFile, targetChannelLink, fastFile)
                os.remove(downloadedFile)

    async def direct_sender(self, targetChannelLink, fileDownloadLink,
                            extension, voicePlayable, streamableFiles, f):
        try:
            if extension in voicePlayable:
                while not self.tracker.request_allowed(targetChannelLink):
                    await asyncio.sleep(1)
                self.ts(self.client.send_file(targetChannelLink, fileDownloadLink,
                                              supports_streaming=True,
                                              progress_callback=self.uploadPcb),
                        self.client.loop).result()
            elif extension in streamableFiles:
                while not self.tracker.request_allowed(targetChannelLink):
                    await asyncio.sleep(1)
                self.ts(self.client.send_file(targetChannelLink,
                                              fileDownloadLink, supports_streaming=True,
                                              progress_callback=self.uploadPcb),
                        self.client.loop).result()
            else:
                while not self.tracker.request_allowed(targetChannelLink):
                    await asyncio.sleep(1)
                self.ts(self.client.send_file(
                    targetChannelLink, fileDownloadLink, progress_callback=self.uploadPcb),
                    self.client.loop).result()
        except errors.rpcerrorlist.ExternalUrlInvalidError:
            downloadedFile = await self.seedr.downloadFile(f.get('id'),
                                                           f'{self.downloadLocation}/{f.get("name")}')
            if not self.validSize(downloadedFile):
                self.logger.info('File size is not valid ...')
            toSend = open(downloadedFile, 'rb')
            try:
                fastFile = self.ts(upload_file(self.client, toSend, fileName=f.get("name"),
                                               progress_callback=self.uploadPcb),
                                   self.client.loop).result()
                self.logger.info('Fast file created!')
            except ValueError:
                await asyncio.sleep(0.8)
                await self.setStatus(
                    f'The file {f.get("name")} is too large to upload!')
                self.logger.info(
                    f'File is too larget to upload:  {self.fileName}')
                return
            try:
                await self.local_sender(extension, voicePlayable, streamableFiles,
                                        downloadedFile, targetChannelLink, fastFile)
            except errors.rpcerrorlist.FloodWaitError as e:
                self.logger.info(
                    f'Flood wait error! \nWaiting for {e.seconds} seconds before retry!')
                await asyncio.sleep(int(e.seconds) + 5)
                await self.local_sender(extension, voicePlayable, streamableFiles,
                                        downloadedFile, targetChannelLink, fastFile)
            os.remove(downloadedFile)

    async def local_sender(self, extension, voicePlayable, streamableFiles,
                           downloadedFile, targetChannelLink, fastFile):
        self.logger.info(f'Using local sender ...')
        if extension in voicePlayable:
            self.logger.info('Sending as voice playable ...')
            metadata = self.getMetadata(downloadedFile)
            try:
                attributes = [
                    DocumentAttributeAudio(
                        int(metadata.streaminfo.duration), performer=metadata.tags.artist[0], voice=False, title=metadata.tags.title[0],)
                ]
            except AttributeError:
                attributes = [
                    DocumentAttributeAudio(
                        int(0), performer='Unknown', voice=False, title='Unknown',)
                ]

            while not self.tracker.request_allowed(targetChannelLink):
                await asyncio.sleep(1)
            self.ts(self.client.send_file(targetChannelLink, fastFile,
                                          attributes=attributes, supports_streaming=True,
                                          progress_callback=self.uploadPcb),
                    self.client.loop).result()
        elif extension in streamableFiles:
            self.logger.info('Sending as streamable ...')
            duration, width, height = self.getVideoMetadata(
                downloadedFile)
            attributes = [DocumentAttributeVideo(
                duration, width, height, supports_streaming=True)]
            while not self.tracker.request_allowed(targetChannelLink):
                await asyncio.sleep(1)
            self.ts(self.client.send_file(targetChannelLink, fastFile,
                                          supports_streaming=True, attributes=attributes,
                                          progress_callback=self.uploadPcb),
                    self.client.loop).result()
        else:
            self.logger.info('Sending as raw ...')
            while not self.tracker.request_allowed(targetChannelLink):
                await asyncio.sleep(1)
            self.ts(self.client.send_file(targetChannelLink, fastFile,
                                          progress_callback=self.uploadPcb),
                    self.client.loop).result()

    async def setStatus(self, message):
        if not hasattr(self, 'status'):
            try:
                self.status = self.ts(self.bot.send_message(self.userID, message),
                                      self.bot.loop).result()
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                print(f'Flood wait for {e.seconds}')
                await asyncio.sleep(int(e.seconds) + 1)
            return
        try:
            self.ts(self.status.edit(
                message), self.bot.loop)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
            print(f'Flood wait for {e.seconds}')
            await asyncio.sleep(int(e.seconds) + 1)

    async def uploadPcb(self, uploaded, total):
        if not hasattr(self, 'uploadComplete'):
            self.uploadComplete = False
        if self.uploadComplete:
            return
        if uploaded == total:
            await self.setStatus('Upload Complete!')
            self.uploadComplete = True
            return
        if not self.tracker.request_allowed(self.userID):
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
