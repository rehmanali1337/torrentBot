from models.ytube import YTube, getVideosLinks
import asyncio
import json


class YTAutomator:
    def __init__(self, threadName, bot, client, queue):
        self.threadName = threadName
        f = open('config.json', 'r')
        self.config = json.load(f)
        self.bot = bot
        self.client = client
        self.queue = queue
        self.loop = asyncio.new_event_loop()

    def start(self):
        self.loop.run_until_complete(self.main())

    async def main(self):
        while True:
            print(f'Youtube Thread {self.threadName} waiting for job ..')
            job = self.queue.get()
            self.job = job
            if job.get("linkType") == 'playlist':
                linksList = getVideosLinks(job.get("URL"))
                for link in linksList:
                    y = YTube(self.bot, self.client, link,
                              'tiny', self.job.get("userID"), self.job.get("channel"))
                    await y.sendAudio()
                self.queue.task_done()
                continue
            y = YTube(self.bot, self.client, job.get(
                "URL"), job.get("resolution"), job.get("userID"),
                job.get("channel"))
            if job.get('resolution') != 'tiny':
                await y.sendVideo()
                await y.delete()
                self.queue.task_done()
                continue
            await y.sendAudio()
            try:
                await y.delete()
            except FileNotFoundError:
                pass
            self.queue.task_done()
