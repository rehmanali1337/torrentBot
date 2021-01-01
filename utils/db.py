from pymongo import MongoClient


class DB:
    def __init__(self):
        client = MongoClient()
        self.db = client.mainDB
        self.channels = self.db.channels
        self.users = self.db.users

    async def getChannelsList(self):
        channels = self.channels.find({})
        if channels.count() == 0:
            print('Count is 0')
            return []
        finalList = []
        for ch in channels:
            finalList.append(ch)
        return finalList

    async def addNewChannel(self, channelLink: str, channelTitle: str, channelID: int):
        channel = {
            'id': channelID,
            'link': channelLink,
            'title': channelTitle,
        }
        self.channels.insert_one(channel)

    async def removeChannelByLink(self, channelLink):
        self.channels.delete_one({'link': channelLink})

    async def channelExists(self, channelID):
        pass

    async def getAllChannels(self):
        channels = self.channels.find({})
        return [channel for channel in channels]

    async def getChannelLinkByID(self, channelID):
        channel = self.channels.find_one({'id': channelID})
        return channel['link'] if channel else None

    async def addUser(self, userID: int, username: str = None,
                      firstName: str = None, lastName: str = None):
        self.users.insert_one({
            'id': userID,
            'firstName': firstName,
            'lastName': lastName,
            'username': username,
        })

    async def userExists(self, userID):
        user = self.users.find_one({'id': userID})
        return True if user else False

    async def removeUser(self, userID):
        self.users.delete_one({'id': userID})

    def getAllUserIDs(self):
        users = self.users.find({})
        return [user['id'] for user in users]

    async def getAllUsers(self):
        users = self.users.find({})
        users = [user for user in users]
        return users
