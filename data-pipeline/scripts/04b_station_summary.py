"""Step 1.6: station summaries.

Builds public/data/station_summary.json (one record per sampling point, totals
across all five seasons, as in the Data contract in PLAN.md) and the same
records as processed/station_summary.csv, then prints the checks.

Uses the same rules as 04_site_summary.py, so the two files agree: May 2002 –
Oct 2004 only, CO2 traps for abundance, every dissected mosquito for infection,
station 200 dropped from bird counts, NOBI events kept, bird count file read
with keep_default_na=False. Infection is stored as counts, not percentages,
because station sample sizes are small.

Requires public/data/site_summary.json (04_site_summary.py) for the sum checks.
Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/04b_station_summary.py
"""

import json
from pathlib import Path

import pandas as pd

# file locations, built from where this script lives so it runs from any folder
PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent
BIO = PIPELINE / "raw" / "biocomplexity_2001_2004"
LOOKUP = PIPELINE / "species_lookup.csv"
SITES_GEOJSON = ROOT / "public" / "data" / "sites.geojson"
STATIONS_GEOJSON = ROOT / "public" / "data" / "stations.geojson"
SITE_SUMMARY = ROOT / "public" / "data" / "site_summary.json"
OUTPUT = ROOT / "public" / "data" / "station_summary.json"
OUTPUT_CSV = PIPELINE / "processed" / "station_summary.csv"

# show every column when printing, and keep wide tables on one line
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)


# ===========================================================================
# Settings (the same as 04_site_summary.py; see data_notes.md)
# ===========================================================================
# Stations use the whole window (all five seasons together): there is too little data at
# one station to split it by season.
START = pd.Timestamp("2002-05-01")
END = pd.Timestamp("2004-10-31")
BIRD_COUNT_STATIONS = [100, 300, 500, 700, 900]  # station 200 dropped

KEY = ["site", "station", "transect"]  # one sampling point
TOP_STATIONS = 3  # stations printed per site, ranked by Culex per trap night

# the fields of each record, in order (the Data contract in PLAN.md)
FIELDS = [
    "site", "station", "transect",
    "culex_per_trap_night", "trap_nights",
    "mosq_midgut_n", "mosq_midgut_infected",
    "mosq_salivary_n", "mosq_salivary_infected",
    "honeycreepers_per_count", "nonnative_birds_per_count", "bird_counts_n",
]


# a rate (e.g. Culex per trap night), or None (null) when there is nothing to divide by
def rate(value, n, digits):
    if n > 0:
        return round(value / n, digits)
    return None


# ===========================================================================
# 1. Species groups from the species lookup (Step 1.3)
# ===========================================================================
df_lookup = pd.read_csv(LOOKUP, keep_default_na=False)
canonical = dict(zip(df_lookup["code"], df_lookup["canonical_code"]))
species = df_lookup[df_lookup["canonical_code"] != ""].drop_duplicates("canonical_code")
honeycreeper_codes = set(species.loc[species["honeycreeper"] == "true", "canonical_code"])
nonnative_codes = set(species.loc[species["native"] == "false", "canonical_code"])


# ===========================================================================
# 2. Load the data and keep May 2002 – Oct 2004
# ===========================================================================
# Each file's dates are parsed with that file's own format (an unreadable date stops the
# script). The blood samples aren't needed: bird prevalence is only calculated per site.

# mosquito captures: CO2 traps only, for abundance
df_traps = pd.read_csv(BIO / "Biocomplexity_mosquito capture data.csv")
df_traps["when"] = pd.to_datetime(df_traps["date"], format="%m/%d/%Y")
df_traps = df_traps[df_traps["when"].between(START, END) & (df_traps["trap_type"] == "co2")]

# mosquito dissections: every trap type, for infection; dates come from date_collected
df_dissect = pd.read_csv(BIO / "Biocomplexity_mosquito avian malaria infection and parity data.csv")
df_dissect["when"] = pd.to_datetime(df_dissect["date_collected"], format="%Y-%m-%d")
df_dissect = df_dissect[df_dissect["when"].between(START, END)]

# bird counts: keep_default_na=False keeps guild "NA" as text; station 200 dropped
df_counts = pd.read_csv(BIO / "Biocomplexity_bird count data.csv", keep_default_na=False)
df_counts["when"] = pd.to_datetime(df_counts["obsvdate"], format="%m/%d/%Y")
df_counts = df_counts[df_counts["when"].between(START, END)
                      & df_counts["station"].isin(BIRD_COUNT_STATIONS)].copy()
df_counts["species"] = df_counts["alphacode"].map(canonical)

# every species code in the bird counts must be in the lookup, or it would go uncounted
missing_codes = set(df_counts["alphacode"]) - set(canonical)
assert not missing_codes, f"species codes missing from species_lookup.csv: {missing_codes}"

# the 405 sampling points, in the order of stations.geojson (Step 1.2)
station_features = json.loads(STATIONS_GEOJSON.read_text(encoding="utf-8"))["features"]
points = [(f["properties"]["site"], f["properties"]["station"], f["properties"]["transect"])
          for f in station_features]

# sites in order from lowest to highest, from sites.geojson (Step 1.2)
site_features = json.loads(SITES_GEOJSON.read_text(encoding="utf-8"))["features"]
site_features = sorted(site_features, key=lambda f: f["properties"]["elevation_m"])
sites = [f["properties"]["site"] for f in site_features]


# ===========================================================================
# 3. Totals per sampling point
# ===========================================================================
# Each total is a groupby on site + station + transect, giving one value per point.
# A point missing from a total had no samples of that kind, and gets 0 below.

# Culex caught and CO2 trap nights (one row = one trap night)
culex = df_traps.groupby(KEY)["culex"].sum()
trap_nights = df_traps.groupby(KEY).size()

# mosquitoes examined and positive for each test; a blank result means that organ wasn't
# examined, so those rows are left out of that test
midgut = df_dissect[df_dissect["midgut_infection"].notna()]
salivary = df_dissect[df_dissect["salivary_infection"].notna()]
midgut_n = midgut.groupby(KEY).size()
midgut_pos = (midgut["midgut_infection"] == "yes").groupby([midgut[k] for k in KEY]).sum()
salivary_n = salivary.groupby(KEY).size()
salivary_pos = (salivary["salivary_infection"] == "yes").groupby([salivary[k] for k in KEY]).sum()

# counting events (one per station + transect + date, NOBI included) and honeycreeper and
# non-native detections (NOBI left out, since it isn't a bird)
events = df_counts.drop_duplicates(KEY + ["obsvdate"]).groupby(KEY).size()
detections = df_counts[df_counts["alphacode"] != "NOBI"]
honey_detections = detections[detections["species"].isin(honeycreeper_codes)].groupby(KEY).size()
nonnative_detections = detections[detections["species"].isin(nonnative_codes)].groupby(KEY).size()

# every point that has data must be one of the 405 points in stations.geojson
points_with_data = set(trap_nights.index) | set(midgut_n.index) | set(events.index)
unmatched = points_with_data - set(points)
assert not unmatched, f"data at sampling points missing from stations.geojson: {sorted(unmatched)}"


# ===========================================================================
# 4. Turn the totals into one record per point
# ===========================================================================
# .get(point, 0) gives 0 for a point with no samples of that kind. Infected counts are null
# when nothing was examined; rates are null when there's nothing to divide by.
records = []
for point in points:
    site, station, transect = point
    n_nights = int(trap_nights.get(point, 0))
    n_midgut = int(midgut_n.get(point, 0))
    n_salivary = int(salivary_n.get(point, 0))
    n_events = int(events.get(point, 0))
    records.append({
        "site": site, "station": station, "transect": transect,
        "culex_per_trap_night": rate(int(culex.get(point, 0)), n_nights, 3),
        "trap_nights": n_nights,
        "mosq_midgut_n": n_midgut,
        "mosq_midgut_infected": int(midgut_pos.get(point, 0)) if n_midgut else None,
        "mosq_salivary_n": n_salivary,
        "mosq_salivary_infected": int(salivary_pos.get(point, 0)) if n_salivary else None,
        "honeycreepers_per_count": rate(int(honey_detections.get(point, 0)), n_events, 2),
        "nonnative_birds_per_count": rate(int(nonnative_detections.get(point, 0)), n_events, 2),
        "bird_counts_n": n_events,
    })


# ===========================================================================
# 5. Check the records against the Data contract
# ===========================================================================
# 405 records with exactly the contract's fields; each null exactly when its sample is 0;
# no bird counts at stations outside BIRD_COUNT_STATIONS
assert len(records) == len(points) == 405, f"expected 405 records, got {len(records)}"
for r in records:
    assert list(r) == FIELDS, f"field set differs for {r}"
    assert (r["culex_per_trap_night"] is None) == (r["trap_nights"] == 0), r
    assert (r["mosq_midgut_infected"] is None) == (r["mosq_midgut_n"] == 0), r
    assert (r["mosq_salivary_infected"] is None) == (r["mosq_salivary_n"] == 0), r
    assert (r["honeycreepers_per_count"] is None) == (r["bird_counts_n"] == 0), r
    assert (r["nonnative_birds_per_count"] is None) == (r["bird_counts_n"] == 0), r
    if r["station"] not in BIRD_COUNT_STATIONS:
        assert r["bird_counts_n"] == 0, f"bird counts at station {r['station']}: {r}"


# ===========================================================================
# 6. Write station_summary.json and the CSV copy
# ===========================================================================
OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(records)} records)")

# Int64 keeps the infected counts whole numbers in the CSV (blank where untested)
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df_stations = pd.DataFrame(records).astype({"mosq_midgut_infected": "Int64", "mosq_salivary_infected": "Int64"})
df_stations.to_csv(OUTPUT_CSV, index=False)
print(f"wrote {OUTPUT_CSV.relative_to(ROOT)} ({len(records)} rows)")


# ===========================================================================
# 7. Print the results and checks
# ===========================================================================
print("\nSTATION SUMMARY CHECK")
print(f"{len(records)} records, one per sampling point; totals across all five seasons "
      "(May 2002 – Oct 2004).")
print("Contract checks: pass (exact field set; _infected null exactly when its n = 0; "
      "per-count values null exactly when there are no counts; no bird counts at even stations)")
print(f"Stations with no mosquitoes examined (salivary): "
      f"{(df_stations['mosq_salivary_n'] == 0).sum()} of {len(records)}")
print(f"Stations with bird counts: {(df_stations['bird_counts_n'] > 0).sum()} of {len(records)}")

# sum checks: each site's 45 stations must add up to the site's `all` value in
# site_summary.json, which shows the two scripts used the same rows
site_all = {r["site"]: r for r in json.loads(SITE_SUMMARY.read_text(encoding="utf-8"))
            if r["period"] == "all"}
# (station field, site field, label)
compared = [("trap_nights", "mosquito_trap_nights", "CO2 trap nights"),
            ("mosq_midgut_n", "mosq_midgut_n", "midgut examined"),
            ("mosq_salivary_n", "mosq_salivary_n", "salivary examined"),
            ("bird_counts_n", "bird_counts_n", "counting events")]
sum_rows = []
sums_ok = True
for site in sites:
    row = {"site": site}
    for station_field, site_field, label in compared:
        station_total = df_stations.loc[df_stations["site"] == site, station_field].sum()
        site_value = site_all[site][site_field]
        sums_ok = sums_ok and station_total == site_value
        row[label] = f"{station_total} / {site_value}" + ("" if station_total == site_value else " FAIL")
    sum_rows.append(row)
print("\nSum checks against site_summary.json `all` (sum over the site's 45 stations / "
      "site value; must be equal):")
print(pd.DataFrame(sum_rows).to_string(index=False))

# the stations with the most Culex per trap night at each site
top_rows = []
for site in sites:
    site_stations = df_stations[(df_stations["site"] == site) & df_stations["culex_per_trap_night"].notna()]
    ranked = site_stations.sort_values("culex_per_trap_night", ascending=False, kind="stable").head(TOP_STATIONS)
    for rank, r in enumerate(ranked.itertuples(index=False), start=1):
        top_rows.append({"site": site, "rank": rank, "station": r.station, "transect": r.transect,
                         "culex_per_trap_night": r.culex_per_trap_night, "trap_nights": r.trap_nights})
print(f"\nTop {TOP_STATIONS} stations by Culex per trap night, per site (low to high elevation):")
print(pd.DataFrame(top_rows).to_string(index=False))

print(f"\nsum checks: {'pass' if sums_ok else 'FAIL'}")
