"""Export a park's mapped outdoor pedestrian paths from OSM XML snapshots."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import LineString, mapping
from shapely.ops import polygonize, unary_union


def read_osm(files):
    objects = {kind: {} for kind in ("node", "way", "relation")}
    for file in files:
        for item in ET.parse(file).getroot():
            if item.tag in objects:
                objects[item.tag][item.attrib["id"]] = item
    return objects


def tags(item):
    return {tag.attrib["k"]: tag.attrib["v"] for tag in item.findall("tag")}


def refs(way):
    return [node.attrib["ref"] for node in way.findall("nd")]


def polygon(osm, relation_id, coords):
    rings = {"outer": [], "inner": []}
    for member in osm["relation"][relation_id].findall("member"):
        role = member.attrib["role"] or "outer"
        if member.attrib["type"] == "way" and role in rings:
            way = osm["way"][member.attrib["ref"]]
            rings[role].append(LineString([coords[node] for node in refs(way)]))
    exterior = unary_union(list(polygonize(rings["outer"])))
    if exterior.is_empty:
        raise ValueError(f"OSM relation {relation_id} has no closed outer ring")
    return exterior.difference(unary_union(list(polygonize(rings["inner"]))))


def permitted(t):
    banned = {"no", "private", "customers", "permit", "use_sidepath", "discouraged"}
    if t.get("foot") in banned or any(key in t for key in ("access:conditional", "foot:conditional")):
        return False
    return t.get("access") not in banned or t.get("foot") in {"yes", "designated", "permissive"}


def trail_type(t):
    if t["highway"] == "steps":
        return "steps"
    if t.get("bridge") == "boardwalk" or t.get("surface") == "wood":
        return "boardwalk"
    if t.get("surface") in {"asphalt", "concrete", "paved", "paving_stones", "concrete:plates", "sett", "cobblestone"}:
        return "paved"
    if t.get("surface") in {"unpaved", "ground", "dirt", "earth", "grass", "gravel", "fine_gravel", "compacted", "sand", "mud"}:
        return "unpaved"
    return "unknown"


def lines(geometry):
    if geometry.geom_type == "LineString" and not geometry.is_empty:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from lines(part)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--park", required=True, help="OSM boundary relation ID")
    parser.add_argument("--exclude", action="append", default=[], help="Excluded OSM relation ID")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    osm = read_osm(args.files)
    coords = {key: (float(node.attrib["lon"]), float(node.attrib["lat"])) for key, node in osm["node"].items()}
    blocked = {key for key, node in osm["node"].items() if not permitted(tags(node))}
    boundary = polygon(osm, args.park, coords)
    excluded = unary_union([polygon(osm, item, coords) for item in args.exclude])
    allowed = boundary.difference(excluded)
    features = []
    for key, way in sorted(osm["way"].items(), key=lambda item: int(item[0])):
        t = tags(way)
        kind = t.get("highway")
        if kind not in {"path", "footway", "pedestrian", "steps", "track", "cycleway", "service"}:
            continue
        if kind in {"cycleway", "service"} and t.get("foot") not in {"yes", "designated", "permissive"}:
            continue
        if not permitted(t) or t.get("indoor") == "yes" or t.get("area") == "yes" or t.get("fee") == "yes":
            continue
        node_ids = refs(way)
        if len(node_ids) < 2 or any(node not in coords or node in blocked for node in node_ids):
            continue
        track = LineString([coords[node] for node in node_ids]).intersection(allowed)
        for part in lines(track):
            points = [[round(x, 6), round(y, 6)] for x, y in part.coords]
            if len({tuple(point) for point in points}) > 1:
                props = {"kind": trail_type(t), "osm": key}
                if t.get("name"):
                    props["name"] = t["name"]
                features.append({"type": "Feature", "properties": props, "geometry": {"type": "LineString", "coordinates": points}})
    if not features:
        raise ValueError("No pedestrian paths found inside the supplied park boundary")
    for kind, geometry in (("boundary", boundary), ("excluded", excluded)):
        if not geometry.is_empty:
            features.insert(0, {"type": "Feature", "properties": {"kind": kind}, "geometry": mapping(geometry)})
    args.output.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                     ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Exported {sum(f['geometry']['type'] == 'LineString' for f in features)} path sections")


if __name__ == "__main__":
    main()
