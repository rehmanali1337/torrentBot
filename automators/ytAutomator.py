from models.ytube import YTube, getVideosLinks
import asyncio
import json
from globals.global_utils import NoWorkingProxy


class YTAutomator:
    def __init__(self, threadName, bot, client, queue, tracker):
        self.threadName = threadName
        f = open('config.json', 'r')
        self.config = json.load(f)
        self.bot = bot
        self.client = client
        self.tracker = tracker
        self.queue = queue
        self.loop = asyncio.new_event_loop()
        self.ts = asyncio.run_coroutine_threadsafe

    def start(self):
        self.loop.run_until_complete(self.main())

    async def main(self):
        while True:
            print(f'Youtube Thread {self.threadName} waiting for job ..')
            try:
                job = self.queue.get()
                self.job = job
                try:
                    if job.get("linkType") == 'playlist':
                        linksList = getVideosLinks(job.get("URL"))
                        for link in linksList:
                            y = YTube(self.bot, self.client, link,
                                      'tiny', self.job.get("userID"),
                                      self.job.get("channel"), self.tracker)
                            await y.sendAudio()
                        self.queue.task_done()
                        continue
                    y = YTube(self.bot, self.client, job.get(
                        "URL"), job.get("resolution"), job.get("userID"),
                        job.get("channel"), self.tracker)
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
                except NoWorkingProxy:
                    self.ts(self.bot.send_message(job.get("userID"),
                                                  'No working proxy found for youtube!\nPlease try again later!'),
                            self.bot.loop).result()
                continue
            except Exception as e:
                print('Got exception in YT Automator!')
                print(e)
                continue
