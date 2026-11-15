"""Быстрые переходы на страницах поездок. Используется build_zagorod.py.

Можно применить к уже собранным страницам без пересборки данных и оформления:
python tools/zagorod_navigation.py. Повторный запуск ничего не меняет.
"""
from pathlib import Path
import re

SECTIONS = {
    'Как добраться': ('getting-there', 'Как добраться'),
    'Маршрут на день': ('route', 'Карта и маршрут'),
    'Маршрут на выходные': ('route', 'Карта и маршрут'),
    'Что посмотреть подробно': ('sights', 'Что посмотреть'),
    'Сколько стоит день': ('budget', 'Бюджет'),
    'Где поесть': ('food', 'Где поесть'),
    'Что учесть': ('tips', 'Что учесть'),
}


def add_navigation(page):
    page = re.sub(r'<!--ZG-CONTENTS-->.*?<!--ZG-CONTENTS-END-->', '', page, flags=re.S)
    page = re.sub(r'<link rel="stylesheet" href="../trip-navigation.css[^\"]*">', '', page)
    page = re.sub(r'<script defer src="../navigation.js[^\"]*"></script>', '', page)
    links = []
    used_anchors = set()
    used_labels = set()

    def section(match):
        tag, title = match.groups()
        if title not in SECTIONS:
            return match.group(0)
        anchor, label = SECTIONS[title]
        existing = re.search(r'\bid="([^"]+)"', tag)
        if existing:
            anchor = existing.group(1)
        base = anchor
        suffix = 2
        while anchor in used_anchors:
            anchor = f'{base}-{suffix}'
            suffix += 1
        used_anchors.add(anchor)
        if existing:
            tag = tag.replace(f'id="{existing.group(1)}"', f'id="{anchor}"', 1)
        else:
            tag = tag[:-1] + f' id="{anchor}">'
        if label not in used_labels:
            links.append(f'<a href="#{anchor}">{label}</a>')
            used_labels.add(label)
        return tag + '<h2>' + title + '</h2>'

    page = re.sub(r'(<section\b[^>]*>)<h2>([^<]+)</h2>', section, page)
    if '<footer class="zg-src"' in page:
        page = page.replace('<footer class="zg-src">', '<footer class="zg-src" id="sources">', 1)
        links.append('<a href="#sources">Источники</a>')
    if not links:
        return page
    nav = ('<!--ZG-CONTENTS--><nav class="zg-contents" aria-label="В этой поездке">'
           '<span>В этой поездке</span><div>' + ''.join(links) + '</div></nav><!--ZG-CONTENTS-END-->')
    page = re.sub(r'(<header class="hero[^\"]*">.*?</header>)', lambda m: m[1] + nav, page, count=1, flags=re.S)
    page = page.replace('</head>', '<link rel="stylesheet" href="../trip-navigation.css?v=20261115-nav"><script defer src="../navigation.js?v=20261115-nav"></script></head>', 1)
    return page


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    count = 0
    for path in (root / 'zagorod').glob('*/index.html'):
        before = path.read_text(encoding='utf-8')
        if '"@type": "TouristAttraction"' not in before:
            continue
        after = add_navigation(before)
        if after != before:
            path.write_text(after, encoding='utf-8')
            count += 1
    print('Навигация добавлена на страницах:', count)
