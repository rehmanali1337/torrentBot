from telethon import TelegramClient
import json

f = open('config.json', 'r')
config = json.load(f)

client = TelegramClient('./sessionFiles/client',
                        config.get("API_ID"), config.get("API_HASH"))

username = '@rehmanali1337'


async def fetchID():
    en = await client.get_entity(username)
    print(en.stringify())

client.start(phone=config.get("PHONE_NUMBER"))
client.loop.create_task(fetchID())
print(
    ' Bot is up!'
)
client.run_until_disconnected()
