"""Сообщить Яндексу (IndexNow) обо всех страницах из sitemap.xml. Запускать после публикации."""
import re, json, urllib.request
KEY = "324e282c3bce892dd7bb618fbc1dc286"
urls = re.findall(r"<loc>(.*?)</loc>", open("sitemap.xml", encoding="utf-8").read())
body = json.dumps({"host": "www.mskatlas.ru", "key": KEY,
                   "keyLocation": f"https://www.mskatlas.ru/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://yandex.com/indexnow", body, {"Content-Type": "application/json; charset=utf-8"})
print(len(urls), "URL →", urllib.request.urlopen(req).status)
