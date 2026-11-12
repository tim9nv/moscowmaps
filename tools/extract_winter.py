#!/usr/bin/env python3
"""Зимний слой «За город» из OpenStreetMap → tools/data/winter_osm.json.

Горнолыжные курорты собираются из склонов (piste:type=downhill) и подъёмников (aerialway) кучками по 1,5 км;
название — ближайший подписанный landuse=winter_sports / sport=skiing в 2 км. Лыжные маршруты — отношения
route=ski / route=piste (piste:type=nordic) с названием, длина — по линиям участников. Беговые трассы рядом с
курортами и базами — линии piste:type=nordic (для мини-схем).

Запуск: python3 tools/extract_winter.py /tmp/moscow.osm.pbf /tmp/moscow_oblast.osm.pbf /tmp/kaluga_oblast.osm.pbf /tmp/tula_oblast.osm.pbf
Ручные поля (перепад, прокат, сайт) — отдельно в tools/data/winter.json, этот файл их не трогает.
"""
import json, math, os, sys
import osmium

C = (55.752, 37.6175)
RADIUS = 125  # км
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def km(a, b):
    k = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * 111.32, (a[1] - b[1]) * 111.32 * k)


def length(pts):
    return sum(km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def simplify(pts, tol=0.00012):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        num = abs((b[1] - a[1]) * (a[0] - p[0]) - (a[1] - p[1]) * (b[0] - a[0]))
        den = math.hypot(b[1] - a[1], b[0] - a[0]) or 1e-12
        d = num / den
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]


R5 = lambda pts: [[round(p[0], 5), round(p[1], 5)] for p in pts]


class Rel(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.rels = {}

    def relation(self, r):
        t = r.tags
        if t.get('route') in ('ski', 'piste') and t.get('piste:type', 'nordic') == 'nordic' and t.get('name'):
            self.rels[r.id] = dict(name=t.get('name'), ways=[m.ref for m in r.members if m.type == 'w'],
                                   frm=t.get('from', ''), to=t.get('to', ''))


class Ways(osmium.SimpleHandler):
    def __init__(self, want):
        super().__init__(); self.want = want
        self.down, self.lift, self.nordic, self.named, self.memb = [], [], [], [], {}

    def geom(self, w):
        try:
            return [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
        except Exception:
            return []

    def way(self, w):
        t = w.tags
        pt, aw = t.get('piste:type'), t.get('aerialway')
        need = w.id in self.want or pt in ('downhill', 'nordic') or (aw and aw not in ('pylon', 'station', 'goods')) \
            or t.get('landuse') == 'winter_sports' or ('skiing' in (t.get('sport') or '') and t.get('name'))
        if not need:
            return
        g = self.geom(w)
        if len(g) < 2:
            return
        mid = g[len(g) // 2]
        if w.id in self.want:
            self.memb[w.id] = g
        if km(mid, C) > RADIUS:
            return
        if pt == 'downhill':
            self.down.append(dict(d=t.get('piste:difficulty', ''), n=t.get('name', ''), g=g))
        elif aw and aw not in ('pylon', 'station', 'goods', 'zip_line'):
            self.lift.append(dict(t=aw, n=t.get('name', ''), g=g))
        elif pt == 'nordic':
            self.nordic.append(dict(n=t.get('name', ''), s=t.get('piste:grooming', ''), g=g))
        if (t.get('landuse') == 'winter_sports' or 'skiing' in (t.get('sport') or '')) and t.get('name'):
            lat = sum(p[0] for p in g) / len(g); lon = sum(p[1] for p in g) / len(g)
            self.named.append(dict(n=t.get('name'), c=(lat, lon), web=t.get('website', '') or t.get('contact:website', '')))

    def node(self, n):
        t = n.tags
        if ('skiing' in (t.get('sport') or '') or t.get('landuse') == 'winter_sports') and t.get('name'):
            c = (n.location.lat, n.location.lon)
            if km(c, C) <= RADIUS:
                self.named.append(dict(n=t.get('name'), c=c, web=t.get('website', '') or t.get('contact:website', '')))


def main(files):
    rels = {}
    for f in files:
        h = Rel(); h.apply_file(f); rels.update(h.rels)
    want = {w for r in rels.values() for w in r['ways']}
    W = dict(down=[], lift=[], nordic=[], named=[], memb={})
    for f in files:
        h = Ways(want); h.apply_file(f, locations=True)
        for k in ('down', 'lift', 'nordic', 'named'):
            W[k] += h.__dict__[k]
        W['memb'].update(h.memb)
    # курорты
    objs = [('d', o) for o in W['down']] + [('l', o) for o in W['lift']]
    cl = []
    for k, o in objs:
        c = o['g'][len(o['g']) // 2]
        for g in cl:
            if km(g['c'], c) < 1.5:
                g['o'].append((k, o)); break
        else:
            cl.append(dict(c=c, o=[(k, o)]))
    resorts = []
    for g in cl:
        dn = [o for k, o in g['o'] if k == 'd']
        lf = [o for k, o in g['o'] if k == 'l']
        if len(dn) < 2:
            continue
        pts = [p for o in dn + lf for p in o['g']]
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        near = sorted(W['named'], key=lambda o: km(o['c'], c))
        nm = near[0] if near and km(near[0]['c'], c) < 2 else None
        resorts.append(dict(c=[round(c[0], 5), round(c[1], 5)], osm_name=nm['n'] if nm else '', osm_web=nm['web'] if nm else '',
                            n_pistes=len(dn), km_pistes=round(sum(length(o['g']) for o in dn), 1), n_lifts=len(lf),
                            lifts_by=dict((t, sum(1 for o in lf if o['t'] == t)) for t in sorted({o['t'] for o in lf})),
                            pistes=[[o['d'], R5(simplify(o['g'], 0.00005))] for o in dn],
                            lifts=[[o['t'], R5([o['g'][0], o['g'][-1]])] for o in lf],
                            msk_km=round(km(c, C), 1)))
    resorts.sort(key=lambda r: -r['n_pistes'])
    # маршруты
    routes = []
    for rid, r in rels.items():
        segs = [W['memb'][w] for w in r['ways'] if w in W['memb']]
        if not segs:
            continue
        L = sum(length(s) for s in segs)
        allp = [p for s in segs for p in s]
        c = (sum(p[0] for p in allp) / len(allp), sum(p[1] for p in allp) / len(allp))
        if km(c, C) > RADIUS or L < 3:
            continue
        routes.append(dict(id=rid, name=r['name'], km=round(L, 1), frm=r['frm'], to=r['to'], c=[round(c[0], 5), round(c[1], 5)],
                           g=[R5(simplify(s, 0.0003)) for s in segs]))
    routes.sort(key=lambda r: -r['km'])
    # беговые линии (для мини-схем; только длиннее 300 м)
    nordic = [[o['s'], R5(simplify(o['g'], 0.0001))] for o in W['nordic'] if length(o['g']) > 0.3]
    out = dict(date='2026-11-12', source='OpenStreetMap (выгрузки download.openstreetmap.fr)', resorts=resorts, routes=routes, nordic=nordic)
    p = os.path.join(ROOT, 'tools/data/winter_osm.json')
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('курортов', len(resorts), 'маршрутов', len(routes), 'беговых линий', len(nordic), 'файл', os.path.getsize(p) // 1024, 'КБ')
    for r in resorts[:25]:
        print(f"  {r['c']} {r['osm_name'] or '?'}: спусков {r['n_pistes']} ({r['km_pistes']} км), подъёмников {r['n_lifts']} {r['lifts_by']}, {r['msk_km']} км")
    for r in routes[:15]:
        print(f"  маршрут {r['name']}: {r['km']} км")


if __name__ == '__main__':
    main(sys.argv[1:])
