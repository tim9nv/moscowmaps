"""Build the park catalogue and walking layers from the Atlas index and OSM PBF."""
import argparse
import base64
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

import osmium
from shapely import from_wkb, make_valid
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

rules = __import__("extract-park-trails")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "parks/catalog"
ALLOWED = {"path", "footway", "pedestrian", "steps", "track", "cycleway", "service"}


def packed(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.b64encode(gzip.compress(raw, mtime=0)).decode()


class Extract(osmium.SimpleHandler):
    def __init__(self, shapes):
        super().__init__()
        self.tree = STRtree(shapes)
        self.shapes = shapes
        self.restricted = []
        self.ways = defaultdict(list)
        self.blocked_nodes = set()
        self.factory = osmium.geom.WKBFactory()

    def node(self, node):
        if len(node.tags) and not rules.permitted(dict(node.tags)):
            self.blocked_nodes.add(node.id)

    def way(self, way):
        t = dict(way.tags)
        kind = t.get("highway")
        if kind not in ALLOWED or not rules.permitted(t) or any(t.get(k) == "yes" for k in ("indoor", "fee", "area")):
            return
        if kind in {"service", "cycleway"} and t.get("foot") not in {"yes", "designated", "permissive"}:
            return
        if any(n.ref in self.blocked_nodes for n in way.nodes):
            return
        points = [(n.lon, n.lat) for n in way.nodes if n.location.valid()]
        if len(points) != len(way.nodes) or len(set(points)) < 2:
            return
        line = LineString(points)
        for i in self.tree.query(line, predicate="intersects"):
            self.ways[int(i)].append((rules.trail_type(t), line))

    def area(self, area):
        t = dict(area.tags)
        if not (t.get("access") in {"no", "private", "permit", "customers"} or t.get("fee") == "yes"):
            return
        if t.get("building") or not any(k in t for k in ("leisure", "landuse", "boundary", "tourism", "natural")):
            return
        try:
            shape = make_valid(from_wkb(bytes.fromhex(self.factory.create_multipolygon(area))))
        except (RuntimeError, ValueError):
            return
        if not shape.is_empty and len(self.tree.query(shape, predicate="intersects")):
            self.restricted.append(shape)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbf", type=Path)
    args = parser.parse_args()
    parks = json.loads(re.search(r"const PARKS = (.*?);\n", (ROOT / "parks.html").read_text()).group(1))
    shapes = [unary_union([make_valid(Polygon(ring)) for ring in p["p"] if len(ring) >= 4]) for p in parks]
    extract = Extract(shapes)
    extract.apply_file(str(args.pbf), locations=True, idx="flex_mem")
    restrictions = STRtree(extract.restricted)
    index = []
    groups = []
    group = {}
    for i, (park, shape) in enumerate(zip(parks, shapes)):
        blocked = unary_union([extract.restricted[j] for j in restrictions.query(shape, predicate="intersects")])
        allowed = shape.difference(blocked)
        trails = defaultdict(list)
        for kind, line in extract.ways[i]:
            for part in rules.lines(line.intersection(allowed)):
                points = [[round(y, 6), round(x, 6)] for x, y in part.coords]
                if len({tuple(point) for point in points}) > 1:
                    trails[kind].append(points)
        record = {"b": park["p"], "t": trails}
        key = str(i + 1)
        group[key] = record
        if len(packed(group)) > 240000 and len(group) > 1:
            del group[key]
            groups.append(group)
            group = {key: record}
        index.append({"id": key, "name": park["n"], "short": park["s"], "center": park["c"],
                      "group": len(groups) + 1, "count": sum(map(len, trails.values()))})
    if group:
        groups.append(group)
    for old in OUT.glob("trails-*.txt"):
        old.unlink()
    for i, value in enumerate(groups, 1):
        (OUT / f"trails-{i}.txt").write_text(packed(value))
    (OUT / "parks.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(len(index), "parks;", sum(x["count"] for x in index), "sections;", len(groups), "packs")


if __name__ == "__main__":
    main()
