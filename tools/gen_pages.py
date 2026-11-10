import json, re, os, math, html
from shapely.geometry import shape

import os as _os
TOOLS=_os.path.dirname(_os.path.abspath(__file__)); DATA=_os.path.join(TOOLS,'data'); ROOT=_os.path.dirname(TOOLS)
REPO = ROOT
BASE = 'https://www.mskatlas.ru'
s = open(f'{REPO}/index.html', encoding='utf-8').read()
js = open(f'{REPO}/assets/atlas.js', encoding='utf-8').read()
i = js.index('const DATA')
i = i + js[i:].index('=') + 1
while js[i] == ' ': i += 1
D, _ = json.JSONDecoder().raw_decode(js[i:])
F = D['features']
head_src = s[:s.index('<body')]
body0 = s[s.index('<body'):]
topbar = re.search(r'<header class="topbar">.*?</header>', body0, re.S).group(0)
topbar = topbar.replace(' aria-current="page"', '')

TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
  ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))
def slug(n):
    n = n.replace(' административный округ', '').lower()
    out = ''.join(TR.get(c, c if re.match(r'[a-z0-9]', c) else '-') for c in n)
    return re.sub(r'-+', '-', out).strip('-')

OKR = {"ЦАО":"Центральный","САО":"Северный","СВАО":"Северо-Восточный","ВАО":"Восточный","ЮВАО":"Юго-Восточный","ЮАО":"Южный",
       "ЮЗАО":"Юго-Западный","ЗАО":"Западный","СЗАО":"Северо-Западный","ЗелАО":"Зеленоградский","НАО":"Новомосковский","ТАО":"Троицкий"}
OKR_ORDER = list(OKR)
def okr_full(o): return f'{OKR.get(o, o)} административный округ'

for f in F: f['properties']['slug'] = slug(f['properties']['n'])
BY = {f['properties']['slug']: f for f in F}
P = lambda f: f['properties']
eco_rank = sorted(F, key=lambda f: (P(f)['i'], P(f).get('raw') or 0))
soc_F = [f for f in F if P(f).get('score') is not None]
soc_rank = sorted(soc_F, key=lambda f: -P(f)['score'])
tr_F = [f for f in F if P(f).get('tr')]
tr_rank = sorted(tr_F, key=lambda f: -P(f)['tr']['score'])
sp_F = [f for f in F if P(f).get('sp') and P(f)['sp'].get('s') is not None]
sp_rank = sorted(sp_F, key=lambda f: -P(f)['sp']['s'])
N = len(F)
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proscons
zhit = proscons.zhit; pl = proscons.pl; minut_rod = proscons.minut_rod
GREEN = proscons.load_green(REPO)
green_F = [f for f in F if (GREEN.get(P(f)['n']) or {}).get('pct') is not None]
green_rank = sorted(green_F, key=lambda f: -GREEN[P(f)['n']]['pct'])

def fmt(v): return '—' if v is None else f'{float(v):.1f}'.replace('.', ',')
def num(v): return '—' if v is None else f'{round(v):,}'.replace(',', ' ')
E = html.escape
def band(v, b=(3, 4.5, 6, 7.5, 99)):
    for k, x in enumerate(b):
        if v < x: return k + 1
    return 5
def hcol(v):
    for lim, c in [(370000,"#f3e7c9"),(410000,"#e6c58c"),(460000,"#d49a5d"),(530000,"#b5693f"),(1e12,"#7c3a2a")]:
        if v < lim: return c
LV = ["Очень тихо", "Тихо", "Средне", "Оживлённо", "Очень оживлённо"]
TYPES = {"npz":"НПЗ","msz":"Мусоросжигательный завод","abz":"Асфальтобетонный завод","tec":"ТЭЦ","ochist":"Очистные сооружения","rad":"Радиационно опасный объект","waste":"Свалка, мусоросортировка","air":"Аэропорт","prom":"Промзона"}

import hashlib, urllib.parse
ARMS = json.load(open(_os.path.join(DATA,'arms.json')))
def local_arms(sl): return os.path.exists(f'{REPO}/rayon/gerb/{sl}.png') and os.path.getsize(f'{REPO}/rayon/gerb/{sl}.png') > 500
def arms(sl): return local_arms(sl) or bool((ARMS.get(sl) or {}).get('file'))
def arms_src(sl, pre):
    if local_arms(sl): return f'{pre}gerb/{sl}.png'
    f = ARMS[sl]['file'].replace(' ', '_'); h = hashlib.md5(f.encode()).hexdigest(); q = urllib.parse.quote(f)
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/250px-{q}" + ('.png' if f.lower().endswith('.svg') else '')

def tile(eyebrow, big, rk, width, color, warn=False):
    st = ' style="color:var(--warn)"' if warn else ''
    return (f'<div class="tile"><div class="eyebrow">{eyebrow}</div><div class="big"{st}>{big}</div>'
            f'<div class="rk">{rk}</div><div class="bar"><i style="width:{width:.0f}%;background:{color}"></i></div></div>')
def stat(l, c, per, p10, empty='нет объектов'):
    tail = f' · {fmt(p10)} на 10 тыс.' if p10 is not None else ''
    return (f'<div class="stat"><div class="l">{l}</div><div class="v">{num(c)}</div>'
            f'<div class="s">{"1 на " + num(per) + " чел." if per else empty}{tail}</div></div>')

# ---------- district outline svg ----------
def svg_for(f, nbs):
    geoms = [(f, shape(f['geometry']))] + [(n, shape(n['geometry'])) for n in nbs]
    minx = min(g.bounds[0] for _, g in geoms); miny = min(g.bounds[1] for _, g in geoms)
    maxx = max(g.bounds[2] for _, g in geoms); maxy = max(g.bounds[3] for _, g in geoms)
    k = math.cos(math.radians((miny + maxy) / 2))
    W, H, pad = 600, 420, 18
    sx = (W - 2 * pad) / ((maxx - minx) * k); sy = (H - 2 * pad) / (maxy - miny); sc = min(sx, sy)
    ox = (W - (maxx - minx) * k * sc) / 2; oy = (H - (maxy - miny) * sc) / 2
    pr = lambda x, y: (ox + (x - minx) * k * sc, oy + (maxy - y) * sc)
    def d_of(g):
        polys = [g] if g.geom_type == 'Polygon' else list(g.geoms)
        out = []
        for pg in polys:
            for ring in [pg.exterior] + list(pg.interiors):
                pts = [pr(x, y) for x, y in ring.coords]
                out.append('M' + 'L'.join(f'{a:.1f},{b:.1f}' for a, b in pts) + 'Z')
        return ''.join(out)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Схема района {E(P(f)["n"])} и соседних районов" class="dsvg">']
    labels = []
    for n, g in geoms[1:]:
        parts.append(f'<a href="../{P(n)["slug"]}/"><path class="nb" d="{d_of(g)}"><title>{E(P(n)["n"])}</title></path></a>')
        c = g.buffer(0).representative_point(); x, y = pr(c.x, c.y)
        labels.append(f'<text class="nbl" x="{x:.0f}" y="{y:.0f}">{E(P(n)["n"])}</text>')
    g = geoms[0][1]
    parts.append(f'<path class="me" d="{d_of(g)}"/>')
    c = g.buffer(0).representative_point(); x, y = pr(c.x, c.y)
    labels.append(f'<text class="mel" x="{x:.0f}" y="{y:.0f}">{E(P(f)["n"])}</text>')
    parts += labels + ['</svg>']
    return ''.join(parts)

EXTRA_CSS = '''<style>
.crumbs{font-size:14px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px}.crumbs a{color:var(--accent);text-decoration:none}
.lead{font-size:17px;line-height:1.6;max-width:70ch;margin:10px 0 0}
.golink{display:inline-flex;align-items:center;gap:6px;padding:10px 16px;border-radius:10px;background:var(--fg);color:var(--bg)!important;text-decoration:none;font-size:15px;font-weight:500;align-self:flex-start}
.golink:hover{opacity:.88}.golink:focus-visible{outline:2px solid var(--fg);outline-offset:2px}
.dmap{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.dsvg{display:block;width:100%;height:auto}
.dsvg .nb{fill:var(--soft);stroke:var(--line);stroke-width:1.2;cursor:pointer}.dsvg a:hover .nb,.dsvg a:focus .nb{fill:var(--e2)}
.dsvg .me{fill:var(--accent);fill-opacity:.85;stroke:var(--fg);stroke-width:1.6}
.dsvg text{font:500 12px var(--body);text-anchor:middle;dominant-baseline:middle;pointer-events:none;paint-order:stroke;stroke:var(--surface);stroke-width:3px;fill:var(--muted)}
.dsvg .mel{font:700 14px var(--display);fill:var(--fg)}
.okr h2{margin-top:6px}.okr .chips{margin-bottom:6px}
.dhead{display:flex;gap:16px;align-items:center}.dhead .arms{width:76px;height:auto;flex:none;object-fit:contain}
@media (max-width:520px){.dhead .arms{width:56px}}
.chips a img{width:18px;height:22px;object-fit:contain;vertical-align:-5px;margin-right:6px}
.pcg{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}
.pcg>div{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 16px}
.pcg h3{margin:0 0 6px;font-size:15px}.pcp h3{color:var(--s5)}.pcm h3{color:var(--warn)}
.pcg ul{margin:0;padding-left:18px}.pcg li{margin:4px 0;font-size:15px;line-height:1.5}
.faq details{border-bottom:1px solid var(--line);padding:10px 0}.faq summary{cursor:pointer;font-weight:600;font-size:15.5px}
.faq details p{margin:8px 0 0;font-size:15px;line-height:1.55;max-width:70ch}
.foot{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:14px}.foot a{color:var(--accent)}
</style>'''

def head(title, desc, canon, depth, img=None):
    h = head_src
    # свои description, canonical и og у каждой страницы: убираем те, что пришли из шапки главной
    h = re.sub(r'<meta name="description"[^>]*>\n?|<link rel="canonical"[^>]*>\n?|<meta property="og:[^>]*>\n?', '', h)
    h = re.sub(r'<title>.*?</title>', f'<title>{E(title)}</title>', h, count=1, flags=re.S)
    meta = (f'<meta name="description" content="{E(desc)}">\n<link rel="canonical" href="{canon}">\n'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{E(title)}">'
            f'<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">'
            + (f'<meta property="og:image" content="{img}">' if img else '') + f'<meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="Атлас районов Москвы">\n')
    h = h.replace('</title>', '</title>\n' + meta, 1)
    return h.replace('</head>', EXTRA_CSS + '\n</head>')

def fix_links(t, depth):
    pre = '../' * depth
    return re.sub(r'href="([a-z-]+\.html)', lambda m: f'href="{pre}{m.group(1)}', t)

def foot(depth):
    pre = '../' * depth
    return (f'<p class="foot">Данные: экорейтинг EcoStandard и замеры Мосэкомониторинга, цены — объявления Циана (ноябрь 2026), '
            f'транспорт, школы, поликлиники, спорт и магазины — OpenStreetMap (ноябрь 2026), население — Росстат и Wikidata 2025, гербы — Викисклад. '
            f'Подробно о методике — на страницах <a href="{pre}ecology.html">экологии</a>, <a href="{pre}housing.html">цен</a>, '
            f'<a href="{pre}transport.html">транспорта</a>, <a href="{pre}social.html">городской среды</a> и <a href="{pre}climate.html">географии</a>. '
            f'<a href="{pre}rayon/">Все районы Москвы</a> · <a href="{pre}reyting/">Рейтинги районов</a>: <a href="{pre}reyting/luchshie-rayony/">лучшие</a>, <a href="{pre}reyting/ekologiya/">экология</a>, <a href="{pre}reyting/zelenye-rayony/">зелёные</a>, <a href="{pre}reyting/deshevye-rayony/">дешёвые</a>, <a href="{pre}reyting/transport/">транспорт</a>, <a href="{pre}reyting/dlya-semi-s-detmi/">для семьи</a>.</p>')

def page(f):
    p = P(f); sl = p['slug']; n = p['n']; o = p['o']
    nbs = [BY[x] for x in (p.get('nb') or []) if x in BY]
    er = eco_rank.index(f) + 1
    title = f'Район {n} ({o}): цены на квартиры, экология, транспорт, плюсы и минусы'
    bits = [f'{n} — район {o} Москвы' + (f', {num(p["pop"])} {zhit(p["pop"])}' if p.get('pop') else '')]
    if p.get('hp'): bits.append(f'метр жилья на вторичке около {num(p["hp"]/1000)} тыс. ₽ ({p["hrk"]}-е место из 125 по цене)')
    bits.append(f'экологический балл {fmt(p["i"])} из 10 (чем меньше, тем чище), {er}-е место по чистоте')
    if p.get('tr'): bits.append(f'до центра около {p["tr"]["tmed"]} {minut_rod(p["tr"]["tmed"])}')
    desc = '; '.join(bits) + '. Школы, поликлиники, спорт, парки и микроклимат в сравнении со всеми районами Москвы.'
    lead = bits[0] + '. ' + '. '.join(x[0].upper() + x[1:] for x in bits[1:]) + '.' if len(bits) > 1 else bits[0] + '.'
    canon = f'{BASE}/rayon/{sl}/'
    tiles = []
    tiles.append(tile('Цена за м²', f'{num(p["hp"]/1000)}<span style="font-size:18px"> тыс. ₽</span>' if p.get('hp') else '—',
                      f'{p["hrk"]}-е место из 125 по цене' if p.get('hp') else 'нет данных',
                      min(100, p['hp']/10000) if p.get('hp') else 0, hcol(p['hp']) if p.get('hp') else 'none'))
    tiles.append(tile('Экология · 10 грязно', fmt(p['i']), f'{er}-е место из {N} по чистоте', p['i']*10, f'var(--e{band(p["i"])})', p['i'] >= 6))
    if p.get('tr'): tiles.append(tile('Транспорт', fmt(p['tr']['score']), f'{tr_rank.index(f)+1}-е место из {len(tr_F)} · до центра {p["tr"]["tmed"]} мин', p['tr']['score']*10, f'var(--s{band(p["tr"]["score"])})'))
    if p.get('score') is not None: tiles.append(tile('Соцобъекты', fmt(p['score']), f'{soc_rank.index(f)+1}-е место из {len(soc_F)}', p['score']*10, f'var(--s{band(p["score"])})', p['score'] < 4.5))
    if f in sp_F: tiles.append(tile('Спорт', fmt(p['sp']['s']), f'{sp_rank.index(f)+1}-е место из {len(sp_F)}', p['sp']['s']*10, f'var(--s{band(p["sp"]["s"])})'))
    if p.get('lv'): tiles.append(tile('Оживлённость', f'<span style="font-size:20px;line-height:1.25;display:block;padding-top:8px">{LV[p["lv"]["l"]]}</span>', f'{num(p["lv"]["d"])} кафе и магазинов на км²', (p['lv']['l']+1)*20, 'var(--accent)'))
    sec = []
    # housing & transport
    if p.get('hp') or p.get('tr'):
        st = []
        if p.get('hp'): st.append(f'<div class="stat"><div class="l">Двушка 54 м²</div><div class="v">≈ {fmt(p["hp"]*54/1e6)} млн ₽</div><div class="s">по средней цене метра на вторичке</div></div>')
        if p.get('tr'):
            st.append(f'<div class="stat"><div class="l">До станции</div><div class="v">{p["tr"]["walk"]} мин</div><div class="s">пешком от типичной точки района · {p["tr"]["cov"]} % территории в 1 км от станции</div></div>')
            st.append(f'<div class="stat"><div class="l">До центра</div><div class="v">{p["tr"]["tmed"]} мин</div><div class="s">типичная поездка до станций у Кремля</div></div>')
        txt = ''
        if p.get('tr'):
            ss = p['tr']['st']
            txt = ('Станции в районе: ' + '; '.join(E(x[0]) + ' (' + (', '.join(x[2]) if x[1] != 'mcc' else 'МЦК') + ')' for x in ss) + '.') if ss else 'Внутри района нет станций метро, МЦК и МЦД.'
            txt = f'<p class="small" style="margin-top:10px">{txt}</p>'
        if p.get('hp'): txt += f'<p class="small">Цена — медиана цены метра в объявлениях о продаже квартир на вторичке на Циане (ноябрь 2026, {num(p.get("hcnt"))} {pl(p.get("hcnt") or 0,"объявление","объявления","объявлений")} в районе).</p>'
        sec.append(f'<section><h2>Жильё и транспорт</h2><div class="stats">{"".join(st)}</div>{txt}</section>')
    # ecology
    fac = [f'<div><span>База: EcoStandard и замеры воздуха<span class="note">EcoStandard {fmt(p["a"])} · замеры {p["b"]}</span></span><b>{fmt(0.6*p["a"]+0.4*p["b"])}</b></div>']
    if p.get('rb'): fac.append(f'<div><span>Москва-река или Яуза у берега</span><b>+{fmt(p["rb"])}</b></div>')
    if p.get('pb'): fac.append('<div><span>Объекты в радиусе 3 км<span class="note">' + '; '.join(E(x[1]) + (f' — {fmt(x[2])} км' if x[2] else ' — в районе') for x in p['s']) + f'</span></span><b>+{fmt(p["pb"])}</b></div>')
    if p.get('tb'): fac.append(f'<div><span>Загруженные магистрали<span class="note">{E(", ".join(p["r"]))}</span></span><b>+{fmt(p["tb"])}</b></div>')
    if p.get('wb'): fac.append(f'<div><span>Подветренная сторона города</span><b>+{fmt(p["wb"])}</b></div>')
    sec.append(f'<section><h2>Экология района {E(n)}</h2><div class="facts">{"".join(fac)}</div>' + (f'<p class="small" style="margin-top:10px">{E(p["t"])}</p>' if p.get('t') else '') +
               f'<p class="small" style="margin-top:10px">Итоговый балл {fmt(p["i"])} из 10, чем меньше, тем чище.' + (f' Сумма составляющих {fmt(p["raw"])} приведена к шкале 1–10.' if p.get("raw") and abs(p["raw"]-p["i"])>0.15 else '') + f' <a href="../../ecology.html">Карта экологии всех районов</a>.</p></section>')
    if p.get('score') is not None:
        sec.append(f'<section><h2>Школы, детские сады и поликлиники</h2><div class="stats">{stat("Школы (здания)",p["school"],p["school_per"],p["school_10k"])}{stat("Детские сады",p["kinder"],p["kinder_per"],p["kinder_10k"])}{stat("Поликлиники и больницы",p["clinic"],p["clinic_per"],p["clinic_10k"])}</div>'
                   f'<p class="small" style="margin-top:10px">Образование {fmt(p["edu"])} из 10 · здравоохранение {fmt(p["med"])} из 10. Школа считается по зданиям: у одной школы-комплекса их бывает несколько.</p></section>')
    if p.get('sp'):
        q = p['sp']; lv = p['lv']
        sec.append(f'<section><h2>Спорт и жизнь вокруг</h2><div class="stats">{stat("Бассейны",q["pool"],q["pp"],q["p10"])}{stat("Спортзалы и клубы",q["halls"],q["hp"],q["h10"])}{stat("Площадки и воркауты",q["grounds"],q["gp"],q["g10"])}'
                   f'<div class="stat"><div class="l">Оживлённость</div><div class="v">{LV[lv["l"]]}</div><div class="s">{num(lv["f"])} кафе и ресторанов · {num(lv["h"])} {pl(lv["h"],"магазин","магазина","магазинов")} · {num(lv["d"])} на км²</div></div></div>'
                   f'<p class="small" style="margin-top:10px">Спорт {fmt(q["s"])} из 10 · <a href="../../sport.html">карта спорта по районам</a>. Оживлённость — кафе, рестораны, бары и магазины на квадратный километр; это характеристика, а не оценка.</p></section>')
    if p.get('cl'):
        c = p['cl']
        st = [f'<div class="stat"><div class="l">Средняя высота</div><div class="v">{round(c["h"])} м</div><div class="s">{"+" if c["rel"]>=0 else ""}{round(c["rel"])} м к середине города · перепад {round(c["rng"])} м</div></div>']
        if c.get('uhi') is not None:
            st.append(f'<div class="stat"><div class="l">Теплее за год</div><div class="v">+{fmt(c["uhi"])} °C</div><div class="s">к Подмосковью · ясной зимней ночью разница до +{fmt(c["night"])} °C</div></div>')
            st.append(f'<div class="stat"><div class="l">Влажность и ветер</div><div class="v">{fmt(76.6+c["rh"])} %</div><div class="s">{fmt(c["rh"])} % к Подмосковью · ветер {fmt(c["wind"])} м/с</div></div>')
        st.append(f'<div class="stat"><div class="l">Сырость и туманы</div><div class="v">{fmt(c["damp"])}</div><div class="s">из 10 · {round(c["low"])}% территории ниже 135 м</div></div>')
        t = ("Район на возвышенности: лучше продувается, туманы и холодный воздух не застаиваются." if c['rel'] >= 25 else
             "Район в низине: ночью сюда стекает холодный воздух, чаще туманы и сырость, в безветрие дольше держатся выбросы." if c['rel'] <= -20 else "По высоте район средний для Москвы: не возвышенность и не низина.")
        sec.append(f'<section><h2>Рельеф и микроклимат</h2><div class="stats">{"".join(st)}</div><p class="small" style="margin-top:10px">{t}</p></section>')
    ranks = {'er': er, 'soc_r': soc_rank.index(f)+1 if f in soc_F else None, 'soc_n': len(soc_F),
             'green_r': green_rank.index(f)+1 if f in green_F else None, 'green_n': len(green_F)}
    pros, cons, faq = proscons.build(p, ranks, GREEN, N)
    pc = ''
    if pros or cons:
        pc = ('<section class="pc"><h2>Плюсы и минусы района ' + E(n) + '</h2><div class="pcg">'
              + ('<div class="pcp"><h3>Плюсы</h3><ul>' + ''.join(f'<li>{E(x)}</li>' for x in pros) + '</ul></div>' if pros else '')
              + ('<div class="pcm"><h3>Минусы</h3><ul>' + ''.join(f'<li>{E(x)}</li>' for x in cons) + '</ul></div>' if cons else '')
              + '</div></section>')
    faq_html = '<section class="faq"><h2>Частые вопросы о районе ' + E(n) + '</h2>' + ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in faq) + '</section>'
    sec.append(faq_html)
    if nbs:
        sec.append('<section><h2>Соседние районы</h2><div class="chips">' + ''.join(f'<a href="../{P(x)["slug"]}/">{E(P(x)["n"])}</a>' for x in nbs) + '</div></section>')
    ld = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Районы Москвы","item":f"{BASE}/rayon/"},
        {"@type":"ListItem","position":2,"name":okr_full(o),"item":f"{BASE}/rayon/#{slug(o)}"},
        {"@type":"ListItem","position":3,"name":n,"item":canon}]}
    body = (f'<body>\n{fix_links(topbar,2)}\n<main class="wrap">\n'
            f'<nav class="crumbs" aria-label="Навигация"><a href="../">Все районы</a><span>›</span><a href="../#{slug(o)}">{OKR.get(o,o)} округ</a><span>›</span><span>{E(n)}</span></nav>\n'
            f'<header><div class="dhead">' + (f'<img class="arms" src="{arms_src(sl,"../")}" alt="Герб района {E(n)}" width="76" height="90" onerror="this.remove()">' if arms(sl) else '') + '<div>'
            f'<div class="eyebrow">{E(okr_full(o))}' + (f' · {num(p["pop"])} {zhit(p["pop"])} · {num(p["dens"])} чел/км² · {fmt(p["area"])} км²' if p.get('pop') else '') + '</div>'
            f'<h1>Район {E(n)}</h1></div></div><p class="lead">{E(lead)}</p>' + (f'<p class="hist">{E(p["hist"])}</p>' if p.get('hist') else '') + '</header>\n'
            f'<section class="scores">{"".join(tiles)}</section>\n' + pc + '\n'
            f'<section class="map" style="position:relative"><div class="zb" id="zb"><button data-z="in" aria-label="Приблизить">+</button><button data-z="out" aria-label="Отдалить">−</button><button data-z="reset" aria-label="Сбросить масштаб">⟲</button></div><svg id="dm" viewBox="0 0 600 460" role="img" aria-label="Карта района {E(n)}: улицы, станции, рельеф и источники загрязнения рядом"></svg><div class="small" style="padding:0 14px 8px">Приближайте двумя пальцами или колесом с Ctrl. Клик по соседнему району откроет его страницу.</div><div class="legend" id="dlg"></div></section>\n'
            + '\n'.join(sec) + f'\n{foot(2)}\n</main>\n<script>window.ATLAS_ROOT="../../";window.ATLAS_DISTRICT="{sl}";(function(){{var done=0;function go(){{if(done)return;done=1;var a=document.createElement("script");a.src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js";a.onload=function(){{var b=document.createElement("script");b.src="../../assets/atlas.js?v=20261110";document.body.appendChild(b)}};document.body.appendChild(a)}}var el=document.getElementById("dm");if("IntersectionObserver" in window&&el){{new IntersectionObserver(function(e,o){{if(e.some(function(x){{return x.isIntersecting}})){{o.disconnect();go()}}}},{{rootMargin:"600px"}}).observe(el)}}else go()}})();</script>\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n<script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faq]}, ensure_ascii=False)}</script>\n</body>\n</html>\n')
    return head(title, desc, canon, 2, f'{BASE}/rayon/gerb/{sl}.png' if local_arms(sl) else None) + body

def index_page():
    by = {}
    for f in F: by.setdefault(P(f)['o'], []).append(f)
    blocks = []
    for o in sorted(by, key=lambda x: OKR_ORDER.index(x) if x in OKR_ORDER else 99):
        fs = sorted(by[o], key=lambda f: P(f)['n'])
        blocks.append(f'<section class="okr" id="{slug(o)}"><h2>{E(okr_full(o))}</h2><div class="chips">' +
                      ''.join(f'<a href="{P(f)["slug"]}/">' + (f'<img src="{arms_src(P(f)["slug"],"")}" alt="" loading="lazy" onerror="this.remove()">' if arms(P(f)["slug"]) else '') + f'{E(P(f)["n"])}</a>' for f in fs) + '</div></section>')
    title = 'Все районы Москвы по округам — экология, цены, транспорт, школы | Атлас районов Москвы'
    desc = f'Список всех {N} районов Москвы по административным округам. У каждого района своя страница: цена метра, экология, транспорт, школы и поликлиники, спорт, рельеф и микроклимат.'
    body = (f'<body>\n{fix_links(topbar,1)}\n<main class="wrap">\n<header><h1>Все районы Москвы</h1><p class="lead">{N} районов по административным округам. '
            f'У каждого — страница с ценой метра, экологией, транспортом, школами и поликлиниками, спортом и микроклиматом. '
            f'Сравнить районы на карте можно <a href="../index.html">на главной</a>.</p></header>\n' + '\n'.join(blocks) + f'\n{foot(1)}\n</main>\n</body>\n</html>\n')
    return head(title, desc, f'{BASE}/rayon/', 1) + body

os.makedirs(f'{REPO}/rayon', exist_ok=True)
for f in F:
    d = f'{REPO}/rayon/{P(f)["slug"]}'; os.makedirs(d, exist_ok=True)
    open(f'{d}/index.html', 'w', encoding='utf-8').write(page(f))
open(f'{REPO}/rayon/index.html', 'w', encoding='utf-8').write(index_page())
json.dump([[P(f)['slug'], P(f)['n'], P(f)['o']] for f in F], open(_os.path.join(DATA,'districts_list.json'), 'w'), ensure_ascii=False)
print('pages', len(F), 'okrugs', sorted({P(f)['o'] for f in F}))

from datetime import date
urls=[f'{BASE}/','f'][:1]
pages=['index.html','housing.html','ecology.html','climate.html','transport.html','social.html','parks.html','sport.html','new-moscow.html']
locs=[f'{BASE}/']+[f'{BASE}/{x}' for x in pages[1:]]+[f'{BASE}/rayon/']+[f'{BASE}/rayon/{P(f)["slug"]}/' for f in F]
today=date.today().isoformat()
sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in locs)+'</urlset>\n'
open(f'{REPO}/sitemap.xml','w').write(sm)
open(f'{REPO}/robots.txt','w').write(f'User-agent: *\nAllow: /\nClean-param: v\n\nHost: {BASE}\nSitemap: {BASE}/sitemap.xml\n')
print('sitemap urls',len(locs))

# ================= rating landing pages =================
def pct_rank(vals):
    """value list -> dict index->0..10 percentile"""
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    out = {}
    for pos, k in enumerate(order): out[k] = 10 * pos / (len(vals) - 1)
    return out
def pr_map(fs, key):
    fs = [f for f in fs if key(f) is not None]
    vals = [key(f) for f in fs]; r = pct_rank(vals)
    return {P(f)['slug']: r[k] for k, f in enumerate(fs)}
g_pct = lambda f: (GREEN.get(P(f)['n']) or {}).get('pct')
PR = {
  'eco': pr_map(F, lambda f: -P(f)['i']),
  'tr': pr_map(F, lambda f: P(f)['tr']['score'] if P(f).get('tr') else None),
  'soc': pr_map(F, lambda f: P(f).get('score')),
  'edu': pr_map(F, lambda f: P(f).get('edu')),
  'green': pr_map(F, g_pct),
  'sport': pr_map(F, lambda f: P(f)['sp']['s'] if P(f).get('sp') else None),
  'cheap': pr_map(F, lambda f: -P(f)['hp'] if P(f).get('hp') else None),
}
def combo(f, w):
    sl = P(f)['slug']; s = t = 0
    for k, x in w.items():
        if sl in PR[k]: s += PR[k][sl] * x; t += x
    return round(s / t, 1) if t else None

def cell_dist(f, pre):
    sl = P(f)['slug']
    img = f'<img src="{arms_src(sl, pre)}" alt="" loading="lazy" onerror="this.remove()">' if arms(sl) else ''
    return f'<a href="{pre}{sl}/">{img}{E(P(f)["n"])}</a>'

RATINGS = [
 dict(slug='luchshie-rayony', h1='Лучшие районы Москвы для жизни: рейтинг 2026',
      title='Лучшие районы Москвы для жизни — рейтинг всех 125 районов 2026',
      desc='Рейтинг районов Москвы для жизни: экология, транспорт, школы и поликлиники, зелень и спорт. Все 125 районов с оценками и ценами на жильё.',
      intro='Общий рейтинг районов для жизни. Учитывает экологию (25 %), транспорт (20 %), школы, сады и поликлиники (20 %), долю зелени (20 %) и спорт (15 %). Цена жилья в балл не входит — она показана рядом, чтобы было видно, где хорошо и недорого.',
      w={'eco':25,'tr':20,'soc':20,'green':20,'sport':15}, metric='Балл', cols=['price','eco','tr']),
 dict(slug='ekologiya', h1='Экология районов Москвы: самые чистые и самые грязные районы',
      title='Экология районов Москвы 2026 — рейтинг самых чистых и грязных районов',
      desc='Экологический рейтинг всех 125 районов Москвы: где чище воздух, где рядом ТЭЦ, НПЗ, заводы и мусорные полигоны. Карта и оценки 2026 года.',
      intro='Районы по экологическому баллу: от самых чистых к самым грязным. Балл учитывает экорейтинг EcoStandard, замеры воздуха Мосэкомониторинга, заводы, ТЭЦ и мусорные объекты в радиусе 3 км, загруженные магистрали и розу ветров.',
      key=lambda f: P(f)['i'], asc=True, metric='Экобалл (10 — грязно)', cols=['src','green']),
 dict(slug='zelenye-rayony', h1='Самые зелёные районы Москвы',
      title='Самые зелёные районы Москвы — рейтинг по доле парков и деревьев',
      desc='Какие районы Москвы самые зелёные: доля деревьев и газонов, зелень на жителя, крупные парки и лесопарки в каждом из 125 районов.',
      intro='Районы по доле территории, занятой деревьями и газонами, по спутниковым снимкам. Рядом — сколько зелени приходится на одного жителя и какие крупные парки есть в районе.',
      key=lambda f: -(g_pct(f) or -1), asc=True, metric='Зелень, % территории', cols=['gpp','parks']),
 dict(slug='deshevye-rayony', h1='Самые дешёвые районы Москвы: где купить квартиру недорого',
      title='Самые дешёвые районы Москвы 2026 — цена квадратного метра на вторичке',
      desc='Где в Москве дешевле всего купить квартиру: средняя цена метра на вторичке по всем районам (ноябрь 2026) и экология, транспорт для каждого.',
      intro='Районы по средней цене квадратного метра на вторичке — от самых дешёвых к самым дорогим (объявления Циана, ноябрь 2026). Рядом экология и время до центра, чтобы было видно, где дёшево без больших минусов.',
      key=lambda f: P(f).get('hp') or 9e9, asc=True, metric='Цена, тыс. ₽/м²', cols=['two','eco','tr']),
 dict(slug='transport', h1='Районы Москвы с лучшей транспортной доступностью',
      title='Транспортная доступность районов Москвы — рейтинг по метро и времени до центра',
      desc='В каких районах Москвы удобнее всего добираться до центра: время в пути, расстояние до метро, МЦК и МЦД для всех 125 районов.',
      intro='Районы по транспортному баллу: время до центра на общественном транспорте, сколько идти до ближайшей станции метро, МЦК или МЦД и какая часть района в пешей доступности от станции.',
      key=lambda f: -(P(f)['tr']['score'] if P(f).get('tr') else -1), asc=True, metric='Транспорт, балл', cols=['tmed','walk']),
 dict(slug='dlya-semi-s-detmi', h1='Лучшие районы Москвы для семьи с детьми',
      title='Лучшие районы Москвы для семьи с детьми — школы, сады, парки, экология',
      desc='Рейтинг районов Москвы для семей с детьми: школы и детские сады на жителя, поликлиники, парки, экология и спорт.',
      intro='Рейтинг для семей с детьми. Больше всего весят школы и детские сады на жителя (30 %), затем экология (25 %), зелень и парки (20 %), поликлиники и прочая соцсфера (10 %) и спорт (15 %).',
      w={'edu':30,'eco':25,'green':20,'soc':10,'sport':15}, metric='Балл', cols=['school','green','eco']),
]
def col_val(c, f, pre):
    p = P(f); g = GREEN.get(p['n']) or {}
    if c == 'price': return ('Цена м²', f'{num(p["hp"]/1000)}&nbsp;тыс.&nbsp;₽' if p.get('hp') else '—')
    if c == 'eco': return ('Экология', fmt(p['i']))
    if c == 'tr': return ('До центра', f'{p["tr"]["tmed"]} мин' if p.get('tr') else '—')
    if c == 'src': return ('Источники рядом', E(', '.join(x[1] for x in (p.get('s') or [])[:2])) or '—')
    if c == 'green': return ('Зелень', f'{g["pct"]} %' if g.get('pct') is not None else '—')
    if c == 'gpp': return ('На жителя', f'{num(g["pp"])} м²' if g.get('pp') else '—')
    if c == 'parks': return ('Крупные парки', E(', '.join((g.get('parks') or [])[:2])) or '—')
    if c == 'two': return ('Двушка 54 м²', f'≈ {fmt(p["hp"]*54/1e6)} млн ₽' if p.get('hp') else '—')
    if c == 'tmed': return ('До центра', f'{p["tr"]["tmed"]} мин' if p.get('tr') else '—')
    if c == 'walk': return ('До станции пешком', f'{p["tr"]["walk"]} мин' if p.get('tr') else '—')
    if c == 'school': return ('Школы и сады', f'{fmt(p["edu"])} из 10' if p.get('edu') is not None else '—')
def metric_val(R, f):
    p = P(f)
    if 'w' in R: return fmt(combo(f, R['w']))
    if R['slug'] == 'ekologiya': return fmt(p['i'])
    if R['slug'] == 'zelenye-rayony': g = g_pct(f); return f'{g} %' if g is not None else '—'
    if R['slug'] == 'deshevye-rayony': return f'{num(p["hp"]/1000)}' if p.get('hp') else '—'
    if R['slug'] == 'transport': return fmt(p['tr']['score']) if p.get('tr') else '—'

RCSS = '''<style>.rt{width:100%;border-collapse:collapse;font-size:14.5px;font-variant-numeric:tabular-nums}
.rt th{text-align:left;font-size:12px;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:.03em;padding:6px 8px;border-bottom:1px solid var(--line)}
.rt td{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}.rt td.n{color:var(--muted);width:2.2em}.rt td.m{font-weight:600;white-space:nowrap}
.rt a{color:var(--fg);text-decoration:none;font-weight:500}.rt a:hover{text-decoration:underline}.rt img{width:16px;height:20px;object-fit:contain;vertical-align:-4px;margin-right:6px}
.rtw{overflow-x:auto}.rlinks{display:flex;flex-wrap:wrap;gap:8px}.rlinks a{border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:6px 12px;font-size:14px;text-decoration:none;color:var(--fg)}
.rlinks a[aria-current]{background:var(--fg);color:var(--bg)}
@media (max-width:600px){.rt .hx{display:none}}</style>'''

def rating_links(pre, cur=None):
    return '<nav class="rlinks" aria-label="Рейтинги">' + ''.join(
        f'<a href="{pre}{R["slug"]}/"' + (' aria-current="page"' if R['slug'] == cur else '') + f'>{E(R["h1"].split(":")[0])}</a>' for R in RATINGS) + '</nav>'

def rating_page(R):
    pre = '../../rayon/'
    if 'w' in R: fs = sorted([f for f in F if combo(f, R['w']) is not None], key=lambda f: -combo(f, R['w']))
    else: fs = sorted(F, key=R['key']) if R.get('asc') else sorted(F, key=R['key'], reverse=True)
    top = [P(f)['n'] for f in fs[:3]]; bot = [P(f)['n'] for f in fs[-3:]]
    rows = []
    for k, f in enumerate(fs, 1):
        extra = [col_val(c, f, pre) for c in R['cols']]
        rows.append(f'<tr><td class="n">{k}</td><td>{cell_dist(f, pre)}<div class="small">{E(P(f)["o"])}</div></td><td class="m">{metric_val(R, f)}</td>'
                    + ''.join(f'<td{" class=hx" if i else ""}>{v}</td>' for i, (_, v) in enumerate(extra)) + '</tr>')
    heads = ''.join(f'<th{" class=hx" if i else ""}>{h}</th>' for i, (h, _) in enumerate(col_val(c, fs[0], pre) for c in R['cols']))
    canon = f'{BASE}/reyting/{R["slug"]}/'
    summary = f'В лидерах — {", ".join(top)}. Замыкают список {", ".join(bot)}.'
    body = (f'<body>\n{fix_links(topbar, 2)}\n<main class="wrap">\n<nav class="crumbs"><a href="../">Рейтинги районов</a><span>›</span><span>{E(R["h1"].split(":")[0])}</span></nav>\n'
            f'<header><h1>{E(R["h1"])}</h1><p class="lead">{E(R["intro"])}</p><p class="lead">{E(summary)}</p></header>\n'
            f'<section class="rtw"><table class="rt"><thead><tr><th>№</th><th>Район</th><th>{R["metric"]}</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></section>\n'
            f'<section><h2>Другие рейтинги</h2>{rating_links("../", R["slug"])}</section>\n'
            f'<p class="small">Нажмите на район, чтобы открыть его страницу с картой, плюсами и минусами. Данные обновлены в ноябре 2026.</p>\n{foot(2)}\n</main>\n</body>\n</html>\n')
    return head(R['title'], R['desc'], canon, 2).replace('</head>', RCSS + '\n</head>') + body

def rating_hub():
    items = ''.join(f'<section><h2><a href="{R["slug"]}/" style="color:inherit">{E(R["h1"])}</a></h2><p class="small" style="margin:4px 0 0">{E(R["intro"])}</p></section>' for R in RATINGS)
    body = (f'<body>\n{fix_links(topbar, 1)}\n<main class="wrap">\n<header><h1>Рейтинги районов Москвы 2026</h1><p class="lead">Все 125 районов Москвы в рейтингах: лучшие для жизни, для семьи с детьми, самые экологичные, зелёные, дешёвые и с лучшим транспортом.</p></header>\n'
            f'{rating_links("")}\n{items}\n{foot(1)}\n</main>\n</body>\n</html>\n')
    return head('Рейтинги районов Москвы 2026 — лучшие, экологичные, зелёные, дешёвые', 'Рейтинги всех 125 районов Москвы: лучшие для жизни и для семьи с детьми, экология, зелень, цены на жильё и транспорт.', f'{BASE}/reyting/', 1).replace('</head>', RCSS + '\n</head>') + body

os.makedirs(f'{REPO}/reyting', exist_ok=True)
open(f'{REPO}/reyting/index.html', 'w', encoding='utf-8').write(rating_hub())
for R in RATINGS:
    os.makedirs(f'{REPO}/reyting/{R["slug"]}', exist_ok=True)
    open(f'{REPO}/reyting/{R["slug"]}/index.html', 'w', encoding='utf-8').write(rating_page(R))
# sitemap with ratings
locs2 = locs + [f'{BASE}/reyting/'] + [f'{BASE}/reyting/{R["slug"]}/' for R in RATINGS]
sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in locs2)+'</urlset>\n'
open(f'{REPO}/sitemap.xml','w').write(sm)
print('ratings', len(RATINGS), 'sitemap', len(locs2))
