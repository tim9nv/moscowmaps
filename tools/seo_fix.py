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
                     'Цены за квадратный метр на вторичном рынке в 125 районах Москвы. Карта и рейтинг по срезу объявлений Циана от 7 ноября 2026 года.'),
    'ecology.html': ('Экология Москвы по районам — карта и рейтинг',
                     'Сравните экологическую нагрузку в 125 районах Москвы. Карта, выбор района, крупные источники загрязнения и ссылка на замеры Мосэкомониторинга.'),
    'transport.html': ('Транспорт в районах Москвы: метро и время до центра',
                       'Метро, МЦК и МЦД в каждом районе Москвы: сколько ехать до центра и идти до станции. Карта и рейтинг транспортной доступности.'),
    'social.html': ('Школы и поликлиники по районам Москвы на карте',
                    'Школы, детские сады, поликлиники и больницы на 10 тысяч жителей. Карта 125 районов Москвы и ссылки на городские сервисы.'),
    'parks.html': ('Парки и прогулки по районам Москвы — карта зелени',
                   'Парки, лесопарки и достопримечательности Москвы на карте: доля зелени и парки на жителя в каждом районе, страницы парков с тропами.'),
    'sport.html': ('Спорт в районах Москвы: бассейны, фитнес, площадки',
                   'Бассейны, спорткомплексы, фитнес-клубы, площадки и воркауты в каждом районе Москвы на жителей. Где удобнее всего заниматься спортом.'),
    'climate.html': ('Рельеф и микроклимат Москвы — карта высот Copernicus',
                     'Рельеф Москвы по Copernicus DEM, включая Зеленоград и Новую Москву. Высоты, горизонтали, данные по районам и оценки микроклимата.'),
    'new-moscow.html': ('Новая Москва на карте: поселения, экология, транспорт',
                        'Поселения Новомосковского и Троицкого округов на карте: рельеф, экология и транспорт. Чем Новая Москва отличается от старой.'),
    'index.html': (None, None),
}
OG = {'index.html': 'home', 'housing.html': 'housing', 'ecology.html': 'ecology', 'transport.html': 'transport',
      'social.html': 'social', 'parks.html': 'parks', 'sport.html': 'sport', 'climate.html': 'climate',
      'new-moscow.html': 'new-moscow', 'reyting/index.html': 'reyting', 'rayon/index.html': 'home'}
OG['zagorod/bez-mashiny/index.html'] = 'zagorod'
PARK_TWINS = {
    'park-nikulino': ('Парк Никулино у памятника Скобелеву',
                      'Карта участка парка Никулино в Тропарёве-Никулине. На ней отмечены памятник М. Д. Скобелеву и две детские площадки.'),
    'park-nikulino-192': ('Парк Никулино у храма Архангела Михаила',
                          'Участок парка Никулино у храма Архангела Михаила в Тропарёве. На карте можно найти храм, дорожки и две детские площадки.'),
    'park-v-poyme-reki-gorodni': ('Парк в пойме Городни в Братееве',
                                  'Карта участка в пойме реки Городни в районе Братеево. На ней отмечены кафе, три детские площадки и туалеты.'),
    'park-v-poyme-reki-gorodni-145': ('Парк в пойме Городни в Братееве и Зябликове',
                                      'Карта участка парка в районах Братеево и Зябликово. Найдите «Цаплю», детские площадки и туалеты в пойме Городни.'),
    'park-druzhby': ('Парк Дружбы в Левобережном и Головинском районах',
                     'Карта парка Дружбы в Левобережном и Головинском районах. Здесь отмечены памятники Сервантесу и Тагору, кафе и детские площадки.'),
    'park-druzhby-78': ('Парк Дружбы в Некрасовке',
                        'Дорожки парка Дружбы в Некрасовке на карте Москвы. Посмотрите, где находятся смотровая площадка и кафе.'),
    'yablonevyy-sad': ('Яблоневый сад в Конькове',
                       'На карте Яблоневого сада в Конькове отмечены скульптуры «Косули», «Олени» и «Сердце», детские площадки и туалет.'),
    'yablonevyy-sad-195': ('Яблоневый сад в районе Орехово-Борисово Южное',
                           'Дорожки Яблоневого сада в районе Орехово-Борисово Южное. На карте обозначены граница сада и детская площадка.'),
    'yablonevyy-sad-214': ('Яблоневый сад в Восточном Бирюлёве',
                           'Карта Яблоневого сада в районе Бирюлёво Восточное с дорожками и тремя детскими площадками.'),
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


def search_landing(s, path):
    if path == 'rayon/lefortovo/index.html':
        title = 'Район Лефортово (ЮВАО) — границы, метро и цены'
        description = 'Лефортово входит в Юго-Восточный административный округ Москвы. Карта границ и домов, транспорт, цены на жильё и Лефортовский парк.'
        if 'id="lefortovo-location"' not in s:
            s = s.replace('<h1>Район Лефортово</h1>',
                          '<h1>Район Лефортово</h1><p id="lefortovo-location">Лефортово входит в Юго-Восточный административный округ Москвы (ЮВАО). '
                          '<a href="#dm">Смотрите границы района и дома на карте</a> или откройте <a href="../../parks/lefortovskiy-park/">карту Лефортовского парка</a>.</p>', 1)
    elif path == 'parks/chobotovskiy-les/index.html':
        title = 'Чоботовский лес в Москве — карта троп и как добраться'
        description = 'Чоботовский лес в Ново-Переделкине. Карта троп и детских площадок, ориентиры от метро «Боровское шоссе» и со стороны станции Переделкино.'
        if 'id="chobotovo-visit"' not in s:
            s = s.replace('  <p id="load-error"', '''  <section class="park-sec" aria-labelledby="chobotovo-visit">
    <h2 id="chobotovo-visit">Как добраться до Чоботовского леса</h2>
    <p>Если едете на метро, ориентир — станция «Боровское шоссе» и Чоботовская улица. С юга удобнее подъехать на МЦД-4 до станции Переделкино. От станции есть наземный переход в сторону 9-й Чоботовской аллеи. Сверьте подход к лесу с картой троп.</p>
    <p><a href="#map-section">Открыть карту троп и площадок</a> · <a href="https://mtp.mos.ru/projects/proekt-transportnogo-i-peshehodnogo-obslujivaniia-novyh-stancii-metro-i-mcd">Схема подходов к станции Переделкино</a></p>
  </section>
  <p id="load-error"''', 1)
    else:
        return s
    for tag, value in (('title', title), ('og:title', title), ('description', description), ('og:description', description)):
        s = set_tag(s, tag, value)
    return s


def main(files=None):
    changed = 0
    if files is None:
        files = sorted(set(glob.glob('*.html') + glob.glob('*/index.html') + glob.glob('*/*/index.html')))
    for f in files:
        f = f.replace(os.sep, '/')
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
        if f.startswith('parks/') and f.split('/')[1] in PARK_TWINS:
            name, description = PARK_TWINS[f.split('/')[1]]
            title = name + ' — карта'
            for tag, value in (('title', title), ('og:title', title), ('description', description), ('og:description', description)):
                s = set_tag(s, tag, value)
            s = re.sub(r'<h1 id="title">[^<]+</h1>', f'<h1 id="title">{E(name)}</h1>', s, count=1)
        elif f.startswith('parks/'):
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
        s = search_landing(s, f)
        if s != s0:
            open(f, 'w', encoding='utf-8').write(s)
            changed += 1
    print('seo_fix: изменено страниц', changed)


if __name__ == '__main__':
    main()
