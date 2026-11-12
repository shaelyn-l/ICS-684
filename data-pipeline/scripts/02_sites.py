"""Step 1.2: map-ready station and site points.

Reads the Biocomplexity sampling coordinates (already WGS84 longitude/latitude, so
no reprojection is needed), plus the mosquito capture and bird count files to flag
which points were used for each.

Writes:
  public/data/stations.geojson   one point per site + station + transect
  public/data/sites.geojson      one point per site at the mean of its stations

Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/02_sites.py
"""

import json
from pathlib import Path

import pandas as pd

# file locations, built from where this script lives so it runs from any folder
PIPELINE = Path(__file__).resolve().parent.parent
BIO = PIPELINE / "raw" / "biocomplexity_2001_2004"
OUT = PIPELINE.parent / "public" / "data"

# Bird counts were done at the odd-numbered stations only (per the Biocomplexity metadata).
# The 25 bird count rows at station 200 were checked earlier and are dropped from bird
# counts; see "Bird counts" in reports/data_notes.md.
BIRD_COUNT_STATIONS = [100, 300, 500, 700, 900]

# Full site names, taken from the site / LOCATION code lists in the two XML metadata files.
# That cross-reference was done in an earlier version of this script, so the names are
# written in here instead of being read from the XML each time.
SITE_NAMES = {
    "MAL": "Malama Ki Forest Reserve",
    "NAN": "Nanawale Forest Reserve",
    "BRY": "Bryson’s Cinder Cone, Puu Kaliu, Leilani Estates",
    "WAI": "Waiakea Forest Reserve",
    "COO": "Cooper Center, Volcano Village",
    "CRA": "Crater Rim, Hawaii Volcanoes National Park",
    "PUU": "Pu'u Unit, Ola'a Tract of Hawaii Volcanoes National Park",
    "CJR": "CJ Ralph, Kamehameha Schools Bishop Estates, Keauhou",
    "SOL": "Solomon’s Watering Hole, Kamehameha Schools Bishop Estates, Keauhou",
}


# ===========================================================================
# 1. Load the data
# ===========================================================================
df_coords = pd.read_csv(BIO / "Biocomplexity_sampling station spatial coordinates.csv")
df_capture = pd.read_csv(BIO / "Biocomplexity_mosquito capture data.csv")
df_counts = pd.read_csv(BIO / "Biocomplexity_bird count data.csv")

print(df_coords.shape)
print(df_coords.head())

# ===========================================================================
# 3. Which points had mosquito traps and which had bird counts
# ===========================================================================
# a point had traps if it appears anywhere in the capture file
trap_points = df_capture[["site", "station", "transect"]].drop_duplicates()
trap_points["has_mosquito_traps"] = True

# a point had bird counts if it appears in the bird count file at an odd-numbered station
counted = df_counts[df_counts["station"].isin(BIRD_COUNT_STATIONS)]
count_points = counted[["site", "station", "transect"]].drop_duplicates()
count_points["has_bird_counts"] = True

# join both flags onto the coordinates; points missing from a file get False
df_stations = df_coords.merge(trap_points, on=["site", "station", "transect"], how="left")
df_stations = df_stations.merge(count_points, on=["site", "station", "transect"], how="left")
df_stations["has_mosquito_traps"] = df_stations["has_mosquito_traps"].fillna(False).astype(bool)
df_stations["has_bird_counts"] = df_stations["has_bird_counts"].fillna(False).astype(bool)

print("stations with mosquito traps:", df_stations["has_mosquito_traps"].sum(), "of", len(df_stations))
print("stations with bird counts:   ", df_stations["has_bird_counts"].sum(), "of", len(df_stations))

# every trapped or counted point should have coordinates; any that don't are printed
all_data_points = pd.concat([trap_points, count_points])[["site", "station", "transect"]].drop_duplicates()
no_coords = all_data_points.merge(df_coords, on=["site", "station", "transect"], how="left", indicator=True)
no_coords = no_coords[no_coords["_merge"] == "left_only"]


# ===========================================================================
# 4. Write stations.geojson
# ===========================================================================
# GeoJSON is a list of "features": each has a point geometry [longitude, latitude] and a
# set of properties. Coordinates are rounded to 7 decimals (about 1 cm).
station_features = []
for row in df_stations.itertuples(index=False):
    station_features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(row.x_long, 7), round(row.y_lat, 7)]},
        "properties": {
            "site": row.site,
            "station": int(row.station),
            "transect": int(row.transect),
            "elevation_m": float(row.elevation_m),
            "has_mosquito_traps": bool(row.has_mosquito_traps),
            "has_bird_counts": bool(row.has_bird_counts),
        },
    })

OUT.mkdir(parents=True, exist_ok=True)
stations_json = {"type": "FeatureCollection", "features": station_features}
(OUT / "stations.geojson").write_text(json.dumps(stations_json, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
print("wrote public/data/stations.geojson:", len(station_features), "features")


# ===========================================================================
# 5. Site points: the mean of each site's stations
# ===========================================================================
# group the 45 stations of each site and take the mean position and elevation, plus the
# lowest and highest station elevation; sort from lowest to highest site
df_sites = df_coords.groupby("site").agg(
    lon=("x_long", "mean"),
    lat=("y_lat", "mean"),
    elevation_m=("elevation_m", "mean"),
    elevation_min_m=("elevation_m", "min"),
    elevation_max_m=("elevation_m", "max"),
    n_stations=("elevation_m", "size"),
)
df_sites = df_sites.sort_values("elevation_m")
df_sites["site_name"] = df_sites.index.map(SITE_NAMES)


# ===========================================================================
# 6. Write sites.geojson
# ===========================================================================
site_features = []
for site, row in df_sites.iterrows():
    site_features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(row.lon, 7), round(row.lat, 7)]},
        "properties": {
            "site": site,
            "site_name": row.site_name,
            "elevation_m": round(row.elevation_m, 1),
            "elevation_min_m": round(row.elevation_min_m, 1),
            "elevation_max_m": round(row.elevation_max_m, 1),
            "n_stations": int(row.n_stations),
        },
    })

sites_json = {"type": "FeatureCollection", "features": site_features}
(OUT / "sites.geojson").write_text(json.dumps(sites_json, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
print("wrote public/data/sites.geojson:", len(site_features), "features")
