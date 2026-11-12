# Data notes

Known data issues and decisions from the Step 1.1 inspection (`reports/inspection.md`).
Read this before any data-pipeline step. Items marked **TBD** still need a decision.

## Files and key columns

| File | Folder | Site column | Date column | Date format |
|---|---|---|---|---|
| Biocomplexity_sampling station spatial coordinates.csv | biocomplexity_2001_2004 | `site` | none | n/a |
| Biocomplexity_mosquito capture data.csv | biocomplexity_2001_2004 | `site` | `date` | M/D/YYYY |
| Biocomplexity_mosquito avian malaria infection and parity data.csv | biocomplexity_2001_2004 | `site` | `date_collected` | YYYY-MM-DD |
| Biocomplexity_bird count data.csv | biocomplexity_2001_2004 | `site` | `obsvdate` | M/D/YYYY |
| Banding Diagnostics Data Final_revised.csv | bird_malaria_2001_2005 | `LOCATION` | `DATE` | M/D/YYYY |

- Parse each date column with its own format. The dissection file uses a different format from the others.

## Sites and coordinates (verified)

- All nine site codes match across every file: BRY, CJR, COO, CRA, MAL, NAN, PUU, SOL, WAI.
- `LOCATION` in the bird blood file = `site` in the Biocomplexity files.
- Coordinates (`x_long`, `y_lat`) are already decimal-degree WGS84 longitude/latitude, east Hawaiʻi Island. No UTM conversion needed.
- `elevation_m` ranges 28–1,836 m.
- Coordinates file has 405 rows = 9 sites × 9 stations × 5 transects, one row per sampling point.

## Missing-value codes

- `9999` = missing in bird count weather/time columns (`timestart`, `cloud`, `rain`, `wind`, `gust`, plus single rows in `distance` and `detection_type`). Treat as null.
- `ND` = missing in bird blood columns and in mosquito `wing_length` and `ovary_parity`. Treat as null; convert measurement columns to numbers afterward.
- Blank `midgut_infection` (366 rows) and `salivary_infection` (403 rows) = not examined. Exclude from the denominator; do not count as negative.

## Mosquito captures

- Columns `culex`, `aedes`, `wyeomyia` are counts per trap. Only *Culex* carries avian malaria. **Use `culex` for mosquito abundance.**
- Two trap types (`co2`, `gravid`) catch differently. May 2002–Oct 2004: CO2 averaged 0.59 *Culex* per trap night and gravid 0.13, with similar effort per site, but the ratio varies widely by site (PUU 2.02 vs. 0.06; CRA 0.05 vs. 0.19).
- **Decision:** mosquito abundance uses **CO2 traps only** (host-seeking females, the ones that bite birds). Infection rates use every dissected mosquito, whichever trap caught it.
- **Decision (reviewed after Step 1.5):** keep both trap types for infection rates, to keep sample sizes up. Caveat: gravid-trap mosquitoes are salivary-positive far more often (31.6% vs. 7.8% for CO2, May 2002–Oct 2004) because they have already blood-fed. So a site's infection rate partly reflects its trap mix. CRA is the clearest case: 75% of its dissections came from gravid traps, giving 32.5% salivary overall, though by trap type it matches COO (CO2 9.5% vs. 9.3%; gravid 40.2% vs. 40.3%). PUU's 6.3% is pulled down the other way (98% CO2). **State this caveat in the app's "About the data" panel (Step 7.2).**
- 72 rows repeat another row's site, station, transect, date and trap type, usually with different catches, so likely a second trap. Each row counts as one trap night.

## Mosquito dissections

- All rows are Culex.
- 2,128 rows have no `date_dissected`. **Use `date_collected` for time periods.**
- `sporulated_oocysts_l` loads as text while other oocyst columns are numbers. Check for stray values before using it.

## Small samples

- Mosquito dissections per site: COO 1,959; PUU 1,523; WAI 1,517; NAN 661; MAL 451; CRA 328; BRY 282; CJR 60; SOL 2.
- **Decision (Step 1.4):** minimum sample size is 20, for percentages only (mosquito infection, bird prevalence). Below 20 the percentage is `null`, the sample size is still filled in, and the app shows "too few samples." Abundance measures (per trap night, per count) are shown whenever the sample size is above zero. See `reports/coverage.md`.

## Bird counts

- Each row is one bird detected, not a count total. To get birds per count, define one counting event as a unique site + station + transect + date, then divide detections by events.
- Bird counts were done at stations 100, 300, 500, 700, 900 only (25 count stations per site, 200 m apart, per the Biocomplexity metadata).
- Station 200 (25 rows) is outside this protocol. See `reports/station200_check.md`.
  - MAL, transect 0, 2003-05-06: an extra stop between 100 and 300; all five standard stops also present.
  - CRA, transect 600, 2004-05-22: likely mislabeled (station 900 missing, timing out of order); can't be corrected confidently.
- **Decision:** drop all 25 station-200 rows from bird count summaries (0.07% of rows; no meaningful effect on results). Keep the raw file unchanged. Station 200 points have `has_bird_counts = false` in `stations.geojson` (applied in `scripts/02_sites.py` via `BIRD_COUNT_STATIONS`). Later scripts that summarize bird counts must drop these rows too.

## Bird blood samples (malaria infection)

- Diagnostic columns: `MALARIA DIAGNOSIS`, `SEROLOGY`, `SMEAR`, `PCR`, `IMMUNOBLOT`, `INFECTION_STATUS`.
- `INFECTION_STATUS` is the final combined result: "malarial infection status based on serology, blood smear, and PCR or some combination of these tests" (bird blood XML metadata). Values, with row counts out of 12,880 rows:

  | Value | Meaning (from the metadata) | Rows |
  |---|---|---|
  | `P` | Positive for malaria by one or more assays | 3,245 |
  | `N` | Negative for malaria by one or more assays | 6,299 |
  | `U` | Unknown; insufficient data to classify as positive or negative | 3,336 |

  - `U` is the "not determined" case: treat it as missing, not negative. About 26% of rows are `U`, so bird sample sizes will be noticeably smaller than the raw row counts.
  - The metadata warns that when only one test was done, status rests on that test alone, so prevalence may be underestimated (especially smear-only samples). Mention this as a caveat in the app's "About the data" panel.

### Recaptures
- Many birds were caught more than once: 12,880 rows, 8,774 unique `BANDNUMBER`s. `RECAPTURE STATUS` marks recaptures.
- **Decision:** count each bird once per time period. Across periods, a bird counts once in each period it was sampled.
- **Decision:** when a bird has several results in the same period, combine them as:
  - **Positive** if any result is `P` (chronic infections persist; a later negative is likely a missed detection).
  - **Negative** if at least one result is `N` and none are `P`.
  - **Missing** if all results are `U` (bird excluded from that period's sample).
- Unbanded birds (`BANDNUMBER` = `NB`) are counted one row per bird, since they can't be matched across samples. Only 27 have a determined result in 2002–2004 (24 within the five seasons).
- 8 band numbers appear under more than one species. These are kept as separate birds: a bird is a unique site + period + band number + species.

## Species codes (resolved in Step 1.3)

- Lookup: `species_lookup.csv`. Summary: `reports/species_check.md`. 30 codes, 24 distinct species after merging.
- All codes resolved from the two XML metadata files. Merged codes (same scientific name in both files):
  - AKIA → AKIP (ʻAkiapōlāʻau)
  - HWAH → HAWH (ʻIo, Hawaiian Hawk)
  - JAWE → WAWE (Warbling White-eye)
  - MELT → HWAM (Hwamei)
  - NUMA → SBMU (Scaly-breasted Munia)
- Always group by `canonical_code`, never by raw `code`.
- **Decision:** HCRE displayed as "Hawaiʻi Creeper (ʻAlawī)", *Loxops mana* (files disagree on the name; same species).
- Honeycreepers: APAP, HAAM, IIWI, HAAK, HCRE, AKIP. Native non-honeycreepers: OMAO, HAEL, HAWH (ʻIo).
- Guild `NA` must be read as a text value, not missing (REJU, NOBI). Native status follows guild: ENDM = native; XNTV and GAME = non-native.
- `NOBI` = "no birds detected." Not a species, but a real counting event with zero birds. **Keep these events in birds-per-count denominators** (Step 1.5).
- **Decision:** the app's "native bird abundance" measure = **honeycreepers only** (`honeycreeper = true`). Non-native abundance = all `native = false` species.

## Date ranges

| Dataset | Start | End |
|---|---|---|
| Mosquito dissections (`date_collected`) | 2001-06 | 2004-12 |
| Mosquito captures | 2002-02 | 2004-12 |
| Bird counts | 2002-03 | 2004-12 |
| Bird blood samples | 2001-03 | 2005-07 |

- All four datasets overlap 2002–2004.
- **Decision:** trim to end of 2004 to match the Biocomplexity data.
- **Decision (Step 1.4):** time periods are Hawaiian seasons (wet Nov–Apr, dry May–Oct), starting 2002, five full seasons only: `2002-dry`, `2002-wet`, `2003-dry`, `2003-wet`, `2004-dry` (`2002-wet` = Nov 2002–Apr 2003). The partial periods Jan–Apr 2002 and Nov–Dec 2004 are dropped, so the data used runs May 2002–Oct 2004. Combined periods `all`, `dry` and `wet` are built from these five seasons only. In the app, time steps are buttons, not a slider.

## Known gaps

These are real results, not data errors. Figures are for the five seasons, using salivary-examined mosquitoes and honeycreepers with a determined status.

- **SOL mosquito infection is blank under every period**: only 2 *Culex* caught in three years, and only 2 examined (both in `2004-dry`). The app should show "too few mosquitoes to test," not an empty value.
- **CJR mosquito infection is blank in most periods**: 76 *Culex* caught in three years. Only `2004-dry` (32 examined) and the combined `dry` (40) and `all` (42) reach 20; the other four seasons and `wet` show "too few mosquitoes to test."
- **WAI honeycreeper prevalence is blank in every period**: 1–7 honeycreepers per season, 17 across `all`. It always shows "too few samples."