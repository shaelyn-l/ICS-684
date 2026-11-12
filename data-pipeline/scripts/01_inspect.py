"""Step 1.1: inspect the raw field-data CSVs before any processing.

Basic exploratory look at each raw file using pandas: size, columns, types,
empty cells, summary statistics, site/station values, date ranges, species
values, and the first rows. Read-only: nothing is changed or saved.

Run from anywhere:  python data-pipeline/scripts/01_inspect.py
"""

from pathlib import Path

import pandas as pd

# file locations, built from where this script lives so it runs from any folder
RAW = Path(__file__).resolve().parent.parent / "raw"
BIO = RAW / "biocomplexity_2001_2004"
MALARIA = RAW / "bird_malaria_2001_2005"

# show every column and row when printing, instead of hiding the middle with "..."
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 250)

# values these files use in place of empty cells; they are counted, not changed
MISSING_CODES = [9999, -9999, "9999", "-9999", "ND", "N/A"]


# ===========================================================================
# 1. Bird count data
# ===========================================================================
print("=" * 80)
print("BIRD COUNT DATA")
df_counts = pd.read_csv(BIO / "Biocomplexity_bird count data.csv")

# general formatting info on dataset
print(df_counts.shape)
print(df_counts.columns.tolist())
print(df_counts.head())

# column types, empty cells, and missing-value codes per column
print(df_counts.dtypes)
print(df_counts.isna().sum())
print(df_counts.isin(MISSING_CODES).sum())

# dataset description (count, mean, min, max of the number columns) and unique values per column
print(df_counts.describe())
print(df_counts.nunique())

# site, station, and transect values
print(df_counts["site"].value_counts())
print(df_counts["station"].value_counts())
print(df_counts["transect"].value_counts())

# date range; errors="coerce" turns unreadable dates into NaT so they can be counted
counts_dates = pd.to_datetime(df_counts["obsvdate"], format="%m/%d/%Y", errors="coerce")
print("obsvdate:", counts_dates.min(), "to", counts_dates.max(), "| unreadable:", counts_dates.isna().sum())

# bird count rows per calendar month (1 = January), to see when counting rounds happened;
# rounds about every three months fit the Hawaiian wet (Nov–Apr) and dry (May–Oct) seasons
print(counts_dates.dt.month.value_counts().sort_index())

# species values (4-letter bird codes)
print(df_counts["alphacode"].value_counts())


# ===========================================================================
# 2. Mosquito dissection (infection and parity) data
# ===========================================================================
print("=" * 80)
print("MOSQUITO DISSECTION DATA")
df_dissect = pd.read_csv(BIO / "Biocomplexity_mosquito avian malaria infection and parity data.csv")

# general formatting info on dataset
print(df_dissect.shape)
print(df_dissect.columns.tolist())
print(df_dissect.head())

# column types, empty cells, and missing-value codes per column
print(df_dissect.dtypes)
print(df_dissect.isna().sum())
print(df_dissect.isin(MISSING_CODES).sum())

# dataset description and unique values per column
print(df_dissect.describe())
print(df_dissect.nunique())

# site, station, and transect values
print(df_dissect["site"].value_counts())
print(df_dissect["station"].value_counts())
print(df_dissect["transect"].value_counts())

# date ranges; this file writes dates as year-month-day, unlike the others
collected = pd.to_datetime(df_dissect["date_collected"], format="%Y-%m-%d", errors="coerce")
dissected = pd.to_datetime(df_dissect["date_dissected"], format="%Y-%m-%d", errors="coerce")
print("date_collected:", collected.min(), "to", collected.max(),
      "| unreadable:", collected.isna().sum())
print("date_dissected:", dissected.min(), "to", dissected.max(),
      "| empty or unreadable:", dissected.isna().sum())

# species values
print(df_dissect["species"].value_counts())


# ===========================================================================
# 3. Mosquito capture data
# ===========================================================================
print("=" * 80)
print("MOSQUITO CAPTURE DATA")
df_capture = pd.read_csv(BIO / "Biocomplexity_mosquito capture data.csv")

# general formatting info on dataset
print(df_capture.shape)
print(df_capture.columns.tolist())
print(df_capture.head())

# column types, empty cells, and missing-value codes per column
print(df_capture.dtypes)
print(df_capture.isna().sum())
print(df_capture.isin(MISSING_CODES).sum())

# dataset description and unique values per column
print(df_capture.describe())
print(df_capture.nunique())

# site, station, and transect values
print(df_capture["site"].value_counts())
print(df_capture["station"].value_counts())
print(df_capture["transect"].value_counts())

# date range
capture_dates = pd.to_datetime(df_capture["date"], format="%m/%d/%Y", errors="coerce")
print("date:", capture_dates.min(), "to", capture_dates.max(), "| unreadable:", capture_dates.isna().sum())

# no species column: mosquitoes are counted in separate culex / aedes / wyeomyia columns


# ===========================================================================
# 4. Sampling station coordinates
# ===========================================================================
print("=" * 80)
print("SAMPLING STATION COORDINATES")
df_coords = pd.read_csv(BIO / "Biocomplexity_sampling station spatial coordinates.csv")

# general formatting info on dataset
print(df_coords.shape)
print(df_coords.columns.tolist())
print(df_coords.head())

# column types, empty cells, and missing-value codes per column
print(df_coords.dtypes)
print(df_coords.isna().sum())
print(df_coords.isin(MISSING_CODES).sum())

# dataset description (includes the longitude, latitude, and elevation ranges) and unique values
print(df_coords.describe())
print(df_coords.nunique())

# site, station, and transect values
print(df_coords["site"].value_counts())
print(df_coords["station"].value_counts())
print(df_coords["transect"].value_counts())

# no date or species columns in this file


# ===========================================================================
# 5. Bird blood samples (banding diagnostics)
# ===========================================================================
print("=" * 80)
print("BIRD BLOOD SAMPLES")
df_blood = pd.read_csv(MALARIA / "Banding Diagnostics Data Final_revised.csv", low_memory=False)

# general formatting info on dataset
print(df_blood.shape)
print(df_blood.columns.tolist())
print(df_blood.head())

# column types, empty cells, and missing-value codes per column
print(df_blood.dtypes)
print(df_blood.isna().sum())
print(df_blood.isin(MISSING_CODES).sum())

# dataset description and unique values per column
print(df_blood.describe())
print(df_blood.nunique())

# site values (this file calls the site column LOCATION and has no station or transect)
print(df_blood["LOCATION"].value_counts())

# date range
blood_dates = pd.to_datetime(df_blood["DATE"], format="%m/%d/%Y", errors="coerce")
print("DATE:", blood_dates.min(), "to", blood_dates.max(), "| unreadable:", blood_dates.isna().sum())

# species values
print(df_blood["SPECIES"].value_counts())


# ===========================================================================
# Cross-file check: do all five files use the same site codes?
# ===========================================================================
print("=" * 80)
print("SITE CODES IN EACH FILE")
print("bird counts: ", sorted(df_counts["site"].unique()))
print("dissections: ", sorted(df_dissect["site"].unique()))
print("captures:    ", sorted(df_capture["site"].unique()))
print("coordinates: ", sorted(df_coords["site"].unique()))
print("blood:       ", sorted(df_blood["LOCATION"].unique()))

# True if every file has exactly the same set of site codes
site_sets = [set(df_counts["site"]), set(df_dissect["site"]), set(df_capture["site"]),
             set(df_coords["site"]), set(df_blood["LOCATION"])]
print("all files match:", all(s == site_sets[0] for s in site_sets))
