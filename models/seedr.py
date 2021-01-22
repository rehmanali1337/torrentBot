import requests
import os
import subprocess
import asyncio
import json
import blacklist
from random import randrange


class Seedr:
    def __init__(self, magnet=None, torrentFile=None):
        f = open('config.json')
        self.config = json.load(f)
        self.magnet = magnet
        self.torrentFile = torrentFile
        self.auth = (self.config.get("EMAIL"), self.config.get("PASSWORD"))
        self.baseURL = 'https://www.seedr.cc/rest'

    async def getFolderContent(self, folderID=None):
        URL = f'{self.baseURL}/folder/{folderID}'
        while True:
            try:
                res = requests.get(URL,
                                   auth=self.auth)
                try:
                    return res.json()
                except json.decoder.JSONDecodeError:
                    continue
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def getUserData(self):
        URL = f'{self.baseURL}/user'
        while True:
            try:
                userData = requests.get(URL, auth=self.auth)
                return userData.json()
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue
            except TimeoutError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def getHLSURL(self, fileID):
        URL = f'{self.baseURL}/file/{fileID}/hls'
        while True:
            try:
                requests.get(URL, auth=self.auth, allow_redirects=True)
                break
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def getDownloadLink(self, fileID):
        URL = f'{self.baseURL}/file/{fileID}'
        while True:
            try:
                res = requests.get(URL, auth=self.auth, allow_redirects=False)
                return res.headers.get('Location')
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def getTorrentData(self, torrentID):
        URL = f'{self.baseURL}/torrent/{torrentID}'
        while True:
            try:
                data = requests.get(URL, auth=self.auth)
                return data.json()
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue
            except json.decoder.JSONDecodeError:
                continue

    async def downloadUsingMagnet(self, magnetLink):
        URL = f'{self.baseURL}/torrent/magnet'
        params = {
            'magnet': magnetLink
        }
        while True:
            try:
                added = requests.post(URL, data=params,
                                      auth=self.auth).json()
                return added
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def downloadUsingTorrentFile(self, fileName):
        URL = f'{self.baseURL}/torrent/url'
        params = {
            'torrent_file': open(fileName, 'rb')
        }
        while True:
            try:
                added = requests.post(
                    URL, files=params, auth=self.auth).json()
                return added
            except requests.exceptions.ConnectionError:
                # await asyncio.sleep(randrange(2, 4))
                continue

    async def waitUntilDownloadComplete(self, torrentID):
        while True:
            torrent = await self.getTorrentData(torrentID)
            if torrent.get('progress') != 101:
                await asyncio.sleep(10)
                continue
            break
        return torrent

    async def filterDownloadedContent(self, folderID):
        content = await self.getFolderContent(folderID=folderID)
        files = content.get('files')
        for f in files:
            extension = f.get('name').split('.')[-1]
            if extension in blacklist.blacklistedFiles:
                # Delete the file
                await self.deleteFile(f.get('id'))

    async def deleteFile(self, fileID):
        URL = f'{self.baseURL}/file/{fileID}'
        while True:
            try:
                requests.delete(URL, auth=self.auth)
                break
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def deleteFolder(self, folderId):
        URL = f'{self.baseURL}/folder/{folderId}'
        while True:
            try:
                requests.delete(URL, auth=self.auth)
                break
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def renameFile(self, fileID, newName):
        URL = f'{self.baseURL}/{fileID}/rename'
        params = {
            'rename_to': newName
        }
        while True:
            try:
                requests.post(URL, params=params, auth=self.auth)
                break
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue

    async def deleteTorrent(self, torrentID):
        URL = f'{self.baseURL}/torrent/{torrentID}'
        res = requests.delete(URL, auth=self.auth)
        return res

    async def downloadFile(self, fileID, fileName):
        URL = f'{self.baseURL}/file/{fileID}'
        while True:
            try:
                with requests.get(URL, stream=True, auth=self.auth) as r:
                    r.raise_for_status()
                    with open(fileName, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            # if chunk:
                            f.write(chunk)
                return fileName
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(randrange(2, 4))
                continue
