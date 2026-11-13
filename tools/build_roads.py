"""Вкладка «Транспорт → На автомобиле»: roads.html — карта районов по нагрузке на дороги (tools/data/road_load.json).
Собирается из transport.html (та же раскладка, карта на том же месте) и ставит на обе страницы
переключатель «На метро | На автомобиле». Идемпотентно; запускать после atlas_style.py, перед seo_fix.py.
"""
import json, os, re, html
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = html.escape
RL = json.load(open(f'{REPO}/tools/data/road_load.json', encoding='utf-8'))
SLUG = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
ddmm = '.'.join(RL['date'].split('-')[::-1])

SW = ('<!--TR-SWITCH--><nav class="trsw" aria-label="Как добираться"><a href="transport.html"{a}>На метро</a><a href="roads.html"{b}>На автомобиле</a></nav>'
      '<style>.trsw{display:flex;gap:0;margin:0 0 14px;border:1px solid #3a4a80;max-width:100%;min-width:0}.trsw a{flex:1 1 auto;text-align:center}.trsw a{padding:9px 16px;font:500 14px/1.2 var(--label,sans-serif);letter-spacing:.06em;text-transform:uppercase;color:var(--fg,#E6EBFA);text-decoration:none}'
      '.trsw a[aria-current]{background:#FFD86B;color:#0B1330}.trsw a:focus-visible{outline:2px solid #FFD86B;outline-offset:2px}@media (max-width:1000px){.wrap>*,.wrap>*>*{min-width:0;max-width:100%}.wrap>header>h1{white-space:normal!important}}@media (max-width:420px){.trsw a{padding:9px 8px;font-size:12px}}</style><!--TR-SWITCH-END-->')

def put_switch(s, here):
    s = re.sub(r'<!--TR-SWITCH-->.*?<!--TR-SWITCH-END-->', '', s, flags=re.S)
    sw = SW.replace('{a}', ' aria-current="page"' if here == 'tr' else '').replace('{b}', ' aria-current="page"' if here == 'rl' else '')
    i = s.index('</p>', s.index('<p class="lede">')) + 4
    return s[:i] + sw + s[i:]

tr = open(f'{REPO}/transport.html', encoding='utf-8').read()
tr = put_switch(tr, 'tr')
open(f'{REPO}/transport.html', 'w', encoding='utf-8').write(tr)

s = tr
# данные: v — квартир на полосо-километр
j = s.index('{', s.index('const DATA')); D, end = json.JSONDecoder().raw_decode(s[j:])
for f in D['features']:
    p = f['properties']; r = RL['d'].get(SLUG.get(p['n']))
    p['v'] = r['per_lane_km'] if r else None
    p['rl'] = {'fl': r['flats'], 'fe': round(100 * r['flats_est'] / r['flats']) if r and r['flats'] else 0, 'lk': r['lane_km'], 'rd': r['roads'][:5]} if r else None
s = s[:j] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + s[j + end:]
# настройки карты
j = s.index('{', s.index('const CFG')); C, end = json.JSONDecoder().raw_decode(s[j:])
C.update({'kind': 'rl', 'fmt': 'int', 'dir': -1,
          'bins': [[0, 150, 'до 150 · свободнее', 'var(--c5)'], [150, 250, '150–250', 'var(--c4)'], [250, 350, '250–350', 'var(--c3)'],
                   [350, 450, '350–450', 'var(--c2)'], [450, 1e9, 'больше 450 · тесно', 'var(--c1)']],
          'ha': 'Больше всего жилья на дороги', 'hb': 'Меньше всего жилья на дороги', 'flabel': 'Квартир на полосо-километр',
          'fhint': 'чем больше, тем теснее на дорогах в часы пик · можно выбрать несколько', 'cardsub': 'квартир на 1 полосо-километр крупных дорог', 'nodata': 'Нет данных'})
s = s[:j] + json.dumps(C, ensure_ascii=False, separators=(',', ':')) + s[j + end:]
s = s.replace('const fmt=CFG.fmt==="rub"?', 'const fmt=CFG.fmt==="int"?(v=>Math.round(v).toLocaleString("ru-RU")):CFG.fmt==="rub"?', 1)
s = s.replace('function card(p){\n', '''function card(p){
  if(CFG.kind==="rl"){const r=p.rl;return `<div class="stats">
    <div class="stat"><div class="l">Квартир в районе</div><div class="v">≈ ${num(r.fl)}</div><div class="s">по домам OpenStreetMap${r.fe?", "+r.fe+" % из них — оценка по площади и этажам":""}</div></div>
    <div class="stat"><div class="l">Крупные дороги</div><div class="v">${r.lk.toFixed(0)}</div><div class="s">полосо-км в районе и в 1 км вокруг (с весом)</div></div></div>
    ${r.rd.length?`<div class="note">Главные дороги рядом: ${r.rd.join(", ")}.</div>`:""}`}
''', 1)
s = s.replace('const meta=p=>CFG.kind==="hs"?', 'const meta=p=>CFG.kind==="rl"?`≈ ${num(p.rl.fl)} квартир · ${p.rl.lk.toFixed(0)} полосо-км`:CFG.kind==="hs"?', 1)
# тексты
s = re.sub(r'<h1>Транспорт</h1>\s*<p class="lede">.*?</p>', '<h1>На автомобиле: дороги и пробки</h1>\n    <p class="lede">Где жилья настроили много, а дороги остались прежними — и утром и вечером тесно. '
           'Для каждого района: сколько квартир приходится на один полосо-километр крупных дорог в районе и в километре вокруг. Чем больше, тем теснее в час пик. '
           'Это не замер пробок, а соотношение домов и дорог по OpenStreetMap. Наведите на район, чтобы увидеть цифры, нажмите, чтобы открыть его страницу.</p>', s, count=1, flags=re.S)
s = re.sub(r'<section class="method">.*?</section>', '<section class="method"><h2>Как считали</h2>'
           '<p><b>Квартиры.</b> Сумма квартир в жилых домах района по OpenStreetMap (у 77 % многоквартирных домов Москвы число квартир указано). '
           f'Где не указано, оценили по площади дома и этажности: в среднем {str(RL["k_m2_per_flat"]).replace(".", ",")} м² площади этажа на квартиру — так выходит по домам, где квартиры известны.</p>'
           '<p><b>Дороги.</b> Полосо-километры крупных дорог — магистралей (МКАД, хорды, вылетные шоссе), больших улиц и проспектов — в самом районе и в полосе 1 км вокруг него: по ним жители и выезжают. '
           'Число полос — из OpenStreetMap (у таких дорог оно указано почти везде), без отметки — 2 полосы на двустороннюю и 1 на одностороннюю. '
           'Скоростные дороги без светофоров пропускают больше, поэтому магистраль весит вдвое больше обычной улицы, вылетное шоссе — в полтора раза, улица районного значения — три четверти.</p>'
           '<p><b>Чего здесь нет.</b> Это не замер пробок: открытых данных о загрузке улиц по районам нет (Яндекс публиковал исследования только по городу целиком — в 2014 и 2017 годах). '
           'Не учтены светофоры, сужения и куда именно все едут. Метро отдельно — на соседней вкладке «На метро».</p></section>', s, count=1, flags=re.S)
s = re.sub(r'(<p class="small"[^>]*>|<footer[^>]*>)?Источники?:.*?</(p|footer)>', lambda m: m.group(0), s)
s = s.replace('aria-label="Транспортная доступность районов Москвы"', 'aria-label="Нагрузка на дороги по районам Москвы"')
# шапка страницы
s = re.sub(r'<title>.*?</title>', '<title>Пробки по районам Москвы: где много жилья и мало дорог</title>', s, count=1, flags=re.S)
def meta(s, attr, key, val):
    pat = re.compile(rf'<meta {attr}="{re.escape(key)}" content="[^"]*">')
    tag = f'<meta {attr}="{key}" content="{E(val)}">'
    return pat.sub(tag, s, count=1) if pat.search(s) else s.replace('</title>', '</title>' + tag, 1)
DESC = 'Нагрузка на дороги в районах Москвы: сколько квартир приходится на крупные дороги вокруг. Где в час пик теснее — карта всех районов внутри МКАД.'
s = meta(s, 'name', 'description', DESC)
s = meta(s, 'property', 'og:title', 'Пробки по районам Москвы: где много жилья и мало дорог')
s = meta(s, 'property', 'og:description', DESC)
s = meta(s, 'property', 'og:url', 'https://www.mskatlas.ru/roads.html')
s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="https://www.mskatlas.ru/roads.html">', s)
s = put_switch(s, 'rl')
open(f'{REPO}/roads.html', 'w', encoding='utf-8').write(s)
sm = open(f'{REPO}/sitemap.xml', encoding='utf-8').read()
if '/roads.html<' not in sm:
    sm = sm.replace('</urlset>', f'  <url><loc>https://www.mskatlas.ru/roads.html</loc><lastmod>{RL["date"]}</lastmod></url>\n</urlset>')
    open(f'{REPO}/sitemap.xml', 'w', encoding='utf-8').write(sm)
print('roads.html готов, данные', ddmm)
