"""Возраст жилых домов по районам из OpenStreetMap -> tools/data/house_age.json
Запуск: python3 tools/extract_house_age.py /tmp/moscow.osm.pbf
Берём только жилые дома (building=apartments|residential|house|detached|semidetached_house|terrace|dormitory)
с годом постройки в start_date / building:start_date / construction_date. Без года — не учитываем, долю таких пишем в файл.
"""
import osmium, json, sys, os, re, datetime
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = {'apartments', 'residential', 'house', 'detached', 'semidetached_house', 'terrace', 'dormitory'}
BINS = [(0, 1945, 'до 1945'), (1946, 1960, '1946–1960'), (1961, 1980, '1961–1980'), (1981, 2000, '1981–2000'), (2001, 2014, '2001–2014'), (2015, 2100, 'с 2015')]
def year(t):
    for k in ('start_date', 'building:start_date', 'construction_date'):
        v = t.get(k)
        if v:
            m = re.search(r'(1[6-9]\d\d|20[0-3]\d)', v)
            if m: return int(m.group(1))
    return None
pts = []
class H(osmium.SimpleHandler):
    def area(self, a):
        if a.tags.get('building') not in RES: return
        try:
            ring = next(iter(a.outer_rings()))
            xs = [n.lon for n in ring]; ys = [n.lat for n in ring]
        except Exception: return
        if xs: pts.append((sum(xs) / len(xs), sum(ys) / len(ys), year(a.tags)))
H().apply_file(sys.argv[1], locations=True)
feats = json.load(open(f'{REPO}/tools/data/districts.json', encoding='utf-8'))['features']
slugs = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
geoms = [shape(f['geometry']).buffer(0) for f in feats]; tree = STRtree(geoms)
res = {slugs[f['properties']['n']]: {'all': 0, 'dated': 0, 'bins': [0] * len(BINS)} for f in feats}
for lon, lat, y in pts:
    p = Point(lon, lat)
    for i in tree.query(p):
        if geoms[i].contains(p):
            r = res[slugs[feats[i]['properties']['n']]]; r['all'] += 1
            if y:
                r['dated'] += 1
                for k, (a, b, _) in enumerate(BINS):
                    if a <= y <= b: r['bins'][k] += 1; break
            break
out = {'date': datetime.date.today().isoformat(), 'source': 'OpenStreetMap', 'bins': [b[2] for b in BINS], 'districts': res}
json.dump(out, open(f'{REPO}/tools/data/house_age.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
tot = sum(r['all'] for r in res.values()); dt = sum(r['dated'] for r in res.values())
print(f'жилых домов {tot}, с годом {dt} ({dt / max(tot, 1):.0%})')
for s in ('otradnoe', 'arbat', 'kurkino', 'vostochnyy', 'kotlovka'): print(s, res[s])
