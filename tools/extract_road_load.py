"""Нагрузка на дороги: сколько квартир района приходится на один полосо-километр крупных дорог вокруг -> tools/data/road_load.json
Запуск: python3 tools/extract_road_load.py /tmp/moscow.osm.pbf
Источник — OpenStreetMap. Это не замер пробок, а соотношение жилья и дорог:
- квартиры: тег building:flats у жилых домов внутри района; где его нет — оценка «площадь дома × этажи / K»,
  K (м² площади этажа на квартиру) подбирается по домам, где квартиры указаны;
- дороги: полосо-километры магистралей, trunk, primary, secondary (и съездов) внутри района и в полосе 1 км вокруг него
  (по ним жители и выезжают); без тега lanes — 2 полосы на двустороннюю, 1 на одностороннюю;
  магистрали (motorway) весят 2, trunk 1,5, primary 1, secondary 0,75 — скоростные дороги без светофоров пропускают больше.
  (Первая попытка — считать только полосы, пересекающие границу района, — не сработала: дороги в OSM порезаны на куски
  у перекрёстков, а границы районов часто идут по осям улиц.)
"""
import osmium, json, sys, os, re, math, datetime, statistics
from shapely.geometry import shape, Point, Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KX, KY = 111320 * math.cos(math.radians(55.75)), 110540
feats = json.load(open(f'{REPO}/tools/data/districts.json', encoding='utf-8'))['features']
slugs = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
D = []
for f in feats:
    g = shape(f['geometry']).buffer(0)
    gm = Polygon() if g.is_empty else g
    from shapely.affinity import scale
    gmm = scale(gm, KX, KY, origin=(0, 0))
    D.append(dict(slug=slugs[f['properties']['n']], g=g, pin=prep(g), zone=gmm.buffer(1000)))
tree = STRtree([d['g'] for d in D]); ztree = STRtree([d['zone'] for d in D])
W = {'motorway': 2, 'motorway_link': 2, 'trunk': 1.5, 'trunk_link': 1.5, 'primary': 1, 'primary_link': 1, 'secondary': .75, 'secondary_link': .75}
RES = {'apartments', 'residential', 'dormitory'}
houses = []   # (lon, lat, flats|None, area*levels|None)
lanes_out = {d['slug']: 0.0 for d in D}; exits = {d['slug']: [] for d in D}
def ln(t, k):
    m = re.match(r'\d+', t.get(k) or '')
    return int(m.group(0)) if m else None
class H(osmium.SimpleHandler):
    def area(self, a):
        t = a.tags
        if t.get('building') not in RES: return
        try: ring = [(n.lon, n.lat) for n in next(iter(a.outer_rings()))]
        except Exception: return
        if len(ring) < 4: return
        ar = abs(sum(ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1] for k in range(len(ring) - 1))) / 2 * KX * KY
        lv = ln(t, 'building:levels'); fl = ln(t, 'building:flats')
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        houses.append((cx, cy, fl if fl and fl < 5000 else None, ar * lv if lv else None))
    def way(self, w):
        t = w.tags; hw = t.get('highway')
        if hw not in W or t.get('access') in ('no', 'private'): return
        try: pts = [(n.lon, n.lat) for n in w.nodes]
        except Exception: return
        if len(pts) < 2: return
        ow = t.get('oneway') in ('yes', 'true', '1') or hw in ('motorway', 'motorway_link') or t.get('junction') == 'roundabout'
        rev = t.get('oneway') == '-1'
        L = ln(t, 'lanes'); fw, bw = ln(t, 'lanes:forward'), ln(t, 'lanes:backward')
        if ow: fwd, bwd = (L or 1), 0
        else:
            fwd = fw or (L // 2 if L and L >= 2 else 1); bwd = bw or (L - fwd if L and L > fwd else 1)
        if rev: fwd, bwd = bwd, fwd
        from shapely.geometry import LineString
        tot = (L or 1) if ow else (L or 2)
        line = LineString([(x * KX, y * KY) for x, y in pts])
        for i in ztree.query(line):
            d = D[i]; km = line.intersection(d['zone']).length / 1000
            if km > 0:
                lanes_out[d['slug']] += km * tot * W[hw]
                if hw in ('motorway', 'trunk', 'primary') and t.get('name') and km > .3: exits[d['slug']].append((t['name'], km, hw))
H().apply_file(sys.argv[1], locations=True)
# коэффициент: площадь этажей на квартиру, по домам с известными квартирами
k = statistics.median(h[3] / h[2] for h in houses if h[2] and h[3] and h[2] >= 8)
fl = {d['slug']: [0, 0, 0] for d in D}   # квартир всего, из них указано в OSM, оценено
for lon, lat, f, s in houses:
    p = Point(lon, lat)
    for i in tree.query(p):
        if D[i]['pin'].contains(p):
            v = f if f else (round(s / k) if s else None)
            if v is None: break
            fl[D[i]['slug']][0] += v; fl[D[i]['slug']][1 if f else 2] += v
            break
out = {}
for d in D:
    s = d['slug']; L = lanes_out[s]; F = fl[s][0]
    agg = {}
    for n_, km_, hw_ in exits[s]: agg[n_] = agg.get(n_, 0) + km_
    names = [n_ for n_, _ in sorted(agg.items(), key=lambda x: -x[1])]
    out[s] = {'flats': F, 'flats_osm': fl[s][1], 'flats_est': fl[s][2], 'lane_km': round(L, 1), 'per_lane_km': round(F / L) if L else None, 'roads': names[:8]}
json.dump({'date': datetime.date.today().isoformat(), 'k_m2_per_flat': round(k, 1),
           'note': 'квартир района на один взвешенный полосо-километр крупных дорог в районе и в 1 км вокруг (OSM); не замер пробок', 'd': out},
          open(f'{REPO}/tools/data/road_load.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('K =', round(k, 1), 'м² на квартиру; районов', len(out))
