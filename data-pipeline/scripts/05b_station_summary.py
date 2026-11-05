"""Step 1.6: station summaries.

Builds public/data/station_summary.json (one record per sampling point, totals
across all five seasons, as in the Data contract in PLAN.md) and
reports/station_summary_check.md.

Reuses the loading and rules from 05_site_summary.py, so the two files always
agree: May 2002 – Oct 2004 only, CO2 traps for abundance, every dissected
mosquito for infection, station 200 dropped from bird counts, NOBI events kept,
bird count file read with keep_default_na=False. Infection is stored as counts,
not percentages, because station sample sizes are small.

Requires public/data/site_summary.json (Step 1.5) for the sum checks.
Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/05b_station_summary.py
"""

import importlib.util
import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

# 05_site_summary.py can't be imported by name (it starts with a digit).
_spec = importlib.util.spec_from_file_location("site_summary", SCRIPTS / "05_site_summary.py")
site_summary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_summary)

PIPELINE, ROOT = site_summary.PIPELINE, site_summary.ROOT
STATIONS_GEOJSON = ROOT / "public" / "data" / "stations.geojson"
SITE_SUMMARY = site_summary.OUTPUT
OUTPUT = ROOT / "public" / "data" / "station_summary.json"
REPORT = PIPELINE / "reports" / "station_summary_check.md"

KEY = ["site", "station", "transect"]
FIELDS = [
    "site", "station", "transect",
    "culex_per_trap_night", "trap_nights",
    "mosq_midgut_n", "mosq_midgut_infected",
    "mosq_salivary_n", "mosq_salivary_infected",
    "honeycreepers_per_count", "nonnative_birds_per_count", "bird_counts_n",
]
TOP_STATIONS = 3  # stations listed per site in the check report


def by_key(df, agg):
    """Group by sampling point and return {(site, station, transect): value}."""
    return agg(df.groupby(KEY)).to_dict()


def summarize(traps, dissected, counts, honeycreepers, nonnative, points):
    culex = by_key(traps, lambda g: g["culex"].sum())
    nights = by_key(traps, lambda g: g.size())

    midgut = dissected.dropna(subset=["midgut_infection"])
    salivary = dissected.dropna(subset=["salivary_infection"])
    midgut_n = by_key(midgut, lambda g: g.size())
    midgut_pos = by_key(midgut, lambda g: g["midgut_infection"].apply(lambda s: (s == "yes").sum()))
    salivary_n = by_key(salivary, lambda g: g.size())
    salivary_pos = by_key(salivary, lambda g: g["salivary_infection"].apply(lambda s: (s == "yes").sum()))

    events = by_key(counts.drop_duplicates(KEY + ["obsvdate"]), lambda g: g.size())
    detections = counts[counts["alphacode"] != "NOBI"]
    honey = by_key(detections[detections["species"].isin(honeycreepers)], lambda g: g.size())
    nonnat = by_key(detections[detections["species"].isin(nonnative)], lambda g: g.size())

    unmatched = (set(nights) | set(midgut_n) | set(events)) - set(points)
    records = []
    for key in points:
        site, station, transect = key
        n_nights, n_mid, n_sal, n_events = (nights.get(key, 0), midgut_n.get(key, 0),
                                            salivary_n.get(key, 0), events.get(key, 0))
        records.append({
            "site": site, "station": station, "transect": transect,
            "culex_per_trap_night": site_summary.rate(culex.get(key, 0), n_nights, 3),
            "trap_nights": int(n_nights),
            "mosq_midgut_n": int(n_mid),
            "mosq_midgut_infected": int(midgut_pos.get(key, 0)) if n_mid else None,
            "mosq_salivary_n": int(n_sal),
            "mosq_salivary_infected": int(salivary_pos.get(key, 0)) if n_sal else None,
            "honeycreepers_per_count": site_summary.rate(honey.get(key, 0), n_events, 2),
            "nonnative_birds_per_count": site_summary.rate(nonnat.get(key, 0), n_events, 2),
            "bird_counts_n": int(n_events),
        })
    return records, unmatched


def check_contract(records, n_points):
    assert len(records) == n_points == 405, f"expected 405 records, got {len(records)}"
    for r in records:
        assert list(r) == FIELDS, f"field set differs for {r}"
        assert (r["culex_per_trap_night"] is None) == (r["trap_nights"] == 0), r
        assert (r["mosq_midgut_infected"] is None) == (r["mosq_midgut_n"] == 0), r
        assert (r["mosq_salivary_infected"] is None) == (r["mosq_salivary_n"] == 0), r
        for f in ("honeycreepers_per_count", "nonnative_birds_per_count"):
            assert (r[f] is None) == (r["bird_counts_n"] == 0), r
        if r["station"] not in site_summary.BIRD_COUNT_STATIONS:
            assert r["bird_counts_n"] == 0, f"bird counts at station {r['station']}: {r}"


def sum_checks(records, sites):
    site_all = {r["site"]: r for r in json.loads(SITE_SUMMARY.read_text(encoding="utf-8"))
                if r["period"] == "all"}
    pairs = [("trap_nights", "mosquito_trap_nights", "CO2 trap nights"),
             ("mosq_midgut_n", "mosq_midgut_n", "Mosquitoes examined (midgut)"),
             ("mosq_salivary_n", "mosq_salivary_n", "Mosquitoes examined (salivary)"),
             ("bird_counts_n", "bird_counts_n", "Counting events")]
    rows, ok = [], True
    for site in sites:
        row = [site]
        for station_field, site_field, _ in pairs:
            total = sum(r[station_field] for r in records if r["site"] == site)
            expected = site_all[site][site_field]
            ok &= total == expected
            row.append(f"{total} / {expected}" + ("" if total == expected else " **FAIL**"))
        rows.append(row)
    headers = ["Site"] + [f"{label} (stations / site `all`)" for *_, label in pairs]
    return site_summary.md_table(headers, rows), ok


def top_stations(records, sites):
    rows = []
    for site in sites:
        ranked = sorted((r for r in records if r["site"] == site and r["culex_per_trap_night"] is not None),
                        key=lambda r: r["culex_per_trap_night"], reverse=True)[:TOP_STATIONS]
        for i, r in enumerate(ranked, 1):
            rows.append([site if i == 1 else "", i, r["station"], r["transect"],
                         r["culex_per_trap_night"], r["trap_nights"]])
    return site_summary.md_table(["Site", "Rank", "Station", "Transect", "Culex / trap night",
                                  "CO2 trap nights"], rows)


def main():
    features = json.loads(STATIONS_GEOJSON.read_text(encoding="utf-8"))["features"]
    points = [tuple(f["properties"][k] for k in KEY) for f in features]
    site_features = json.loads(site_summary.SITES_GEOJSON.read_text(encoding="utf-8"))["features"]
    sites = [f["properties"]["site"]
             for f in sorted(site_features, key=lambda f: f["properties"]["elevation_m"])]

    traps, dissected, _blood, counts, honeycreepers, nonnative = site_summary.load()
    records, unmatched = summarize(traps, dissected, counts, honeycreepers, nonnative, points)
    check_contract(records, len(points))
    assert not unmatched, f"data at sampling points missing from stations.geojson: {sorted(unmatched)}"

    OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(records)} records)")

    sums_table, sums_ok = sum_checks(records, sites)
    no_dissections = sum(r["mosq_salivary_n"] == 0 for r in records)
    with_counts = sum(r["bird_counts_n"] > 0 for r in records)
    lines = [
        "# Station summary check", "",
        "Generated by `scripts/05b_station_summary.py`. Output: `public/data/station_summary.json` "
        f"({len(records)} records, one per sampling point). Totals across all five seasons "
        "(May 2002 – Oct 2004).", "",
        "- Contract checks: pass (exact field set; `_infected` null exactly when its n = 0; "
        "per-count values null exactly when there are no counts; no bird counts at even stations).",
        f"- Sum checks: {'pass' if sums_ok else 'FAIL'}.",
        f"- Stations with no mosquitoes examined (salivary): {no_dissections} of {len(records)}.",
        f"- Stations with bird counts: {with_counts} of {len(records)}.", "",
        "## 1. Sum checks against `site_summary.json` (`all`)", "",
        "Each cell is the sum over the site's 45 stations / the site's `all` value. They must be equal.", "",
        sums_table, "",
        f"## 2. Top {TOP_STATIONS} stations by *Culex* per trap night, per site (low to high elevation)", "",
        top_stations(records, sites), "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(PIPELINE)}")
    print(f"sum checks: {'pass' if sums_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
