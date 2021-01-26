import json
from random import randrange
import urllib.request
import socket
import urllib.error
import json
import youtube_dl


class NoWorkingProxy(Exception):
    pass


def is_working_proxy(proxy):
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy})
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        # change the URL to test here
        req = urllib.request.Request('http://www.example.com')
        urllib.request.urlopen(req)
    except urllib.error.HTTPError:
        # print('Error code: ', e.code)
        return False
    except Exception:
        # print("ERROR:", detail)
        return False
    return True


def is_blacklisted(proxy):
    test_URL = 'https://www.youtube.com/watch?v=MY-WlEVneFE'
    ydl_opts = {
        'proxy': proxy
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.extract_info(url=test_URL, download=False)
            return False
        except Exception:
            return True


def get_random_proxy():
    f = open('youtube_proxies.json', 'r')
    config = json.load(f)
    checked = []
    while True:
        proxies = list(config.get("PROXIES_LIST"))
        index = randrange(len(proxies))
        proxy = proxies[index]
        if proxies in checked:
            continue
        if proxies == checked:
            raise NoWorkingProxy
        if is_blacklisted(proxy):
            checked.append(proxy)
            continue
        return proxy


if __name__ == '__main__':
    p = get_random_proxy()
    print(p)
