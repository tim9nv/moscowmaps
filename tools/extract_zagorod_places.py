"""Что есть рядом с местами раздела «За город» — из OpenStreetMap -> zagorod/<slug>/places.json
Запуск: python3 tools/extract_zagorod_places.py /tmp/moscow_oblast.osm.pbf /tmp/kaluga_oblast.osm.pbf /tmp/tula_oblast.osm.pbf /tmp/yaroslavl_oblast.osm.pbf
Берём только объекты с названием в радиусе от центра места: достопримечательности, музеи, храмы, смотровые, кафе, гостиницы; парковки и туалеты — и без названия.
"""
import osmium, json, sys, os, math, datetime, re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AREAS = {  # slug: [(lat, lon, радиус м), ...]
 'sergiev-posad': [(56.3105, 38.1310, 1500)], 'kolomna': [(55.1045, 38.7620, 1500)], 'arhangelskoe': [(55.7860, 37.2870, 1200)],
 'abramtsevo': [(56.2365, 37.9665, 1000)], 'zvenigorod': [(55.7282, 36.8163, 900), (55.7310, 36.8500, 1500)], 'novyy-ierusalim': [(55.9230, 36.8450, 1300)],
 'melihovo': [(55.1148, 37.6468, 800)], 'dmitrov': [(56.3440, 37.5210, 1300)], 'muranovo': [(56.1807, 37.9021, 700)],
 'ostafevo': [(55.4943, 37.5036, 800), (55.4410, 37.4950, 800)], 'tarusa-polenovo': [(54.7290, 37.1800, 1500), (54.7482, 37.2357, 1000)],
 'nikola-lenivets': [(54.7500, 35.6100, 2500)], 'etnomir': [(55.2453, 36.4276, 900)], 'kochevnik': [(56.2413, 38.0532, 500)], 'vorobi': [(55.1585, 36.7778, 700)],
 'zaraysk': [(54.7590, 38.8740, 1300)], 'zubry': [(54.9152, 37.5688, 1500)], 'serednikovo': [(55.9286, 37.2414, 900)],
 'serpuhov': [(54.9030, 37.4220, 900), (54.9166, 37.4027, 900), (54.8989, 37.3987, 500)], 'borovsk': [(55.2071, 36.4900, 1500), (55.2147, 36.5330, 600)],
 'mozhaysk-borodino': [(55.5120, 36.0090, 1500), (55.5150, 35.8280, 2500)], 'egorevsk': [(55.3835, 39.0370, 1300)], 'klin': [(56.3350, 36.7300, 1400), (56.3284, 36.7454, 500)],
 'monino': [(55.8328, 38.1860, 900)], 'senezh': [(56.1930, 36.9800, 1500)], 'gorki-leninskie': [(55.5060, 37.7690, 1200)],
 'pereslavl-zalesskiy': [(56.7364, 38.8529, 1500), (56.7225, 38.7900, 1800), (56.7612, 38.8589, 600)], 'rostov-velikiy': [(57.1850, 39.4150, 1500), (57.1743, 39.3924, 600)], 'uglich': [(57.5280, 38.3180, 1500)],
}
# новые места из tools/data/zagorod_new.json: круги по 1 км вокруг их точек (кроме станций)
import json as _j, os as _o
_nf = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), 'data', 'zagorod_new.json')
if _o.path.exists(_nf):
    for _q in _j.load(open(_nf, encoding='utf-8')):
        AREAS.setdefault(_q['slug'], [(t[1], t[2], 1000) for t in _q['points'] if t[5] != 'Ст'][:3])
CAP = {'food': 24, 'hotel': 12, 'parking': 8, 'wc': 8}
def dist(a, b, c, d):
    k = math.cos(math.radians(a)); return math.hypot((a - c) * 111320, (b - d) * 111320 * k)
def cat(t):
    tour, hist, am = t.get('tourism'), t.get('historic'), t.get('amenity')
    if tour == 'museum' or am in ('theatre', 'arts_centre'): return 'museum'
    if tour == 'viewpoint': return 'view'
    if tour == 'artwork': return 'art'
    if am == 'place_of_worship' or t.get('building') in ('church', 'cathedral', 'chapel') or hist in ('monastery', 'church'): return 'church'
    if hist in ('monument', 'memorial', 'castle', 'manor', 'ruins', 'city_gate', 'tower', 'fort', 'archaeological_site', 'building') or tour == 'attraction': return 'sight'
    if am in ('cafe', 'restaurant', 'fast_food', 'bar', 'pub'): return 'food'
    if tour in ('hotel', 'guest_house', 'hostel', 'apartment', 'chalet'): return 'hotel'
    if am == 'parking' and t.get('access') not in ('private', 'no', 'customers'): return 'parking'
    if am == 'toilets': return 'wc'
    return None
BAD = re.compile(r'мемориальная доска|закладной камень|^памятный знак$', re.I)
res = {s: [] for s in AREAS}
def add(tags, lat, lon):
    c = cat(tags)
    if not c: return
    name = (tags.get('name') or '').strip()
    if not name and c not in ('parking', 'wc'): return
    if tags.get('memorial') in ('plaque', 'stolperstein') or BAD.search(name): return
    for s, ar in AREAS.items():
        for la, lo, r in ar:
            d = dist(lat, lon, la, lo)
            if d <= r: res[s].append((d, [round(lat, 5), round(lon, 5), c, name])); return
class H(osmium.SimpleHandler):
    def node(self, n):
        if n.tags: add({t.k: t.v for t in n.tags}, n.location.lat, n.location.lon)
    def area(self, a):
        t = {x.k: x.v for x in a.tags}
        if not cat(t): return
        try:
            ring = next(iter(a.outer_rings())); xs = [n.lon for n in ring]; ys = [n.lat for n in ring]
        except Exception: return
        if xs: add(t, sum(ys) / len(ys), sum(xs) / len(xs))
for f in sys.argv[1:]:
    H().apply_file(f, locations=True)
for s, items in res.items():
    items.sort(key=lambda x: x[0]); seen = set(); out = []; cnt = {}
    for d, it in items:
        k = (it[2], it[3].lower()) if it[3] else (it[2], it[0], it[1])
        if k in seen: continue
        if it[3] and any(o[3].lower() == it[3].lower() and dist(o[0], o[1], it[0], it[1]) < 60 for o in out): continue   # одно и то же место под разными категориями
        seen.add(k); cnt[it[2]] = cnt.get(it[2], 0) + 1
        if cnt[it[2]] > CAP.get(it[2], 60): continue
        out.append(it)
    os.makedirs(f'{REPO}/zagorod/{s}', exist_ok=True); json.dump({'date': datetime.date.today().isoformat(), 'places': out}, open(f'{REPO}/zagorod/{s}/places.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(s, len(out), {c: sum(1 for o in out if o[2] == c) for c in sorted({o[2] for o in out})})
