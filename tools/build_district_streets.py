"""Собирает уличную сеть для карт районов из выгрузки OpenStreetMap.

python tools/build_district_streets.py /path/to/moscow.osm.pbf
Зависимости: osmium, shapely >= 2. Слой не включает дворовые проезды.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import osmium
from shapely.geometry import LineString, shape
from shapely.ops import linemerge
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
RANK = {
    'motorway': 1, 'trunk': 1, 'motorway_link': 1, 'trunk_link': 1,
    'primary': 2, 'secondary': 2, 'primary_link': 2, 'secondary_link': 2,
    'tertiary': 3, 'unclassified': 3,
    'residential': 4, 'living_street': 4, 'pedestrian': 4,
}


def lines(geometry):
    if geometry.geom_type == 'LineString' and not geometry.is_empty:
        yield geometry
    elif hasattr(geometry, 'geoms'):
        for part in geometry.geoms:
            yield from lines(part)


def build(source, output):
    data = ROOT / 'tools/data'
    slugs = {name: slug for slug, name, _ in json.loads(
        (data / 'districts_list.json').read_text(encoding='utf-8'))}
    features = json.loads((data / 'districts.json').read_text(encoding='utf-8'))['features']
    districts = [(slugs[f['properties']['n']], shape(f['geometry']).buffer(0.0025))
                 for f in features if f['properties']['n'] in slugs]
    tree = STRtree([area for _, area in districts])
    groups = [defaultdict(list) for _ in districts]

    class Streets(osmium.SimpleHandler):
        def way(self, way):
            tags = way.tags
            rank = RANK.get(tags.get('highway'))
            if not rank or tags.get('area') == 'yes' or tags.get('access') == 'private':
                return
            name = (tags.get('name') or tags.get('ref') or '').strip()
            if not name and rank >= 3:
                return
            if tags.get('highway', '').endswith('_link'):
                name = ''
            if len(way.nodes) < 2 or not all(n.location.valid() for n in way.nodes):
                return
            line = LineString([(n.lon, n.lat) for n in way.nodes])
            for i in tree.query(line, predicate='intersects'):
                groups[i][rank, name].extend(lines(line.intersection(districts[i][1])))

    Streets().apply_file(str(source), locations=True, idx='flex_mem')
    output.mkdir(parents=True, exist_ok=True)
    for (slug, _), groups_by_street in zip(districts, groups):
        rows = []
        for (rank, name), parts in sorted(groups_by_street.items()):
            for line in lines(linemerge(parts)):
                points = [[round(lon, 5), round(lat, 5)]
                          for lon, lat in line.simplify(0.000022).coords]
                if len({tuple(point) for point in points}) >= 2:
                    rows.append([rank, name, points])
        (output / f'{slug}.json').write_text(
            json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Уличный слой: {len(districts)} районов')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/district-streets')
    args = parser.parse_args()
    build(args.source, args.output)
