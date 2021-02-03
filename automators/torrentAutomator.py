import logging
import os
import asyncio
from models.torrent import Torrenter


class TorrentAutomator:
    def __init__(self, threadName, bot, client, queue, tracker):
        self.threadName = threadName
        self.bot = bot
        self.queue = queue
        self.client = client
        self.tracker = tracker
        self.loop = asyncio.new_event_loop()

    def start(self):
        self.loop.run_until_complete(self.main())

    async def main(self):
        while True:
            print(
                f'Torrent Thread {self.threadName} waiting for torrent ...')
            try:
                job = self.queue.get()
                self.job = job
                self.status = None
                self.userID = job.get('userID')
                self.targetChannelLink = job.get("targetChannelLink")
                downloadType = job.get('downloadType')
                if downloadType == 'file':
                    t = Torrenter(self.client, self.bot,
                                  fileLocation=job.get("fileLocation"),
                                  userID=job.get("userID"),
                                  targetChannelLink=job.get(
                                      "targetChannelLink"),
                                  tracker=self.tracker)
                    await t.handleTorrentFile()
                    try:
                        os.remove(job.get('fileLocation'))
                    except FileNotFoundError:
                        pass
                    self.queue.task_done()
                    continue
                if downloadType == 'magnet':
                    t = Torrenter(self.client, self.bot,
                                  magnet=job.get("magnet"),
                                  userID=job.get("userID"),
                                  targetChannelLink=job.get(
                                      "targetChannelLink"),
                                  tracker=self.tracker)
                    await t.handleMagnetLink()
                    self.queue.task_done()
                    continue
            except Exception as e:
                print('\nGot exception in torrent Automator!\n')
                print(e)
                continue
