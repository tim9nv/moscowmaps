"""Build the Moscow-wide relief layer from Copernicus GLO-30 Public (2021).

Usage: python tools/build_city_relief.py moscow.osm.pbf /path/to/tiles
Dependencies: numpy, rasterio, shapely >= 2.1, osmium.
Download Copernicus_DSM_COG_10_N55_00_E036/037_00_DEM and
Copernicus_DSM_COG_10_N56_00_E037_00_DEM from the AWS registry (each is a
directory containing its namesake .tif). Copernicus heights use EGM2008.
"""
import argparse
import base64
from itertools import groupby
import json
import math
from pathlib import Path

import numpy as np
import osmium
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject
from shapely import orient_polygons
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
MOSCOW = 102269
ANNEX = {2263058: ("Новомосковский округ", "НАО"), 2263059: ("Троицкий округ", "ТАО")}
LON_CELLS = 600
LAT_CELLS = 1000


def boundaries(pbf):
    factory = osmium.geom.GeoJSONFactory()
    polygons = {}

    class Extract(osmium.SimpleHandler):
        def area(self, area):
            if not area.from_way() and area.orig_id() in {MOSCOW, *ANNEX}:
                polygons[area.orig_id()] = shape(json.loads(factory.create_multipolygon(area))).buffer(0)

    Extract().apply_file(str(pbf), locations=True)
    if set(polygons) != {MOSCOW, *ANNEX}:
        raise ValueError("The OSM extract must contain Moscow and both annexed districts")
    return polygons


def read_grid(tile_dir, city):
    left, bottom, right, top = city.bounds
    # Grid edges align with integer degrees so tile seams need no compositing.
    xmin = math.floor(left * LON_CELLS) - 2
    xmax = math.ceil(right * LON_CELLS) + 2
    ymin = math.floor(bottom * LAT_CELLS) - 2
    ymax = math.ceil(top * LAT_CELLS) + 2
    width, height = xmax - xmin, ymax - ymin
    bounds = [xmin / LON_CELLS, ymin / LAT_CELLS, xmax / LON_CELLS, ymax / LAT_CELLS]
    transform = from_bounds(*bounds, width, height)
    grid = np.full((height, width), np.nan, dtype=np.float32)
    tiles = []
    for path in sorted(tile_dir.glob("Copernicus_DSM_COG_10_*_DEM.tif")):
        with rasterio.open(path) as src:
            if src.crs.to_epsg() != 4326 or abs(src.res[1] - 1 / 3600) > 1e-8:
                raise ValueError(f"Unexpected grid in {path}")
            reproject(rasterio.band(src, 1), grid, dst_transform=transform,
                      dst_crs="EPSG:4326", dst_nodata=np.nan,
                      init_dest_nodata=False, resampling=Resampling.average)
            tiles.append(path.stem)
    return grid, transform, bounds, tiles


def summary(heights):
    if not heights.size or not np.isfinite(heights).all():
        raise ValueError("An elevation zone has uncovered cells")
    return {
        "h": round(float(heights.mean()), 1),
        "hmin": round(float(heights.min()), 1),
        "hmax": round(float(heights.max()), 1),
        "low": round(float((heights < 135).mean()) * 100, 1),
        "cells": int(heights.size),
    }


def encode_grid(values):
    """Keep nonzero cells verbatim and store zero runs as a marker and length."""
    packed = bytearray()
    for is_empty, cells in groupby(values.tobytes(), key=lambda value: value == 0):
        if not is_empty:
            packed.extend(cells)
            continue
        length = sum(1 for _ in cells)
        runs, remainder = divmod(length, 255)
        packed.extend(b'\x00\xff' * runs)
        if remainder:
            packed.extend((0, remainder))
    return base64.b64encode(packed).decode("ascii")


def build(pbf, tile_dir, output):
    polygons = boundaries(pbf)
    city = polygons[MOSCOW]
    grid, transform, bounds, tiles = read_grid(tile_dir, city)

    def mask(geo):
        return geometry_mask([geo], grid.shape, transform, invert=True)

    def outline(geo):
        return mapping(orient_polygons(geo.simplify(0.00025), exterior_cw=True))

    city_mask = mask(city)
    whole = summary(grid[city_mask])
    print(f"Moscow: {whole}; cells {grid.shape}; {tiles}")
    # Restrict the color range to the city's sampled grid, pad outside the
    # raster support and let the web map clip the contours to the city.
    lo = math.floor(whole["hmin"])
    hi = math.ceil(whole["hmax"])
    if hi - lo > 255:
        raise ValueError("Elevation range exceeds the byte encoding")
    padding = mask(city.buffer(0.004))
    encoded = np.rint(np.clip(np.nan_to_num(grid, nan=lo), lo, hi) - lo).astype(np.uint8)
    encoded[~padding] = 0
    regions = json.loads((ROOT / "tools/data/districts.json").read_text(encoding="utf-8"))["features"]
    names = {f["properties"]["n"]: shape(f["geometry"]).buffer(0) for f in regions}
    annex = []
    for relation, (name, district) in ANNEX.items():
        geo = polygons[relation]
        names[name] = geo
        annex.append({"type": "Feature", "properties": {"n": name, "o": district}, "geometry": outline(geo)})
    stats = {name: summary(grid[mask(geometry) & city_mask]) for name, geometry in names.items()}
    if len(stats) != 127:
        raise ValueError(f"Expected 127 areas, got {len(stats)}")

    payload = {
        "source": "Copernicus DEM GLO-30 Public (2021)",
        "tiles": tiles,
        "boundary": outline(city),
        "annex": annex,
        "stats": stats,
        "grid": {"bounds": bounds, "nx": grid.shape[1], "ny": grid.shape[0],
                 "offset": lo, "bytes": encode_grid(encoded)},
    }
    output.write_text("const CITY_RELIEF = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                      encoding="utf-8")
    print(f"{len(stats)} areas; {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("osm", type=Path)
    parser.add_argument("tiles", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "assets/city-relief.js")
    args = parser.parse_args()
    build(args.osm, args.tiles, args.output)
