"""Возраст жилых домов по районам из OpenStreetMap и Дом.МинЖКХ -> tools/data/house_age.json
Запуск: python3 tools/extract_house_age.py /tmp/moscow.osm.pbf
Берём только жилые дома (building=apartments|residential|house|detached|semidetached_house|terrace|dormitory)
с годом постройки в start_date / building:start_date / construction_date. Без года — не учитываем, долю таких пишем в файл.
"""
import osmium, json, sys, os, datetime
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from house_years import RESIDENTIAL, load_verified, resolve_year
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
verified = load_verified()
BINS = [
    (0, 1956, 'до 1957'),
    (1957, 1968, '1957–1968'),
    (1969, 1980, '1969–1980'),
    (1981, 1991, '1981–1991'),
    (1992, 2010, '1992–2010'),
    (2011, 9999, 'с 2011'),
]
pts = []
class H(osmium.SimpleHandler):
    def area(self, a):
        if a.tags.get('building') not in RESIDENTIAL and str(a.id) not in verified['houses']: return
        try:
            ring = [(n.lon, n.lat) for n in next(iter(a.outer_rings()))]
        except Exception: return
        if ring:
            year, source_id = resolve_year(verified['houses'], a, ring)
            if a.tags.get('building') not in RESIDENTIAL and source_id >= 0:
                return
            pts.append((sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring), year, source_id))
source_path = sys.argv[1]
with osmium.io.Reader(source_path) as reader:
    source_timestamp = reader.header().get('osmosis_replication_timestamp')
H().apply_file(source_path, locations=True)
feats = json.load(open(f'{REPO}/tools/data/districts.json', encoding='utf-8'))['features']
slugs = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
geoms = [shape(f['geometry']).buffer(0) for f in feats]; tree = STRtree(geoms)
res = {slugs[f['properties']['n']]: {'all': 0, 'dated': 0, 'verified': 0, 'bins': [0] * len(BINS)} for f in feats}
for lon, lat, y, source_id in pts:
    p = Point(lon, lat)
    for i in tree.query(p):
        if geoms[i].contains(p):
            r = res[slugs[feats[i]['properties']['n']]]; r['all'] += 1
            if y:
                r['dated'] += 1
                r['verified'] += bool(source_id)
                if source_id < 0:
                    r['reviewed'] = r.get('reviewed', 0) + 1
                for k, (a, b, _) in enumerate(BINS):
                    if a <= y <= b: r['bins'][k] += 1; break
            break
source_date = source_timestamp[:10] if source_timestamp else datetime.date.today().isoformat()
out = {'date': source_date, 'source': 'OpenStreetMap', 'bins': [b[2] for b in BINS], 'districts': res}
if verified['date']:
    out['verification'] = {'date': verified['date'], 'source': verified['source']}
json.dump(out, open(f'{REPO}/tools/data/house_age.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
tot = sum(r['all'] for r in res.values()); dt = sum(r['dated'] for r in res.values())
print(f'жилых домов {tot}, с годом {dt} ({dt / max(tot, 1):.0%})')
for s in ('otradnoe', 'arbat', 'kurkino', 'vostochnyy', 'kotlovka'): print(s, res[s])
