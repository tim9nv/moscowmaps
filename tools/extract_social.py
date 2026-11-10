"""Школы, детские сады, поликлиники и больницы из OpenStreetMap -> assets/places/<slug>.json
Запуск: python3 tools/extract_social.py /tmp/moscow.osm.pbf
Формат файла района: {"date": "...", "schools": [[lon, lat, название, адрес], ...], "kindergartens": [...], "clinics": [...]}
Для Отрадного берутся выверенные вручную списки ChatGPT (assets/otradnoe-*.json), остальные районы — как в OSM.
"""
import osmium, json, sys, os, re, datetime
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = {'school': 'schools', 'kindergarten': 'kindergartens', 'clinic': 'clinics', 'hospital': 'clinics'}
DEF = {'school': 'Школа', 'kindergarten': 'Детский сад', 'clinic': 'Поликлиника', 'hospital': 'Больница'}
out = []
def rec(t, lon, lat):
    am = t.get('amenity')
    if am not in KIND: return
    if t.get('disused') == 'yes' or t.get('abandoned') == 'yes': return
    name = (t.get('short_name') or t.get('name') or t.get('official_name') or DEF[am]).strip()
    if len(name) > 70: name = (t.get('name') or name)[:67].rstrip() + '…'
    st, hn = t.get('addr:street'), t.get('addr:housenumber')
    addr = f'{st}, {hn}' if st and hn else (st or '')
    out.append((am, round(lon, 6), round(lat, 6), name, addr))
class H(osmium.SimpleHandler):
    def node(self, n):
        if n.location.valid(): rec(n.tags, n.location.lon, n.location.lat)
    def area(self, a):   # замкнутые линии и мультиполигоны (здания и территории)
        if a.tags.get('amenity') not in KIND: return
        xs, ys = [], []
        try:
            for ring in a.outer_rings():
                for nd in ring: xs.append(nd.lon); ys.append(nd.lat)
        except Exception: return
        if xs: rec(a.tags, sum(xs) / len(xs), sum(ys) / len(ys))
H().apply_file(sys.argv[1], locations=True)
feats = json.load(open(f'{REPO}/tools/data/districts.json', encoding='utf-8'))['features']
slugs = {n: s for s, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
geoms = [shape(f['geometry']).buffer(0) for f in feats]
tree = STRtree(geoms)
res = {slugs[f['properties']['n']]: {'schools': [], 'kindergartens': [], 'clinics': []} for f in feats}
seen = set()
for am, lon, lat, name, addr in out:
    pt = Point(lon, lat)
    for i in tree.query(pt):
        if geoms[i].contains(pt):
            sl = slugs[feats[i]['properties']['n']]
            key = (sl, KIND[am], name, addr or (round(lon, 3), round(lat, 3)))   # одно здание, отмеченное и точкой, и контуром
            if key in seen: break
            seen.add(key); res[sl][KIND[am]].append([lon, lat, name, addr]); break
# Отрадное: списки, сверенные с городскими перечнями
for k in ('schools', 'kindergartens', 'clinics'):
    p = f'{REPO}/assets/otradnoe-{k}.json'
    if os.path.exists(p):
        res['otradnoe'][k] = [[x['coordinates'][0], x['coordinates'][1], x['name'], x['address']] for x in json.load(open(p, encoding='utf-8'))]
date = datetime.date.today().strftime('%d.%m.%Y')
os.makedirs(f'{REPO}/assets/places', exist_ok=True)
tot = {'schools': 0, 'kindergartens': 0, 'clinics': 0}
for sl, d in res.items():
    for k in tot: d[k].sort(key=lambda x: (x[2], x[3])); tot[k] += len(d[k])
    d['date'] = date
    json.dump(d, open(f'{REPO}/assets/places/{sl}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(res), 'районов', tot)
