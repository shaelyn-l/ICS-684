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
- Two trap types (`co2`, `gravid`) catch differently. Keep `trap_type` available; don't mix them without noting it.

## Mosquito dissections

- All rows are Culex.
- 2,128 rows have no `date_dissected`. **Use `date_collected` for time periods.**
- `sporulated_oocysts_l` loads as text while other oocyst columns are numbers. Check for stray values before using it.

## Small samples

- Mosquito dissections per site: COO 1,959; PUU 1,523; WAI 1,517; NAN 661; MAL 451; CRA 328; BRY 282; CJR 60; SOL 2.
- **Decision (TBD):** show infection rates only where dissections ≥ [minimum, e.g. 20]; otherwise show "too few samples."

## Bird counts

- Each row is one bird detected, not a count total. To get birds per count, define one counting event as a unique site + station + transect + date, then divide detections by events.
- Bird counts were done at stations 100, 300, 500, 700, 900 only (25 count stations per site, 200 m apart, per the Biocomplexity metadata).
- Station 200 (25 rows) is outside this protocol. See `reports/station200_check.md`.
  - MAL, transect 0, 2003-05-06: an extra stop between 100 and 300; all five standard stops also present.
  - CRA, transect 600, 2004-05-22: likely mislabeled (station 900 missing, timing out of order); can't be corrected confidently.
- **Decision:** drop all 25 station-200 rows from bird count summaries (0.07% of rows; no meaningful effect on results). Keep the raw file unchanged. Station 200 points have `has_bird_counts = false` in `stations.geojson` (applied in `scripts/02_sites.py` via `BIRD_COUNT_STATIONS`). Later scripts that summarize bird counts must drop these rows too.

## Bird blood samples (malaria infection)

- Diagnostic columns: `MALARIA DIAGNOSIS`, `SEROLOGY`, `SMEAR`, `PCR`, `IMMUNOBLOT`, `INFECTION_STATUS`.
- `INFECTION_STATUS` appears to be the final combined result (`P` = positive in sample rows). It has three values. **Check the XML metadata** to confirm what each means; treat "not determined" as missing, not negative.
- Many birds were caught more than once: 12,880 rows, 8,774 unique `BANDNUMBER`s. `RECAPTURE STATUS` marks recaptures. **Count each bird once per time period.**

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
- **Decision (TBD):** start in 2002 so all datasets cover the same period, or keep the 2001 dissections and blood samples as partial data.