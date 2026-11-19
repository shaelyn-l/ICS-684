"""Mountain profile (side view) data.

Builds public/data/profile.json: a line from the coast, through the nine study
sites, up to the summit of Mauna Loa, with ground elevation sampled every ~100 m
along it and each site placed on the line. Also writes reports/profile_check.md
(the checks and a text sketch of the profile) and prints the same checks.

Elevation comes from the USGS 10 m DEM if a GeoTIFF is present in raw/dem/,
otherwise from the free AWS Terrain Tiles (Terrarium PNGs, no key), which are
downloaded once and cached in raw/terrain_cache/ (git-ignored with the rest of
raw/). Site elevations come from sites.geojson, not from the sampled terrain.

Requires public/data/sites.geojson (02_sites.py) and, for the AWS tiles, an
internet connection on the first run. Rerunning overwrites the outputs.
Run from anywhere:  python data-pipeline/scripts/05_profile.py
"""

import json
import math
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.errors import NotGeoreferencedWarning

# file locations, built from where this script lives so it runs from any folder
PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent
SITES_GEOJSON = ROOT / "public" / "data" / "sites.geojson"
DEM_DIR = PIPELINE / "raw" / "dem"
TILE_CACHE = PIPELINE / "raw" / "terrain_cache"
OUTPUT = ROOT / "public" / "data" / "profile.json"
REPORT = PIPELINE / "reports" / "profile_check.md"


# ===========================================================================
# Settings
# ===========================================================================
SUMMIT = (-155.6054, 19.4756)   # Mauna Loa summit (lon, lat)
SUMMIT_REFERENCE_M = 4169       # published summit elevation, for the check only
STEP_M = 100                    # sampling interval along the line
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ZOOM = 12                       # ~36 m pixels at this latitude, enough for 100 m sampling
BEND_THRESHOLD_KM = 2.0         # bend the line if the fitted line misses the summit by more
MAX_COAST_SEARCH_KM = 40        # how far past the lowest site to look for the coastline
OFF_LINE_FLAG_KM = 5.0          # sites farther than this from the line are flagged

# UTM zone 5N: metres, so distances and the line fit are in real units
to_metres = Transformer.from_crs("EPSG:4326", "EPSG:32605", always_xy=True)
to_lonlat = Transformer.from_crs("EPSG:32605", "EPSG:4326", always_xy=True)


# ===========================================================================
# Elevation lookup: USGS DEM if present, otherwise AWS Terrarium tiles
# ===========================================================================
dem_files = sorted(DEM_DIR.glob("*.tif")) + sorted(DEM_DIR.glob("*.tiff")) if DEM_DIR.exists() else []

if dem_files:
    SOURCE = "usgs-dem-10m"
    dem = rasterio.open(dem_files[0])
    dem_band = dem.read(1, masked=True)
    from_lonlat_to_dem = Transformer.from_crs("EPSG:4326", dem.crs, always_xy=True)

    def elevation_at(lon, lat):
        x, y = from_lonlat_to_dem.transform(lon, lat)
        row, col = dem.index(x, y)
        value = dem_band[row, col]
        return None if np.ma.is_masked(value) else float(value)

else:
    SOURCE = "aws-terrarium"
    TILE_CACHE.mkdir(parents=True, exist_ok=True)
    tiles = {}  # (x, y) -> elevation array, so each tile is read once

    def load_tile(tx, ty):
        if (tx, ty) not in tiles:
            path = TILE_CACHE / f"{ZOOM}_{tx}_{ty}.png"
            if not path.exists():
                request = urllib.request.Request(TILE_URL.format(z=ZOOM, x=tx, y=ty),
                                                 headers={"User-Agent": "terrain-profile-script"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    path.write_bytes(response.read())
            # the PNGs have no map coordinates, so rasterio warns; that's expected
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", NotGeoreferencedWarning)
                with rasterio.open(path) as png:
                    rgb = png.read([1, 2, 3]).astype(float)
            # Terrarium encoding: elevation = R×256 + G + B/256 − 32768 (metres)
            tiles[(tx, ty)] = rgb[0] * 256 + rgb[1] + rgb[2] / 256 - 32768
        return tiles[(tx, ty)]

    def pixel_value(px, py):
        # px, py: whole pixel numbers across the whole zoom level
        tile = load_tile(px // 256, py // 256)
        return tile[py % 256, px % 256]

    def elevation_at(lon, lat):
        # web mercator position in pixels at this zoom, then bilinear interpolation
        # between the four surrounding pixel centres
        n = 2 ** ZOOM * 256
        fx = (lon + 180) / 360 * n - 0.5
        lat_rad = math.radians(lat)
        fy = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n - 0.5
        x0, y0 = math.floor(fx), math.floor(fy)
        dx, dy = fx - x0, fy - y0
        top = pixel_value(x0, y0) * (1 - dx) + pixel_value(x0 + 1, y0) * dx
        bottom = pixel_value(x0, y0 + 1) * (1 - dx) + pixel_value(x0 + 1, y0 + 1) * dx
        return float(top * (1 - dy) + bottom * dy)


def elevation_at_metres(point):
    return elevation_at(*to_lonlat.transform(point[0], point[1]))


print("elevation source:", SOURCE, f"({dem_files[0].name})" if dem_files else f"(zoom {ZOOM})")


# ===========================================================================
# 1. Load the sites, in metres, ordered by elevation
# ===========================================================================
with open(SITES_GEOJSON) as f:
    site_features = json.load(f)["features"]

sites = []
for feature in site_features:
    x, y = to_metres.transform(*feature["geometry"]["coordinates"])
    sites.append({
        "site": feature["properties"]["site"],
        "elevation_m": feature["properties"]["elevation_m"],
        "xy": np.array([x, y]),
    })
sites.sort(key=lambda s: s["elevation_m"])
print("\nsites, lowest to highest:", ", ".join(s["site"] for s in sites))


# ===========================================================================
# 2. Fit a straight line through the site centroids
# ===========================================================================
# The best-fit line (total least squares, through the mean point, along the direction
# the sites spread out most). Its direction is turned to point upslope: from the lowest
# site toward the highest.
points = np.array([s["xy"] for s in sites])
centre = points.mean(axis=0)
_, _, axes = np.linalg.svd(points - centre)
direction = axes[0]
if np.dot(sites[-1]["xy"] - sites[0]["xy"], direction) < 0:
    direction = -direction
normal = np.array([-direction[1], direction[0]])  # 90° to the left of upslope

along = [(s["xy"] - centre) @ direction for s in sites]
bearing = math.degrees(math.atan2(direction[0], direction[1])) % 360
print(f"fitted line: heads upslope at bearing {bearing:.0f}°, sites span {(max(along) - min(along)) / 1000:.1f} km along it")

summit_xy = np.array(to_metres.transform(*SUMMIT))
summit_off_km = abs((summit_xy - centre) @ normal) / 1000
print(f"the fitted line, extended upslope, passes {summit_off_km:.1f} km from the summit")


# ===========================================================================
# 3. Choose the upper end: straight to the summit, or bend
# ===========================================================================
# The sites sit on the windward (east) slope; the summit is ~30 km farther west. If the
# fitted line, extended, passes within BEND_THRESHOLD_KM of the summit, one straight line
# from the coast to the summit is used. Otherwise the straight line would end on the flank
# of Mauna Loa, not at its top, so the profile would never reach the summit. In that case
# the line follows the fit through the sites as far as the highest site along it, then
# turns and runs straight to the summit. The bend is above all the sites, so it doesn't
# change where any site falls on the line.
upper_site_point = centre + max(along) * direction
if summit_off_km <= BEND_THRESHOLD_KM:
    LINE_SHAPE = "straight"
    vertices_upper = [summit_xy]
else:
    LINE_SHAPE = "bent"
    vertices_upper = [upper_site_point, summit_xy]
print("line shape:", LINE_SHAPE)


# ===========================================================================
# 4. Find the coastline: extend downslope from the lowest site until the ground is at sea level
# ===========================================================================
# Terrarium tiles include sea-floor depth, so the first sample at or below 0 m is the coast.
lower_site_point = centre + min(along) * direction
coast_xy = None
for step in range(int(MAX_COAST_SEARCH_KM * 1000 / STEP_M) + 1):
    candidate = lower_site_point - step * STEP_M * direction
    if elevation_at_metres(candidate) <= 0:
        coast_xy = candidate
        break
if coast_xy is None:
    raise SystemExit(f"no coastline within {MAX_COAST_SEARCH_KM} km downslope of the lowest site")
print(f"coastline found {np.linalg.norm(coast_xy - lower_site_point) / 1000:.1f} km beyond the lowest site along the line")

vertices = [coast_xy] + vertices_upper


# ===========================================================================
# 5. Sample elevation every STEP_M along the line
# ===========================================================================
segment_lengths = [np.linalg.norm(b - a) for a, b in zip(vertices[:-1], vertices[1:])]
total_m = sum(segment_lengths)

profile = []
for d in np.append(np.arange(0, total_m, STEP_M), total_m):
    # walk along the segments to the point at distance d
    remaining = d
    last = len(segment_lengths) - 1
    for i, (a, b, length) in enumerate(zip(vertices[:-1], vertices[1:], segment_lengths)):
        if remaining <= length or i == last:
            point = a + (b - a) * min(remaining / length, 1)
            break
        remaining -= length
    profile.append({"distance_km": round(d / 1000, 2),
                    "elevation_m": round(elevation_at_metres(point))})

elevations = [p["elevation_m"] for p in profile]
print(f"\nline length {total_m / 1000:.1f} km, {len(profile)} samples")
print(f"elevation sampled: min {min(elevations)} m, max {max(elevations)} m")
print(f"coast end {profile[0]['elevation_m']} m, summit end {profile[-1]['elevation_m']} m "
      f"(published summit {SUMMIT_REFERENCE_M} m)")


# ===========================================================================
# 6. Place each site on the line
# ===========================================================================
# The sites spread ~23 km across the slope, so no single line passes close to all of
# them: projected straight onto the line, NAN, COO, CRA and WAI land 6.5–12.3 km off it,
# and WAI (966 m) lands after CRA (1,142 m). So each site is placed by its elevation
# instead: distance_km is where the sampled ground along the line first rises to the
# site's elevation (interpolated between samples, searching up from the coast). Sites
# are then always in elevation order and sit on the ground in the side view.
# offset_km is still the distance from the site to the nearest point on the line, so
# the app (and this report) can say how far each real site is from the slice.
def distance_at_elevation(target_m):
    for before, after in zip(profile[:-1], profile[1:]):
        if before["elevation_m"] < target_m <= after["elevation_m"]:
            share = (target_m - before["elevation_m"]) / (after["elevation_m"] - before["elevation_m"])
            return before["distance_km"] + share * (after["distance_km"] - before["distance_km"])
    return profile[0]["distance_km"] if target_m <= profile[0]["elevation_m"] else profile[-1]["distance_km"]


site_records = []
for s in sites:
    best = None
    start = 0.0
    for a, b, length in zip(vertices[:-1], vertices[1:], segment_lengths):
        t = np.clip((s["xy"] - a) @ (b - a) / length ** 2, 0, 1)
        nearest = a + t * (b - a)
        offset = np.linalg.norm(s["xy"] - nearest)
        # which side of the line, looking upslope: + north-ish (left), − south-ish (right)
        u, v = b - a, s["xy"] - a
        side = np.sign(u[0] * v[1] - u[1] * v[0])
        if best is None or offset < best[1]:
            best = (start + t * length, offset, side)
        start += length
    site_records.append({
        "site": s["site"],
        "distance_km": round(distance_at_elevation(s["elevation_m"]), 2),
        "projected_km": round(best[0] / 1000, 2),  # report only: nearest point on the line
        "offset_km": round(best[1] / 1000, 2),
        "elevation_m": s["elevation_m"],
        "side": "left (north)" if best[2] > 0 else "right (south)",
    })

summit_record = {"distance_km": round(total_m / 1000, 2), "elevation_m": profile[-1]["elevation_m"]}


# ===========================================================================
# 7. Write profile.json
# ===========================================================================
output = {
    "source": SOURCE,
    "line": [[round(lon, 5), round(lat, 5)] for lon, lat in (to_lonlat.transform(*v) for v in vertices)],
    "profile": profile,
    "sites": [{k: r[k] for k in ("site", "distance_km", "offset_km", "elevation_m")} for r in site_records],
    "summit": summit_record,
}
OUTPUT.write_text(json.dumps(output, indent=1) + "\n")
print("\nwrote public/data/profile.json")


# ===========================================================================
# 8. Checks
# ===========================================================================
by_distance = sorted(site_records, key=lambda r: r["distance_km"])
order_along = [r["site"] for r in by_distance]
order_elevation = [s["site"] for s in sites]
in_order = order_along == order_elevation
out_of_order = [f"{a['site']} ({a['elevation_m']:.0f} m) comes before {b['site']} ({b['elevation_m']:.0f} m)"
                for a, b in zip(by_distance[:-1], by_distance[1:]) if a["elevation_m"] > b["elevation_m"]]
far = [r for r in site_records if r["offset_km"] > OFF_LINE_FLAG_KM]

checks = [
    ("coast end near sea level (within ±50 m)", abs(profile[0]["elevation_m"]) <= 50),
    ("summit end near the summit (3,800–4,250 m)", 3800 <= profile[-1]["elevation_m"] <= 4250),
    ("sites in elevation order along the line", in_order),
    (f"no site more than {OFF_LINE_FLAG_KM:.0f} km off the line (information only: sites are placed by elevation)", not far),
]
print("\nchecks:")
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
for line in out_of_order:
    print("        out of order:", line)
for r in far:
    print(f"        far off the line: {r['site']} {r['offset_km']:.1f} km, {r['side']}")


# ===========================================================================
# 9. Text sketch of the profile, with sites marked
# ===========================================================================
WIDTH, HEIGHT = 100, 22
top = max(max(elevations), max(r["elevation_m"] for r in site_records))
total_km = total_m / 1000
grid = [[" "] * WIDTH for _ in range(HEIGHT)]


def col_of(km):
    return min(WIDTH - 1, int(km / total_km * (WIDTH - 1) + 0.5))


def row_of(m):
    return HEIGHT - 1 - min(HEIGHT - 1, max(0, int(m / top * (HEIGHT - 1) + 0.5)))


# ground: highest sample in each column, filled below
for c in range(WIDTH):
    column = [p["elevation_m"] for p in profile if col_of(p["distance_km"]) == c]
    if column:
        r = row_of(max(column))
        grid[r][c] = "_" if r == HEIGHT - 1 else "."
        for below in range(r + 1, HEIGHT):
            grid[below][c] = ":"
# sites: a number at their distance and their own elevation (key below)
for i, r in enumerate(by_distance, start=1):
    grid[row_of(r["elevation_m"])][col_of(r["distance_km"])] = str(i)
grid[row_of(summit_record["elevation_m"])][WIDTH - 1] = "^"

labels = []
for r_index in range(HEIGHT):
    m = (HEIGHT - 1 - r_index) / (HEIGHT - 1) * top
    labels.append(f"{m:>5.0f} m |" if r_index % 3 == 0 or r_index == HEIGHT - 1 else "        |")
sketch = [labels[i] + "".join(grid[i]) for i in range(HEIGHT)]
sketch.append("        +" + "-" * WIDTH)
ticks = [" "] * WIDTH
tick_text = []
for km in range(0, int(total_km) + 1, 10):
    tick_text.append((col_of(km), f"{km}"))
axis = list(" " * (WIDTH + 12))
for c, text in tick_text:
    for j, ch in enumerate(text):
        if 9 + c + j < len(axis):
            axis[9 + c + j] = ch
sketch.append("".join(axis).rstrip() + "  km from the coast")
sketch.append("")
sketch.append("coast at 0 km (left), Mauna Loa summit ^ at the right end. Sites (by distance):")
sketch.append("  " + "   ".join(f"{i} {r['site']}" for i, r in enumerate(by_distance, start=1)))
print("\n" + "\n".join(sketch))


# ===========================================================================
# 10. Write the report
# ===========================================================================
report = [
    "# Profile check (05_profile.py)",
    "",
    "Generated by `scripts/05_profile.py`; rerunning overwrites this file.",
    "",
    "## Line",
    "",
    f"- Elevation source: `{SOURCE}`" + (f" ({dem_files[0].name})" if dem_files else f" (AWS Terrain Tiles, Terrarium, zoom {ZOOM}, cached in `raw/terrain_cache/`)"),
    f"- Shape: **{LINE_SHAPE}**. The straight line fitted through the nine sites (bearing {bearing:.0f}° upslope) "
    f"passes {summit_off_km:.1f} km from the summit"
    + (f", more than the {BEND_THRESHOLD_KM:.0f} km limit, so the line follows the fit from the coast to the "
       f"highest site along it and then turns straight to the summit." if LINE_SHAPE == "bent"
       else f", within the {BEND_THRESHOLD_KM:.0f} km limit, so one straight line runs from the coast to the summit."),
    f"- Vertices (lon, lat): " + " → ".join(f"({lon}, {lat})" for lon, lat in output["line"]),
    f"- Total length: **{total_km:.1f} km**, sampled every {STEP_M} m ({len(profile)} samples)",
    f"- Elevation sampled: min **{min(elevations)} m**, max **{max(elevations)} m**",
    f"- Coast end: {profile[0]['elevation_m']} m. Summit end: {profile[-1]['elevation_m']} m "
    f"(published {SUMMIT_REFERENCE_M} m; the tiles smooth the summit slightly)",
    "",
    "## Sites on the line",
    "",
    "Site elevation is from `sites.geojson` (mean of its 45 stations), not the sampled terrain. "
    "Placed at = where the ground along the line first reaches the site's elevation (the `distance_km` in profile.json). "
    "Projected = the nearest point on the line, for comparison. Offset = distance from the site to that nearest point; "
    "side is looking upslope.",
    "",
    "| Site | Elevation (m) | Placed at (km) | Projected (km) | Offset (km) | Side | Flag |",
    "|---|---|---|---|---|---|---|",
]
for r in by_distance:
    flag = f"**more than {OFF_LINE_FLAG_KM:.0f} km off**" if r["offset_km"] > OFF_LINE_FLAG_KM else ""
    report.append(f"| {r['site']} | {r['elevation_m']:,.0f} | {r['distance_km']:.1f} | {r['projected_km']:.1f} | {r['offset_km']:.1f} | {r['side']} | {flag} |")
report += ["", "## Checks", ""]
report += [f"- {'PASS' if ok else 'FAIL'}: {label}" for label, ok in checks]
report += [f"  - Out of order: {line}" for line in out_of_order]
report += [f"  - Far off the line: {r['site']} ({r['offset_km']:.1f} km, {r['side']})" for r in far]
report += ["", "## Sketch", "", "```", *sketch, "```", ""]
REPORT.write_text("\n".join(report))
print("\nwrote data-pipeline/reports/profile_check.md")
