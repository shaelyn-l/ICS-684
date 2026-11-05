"""Step 1.4: sample coverage per site for each time-period option.

Counts the samples Step 1.5 will actually use, following reports/data_notes.md:
  - trap nights        mosquito capture rows (one trap on one night)
  - midgut examined    dissected mosquitoes with a recorded midgut_infection
  - salivary examined  dissected mosquitoes with a recorded salivary_infection
  - birds (all)        unique birds per period with a determined INFECTION_STATUS
  - birds (honeycr.)   the same, honeycreepers only
  - counting events    site + station + transect + date, NOBI included, station 200 dropped

Period options: month, Hawaiian season (wet Nov–Apr / dry May–Oct), four seasons,
year. Each is reported for a 2001 start and a 2002 start, ending 2004-12-31.

Writes reports/coverage.md. Rerunning overwrites it. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/04_coverage.py
"""

from pathlib import Path

import pandas as pd

PIPELINE = Path(__file__).resolve().parent.parent
RAW = PIPELINE / "raw"
BIO = RAW / "biocomplexity_2001_2004"
BLOOD_CSV = RAW / "bird_malaria_2001_2005" / "Banding Diagnostics Data Final_revised.csv"
LOOKUP = PIPELINE / "species_lookup.csv"
REPORT = PIPELINE / "reports" / "coverage.md"

SITES = ["MAL", "NAN", "BRY", "WAI", "COO", "CRA", "PUU", "CJR", "SOL"]  # low to high elevation
END = pd.Timestamp("2004-12-31")
STARTS = {"2001": pd.Timestamp("2001-01-01"), "2002": pd.Timestamp("2002-01-01")}
THRESHOLDS = [10, 20, 30]
BIRD_COUNT_STATIONS = {100, 300, 500, 700, 900}  # station 200 dropped; see data_notes.md


# ---------- period options ----------

def month_label(ts):
    return f"{ts.year}-{ts.month:02d}"


def hawaiian_label(ts):
    # Wet season Nov–Apr, labeled by the year it starts: 2002-wet = Nov 2002–Apr 2003.
    if ts.month >= 11:
        return f"{ts.year}-wet"
    if ts.month <= 4:
        return f"{ts.year - 1}-wet"
    return f"{ts.year}-dry"


def four_season_label(ts):
    # December belongs to the following year's Dec–Feb season.
    if ts.month == 12:
        return f"{ts.year + 1}-DJF"
    return f"{ts.year}-" + {1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA",
                            7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}[ts.month]


def year_label(ts):
    return str(ts.year)


OPTIONS = {  # name -> (label function, months per full period)
    "Month": (month_label, 1),
    "Hawaiian season": (hawaiian_label, 6),
    "Four seasons": (four_season_label, 3),
    "Year": (year_label, 12),
}


def periods_in_window(label_fn, months_per_period, start):
    """Ordered period labels overlapping [start, END], and which are cut short by the window."""
    months = pd.date_range(start, END, freq="MS")
    labels = pd.Series([label_fn(m) for m in months])
    order = list(dict.fromkeys(labels))
    partial = {p for p, n in labels.value_counts().items() if n < months_per_period}
    return order, partial


# ---------- load the samples Step 1.5 will use ----------

def read_dated(path, date_col, fmt, **kwargs):
    df = pd.read_csv(path, **kwargs)
    df["when"] = pd.to_datetime(df[date_col], format=fmt)  # raises on any unparseable date
    return df[df["when"] <= END]


def load_samples():
    """One row per sample, with columns site and when, for each dataset."""
    out, notes = {}, []

    cap = read_dated(BIO / "Biocomplexity_mosquito capture data.csv", "date", "%m/%d/%Y")
    out["Mosquito trap nights"] = cap[["site", "when"]]
    dup = cap.duplicated(["site", "station", "transect", "date", "trap_type"]).sum()
    notes.append(f"Mosquito captures: {dup} rows repeat another row's site, station, transect, date "
                 "and trap type (usually with different catches, so probably a second trap). "
                 "Each row is counted as one trap night.")

    dis = read_dated(BIO / "Biocomplexity_mosquito avian malaria infection and parity data.csv",
                     "date_collected", "%Y-%m-%d")
    out["Mosquitoes examined (midgut)"] = dis[dis["midgut_infection"].notna()][["site", "when"]]
    out["Mosquitoes examined (salivary)"] = dis[dis["salivary_infection"].notna()][["site", "when"]]

    blood = read_dated(BLOOD_CSV, "DATE", "%m/%d/%Y", keep_default_na=False)
    blood = blood.rename(columns={"LOCATION": "site"})
    lookup = pd.read_csv(LOOKUP, keep_default_na=False)
    canon = dict(zip(lookup["code"], lookup["canonical_code"]))
    honey = set(lookup.loc[lookup["honeycreeper"] == "true", "canonical_code"])
    blood["species"] = blood["SPECIES"].map(canon)
    determined = blood[blood["INFECTION_STATUS"].isin(["P", "N"])]
    nb = (determined["BANDNUMBER"] == "NB").sum()
    multi_species = (blood.groupby("BANDNUMBER")["species"].nunique() > 1).sum()
    notes.append(f"Bird blood samples: {(blood['BANDNUMBER'] == 'NB').sum()} rows have band number "
                 f"`NB` (no band); {nb} of them have a determined status. Unbanded birds can't be "
                 "matched across samples, so each `NB` row is counted as a separate bird.")
    notes.append(f"Bird blood samples: {multi_species} band numbers appear under more than one "
                 "species. Birds are counted as unique site + period + band number + species, so "
                 "these are not merged.")
    out["Birds sampled (all)"] = determined
    out["Birds sampled (honeycreepers)"] = determined[determined["species"].isin(honey)]

    counts = read_dated(BIO / "Biocomplexity_bird count data.csv", "obsvdate", "%m/%d/%Y",
                        keep_default_na=False)
    counts = counts[counts["station"].isin(BIRD_COUNT_STATIONS)]
    out["Bird counting events"] = counts.drop_duplicates(["site", "station", "transect", "obsvdate"])

    return out, notes


def per_cell_counts(df, dataset, label_fn, periods):
    """Samples per site per period, as a sites x periods table including zero cells."""
    df = df.assign(period=df["when"].map(label_fn))
    if dataset.startswith("Birds sampled"):
        # Count each bird once per site-period; NB rows are each their own bird.
        banded = df[df["BANDNUMBER"] != "NB"].drop_duplicates(["site", "period", "BANDNUMBER", "species"])
        df = pd.concat([banded, df[df["BANDNUMBER"] == "NB"]])
    table = df.groupby(["site", "period"]).size().unstack(fill_value=0)
    return table.reindex(index=SITES, columns=periods, fill_value=0)


# ---------- report helpers ----------

def md_table(headers, rows):
    lines = ["| " + " | ".join(map(str, headers)) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(lines)


def runs(labels, order):
    """Collapse consecutive period labels into ranges, e.g. 2001-01–2001-06."""
    pos = {p: i for i, p in enumerate(order)}
    idx = sorted(pos[p] for p in labels)
    groups, start = [], None
    for i, j in zip(idx, idx[1:] + [None]):
        start = i if start is None else start
        if j != i + 1:
            groups.append(order[start] if start == i else f"{order[start]}–{order[i]}")
            start = None
    return ", ".join(groups)


def pct(x):
    return f"{x:.0f}%"


def main():
    samples, notes = load_samples()
    summary = {}  # (start, option, dataset) -> % cells >= each threshold

    body = []
    for start_name, start in STARTS.items():
        body += [f"# Starting {start_name}", ""]
        for dataset, df in samples.items():
            df = df[df["when"] >= start]
            body += [f"## {dataset} (start {start_name})", ""]
            rows, zero_lists, medians = [], [], {}
            for option, (fn, months) in OPTIONS.items():
                periods, partial = periods_in_window(fn, months, start)
                t = per_cell_counts(df, dataset, fn, periods)
                cells = t.size
                shares = [(t >= th).to_numpy().mean() * 100 for th in THRESHOLDS]
                zeros = (t == 0).to_numpy().sum()
                # % of cells at >=10, >=20, >=30 samples, then % of cells with zero samples
                summary[(start_name, option, dataset)] = shares + [zeros / cells * 100]
                part = f" ({len(partial)} partial)" if partial else ""
                rows.append([option, f"{len(periods)}{part}", cells, *map(pct, shares),
                             f"{zeros} ({zeros / cells * 100:.0f}%)"])
                zero_lists.append((option, periods, t))
                medians[option] = t.median(axis=1)

            body += [md_table(["Period option", "Periods", "Site-period cells",
                               *[f"≥{th} samples" for th in THRESHOLDS], "Zero cells"], rows), ""]

            body += ["Median samples per period, by site (low to high elevation):", "",
                     md_table(["Site", *OPTIONS], [[s, *[f"{medians[o][s]:g}" for o in OPTIONS]]
                                                  for s in SITES]), ""]

            body += ["<details><summary>Zero-sample cells</summary>", ""]
            for option, periods, t in zero_lists:
                body.append(f"**{option}**")
                body.append("")
                any_zero = False
                for s in SITES:
                    z = [p for p in periods if t.loc[s, p] == 0]
                    if z:
                        any_zero = True
                        body.append(f"- {s}: {runs(z, periods)}")
                if not any_zero:
                    body.append("- none")
                body.append("")
            body += ["</details>", ""]

    head = [
        "# Sample coverage by time period", "",
        "Generated by `scripts/04_coverage.py`. Counts are the samples Step 1.5 will use, after "
        "the rules in `data_notes.md` (dates trimmed to 2004-12-31, blank infection results "
        "excluded, `U` infection status excluded, each bird counted once per site-period, "
        "station 200 dropped, NOBI events kept).", "",
        "Period options:", "",
        "- **Month**: e.g. `2002-03`.",
        "- **Hawaiian season**: wet Nov–Apr, dry May–Oct. Wet seasons are labeled by start year "
        "(`2002-wet` = Nov 2002–Apr 2003).",
        "- **Four seasons**: DJF, MAM, JJA, SON. December counts toward the next year's DJF.",
        "- **Year**.", "",
        "A period marked *partial* is cut short by the start or end date (for example `2000-wet` "
        "holds only Jan–Apr 2001, and `2005-DJF` holds only Dec 2004). Partial periods are "
        "included in the cell counts below.", "",
        "## Data notes from this script", "",
        *[f"- {n}" for n in notes], "",
        "## Overview: % of site-period cells with at least 20 samples", "",
    ]
    datasets = list(samples)
    for start_name in STARTS:
        head += [f"Start {start_name}:", "",
                 md_table(["Period option", *datasets],
                          [[o, *[pct(summary[(start_name, o, d)][1]) for d in datasets]]
                           for o in OPTIONS]), ""]

    REPORT.write_text("\n".join(head + body + recommendation(summary, datasets)), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(PIPELINE)}")
    for start_name in STARTS:
        print(f"\n% cells >= 10 / 20 / 30, start {start_name}")
        for o in OPTIONS:
            print(f"  {o:16}", "  ".join(
                f"{d.split(' (')[0][:14]:>14}: " + "/".join(f"{v:.0f}" for v in summary[(start_name, o, d)])
                for d in datasets))


def recommendation(summary, datasets):
    def s(option, dataset, i=1, start="2002"):
        """% of cells with >=10 (i=0), >=20 (i=1), >=30 (i=2) samples, or zero samples (i=3)."""
        return pct(summary[(start, option, dataset)][i])

    honey, saliv, counts, traps = ("Birds sampled (honeycreepers)", "Mosquitoes examined (salivary)",
                                   "Bird counting events", "Mosquito trap nights")
    return [
        "# Recommendation", "",
        "These are suggestions with trade-offs; the decision is yours. Record it in the Decisions "
        "log in PLAN.md and in data_notes.md. Figures below are for a 2002 start unless noted.", "",
        "## (a) Period option: Hawaiian season (wet/dry)", "",
        "- **Month** is too fine. Only "
        f"{s('Month', honey)} of site-months have ≥20 honeycreepers sampled and "
        f"{s('Month', saliv)} have ≥20 mosquitoes examined, and {s('Month', counts, 3)} of "
        "site-months have no bird counts at all, because counts were done in rounds about every "
        "three months.",
        "- **Four seasons** splits the bird count rounds badly: the rounds fall around Feb–Mar, "
        "May–Jun, Aug–Sep and Nov–Dec, which straddle the DJF/MAM and SON/DJF boundaries, so "
        f"{s('Four seasons', counts, 3)} of site-seasons have no bird counts while others get two "
        f"rounds. Only {s('Four seasons', honey)} of cells have ≥20 honeycreepers sampled and "
        f"{s('Four seasons', saliv)} have ≥20 mosquitoes examined.",
        "- **Hawaiian season** puts two count rounds in every site-season "
        f"({s('Hawaiian season', counts, 3)} zero cells), and raises the share of cells with ≥20 "
        f"samples to {s('Hawaiian season', honey)} for honeycreepers and "
        f"{s('Hawaiian season', saliv)} for mosquitoes examined. Wet vs. dry is also a natural "
        "frame for mosquito breeding. Trade-offs: only 5 full seasons in 2002–2004 (7 slider "
        "steps counting the partial ones below), and each "
        "wet season spans two calendar years (`2002-wet` = Nov 2002–Apr 2003), which needs a "
        "sentence of explanation.",
        "- **Year** has the most samples per cell but only three steps, and it hides the seasonal "
        "swing in mosquitoes and transmission.",
        "",
        "With a 2002 start, the Hawaiian-season slider has two partial periods: `2001-wet` "
        "(Jan–Apr 2002 only; mosquito trapping starts in Feb and counts in Mar) and `2004-wet` "
        "(Nov–Dec 2004 only). Either keep them and label them as partial, or run the slider "
        "`2002-dry` to `2004-dry` (5 full seasons) and leave those months out.",
        "",
        "## (b) Start date: 2002", "",
        "- Mosquito captures begin in Feb 2002 and bird counts in Mar 2002, so a 2002 start is the "
        "first point where all four datasets are running. With a 2001 start, every 2001 period "
        "has zero trap nights and zero bird counts, so half the measures would be blank for those "
        f"steps (Hawaiian season: {s('Hawaiian season', traps, 3, '2001')} of cells with no trap "
        f"nights vs. {s('Hawaiian season', traps, 3)} with a 2002 start).",
        "- Trade-off: a 2002 start drops the 2001 mosquito dissections and blood samples.",
        "",
        "## (c) Minimum sample size for showing a percentage: 20", "",
        "- At 20 samples one infected bird or mosquito moves the percentage by 5 points; the "
        "margin of error is still wide (roughly ±20 points near 50%), so pair it with the sample "
        "size in the popup.",
        "- **10** shows more cells but lets a single sample swing the value by 10 points. "
        "**30** is steadier but blanks noticeably more cells (see the ≥30 columns).",
        "- No minimum rescues mosquito infection at the two highest sites: SOL had 2 *Culex* "
        "caught in three years and CJR 76, so their infection percentages will be blank under any "
        "option. That is a real result (almost no mosquitoes at high elevation), so the app should "
        "say \"too few mosquitoes to test\" rather than show nothing.",
        "- The minimum applies to percentages only (infection and prevalence). Abundance measures "
        "(per trap night, per count) can be shown whenever the sample size is above zero.",
        "",
    ]


if __name__ == "__main__":
    main()
