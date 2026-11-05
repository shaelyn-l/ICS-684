# Hawaiʻi Island Avian Malaria Story Map — Build Plan

An interactive web application telling the story of avian malaria and Hawaiian honeycreepers on Hawaiʻi Island, using a 3D terrain map, environmental layers, field data from nine study sites, and a flat comparison view.

This plan is written to be fed to Claude Code **one step at a time**. Each step has a goal, a prompt you can paste, and a "done when" check. Finish and check each step before starting the next, so any problem is easy to trace to the step that caused it.

---

## How to use this plan with Claude Code

1. Put this file in the root of the repository as `PLAN.md`.
2. Start each Claude Code session with: *"Read PLAN.md. We are doing Step X.Y only."* Then paste that step's prompt.
3. After each step: run the app or script, check the "done when" list, then commit (`git commit -m "Step X.Y: ..."`).
4. If something breaks, you know it came from the most recent step. Ask Claude Code to fix it before moving on.

### Ground rules for Claude Code (include in every session)

- Do **only** the current step. Don't start later steps or refactor unrelated files.
- Don't change the data file formats in `public/data/` without updating the **Data contract** section of this plan.
- Keep dependencies free and open source. No API keys or paid services.
- Explain any new dependency before adding it.
- When a step is finished, summarize what changed and how to test it.

---

## Tech stack (all free, shareable among team members)

| Part | Choice | Why |
|---|---|---|
| Web framework | **React + Vite** | Free, widely documented, components keep map, charts, and story separate |
| Map | **MapLibre GL JS** | Free and open source, 3D terrain, no account or token |
| Terrain tiles | **AWS Terrain Tiles (Terrarium format)** to start; optionally self-generated tiles from the USGS 10 m DEM later | Free, no key, works with MapLibre immediately |
| Charts | **D3** | Flat bar chart view and small linked charts |
| Scroll story | **Scrollama** (Phase 6) | Lightweight scroll-triggered chapters |
| Data processing | **Python** (pandas, geopandas, pyproj, rasterio, shapely) | Handles CSVs, coordinate conversion, and rasters |
| Collaboration | **GitHub** repository | Shared code, issues, and history |
| Hosting | **GitHub Pages** (or Netlify/Vercel free tier) | Free public link for the team and viewers |

---

## Folder structure

```
/
├── PLAN.md                  ← this file
├── README.md                ← setup instructions for teammates
├── data-pipeline/           ← Python scripts (run locally, not part of the website)
│   ├── requirements.txt
│   ├── raw/                 ← downloaded source data (large files git-ignored)
│   ├── scripts/             ← one script per processing step
│   └── reports/             ← text summaries from inspection scripts
├── public/
│   └── data/                ← processed, web-ready files the app loads
└── src/                     ← React app
    ├── components/          ← Map, LayerControls, SeasonButtons, FlatChart, Story...
    ├── config/              ← colors, layer settings, chapter definitions
    └── App.jsx
```

---

## Source data you need to download (into `data-pipeline/raw/`)

| Folder name | Dataset | Link |
|---|---|---|
| `biocomplexity_2001_2004/` | Island of Hawaiʻi bird, mosquito, and avian malaria infection data 2001–2004: all four CSVs plus the XML metadata | https://usgs.gov/data/island-hawaii-bird-mosquito-and-avian-malaria-infection-data-2001-2004 |
| `bird_malaria_2001_2005/` | Island of Hawaiʻi forest bird malaria infection data 2001–2005: CSV plus metadata | https://data.usgs.gov/datacatalog/data/USGS:671c19e5d34efed56210f490 |
| `land_cover/` | Hawaiʻi Land Cover and Habitat Status (Carbon Assessment of Hawaiʻi) | https://www.usgs.gov/data/hawaii-land-cover-and-habitat-status |
| `temperature/` | Climate of Hawaiʻi air temperature GIS layers (mean annual, and monthly if available) | https://www.hawaii.edu/climate-data-portal/climate-atlas/ |
| `dem/` | USGS 10 m DEM, Big Island (PacIOOS). Optional at first, since terrain tiles cover the visual. Needed for area calculations. | https://pae-paha.pacioos.hawaii.edu/erddap/griddap/usgs_dem_10m_bigisland.html |

Later phases (not needed for the core story):
- Fortini et al. 2015 species range projections: https://www.sciencebase.gov/catalog/item/55e108e0e4b05561fa20652f
- Predicted malaria risk 2098–2100: https://sciencebase.gov/catalog/item/57ec5fbce4b090825010b908

Key reference for the malaria temperature thresholds (13°C refuge limit, reduced development below 21°C): LaPointe, Goff & Atkinson 2010, https://pubs.usgs.gov/publication/70200648

---

## Data contract (what the app expects in `public/data/`)

Claude Code should create these exact files and fields. If a step needs to change them, update this section first.

**`stations.geojson`**: Point features, one per sampling point (site + station + transect; 405 total).
Properties: `site`, `station`, `transect`, `elevation_m`, `has_mosquito_traps` (true/false), `has_bird_counts` (true/false)

**`sites.geojson`**: Point features, one per site (the centroid of its stations).
Properties: `site`, `site_name` (from the XML metadata, or `null` if not found), `elevation_m` (mean of stations), `elevation_min_m`, `elevation_max_m`, `n_stations`

**`site_summary.json`**: Measures per site per time period.
```json
[
  {
    "site": "COO",
    "period": "2002-dry",
    "mosquito_per_trap_night": 1.4,      "mosquito_trap_nights": 52,
    "mosq_midgut_pct": 4.2,              "mosq_midgut_n": 95,
    "mosq_salivary_pct": 1.1,            "mosq_salivary_n": 93,
    "bird_prevalence_pct": 22.0,         "bird_sampled_n": 41,
    "honeycreeper_prevalence_pct": 18.5, "honeycreeper_sampled_n": 27,
    "honeycreepers_per_count": 3.1,      "nonnative_birds_per_count": 5.2,   "bird_counts_n": 30
  }
]
```

| Field | Definition |
|---|---|
| `site` | Site code, one of the nine in `sites.geojson`. |
| `period` | One of eight values. Five Hawaiian seasons (wet Nov–Apr, dry May–Oct; wet seasons labeled by start year, so `2002-wet` = Nov 2002–Apr 2003): `2002-dry`, `2002-wet`, `2003-dry`, `2003-wet`, `2004-dry`. Three combined periods: `all` (all five seasons together), `dry` (the three dry seasons), `wet` (the two wet seasons). Samples from Jan–Apr 2002 and Nov–Dec 2004 are dropped from every period, including the combined ones. |
| `mosquito_per_trap_night` | *Culex* caught in CO2 traps ÷ `mosquito_trap_nights`. Uses the `culex` column only (the only malaria vector). Gravid traps are not used for abundance. |
| `mosquito_trap_nights` | CO2 trap rows in the mosquito capture file for this site-period (one row = one trap set for one night). |
| `mosq_midgut_pct` | % of dissected *Culex* with `midgut_infection` = yes. Period assigned by `date_collected`. |
| `mosq_midgut_n` | Dissected mosquitoes with a recorded `midgut_infection`. Blank = not examined, excluded. |
| `mosq_salivary_pct` | % of dissected *Culex* with `salivary_infection` = yes. Period assigned by `date_collected`. |
| `mosq_salivary_n` | Dissected mosquitoes with a recorded `salivary_infection`. Blank = not examined, excluded. |
| `bird_prevalence_pct` | % of sampled birds (all species) infected, from `INFECTION_STATUS`. |
| `bird_sampled_n` | Unique birds (`BANDNUMBER`) sampled in this site-period, counting each bird once. A bird is a unique site + period + band number + species; unbanded (`NB`) rows count as one bird each. A bird with several results in the period is positive if any is `P`, negative if any is `N` and none `P`, and excluded if all are `U` (see data_notes.md). |
| `honeycreeper_prevalence_pct` | Same as `bird_prevalence_pct`, restricted to species with `honeycreeper = true` in `species_lookup.csv`. |
| `honeycreeper_sampled_n` | Same as `bird_sampled_n`, restricted to honeycreepers. |
| `honeycreepers_per_count` | Honeycreeper detections ÷ `bird_counts_n`. This is the app's "native bird abundance" measure. Native non-honeycreepers (ʻŌmaʻo, ʻElepaio, ʻIo) are in neither abundance field. |
| `nonnative_birds_per_count` | Detections of species with `native = false` ÷ `bird_counts_n`. |
| `bird_counts_n` | Counting events: unique site + station + transect + date in the bird count file. Stations 100, 300, 500, 700, 900 only (station 200 rows dropped). Events recorded as `NOBI` (no birds detected) are included. |

Rules:
- Missing data is `null`, never `0`. A measure is `null` when its sample size is 0. A true zero (counts or dissections done, nothing found) is `0`.
- Every percentage has its own sample size next to it.
- Percentages (`mosq_midgut_pct`, `mosq_salivary_pct`, `bird_prevalence_pct`, `honeycreeper_prevalence_pct`) are `null` when their sample size is below 20. The sample size is still filled in, and the app shows "too few samples".
- Abundance measures (`mosquito_per_trap_night`, `honeycreepers_per_count`, `nonnative_birds_per_count`) are shown whenever their sample size is above 0.
- Species are matched through `canonical_code` in `species_lookup.csv`, never the raw code.

**`landcover.geojson`** (or `.pmtiles` if too large): simplified polygons clipped to Hawaiʻi Island.
Property: `class` (one of a small set, e.g. `wet_forest`, `dry_forest`, `shrub_grass`, `bare_lava`, `developed_ag`), plus `native_status` if using Habitat Status.

**`malaria_zones.geojson`**: polygons clipped to Hawaiʻi Island.
Property: `zone` = `high_risk` (>21°C), `episodic` (13–21°C), `refuge` (<13°C).

**`species_lookup.csv`** (in `data-pipeline/`): one row per species code found in either bird file.
Columns: `code`, `canonical_code` (one code per species, merging codes for the same bird across files), `common_name`, `scientific_name`, `native` (true/false), `honeycreeper` (true/false), `in_counts` (true/false), `in_blood` (true/false), `count_guild` (the bird count file's `guild` value, blank if none), `notes` (`CHECK` marks rows needing review).
`NOBI` ("no birds detected") is included with blank `canonical_code`, `native` and `honeycreeper`: it is a zero-detection count, not a species.

---

# Phase 0: Project setup

### Step 0.1: Create the repository and app skeleton
**Goal:** an empty React + Vite app that runs, with the folder structure above.

**Prompt:**
> Read PLAN.md. Do Step 0.1 only. Create a React + Vite project in this repository using the folder structure in PLAN.md. Add a README.md explaining how a teammate installs and runs the app (`npm install`, `npm run dev`) and how to set up the Python environment for `data-pipeline/`. Create `data-pipeline/requirements.txt` with pandas, geopandas, pyproj, rasterio, shapely. Add a `.gitignore` that ignores `node_modules`, Python virtual environments, and large raw data files in `data-pipeline/raw/` (but keeps a `README` listing what goes there). The app should show only a page title for now.

**Done when:**
- [ ] `npm run dev` shows the page title in the browser
- [ ] Python environment installs from `requirements.txt` without errors
- [ ] Folder structure matches PLAN.md

---

# Phase 1: Data pipeline (Python)

Each script reads from `raw/`, writes to `public/data/` or `reports/`, and can be rerun safely.

### Step 1.1: Inspect the raw data
**Goal:** a written report of what's actually in each file before any processing.

**Prompt:**
> Read PLAN.md. Do Step 1.1 only. Write `data-pipeline/scripts/01_inspect.py`. For each CSV in `raw/biocomplexity_2001_2004/` and `raw/bird_malaria_2001_2005/`, report: column names and types, row count, unique values of site or location columns, min/max dates, count of nulls per column, and the first five rows. Also list unique species values in each file. Write the output to `data-pipeline/reports/inspection.md`. Do not transform any data.

**Done when:**
- [ ] `reports/inspection.md` exists
- [ ] **You** review it and confirm: site codes match across files (e.g. `site` in Biocomplexity files = `LOCATION` in the bird blood file), coordinate columns look like lat/long, date formats are readable
- [ ] Note any surprises in the report before Step 1.2

### Step 1.2: Stations and sites
**Goal:** map-ready station and site points.

**Prompt:**
> Read PLAN.md and data-pipeline/reports/data_notes.md. Do Step 1.2 only. Write `scripts/02_sites.py`. The sampling station spatial coordinates CSV is already in WGS84 decimal degrees (`x_long`, `y_lat`), so no coordinate conversion is needed.
>
> 1. Create `public/data/stations.geojson` with one point per site + station + transect (405 points). Properties: `site`, `station`, `transect`, `elevation_m`, plus `has_mosquito_traps` and `has_bird_counts` (true/false), based on whether that site + station + transect appears in the mosquito capture file and the bird count file.
> 2. Check the bird count rows at station 200 (25 rows): which sites, transects, and dates they come from, and whether they look like data entry errors. Write findings to `reports/station200_check.md`. Do not change or drop them yet.
> 3. Look in the two XML metadata files for full site names matching the nine site codes.
> 4. Create `public/data/sites.geojson` with one point per site at the mean of its stations' coordinates. Properties: `site`, `site_name` (from the metadata, or null if not found), `elevation_m` (mean), `elevation_min_m`, `elevation_max_m`, `n_stations`.
> 5. Print a table of sites sorted by mean elevation.
>
> Update the Data contract in PLAN.md to include the new properties.

**Done when:**
- [ ] `stations.geojson` has 405 points and `sites.geojson` has 9, both on Hawaiʻi Island's east side in https://geojson.io
- [ ] Site elevations roughly 25–1,800 m
- [ ] `has_bird_counts` is true only at stations 100, 300, 500, 700, 900 (plus wherever the station 200 rows fall)
- [ ] `reports/station200_check.md` exists. **You** decide what to do with those rows and record it in data_notes.md
- [ ] Site names filled in, or noted as not found

### Step 1.3: Species lookup
**Goal:** one table that defines every species code in both bird files, merges codes that mean the same bird, and marks native vs. non-native and honeycreeper species.

**Prompt:**
> Read PLAN.md and data-pipeline/reports/data_notes.md. Do Step 1.3 only. Write `scripts/03_species.py` that builds `data-pipeline/species_lookup.csv` covering every species code in the bird count file (`alphacode`) and the bird blood file (`SPECIES`).
>
> 1. Look up each code's meaning in the two XML metadata files first. Only use outside knowledge when a code isn't defined there, and say so in the notes.
> 2. Columns: `code`, `canonical_code`, `common_name`, `scientific_name`, `native` (true/false), `honeycreeper` (true/false), `in_counts` (true/false), `in_blood` (true/false), `count_guild` (the `guild` value from the bird count file, if any), `notes`.
> 3. `canonical_code` merges codes for the same species across files. Known candidates from data_notes.md: JAWE/WAWE (white-eye), AKIP/AKIA (ʻAkiapōlāʻau). HWAH, HWAM, and HAWH are unresolved: merge them only if the metadata confirms they are the same species.
> 4. Report the three `guild` values and what they mean (from the metadata), and flag any species where `guild` disagrees with the `native` column.
> 5. Mark anything uncertain with `CHECK` in `notes` rather than guessing.
> 6. Write a short summary to `reports/species_check.md`: merged codes, unresolved codes, guild meanings, and any disagreements.
>
> Update the `species_lookup.csv` entry in the Data contract in PLAN.md to match the new columns.

**Done when:**
- [ ] Every code from both files appears in the lookup (23 from counts, 20 from blood, with overlaps)
- [ ] JAWE/WAWE and AKIP/AKIA resolved, with the source of the decision noted
- [ ] HWAH/HWAM/HAWH either resolved from the metadata or marked `CHECK`
- [ ] Guild meanings reported, with no unexplained disagreements with `native`
- [ ] **You** review rows marked `CHECK` and record decisions in data_notes.md

### Step 1.4: Choose time periods
**Goal:** decide the time periods the season buttons will step through and the start date, based on how much usable data each site has per period. Also set the minimum sample sizes.

**Prompt:**
> Read PLAN.md and data-pipeline/reports/data_notes.md. Do Step 1.4 only. Write `scripts/04_coverage.py`. Apply the rules in data_notes.md so the counts match what Step 1.5 will actually use:
> - Mosquito captures: count trap nights (one trap on one night), using the `culex` column.
> - Mosquito dissections: count examined mosquitoes only (exclude blank `midgut_infection` / `salivary_infection`), dated by `date_collected`.
> - Bird blood samples: count unique birds (`BANDNUMBER`) per period with a determined `INFECTION_STATUS`. Report all birds and honeycreepers separately.
> - Bird counts: count counting events (site + station + transect + date), including NOBI events and excluding station 200.
> - Parse each file's dates with its own format. Trim everything after 2004-12-31.
>
> For each dataset, count samples per site for each of these period options:
> 1. Month
> 2. Hawaiian season: wet (Nov–Apr) and dry (May–Oct). Label wet seasons by start year, e.g. `2002-wet` = Nov 2002–Apr 2003.
> 3. Four seasons (Dec–Feb, Mar–May, Jun–Aug, Sep–Nov). Assign December to the following year's Dec–Feb season.
> 4. Year
>
> For each option, report the % of site-period cells with at least 10, 20, and 30 samples, and list cells with zero samples. Show results twice: starting 2001, and starting 2002.
>
> Write everything to `reports/coverage.md`, ending with a recommendation for: (a) the period option, (b) the start date, (c) a minimum sample size for showing a percentage. Do not choose for me; present the recommendation and the trade-offs.

**Done when:**
- [ ] `reports/coverage.md` exists with tables for all four datasets and all four period options
- [ ] **You** decide the period option, start date, and minimum sample sizes
- [ ] Decisions recorded in the Decisions log in PLAN.md and in data_notes.md
- [ ] Data contract's `period` format updated to match the chosen option

### Step 1.5: Site summaries
**Goal:** the main data file the app reads: one record per site per period, every value with its sample size.

**Prompt:**
> Read PLAN.md and data-pipeline/reports/data_notes.md. Do Step 1.5 only. Write `scripts/05_site_summary.py` that produces `public/data/site_summary.json` exactly as described in the Data contract, and `reports/site_summary_check.md`.
>
> **Periods.** Assign every sample to a Hawaiian season by its date (wet Nov–Apr, dry May–Oct; `2002-wet` = Nov 2002–Apr 2003). Keep only May 2002–Oct 2004, the five full seasons. Build `all`, `dry` and `wet` by pooling the underlying samples, not by averaging seasonal values. Output one record per site per period (9 sites × 8 periods = 72), sorted by site elevation and then period (`2002-dry` … `2004-dry`, `all`, `dry`, `wet`). Every record has every contract field.
>
> **Mosquito abundance.** CO2 trap rows only. `mosquito_trap_nights` = CO2 rows; `mosquito_per_trap_night` = sum of `culex` ÷ trap nights. Count each row as a trap night, including the 72 repeated rows.
>
> **Mosquito infection.** Every dissected mosquito, whatever trap caught it, dated by `date_collected`. Midgut and salivary are computed separately, each over the mosquitoes with a recorded (non-blank) result for that test.
>
> **Bird prevalence.** From the bird blood file. A bird is a unique site + period + `BANDNUMBER` + `canonical_code`; each `NB` row is its own bird. Combine a bird's results within the period: any `P` → positive; else any `N` → negative; all `U` → excluded. In combined periods, a bird sampled in several seasons counts once. Honeycreeper fields use `honeycreeper = true` in `species_lookup.csv`, matched through `canonical_code`.
>
> **Bird abundance.** From the bird count file, read with `keep_default_na=False` so guild `NA` stays text. Drop station 200. A counting event is a unique site + station + transect + date, NOBI events included. Detections are rows, excluding NOBI. `honeycreepers_per_count` = honeycreeper detections ÷ events; `nonnative_birds_per_count` = `native = false` detections ÷ events. Native non-honeycreepers are in neither.
>
> **Nulls and rounding.** Apply the Data contract rules: percentages `null` below 20 samples (sample size still filled in), abundance `null` only when its sample size is 0, a true zero stays `0`. Round percentages to 1 decimal, per-count values to 2, per-trap-night values to 3. Before writing, assert the contract holds: 72 records, exact field set, every percentage `null` exactly when its n < 20.
>
> **Check report** (`reports/site_summary_check.md`):
> 1. Per-site raw totals for `all`: Culex caught, CO2 trap nights, mosquitoes examined and infected (midgut, salivary), birds sampled and positive (all, honeycreepers), counting events, honeycreeper and non-native detections.
> 2. Sum checks: for trap nights, mosquitoes examined and counting events, the five seasons add up to `all`, and `dry` + `wet` = `all`. (Bird sample sizes don't have to add up, since a bird can appear in more than one season.)
> 3. Every cell where a percentage is `null` because n < 20, by site and period.
> 4. Whether the Known gaps in data_notes.md still hold (SOL, CJR mosquito infection; WAI honeycreeper prevalence). Flag any difference.
>
> Do not change data_notes.md or the Data contract. If something in the data contradicts them, report it in the check file instead.

**Done when:**
- [ ] `site_summary.json` has 72 records with exactly the contract's fields, and the script's contract checks pass
- [ ] Sum checks in `site_summary_check.md` pass
- [ ] Known gaps match data_notes.md, or differences are explained
- [ ] **You** review the per-site table for plausibility: *Culex* near zero at CJR and SOL and highest at the mid-elevation sites (PUU, WAI, COO), matching `reports/coverage.md`

---

# Phase 2: The base map

### Step 2.1: Flat map of Hawaiʻi Island
**Prompt:**
> Read PLAN.md. Do Step 2.1 only. Add MapLibre GL JS. Create a `Map` component showing Hawaiʻi Island that fills the whole browser window (full width and height, no scrollbars), using a free basemap style that needs no API key (e.g. OpenFreeMap). Include navigation controls. The map should resize correctly when the browser window is resized.

**Done when:**
- [ ] Map fills the entire window, with no scrollbars or gaps
- [ ] Map loads centered on Hawaiʻi Island, pans and zooms
- [ ] Map resizes correctly when the window is resized

### Step 2.2: 3D terrain
**Prompt:**
> Read PLAN.md. Do Step 2.2 only. Add 3D terrain from the free AWS Terrain Tiles (`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`, `encoding: "terrarium"`, tileSize 256, maxzoom 15) as a raster-dem source, added after the basemap style loads. Add a hillshade layer from the same data, placed above the basemap's land layers but below its roads and labels; record that insertion layer in `src/config/map.js` so later draped layers (land cover, malaria zones) use it too. Add the terrain data's attribution.
>
> Set terrain exaggeration to about 3× so the 28–1,836 m study gradient stands out clearly. Make the hillshade pronounced (darker shadows, light highlights), and add a semi-transparent elevation color tint (`color-relief` layer from the same terrain data) below the hillshade, with most of its color change in 0–2,000 m where the sites are (green lowlands → tan/brown uplands → grey/white summits). Allow the camera to tilt to about 80°. Set the starting camera from `sites.geojson`: centered on the nine sites, pitched about 60°, looking upslope roughly west so the low sites are in the foreground and Mauna Loa rises behind the high sites. Leave right-side padding for the side panel (Step 2.4). Put exaggeration, hillshade, tint, tilt, camera, and padding settings in `src/config/map.js`. Terrain is visual only: any elevation shown to users comes from the data, not the terrain.

**Done when:**
- [ ] Mountains appear in 3D and you can tilt (to about 80°) and rotate
- [ ] Elevation differences are easy to see: low, mid, and high sites fall on clearly different tint colors
- [ ] The starting view shows all nine site locations, looking upslope from the ocean side, clear of the side panel's area
- [ ] Hillshade sits under roads and labels; place names stay readable
- [ ] Terrain attribution is shown
- [ ] Performance is acceptable on a normal laptop

### Step 2.3: Sites and stations
**Prompt:**
> Read PLAN.md. Do Step 2.3 only. Add `stations.geojson` and `sites.geojson` as GeoJSON sources with MapLibre layers (not HTML markers), so later steps can restyle and animate the site markers from data (Steps 4.1, 4.2, 5.3). Load `sites.geojson` once and reuse it for the starting camera from Step 2.2. Add these layers on top of all basemap layers.
>
> - Stations: small, semi-transparent grey circles with a thin white outline, shown from about zoom 11 so they don't crowd the starting view.
> - Sites: larger circles with a white outline, plus a label with the site code (white text halo so it stays readable over the elevation tint and hillshade).
> - Clicking a site opens a popup with its code, full `site_name`, mean elevation with its range (e.g. "1,786 m (1,742–1,836 m)"), and "45 sampling points (9 stations × 5 transects)". All values come from `sites.geojson`. Show a pointer cursor when hovering over a site.
>
> Put marker sizes, colors, and the station zoom threshold in `src/config/map.js`.

**Done when:**
- [ ] All nine sites appear as labeled circles in the starting view, sitting on the terrain at the right places
- [ ] Stations appear when zoomed in to a site and sit on the terrain along their transects
- [ ] Site labels and markers stay readable over the elevation tint and hillshade
- [ ] Popups show the correct name, elevation, elevation range, and sampling points for each site
- [ ] Sanity check: low sites (MAL, NAN, BRY) sit on green tint, high sites (CJR, SOL) on tan/brown

### Step 2.4: Collapsible side panel
**Goal:** a side panel for controls, legends, and info that users can open and close, so the map can use the full screen when the panel isn't needed.

**Prompt:**
> Read PLAN.md. Do Step 2.4 only. Add a `SidePanel` component on the right side of the screen that slides over the full-screen map. It should:
> - open and close with a clearly visible toggle button (e.g. a tab on the panel's edge), with a smooth slide animation;
> - be about 350px wide on desktop when open, and resizable by dragging its left edge (minimum ~280px, maximum ~50% of the window);
> - remember whether it was open or closed and its width while the page is open;
> - start open, with placeholder text for now;
> - on screens narrower than 768px, become a bottom sheet that slides up instead.
>
> The map stays full screen underneath. When the panel opens or closes, keep the map's navigation controls visible and not hidden behind the panel. Respect reduced-motion preferences by opening and closing instantly instead of sliding.

**Done when:**
- [ ] Panel opens and closes smoothly with the toggle button
- [ ] Panel can be resized by dragging its edge, within the min and max widths
- [ ] Map stays usable and full screen underneath; navigation controls are never hidden
- [ ] On a narrow window, the panel becomes a bottom sheet

---

# Phase 3: Environment layers

### Step 3.1: Process land cover
**Prompt:**
> Read PLAN.md. Do Step 3.1 only. Write `scripts/05_landcover.py`. From the Carbon Assessment of Hawaiʻi land cover raster, clip to Hawaiʻi Island, regroup classes into the small set in the Data contract (document the mapping in the script), convert to polygons, simplify geometry so the output is under ~5 MB, and save `public/data/landcover.geojson`. If it can't get under ~5 MB without losing the shape, save PMTiles instead and explain how to load it.

**Done when:**
- [ ] File is a reasonable size and looks right in geojson.io (forest belts on the windward slopes, bare areas near the summits)

### Step 3.2: Show land cover
**Prompt:**
> Read PLAN.md. Do Step 3.2 only. Add the land cover layer draped on the terrain with semi-transparent fills, a legend, and an on/off toggle in the right panel. Put colors in `src/config/colors.js`.

**Done when:**
- [ ] Layer drapes correctly on the 3D terrain and toggles on and off

### Step 3.3: Process malaria zones
**Prompt:**
> Read PLAN.md. Do Step 3.3 only. Write `scripts/06_malaria_zones.py`. Using the Climate of Hawaiʻi air temperature raster (use summer months if monthly layers exist, otherwise mean annual, and note which in the script), clip to Hawaiʻi Island and classify into three zones: `high_risk` (>21°C), `episodic` (13–21°C), `refuge` (<13°C), based on LaPointe et al. 2010. Convert to simplified polygons and save `public/data/malaria_zones.geojson`. Print the area in km² of each zone, and the area of refuge zone that overlaps forest classes from the land cover data.

**Done when:**
- [ ] Refuge zone sits at high elevation on the mountains
- [ ] Area numbers are printed and recorded in the Decisions log

### Step 3.4: Show malaria zones
**Prompt:**
> Read PLAN.md. Do Step 3.4 only. Add the malaria zones as a semi-transparent tint on the terrain (warm colors for risk, cool for refuge) with softened edges, a legend, and a toggle. Show the "safe forest remaining" area figure in the right panel. Add a short note that zones are modeled from temperature.

**Done when:**
- [ ] Zones and land cover can be shown together or separately
- [ ] Site markers remain visible on top

---

# Phase 4: Site data on the map

### Step 4.1: Layer selector
**Prompt:**
> Read PLAN.md. Do Step 4.1 only. Load `site_summary.json`. Add a selector in the right panel with four measures: mosquito abundance, infectious mosquitoes (% salivary), bird malaria prevalence, native bird abundance. Color and size site markers by the selected measure, aggregated across all periods for now. Show sample size in each site's popup. Sites with no data for a measure appear as grey outlines, not zero.

**Done when:**
- [ ] Switching measures updates markers correctly
- [ ] No-data sites are visually distinct

### Step 4.2: Season buttons
**Goal:** let users switch between the five survey seasons, plus combined views, with smooth animated transitions.

**Prompt:**
> Read PLAN.md. Do Step 4.2 only. Add a row of season buttons along the bottom of the map, in time order: Dry 2002, Wet 2002–03, Dry 2003, Wet 2003–04, Dry 2004 (matching the `period` values in site_summary.json). Also add:
> - an "All seasons" button (period `all`), selected by default;
> - a "Wet vs. Dry" toggle that switches between the combined `wet` and `dry` periods;
> - a play button that steps through the five seasons in order, pausing about 2 seconds on each, with a pause/stop control.
>
> When a button is pressed, site markers animate smoothly (size and color) from their current values to the new period's values rather than jumping. The selected button is clearly highlighted, and a label shows the season's months (e.g. "Wet season: Nov 2003 – Apr 2004").
>
> Site-periods with no data show as grey outlines. Percentages below the minimum sample size show "too few samples" in the popup; SOL and CJR mosquito infection shows "too few mosquitoes to test." Respect reduced-motion preferences by switching instantly instead of animating.

**Done when:**
- [ ] Each button shows the right period's values, and markers animate between them
- [ ] "All seasons" is selected on load
- [ ] Wet vs. Dry toggle switches between the two combined views
- [ ] Play steps through all five seasons and can be paused
- [ ] No-data and too-few-samples cases display correctly

---

# Phase 5: Flat comparison view

### Step 5.1: Flat bar chart
**Prompt:**
> Read PLAN.md. Do Step 5.1 only. Create a `FlatChart` component with D3: one bar per site for the selected measure and period, sorted by elevation, with light background bands for elevation zones, bar labels showing site, elevation, and sample size, and no-data sites shown as empty outlines. Same measure selector and season buttons as the map.

**Done when:**
- [ ] Chart matches the map for the same measure and period

### Step 5.2: Terrain / flat toggle
**Prompt:**
> Read PLAN.md. Do Step 5.2 only. Add a "Terrain / Flat" toggle that switches the main view between the 3D map and `FlatChart` with a simple crossfade. Measure and period selections carry over between views.

**Done when:**
- [ ] Switching keeps selections and works both ways

### Step 5.3 (optional): Animated morph
**Prompt:**
> Read PLAN.md. Do Step 5.3 only. Replace the crossfade with an animation where each site's marker moves from its screen position on the map into its bar position in the flat chart, and back. Keep the crossfade as a fallback if reduced motion is preferred.

---

# Phase 6: Scroll story

### Step 6.1: Story layout and chapter config
**Prompt:**
> Read PLAN.md. Do Step 6.1 only. Add Scrollama. Create a layout where story text scrolls in a column while the map stays fixed. Define chapters in `src/config/chapters.js`, each with: title, text, camera (center, zoom, pitch, bearing), visible layers, selected measure, and period. Create three placeholder chapters to test that scrolling moves the camera and switches layers.

**Done when:**
- [ ] Scrolling triggers smooth camera moves and layer changes

### Step 6.2: Write the core chapters
Suggested chapters (edit the text yourself):
1. **The mountain:** terrain only, wide view of the island.
2. **Where the forest is:** land cover on.
3. **Where malaria can spread:** malaria zones on; explain the temperature limits.
4. **The refuge:** highlight refuge zone overlapping forest; show remaining area.
5. **Evidence from the field:** sites on; mosquito abundance, then infectious mosquitoes.
6. **The birds:** bird prevalence, then native bird abundance.
7. **Compare directly:** switch to flat view.
8. **Explore:** hand full control to the user.

**Prompt:**
> Read PLAN.md. Do Step 6.2 only. Replace the placeholder chapters with the eight chapters listed in PLAN.md Step 6.2, using the camera positions and layer settings that best show each point. Use placeholder text I will edit later. In the final chapter, unlock all controls.

---

# Phase 7: Polish and deploy

### Step 7.1: Mobile and accessibility
**Prompt:**
> Read PLAN.md. Do Step 7.1 only. Make the layout work on phones: the side panel becomes a bottom sheet, story text overlays the map. Respect reduced-motion preferences. Make sure controls are keyboard accessible, colors pass contrast checks, and color is never the only way information is shown.

### Step 7.2: Data sources and credits
**Prompt:**
> Read PLAN.md. Do Step 7.2 only. Add an "About the data" panel listing every dataset with citation and link, the temperature thresholds and their source, and caveats: zones are modeled; prevalence reflects surviving birds only; site data covers 2001–2005.

### Step 7.3: Deploy
**Prompt:**
> Read PLAN.md. Do Step 7.3 only. Set up deployment to GitHub Pages with a GitHub Actions workflow that builds the Vite app on every push to `main`. Configure the Vite base path for the repository name. Update README.md with the live link and how teammates deploy.

**Done when:**
- [ ] Public link works for teammates

---

# Later phases (after the core story works)

- **Future chapter:** Fortini et al. 2015 species range projections (range lost / kept / gained per species) with a species picker; climate scenario toggle using the 2098–2100 risk projections.
- **Self-hosted terrain:** generate terrain tiles from the USGS 10 m DEM for higher accuracy.
- **Temperature over time:** daily 250 m temperature maps (1990–2021) to show the 13°C line moving.
- **Explore mode upgrades:** filters plus the linked summary panel.
- **Additional context:** statewide 2018–2021 prevalence data as an opening overview, Hakalau refuge bird trends.

---

## Decisions log

Record choices here as you make them so every session and teammate stays in sync.

| Date | Decision | Reason |
|---|---|---|
| | Stack: React + Vite, MapLibre GL, D3, Python pipeline, GitHub Pages | Free, shareable, no API keys |
| | Scope: core story first | Build incrementally |
| 2026-11-04 | Time period: Hawaiian season (wet Nov–Apr, dry May–Oct) | Every site-season gets two bird count rounds, and it has the most samples per cell short of whole years (`reports/coverage.md`) |
| 2026-11-04 | Start date: 2002, five full seasons only (`2002-dry` to `2004-dry`); Jan–Apr 2002 and Nov–Dec 2004 dropped | Mosquito trapping and bird counts start in early 2002, and partial seasons aren't comparable to full ones |
| 2026-11-04 | Minimum sample size: 20 for percentages only; below 20 the value is `null` and the app shows "too few samples". Abundance shown whenever n > 0 | At n = 20 one sample moves a percentage by 5 points; abundance doesn't swing the same way |
| 2026-11-04 | Mosquito abundance uses CO2 traps only; gravid traps are ignored for abundance. Infection uses all dissected mosquitoes | CO2 traps catch host-seeking females (the ones that bite birds) at ~4.5× the gravid rate, and the gravid/CO2 ratio varies a lot by site, so pooling would mix two methods |
| 2026-11-04 | Mosquito infection keeps both trap types (reviewed after Step 1.5) | Keeps sample sizes up (CO2-only would blank CJR entirely and most CRA seasons). Trap-mix caveat, which inflates CRA, goes in the About panel; see data_notes.md |
| 2026-11-04 | Time steps in the app are season buttons: one per season plus `all`, `wet` and `dry` | Five seasons plus three combined periods suit a small set of labeled buttons |
| | Malaria zone temperature source: _(Step 3.3)_ | |
| | Refuge area figures: _(Step 3.3)_ | |
