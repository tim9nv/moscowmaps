#!/usr/bin/env python3
"""Поисковые правки поверх собранных страниц (идемпотентно). Запускать последним, после night_theme.py.

- короткие title/description у страниц районов (Яндекс режет title после ~70 знаков, description после ~160);
- title, description и og-теги у вкладок;
- короткие title у парков, различимые title у парков-тёзок;
- ссылки на главную и на разделы ведут на адрес папки («../../»), а не на «index.html»: так у страницы один адрес;
- og:image (картинки 1200×630 из assets/og/, делает tools/og_images.py) там, где её нет.
"""
import glob, html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.mskatlas.ru'
os.chdir(ROOT)

TABS = {
    'housing.html': ('Цены на квартиры по районам Москвы — карта 2026',
                     'Сколько стоит квадратный метр на вторичке в каждом из 125 районов Москвы: карта, рейтинг от дешёвых к дорогим, данные по свежим объявлениям.'),
    'ecology.html': ('Экология районов Москвы — карта загрязнения 2026',
                     'Экологический балл каждого района Москвы: заводы, ТЭЦ, магистрали и замеры воздуха на карте. Самые чистые и самые загрязнённые районы.'),
    'transport.html': ('Транспорт в районах Москвы: метро и время до центра',
                       'Метро, МЦК и МЦД в каждом районе Москвы: сколько ехать до центра и идти до станции. Карта и рейтинг транспортной доступности.'),
    'social.html': ('Школы и поликлиники по районам Москвы на карте',
                    'Школы, детские сады, поликлиники и больницы в каждом районе Москвы: сколько их на жителей и где нагрузка выше. Карта всех 125 районов.'),
    'parks.html': ('Парки и прогулки по районам Москвы — карта зелени',
                   'Парки, лесопарки и достопримечательности Москвы на карте: доля зелени и парки на жителя в каждом районе, страницы парков с тропами.'),
    'sport.html': ('Спорт в районах Москвы: бассейны, фитнес, площадки',
                   'Бассейны, спорткомплексы, фитнес-клубы, площадки и воркауты в каждом районе Москвы на жителей. Где удобнее всего заниматься спортом.'),
    'climate.html': ('Рельеф и микроклимат районов Москвы на карте',
                     'Где в Москве выше и ниже, теплее и сырее: рельеф, высоты, остров тепла, влажность, ветер и туманы по каждому району.'),
    'new-moscow.html': ('Новая Москва на карте: поселения, экология, транспорт',
                        'Поселения Новомосковского и Троицкого округов на карте: рельеф, экология и транспорт. Чем Новая Москва отличается от старой.'),
    'index.html': (None, None),
}
OG = {'index.html': 'home', 'housing.html': 'housing', 'ecology.html': 'ecology', 'transport.html': 'transport',
      'social.html': 'social', 'parks.html': 'parks', 'sport.html': 'sport', 'climate.html': 'climate',
      'new-moscow.html': 'new-moscow', 'reyting/index.html': 'reyting', 'rayon/index.html': 'home'}
PARK_TWINS = {  # два разных участка с одним именем в OpenStreetMap
    'parks/park-nikulino/index.html': 'Парк Никулино у памятника Скобелеву (Тропарево-Никулино)',
    'parks/park-nikulino-192/index.html': 'Парк Никулино у храма Архангела Михаила (Тропарево-Никулино)',
    'parks/park-v-poyme-reki-gorodni/index.html': 'Парк в пойме реки Городни (Братеево): карта',
    'parks/park-v-poyme-reki-gorodni-145/index.html': 'Парк в пойме Городни (Братеево и Зябликово): карта',
}
DESC_OVERRIDE = {
    'rayon/index.html': 'Все 125 районов Москвы по округам. У каждого своя страница: цена метра, экология, транспорт, школы, поликлиники и парки.',
    'reyting/transport/index.html': None,
}
TITLE_OVERRIDE = {
    'reyting/transport/index.html': 'Транспортная доступность районов Москвы — рейтинг 2026',
    'reyting/dlya-semi-s-detmi/index.html': 'Лучшие районы Москвы для семьи с детьми — рейтинг 2026',
}

E = lambda s: html.escape(s, quote=True)


def set_tag(s, kind, value):
    """kind: title | description | og:title | og:description | og:url | og:image | og:type"""
    v = E(value)
    if kind == 'title':
        return re.sub(r'<title>[^<]*</title>', f'<title>{v}</title>', s, count=1)
    if kind == 'description':
        if re.search(r'<meta name="description" content="[^"]*">', s):
            return re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{v}">', s, count=1)
        return s.replace('</title>', f'</title>\n<meta name="description" content="{v}">', 1)
    pat = rf'<meta property="{kind}" content="[^"]*">'
    tag = f'<meta property="{kind}" content="{v}">'
    if re.search(pat, s):
        return re.sub(pat, tag, s, count=1)
    return s.replace('</head>', f'{tag}\n</head>', 1)


def get(s, kind):
    if kind == 'title':
        m = re.search(r'<title>([^<]*)</title>', s)
    elif kind == 'description':
        m = re.search(r'<meta name="description" content="([^"]*)">', s)
    else:
        m = re.search(rf'<meta property="{kind}" content="([^"]*)">', s)
    return html.unescape(m.group(1)) if m else None


def district(s):
    t = get(s, 'title') or ''
    m = re.match(r'Район (.+) \(([^)]+)\): цены на квартиры', t)
    if not m:
        return s  # уже исправлено или другой шаблон
    n, o = m.groups()
    d = get(s, 'description') or ''
    title = f'{n} ({o}): плюсы и минусы, цены, экология'
    if len(title) > 70:
        title = f'{n} ({o}): плюсы и минусы, цены'
    hp = re.search(r'около ([\d  ]+) тыс\. ₽', d)
    eco = re.search(r'(\d+)-е место по чистоте', d)
    tc = re.search(r'до центра около (\d+) мин', d)
    parts = []
    if hp: parts.append(f'метр ~{hp.group(1).strip()} тыс. ₽')
    if eco: parts.append(f'{eco.group(1)}-е место из 125 по чистоте')
    if tc: parts.append(f'до центра {tc.group(1)} мин')
    desc = f'Район {n} ({o}): ' + ', '.join(parts) + '. Плюсы и минусы, школы, парки, транспорт.'
    if len(desc) > 160:
        desc = f'{n} ({o}): ' + ', '.join(parts) + '. Плюсы и минусы, школы, парки.'
    for k, v in (('title', title), ('og:title', title), ('description', desc), ('og:description', desc)):
        s = set_tag(s, k, v)
    return s


def home_links(s):
    # href="../../index.html" → href="../../", href="index.html" → href="./"
    s = re.sub(r'href="((?:\.\./)+)index\.html"', r'href="\1"', s)
    s = re.sub(r'href="index\.html"', 'href="./"', s)
    return s


def og_image(s, name):
    p = f'assets/og/{name}.jpg'
    if not os.path.exists(p):
        return s
    url = f'{BASE}/{p}'
    if get(s, 'og:image') == url:
        return s
    s = set_tag(s, 'og:image', url)
    if 'twitter:card' not in s:
        s = s.replace('</head>', '<meta name="twitter:card" content="summary_large_image">\n</head>', 1)
    return s


def main():
    changed = 0
    files = sorted(set(glob.glob('*.html') + glob.glob('*/index.html') + glob.glob('*/*/index.html')))
    for f in files:
        if os.path.basename(f).startswith(('yandex_', 'google')):
            continue
        s0 = s = open(f, encoding='utf-8').read()
        s = home_links(s)
        if f.startswith('rayon/') and f.count('/') == 2 and not f.startswith('rayon/gerb'):
            s = district(s)
        if f in TABS and TABS[f][0]:
            t, d = TABS[f]
            url = f'{BASE}/{f}'
            for k, v in (('title', t), ('description', d), ('og:title', t), ('og:description', d), ('og:url', url), ('og:type', 'website')):
                s = set_tag(s, k, v)
            if 'og:site_name' not in s:
                s = s.replace('</head>', '<meta property="og:site_name" content="Атлас Москвы">\n<meta property="og:locale" content="ru_RU">\n</head>', 1)
        if f in DESC_OVERRIDE and DESC_OVERRIDE[f]:
            s = set_tag(s, 'description', DESC_OVERRIDE[f])
        if f in TITLE_OVERRIDE:
            s = set_tag(s, 'title', TITLE_OVERRIDE[f])
            if get(s, 'og:title'):
                s = set_tag(s, 'og:title', TITLE_OVERRIDE[f])
        if f in PARK_TWINS:
            s = set_tag(s, 'title', PARK_TWINS[f])
            s = set_tag(s, 'og:title', PARK_TWINS[f])
        elif f.startswith('parks/'):
            d = get(s, 'description') or ''
            if len(d) > 160 and d.endswith(' Геолокация «Я на карте».'):
                d = d[:-len(' Геолокация «Я на карте».')]
                s = set_tag(s, 'description', d)
                if get(s, 'og:description'):
                    s = set_tag(s, 'og:description', d)
            t = get(s, 'title') or ''
            if len(t) > 70 and t.endswith(' — карта и что посмотреть'):
                t2 = t[:-len(' — карта и что посмотреть')] + ': карта'
                if len(t2) > 70:
                    t2 = t[:-len(' — карта и что посмотреть')]
                s = set_tag(s, 'title', t2)
                if get(s, 'og:title'):
                    s = set_tag(s, 'og:title', t2)
        if f in OG:
            s = og_image(s, OG[f])
        elif f.startswith('reyting/'):
            s = og_image(s, 'reyting')
        elif f.startswith('zagorod/'):
            slug = f.split('/')[1] if f.count('/') == 2 else 'zagorod'
            s = og_image(s, 'zagorod-' + slug if slug != 'zagorod' else 'zagorod')
        elif f.startswith('parks/'):
            # своей картинки у парка нет — общая картинка вкладки «Парки», чтобы ссылка в мессенджере была с превью
            s = og_image(s, 'parks')
        if s != s0:
            open(f, 'w', encoding='utf-8').write(s)
            changed += 1
    print('seo_fix: изменено страниц', changed)


if __name__ == '__main__':
    main()
