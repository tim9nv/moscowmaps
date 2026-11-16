#!/usr/bin/env python3
"""Проверка поисковых директив: python3 tools/check_indexing.py.

Не меняет файлы и ничего не отправляет поисковикам.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://www.mskatlas.ru/'


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.canonical, self.robots, self.redirects = [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonical.append(a.get('href', ''))
        if tag == 'meta':
            if a.get('name', '').lower() in ('robots', 'googlebot'):
                self.robots.extend(a.get('content', '').lower().replace(',', ' ').split())
            if a.get('http-equiv', '').lower() == 'refresh':
                self.redirects.append(a.get('content', ''))

    @property
    def excluded(self):
        return bool({'noindex', 'none'} & set(self.robots))


def main():
    urls = [e.text for e in ET.parse(ROOT / 'sitemap.xml').iter()
            if e.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}loc']
    errors = [f'Повтор в sitemap: {u}' for u, n in Counter(urls).items() if n > 1]
    if not urls:
        errors.append('Sitemap не содержит адресов')
    sitemap = set(urls)
    for u in urls:
        if not u.startswith(BASE) or urlsplit(u).query or urlsplit(u).fragment:
            errors.append(f'Неканонический адрес в sitemap: {u}')
            continue
        path = urlsplit(u).path.lstrip('/')
        f = ROOT / (path + 'index.html' if not path or path.endswith('/') else path)
        if not f.is_file():
            errors.append(f'Нет файла для {u}')
            continue
        h = Head(f.read_text(encoding='utf-8'))
        if h.excluded or h.redirects:
            errors.append(f'В sitemap закрытая страница или переадресация: {u}')
        if h.canonical != [u]:
            errors.append(f'Canonical не совпадает с sitemap: {u}: {h.canonical}')
    excluded, redirects = [], []
    for f in sorted(ROOT.rglob('*.html')):
        h = Head(f.read_text(encoding='utf-8'))
        name = f.relative_to(ROOT).as_posix()
        if h.excluded:
            excluded.append(name)
        if h.redirects:
            redirects.append(name)
            if h.excluded:
                errors.append(f'noindex на переадресации: {name}')
            if len(h.canonical) != 1 or h.canonical[0] not in sitemap:
                errors.append(f'Цель canonical переадресации отсутствует в sitemap: {name}')
            for refresh in h.redirects:
                delay, sep, target = refresh.partition(';')
                if delay.strip() != '0' or not sep or not target.strip().lower().startswith('url='):
                    errors.append(f'Не мгновенная переадресация: {name}')
                    continue
                source = urljoin(BASE, name.removesuffix('index.html'))
                dest = urljoin(source, target.strip()[4:].strip(' \"\''))
                if h.canonical != [dest]:
                    errors.append(f'Разные цели refresh и canonical: {name}')
    print(f'Sitemap: {len(urls)} адресов; переадресаций: {len(redirects)}; noindex: {len(excluded)}')
    for name in excluded:
        print(f'  noindex (проверить намеренность): {name}')
    for error in errors:
        print('ОШИБКА:', error)
    print('Проверка пройдена' if not errors else f'Ошибок: {len(errors)}')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
