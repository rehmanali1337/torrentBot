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
    f = open('nord_ips.json', 'r')
    config = json.load(f)
    proxies = list(config.get("PROXIES_LIST"))
    checked = []
    username = config.get("USERNAME")
    password = config.get("PASSWORD")
    port = 1080
    while True:
        index = randrange(len(proxies))
        ip = proxies[index]
        currentProxy = f'socks5://{username}:{password}@{ip}:{port}'
        if proxies in checked:
            continue
        if is_blacklisted(currentProxy):
            checked.append(currentProxy)
            continue
        if proxies == checked:
            raise NoWorkingProxy
        return currentProxy


if __name__ == '__main__':
    get_random_proxy()
