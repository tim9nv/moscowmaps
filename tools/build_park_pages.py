"""Отдельная страница для каждого парка: parks/<slug>/index.html (по образцу путеводителей ВДНХ и Ботсада).
Запуск: python3 tools/build_park_pages.py   (после build-park-catalog.py и extract_park_places.py)
Берёт parks/catalog/parks.json, places.json, trails-*.txt и const PARKS из parks.html.
Пишет страницы, добавляет в parks.json поле url ("../<slug>/") и обновляет раздел парков в sitemap.xml.
Карту и объекты на странице рисует parks/catalog/catalog.js (window.PARK_ID, window.PARK_BASE).
"""
import json, re, os, gzip, base64, math, html, datetime
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = f'{REPO}/parks/catalog'
BASE = 'https://www.mskatlas.ru'
V = datetime.date.today().strftime("%Y%m%d") + "n"
GUIDES = {'14': '../botanicheskiy-sad/'}          # у этих парков уже есть свой путеводитель
RESERVED = {'catalog', 'vdnh', 'botanicheskiy-sad'}
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))
def slugify(t):
    t = ''.join(TR.get(c, c) for c in t.lower())
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', t)).strip('-')[:60].strip('-')
def E(t): return html.escape(t, quote=True)
def num(v, d=1): return (f'{v:.{d}f}').replace('.', ',')
def pl(n, a, b, c): return a if n % 10 == 1 and n % 100 != 11 else (b if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else c)
def cap(t): return t[0].upper() + t[1:]
def km(lines):
    s = 0
    for ln in lines:
        for (a, b), (c, d) in zip(ln, ln[1:]):
            x = math.radians(d - b) * math.cos(math.radians((a + c) / 2)); y = math.radians(c - a); s += 6371 * math.hypot(x, y)
    return s
parks = json.load(open(f'{CAT}/parks.json', encoding='utf-8'))
places = json.load(open(f'{CAT}/places.json', encoding='utf-8'))
PARKS = json.loads(re.search(r'const PARKS = (.*?);\n', open(f'{REPO}/parks.html', encoding='utf-8').read()).group(1))
dslug = {n: (s, o) for s, n, o in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
walks = json.load(open(f'{CAT}/walks.json', encoding='utf-8')) if os.path.exists(f'{CAT}/walks.json') else {}
METRIKA = open(f'{REPO}/tools/metrika.html', encoding='utf-8').read().strip()
by_district = {}
for q in parks:
    for d in PARKS[int(q['id']) - 1].get('d', []): by_district.setdefault(d, []).append(q)
trails = {}
for g in sorted({p['group'] for p in parks}):
    trails.update(json.loads(gzip.decompress(base64.b64decode(open(f'{CAT}/trails-{g}.txt').read()))))
KIND = {'park': 'парк', 'protected_area': 'природная территория', 'garden': 'сад'}
CATS = [('sight', 'Достопримечательности', ('достопримечательность', 'достопримечательности', 'достопримечательностей')),
        ('museum', 'Музеи и театры', ('музей', 'музея', 'музеев')), ('view', 'Смотровые площадки', ('смотровая площадка', 'смотровые площадки', 'смотровых площадок')),
        ('art', 'Скульптуры', ('скульптура', 'скульптуры', 'скульптур')), ('food', 'Кафе и рестораны', ('кафе', 'кафе', 'кафе')),
        ('play', 'Детские площадки', ('детская площадка', 'детские площадки', 'детских площадок')), ('wc', 'Туалеты', ('туалет', 'туалета', 'туалетов'))]
used = set(RESERVED); urls = []
for p in parks:   # первый проход: адреса
    if p['id'] in GUIDES: p['url'] = GUIDES[p['id']]; continue
    sl = slugify(p['name']) or f'park-{p["id"]}'
    if sl in used: sl = f'{sl}-{p["id"]}'
    used.add(sl); p['url'] = f'../{sl}/'; p['slug'] = sl
for p in parks:
    pid = p['id']
    if pid in GUIDES: p['url'] = GUIDES[pid]; continue
    sl = p['slug']
    src = PARKS[int(pid) - 1]; name = cap(p['name'])
    pls = places['parks'].get(pid, [])
    t = trails.get(pid, {}).get('t', {})
    total = sum(km(v) for v in t.values()); paved = km(t.get('paved', []))
    dist = [d for d in src.get('d', []) if d in dslug]
    by = {c: [x[3] for x in pls if x[2] == c] for c, _, _ in CATS}
    facts = []
    if src.get('a'): facts.append(f'площадь {num(src["a"], 2 if src["a"] < 1 else 1)} км²')
    # длину дорожек в текст не пишем: в выгрузке много параллельных и служебных линий, сумма выходит завышенной
    cnt = [f'{len(by[c])} {pl(len(by[c]), *w)}' for c, _, w in CATS if by[c]]
    where = ('в ' + pl(len(dist), 'районе', 'районах', 'районах') + ' ' + ', '.join(dist)) if dist else 'в Москве'
    kind = KIND.get(src.get('k'), 'парк')
    lead = (f'{name} находится {where}' if re.search('парк|сад|лес|заповедник|заказник|роща|бульвар|сквер', name.lower()) else f'{name} — {kind} {where}') + (', ' + ', '.join(facts) if facts else '') + '.'
    if cnt: lead += ' На карте отмечено: ' + ', '.join(cnt) + '.'
    title = f'{name} ({dist[0]}) — карта и что посмотреть' if dist else f'{name} — карта и что посмотреть'
    empty = not pls and total < 0.3      # ни объектов, ни троп: в поиск не отдаём, пока не дописана
    desc = (f'{name} в Москве: карта с дорожками и тропами' + (', ' + ', '.join(cnt[:4]) if cnt else '') + '. Геолокация «Я на карте».')
    secs = ''
    for c, h, _ in CATS[:5]:
        names = sorted(set(by[c]), key=lambda x: x.lower())
        if not names: continue
        more = f'<li class="muted">и ещё {len(names) - 40} — на карте</li>' if len(names) > 40 else ''
        secs += f'<section class="park-sec"><h2>{h}</h2><ul class="park-names">' + ''.join(f'<li>{E(n)}</li>' for n in names[:40]) + more + '</ul></section>\n'
    wk = walks.get(pid)
    walk_html = ''; route_ui = '<div hidden><div id="routes"></div><div id="selected-route"></div><button id="clear-route"></button><select id="route-leg"></select></div>'
    if wk:
        r = wk['routes'][0]; names = {x['id']: x['name'] for x in wk['places']}
        kmr = num(r['metres'] / 1000); mins = math.ceil(r['metres'] / (4000 / 60) / 5) * 5
        walk_html = (f'<section id="walks" class="park-sec"><h2>Прогулка Атласа</h2><p class="muted">Длина по пешеходным дорожкам, время без остановок.</p><div id="routes" class="routes"></div>'
                     f'<noscript><p><b>{E(r["name"])}</b> — {kmr} км, около {mins} мин. ' + ' → '.join(E(names[i]) for i in r['stops']) + '</p></noscript></section>\n')
        route_ui = ''
        lead += f' Есть готовая прогулка: «{r["name"]}», {kmr} км.'
        desc = desc.replace(' Геолокация «Я на карте».', f' Готовая прогулка на {kmr} км.')
    others = []
    for d in dist:
        for q in by_district.get(d, []):
            if q['id'] != pid and q not in others: others.append(q)
    others_html = ('<section class="park-sec"><h2>Другие парки рядом</h2><ul class="park-names">' + ''.join(f'<li><a href="{E(q.get("url") or "../" + q.get("slug", "") + "/")}">{E(cap(q["name"]))}</a></li>' for q in others[:12]) + '</ul></section>\n') if others else ''
    links = ''.join(f'<a href="../../rayon/{dslug[d][0]}/">Район {E(d)}</a>' for d in dist)
    page = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE}/parks/{sl}/">{'<meta name="robots" content="noindex, follow">' if empty else ''}
<meta property="og:type" content="article"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{BASE}/parks/{sl}/"><meta property="og:site_name" content="Атлас Москвы"><meta property="og:locale" content="ru_RU">
<link rel="stylesheet" href="../vdnh/guide.css?v={V}">
<link rel="stylesheet" href="../catalog/catalog.css?v={V}">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>window.PARK_ID="{pid}";window.PARK_BASE="../catalog/";</script>
<script defer src="../catalog/catalog.js?v={V}"></script>
</head>
<body>
<header class="topbar"><div class="in"><a class="brand" href="../../index.html" aria-label="Атлас Москвы, на главную"><i aria-hidden="true"></i>Атлас Москвы</a><nav class="tabs" aria-label="Разделы"><a href="../../index.html">Районы</a><a href="../../housing.html">Цены</a><a href="../../ecology.html">Экология</a><a href="../../transport.html">Транспорт</a><a href="../../social.html">Школы и поликлиники</a><a href="../../parks.html" aria-current="page">Парки и прогулки</a><a href="../../zagorod/">За город</a><a href="../../reyting/">Рейтинги</a><a href="../../new-moscow.html">Новая Москва</a><a href="../../climate.html">Климат и рельеф</a></nav></div></header><script>(function(){{var t=document.querySelector(".topbar .tabs"),a=t&&t.querySelector("[aria-current]");if(a&&t.scrollWidth>t.clientWidth)t.scrollLeft=a.offsetLeft-(t.clientWidth-a.offsetWidth)/2}})()</script>
<main class="wrap">
  <nav class="crumb" aria-label="Навигация"><a href="../catalog/">Все карты парков</a> / {E(cap(p["short"]))}</nav>
  <header class="hero"><div class="hero-copy"><p class="eyebrow">Прогулки по Москве{(" · " + E(dist[0])) if dist else ""}</p><h1 id="title">{E(name)}</h1><p id="intro">{E(lead)}</p><div class="actions"><a class="primary" href="#map-section">Открыть карту</a></div></div></header>
  <p id="load-error" role="status" hidden></p>
  <section id="map-section" aria-labelledby="map-title" hidden>
    <div class="section-head"><h2 id="map-title" tabindex="-1">Карта парка</h2></div>
    <div class="map-shell" id="map-shell">
      <div class="map-toolbar" aria-label="Управление картой">
        <button id="locate" type="button" aria-pressed="false">◎ Я на карте</button>
        <button id="map-expand" type="button" aria-pressed="false">⛶ На весь экран</button>
      </div>
      <div class="tools" id="park-tools" hidden><label for="search">Найти в парке</label><input type="search" id="search" placeholder="Например, кафе или памятник"><div id="filters" class="filters" aria-label="Категории"></div></div>
      {'<div id="selected-route" class="selected-route" hidden><strong id="selected-route-name"></strong><button id="clear-route" type="button">Скрыть маршрут</button></div><div id="route-tools" class="route-tools" hidden><label for="route-leg">Участок прогулки</label><select id="route-leg"></select></div>' if wk else ''}
      <div class="trail-controls">
        <label><input id="trail-toggle" type="checkbox" checked disabled> Тропы и аллеи</label>
        <div class="trail-legend" aria-label="Типы дорожек"><span class="paved">Твёрдое покрытие</span><span class="unpaved">Грунт и гравий</span><span class="boardwalk">Настил</span><span class="steps">Ступени</span><span class="unknown">Покрытие неизвестно</span></div>
        <p id="trail-status" class="muted" role="status"></p>
      </div>
      <div id="map" aria-label="Интерактивная карта парка"></div>
      <p id="status" role="status"></p>
    </div>
    <details id="places" hidden><summary>Объекты списком <span id="count"></span></summary><p class="muted" id="places-note"></p><ul id="place-list"></ul></details>
    {route_ui}
  </section>
{walk_html}{secs}{others_html}  {f'<nav class="park-links" aria-label="Районы рядом">{links}</nav>' if links else ''}
  <footer>Карта, дорожки и объекты — <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a>, выгрузка {places["date"]}. Площадь — по контуру парка на карте Атласа. Проходы и ограничения могут меняться. Сверяйтесь с указателями на месте.</footer>
</main>
{METRIKA}
</body>
</html>
'''
    os.makedirs(f'{REPO}/parks/{sl}', exist_ok=True)
    open(f'{REPO}/parks/{sl}/index.html', 'w', encoding='utf-8').write(page)
    if not empty: urls.append(f'{BASE}/parks/{sl}/')
json.dump(parks, open(f'{CAT}/parks.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
sm = open(f'{REPO}/sitemap.xml', encoding='utf-8').read()
sm = re.sub(r'  <url><loc>' + re.escape(BASE) + r'/parks/(?!catalog/|vdnh/|botanicheskiy-sad/)[^<]*</loc>.*?</url>\n', '', sm)
today = datetime.date.today().isoformat()
sm = sm.replace('</urlset>', ''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>')
open(f'{REPO}/sitemap.xml', 'w', encoding='utf-8').write(sm)
print(len(urls), 'страниц парков')

# Каталог: обычный список ссылок на все парки по округам (раньше ссылки строил только скрипт — поисковик их не видел)
OKR = ['ЦАО', 'САО', 'СВАО', 'ВАО', 'ЮВАО', 'ЮАО', 'ЮЗАО', 'ЗАО', 'СЗАО', 'ЗелАО', 'НАО', 'ТАО']
groups = {}
for q in parks:
    d = PARKS[int(q['id']) - 1].get('d', [])
    o = dslug[d[0]][1] if d and d[0] in dslug else 'Новая Москва'
    groups.setdefault(o, []).append(q)
lst = '<!--PARK-LIST--><section class="park-sec" aria-labelledby="all-parks"><h2 id="all-parks">Все парки по округам</h2>' + ''.join(
    f'<h3>{E(o)}</h3><ul class="park-names">' + ''.join(f'<li><a href="{E(q["url"].replace("../", "../", 1))}">{E(cap(q["name"]))}</a></li>' for q in sorted(groups[o], key=lambda q: q['name'].lower())) + '</ul>'
    for o in sorted(groups, key=lambda o: OKR.index(o) if o in OKR else 99)) + '</section><!--PARK-LIST-END-->'
c = open(f'{CAT}/index.html', encoding='utf-8').read()
c = re.sub(r'<!--PARK-LIST-->.*?<!--PARK-LIST-END-->', '', c, flags=re.S)
c = c.replace('</main>', lst + '\n</main>', 1)
if 'Yandex.Metrika counter' not in c: c = c.replace('</body>', METRIKA + '\n</body>', 1)
open(f'{CAT}/index.html', 'w', encoding='utf-8').write(c)
for g in ('vdnh', 'botanicheskiy-sad'):
    f = f'{REPO}/parks/{g}/index.html'; t = open(f, encoding='utf-8').read()
    if 'Yandex.Metrika counter' not in t: open(f, 'w', encoding='utf-8').write(t.replace('</body>', METRIKA + '\n</body>', 1))
# Страницы районов: блок «Парки района» со ссылками (перед «Частыми вопросами»)
n = 0
for d, (dsl, o) in dslug.items():
    f = f'{REPO}/rayon/{dsl}/index.html'
    if not os.path.exists(f): continue
    t = open(f, encoding='utf-8').read()
    t = re.sub(r'<!--DISTRICT-PARKS-->.*?<!--DISTRICT-PARKS-END-->', '', t, flags=re.S)
    qs = sorted(by_district.get(d, []), key=lambda q: -(PARKS[int(q['id']) - 1].get('a') or 0))
    if qs:
        blk = (f'<!--DISTRICT-PARKS--><section><h2>Парки района {E(d)}</h2><p>Карты с дорожками, что посмотреть, кафе и туалеты:</p><ul>'
               + ''.join(f'<li><a href="../../parks/{q["url"][3:] if q["url"].startswith("../") else q["url"]}">{E(cap(q["name"]))}</a></li>' for q in qs[:15]) + '</ul></section><!--DISTRICT-PARKS-END-->')
        i = t.find('<section class="faq">')
        if i > 0: t = t[:i] + blk + t[i:]; n += 1
    open(f, 'w', encoding='utf-8').write(t)
print('районов с парками:', n)
