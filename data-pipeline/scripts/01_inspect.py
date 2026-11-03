"""Step 1.1: inspect the raw field-data CSVs before any processing.

Reads every CSV in raw/biocomplexity_2001_2004/ and raw/bird_malaria_2001_2005/
and writes reports/inspection.md. Read-only: no data is transformed or saved.

Run from anywhere:  python data-pipeline/scripts/01_inspect.py
"""

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

PIPELINE = Path(__file__).resolve().parent.parent
RAW = PIPELINE / "raw"
REPORT = PIPELINE / "reports" / "inspection.md"
FOLDERS = ["biocomplexity_2001_2004", "bird_malaria_2001_2005"]

# Columns are found by name, case-insensitively. Adjust these if the report
# shows a site, date, or species column being missed.
SITE_PATTERN = re.compile(r"site|location|^loc|station|transect", re.I)
CROSS_FILE_PATTERN = re.compile(r"site|location|^loc", re.I)  # site codes only, not station numbers
DATE_PATTERN = re.compile(r"date", re.I)
SPECIES_PATTERN = re.compile(r"spec|^spp?$|^sp_|taxon|alphacode", re.I)

# Values these files appear to use in place of empty cells. Counted, not changed.
MISSING_CODES = [9999, -9999, "9999", "-9999", "ND", "NA", "N/A"]

MAX_UNIQUE_LISTED = 100  # longer lists of unique values are cut off


def read_csv(path):
    """Read a CSV as-is, trying UTF-8 first, then Latin-1 (common in USGS exports)."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"could not decode {path}")


def cell(value):
    """Format a value for a markdown table cell."""
    if pd.isna(value):
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def md_table(headers, rows):
    lines = ["| " + " | ".join(cell(h) for h in headers) + " |",
             "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def column_summary(df):
    rows = []
    for col in df.columns:
        s = df[col]
        lo = hi = None
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            lo, hi = s.min(), s.max()
        codes = s.astype(str).str.strip().value_counts()
        found = {str(c): codes[str(c)] for c in MISSING_CODES if str(c) in codes}
        coded = ", ".join(f"{c}×{n}" for c, n in found.items())
        rows.append([col, str(s.dtype), s.isna().sum(), coded, s.nunique(dropna=True), lo, hi])
    return md_table(["column", "type", "nulls", "missing codes", "unique", "min", "max"], rows)


def value_counts_section(df, cols, label):
    out = []
    for col in cols:
        counts = df[col].value_counts(dropna=False)
        out += [f"**{label} column `{col}`**: {len(counts)} unique values", ""]
        shown = counts.head(MAX_UNIQUE_LISTED)
        out += [md_table(["value", "rows"], [[("(null)" if pd.isna(v) else v), n]
                                             for v, n in shown.items()]), ""]
        if len(counts) > MAX_UNIQUE_LISTED:
            out += [f"_…{len(counts) - MAX_UNIQUE_LISTED} more not shown._", ""]
    return out


def date_section(df, cols):
    rows = []
    for col in cols:
        raw = df[col].dropna().astype(str)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(raw, errors="coerce", format="mixed")
        n_bad = parsed.isna().sum()
        example = raw.iloc[0] if len(raw) else None
        rows.append([col, example, parsed.min(), parsed.max(), n_bad])
    return md_table(["column", "example raw value", "min", "max", "unparseable"], rows)


def inspect_file(path, site_values):
    df, encoding = read_csv(path)
    name = path.relative_to(RAW).as_posix()
    site_cols = [c for c in df.columns if SITE_PATTERN.search(c)]
    date_cols = [c for c in df.columns if DATE_PATTERN.search(c)]
    species_cols = [c for c in df.columns if SPECIES_PATTERN.search(c)]

    out = [f"## `{name}`", "",
           f"- Rows: {len(df):,}",
           f"- Columns: {len(df.columns)}",
           f"- Encoding: {encoding}",
           f"- Site/location columns found: {', '.join(f'`{c}`' for c in site_cols) or 'none'}",
           f"- Date columns found: {', '.join(f'`{c}`' for c in date_cols) or 'none'}",
           f"- Species columns found: {', '.join(f'`{c}`' for c in species_cols) or 'none'}",
           "", "### Columns, types, and nulls", "", column_summary(df), ""]

    out += ["### Site / location values", ""]
    out += value_counts_section(df, site_cols, "Site") if site_cols else ["_No site or location column found._"]
    out.append("")

    out += ["### Date range", ""]
    out.append(date_section(df, date_cols) if date_cols else "_No date column found._")
    out.append("")

    out += ["### Species values", ""]
    out += value_counts_section(df, species_cols, "Species") if species_cols else ["_No species column found._"]
    out.append("")

    out += ["### First five rows", "", md_table(df.columns, df.head(5).itertuples(index=False)), ""]

    for col in site_cols:
        if CROSS_FILE_PATTERN.search(col):
            for v in df[col].dropna().unique():
                site_values.setdefault(str(v), set()).add(f"{path.stem}: {col}")
    return out


def cross_file_section(site_values):
    """Which site codes appear in which file, to check they match."""
    sources = sorted({src for srcs in site_values.values() for src in srcs})
    if not sources:
        return []
    headers = ["site"] + sources
    rows = [[v] + ["✓" if s in site_values[v] else "" for s in sources]
            for v in sorted(site_values)]
    return ["## Cross-file check: site codes", "",
            "Each column is one file and its site column. A blank cell means that site "
            "code does not appear in that file.", "",
            md_table(headers, rows), ""]


def main():
    out = ["# Raw data inspection", "",
           "Generated by `scripts/01_inspect.py`. Raw data is read only; nothing is transformed.", ""]
    site_values = {}
    files = []
    for folder in FOLDERS:
        d = RAW / folder
        if not d.is_dir():
            out += [f"**Missing folder:** `raw/{folder}/`. See `raw/README.md`.", ""]
            continue
        csvs = sorted(d.rglob("*.csv"))
        others = sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() != ".csv")
        out += [f"# Folder `raw/{folder}/`", "",
                f"CSV files: {len(csvs)}. Other files: "
                + (", ".join(f"`{p.relative_to(d).as_posix()}`" for p in others) or "none"), ""]
        for path in csvs:
            print(f"inspecting {path.relative_to(RAW)}")
            out += inspect_file(path, site_values)
            files.append(path)

    if not files:
        print("No CSVs found. Download the data into data-pipeline/raw/ first (see raw/README.md).")
        sys.exit(1)

    out += cross_file_section(site_values)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(PIPELINE)}")


if __name__ == "__main__":
    main()
