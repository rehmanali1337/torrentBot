
from youtube_dl import YoutubeDL
import youtube_dl
import os
from pprint import pprint
import asyncio
from tg_exts.TGUtils import YoutubeAudioSender, YoutuebeVideoSender
from telethon.errors import rpcerrorlist
import ffmpeg
import threading
from glob import glob
import shutil
import requests
import re
from datetime import datetime as dt


class YTube:
    def __init__(self, bot, client,
                 url, selectedFormat, userID, channelLink):
        self.url = url
        self.bot = bot
        self.client = client
        self.userID = userID
        self.channelLink = channelLink
        self.selectedFormat = selectedFormat
        self.rootLocation = os.getcwd()
        self.downloadLocation = f'{self.rootLocation}/Downloads/{threading.get_ident()}'
        self.thumbnailDir = f'{self.downloadLocation}/thumbnail'
        if not os.path.exists(self.downloadLocation):
            os.makedirs(self.downloadLocation)
            os.makedirs(self.thumbnailDir)
        self.ts = asyncio.run_coroutine_threadsafe

    @staticmethod
    def filterTitle(title):
        # Filter the unwanted words from the title
        wordList = ['Lyric', 'Official', 'Music', 'Video',
                    'OFFICIAL', 'VIDEO', 'Official', 'video', 'Lyrics', '(', ')', '[', ']']
        wordsRegex = re.compile('|'.join(map(re.escape, wordList)))
        title = wordsRegex.sub('', title)
        title = re.sub(' +', ' ', title)
        return title

    async def sendVideo(self):
        ydl_opts = {
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url=self.url, download=False)
            self.status = self.ts(self.bot.send_message(self.userID,
                                                        f'Starting to download {info["title"]}'),
                                  self.bot.loop).result()

            self.fileName = info["title"]
            channel = info["uploader"]
            artist = info["artist"]
            self.title = f'{info["title"]}'
            self.title = self.filterTitle(self.title)
            if artist:
                self.title = f'{self.title}\nArtist : {artist}'
            else:
                self.title = f'{self.title}\nChannel : {channel}'
            for f in info['formats']:
                if self.selectedFormat == f['format_note'] and f['ext'] == 'mp4':
                    self.formatID = f['format_id']

        ydl_opts = {
            'format': f'{self.formatID}+bestaudio',
            'progress_hooks': [self.ytDownloadPcb],
            'outtmpl': self.downloadLocation + '/%(title)s.%(ext)s'
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])
        self.fileLocation = glob(
            f'{self.downloadLocation}/*')[0]
        if os.path.isdir(self.fileLocation):
            self.fileLocation = glob(
                f'{self.downloadLocation}/*')[1]
        assert os.path.isfile(self.fileLocation)
        self.fileName = self.fileLocation.split('/')[-1]
        if self.fileName.endswith('.mkv'):
            await self.setStatus('Converting mkv file to mp4 ...')
            # os.system(
            # f'ffmpeg -i {self.fileLocation} -codec copy {self.fileLocation}.mp4')
            ffmpeg.input(self.fileLocation).output(
                f'{self.fileLocation}.mp4').run()
            self.fileLocation = f'{self.fileLocation}.mp4'
            await self.setStatus('Conversion complete!')
        self.fileName = self.fileLocation.split('/')[-1]
        thumbnailURL = info['thumbnails'][-1]['url']
        self.thumbnailLocation = self.download_file(thumbnailURL)
        sender = YoutuebeVideoSender(self.bot, self.client, self.fileLocation,
                                     self.fileName, self.channelLink,
                                     self.status, thumbnailLocation=self.thumbnailLocation, title=self.title)
        await sender.send()
        await self.setStatus('Job completed!')
        await self.delete()

    async def setStatus(self, message):
        if not hasattr(self, 'status'):
            try:
                # await asyncio.sleep(1)
                self.status = self.ts(self.bot.send_message(self.userID,
                                                            message),
                                      self.bot.loop).result()
            except rpcerrorlist.MessageNotModifiedError:
                pass
            except rpcerrorlist.FloodWaitError as e:
                print(f'Flood error!\nSleeping for {e.seconds}')
                await asyncio.sleep(int(e.seconds) + 1)
            return
        try:
            self.ts(self.status.edit(message), self.bot.loop)
            # await asyncio.sleep(1)
        except rpcerrorlist.MessageNotModifiedError:
            pass
        except rpcerrorlist.FloodWaitError as e:
            print(f'Flood error!\nSleeping for {e.seconds}')
            await asyncio.sleep(int(e.seconds) + 1)

    def ytDownloadPcb(self, d):
        if not hasattr(self, 'timer'):
            self.timer = dt.now().today().ctime()
            return
        if d['status'] == 'downloading':
            ctimer = dt.now().today().ctime()
            if self.timer == ctimer:
                return
            self.timer = ctimer
            percent = int(int(d['_percent_str'].split('.')[0].strip())/2)
            spaces = int(50 - percent)
            spacesBar = ''.center(spaces, ' ')
            bar = ''.center(percent, ':')
            bar = f'{bar}'
            finalBar = f'[{bar}{spacesBar}] {d["_percent_str"]}'
            title = d["filename"].split('/')[-1]
            message = f'Title : {title}\n{finalBar}\n\
Downloading Speed : {d["_speed_str"]}\nETA : {d["_eta_str"]}\nTotal Size : {d["_total_bytes_str"]}'
            self.ts(self.setStatus(f'{message}'), self.bot.loop).result()
            return
        if d['status'] == 'finished':
            bar = ''.center(50, ':')
            bar = f'{bar}'
            finalBar = f'[{bar}] 100%'
            title = d["filename"].split('/')[-1]
            try:
                message = f'Title : {d["filename"]}\n{finalBar}\n\
Elapsed : {d["_elapsed_str"]}\nTotal Size : {d["_total_bytes_str"]}'
            except KeyError:
                message = f'Title : {d["filename"]}\n{finalBar}\n\
Total Size : {d["_total_bytes_str"]}'
            self.ts(self.setStatus(f'{message}'), self.bot.loop).result()

    async def sendAudio(self):
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url=self.url, download=False)
            self.title = f'{info["title"]}.mp3'
            channel = info["uploader"]
            artist = info["artist"]
            self.title = self.filterTitle(self.title)
            if artist:
                self.title = f'{self.title}\nArtist : {artist}'
            else:
                self.title = f'{self.title}\nChannel : {channel}'
        await self.setStatus('Starting to downlad the audio ..')
        ydl_opts = {
            'format': 'bestaudio/best',
            'progress_hooks': [self.ytDownloadPcb],
            'forcethumbnail': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': self.downloadLocation + '/ %(title)s.%(ext)s'
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url=self.url, download=True)
        self.fileLocation = glob(
            f'{self.downloadLocation}/*')[0]
        if self.fileLocation.split('/')[-1] == 'thumbnail':
            self.fileLocation = glob(
                f'{self.downloadLocation}/*')[1]
        self.fileName = self.fileLocation.split('/')[-1]
        thumbnailURL = info['thumbnails'][-1]['url']
        self.thumbnailLocation = self.download_file(thumbnailURL)
        sender = YoutubeAudioSender(self.bot, self.client, self.fileLocation,
                                    self.fileName, self.channelLink,
                                    self.status, thumbnailLocation=self.thumbnailLocation, title=self.title)

        await sender.send()
        await self.setStatus('Job completed!')
        await self.delete()

    def download_file(self, url):
        filename = f'{self.thumbnailDir}/thumb.jpg'
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return filename

    async def sendPlayList(self):
        pass
        ydl = youtube_dl.YoutubeDL(
            {'outtmpl': '%(id)s%(ext)s', 'quiet': True, })
        video = ""

        with ydl:
            result = ydl.extract_info(self.url,
                                      download=False)  # We just want to extract the info

            if 'entries' in result:
                # Can be a playlist or a list of videos
                video = result['entries']

                # loops entries to grab each video_url
                for i, item in enumerate(video):
                    video = result['entries'][i]
                    # url of the video
                    result['entries'][i]['title']  # title of video
                    result['entries'][i]['uploader']  # username of uploader
                    result['entries'][i]['playlist']  # name of the playlist
                    result['entries'][i]['playlist_index']

    async def delete(self):
        try:
            shutil.rmtree(self.downloadLocation)
        except FileNotFoundError:
            pass


def getAllFormats(url):
    ydl_opts = {
        'forcethumbnail': True,
        'ignoreerrors': True
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url=url, download=False)
        typeOfLink = info.get('_type')
        if typeOfLink == 'playlist':
            return 'playlist'
        formats = []
        for f in info['formats']:
            formats.append(f['format_note'])
        return formats


def getVideosLinks(playListURL):
    # ydl = youtube_dl.YoutubeDL(
    # {'outtmpl': '%(id)s%(ext)s', 'quiet': True, })
    video = ""
    with youtube_dl.YoutubeDL({'ignoreerrors': True}) as ydl:
        result = ydl.extract_info(url=playListURL,
                                  download=False)  # We just want to extract the info
        if 'entries' in result:
            # Can be a playlist or a list of videos
            video = result['entries']

            linksList = []
            # loops entries to grab each video_url
            for i, item in enumerate(video):
                video = result['entries'][i]
                # url of the video
                try:
                    url = result['entries'][i]['webpage_url']
                except TypeError:
                    continue
                linksList.append(url)
                result['entries'][i]['title']  # title of video
                result['entries'][i]['uploader']  # username of uploader
                result['entries'][i]['playlist']  # name of the playlist
                result['entries'][i]['playlist_index']
            return linksList
