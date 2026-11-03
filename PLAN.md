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
    ├── components/          ← Map, LayerControls, TimeSlider, FlatChart, Story...
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

**`stations.geojson`**: Point features, one per sampling station.
Properties: `site`, `station`, `transect`, `elevation_m`

**`sites.geojson`**: Point features, one per site (the centroid of its stations).
Properties: `site`, `site_name` (if known), `elevation_m` (mean of stations), `n_stations`

**`site_summary.json`**: Measures per site per time period.
```json
[
  {
    "site": "COO",
    "period": "2002-Summer",
    "mosquito_per_trap_night": 1.4,   "mosquito_trap_nights": 52,
    "mosq_midgut_pct": 4.2,           "mosq_salivary_pct": 1.1,   "mosq_dissected_n": 95,
    "bird_prevalence_pct": 22.0,      "bird_sampled_n": 41,
    "native_birds_per_count": 3.1,    "nonnative_birds_per_count": 5.2,   "bird_counts_n": 30
  }
]
```
Missing data is `null`, never `0`. Every percentage has its sample size next to it.

**`landcover.geojson`** (or `.pmtiles` if too large): simplified polygons clipped to Hawaiʻi Island.
Property: `class` (one of a small set, e.g. `wet_forest`, `dry_forest`, `shrub_grass`, `bare_lava`, `developed_ag`), plus `native_status` if using Habitat Status.

**`malaria_zones.geojson`**: polygons clipped to Hawaiʻi Island.
Property: `zone` = `high_risk` (>21°C), `episodic` (13–21°C), `refuge` (<13°C).

**`species_lookup.csv`** (in `data-pipeline/`): `code`, `common_name`, `scientific_name`, `native` (true/false), `honeycreeper` (true/false).

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
> Read PLAN.md. Do Step 1.2 only. Write `scripts/02_sites.py`. From the sampling station spatial coordinates CSV, create `public/data/stations.geojson` with the properties in the Data contract. Confirm the coordinates are WGS84 lat/long; if they are UTM, convert from UTM Zone 5N. Then create `public/data/sites.geojson` with one point per site at the mean of its stations' coordinates, with mean elevation and station count. Print a table of sites sorted by elevation.

**Done when:**
- [ ] Both files exist and open in https://geojson.io with points on Hawaiʻi Island's east side
- [ ] Nine sites (or however many the inspection found), elevations roughly 25–1,800 m

### Step 1.3: Species lookup
**Goal:** a table marking native vs. non-native and honeycreeper species.

**Prompt:**
> Read PLAN.md. Do Step 1.3 only. Using the unique species values from `reports/inspection.md`, create `data-pipeline/species_lookup.csv` with the columns in the Data contract. Fill in common and scientific names and whether each species is native to Hawaiʻi and whether it is a Hawaiian honeycreeper. Mark anything you are unsure about with `CHECK` in a notes column rather than guessing.

**Done when:**
- [ ] Every species code in the data appears in the lookup
- [ ] **You** review rows marked `CHECK`

### Step 1.4: Choose time periods
**Goal:** decide whether the slider uses months, seasons, or years, based on how much data each period has.

**Prompt:**
> Read PLAN.md. Do Step 1.4 only. Write `scripts/03_coverage.py`. For each dataset (mosquito captures, mosquito dissections, bird blood samples, bird counts), count samples per site per month, per season (define seasons as Dec–Feb, Mar–May, Jun–Aug, Sep–Nov), and per year. Write the tables to `reports/coverage.md` and recommend the finest time period where most site-period cells have at least 10 samples. Do not choose for me; present the recommendation.

**Done when:**
- [ ] **You** pick the time period and record it in PLAN.md under "Decisions log" at the bottom

### Step 1.5: Site summaries
**Goal:** the main data file the app reads.

**Prompt:**
> Read PLAN.md. Do Step 1.5 only. Write `scripts/04_site_summary.py` producing `public/data/site_summary.json` exactly as described in the Data contract, using the time period in the Decisions log. Mosquito abundance = mosquitoes caught per trap night. Mosquito infection = % of dissected mosquitoes with midgut infection and % with salivary infection. Bird prevalence = % of birds positive, counting each band number once per period. Bird counts split native vs. non-native using `species_lookup.csv`. Use `null` for site-periods with no data. Also write `reports/site_summary_check.md` with per-site totals across all periods.

**Done when:**
- [ ] JSON matches the contract
- [ ] Overall pattern looks plausible: more mosquitoes and infection at low elevation, less at high
- [ ] No percentages without a matching sample size

---

# Phase 2: The base map

### Step 2.1: Flat map of Hawaiʻi Island
**Prompt:**
> Read PLAN.md. Do Step 2.1 only. Add MapLibre GL JS. Create a `Map` component showing Hawaiʻi Island, filling the left ~65% of the screen, using a free basemap style that needs no API key (e.g. OpenFreeMap). Include navigation controls. The right ~35% is an empty panel for now.

**Done when:**
- [ ] Map loads centered on Hawaiʻi Island, pans and zooms

### Step 2.2: 3D terrain
**Prompt:**
> Read PLAN.md. Do Step 2.2 only. Add 3D terrain using the free AWS Terrain Tiles (Terrarium encoding) as a raster-dem source, with a hillshade layer. Set a moderate terrain exaggeration and start the camera pitched and angled toward the east flank of Mauna Loa and Kīlauea. Put exaggeration and camera settings in `src/config/map.js`.

**Done when:**
- [ ] Mountains appear in 3D and you can tilt and rotate
- [ ] Performance is acceptable on a normal laptop

### Step 2.3: Sites and stations
**Prompt:**
> Read PLAN.md. Do Step 2.3 only. Load `stations.geojson` as small grey dots and `sites.geojson` as larger labeled markers. Clicking a site opens a popup with its code, elevation, and number of stations.

**Done when:**
- [ ] Points sit on the terrain in the right places
- [ ] Popups show correct values

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

### Step 4.2: Time slider
**Prompt:**
> Read PLAN.md. Do Step 4.2 only. Add a time slider along the bottom of the map using the periods in `site_summary.json`, plus an "All periods" option and a play button. Markers update for the selected period. No-data site-periods show as grey outlines.

**Done when:**
- [ ] Slider steps through periods and markers update
- [ ] Play/pause works

---

# Phase 5: Flat comparison view

### Step 5.1: Flat bar chart
**Prompt:**
> Read PLAN.md. Do Step 5.1 only. Create a `FlatChart` component with D3: one bar per site for the selected measure and period, sorted by elevation, with light background bands for elevation zones, bar labels showing site, elevation, and sample size, and no-data sites shown as empty outlines. Same measure selector and time slider as the map.

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
| | Time period for slider: _(Step 1.4)_ | |
| | Malaria zone temperature source: _(Step 3.3)_ | |
| | Refuge area figures: _(Step 3.3)_ | |
