import os
import asyncio
from telethon.errors import rpcerrorlist
from telethon import TelegramClient, errors, events
from telethon.tl.custom import Button
from telethon.tl.types import KeyboardButtonCallback
from telethon.tl.types import KeyboardButton
from telethon.tl.types import DocumentAttributeAudio
from moviepy.editor import VideoFileClip
from telethon.tl.types import DocumentAttributeVideo
from tg_exts.fast_streams import upload_file
import audio_metadata
import logging
from tinytag import TinyTag
from hurry.filesize import size
from datetime import datetime as dt


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.ERROR)


def getVideoMetadata(videoLocation):
    video = VideoFileClip(videoLocation)
    duration = video.duration
    width = video.size[0]
    height = video.size[1]
    return int(duration), int(width), int(height)


def getMetadata(fileName):
    try:
        metadata = audio_metadata.load(fileName)
    except audio_metadata.exceptions.UnsupportedFormat:
        return None
    return metadata


def validSize(filePath):
    stat = os.stat(filePath)
    sizeInGB = stat.st_size >> 30
    return sizeInGB <= 2


class MegaSender:
    def __init__(self, bot, client,
                 fileLocation, fileName, channelLink,
                 status, title: str = None):
        self.bot = bot
        self.client = client
        self.fileLocation = fileLocation
        self.fileName = fileName
        self.title = title
        self.targetChannelLink = channelLink
        self.status = status
        self.ts = asyncio.run_coroutine_threadsafe

    async def setStatus(self, message):
        if self.status is not None:
            try:
                self.ts(self.status.edit(
                    message), self.bot.loop)
                # await asyncio.sleep(1)
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                await asyncio.sleep(int(e.seconds) + 1)
            return
        print('Status is none')

    async def uploadPcb(self, uploaded, total):
        if uploaded == total:
            await self.setStatus('File Uploaded!')
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

    async def send(self):
        voicePlayable = ['flac', 'mp3', 'MP3']
        streamableFiles = ['mp4', 'MP4', 'Mp4', 'mP4']
        if not validSize(self.fileLocation):
            await self.setStatus('Too large to upload!')
        toSend = open(self.fileLocation, 'rb')
        try:
            title = self.title.split('\n')[0]
            fastFile = self.ts(upload_file(
                self.client, toSend, fileName=title,
                progress_callback=self.uploadPcb), self.client.loop).result()
        except ValueError:
            await self.setStatus(f'The file {self.title} is too large to upload!')
            return
        extension = self.fileName.split('.')[-1]
        while True:
            try:
                if extension in voicePlayable:
                    print('Sending as audio')
                    metadata = getMetadata(self.fileLocation)
                    data = TinyTag.get(self.fileLocation)
                    try:
                        performer = metadata.tags.artist[0] if metadata else None
                        title = metadata.tags.title[0] if metadata else self.title.split('\n')[
                            0]
                        duration = metadata.streaminfo.duration if metadata else data.duration
                    except AttributeError:
                        performer = None
                        title = self.title
                        duration = data.duration
                    attributes = [
                        DocumentAttributeAudio(
                            int(duration), performer=performer,
                            voice=False, title=f'{title}.mp3')
                    ]
                    self.ts(self.client.send_file(self.targetChannelLink,
                                                  fastFile, attributes=attributes, supports_streaming=True),
                            loop=self.client.loop).result()
                    break
                elif extension in streamableFiles:
                    print('Sending as streamable...')
                    duration, width, height = getVideoMetadata(
                        self.fileLocation)
                    attributes = [DocumentAttributeVideo(
                        duration, width, height, supports_streaming=True)]
                    self.ts(self.client.send_file(self.targetChannelLink,
                                                  fastFile, supports_streaming=True, attributes=attributes),
                            self.client.loop).result()
                    break
                else:
                    print('Sending as file ..')
                    self.ts(self.client.send_file(self.targetChannelLink, fastFile),
                            self.client.loop).result()
                    break
            except errors.rpcerrorlist.FloodWaitError as e:
                await asyncio.sleep(int(e.seconds) + 5)


class TorrentSender:
    def __init__(self, bot, client,
                 fileLocation, fileName, channelLink,
                 status, thumbnailLocation: str = None,
                 title: str = None):
        self.bot = bot
        self.client = client
        self.fileLocation = fileLocation
        self.thumbnailLocation = thumbnailLocation
        self.fileName = fileName
        self.title = title
        self.targetChannelLink = channelLink
        self.status = status
        self.ts = asyncio.run_coroutine_threadsafe

    async def setStatus(self, message):
        if self.status is not None:
            try:
                self.ts(self.status.edit(
                    message), self.bot.loop)
                await asyncio.sleep(1)
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                await asyncio.sleep(int(e.seconds) + 1)
            return
        print('Status is none')

    async def uploadPcb(self, uploaded, total):
        if uploaded == total:
            await self.setStatus('File Uploaded!')
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

    async def send(self):
        voicePlayable = ['flac', 'mp3', 'MP3']
        streamableFiles = ['mp4', 'MP4', 'Mp4', 'mP4']
        if not validSize(self.fileLocation):
            await self.setStatus('Too large to upload!')
        toSend = open(self.fileLocation, 'rb')
        try:
            title = self.title.split('\n')[0]
            print('Creating fast file ...')
            fastFile = self.ts(upload_file(
                self.client, toSend, fileName=title,
                progress_callback=self.uploadPcb), self.client.loop).result()
        except ValueError:
            await self.setStatus(f'The file {self.title} is too large to upload!')
            return
        extension = self.fileName.split('.')[-1]
        while True:
            try:
                if extension in voicePlayable:
                    print('Sending as audio')
                    metadata = getMetadata(self.fileLocation)
                    data = TinyTag.get(self.fileLocation)
                    try:
                        performer = metadata.tags.artist[0] if metadata else None
                        title = metadata.tags.title[0] if metadata else self.title.split('\n')[
                            0]
                        duration = metadata.streaminfo.duration if metadata else data.duration
                    except AttributeError:
                        performer = None
                        title = self.title
                        duration = data.duration
                    attributes = [
                        DocumentAttributeAudio(
                            int(duration), performer=performer,
                            voice=False, title=f'{title}.mp3')
                    ]
                    self.ts(self.client.send_file(self.targetChannelLink,
                                                  fastFile, attributes=attributes, supports_streaming=True),
                            loop=self.client.loop).result()
                    break
                elif extension in streamableFiles:
                    print('Sending as streamable...')
                    duration, width, height = getVideoMetadata(
                        self.fileLocation)
                    attributes = [DocumentAttributeVideo(
                        duration, width, height, supports_streaming=True)]
                    self.ts(self.client.send_file(self.targetChannelLink,
                                                  fastFile, supports_streaming=True, attributes=attributes),
                            self.client.loop).result()
                    break
                else:
                    print('Sending as file ..')
                    self.ts(self.client.send_file(self.targetChannelLink, fastFile),
                            self.client.loop).result()
                    break
            except errors.rpcerrorlist.FloodWaitError as e:
                await asyncio.sleep(int(e.seconds) + 5)


class YoutuebeVideoSender:
    def __init__(self, bot, client,
                 fileLocation, fileName, channelLink,
                 status, thumbnailLocation: str = None,
                 title: str = None):
        self.bot = bot
        self.client = client
        self.fileLocation = fileLocation
        self.thumbnailLocation = thumbnailLocation
        self.fileName = fileName
        self.title = title
        self.targetChannelLink = channelLink
        self.status = status
        self.ts = asyncio.run_coroutine_threadsafe

    async def setStatus(self, message):
        try:
            self.ts(self.status.edit(
                message), self.bot.loop)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
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
        if not hasattr(self, 'timer'):
            self.timer = dt.now().today().ctime()
            return
        ctimer = dt.now().today().ctime()
        if self.timer == ctimer:
            return
        self.timer = ctimer
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

    async def send(self):
        if self.thumbnailLocation:
            await self.setStatus('Sending thumbnail ...')
            title = self.title.replace('.mp3', '')
            caption = f'<b>{self.title}</b>'
            self.ts(self.client.send_file(self.targetChannelLink,
                                          self.thumbnailLocation, caption=caption),
                    self.client.loop)
            await self.setStatus('Thumbnail sent!')
        if not validSize(self.fileLocation):
            await self.setStatus('Too large to upload!')
        toSend = open(self.fileLocation, 'rb')
        try:
            print('Sending as streamable...')
            try:
                title = self.fileLocation.split('/')[-1]
                print('Creating fastfile')
                fastFile = self.ts(upload_file(
                    self.client, toSend, fileName=title,
                    progress_callback=self.uploadPcb), self.client.loop).result()
            except ValueError:
                await self.setStatus(f'The file {self.title} is too large to upload!')
                return
            duration, width, height = getVideoMetadata(
                self.fileLocation)
            attributes = [DocumentAttributeVideo(
                duration, width, height, supports_streaming=True)]
            self.ts(self.client.send_file(self.targetChannelLink,
                                          fastFile, supports_streaming=True, attributes=attributes),
                    self.client.loop).result()
        except errors.rpcerrorlist.FloodWaitError as e:
            await asyncio.sleep(int(e.seconds) + 5)


class YoutubeAudioSender:
    def __init__(self, bot, client,
                 fileLocation, fileName, channelLink,
                 status, thumbnailLocation: str = None,
                 title: str = None):
        self.bot = bot
        self.client = client
        self.fileLocation = fileLocation
        self.thumbnailLocation = thumbnailLocation
        self.fileName = fileName
        self.title = title
        self.targetChannelLink = channelLink
        self.status = status
        self.ts = asyncio.run_coroutine_threadsafe

    async def setStatus(self, message):
        try:
            self.ts(self.status.edit(
                message), self.bot.loop)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
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
        if not hasattr(self, 'timer'):
            self.timer = dt.now().today().ctime()
            return
        ctimer = dt.now().today().ctime()
        if self.timer == ctimer:
            return
        self.timer = ctimer
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
        message = f'Filename : {self.title}\n{finalBar}\nTotal Size : {size(total)}\n\
Uploaded : {size(uploaded)}'
        await self.setStatus(message)

    async def send(self):
        if self.thumbnailLocation:
            await self.setStatus('Sending thumbnail ...')
            title = self.title.replace('.mp3', '')
            caption = f'<b>{self.title}</b>'
            self.ts(self.client.send_file(self.targetChannelLink,
                                          self.thumbnailLocation, caption=caption),
                    self.client.loop)
            await self.setStatus('Thumbnail sent!')
        if not validSize(self.fileLocation):
            await self.setStatus('Too large to upload!')
        toSend = open(self.fileLocation, 'rb')
        try:
            try:
                title = self.title.split('\n')[0]
                print('Sending as audio')
                print('Creating fastfile')
                fastFile = self.ts(upload_file(
                    self.client, toSend, fileName=title,
                    progress_callback=self.uploadPcb), self.client.loop).result()
            except ValueError:
                await self.setStatus(f'The file {self.title} is too large to upload!')
                return
            metadata = getMetadata(self.fileLocation)
            data = TinyTag.get(self.fileLocation)
            try:
                performer = metadata.tags.artist[0] if metadata else None
                title = metadata.tags.title[0] if metadata else self.title.split('\n')[
                    0]
                duration = metadata.streaminfo.duration if metadata else data.duration
            except AttributeError:
                performer = None
                title = self.title
                duration = data.duration
            attributes = [
                DocumentAttributeAudio(
                    int(duration), performer=performer,
                    voice=False, title=f'{title}.mp3')
            ]
            self.ts(self.client.send_file(self.targetChannelLink,
                                          fastFile, attributes=attributes, supports_streaming=True),
                    loop=self.client.loop).result()
        except errors.rpcerrorlist.FloodWaitError as e:
            await asyncio.sleep(int(e.seconds) + 5)
