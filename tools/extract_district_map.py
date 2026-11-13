"""Дома, зелень и промзоны для подробной карты района -> assets/dmap/<slug>.json
Запуск: python3 tools/extract_district_map.py /tmp/moscow.osm.pbf
Источник — OpenStreetMap. Для каждого района берём то, что внутри него и в полосе ~150 м вокруг (окрестности на карте притушены).
Дома мельче 40 м² (будки, гаражи) не берём.
Формат: {"o":[lon0,lat0], "b":[[точки, этажей|0, год|0, жилой 1/0, близость к шумным дорогам 0–3], ...], "g":[точки,...], "i":[[точки, вид], ...], "date":...}
точки — плоский список целых: первая точка (lon-lon0)*1e5, (lat-lat0)*1e5, дальше — приращения.
"""
import osmium, json, sys, os, re, datetime
from shapely.geometry import shape, Polygon, box, LineString
from shapely.strtree import STRtree
from shapely.geometry import Point
from shapely.prepared import prep
import math
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = {'apartments', 'residential', 'house', 'detached', 'semidetached_house', 'terrace', 'dormitory'}
def year(t):
    for k in ('start_date', 'building:start_date', 'construction_date'):
        v = t.get(k)
        if v:
            m = re.search(r'(1[6-9]\d\d|20[0-3]\d)', v)
            if m: return int(m.group(1))
    return 0
def levels(t):
    m = re.match(r'\d+', t.get('building:levels') or '')
    return min(int(m.group(0)), 120) if m else 0
feats = json.load(open(f'{REPO}/tools/data/districts.json', encoding='utf-8'))['features']
slugs = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
boxes, names = [], []
for f in feats:
    boxes.append(shape(f['geometry']).buffer(0).buffer(0.002)); names.append(slugs[f['properties']['n']])
tree = STRtree(boxes); pboxes = [prep(b) for b in boxes]
pin = [prep(shape(f['geometry']).buffer(0)) for f in feats]
out = {s: {'b': [], 'g': [], 'i': []} for s in names}
GREEN = lambda t: t.get('leisure') in ('park', 'garden', 'nature_reserve') or t.get('landuse') == 'forest' or t.get('natural') == 'wood'
IND = {'industrial': 'i', 'construction': 'c', 'garages': 'g', 'railway': 'r'}
# Шумные места: магистрали (motorway, trunk), крупные улицы (primary), железнодорожные станции и платформы
# (сама железная дорога — нет: владелец, 13.11.2026 — «поезд проехал, и всё», шумно у станций, где движуха).
# Это не замер шума, а расстояние от стены дома до такой дороги или станции.
BIG = {'motorway', 'motorway_link', 'trunk', 'trunk_link'}
MID = {'primary', 'primary_link'}
KX, KY = 111320 * math.cos(math.radians(55.75)), 110540
lines_big, lines_mid, stations, parks = [], [], [], []
class H(osmium.SimpleHandler):
    def way(self, w):
        t = w.tags; hw = t.get('highway')
        kind = 'big' if hw in BIG else 'mid' if hw in MID else None
        if not kind or t.get('tunnel') in ('yes', 'building_passage') or t.get('layer', '0').startswith('-'): return
        try: pts = [(n.lon * KX, n.lat * KY) for n in w.nodes]
        except Exception: return
        if len(pts) > 1: (lines_big if kind == 'big' else lines_mid).append(LineString(pts))
    def node(self, n):
        t = n.tags
        if t.get('railway') in ('station', 'halt') and t.get('station') != 'subway' and t.get('subway') != 'yes':
            stations.append(Point(n.location.lon * KX, n.location.lat * KY))
    def area(self, a):
        t = a.tags
        kind = 'b' if t.get('building') and t.get('building') != 'no' else 'g' if GREEN(t) else 'i' if t.get('landuse') in IND else None
        if not kind: return
        try:
            ring = [(n.lon, n.lat) for n in next(iter(a.outer_rings()))]
        except Exception: return
        if len(ring) < 4: return
        if kind == 'b':
            ar = abs(sum(ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1] for k in range(len(ring) - 1))) / 2 * 111320 * 111320 * math.cos(math.radians(ring[0][1]))
            if ar < 40: return
        if kind != 'b':
            try:
                pg = Polygon(ring).simplify(0.00004)
                if pg.is_empty or pg.geom_type != 'Polygon' or pg.area < 2e-7: return   # мельче ~0,15 га не берём
                ring = list(pg.exterior.coords)
            except Exception: return
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        pt = Point(cx, cy)
        for i in tree.query(pt):
            if not pboxes[i].contains(pt): continue
            if kind == 'b': out[names[i]]['b'].append((ring[:-1], levels(t), year(t), 1 if t.get('building') in RES else 0))
            elif kind == 'g': out[names[i]]['g'].append(ring[:-1])
            else: out[names[i]]['i'].append((ring[:-1], IND[t.get('landuse')]))
        if kind == 'g':
            try:
                pm = Polygon([(x * KX, y * KY) for x, y in ring])
                if pm.is_valid and pm.area >= 20000: parks.append(pm)   # парк, сквер или лес от 2 га
            except Exception: pass
H().apply_file(sys.argv[1], locations=True)
tb, tm, ts, tp = STRtree(lines_big), STRtree(lines_mid), STRtree(stations), STRtree(parks)
def park_near(ring):
    try: pg = Polygon([(x * KX, y * KY) for x, y in ring])
    except Exception: return False
    return near(tp, parks, pg) <= 300
def near(tree, lines, pt):
    i = tree.query_nearest(pt, max_distance=450)
    return min((lines[k].distance(pt) for k in i), default=999)
def noise(ring):
    try: pg = Polygon([(x * KX, y * KY) for x, y in ring])
    except Exception: return 0
    db, dm, ds = near(tb, lines_big, pg), near(tm, lines_mid, pg), near(ts, stations, pg)
    return 3 if db <= 100 or dm <= 50 or ds <= 100 else 2 if db <= 250 or dm <= 100 or ds <= 200 else 1 if db <= 400 or dm <= 200 or ds <= 300 else 0
share = {}
os.makedirs(f'{REPO}/assets/dmap', exist_ok=True)
tot = 0
for i, s in enumerate(names):
    x0, y0 = boxes[i].bounds[:2]
    def enc(ring):
        q = [(round((lon - x0) * 1e5), round((lat - y0) * 1e5)) for lon, lat in ring]
        o = [q[0][0], q[0][1]]
        for a, b in zip(q, q[1:]): o += [b[0] - a[0], b[1] - a[1]]
        return o
    d = out[s]
    bs = [[enc(r), l, y, res, noise(r) if res else 0] for r, l, y, res in d['b']]
    inside = [b for b, (r, *_ ) in zip(bs, d['b']) if b[3] and pin[i].contains(Point(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)))]
    rin = [r for (r, l, y, res) in d['b'] if res and pin[i].contains(Point(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)))]
    if inside:
        fl = [b[1] for b in inside if b[1]]
        share[s] = {'n': len(inside), 'n3': sum(1 for b in inside if b[4] == 3), 'n2': sum(1 for b in inside if b[4] == 2),
                    'nf': len(fl), 'f18': sum(1 for x in fl if x >= 18), 'f10': sum(1 for x in fl if 10 <= x < 18),
                    'park': sum(1 for r in rin if park_near(r))}
    js = {'o': [round(x0, 5), round(y0, 5)], 'b': bs, 'g': [enc(r) for r in d['g']],
          'i': [[enc(r), k] for r, k in d['i']], 'date': datetime.date.today().isoformat()}
    p = f'{REPO}/assets/dmap/{s}.json'
    json.dump(js, open(p, 'w'), separators=(',', ':')); tot += os.path.getsize(p)
json.dump({'date': datetime.date.today().isoformat(), 'note': 'жилые дома внутри района (OSM): n — всего; n3 — стена дома до 100 м от оси магистрали (МКАД, ТТК, хорды, вылетные шоссе), до 50 м от оси крупной улицы или до 100 м от ж/д станции; n2 — до 250 / 100 / 200 м; nf — этажность известна, f18 — 18 этажей и выше, f10 — 10–17; park — до парка, сквера или леса от 2 га не больше 300 м', 'd': share},
          open(f'{REPO}/tools/data/houses.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('районов', len(names), 'всего МБ', round(tot / 1e6, 1))
