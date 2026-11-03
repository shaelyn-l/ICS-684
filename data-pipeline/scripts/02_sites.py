"""Step 1.2: map-ready station and site points.

Reads the Biocomplexity sampling coordinates (already WGS84 decimal degrees, so
no reprojection), the mosquito capture and bird count files (to flag which
points were used for each), and the two XML metadata files (for site names).

Writes:
  public/data/stations.geojson   one point per site + station + transect
  public/data/sites.geojson      one point per site at the mean of its stations
  reports/station200_check.md    the bird count rows recorded at station 200

Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/02_sites.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

PIPELINE = Path(__file__).resolve().parent.parent
RAW = PIPELINE / "raw"
BIO = RAW / "biocomplexity_2001_2004"
OUT = PIPELINE.parent / "public" / "data"
REPORTS = PIPELINE / "reports"

COORDS_CSV = BIO / "Biocomplexity_sampling station spatial coordinates.csv"
MOSQUITO_CSV = BIO / "Biocomplexity_mosquito capture data.csv"
BIRD_COUNT_CSV = BIO / "Biocomplexity_bird count data.csv"
METADATA_XML = [BIO / "BiocomplexityDR.xml",
                RAW / "bird_malaria_2001_2005"
                / "Island of Hawaii forest bird malaria infection data 2001-2005 revised.xml"]

KEY = ["site", "station", "transect"]
# Bird counts were done at these stations only (per the Biocomplexity metadata). The 25 rows
# at station 200 are dropped from bird counts; see reports/data_notes.md.
BIRD_COUNT_STATIONS = {100, 300, 500, 700, 900}


def site_names_from_metadata():
    """Map site code -> description from the site/LOCATION attribute domain in the XML."""
    names = {}
    for path in METADATA_XML:
        if not path.exists():
            continue
        for attr in ET.parse(path).getroot().iter("attr"):
            label = (attr.findtext("attrlabl") or "").strip().lower()
            if label not in ("site", "location"):
                continue
            for domain in attr.iter("edom"):
                code = (domain.findtext("edomv") or "").strip()
                desc = " ".join((domain.findtext("edomvd") or "").split())
                if code and desc:
                    names.setdefault(code, desc)
    return names


def point(lon, lat, props):
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 7), round(lat, 7)]},
            "properties": props}


def write_geojson(path, features):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path.relative_to(PIPELINE.parent)} ({len(features)} features)")


def build_stations(coords, mosquito, birds):
    trap_keys = set(mosquito[KEY].drop_duplicates().itertuples(index=False, name=None))
    counted = birds[birds["station"].isin(BIRD_COUNT_STATIONS)]
    count_keys = set(counted[KEY].drop_duplicates().itertuples(index=False, name=None))
    features = []
    for r in coords.itertuples(index=False):
        key = (r.site, r.station, r.transect)
        features.append(point(r.x_long, r.y_lat, {
            "site": r.site,
            "station": int(r.station),
            "transect": int(r.transect),
            "elevation_m": float(r.elevation_m),
            "has_mosquito_traps": key in trap_keys,
            "has_bird_counts": key in count_keys,
        }))
    missing = (trap_keys | count_keys) - set(coords[KEY].itertuples(index=False, name=None))
    if missing:
        print(f"WARNING: {len(missing)} site/station/transect combos in the data have no coordinates: "
              f"{sorted(missing)}")
    return features


def build_sites(coords, names):
    grouped = coords.groupby("site").agg(
        lon=("x_long", "mean"), lat=("y_lat", "mean"),
        elevation_m=("elevation_m", "mean"),
        elevation_min_m=("elevation_m", "min"), elevation_max_m=("elevation_m", "max"),
        n_stations=("elevation_m", "size"),
    ).sort_values("elevation_m")
    features = [point(r.lon, r.lat, {
        "site": site,
        "site_name": names.get(site),
        "elevation_m": round(r.elevation_m, 1),
        "elevation_min_m": round(r.elevation_min_m, 1),
        "elevation_max_m": round(r.elevation_max_m, 1),
        "n_stations": int(r.n_stations),
    }) for site, r in grouped.iterrows()]
    return features, grouped


def station200_report(birds):
    """Describe bird count rows at station 200 and whether they could be a mistyped neighbor."""
    rows = birds[birds["station"] == 200]
    events = (rows.groupby(["site", "transect", "obsvdate", "obscode", "timestart"])
              .size().reset_index(name="detections"))

    # For each station-200 event, which stations on the same site/transect/date have counts,
    # and when each was started (counts walk the transect in order, so times show the sequence)?
    starts = birds.groupby(["site", "transect", "obsvdate", "station"])["timestart"].min()
    events["stations counted that day on this transect (start time)"] = [
        ", ".join(f"{st} ({t})" for st, t in starts[(e.site, e.transect, e.obsvdate)].items())
        for e in events.itertuples(index=False)]

    def table(df):
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(v) for v in row) + " |"
                  for row in df.itertuples(index=False)]
        return "\n".join(lines)

    species = rows["alphacode"].value_counts().reset_index()
    species.columns = ["alphacode", "rows"]
    other_stations = sorted(set(birds["station"].astype(int)) - {200})

    lines = [
        "# Bird count rows at station 200", "",
        "Generated by `scripts/02_sites.py`. Nothing has been changed or dropped.", "",
        f"- Rows at station 200: {len(rows)} of {len(birds):,} bird count rows.",
        f"- Other stations in the bird count file: {', '.join(map(str, other_stations))}.",
        "- The Biocomplexity metadata says counts were done at 25 stations 200 m apart "
        "(5 per transect), which matches the odd stations only.",
        f"- Sites: {', '.join(sorted(rows['site'].unique()))}. "
        f"Transects: {', '.join(map(str, sorted(rows['transect'].unique())))}. "
        f"Dates: {', '.join(sorted(rows['obsvdate'].unique(), key=pd.to_datetime))}.", "",
        "## Counting events at station 200", "",
        "One event = site + transect + date + observer + start time. The last column lists every "
        "station with counts on the same site, transect and date, with its earliest start time "
        "(9999 = not recorded). If one of the usual stations is missing that day, station 200 may "
        "be a mistyped station number; the start times show where it fell in the walk.", "",
        table(events), "",
        "## Species recorded at station 200", "",
        table(species), "",
        "## Decision", "",
        "All 25 station-200 rows are dropped from bird count summaries; station 200 points have "
        "`has_bird_counts = false`. The raw file is unchanged. See `reports/data_notes.md`.", "",
    ]
    path = REPORTS / "station200_check.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path.relative_to(PIPELINE)}")


def main():
    coords = pd.read_csv(COORDS_CSV)
    mosquito = pd.read_csv(MOSQUITO_CSV)
    birds = pd.read_csv(BIRD_COUNT_CSV)

    # Sanity check that coordinates really are WGS84 degrees on Hawaiʻi Island.
    assert coords["x_long"].between(-156.1, -154.8).all(), "x_long outside Hawaiʻi Island"
    assert coords["y_lat"].between(18.9, 20.3).all(), "y_lat outside Hawaiʻi Island"
    assert not coords.duplicated(KEY).any(), "duplicate site/station/transect in coordinates"

    stations = build_stations(coords, mosquito, birds)
    write_geojson(OUT / "stations.geojson", stations)

    names = site_names_from_metadata()
    sites, grouped = build_sites(coords, names)
    write_geojson(OUT / "sites.geojson", sites)

    station200_report(birds)

    unexpected = sorted({(f["properties"]["site"], f["properties"]["station"])
                         for f in stations if f["properties"]["has_bird_counts"]
                         and f["properties"]["station"] not in BIRD_COUNT_STATIONS})
    print(f"\nhas_bird_counts at stations outside {sorted(BIRD_COUNT_STATIONS)}: "
          f"{unexpected or 'none'}")
    print(f"stations with mosquito traps: {sum(f['properties']['has_mosquito_traps'] for f in stations)}"
          f" of {len(stations)}; with bird counts: "
          f"{sum(f['properties']['has_bird_counts'] for f in stations)}")

    print("\nSites by mean elevation:")
    table = grouped.reset_index()[["site", "elevation_m", "elevation_min_m", "elevation_max_m",
                                   "n_stations"]].round(1)
    table["site_name"] = table["site"].map(names).fillna("(not found)")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
