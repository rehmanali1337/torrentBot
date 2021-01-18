import json
import asyncio
from models.mega import Mega


class MegaAutomator:
    def __init__(self, threadName, bot, client, queue, tracker):
        f = open('config.json', 'r')
        self.threadName = threadName
        self.config = json.load(f)
        self.bot = bot
        self.tracker = tracker
        self.client = client
        self.queue = queue
        self.loop = asyncio.new_event_loop()

    def start(self):
        self.loop.run_until_complete(self.main())

    async def main(self):
        while True:
            try:
                print(f'Mega Thread {self.threadName} waiting for job ..')
                job = self.queue.get()
                self.targetChannelLink = job.get('channelLink')
                self.userID = job.get('userID')
                mega = Mega(job.get("megaLink"), self.targetChannelLink,
                            self.userID, self.bot, self.client, self.tracker)
                await mega.send()
                self.queue.task_done()
            except Exception as e:
                print('Exception in Mega thread!')
                print(e)
