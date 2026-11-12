"""Step 1.5: site summaries.

Builds public/data/site_summary.json (one record per site per period, as in the
Data contract in PLAN.md) and the same records as processed/site_summary.csv,
then prints the checks. Follows the decisions in reports/data_notes.md:

  - Hawaiian seasons, five full seasons only (May 2002 – Oct 2004), plus the
    combined periods all / dry / wet
  - mosquito abundance from CO2 traps only; infection from every dissected mosquito
  - birds counted once per site-period (band number + species; NB rows one each),
    combined as any P -> positive, else any N -> negative, all U -> excluded
  - bird counts: station 200 dropped, NOBI events kept in the denominator
  - percentages null below 20 samples; abundance null only when n = 0

Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/04_site_summary.py
"""

import json
from pathlib import Path

import pandas as pd

# file locations, built from where this script lives so it runs from any folder
PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent
BIO = PIPELINE / "raw" / "biocomplexity_2001_2004"
BLOOD_CSV = PIPELINE / "raw" / "bird_malaria_2001_2005" / "Banding Diagnostics Data Final_revised.csv"
LOOKUP = PIPELINE / "species_lookup.csv"
SITES_GEOJSON = ROOT / "public" / "data" / "sites.geojson"
OUTPUT = ROOT / "public" / "data" / "site_summary.json"
OUTPUT_CSV = PIPELINE / "processed" / "site_summary.csv"

# show every column when printing, and don't cut off long text
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)


# ===========================================================================
# Settings (decided in Step 1.4; see data_notes.md)
# ===========================================================================
# Time window: five full Hawaiian seasons. The partial seasons Jan–Apr 2002 and
# Nov–Dec 2004 are left out.
START = pd.Timestamp("2002-05-01")
END = pd.Timestamp("2004-10-31")
SEASONS = ["2002-dry", "2002-wet", "2003-dry", "2003-wet", "2004-dry"]

# each period is a list of the seasons it combines
PERIODS = {
    "2002-dry": ["2002-dry"],
    "2002-wet": ["2002-wet"],
    "2003-dry": ["2003-dry"],
    "2003-wet": ["2003-wet"],
    "2004-dry": ["2004-dry"],
    "all": SEASONS,
    "dry": ["2002-dry", "2003-dry", "2004-dry"],
    "wet": ["2002-wet", "2003-wet"],
}

MIN_N_PCT = 20  # percentages are null below this sample size
BIRD_COUNT_STATIONS = [100, 300, 500, 700, 900]  # station 200 dropped; see data_notes.md

# the fields of each record, in order (the Data contract in PLAN.md)
FIELDS = [
    "site", "period",
    "mosquito_per_trap_night", "mosquito_trap_nights",
    "mosq_midgut_pct", "mosq_midgut_n",
    "mosq_salivary_pct", "mosq_salivary_n",
    "bird_prevalence_pct", "bird_sampled_n",
    "honeycreeper_prevalence_pct", "honeycreeper_sampled_n",
    "honeycreepers_per_count", "nonnative_birds_per_count", "bird_counts_n",
]
# each percentage and abundance field, with the sample-size field it depends on
PCT_FIELDS = {"mosq_midgut_pct": "mosq_midgut_n", "mosq_salivary_pct": "mosq_salivary_n",
              "bird_prevalence_pct": "bird_sampled_n",
              "honeycreeper_prevalence_pct": "honeycreeper_sampled_n"}
ABUNDANCE_FIELDS = {"mosquito_per_trap_night": "mosquito_trap_nights",
                    "honeycreepers_per_count": "bird_counts_n",
                    "nonnative_birds_per_count": "bird_counts_n"}

# What data_notes.md "Known gaps" says: the periods where each percentage is expected to
# have a value (an empty set means blank in every period). Checked at the end.
KNOWN_GAPS = {
    ("SOL", "mosq_salivary_pct"): set(),
    ("SOL", "mosq_midgut_pct"): set(),
    ("CJR", "mosq_salivary_pct"): {"2004-dry", "dry", "all"},
    ("CJR", "mosq_midgut_pct"): {"2004-dry", "dry", "all"},
    ("WAI", "honeycreeper_prevalence_pct"): set(),
}


# ===========================================================================
# Helper functions
# ===========================================================================

# Hawaiian season of a date: dry May–Oct, wet Nov–Apr. A wet season is labeled by the year
# it starts, so 2002-wet = Nov 2002 – Apr 2003 (January–April belong to last year's wet).
def season(date):
    if 5 <= date.month <= 10:
        return f"{date.year}-dry"
    if date.month >= 11:
        return f"{date.year}-wet"
    return f"{date.year - 1}-wet"


# a percentage rounded to 1 decimal, or None (null) when the sample is under MIN_N_PCT
def pct(positives, n):
    if n >= MIN_N_PCT:
        return round(positives / n * 100, 1)
    return None


# a rate (e.g. Culex per trap night), or None when there is nothing to divide by
def rate(value, n, digits):
    if n > 0:
        return round(value / n, digits)
    return None


# one bird's combined result within a period, from all its samples: positive if any sample
# is P, otherwise negative if any is N; a bird with only U (unknown) results is left out
def bird_status(statuses):
    statuses = set(statuses)
    if "P" in statuses:
        return "P"
    if "N" in statuses:
        return "N"
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
# 2. Load the data, keep May 2002 – Oct 2004, and label each row with its season
# ===========================================================================
# Each file's dates are parsed with that file's own format (an unreadable date stops the
# script). Rows outside the five seasons are dropped.

# mosquito captures: CO2 traps only, for abundance
df_traps = pd.read_csv(BIO / "Biocomplexity_mosquito capture data.csv")
df_traps["when"] = pd.to_datetime(df_traps["date"], format="%m/%d/%Y")
df_traps = df_traps[df_traps["when"].between(START, END)].copy()
df_traps["season"] = df_traps["when"].map(season)
df_traps = df_traps[df_traps["trap_type"] == "co2"]

# mosquito dissections: every trap type, for infection; seasons come from date_collected
df_dissect = pd.read_csv(BIO / "Biocomplexity_mosquito avian malaria infection and parity data.csv")
df_dissect["when"] = pd.to_datetime(df_dissect["date_collected"], format="%Y-%m-%d")
df_dissect = df_dissect[df_dissect["when"].between(START, END)].copy()
df_dissect["season"] = df_dissect["when"].map(season)

# bird blood samples: keep_default_na=False keeps "NB" and other codes as text
df_blood = pd.read_csv(BLOOD_CSV, keep_default_na=False)
df_blood["when"] = pd.to_datetime(df_blood["DATE"], format="%m/%d/%Y")
df_blood = df_blood[df_blood["when"].between(START, END)].copy()
df_blood["season"] = df_blood["when"].map(season)
df_blood = df_blood.rename(columns={"LOCATION": "site"})
df_blood["species"] = df_blood["SPECIES"].map(canonical)
# a bird is its band number; unbanded ("NB") rows can't be matched, so each gets its own id
df_blood["bird"] = df_blood["BANDNUMBER"].where(df_blood["BANDNUMBER"] != "NB",
                                                "NB-" + df_blood.index.astype(str))

# bird counts: keep_default_na=False keeps guild "NA" as text; station 200 dropped
df_counts = pd.read_csv(BIO / "Biocomplexity_bird count data.csv", keep_default_na=False)
df_counts["when"] = pd.to_datetime(df_counts["obsvdate"], format="%m/%d/%Y")
df_counts = df_counts[df_counts["when"].between(START, END)].copy()
df_counts["season"] = df_counts["when"].map(season)
df_counts = df_counts[df_counts["station"].isin(BIRD_COUNT_STATIONS)]
df_counts["species"] = df_counts["alphacode"].map(canonical)

# every species code in the bird data must be in the lookup, or it would go uncounted
missing_codes = (set(df_blood["SPECIES"]) | set(df_counts["alphacode"])) - set(canonical)
assert not missing_codes, f"species codes missing from species_lookup.csv: {missing_codes}"

# sites in order from lowest to highest, from sites.geojson (Step 1.2)
site_features = json.loads(SITES_GEOJSON.read_text(encoding="utf-8"))["features"]
site_features = sorted(site_features, key=lambda f: f["properties"]["elevation_m"])
sites = [f["properties"]["site"] for f in site_features]


# ===========================================================================
# 3. Raw totals for every site and period
# ===========================================================================
# For each site and period, keep the rows of that site in the period's seasons, then count:
# Culex caught and trap nights; mosquitoes examined and positive for each test; birds
# sampled and positive (each bird once, combined with bird_status); counting events
# (site + station + transect + date, NOBI included); and honeycreeper and non-native
# detections (NOBI excluded, since it isn't a bird).
totals = []
for site in sites:
    for period, period_seasons in PERIODS.items():
        traps = df_traps[(df_traps["site"] == site) & df_traps["season"].isin(period_seasons)]
        dissect = df_dissect[(df_dissect["site"] == site) & df_dissect["season"].isin(period_seasons)]
        blood = df_blood[(df_blood["site"] == site) & df_blood["season"].isin(period_seasons)]
        counts = df_counts[(df_counts["site"] == site) & df_counts["season"].isin(period_seasons)]

        # a blank infection result means that organ wasn't examined
        midgut = dissect["midgut_infection"].dropna()
        salivary = dissect["salivary_infection"].dropna()

        birds = blood.groupby(["bird", "species"])["INFECTION_STATUS"].apply(bird_status)
        birds = birds.dropna().reset_index(name="status")
        honeycreepers = birds[birds["species"].isin(honeycreeper_codes)]

        events = counts.drop_duplicates(["station", "transect", "obsvdate"])
        detections = counts[counts["alphacode"] != "NOBI"]

        totals.append({
            "site": site, "period": period,
            "culex": int(traps["culex"].sum()), "trap_nights": len(traps),
            "midgut_n": len(midgut), "midgut_pos": int((midgut == "yes").sum()),
            "salivary_n": len(salivary), "salivary_pos": int((salivary == "yes").sum()),
            "birds_n": len(birds), "birds_pos": int((birds["status"] == "P").sum()),
            "honey_n": len(honeycreepers), "honey_pos": int((honeycreepers["status"] == "P").sum()),
            "events": len(events),
            "honey_detections": int(detections["species"].isin(honeycreeper_codes).sum()),
            "nonnative_detections": int(detections["species"].isin(nonnative_codes).sum()),
        })
df_totals = pd.DataFrame(totals)


# ===========================================================================
# 4. Turn the totals into the records the app uses
# ===========================================================================
# rates are rounded to 3 decimals (Culex) or 2 (birds); percentages to 1 decimal
records = []
for row in df_totals.itertuples(index=False):
    records.append({
        "site": row.site, "period": row.period,
        "mosquito_per_trap_night": rate(row.culex, row.trap_nights, 3),
        "mosquito_trap_nights": row.trap_nights,
        "mosq_midgut_pct": pct(row.midgut_pos, row.midgut_n), "mosq_midgut_n": row.midgut_n,
        "mosq_salivary_pct": pct(row.salivary_pos, row.salivary_n), "mosq_salivary_n": row.salivary_n,
        "bird_prevalence_pct": pct(row.birds_pos, row.birds_n), "bird_sampled_n": row.birds_n,
        "honeycreeper_prevalence_pct": pct(row.honey_pos, row.honey_n),
        "honeycreeper_sampled_n": row.honey_n,
        "honeycreepers_per_count": rate(row.honey_detections, row.events, 2),
        "nonnative_birds_per_count": rate(row.nonnative_detections, row.events, 2),
        "bird_counts_n": row.events,
    })


# ===========================================================================
# 5. Check the records against the Data contract
# ===========================================================================
# 9 sites x 8 periods; every record has exactly the contract's fields in order; each
# percentage is null exactly when its sample is under 20; each rate is null exactly when
# its sample is 0
assert len(records) == len(sites) * len(PERIODS), f"expected 72 records, got {len(records)}"
for r in records:
    assert list(r) == FIELDS, f"field set differs for {r['site']} {r['period']}"
    for pct_field, n_field in PCT_FIELDS.items():
        assert (r[pct_field] is None) == (r[n_field] < MIN_N_PCT), f"{pct_field} null rule broken: {r}"
    for rate_field, n_field in ABUNDANCE_FIELDS.items():
        assert (r[rate_field] is None) == (r[n_field] == 0), f"{rate_field} null rule broken: {r}"


# ===========================================================================
# 6. Write site_summary.json and the CSV copy
# ===========================================================================
OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(records)} records)")
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(records).to_csv(OUTPUT_CSV, index=False)
print(f"wrote {OUTPUT_CSV.relative_to(ROOT)} ({len(records)} rows)")


# ===========================================================================
# 7. Print the results and checks
# ===========================================================================
print("\nSITE SUMMARY CHECK")
print(f"{len(records)} records: {len(sites)} sites x {len(PERIODS)} periods. "
      "Data used: May 2002 – Oct 2004 (five full Hawaiian seasons).")
print(f"Contract checks: pass (exact field set, percentages null exactly when n < {MIN_N_PCT}, "
      "abundance null exactly when n = 0)")

# raw totals and final values for the `all` period
print("\nPer-site raw totals for `all` (low to high elevation; detections exclude NOBI):")
all_totals = df_totals[df_totals["period"] == "all"].set_index("site").loc[sites]
print(all_totals.drop(columns="period").to_string())

print("\nValues in site_summary.json for `all`:")
all_records = pd.DataFrame([r for r in records if r["period"] == "all"]).set_index("site")
print(all_records[["mosquito_per_trap_night", "mosq_salivary_pct", "bird_prevalence_pct",
                   "honeycreeper_prevalence_pct", "honeycreepers_per_count",
                   "nonnative_birds_per_count"]].to_string())

# sum checks: sample sizes that simply add up must match across periods (the five seasons,
# and dry + wet, must each equal `all`)
sum_rows = []
sums_ok = True
for column, label in [("trap_nights", "CO2 trap nights"), ("midgut_n", "Mosquitoes examined (midgut)"),
                      ("salivary_n", "Mosquitoes examined (salivary)"), ("events", "Counting events")]:
    by_period = df_totals.pivot(index="site", columns="period", values=column)
    seasons_ok = (by_period[SEASONS].sum(axis=1) == by_period["all"]).all()
    halves_ok = (by_period["dry"] + by_period["wet"] == by_period["all"]).all()
    sums_ok = sums_ok and seasons_ok and halves_ok
    sum_rows.append({"measure": label, "5 seasons = all": "pass" if seasons_ok else "FAIL",
                     "dry + wet = all": "pass" if halves_ok else "FAIL"})
print("\nSum checks (bird sample sizes are left out: a bird sampled in two seasons counts "
      "once in each season but once in `all`):")
print(pd.DataFrame(sum_rows).to_string(index=False))

# percentages set to null because the sample was under 20
print(f"\nPercentages set to null (n < {MIN_N_PCT}), sample size in brackets:")
any_null = False
for site in sites:
    for pct_field, n_field in PCT_FIELDS.items():
        cells = [f"{r['period']} ({r[n_field]})" for r in records
                 if r["site"] == site and r[pct_field] is None]
        if cells:
            any_null = True
            print(f"  {site} {pct_field}: {len(cells)} null: {', '.join(cells)}")
if not any_null:
    print("  none")

# known gaps: do the blank percentages still match what data_notes.md says?
record_by_key = {(r["site"], r["period"]): r for r in records}
gap_rows = []
gaps_ok = True
for (site, field), expected in KNOWN_GAPS.items():
    actual = {p for p in PERIODS if record_by_key[(site, p)][field] is not None}
    match = actual == expected
    gaps_ok = gaps_ok and match
    n_field = PCT_FIELDS[field]
    gap_rows.append({"site": site, "field": field,
                     "data_notes: non-null in": ", ".join(sorted(expected)) or "none",
                     "actual non-null in": ", ".join(p for p in PERIODS if p in actual) or "none",
                     "result": "match" if match else "DIFFERS",
                     "sample sizes by period": ", ".join(f"{p} {record_by_key[(site, p)][n_field]}"
                                                         for p in PERIODS)})
print("\nKnown gaps (data_notes.md):")
print(pd.DataFrame(gap_rows).to_string(index=False))
if not gaps_ok:
    print("A row marked DIFFERS means the data no longer matches data_notes.md; "
          "review and update it by hand.")

print(f"\nsum checks: {'pass' if sums_ok else 'FAIL'}; known gaps: {'match' if gaps_ok else 'DIFFER'}")
