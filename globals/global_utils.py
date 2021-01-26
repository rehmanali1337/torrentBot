import json
from random import randrange
import urllib.request
import socket
import urllib.error
import json


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


def get_random_proxy():
    f = open('youtube_proxies.json', 'r')
    config = json.load(f)
    proxies = list(config.get("PROXIES_LIST"))
    index = randrange(len(proxies))
    proxy = proxies[index]
    if not is_working_proxy(proxy):
        return get_random_proxy()
    return proxy


if __name__ == '__main__':
    p = get_random_proxy()
    print(p)
