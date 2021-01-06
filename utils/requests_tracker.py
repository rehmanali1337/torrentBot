from datetime import datetime as dt
import logging


class Tracker:
    def __init__(self):
        self.loginfo = logging.getLogger(' Request Tracker ').info

    def request_allowed(self, userID) -> bool:
        userID = str(userID)
        if not hasattr(self, userID):
            ctimer = dt.now().today().ctime()
            setattr(self, userID, ctimer)
            self.loginfo(f' Request allowed because {userID} not exist')
            return True
        ctimer = dt.now().today().ctime()
        user = getattr(self, userID)
        if user == ctimer:
            print(f' Request not allowed for : {userID}')
            return False
        setattr(self, userID, ctimer)
        print(f' Request allowed for : {userID}')
        return True
