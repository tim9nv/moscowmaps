#!/usr/bin/env python3
"""Улицы и адреса OSM -> assets/streets.json и assets/street-addresses.json.

python3 tools/build_street_index.py /tmp/moscow.osm.pbf
Зависимости: osmium, shapely >= 2. Исходник:
https://download.openstreetmap.fr/extracts/russia/central_federal_district/moscow.osm.pbf
Границы — те же tools/data/districts.json, что на карте Атласа.
Сначала сопоставляет адресные точки/здания с районами. Если адресов нет,
использует участки линии улицы. Для поиска дома сохраняет только явные
addr:street и addr:housenumber с районом адресной точки или контура.
Для motorway/trunk учитываются также все участки дороги:
адресов на магистралях мало. Касание границы в одной точке не считается.
"""
import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re

import osmium
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent
SOURCE = 'https://download.openstreetmap.fr/extracts/russia/central_federal_district/moscow.osm.pbf'
ROAD_TYPES = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
              'residential', 'living_street', 'pedestrian', 'unclassified', 'road'}
STREET_TYPE = re.compile(r'\b(улица|проезд|переулок|проспект|шоссе|набережная|бульвар|площадь|аллея|тупик|линия)\b', re.I)


def key(name):
    words = re.sub(r'[^а-яa-z0-9]+', ' ', name.lower().replace('ё', 'е')).split()
    return ' '.join(sorted(words))


def build(source, output):
    districts = json.loads((ROOT / 'tools/data/districts_list.json').read_text(encoding='utf-8'))
    by_name = {n: i for i, (_, n, _) in enumerate(districts)}
    # Локальная метрическая проекция нужна только для отсечения касаний и
    # микроскопических фрагментов на упрощённых границах карты.
    import math
    kx, ky = 111320 * math.cos(math.radians(55.75)), 110540
    metric = lambda x, y, z=None: (x * kx, y * ky)
    features = json.loads((ROOT / 'tools/data/districts.json').read_text(encoding='utf-8'))['features']
    polygons, ids = [], []
    for f in features:
        if f['properties']['n'] not in by_name:
            continue
        polygons.append(transform(metric, shape(f['geometry']).buffer(0)))
        ids.append(by_name[f['properties']['n']])
    tree = STRtree(polygons)
    entries = {}
    skipped = 0

    def add(name, geometry, aliases=(), is_road=False, number=None):
        nonlocal skipped
        if not name or not re.search('[А-Яа-яЁё]', name) or '/' in name:
            return
        hits = set()
        for i in tree.query(geometry, predicate='intersects'):
            if is_road and geometry.intersection(polygons[i]).length < 20:
                continue
            hits.add(ids[i])
        if not hits:
            return
        k = key(name)
        if not k:
            return
        e = entries.setdefault(k, {'names': defaultdict(int), 'districts': set(), 'aliases': set(), 'roads': defaultdict(float), 'addresses': defaultdict(int)})
        e['names'][name] += 1
        e['districts'].update(hits)
        for i in tree.query(geometry, predicate='intersects'):
            if ids[i] in hits:
                if is_road: e['roads'][ids[i]] += geometry.intersection(polygons[i]).length
                else: e['addresses'][ids[i]] += 1
        e['aliases'].update(a.strip() for a in aliases if a.strip())
        if number:
            numbers = e.setdefault('houses', defaultdict(set))
            for value in number.split(';'):
                value = value.strip().casefold().replace('ё', 'е')
                value = re.sub(r'[\s,.–—-]+', '', value)
                value = re.sub(r'корпус|корп', 'к', value)
                value = re.sub(r'строение|стр', 'с', value)
                value = re.sub(r'владение|влд', 'вл', value)
                if re.fullmatch(r'\d+[а-я]?(?:/\d+[а-я]?)?(?:(?:вл|к|с)\d+[а-я]?)*', value):
                    numbers[value].update(hits)

    class Handler(osmium.SimpleHandler):
        def node(self, n):
            street = n.tags.get('addr:street')
            if street and n.location.valid():
                add(street, Point(n.location.lon * kx, n.location.lat * ky), number=n.tags.get('addr:housenumber'))

        def way(self, w):
            nonlocal skipped
            t = w.tags
            name, road, street = t.get('name'), t.get('highway'), t.get('addr:street')
            named_road = name and (road in ROAD_TYPES or (road == 'service' and STREET_TYPE.search(name)))
            if not named_road and not street:
                return
            try:
                points = [(n.lon * kx, n.lat * ky) for n in w.nodes]
            except osmium.InvalidLocationError:
                skipped += 1
                return
            if len(points) < 2:
                return
            if named_road:
                aliases = [a for tag in ('alt_name', 'official_name', 'short_name')
                           for a in t.get(tag, '').split(';')]
                add(name, LineString(points), aliases, is_road=True)
                if road in {'motorway', 'trunk'} and key(name) in entries:
                    entries[key(name)]['major'] = True
            if street:
                # Адреса домов дополняют осевые линии пограничных улиц.
                g = Polygon(points).representative_point() if len(points) >= 4 and points[0] == points[-1] else LineString(points).interpolate(.5, normalized=True)
                add(street, g, number=t.get('addr:housenumber'))

    reader = osmium.io.Reader(str(source))
    snapshot = reader.header().get('osmosis_replication_timestamp') or reader.header().get('timestamp')
    reader.close()
    Handler().apply_file(str(source), locations=True)
    # В OSM кольцевая разбита на именованные километры. Общий запрос
    # «МКАД» должен учитывать их все; сами километры остаются для уточнения.
    if key('МКАД') in entries:
        ring = entries[key('МКАД')]
        for e in entries.values():
            if any(re.match(r'^МКАД(?:,|\s).*?(?:километр|\bкм\b)', n, re.I) for n in e['names']):
                ring['districts'].update(e['districts'])
        ring['major'] = True
    rows, address_rows = [], []
    for e in entries.values():
        name = sorted(e['names'], key=lambda n: (-e['names'][n], n))[0]
        aliases = sorted((set(e['names']) | e['aliases']) - {name})
        # Адреса домов предпочтительнее осевой линии: на границе она
        # может проходить по соседнему району без адресов этой улицы.
        members = e['districts'] if e.get('major') else set(e['addresses']) if e['addresses'] else set(e['roads'])
        rows.append([name, sorted(members), aliases])
        if e.get('houses'):
            houses = {number: sorted(ids) for number, ids in sorted(e['houses'].items())}
            address_rows.append([name, aliases, houses])
    rows.sort(key=lambda r: (r[0].casefold(), r[1]))
    result = {'source': SOURCE, 'license': 'https://www.openstreetmap.org/copyright',
              'date': snapshot[:10] if snapshot else date.today().isoformat(),
              'built': date.today().isoformat(), 'method': 'address-points-first; road-intersections-if-no-addresses-or-major-highway', 'districts': districts, 'streets': rows}
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    address_rows.sort(key=lambda row: row[0].casefold())
    address_output = output.with_name('street-addresses.json')
    address_data = {k: result[k] for k in ('source', 'license', 'date', 'districts')}
    address_data['streets'] = address_rows
    address_output.write_text(json.dumps(address_data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Номеров домов: {sum(len(row[2]) for row in address_rows)}, улиц с номерами: {len(address_rows)}, байт: {address_output.stat().st_size}')
    print(f'Улиц: {len(rows)}, районов: {len(set(i for r in rows for i in r[1]))}, байт: {output.stat().st_size}, неполных линий: {skipped}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/streets.json')
    args = parser.parse_args()
    build(args.source, args.output)
