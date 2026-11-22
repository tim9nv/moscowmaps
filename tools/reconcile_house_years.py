"""Сверяет контуры Атласа с таблицей «Все дома в Москве» Дом.МинЖКХ.

python tools/reconcile_house_years.py moscow.osm.pbf mingkh.tsv --date ГГГГ-ММ-ДД
Входная таблица TSV без заголовка: ID карточки, адрес, год постройки.
После сверки запустить extract_house_age.py с той же выгрузкой OSM и
district_layout.py --age-only. Уже опубликованные контуры меняются только в
части года и источника. У объектов, подтверждённых как жилые вручную,
уточняется тип. Слои и границы не пересобираются.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re

import osmium
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

from house_years import RESIDENTIAL, VERIFIED_PATH, outline_fingerprint, osm_year

ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = ROOT / 'tools/data/house_year_review.json'
STREET_TYPES = (
    ('улица', r'улица|ул'), ('переулок', r'переулок|пер'),
    ('проезд', r'проезд|прд|пр\s*-\s*д'), ('проспект', r'проспект|просп|пр\s*-\s*(?:кт|т)'),
    ('шоссе', r'шоссе|ш'), ('бульвар', r'бульвар|бул|б\s*-\s*р'),
    ('площадь', r'площадь|пл'), ('набережная', r'набережная|наб'),
    ('аллея', r'аллея'), ('тупик', r'тупик'), ('линия', r'линия'),
    ('микрорайон', r'микрорайон|мкр'), ('квартал', r'квартал|кв\s*-\s*л'),
)
NUMBER = re.compile(r'\d+[а-я]?(?:/\d+[а-я]?)?(?:(?:вл|к|с)\d*[а-я]?)*')
X, Y = 62649, 110540
REVIEW_GAP = 20
# Дом.МинЖКХ показывает переставленные годы для Алтуфьевского шоссе, 66/2 и 79.
# Сверка: https://www.urbaneconomics.ru/sites/default/files/1_altufevo.pdf
# и https://www.mos.ru/upload/documents/files/3072/74_KP2018-2020_razdelI.pdf
REFERENCE_CONFLICTS = {600082, 600083}


def cleaned(value):
    return value.casefold().replace('ё', 'е').replace('–', '-').replace('—', '-').strip()


def address_key(street, number):
    street = cleaned(street)
    if re.fullmatch(r'(?:г\.?\s+)?зеленоград(?:\s+г\.?)?', street):
        number = re.sub(r'^(?:корпус|корп|к)\.?\s*(?=\d)', '', cleaned(number))
        street = 'зеленоград'
    kind = 'улица'
    for label, pattern in STREET_TYPES:
        street, hits = re.subn(rf'^(?:{pattern})[.\s]+|[\s]+(?:{pattern})\.?$', '', street)
        if hits:
            kind = label
            break
    street = re.sub(r'(\d+)\s*-?\s*(?:ая|ый|ой|й|я)(?=\s|$)', r'\1', street)
    street = ' '.join(re.findall(r'[а-яa-z0-9]+', street))
    quarter = re.fullmatch(r'([1-5])(?: квартал)? капотн[яи]', street)
    if quarter and (kind == 'квартал' or 'квартал' in street):
        kind, street = 'квартал', f'{quarter[1]} капотня'
    number = re.sub(r'^\s*(?:д\.?|дом)\s+(?=\d)', '', cleaned(number))
    number = re.sub(r'[\s.,-]+', '', number)
    number = re.sub(r'корпус|корп', 'к', number)
    number = re.sub(r'строение|стр', 'с', number)
    number = re.sub(r'владение|влд', 'вл', number)
    if street and NUMBER.fullmatch(number):
        return kind, street, number
    return None


def registry(path, snapshot_year):
    by_address = defaultdict(set)
    by_id = defaultdict(set)
    counts = Counter()
    with path.open(encoding='utf-8', newline='') as source:
        for house_id, address, year in csv.reader(source, delimiter='\t'):
            counts['rows'] += 1
            house_id = int(house_id)
            prefix, sep, number = address.rpartition(',')
            street = prefix.rsplit(',', 1)[-1]
            key = address_key(street, number) if sep else None
            if not key:
                counts['unparsed_address'] += 1
                continue
            valid_year = int(year) if year.isdecimal() else 0
            if not 1600 <= valid_year <= snapshot_year:
                counts['no_year'] += 1
                valid_year = 0
            by_id[house_id].add((key, valid_year))
    counts['parsed_cards'] = len(by_id)
    counts['conflicting_cards'] = sum(len(records) > 1 for records in by_id.values())
    for house_id, records in by_id.items():
        if len(records) == 1:
            key, year = next(iter(records))
            by_address[key].add((house_id, year))
    counts['ambiguous_address'] = sum(len(records) > 1 for records in by_address.values())
    return {key: next(iter(records)) for key, records in by_address.items()
            if len(records) == 1 and next(iter(records))[1]}, counts


def osm_houses(path, addresses, reviewed_areas=()):
    shapes, metadata, points = [], [], []
    districts = json.loads((ROOT / 'tools/data/districts.json').read_text(encoding='utf-8'))['features']
    zelenograd_names = {'Крюково', 'Матушкино', 'Савелки', 'Силино', 'Старое Крюково'}
    zelenograd = unary_union([shape(f['geometry']).buffer(0) for f in districts if f['properties']['n'] in zelenograd_names])

    def key(tags, location):
        street = tags.get('addr:street') or tags.get('addr:place')
        number = tags.get('addr:housenumber')
        # Зданию без улицы засчитываем номер корпуса, только если его контур
        # или адресная точка находится внутри пяти районов Зеленограда.
        if not street and number and re.fullmatch(r'к\s*\d+[а-я]?', cleaned(number)) and zelenograd.contains(location):
            street = 'Зеленоград'
        return address_key(street, number) if street and number else None

    class Handler(osmium.SimpleHandler):
        def node(self, node):
            if not node.tags.get('addr:housenumber') or not node.location.valid():
                return
            lon, lat = node.location.lon, node.location.lat
            addr = key(node.tags, Point(lon, lat))
            if addr in addresses:
                points.append((addr, Point(lon * X, lat * Y)))

        def area(self, area):
            if area.tags.get('building') not in RESIDENTIAL and area.id not in reviewed_areas:
                return
            outer_rings = list(area.outer_rings())
            # Карта рисует первый внешний контур. Для ручной сверки допускаем
            # его в составном объекте, если его отпечаток совпал с проверенным.
            if not outer_rings or (len(outer_rings) != 1 and area.id not in reviewed_areas):
                return
            ring = [(n.lon, n.lat) for n in outer_rings[0]]
            if len(ring) < 4:
                return
            holes = [[(n.lon * X, n.lat * Y) for n in inner] for inner in area.inner_rings(outer_rings[0])]
            polygon = Polygon([(x * X, y * Y) for x, y in ring], holes)
            if polygon.is_valid and polygon.area:
                shapes.append(polygon)
                position = polygon.representative_point()
                metadata.append((area.id, ring, osm_year(area.tags), key(area.tags, Point(position.x / X, position.y / Y))))

    Handler().apply_file(str(path), locations=True)
    tree = STRtree(shapes)
    direct = defaultdict(set)
    for i, (_, _, _, key) in enumerate(metadata):
        if key in addresses:
            direct[key].add(i)
    for key, point in points:
        hits = tree.query(point, predicate='covered_by')
        if len(hits) == 1:
            i = int(hits[0])
            # Не переносим адрес метки на контур с собственным другим адресом.
            if metadata[i][3] in (None, key):
                direct[key].add(i)
    matches = defaultdict(set)
    for key, candidates in direct.items():
        if len(candidates) == 1:
            matches[next(iter(candidates))].add(addresses[key])
    return shapes, tree, metadata, {i: next(iter(records)) for i, records in matches.items() if len(records) == 1}


def decoded_polygon(origin, coords):
    lon, lat = origin
    vertices = []
    for dx, dy in zip(coords[::2], coords[1::2]):
        lon += dx / 1e5
        lat += dy / 1e5
        vertices.append((lon * X, lat * Y))
    return Polygon(vertices)


def matched_map_houses(shapes, tree, matches, additional_indices=()):
    for path in sorted((ROOT / 'assets/dmap').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        mapped = []
        for house in data['b']:
            if (not house[3] and not additional_indices) or len(house[0]) < 6:
                continue
            polygon = decoded_polygon(data['o'], house[0])
            if not polygon.is_valid or not polygon.area:
                continue
            hits = []
            for idx in tree.query(polygon, predicate='intersects'):
                if not house[3] and idx not in additional_indices:
                    continue
                other = shapes[idx]
                overlap = polygon.intersection(other).area
                if overlap >= 0.75 * (polygon.area + other.area - overlap):
                    hits.append(int(idx))
            if len(hits) != 1 or hits[0] not in matches:
                continue
            mapped.append((house, hits[0]))
        yield path, data, mapped


def update_existing_maps(maps, matches, checked_at):
    counts = Counter()
    for path, data, mapped in maps:
        changed = False
        for house, i in mapped:
            if i not in matches:
                continue
            source_id, year = matches[i]
            counts['matched'] += 1
            counts['filled'] += house[2] == 0
            counts['corrected'] += bool(house[2] and house[2] != year)
            house[2] = year
            if not house[3]:
                house[3] = 1
                house[4] = None  # У этого контура ещё нет оценки шума.
            house[5:] = [source_id]
            changed = True
        if changed:
            counts['districts'] += 1
            data['age_checked'] = checked_at
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('osm', type=Path)
    parser.add_argument('mingkh_tsv', type=Path)
    parser.add_argument('--date', required=True)
    args = parser.parse_args()
    from datetime import date
    snapshot = date.fromisoformat(args.date)
    addresses, counts = registry(args.mingkh_tsv, snapshot.year)
    review = json.loads(REVIEW_PATH.read_text(encoding='utf-8')) if REVIEW_PATH.exists() else {}
    reviewed_areas = {d['area'] for d in review.values() if d.get('year')}
    additional_areas = {d['area'] for d in review.values() if d.get('confirm_residential')}
    shapes, tree, metadata, matches = osm_houses(args.osm, addresses, reviewed_areas)
    by_area = {area: i for i, (area, _, _, _) in enumerate(metadata)}
    decisions = {}
    # Ручная сверка относится к конкретному контуру и приоритетнее строки
    # реестра. Один адрес может относиться к двум разным зданиям.
    for source_id, decision in review.items():
        if not decision.get('year'):
            continue
        i = by_area.get(decision['area'])
        if i is None or outline_fingerprint(metadata[i][1]) != decision['outline']:
            continue
        decisions[i] = (-int(source_id), decision['year'])
    reviewed_ids = {abs(record[0]) for record in decisions.values()}
    reviewed_ids.update(int(id) for id, decision in review.items() if decision.get('status') == 'replaced')
    matches = {i: record for i, record in matches.items() if record[0] not in reviewed_ids}
    matches.update(decisions)
    additional_indices = {i for i in decisions if metadata[i][0] in additional_areas}
    maps = list(matched_map_houses(shapes, tree, matches, additional_indices))
    # Большой разрыв может относиться к другому зданию с тем же адресом
    # или к реконструкции. Оставляем исходный год до поадресной проверки.
    conflicts = {i for i, (source_id, year) in matches.items()
                 if i not in decisions and (source_id in REFERENCE_CONFLICTS
                 or (metadata[i][2] and abs(metadata[i][2] - year) >= REVIEW_GAP))}
    for _, _, mapped in maps:
        conflicts.update(i for house, i in mapped
                         if i not in decisions and house[2] and abs(house[2] - matches[i][1]) >= REVIEW_GAP)
    counts['needs_review'] = len(conflicts)
    review_ids = sorted(matches[i][0] for i in conflicts)
    matches = {i: record for i, record in matches.items() if i not in conflicts}
    if not matches:
        raise SystemExit('Нет подтверждённых совпадений, файлы не изменены.')
    houses = {}
    for i, (source_id, year) in sorted(matches.items()):
        osm_id, ring, old, _ = metadata[i]
        houses[str(osm_id)] = [outline_fingerprint(ring), year, source_id]
        counts['matched_osm'] += 1
        counts['filled_osm'] += old == 0
        counts['corrected_osm'] += bool(old and old != year)
    data = {'date': snapshot.isoformat(), 'source': 'https://dom.mingkh.ru/moskva/',
            'catalogues': ['https://dom.mingkh.ru/moskva/moskva/houses', 'https://dom.mingkh.ru/moskva/zelenograd/houses'],
            'needs_review': review_ids,
            'houses': houses}
    VERIFIED_PATH.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('Реестр и выгрузка OSM:', dict(counts))
    print('Отрисованные контуры с окрестностями:', dict(update_existing_maps(maps, matches, data['date'])))


if __name__ == '__main__':
    main()
