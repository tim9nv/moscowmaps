"""Подтверждённые годы для контуров домов OpenStreetMap."""
import hashlib
import json
from pathlib import Path
import re
import struct

RESIDENTIAL = {'apartments', 'residential', 'house', 'detached', 'semidetached_house', 'terrace', 'dormitory'}
VERIFIED_PATH = Path(__file__).with_name('data') / 'house_year_verified.json'


def load_verified():
    if VERIFIED_PATH.exists():
        return json.loads(VERIFIED_PATH.read_text(encoding='utf-8'))
    return {'date': None, 'houses': {}}


def outline_fingerprint(ring):
    points = sorted({(round(x * 1e5), round(y * 1e5)) for x, y in ring})
    data = b''.join(struct.pack('<ii', x, y) for x, y in points)
    return hashlib.blake2s(data, digest_size=8).hexdigest()


def osm_year(tags):
    for key in ('start_date', 'building:start_date', 'construction_date'):
        match = re.search(r'(1[6-9]\d\d|20[0-3]\d)', tags.get(key) or '')
        if match:
            return int(match.group(1))
    return 0


def resolve_year(verified, area, ring):
    record = verified.get(str(area.id))
    if record and record[0] == outline_fingerprint(ring):
        return record[1], record[2]
    return osm_year(area.tags), 0
