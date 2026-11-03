# ICS-684: Hawaiʻi Island Avian Malaria Story Map

An interactive web app telling the story of avian malaria and Hawaiian honeycreepers on Hawaiʻi Island. See [PLAN.md](PLAN.md) for the full build plan.

## Running the app

Requires Node.js 20 or later.

```bash
npm install
npm run dev
```

Then open the local URL Vite prints (usually http://localhost:5173).

## Data pipeline (Python)

The scripts in `data-pipeline/` process raw data into the web-ready files in `public/data/`. They run locally and are not part of the website.

Using the built-in `venv`:

```bash
cd data-pipeline
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Or with conda (often easier for geopandas and rasterio):

```bash
conda create -n avian-malaria -c conda-forge python=3.12 pandas geopandas pyproj rasterio shapely
conda activate avian-malaria
```

Download the source datasets into `data-pipeline/raw/` as listed in [data-pipeline/raw/README.md](data-pipeline/raw/README.md). Raw files are git-ignored.

## Folder structure

```
data-pipeline/   Python scripts, raw data (git-ignored), and reports
public/data/     processed files the app loads
src/             React app (components/, config/, App.jsx)
```
