import os


def setup():
    dirs = [
        './Tmps', './sessionFiles', './Downloads', './Torrents'
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.mkdir(d)
