
import requests
from dotenv import load_dotenv
import os
import asyncio
from utils.seedr import Seedr
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
import json

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.ERROR)

f = open('config.json', 'r')
config = json.load(f)
EMAIL = config.get("EMAIL")
PASSWORD = config.get('PASSWORD')
API_ID = config.get('API_ID')
API_HASH = config.get('API_HASH')
PHONE_NUMBER = config.get('PHONE_NUMBER')
BOT_TOKEN = config.get('BOT_TOKEN')
admins = blacklist.admins

client = TelegramClient('client', API_ID, API_HASH)
bot = TelegramClient('bot', API_ID, API_HASH)
seedr = Seedr(EMAIL, PASSWORD)

if not os.path.exists('./Tmps'):
    os.mkdir('./Tmps')


async def getListOfChannels():
    shelf = shelve.open('./Tmps/channels', writeback=True)
    try:
        channelsList = shelf['channelsList']
        shelf.close()
        return channelsList
    except KeyError:
        shelf.close()
        return None


async def addChannel(channelLink):
    shelf = shelve.open('Tmps/channels', writeback=True)
    try:
        shelf['channelsList']
        shelf['channelsList'].append(channelLink)
        shelf.sync()
        shelf.close()
    except KeyError:
        shelf['channelsList'] = [channelLink]
        shelf.sync()
        shelf.close()


async def addToLog(magnetLink):
    shelf = shelve.open('./Tmps/logs', writeback=True)
    try:
        shelf['logs']
        shelf['logs'].append(magnetLink)
        shelf.sync()
        shelf.close()
    except KeyError:
        shelf['logs'] = [magnetLink]
        shelf.sync()
        shelf.close()


async def getLog():
    shelf = shelve.open('./Tmps/logs', writeback=True)
    try:
        logs = shelf['logs']
        shelf.close()
        return logs
    except KeyError:
        shelf['logs'] = []
        shelf.sync()
        shelf.close()
        return []


@bot.on(events.CallbackQuery(chats=admins, data=b'quit'))
async def exit(event):
    await event.delete()


@bot.on(events.NewMessage(pattern='/start', chats=admins))
async def botMessage(message):
    await startConv(message.peer_id)


@bot.on(events.CallbackQuery(chats=admins, data=b'mainpage'))
async def mainpage(event):
    me = await client.get_me()
    await event.delete()
    await asyncio.sleep(0.5)
    await bot.conversation(me.username).cancel_all()
    await startConv(event.query.peer)


async def startConv(peer_id):
    btns = [
        [
            Button.inline(text='Send Torrent', data=b'send'),
            Button.inline(text='Add Channel', data=b'addchannel')
        ],
        [
            Button.inline(text='Exit', data=b'quit')
        ]
    ]
    async with bot.conversation(peer_id) as conv:
        await conv.send_message('Main Menu', buttons=btns)
        try:
            event = await conv.wait_event(events.CallbackQuery())
        except asyncio.TimeoutError:
            conv.cancel()
            return
        if event.data == b'quit':
            await event.delete()
            conv.cancel()
        if event.data == b'send':
            msg = 'Please select the torrent download method!'
            btns = [
                [
                    Button.inline(text='Torrent File',
                                  data=b'torrentfile'),
                    Button.inline(text='Magnet Link', data=b'magnetlink')
                ],
                [
                    Button.inline(text='Back', data=b'mainpage')
                ]
            ]
            try:
                await event.edit(msg, buttons=btns)
            except errors.rpcerrorlist.MessageNotModifiedError:
                pass
        if event.data == b'addchannel':
            conv.cancel()


async def getEntity(channelLink):
    try:
        en = await client.get_entity(channelLink)
        return True, en
    except:
        return False, None


@bot.on(events.CallbackQuery(chats=admins, data=b'addchannel'))
async def handleAddChannel(event):
    await event.delete()
    async with bot.conversation(event.query.peer) as conv:
        btns = [Button.inline(text='Cancel', data=b'mainpage')]
        q = await conv.send_message('Enter channel link.', buttons=btns)
        try:
            resp = await conv.get_response()
        except asyncio.TimeoutError:
            await q.delete()
            conv.send_message('Timeout\nPlease try again...')
            conv.cancel()
            return
        channelLink = resp.message
        await resp.delete()
        await q.delete()
        valid, entity = await getEntity(channelLink)
        if valid:
            newChannel = {
                'id': entity.id,
                'title': entity.title,
                'link': channelLink
            }
            await addChannel(newChannel)
            btns = [
                Button.inline(text='Back', data=b'mainpage')
            ]
            await conv.send_message('Channel added to the list of channels.', buttons=btns)
        else:
            btns = [Button.inline(text='Back', data=b'mainpage')]
            await conv.send_message('The entered link is not a valid telegram channel link.', buttons=btns)


async def sendToTarget(folderId, targetChannelLink, status):
    await seedr.filterDownloadedContent(folderId)
    cover_extensions = ['jpg', 'JPG', 'jpeg', 'JPEG', 'PNG', 'png']
    folderContent = await seedr.getFolderContent(folderID=folderId)
    for f in folderContent['files']:
        extension = f.get('name').split('.')[-1].lower()
        if extension in cover_extensions:
            await status.edit('Sending the cover image ...')
            fileDownloadLink = await seedr.getDownloadLink(f['id'])
            try:
                await client.send_file(targetChannelLink, fileDownloadLink)
            except errors.rpcerrorlist.WebpageCurlFailedError:
                if not os.path.exists('./Downloads'):
                    os.mkdir(
                        './Downloads'
                    )
                downloadedFile = await seedr.downloadFile(f.get('id'), f'Downloads/{f.get("name")}')
                toSend = open(downloadedFile, 'rb')
                await client.send_file(targetChannelLink, toSend)
                os.remove(downloadedFile)

            await status.edit('Cover image sent!')
    if len(folderContent['folders']) != 0:
        for folder in folderContent['folders']:
            await sendToTarget(folder['id'], targetChannelLink, status)
    files = sorted(folderContent['files'], key=itemgetter('name'))
    helperLoop = asyncio.get_event_loop()
    for f in files:

        def pcb(uploaded, total):
            client.loop.create_task(status.edit(
                f'File: {f.get("name")}\nTotal Size : {size(total)}\nUploaded : {size(uploaded)}'))

        voicePlayable = ['flac', 'mp3', 'MP3']
        streamableFiles = ['mp4', 'MP4', 'Mp4', 'mP4']
        await status.edit(f'Sending file : {f.get("name")}')
        extension = f.get('name').split('.')[-1]
        if extension in cover_extensions:
            continue
        try:
            fileDownloadLink = await seedr.getDownloadLink(f['id'])
            while True:
                try:
                    if extension in voicePlayable:
                        await client.send_file(targetChannelLink, fileDownloadLink, supports_streaming=True, voice_note=True)
                    elif extension in streamableFiles:
                        await client.send_file(targetChannelLink, fileDownloadLink, supports_streaming=True)
                    else:
                        await client.send_file(targetChannelLink, fileDownloadLink)
                    break
                except errors.rpcerrorlist.FloodWaitError as e:
                    await asyncio.sleep(int(e.seconds) + 5)
                    continue

        except errors.rpcerrorlist.WebpageCurlFailedError:
            if not os.path.exists('./Downloads'):
                os.mkdir('./Downloads')
            downloadedFile = await seedr.downloadFile(f.get('id'), f'./Downloads/{f.get("name")}')
            if not validSize(downloadedFile):
                continue
            toSend = open(downloadedFile, 'rb')
            try:
                fastFile = await upload_file(client, toSend, fileName=f.get("name"))
            except ValueError:
                await status.edit(f'The file {f.get("name")} is too large to upload!')
                continue
            while True:
                try:
                    if extension in voicePlayable:
                        metadata = getMetadata(downloadedFile)
                        attributes = [
                            DocumentAttributeAudio(
                                int(metadata.streaminfo.duration), performer=metadata.tags.artist[0], voice=False, title=metadata.tags.title[0],)
                        ]
                        await client.send_file(targetChannelLink, fastFile, attributes=attributes, supports_streaming=True)
                    elif extension in streamableFiles:
                        duration, width, height = getVideoMetadata(
                            downloadedFile)
                        attributes = [DocumentAttributeVideo(
                            duration, width, height, supports_streaming=True)]
                        await client.send_file(targetChannelLink, fastFile, supports_streaming=True, attributes=attributes)
                    else:
                        await client.send_file(targetChannelLink, fastFile)
                    break
                except errors.rpcerrorlist.FloodWaitError as e:
                    await asyncio.sleep(int(e.seconds) + 5)
                    continue
            os.remove(downloadedFile)


def getVideoMetadata(videoLocation):
    video = VideoFileClip(videoLocation)
    duration = video.duration
    width = video.size[0]
    height = video.size[1]
    return int(duration), int(width), int(height)


def getMetadata(fileName):
    metadata = audio_metadata.load(fileName)
    return metadata


def validSize(filePath):
    stat = os.stat(filePath)
    sizeInGB = stat.st_size >> 30
    return sizeInGB <= 2


def purifyName(oldName):
    newNameChars = [c for c in oldName if c.isalnum() or c ==
                    '-' or c == '.' or c == ' ']
    newName = ''.join(newNameChars)
    return newName


async def sendFolderContent(user, targetChannelLink, uploadedTorrentFile=None, magnet=None):
    if uploadedTorrentFile == None and magnet == None:
        return
    if uploadedTorrentFile != None:
        addedTorrent = await seedr.downloadUsingTorrentFile(uploadedTorrentFile)
        os.remove(uploadedTorrentFile)
    if magnet != None:
        addedTorrent = await seedr.downloadUsingMagnet(magnet)
    try:
        status = await bot.send_message(user, f'Downloading the torrent : {addedTorrent["title"]}')
    except KeyError:
        status = await bot.send_message(user, f'Could not download torrent for some reason!\nPlease Try again!')
        return
    while True:
        downloadedTorrent = await seedr.getTorrentData(addedTorrent['user_torrent_id'])
        if downloadedTorrent.get('progress') != 101:
            await asyncio.sleep(10)
            continue
        break
    # downloadedTorrent = await seedr.waitUntilDownloadComplete(addedTorrent['user_torrent_id'])
    await status.edit('Downloading complete!')
    createdFolderId = downloadedTorrent['folder_created']
    await sendToTarget(createdFolderId, targetChannelLink, status)
    await status.edit('Deleting torrent from seedr.cc ...')
    await seedr.deleteFolder(createdFolderId)
    await status.edit('Torrent deleted from seedr.cc!')
    await status.edit('All files have been sent successfully!')
    await asyncio.sleep(15)
    await status.delete()


def getMagnetLink(filePath):
    try:
        torrent = Torrent.from_file(filePath)
        return torrent.magnet_link
    except FileNotFoundError:
        return None


@bot.on(events.CallbackQuery(chats=admins, data=b'torrentfile'))
async def handleTorrentFile(event):
    async with bot.conversation(event.query.user_id) as conv:
        await event.delete()
        btns = [
            Button.inline(text='Cancel', data=b'mainpage')
        ]
        q = await conv.send_message('Send the target .torrent file.', buttons=btns)
        response = await conv.get_response()
        if not os.path.exists('./Torrents'):
            os.mkdir('./Torrents')
        uploadedTorrentFile = await response.download_media()
        await response.delete()
        await q.delete()
        magnetLink = getMagnetLink(uploadedTorrentFile)
        logs = await getLog()
        if magnetLink in logs:
            btns = [
                Button.inline(text='Yes', data=b'yes'),
                Button.inline(text='No', data=b'No')
            ]
            await conv.send_message('This torrent has already been sent!\nDo you want to Re-send?', buttons=btns)
            event = await conv.wait_event(events.CallbackQuery())
            if event.data == b'no':
                btns = [
                    Button.inline(text='Back', data=b'mainpage')
                ]
                await event.edit('Go Back', buttons=btns)
                conv.cancel()
            if event.data == b'yes':
                await event.delete()
        channelsList = await getListOfChannels()
        channels = []
        if channelsList != None:
            for channel in channelsList:
                channels.append([Button.inline(
                    text=channel['title'], data=str(channel['id']).encode())])
        channels.append([Button.inline(text='Cancel', data=b'mainpage')])
        if len(channels) != 1:
            await conv.send_message('Choose a channel?', buttons=channels)
        else:
            await conv.send_message('No channels added!\nPlease add channels first!', buttons=[Button.inline(text='Back', data=b'mainpage')])
        event = await conv.wait_event(events.CallbackQuery())
        if event.data != b'mainpage':
            await event.delete()
            targetChannelId = int(event.data.decode('utf-8'))
            for ch in channelsList:
                if ch['id'] == targetChannelId:
                    targetChannelLink = ch['link']

            client.loop.create_task(sendFolderContent(
                event.query.user_id, targetChannelLink, uploadedTorrentFile=uploadedTorrentFile))
            await asyncio.sleep(1)
            await addToLog(magnetLink)
            await conv.send_message(
                'You can now go to the main menu!', buttons=[Button.inline(text='Main Menu', data=b'mainpage')]
            )
            conv.cancel()
        else:
            conv.cancel()


@bot.on(events.CallbackQuery(chats=admins, data='magnetlink'))
async def handleTorrentLink(event):
    async with bot.conversation(event.query.user_id) as conv:
        await event.delete()
        btns = [
            Button.inline('Cancel', data=b'mainpage')
        ]
        q = await conv.send_message('Please enter the magnet link of the torrent!', buttons=btns)
        try:
            response = await conv.wait_event(events.NewMessage)
        except asyncio.CancelledError:
            conv.cancel()
        magnetLink = response.message.message
        await q.delete()
        await response.delete()
        logs = await getLog()
        if magnetLink in logs:
            btns = [
                Button.inline(text='Yes', data=b'yes'),
                Button.inline(text='No', data=b'no')
            ]
            await conv.send_message('This torrent has already been sent!\nDo you want to re-send?', buttons=btns)
            event = await conv.wait_event(events.CallbackQuery)
            if event.data == b'no':
                btns = [
                    Button.inline(text='Back', data=b'mainpage')
                ]
                await event.edit('Go Back', buttons=btns)
                conv.cancel()
            if event.data == b'yes':
                await event.delete()
        channelsList = await getListOfChannels()
        channels = []
        if channelsList != None:
            for channel in channelsList:
                channels.append([Button.inline(
                    text=channel['title'], data=str(channel['id']).encode())])
        channels.append([Button.inline(text='Cancel', data=b'mainpage')])
        if len(channels) != 1:
            await conv.send_message('Choose a channel?', buttons=channels)
        else:
            await conv.send_message('No channels added!\nPlease add channels first!', buttons=[Button.inline(text='Back', data=b'mainpage')])
        event = await conv.wait_event(events.CallbackQuery())
        if event.data != b'mainpage':
            await event.delete()
            targetChannelId = int(event.data.decode('utf-8'))
            for ch in channelsList:
                if ch['id'] == targetChannelId:
                    targetChannelLink = ch['link']

            client.loop.create_task(sendFolderContent(
                event.query.user_id, targetChannelLink, magnet=magnetLink))
            await addToLog(magnetLink)
            await conv.send_message(
                'You can now go to the main menu!', buttons=[Button.inline(text='Main Menu', data=b'mainpage')]
            )
            conv.cancel()
        else:
            conv.cancel()


bot.start(bot_token=BOT_TOKEN)
client.start(phone=PHONE_NUMBER)
print(' Bot is running ...')
bot.run_until_disconnected()
