"""Что есть в парках: достопримечательности, музеи, кафе, детские площадки, туалеты из OpenStreetMap.
Запуск: python3 tools/extract_park_places.py /tmp/moscow.osm.pbf  ->  parks/catalog/places.json
Формат: {"date": "...", "parks": {"<id парка из parks.json>": [[lat, lon, категория, название], ...]}}
Границы парков — const PARKS в parks.html, id = порядковый номер (как в tools/build-park-catalog.py).
"""
import osmium, json, sys, os, re, datetime
from shapely.geometry import shape, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF = {'play': 'Детская площадка', 'wc': 'Туалет', 'view': 'Смотровая площадка', 'water': 'Питьевая вода'}
def cat(t):
    tour, hist, am, le = t.get('tourism'), t.get('historic'), t.get('amenity'), t.get('leisure')
    if tour in ('museum', 'gallery', 'zoo', 'theme_park') or am in ('theatre', 'planetarium'): return 'museum'
    if tour == 'viewpoint': return 'view'
    if tour in ('attraction', 'artwork') or hist in ('monument', 'memorial', 'manor', 'castle', 'church', 'monastery', 'ruins', 'archaeological_site', 'building', 'palace', 'fort', 'city_gate', 'wayside_shrine', 'tomb') or am == 'place_of_worship' or am == 'fountain': return 'sight'
    if am in ('cafe', 'restaurant', 'fast_food', 'ice_cream', 'bar', 'pub'): return 'food'
    if le == 'playground': return 'play'
    if am == 'toilets': return 'wc'
    if am == 'drinking_water': return 'water'
    return None
out = []
def rec(t, lon, lat):
    c = cat(t)
    if not c: return
    if t.get('access') in ('private', 'no') or t.get('disused') == 'yes': return
    name = (t.get('name') or '').strip()
    if not name:
        if c not in DEF: return          # безымянные памятники и кафе не показываем
        name = DEF[c]
    if len(name) > 70: name = name[:67].rstrip() + '…'
    out.append((round(lat, 6), round(lon, 6), c, name))
class H(osmium.SimpleHandler):
    def node(self, n):
        if n.location.valid(): rec(n.tags, n.location.lon, n.location.lat)
    def area(self, a):
        if not cat(a.tags): return
        xs, ys = [], []
        try:
            for ring in a.outer_rings():
                for nd in ring: xs.append(nd.lon); ys.append(nd.lat)
        except Exception: return
        if xs: rec(a.tags, sum(xs) / len(xs), sum(ys) / len(ys))
H().apply_file(sys.argv[1], locations=True)
parks = json.loads(re.search(r'const PARKS = (.*?);\n', open(f'{REPO}/parks.html', encoding='utf-8').read()).group(1))
shapes = [unary_union([Polygon(r).buffer(0) for r in p['p'] if len(r) >= 3]).buffer(0.0003) for p in parks]   # запас ~25 м: входы и кафе у ограды
tree = STRtree(shapes)
res = {}
seen = set()
for lat, lon, c, name in out:
    pt = Point(lon, lat)
    for i in tree.query(pt):
        if shapes[i].contains(pt):
            key = (i, c, name, round(lat, 4), round(lon, 4))
            if key in seen: continue
            seen.add(key); res.setdefault(str(i + 1), []).append([lat, lon, c, name])
ORDER = {'sight': 0, 'museum': 1, 'view': 2, 'food': 3, 'play': 4, 'wc': 5, 'water': 6}
for v in res.values(): v.sort(key=lambda x: (ORDER[x[2]], x[3]))
json.dump({'date': datetime.date.today().strftime('%d.%m.%Y'), 'parks': res}, open(f'{REPO}/parks/catalog/places.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import collections
print(len(res), 'парков с объектами из', len(parks), collections.Counter(x[2] for v in res.values() for x in v))
