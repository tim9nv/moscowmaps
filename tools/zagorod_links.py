#!/usr/bin/env python3
"""Связи «районы ↔ За город» (идемпотентно). Запускать после build_zagorod.py и district_layout.py.

На странице района — блок «За город в вашу сторону»: 4 места, к которым из района ехать по пути
(направление от центра Москвы на район и на место близко). На странице места — «Ближе всего ехать из районов»:
4 района Москвы, ближайших к месту по прямой. Координаты мест — из разметки schema.org на их страницах,
районов — центр полигона из tools/data/districts.json.
"""
import glob, html, json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
C = (55.7520, 37.6175)  # Кремль
E = lambda s: html.escape(s, quote=True)


def bearing(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    x = math.sin(lo2 - lo1) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def km(a, b):
    k = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * k)


def centroid(g):
    ring = g['coordinates'][0] if g['type'] == 'Polygon' else max((p[0] for p in g['coordinates']), key=len)
    return (sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring))


def main():
    names = {n: s for s, n, o in json.load(open('tools/data/districts_list.json'))}
    feats = json.load(open('tools/data/districts.json'))['features']
    D = {}
    for f in feats:
        s = names.get(f['properties']['n'])
        if s and os.path.exists(f'rayon/{s}/index.html'):
            D[s] = (f['properties']['n'], centroid(f['geometry']))
    P = {}
    for f in glob.glob('zagorod/*/index.html'):
        s = open(f, encoding='utf-8').read()
        m = re.search(r'<script type="application/ld\+json">(\{"@context": "https://schema.org", "@type": "TouristAttraction".*?)</script>', s)
        if not m:
            continue
        ld = json.loads(m.group(1))
        kind = re.search(r'<p class="eyebrow">За город · ([^<]*)</p>', s)
        slug = f.split('/')[1]
        pt = (ld['geo']['latitude'], ld['geo']['longitude'])
        P[slug] = dict(name=ld['name'], kind=html.unescape(kind.group(1)) if kind else '', pt=pt,
                       br=bearing(C, pt), km=km(C, pt))

    # районы → места
    for s, (n, c) in D.items():
        br, far = bearing(C, c), km(C, c)
        def score(p):
            d = abs((p['br'] - br + 180) % 360 - 180)
            return d + (40 if p['km'] > 130 else 0) + (15 if p['km'] < 25 else 0)
        pick = sorted(P.items(), key=lambda kv: score(kv[1]))[:4]
        cards = ''.join(f'<a class="nb" href="../../zagorod/{k}/"><b>{E(p["name"])}</b><span>{E(p["kind"])} · ~{round(p["km"] / 5) * 5} км от центра</span></a>'
                        for k, p in pick)
        block = (f'<!--ZG-NEAR--><section><h2>За город в вашу сторону</h2>'
                 f'<p class="muted">Куда съездить на день или выходные, если ехать из района {E(n)}: места в том же направлении от центра Москвы. '
                 f'<a href="../../zagorod/">Все места «За город»</a>.</p><div class="nbs zgn">{cards}</div>'
                 f'<style>.zgn{{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}}.zgn .nb{{display:block;padding:12px 14px;border:1px solid var(--border,#27376B);border-radius:12px;text-decoration:none;color:inherit}}.zgn .nb b{{display:block;margin-bottom:4px}}.zgn .nb span{{font-size:13px;opacity:.75}}@media (hover:hover){{.zgn .nb:hover{{border-color:#FFD86B}}}}</style>'
                 f'</section><!--ZG-NEAR-END-->')
        f = f'rayon/{s}/index.html'
        h0 = h = open(f, encoding='utf-8').read()
        h = re.sub(r'<!--ZG-NEAR-->.*?<!--ZG-NEAR-END-->', '', h, flags=re.S)
        i = h.find('<section class="faq">')
        if i < 0:
            continue
        h = h[:i] + block + h[i:]
        if h != h0:
            open(f, 'w', encoding='utf-8').write(h)

    # места → районы
    for k, p in P.items():
        near = sorted(D.items(), key=lambda kv: km(kv[1][1], p['pt']))[:4]
        links = ', '.join(f'<a href="../../rayon/{s}/">{E(n)}</a>' for s, (n, c) in near)
        block = (f'<!--ZG-FROM--><p class="zg-note zg-from">Ближе всего ехать из районов Москвы: {links}. '
                 f'Что это за районы, сколько там стоит жильё и как с экологией — на их страницах.</p><!--ZG-FROM-END-->')
        f = f'zagorod/{k}/index.html'
        h0 = h = open(f, encoding='utf-8').read()
        h = re.sub(r'<!--ZG-FROM-->.*?<!--ZG-FROM-END-->', '', h, flags=re.S)
        m = re.search(r'(<section class="zg-sec"><h2>Как добраться</h2>.*?</section>)', h, re.S)
        if not m:
            continue
        h = h[:m.end()] .replace(m.group(1), m.group(1)[:-len('</section>')] + block + '</section>') + h[m.end():]
        if h != h0:
            open(f, 'w', encoding='utf-8').write(h)
    print('связи: районов', len(D), '· мест', len(P))


if __name__ == '__main__':
    main()
