from telethon import events, types, functions
from telethon.tl.custom import Button
import json


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def checkButton(checkList):

        def inner(payload):
            button = payload.message.message
            if button in checkList or button == '/start':
                return True
            return False
        return inner

    @staticmethod
    def checkFile(payload):
        if payload.message.media != None:
            return True
        return False

    @staticmethod
    def checkFileOrButton(checkList):
        def inner(payload):
            button = payload.message.message
            if button in checkList or button == '/start':
                return True
            if payload.message.media != None:
                return True
            return False
        return inner

    @staticmethod
    def createButton(btnText: str):
        return Button.text(btnText, single_use=True)

    @staticmethod
    def createDataButton(text, data):
        return Button.inline(text=text, data=data.encode())

    @staticmethod
    async def rm(messages: list):
        for m in messages:
            await m.delete()

    @staticmethod
    def checkDataButton(dataList):
        def inner(payload):
            if payload.data.decode() in dataList:
                return True
            return False
        return inner

    @staticmethod
    def filterFormats(formats):
        filtered = []
        for orig_format in formats:
            if orig_format == 'tiny':
                if 'tiny' in filtered:
                    continue
                filtered.append(orig_format)
                continue
            try:
                f = int(orig_format.replace('p', ''))
            except ValueError:
                continue
            if f >= 720:
                if orig_format in filtered:
                    continue
                filtered.append(orig_format)
        return filtered
