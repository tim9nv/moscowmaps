"""Страница «Зима за городом» (zagorod/zima/): горнолыжные склоны, лыжные маршруты от станции до станции, лыжные базы.

Данные: tools/data/winter_osm.json (делает tools/extract_winter.py из OpenStreetMap) и
tools/data/winter.json (сверенные с официальными сайтами поля: перепад, прокат, вечернее катание, как добраться; с датой).
Подключается из tools/build_zagorod.py: zima_page(head, METRIKA, hubpt).
"""
import html, json, math, os, re
from zg_scheme import scheme_items, km

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = lambda s: html.escape(str(s), quote=True)

# цвета как на схемах курортов (по ним же красим линии поверх карты OpenStreetMap)
DIFF = [('novice', 'учебные', '#2ca25f'), ('easy', 'простые', '#1f6feb'), ('intermediate', 'средние', '#e03131'),
        ('advanced', 'сложные', '#111111'), ('expert', 'очень сложные', '#f08c00'), ('freeride', 'фрирайд', '#f08c00')]
MAPD = {}  # данные карт карточек: ключ -> {'l': [[цвет, точки]], 'f': [точки подъёмников], 'e': [точки начала и конца]}
def map_div(key, lines, lifts=(), ends=()):
    MAPD[key] = {'l': [[DCOL.get(d, '#1f6feb'), [[round(a, 5), round(b, 5)] for a, b in g]] for d, g in lines],
                 'f': [[[round(a, 5), round(b, 5)] for a, b in g] for _, g in lifts], 'e': list(ends)}
    return f'<div class="zw-map" data-k="{key}" role="img" aria-label="Карта: трассы на карте OpenStreetMap"></div>'
DCOL = {k: c for k, _, c in DIFF}
LIFT = {'chair_lift': 'кресельных', 't-bar': 'бугельных', 'j-bar': 'бугельных', 'platter': 'тарелочных',
        'drag_lift': 'бугельных', 'rope_tow': 'верёвочных', 'magic_carpet': 'ленточных', 'mixed_lift': 'кресельно-кабинных',
        'gondola': 'кабинных'}
PREFIX = re.compile(r'^(Горнолыжный|Спортивный|Горнолыжная|Сноупарк|Спорткомплекс|Склон|Спортивно-оздоровительный|Учебно-тренировочный)'
                    r'(\s+(курорт|комплекс|центр|база|клуб|парк))?\s*', re.I)


RENAME = {'Леонида Тягачёва': 'Клуб Леонида Тягачёва (Шуколово)', 'НПП Звезда': 'Склон «Звезда» (Томилино)'}


def clean(n):
    n = PREFIX.sub('', n or '').strip()
    n = n.strip('«»"\' ').replace('"', '').replace('«', '').replace('»', '') or n
    return RENAME.get(n, n)


def mini(lines, lifts=(), w=280, h=170, pad=10):
    pts = [p for _, g in lines for p in g] + [p for _, g in lifts for p in g]
    if not pts:
        return ''
    la0, la1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lo0, lo1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((la0 + la1) / 2))
    sx = (lo1 - lo0) * k or 1e-6
    sy = (la1 - la0) or 1e-6
    sc = min((w - 2 * pad) / sx, (h - 2 * pad) / sy)
    ox = (w - sx * sc) / 2
    oy = (h - sy * sc) / 2
    P = lambda p: f'{ox + (p[1] - lo0) * k * sc:.1f} {oy + (la1 - p[0]) * sc:.1f}'
    o = [f'<svg class="zm" viewBox="0 0 {w} {h}" aria-hidden="true">']
    for d, g in lines:
        o.append(f'<path d="M{"L".join(P(p) for p in g)}" stroke="{DCOL.get(d, "#8f9fd0")}"/>')
    for t, g in lifts:
        o.append(f'<path class="lf" d="M{"L".join(P(p) for p in g)}"/>')
    # масштаб 500 м
    bar = 0.5 / 111.32 * sc
    if bar < w - 20:
        o.append(f'<path class="sb" d="M{w - pad - bar:.1f} {h - 6}h{bar:.1f}"/><text x="{w - pad:.1f}" y="{h - 10}" text-anchor="end">500 м</text>')
    o.append('</svg>')
    return ''.join(o)


def route_svg(segs, w=280, h=120):
    return mini([('', g) for g in segs], (), w, h).replace('stroke="#8f9fd0"', 'stroke="#9CC3FF"').replace('500 м', '500 м')


def lifts_txt(l):
    if not isinstance(l, dict):
        return l if isinstance(l, str) else None
    t = ', '.join(l.get('types') or [])
    return (f"{l['count']}: " if l.get('count') else '') + t if (t or l.get('count')) else None


def manual():
    p = os.path.join(ROOT, 'tools/data/winter.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'resorts': [], 'xc': [], 'checked': ''}


def fact(label, v):
    if v in (None, '', [], 'null'):
        return ''
    if v is True: v = 'есть'
    if v is False: v = 'нет'
    return f'<div><dt>{E(label)}</dt><dd>{E(v)}</dd></div>'


def zima_page(head, METRIKA, hubpt):
    MAPD.clear()
    O = json.load(open(os.path.join(ROOT, 'tools/data/winter_osm.json'), encoding='utf-8'))
    M = manual()
    man = M.get('resorts', [])
    res = []
    for r in O['resorts']:
        m = next((x for x in man if x.get('osm') == clean(r['osm_name'])), None)
        name = (m or {}).get('title') or clean(r['osm_name'])
        if not name:
            continue
        res.append(dict(r=r, m=m or {}, name=name, slug=re.sub(r'[^a-z0-9]+', '-', str(len(res)))))
    city = [x for x in res if x['r']['msk_km'] < 17]
    out = [x for x in res if x['r']['msk_km'] >= 17]
    types = [('ski', 'Горные лыжи', '#FFD86B'), ('xc', 'Беговые маршруты', '#9CC3FF')]
    items = [dict(name=x['name'], href=f'#r{i}', ll=tuple(x['r']['c']), t='ski', tip=f"{x['name']} — склонов на карте {x['r']['n_pistes']}")
             for i, x in enumerate(out)]
    routes = [r for r in O['routes'] if r['km'] >= 15][:14]
    items += [dict(name=r['name'], href=f'#l{i}', ll=tuple(r['c']), t='xc', tip=f"{r['name']} — {r['km']} км") for i, r in enumerate(routes)]
    note = ('Схема, а не карта: объект стоит в своём направлении от Москвы, расстояние сжато. Жёлтые — горнолыжные склоны, '
            'голубые — длинные лыжные маршруты, их середина. Нажмите на точку — откроется описание ниже.')

    def resort_card(i, x, pre='r'):
        r, m = x['r'], x['m']
        lifts = ', '.join(f'{n} {LIFT.get(t, t)}' for t, n in sorted(r['lifts_by'].items(), key=lambda kv: -kv[1]))
        facts = ''.join([
            fact('Перепад высот', f"{m['vertical_m']} м" if m.get('vertical_m') else None),
            fact('Трасс (по курорту)', m.get('trails')),
            fact('Самая длинная', f"{m['longest_m']} м" if m.get('longest_m') else None),
            fact('Подъёмники (по курорту)', lifts_txt(m.get('lifts'))),
            fact('Прокат', m.get('rental')), fact('Школа', m.get('school')), fact('Вечернее катание', m.get('night')),
            fact('Тюбинг', m.get('tubing')), fact('Сезон 2026/27', m.get('season_2026_27')),
        ])
        get = f'<p class="zw-get"><b>Как добраться.</b> {E(m["how_to_get"])}</p>' if m.get('how_to_get') else ''
        pn = re.sub(r'\s*Внимание:.*$', ' Перед поездкой сверьте на сайте курорта.', m.get('price_note') or '')
        price = f'<p class="zw-get"><b>Цены.</b> {E(pn)}</p>' if pn else ''
        src = m.get('sources') or []
        site = m.get('site') or r.get('osm_web')
        seen, urls = set(), []
        for u in ([site] if site else []) + src:
            dom = re.sub(r"^https?://(www\\.)?", "", u).split("/")[0]
            if dom not in seen:
                seen.add(dom); urls.append((u, dom))
        links = ' · '.join(f'<a href="{E(u)}" rel="noopener" target="_blank">{E(dom)}</a>' for u, dom in urls[:3])
        osmline = (f'На карте OpenStreetMap: {r["n_pistes"]} склонов общей длиной {str(r["km_pistes"]).replace(".", ",")} км'
                   + (f', подъёмники: {lifts}' if lifts else '') + '.')
        return (f'<article class="zw" id="{pre}{i}"><div class="zw-h"><h3>{E(x["name"])}</h3>'
                f'<p class="meta">около {round(r["msk_km"] / 5) * 5} км от центра Москвы по прямой</p></div>'
                f'<div class="zw-b">{map_div(pre + str(i), r["pistes"], r["lifts"])}<div>'
                f'<dl class="zw-f">{facts}</dl>' + get + price +
                f'<p class="zw-osm">{E(osmline)}</p>' + (f'<p class="zw-src">{links}' + (f' · проверено {E(M.get("checked"))}' if m else '') + '</p>' if links else '') +
                '</div></div></article>')

    def route_card(i, r):
        fr = f' от {E(r["frm"])} до {E(r["to"])}' if r.get('frm') and r.get('to') else ''
        return (f'<article class="zw" id="l{i}"><div class="zw-h"><h3>{E(r["name"])}</h3><p class="meta">{str(r["km"]).replace(".", ",")} км{fr}</p></div>'
                f'<div class="zw-b">{map_div("l" + str(i), [("", g) for g in r["g"]], (), [r["g"][0][0], r["g"][-1][-1]])}<div><p class="zw-osm">Лыжный маршрут, размеченный туристами в OpenStreetMap '
                f'(<a href="https://www.openstreetmap.org/relation/{r["id"]}" rel="noopener" target="_blank">открыть на карте</a>). '
                'Прокладывают ли лыжню этой зимой — не знаем: это маршрут для похода, а не ухоженная трасса.</p></div></div></article>')

    xc = M.get('xc', [])
    xc_html = ''.join(
        f'<article class="zw"><div class="zw-h"><h3>{E(b["name"])}</h3></div><div><dl class="zw-f">'
        + fact('Круги', b.get('loops_km')) + fact('Стиль', b.get('styles')) + fact('Освещение', b.get('lights'))
        + fact('Прокат', b.get('rental')) + fact('Раздевалка', b.get('changing_room')) + fact('Парковка', b.get('parking')) + '</dl>'
        + (f'<p class="zw-get"><b>Как добраться.</b> {E(b["how_to_get"])}</p>' if b.get('how_to_get') else '')
        + (f'<p class="zw-src">' + ' · '.join(f'<a href="{E(u)}" rel="noopener" target="_blank">{E(re.sub(r"^https?://(www\\.)?", "", u).split("/")[0])}</a>' for u in (b.get('sources') or [])[:2]) + '</p>' if b.get('sources') else '')
        + '</div></article>' for b in xc)

    css = ('<style>.zw-grid{display:grid;gap:16px}.zw{border-top:1px solid #27376B;padding:18px 0}.zw-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px}'
           '.zw-h h3{margin:0}.zw-h .meta{margin:0;color:var(--muted);font-size:14px}.zw-b{display:grid;grid-template-columns:380px 1fr;gap:22px;margin-top:10px;align-items:start}'
           '.zm{width:280px;height:auto;background:#0A1230;border:1px solid #27376B}.zm path{fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}'
           '.zm path.lf{stroke:#B4C1E4;stroke-width:1.3;stroke-dasharray:4 3}.zm path.sb{stroke:#6f80b3;stroke-width:2}.zm text{fill:#6f80b3;font:500 11px var(--label,sans-serif)}'
           '.zw-f{display:flex;flex-wrap:wrap;gap:8px 22px;margin:0 0 8px}.zw-f div{min-width:120px}.zw-f dt{font:500 12px/1.2 var(--label,sans-serif);text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}'
           '.zw-f dd{margin:2px 0 0;font-size:16px}.zw-get{margin:6px 0}.zw-osm,.zw-src{font-size:13.5px;color:var(--muted);margin:6px 0 0}'
           '.zw-leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13.5px;color:var(--muted);margin:4px 0 10px}.zw-leg i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:6px}'
           '.season{display:inline-grid;grid-template-columns:auto auto;border:1px solid #3a4a80;border-radius:2px;overflow:hidden;margin:4px 0 14px}'
           '.season a{padding:10px 18px;font:500 15px/1 var(--label,sans-serif);text-transform:uppercase;letter-spacing:.1em;color:var(--fg);text-decoration:none}'
           '.season a[aria-current]{background:#FFD86B;color:#0B1330}'
           '.zw-map{height:260px;border:1px solid #3a4a80;outline:1px solid #27376B;outline-offset:4px;background:#0A1230}.zw-leg i.adv{outline:1px solid #6f80b3}''@media (max-width:700px){.zw-b{grid-template-columns:1fr}.zw-map{height:240px}}</style>')
    leg = '<div class="zw-leg">' + ''.join(f'<span><i{" class=adv" if k == "advanced" else ""} style="background:{c}"></i>{E(n)}</span>' for k, n, c in DIFF[:5]) + '<span><i style="background:repeating-linear-gradient(90deg,#B4C1E4 0 4px,transparent 4px 7px)"></i>подъёмники (пунктир)</span></div>'
    title = 'Зима за городом: горнолыжные склоны и лыжные трассы у Москвы'
    desc = f'Горнолыжные склоны Подмосковья на схеме, лыжные маршруты от станции до станции и лыжные базы: где кататься зимой рядом с Москвой.'
    url = 'https://www.mskatlas.ru/zagorod/zima/'
    h = head(title, desc, url, '../../')
    body = f'''<main class="wrap">
  <nav class="crumbs"><a href="../">За город</a> / Зима</nav>
  <header class="hero"><div class="hero-copy"><h1>Зима за городом</h1><p>Где покататься на горных и беговых лыжах рядом с Москвой: склоны Подмосковья на одной схеме, лыжные маршруты от станции до станции и лыжные базы. Сверенные с сайтами курортов цифры помечены датой проверки.</p></div></header>
  <nav class="season" aria-label="Сезон"><a href="../">Лето</a><a aria-current="page" href="./">Зима</a></nav>
  <section class="zg-sec"><h2>Склоны и маршруты на схеме</h2>{scheme_items(items, types, hubpt, note)}</section>
  <section class="zg-sec"><h2>Горнолыжные склоны Подмосковья</h2>{leg}<div class="zw-grid">{''.join(resort_card(i, x) for i, x in enumerate(out))}</div></section>
  <section class="zg-sec"><h2>Склоны в самой Москве</h2><div class="zw-grid">{''.join(resort_card(i, x, 'm') for i, x in enumerate(city))}</div></section>
  <section class="zg-sec"><h2>Лыжные маршруты от станции до станции</h2><p class="zg-note">Маршруты турклубов и лыжников, размеченные в OpenStreetMap: доехать на электричке до одной станции, пройти лесом и уехать с другой. Длина — по разметке на карте.</p><div class="zw-grid">{''.join(route_card(i, r) for i, r in enumerate(routes))}</div></section>
  {'<section class="zg-sec"><h2>Лыжные базы и трассы с прокатом</h2><div class="zw-grid">' + xc_html + '</div></section>' if xc_html else ''}
  <footer class="zg-src">Склоны, подъёмники и маршруты — OpenStreetMap, выгрузка {E(O["date"])} (<a href="https://www.openstreetmap.org/copyright">© участники OpenStreetMap</a>); на карте отмечено не всё, и состояние трасс OSM не знает. Цифры курортов — с их официальных сайтов{(", проверено " + E(M.get("checked"))) if M.get("checked") else ""}. Перед поездкой смотрите, открыт ли сезон, на сайте курорта.</footer>
</main>
{METRIKA}
</body>
</html>
'''
    js = ('<script>window.ZW=' + json.dumps(MAPD, ensure_ascii=False, separators=(',', ':')) + ';</script>'
          '<script>addEventListener("load",function(){if(!window.L)return;'
          'function draw(el){var d=ZW[el.dataset.k];if(!d||el._m)return;var m=L.map(el,{scrollWheelZoom:false,zoomSnap:0.25});el._m=m;m.attributionControl.setPrefix(false);'
          'L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:18,attribution:\'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>\'}).addTo(m);'
          'var g=L.featureGroup().addTo(m);'
          'd.l.forEach(function(x){L.polyline(x[1],{color:"#fff",weight:7,opacity:.85}).addTo(g);L.polyline(x[1],{color:x[0],weight:4}).addTo(g)});'
          'd.f.forEach(function(x){L.polyline(x,{color:"#333",weight:2,dashArray:"5 4"}).addTo(g)});'
          'd.e.forEach(function(x,i){L.circleMarker(x,{radius:7,color:"#fff",weight:2,fillColor:i?"#e03131":"#2ca25f",fillOpacity:1}).bindTooltip(i?"конец":"начало").addTo(g)});'
          'm.fitBounds(g.getBounds(),{padding:[16,16],maxZoom:16})}'
          'var els=document.querySelectorAll(".zw-map");'
          'if("IntersectionObserver" in window){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){io.unobserve(e.target);draw(e.target)}})},{rootMargin:"300px"});els.forEach(function(e){io.observe(e)})}else els.forEach(draw)});</script>')
    body = body.replace('</main>', '</main>\n' + js, 1)
    return h.replace('</head>', css + '</head>', 1) + body
