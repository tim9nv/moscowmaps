"""Дома, зелень и промзоны для подробной карты района -> assets/dmap/<slug>.json
Запуск: python3 tools/extract_district_map.py /tmp/moscow.osm.pbf
Источник — OpenStreetMap. Для каждого района берём то, что внутри него и в полосе ~150 м вокруг (окрестности на карте притушены).
Дома мельче 40 м² (будки, гаражи) не берём.
Формат: {"o":[lon0,lat0], "b":[[точки, этажей|0, год|0, жилой 1/0], ...], "g":[точки,...], "i":[[точки, вид], ...], "date":...}
точки — плоский список целых: первая точка (lon-lon0)*1e5, (lat-lat0)*1e5, дальше — приращения.
"""
import osmium, json, sys, os, re, datetime
from shapely.geometry import shape, Polygon, box
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
out = {s: {'b': [], 'g': [], 'i': []} for s in names}
GREEN = lambda t: t.get('leisure') in ('park', 'garden', 'nature_reserve') or t.get('landuse') == 'forest' or t.get('natural') == 'wood'
IND = {'industrial': 'i', 'construction': 'c', 'garages': 'g', 'railway': 'r'}
class H(osmium.SimpleHandler):
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
H().apply_file(sys.argv[1], locations=True)
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
    js = {'o': [round(x0, 5), round(y0, 5)], 'b': [[enc(r), l, y, res] for r, l, y, res in d['b']], 'g': [enc(r) for r in d['g']],
          'i': [[enc(r), k] for r, k in d['i']], 'date': datetime.date.today().isoformat()}
    p = f'{REPO}/assets/dmap/{s}.json'
    json.dump(js, open(p, 'w'), separators=(',', ':')); tot += os.path.getsize(p)
print('районов', len(names), 'всего МБ', round(tot / 1e6, 1))
