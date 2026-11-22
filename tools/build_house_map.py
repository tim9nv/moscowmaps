"""Build the citywide house map from the full Moscow OSM extract.

python tools/build_house_map.py moscow.osm.pbf
Use the same extract as reconcile_house_years.py to reuse its verified years.
Source: https://download.openstreetmap.fr/extracts/russia/central_federal_district/moscow.osm.pbf
Requires osmium and shapely >= 2.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re

import osmium
from shapely import prepare, to_geojson
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from house_years import RESIDENTIAL, load_verified, resolve_year
from reconcile_house_years import address_key

ROOT = Path(__file__).resolve().parents[1]
MOSCOW_RELATION = 102269
NEW_MOSCOW_RELATIONS = {2263058, 2263059}
SCALE = 100000
ZOOM = 15
NUMBER = re.compile(r'\d+[а-я]?(?:/\d+[а-я]?)?(?:(?:вл|к|с)\d+[а-я]?)*')
STREET_TYPES = re.compile(r'\b(?:улица|ул|проспект|просп|пркт|переулок|пер|проезд|прд|шоссе|ш|набережная|наб|бульвар|бул|бр|площадь|пл|аллея|тупик)\b')


def bucket(name):
    # Same normalization and hash as the client. Sorted words allow common
    # changes in word order without putting the entire address index on the wire.
    name = name.lower().replace('ё', 'е')
    name = re.sub(r'пр\s*[-–—]\s*(?:кт|т)', 'проспект', name)
    name = re.sub(r'пр\s*[-–—]\s*д', 'проезд', name)
    name = re.sub(r'б\s*[-–—]\s*р', 'бульвар', name)
    name = re.sub(r'(\d+)\s*[-–—]?\s*(?:я|й|ая|ый)(?=\s|$)', r'\1', name)
    words = STREET_TYPES.sub(' ', re.sub(r'[^а-яa-z0-9]+', ' ', name)).split()
    value = 0
    for char in ' '.join(sorted(words)):
        value = (value * 31 + ord(char)) % 128
    return value


def tile(lon, lat):
    n = 2 ** ZOOM
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def address(tags, zelenograd):
    street = tags.get('addr:street') or tags.get('addr:place')
    number = tags.get('addr:housenumber', '')
    if not street and re.fullmatch(r'к\s*\d+[а-я]?', number, re.I):
        street = tags.get('addr:city') or ('Зеленоград' if zelenograd else '')
        if street == 'Зеленоград':
            number = re.sub(r'^к\s*', '', number, flags=re.I)
        else:
            return ()
    if not street:
        return ()
    results = []
    for item in number.split(';'):
        key = address_key(street, item)
        if key and NUMBER.fullmatch(key[2]):
            results.append((street, key[2]))
    return tuple(results)


def encode(polygon):
    rings = []
    for ring in [polygon.exterior, *polygon.interiors]:
        previous = (0, 0)
        encoded = []
        for lon, lat in list(ring.coords)[:-1]:
            point = (round(lon * SCALE), round(lat * SCALE))
            if point != previous:
                encoded.extend((point[0] - previous[0], point[1] - previous[1]))
            previous = point
        if len(encoded) >= 6:
            rings.append(encoded)
    return rings


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def build(source, output):
    verified = load_verified()['houses']
    regions = json.loads((ROOT / 'tools/data/districts.json').read_text(encoding='utf-8'))['features']
    district_rows = json.loads((ROOT / 'tools/data/districts_list.json').read_text(encoding='utf-8'))
    by_name = {row[1]: i for i, row in enumerate(district_rows)}
    new_moscow_id = len(district_rows)
    district_rows.append(['', 'Новая Москва', ''])
    moscow_id = len(district_rows)
    district_rows.append(['', 'Москва', ''])
    district_shapes = [shape(f['geometry']).buffer(0) for f in regions]
    district_tree = STRtree(district_shapes)
    district_ids = [by_name[f['properties']['n']] for f in regions]
    zelenograd = [district_shapes[i] for i, index in enumerate(district_ids) if district_rows[index][2] == 'ЗелАО']
    zelenograd_tree = STRtree(zelenograd)

    def in_zelenograd(lon, lat):
        return 37.05 < lon < 37.30 and 55.90 < lat < 56.06 and bool(len(
            zelenograd_tree.query(Point(lon, lat), predicate='covered_by')))

    def district(point):
        matches = district_tree.query(point, predicate='within')
        if len(matches):
            return district_ids[matches[0]]
        return new_moscow_id if any(area.covers(point) for area in new_moscow.values()) else moscow_id

    buildings, points = [], []
    city = None
    new_moscow = {}
    factory = osmium.geom.GeoJSONFactory()

    class Extract(osmium.SimpleHandler):
        def node(self, node):
            if not node.tags.get('addr:housenumber') or not node.location.valid():
                return
            lon, lat = node.location.lon, node.location.lat
            names = address(node.tags, in_zelenograd(lon, lat))
            if names:
                points.append((names, Point(lon, lat)))

        def area(self, area):
            nonlocal city
            tags = area.tags
            building = tags.get('building')
            relation = 0 if area.from_way() else area.orig_id()
            border = relation == MOSCOW_RELATION or relation in NEW_MOSCOW_RELATIONS
            if not border and (not building or building in ('no', 'construction', 'demolished', 'proposed', 'ruins')):
                return
            try:
                geometry = shape(json.loads(factory.create_multipolygon(area)))
            except (RuntimeError, ValueError):
                return
            if border:
                if relation == MOSCOW_RELATION:
                    city = geometry.buffer(0)
                else:
                    new_moscow[relation] = geometry.buffer(0)
                return
            if not geometry.is_valid or geometry.is_empty:
                return
            outer = [(node.lon, node.lat) for node in next(iter(area.outer_rings()))]
            year, source_id = resolve_year(verified, area, outer)
            level = re.match(r'\d+', tags.get('building:levels', ''))
            names = address(tags, in_zelenograd(*outer[0])) if tags.get('addr:housenumber') else ()
            buildings.append((str(area.id), geometry, names, year, min(int(level[0]), 120) if level else 0,
                              source_id, building in RESIDENTIAL))

    with osmium.io.Reader(str(source)) as reader:
        date = reader.header().get('osmosis_replication_timestamp') or reader.header().get('timestamp')
    Extract().apply_file(str(source), locations=True)
    if city is None:
        raise ValueError(f'Moscow boundary relation {MOSCOW_RELATION} is missing in the extract')
    if new_moscow.keys() != NEW_MOSCOW_RELATIONS:
        raise ValueError('New Moscow district boundaries are missing in the extract')
    prepare(city)
    for area in new_moscow.values():
        prepare(area)
    points = [(names, pt) for names, pt in points if city.covers(pt)]
    positions = [building[1].representative_point() for building in buildings]
    in_city = [i for i in STRtree(positions).query(city, predicate='covers')]
    buildings = [buildings[i] for i in in_city]
    positions = [positions[i] for i in in_city]
    print(f'Moscow: {len(buildings)} footprints, {len(points)} address points', flush=True)

    tree = STRtree([building[1] for building in buildings])
    names_by_building = [set(building[2]) for building in buildings]
    standalone = []
    for names, point in points:
        hits = tree.query(point, predicate='covered_by')
        if len(hits) == 1:
            outline = names_by_building[hits[0]]
            if not outline or {address_key(*name) for name in names} <= {address_key(*name) for name in outline}:
                outline.update(names)
                continue
        standalone.append((names, point))

    aliases = defaultdict(set)
    street_data = json.loads((ROOT / 'assets/streets.json').read_text(encoding='utf-8'))
    for name, _, other in street_data['streets']:
        for label in [name, *other]:
            aliases[label.casefold()].update([name, *other])
    tiles = defaultdict(list)
    search = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    def index(names, pt, feature_id='', cell='', district_id=None):
        row = (round(pt.y, 6), round(pt.x, 6), district(pt) if district_id is None else district_id, cell, feature_id)
        for name, number in names:
            labels = {name, *aliases[name.casefold()]}
            for label in sorted(labels):
                search[bucket(label)][(name, label)][number].add(row)

    mapped = known = 0
    for (feature_id, geometry, _, year, level, source_id, residential), pt, names in zip(buildings, positions, names_by_building):
        if not (residential or names or year):
            continue
        polygons = [part for part in map(encode, geometry.geoms) if part]
        if not polygons:
            continue
        district_id = district(pt)
        x, y = tile(pt.x, pt.y)
        home_cell = f'{x}-{y}'
        feature = [feature_id, polygons, year, level, source_id, sorted(names), district_id]
        left, bottom, right, top = geometry.bounds
        x0, y0 = tile(left, top)
        x1, y1 = tile(right, bottom)
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                tiles[f'{tx}-{ty}'].append(feature)
        if names:
            index(names, pt, feature_id, home_cell, district_id)
            mapped += 1
            known += bool(year)

    for names, point in standalone:
        index(names, point)

    output.mkdir(parents=True, exist_ok=True)
    for cell, features in sorted(tiles.items()):
        write(output / f't{cell}.json', sorted(features, key=lambda row: int(row[0])))
    for number, streets in sorted(search.items()):
        rows = [[*labels, {n: sorted(hits) for n, hits in sorted(numbers.items())}]
                for labels, numbers in sorted(streets.items())]
        write(output / f'a{number}.json', rows)
    boundary = json.loads(to_geojson(city.simplify(0.0015, preserve_topology=True)))
    write(output / 'index.json', {'date': date[:10], 'zoom': ZOOM, 'districts': district_rows,
                                  'tiles': sorted(tiles), 'boundary': boundary})
    expected = {'index.json', *(f't{cell}.json' for cell in tiles), *(f'a{n}.json' for n in search)}
    for path in output.glob('*.json'):
        if path.name not in expected and re.fullmatch(r'(?:a\d+|t\d+-\d+)\.json', path.name):
            path.unlink()
    print(f'{len(tiles)} tiles. {mapped} addressed outlines; {known} with a year.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/house-map')
    args = parser.parse_args()
    build(args.source, args.output)
