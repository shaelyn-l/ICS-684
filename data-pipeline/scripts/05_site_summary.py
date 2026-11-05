"""Step 1.5: site summaries.

Builds public/data/site_summary.json (one record per site per period, as in the
Data contract in PLAN.md) and reports/site_summary_check.md, following the
decisions in reports/data_notes.md:

  - Hawaiian seasons, five full seasons only (May 2002 – Oct 2004), plus the
    pooled periods all / dry / wet
  - mosquito abundance from CO2 traps only; infection from every dissected mosquito
  - birds counted once per site-period (band number + species; NB rows one each),
    combined as any P -> positive, else any N -> negative, all U -> excluded
  - bird counts: station 200 dropped, NOBI events kept in the denominator
  - percentages null below 20 samples; abundance null only when n = 0

Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/05_site_summary.py
"""

import json
from pathlib import Path

import pandas as pd

PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent
RAW = PIPELINE / "raw"
BIO = RAW / "biocomplexity_2001_2004"
BLOOD_CSV = RAW / "bird_malaria_2001_2005" / "Banding Diagnostics Data Final_revised.csv"
LOOKUP = PIPELINE / "species_lookup.csv"
SITES_GEOJSON = ROOT / "public" / "data" / "sites.geojson"
OUTPUT = ROOT / "public" / "data" / "site_summary.json"
REPORT = PIPELINE / "reports" / "site_summary_check.md"

START, END = pd.Timestamp("2002-05-01"), pd.Timestamp("2004-10-31")  # five full seasons
SEASONS = ["2002-dry", "2002-wet", "2003-dry", "2003-wet", "2004-dry"]
PERIODS = {s: [s] for s in SEASONS}
PERIODS["all"] = SEASONS
PERIODS["dry"] = [s for s in SEASONS if s.endswith("dry")]
PERIODS["wet"] = [s for s in SEASONS if s.endswith("wet")]

MIN_N_PCT = 20  # percentages below this sample size are null
BIRD_COUNT_STATIONS = {100, 300, 500, 700, 900}  # station 200 dropped; see data_notes.md

FIELDS = [
    "site", "period",
    "mosquito_per_trap_night", "mosquito_trap_nights",
    "mosq_midgut_pct", "mosq_midgut_n",
    "mosq_salivary_pct", "mosq_salivary_n",
    "bird_prevalence_pct", "bird_sampled_n",
    "honeycreeper_prevalence_pct", "honeycreeper_sampled_n",
    "honeycreepers_per_count", "nonnative_birds_per_count", "bird_counts_n",
]
PCT_FIELDS = {"mosq_midgut_pct": "mosq_midgut_n", "mosq_salivary_pct": "mosq_salivary_n",
              "bird_prevalence_pct": "bird_sampled_n",
              "honeycreeper_prevalence_pct": "honeycreeper_sampled_n"}
ABUNDANCE_FIELDS = {"mosquito_per_trap_night": "mosquito_trap_nights",
                    "honeycreepers_per_count": "bird_counts_n",
                    "nonnative_birds_per_count": "bird_counts_n"}

# What data_notes.md "Known gaps" says: periods where the percentage is expected to be
# non-null (empty set = blank in every period).
KNOWN_GAPS = {
    ("SOL", "mosq_salivary_pct"): set(),
    ("SOL", "mosq_midgut_pct"): set(),
    ("CJR", "mosq_salivary_pct"): {"2004-dry", "dry", "all"},
    ("CJR", "mosq_midgut_pct"): {"2004-dry", "dry", "all"},
    ("WAI", "honeycreeper_prevalence_pct"): set(),
}


def season(ts):
    """Hawaiian season label; wet seasons are labeled by the year they start."""
    if 5 <= ts.month <= 10:
        return f"{ts.year}-dry"
    return f"{ts.year}-wet" if ts.month >= 11 else f"{ts.year - 1}-wet"


def read_seasonal(path, date_col, fmt, **kwargs):
    """Read a CSV, parse its date column with its own format, keep the five seasons."""
    df = pd.read_csv(path, **kwargs)
    df["when"] = pd.to_datetime(df[date_col], format=fmt)  # raises on any unparseable date
    df = df[df["when"].between(START, END)].copy()
    df["season"] = df["when"].map(season)
    return df


def load():
    lookup = pd.read_csv(LOOKUP, keep_default_na=False)
    canon = dict(zip(lookup["code"], lookup["canonical_code"]))
    species = lookup[lookup["canonical_code"] != ""].drop_duplicates("canonical_code")
    honeycreepers = set(species.loc[species["honeycreeper"] == "true", "canonical_code"])
    nonnative = set(species.loc[species["native"] == "false", "canonical_code"])

    traps = read_seasonal(BIO / "Biocomplexity_mosquito capture data.csv", "date", "%m/%d/%Y")
    traps = traps[traps["trap_type"] == "co2"]

    dissected = read_seasonal(BIO / "Biocomplexity_mosquito avian malaria infection and parity data.csv",
                              "date_collected", "%Y-%m-%d")

    blood = read_seasonal(BLOOD_CSV, "DATE", "%m/%d/%Y", keep_default_na=False)
    blood = blood.rename(columns={"LOCATION": "site"})
    blood["species"] = blood["SPECIES"].map(canon)
    # NB (no band) rows can't be matched across samples: give each its own bird id.
    blood["bird"] = blood["BANDNUMBER"].where(blood["BANDNUMBER"] != "NB",
                                              "NB-" + blood.index.astype(str))

    counts = read_seasonal(BIO / "Biocomplexity_bird count data.csv", "obsvdate", "%m/%d/%Y",
                           keep_default_na=False)  # keeps guild "NA" as text
    counts = counts[counts["station"].isin(BIRD_COUNT_STATIONS)]
    counts["species"] = counts["alphacode"].map(canon)

    missing = (set(blood["SPECIES"]) | set(counts["alphacode"])) - set(canon)
    assert not missing, f"species codes missing from species_lookup.csv: {missing}"
    return traps, dissected, blood, counts, honeycreepers, nonnative


def bird_status(group):
    """Combine one bird's results within a period: any P, else any N, else excluded."""
    statuses = set(group)
    if "P" in statuses:
        return "P"
    return "N" if "N" in statuses else None


def summarize(traps, dissected, blood, counts, honeycreepers, nonnative, sites):
    """Raw totals per site per period, before percentages and rounding."""
    totals = []
    for site in sites:
        for period, members in PERIODS.items():
            t = traps[(traps["site"] == site) & traps["season"].isin(members)]
            d = dissected[(dissected["site"] == site) & dissected["season"].isin(members)]
            b = blood[(blood["site"] == site) & blood["season"].isin(members)]
            c = counts[(counts["site"] == site) & counts["season"].isin(members)]

            midgut = d["midgut_infection"].dropna()
            salivary = d["salivary_infection"].dropna()

            birds = (b.groupby(["bird", "species"])["INFECTION_STATUS"].apply(bird_status)
                     .dropna().reset_index(name="status"))
            honey = birds[birds["species"].isin(honeycreepers)]

            events = c.drop_duplicates(["station", "transect", "obsvdate"])
            detections = c[c["alphacode"] != "NOBI"]

            totals.append({
                "site": site, "period": period,
                "culex": int(t["culex"].sum()), "trap_nights": len(t),
                "midgut_n": len(midgut), "midgut_pos": int((midgut == "yes").sum()),
                "salivary_n": len(salivary), "salivary_pos": int((salivary == "yes").sum()),
                "birds_n": len(birds), "birds_pos": int((birds["status"] == "P").sum()),
                "honey_n": len(honey), "honey_pos": int((honey["status"] == "P").sum()),
                "events": len(events),
                "honey_detections": int(detections["species"].isin(honeycreepers).sum()),
                "nonnative_detections": int(detections["species"].isin(nonnative).sum()),
            })
    return pd.DataFrame(totals)


def pct(pos, n):
    return round(pos / n * 100, 1) if n >= MIN_N_PCT else None


def rate(value, n, digits):
    return round(value / n, digits) if n > 0 else None


def to_records(totals):
    return [{
        "site": r.site, "period": r.period,
        "mosquito_per_trap_night": rate(r.culex, r.trap_nights, 3),
        "mosquito_trap_nights": r.trap_nights,
        "mosq_midgut_pct": pct(r.midgut_pos, r.midgut_n), "mosq_midgut_n": r.midgut_n,
        "mosq_salivary_pct": pct(r.salivary_pos, r.salivary_n), "mosq_salivary_n": r.salivary_n,
        "bird_prevalence_pct": pct(r.birds_pos, r.birds_n), "bird_sampled_n": r.birds_n,
        "honeycreeper_prevalence_pct": pct(r.honey_pos, r.honey_n), "honeycreeper_sampled_n": r.honey_n,
        "honeycreepers_per_count": rate(r.honey_detections, r.events, 2),
        "nonnative_birds_per_count": rate(r.nonnative_detections, r.events, 2),
        "bird_counts_n": r.events,
    } for r in totals.itertuples(index=False)]


def check_contract(records, sites):
    assert len(records) == len(sites) * len(PERIODS), f"expected 72 records, got {len(records)}"
    for r in records:
        assert list(r) == FIELDS, f"field set differs for {r['site']} {r['period']}"
        for p, n in PCT_FIELDS.items():
            assert (r[p] is None) == (r[n] < MIN_N_PCT), f"{p} null rule broken: {r}"
        for a, n in ABUNDANCE_FIELDS.items():
            assert (r[a] is None) == (r[n] == 0), f"{a} null rule broken: {r}"


# ---------- check report ----------

def md_table(headers, rows):
    lines = ["| " + " | ".join(map(str, headers)) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def sum_checks(totals):
    rows, ok = [], True
    for col, label in [("trap_nights", "CO2 trap nights"), ("midgut_n", "Mosquitoes examined (midgut)"),
                       ("salivary_n", "Mosquitoes examined (salivary)"), ("events", "Counting events")]:
        t = totals.pivot(index="site", columns="period", values=col)
        seasons_ok = (t[SEASONS].sum(axis=1) == t["all"]).all()
        halves_ok = (t["dry"] + t["wet"] == t["all"]).all()
        ok &= seasons_ok and halves_ok
        rows.append([label, "pass" if seasons_ok else "FAIL", "pass" if halves_ok else "FAIL"])
    return md_table(["Measure", "5 seasons = all", "dry + wet = all"], rows), ok


def known_gap_checks(records):
    by_key = {(r["site"], r["period"]): r for r in records}
    rows, ok = [], True
    for (site, field), expected in KNOWN_GAPS.items():
        actual = {p for p in PERIODS if by_key[(site, p)][field] is not None}
        match = actual == expected
        ok &= match
        n_field = PCT_FIELDS[field]
        sizes = ", ".join(f"{p} {by_key[(site, p)][n_field]}" for p in PERIODS)
        rows.append([site, f"`{field}`", ", ".join(sorted(expected)) or "none",
                     ", ".join(p for p in PERIODS if p in actual) or "none",
                     "match" if match else "DIFFERS", sizes])
    return md_table(["Site", "Field", "data_notes: non-null in", "Actual non-null in",
                     "Result", "Sample sizes by period"], rows), ok


def write_report(totals, records, sites):
    allp = totals[totals["period"] == "all"].set_index("site").loc[sites]
    site_rows = [[s, r.culex, r.trap_nights,
                  f"{r.midgut_pos}/{r.midgut_n}", f"{r.salivary_pos}/{r.salivary_n}",
                  f"{r.birds_pos}/{r.birds_n}", f"{r.honey_pos}/{r.honey_n}",
                  r.events, r.honey_detections, r.nonnative_detections]
                 for s, r in allp.iterrows()]
    sums_table, sums_ok = sum_checks(totals)
    gaps_table, gaps_ok = known_gap_checks(records)

    small = []
    for r in records:
        for p, n in PCT_FIELDS.items():
            if r[p] is None:
                small.append((r["site"], r["period"], p, r[n]))
    small_rows = []
    for site in sites:
        for p in PCT_FIELDS:
            cells = [f"{per} ({n})" for s, per, f, n in small if s == site and f == p]
            if cells:
                small_rows.append([site, f"`{p}`", len(cells), ", ".join(cells)])

    seasonal = {r["site"]: r for r in records if r["period"] == "all"}
    lines = [
        "# Site summary check", "",
        "Generated by `scripts/05_site_summary.py`. Output: `public/data/site_summary.json` "
        f"({len(records)} records: {len(sites)} sites × {len(PERIODS)} periods). "
        "Data used: May 2002 – Oct 2004 (five full Hawaiian seasons).", "",
        f"- Contract checks: pass (exact field set, percentages null exactly when n < {MIN_N_PCT}, "
        "abundance null exactly when n = 0).",
        f"- Sum checks: {'pass' if sums_ok else 'FAIL'}.",
        f"- Known gaps: {'match data_notes.md' if gaps_ok else 'DIFFER from data_notes.md (see below)'}.", "",
        "## 1. Per-site totals for `all` (low to high elevation)", "",
        "Positive/total for infection and prevalence. Detections exclude NOBI.", "",
        md_table(["Site", "Culex caught (CO2)", "CO2 trap nights", "Midgut +/n", "Salivary +/n",
                  "Birds +/n", "Honeycreepers +/n", "Counting events",
                  "Honeycreeper detections", "Non-native detections"], site_rows), "",
        "Values in `site_summary.json` for `all`:", "",
        md_table(["Site", "Culex / trap night", "Salivary %", "Bird prevalence %",
                  "Honeycreeper prevalence %", "Honeycreepers / count", "Non-native / count"],
                 [[s, seasonal[s]["mosquito_per_trap_night"], seasonal[s]["mosq_salivary_pct"],
                   seasonal[s]["bird_prevalence_pct"], seasonal[s]["honeycreeper_prevalence_pct"],
                   seasonal[s]["honeycreepers_per_count"], seasonal[s]["nonnative_birds_per_count"]]
                  for s in sites]), "",
        "## 2. Sum checks", "",
        "Additive sample sizes only. Bird sample sizes are not additive, because a bird sampled "
        "in two seasons counts once in each season but once in `all`.", "",
        sums_table, "",
        f"## 3. Percentages set to null (n < {MIN_N_PCT})", "",
        "Sample size in brackets.", "",
        md_table(["Site", "Field", "Null cells", "Periods"], small_rows) if small_rows else "None.", "",
        "## 4. Known gaps (data_notes.md)", "",
        gaps_table, "",
    ]
    if not gaps_ok:
        lines += ["A row marked DIFFERS means the data no longer matches what data_notes.md says. "
                  "data_notes.md has not been changed; review and update it by hand.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(PIPELINE)}")
    return sums_ok, gaps_ok


def main():
    features = json.loads(SITES_GEOJSON.read_text(encoding="utf-8"))["features"]
    sites = [f["properties"]["site"]
             for f in sorted(features, key=lambda f: f["properties"]["elevation_m"])]

    totals = summarize(*load(), sites)
    records = to_records(totals)
    check_contract(records, sites)

    OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(records)} records)")
    sums_ok, gaps_ok = write_report(totals, records, sites)
    print(f"sum checks: {'pass' if sums_ok else 'FAIL'}; known gaps: {'match' if gaps_ok else 'DIFFER'}")


if __name__ == "__main__":
    main()
