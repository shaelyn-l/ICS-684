# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Hawaiʻi Island avian malaria story map (ICS 684 final project): a React web app with a 3D terrain map, environmental layers, field data from study sites, and a flat comparison chart.

## PLAN.md is the build plan

`PLAN.md` is the build plan for this project. Read it before any work. We work through it **one step at a time**: each session the user names a single step ("Do Step X.Y only"), and that step's prompt and "Done when" list define the whole task. The user checks and commits each step before the next one starts.

### Ground rules for Claude Code (from PLAN.md)

- Do **only** the current step. Don't start later steps or refactor unrelated files.
- Don't change the data file formats in `public/data/` without updating the **Data contract** section of this plan.
- Keep dependencies free and open source. No API keys or paid services.
- Explain any new dependency before adding it.
- When a step is finished, summarize what changed and how to test it.
- Before any data-pipeline step, read data-pipeline/reports/data_notes.md for known data issues and decisions.

Also record choices the user makes (time period, temperature source, area figures) in the **Decisions log** at the bottom of `PLAN.md`.

## Commands

```bash
npm install
npm run dev       # Vite dev server, http://localhost:5173
npm run build     # production build to dist/
npm run preview   # serve the build
```

There are no tests or linter yet.

Python data pipeline (Python 3.13 works; there's a git-ignored venv at `data-pipeline/.venv`):

```bash
cd data-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The local Node is 20.17, which is why Vite is pinned to 6.x: Vite 7 needs Node 20.19 or later.

## Architecture

There are two separate halves, joined only by the files in `public/data/`:

1. **`data-pipeline/`**: offline Python scripts (pandas, geopandas, pyproj, rasterio, shapely), run locally and never shipped. They're numbered in run order (`scripts/01_inspect.py`, `02_sites.py`, …). Each script reads `raw/`, writes to `public/data/` or `reports/`, and must be safe to rerun. Everything in `raw/` except its README is git-ignored; `raw/README.md` lists which dataset goes in which subfolder.
2. **`src/`**: a React + Vite app that only loads the processed files in `public/data/`. Planned components are MapLibre GL JS (map with AWS Terrarium terrain tiles), D3 (`FlatChart`) and Scrollama (story chapters). Tunable settings belong in `src/config/` (`map.js` for camera and exaggeration, `colors.js`, `chapters.js`), not hard-coded in components.

Data contract rules that matter everywhere: missing data is `null`, never `0`. Every percentage in `site_summary.json` carries its sample size. No-data sites render as grey outlines, not zero values.

Malaria zone thresholds (LaPointe et al. 2010): `high_risk` >21°C, `episodic` 13–21°C, `refuge` <13°C.
