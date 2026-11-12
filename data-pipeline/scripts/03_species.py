"""Step 1.3: species lookup.

Builds data-pipeline/species_lookup.csv: one row per species code found in the
bird count file (`alphacode`) or the bird blood file (`SPECIES`), with one
canonical code per species, names, native status, and honeycreeper status.

Rerunning overwrites the output. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/03_species.py
"""

from pathlib import Path

import pandas as pd

# file locations, built from where this script lives so it runs from any folder
PIPELINE = Path(__file__).resolve().parent.parent
COUNTS_CSV = PIPELINE / "raw" / "biocomplexity_2001_2004" / "Biocomplexity_bird count data.csv"
BLOOD_CSV = PIPELINE / "raw" / "bird_malaria_2001_2005" / "Banding Diagnostics Data Final_revised.csv"
LOOKUP = PIPELINE / "species_lookup.csv"


# ===========================================================================
# Hardcoded species information
# ===========================================================================
# These values were worked out in an earlier version of this script by reading the two XML
# metadata files (BiocomplexityDR.xml for the bird counts, and the bird malaria XML for the
# blood samples) and the bird count file's `guild` column. That cross-reference is done, so
# the results are written in here instead of being read each time.
#
# - Names: from the metadata code lists. Hawaiian names are written with ʻokina and kahakō
#   (the metadata leaves them out).
# - native: from the guild column in the bird count file, whose meanings are given in the
#   metadata: ENDM = native birds; XNTV = non-native birds; GAME = game birds, all introduced.
#   Three species have no guild and were set by hand: REJU (Red Junglefowl) is a game bird,
#   so introduced; MODO and AFSI appear only in the blood file and are introduced to Hawaiʻi
#   (outside knowledge).
# - honeycreeper: outside knowledge. The metadata doesn't say which species are Hawaiian
#   honeycreepers.

# one row per species, keyed by its canonical code:
# (common name, scientific name, native, honeycreeper)
SPECIES = {
    "APAP": ("ʻApapane", "Himatione sanguinea", True, True),
    "HAAM": ("Hawaiʻi ʻAmakihi", "Chlorodrepanis virens", True, True),
    "IIWI": ("ʻIʻiwi", "Drepanis coccinea", True, True),
    "HAAK": ("Hawaiʻi ʻĀkepa", "Loxops coccineus", True, True),
    "AKIP": ("ʻAkiapōlāʻau", "Hemignathus wilsoni", True, True),
    "HCRE": ("Hawaiʻi Creeper (ʻAlawī)", "Loxops mana", True, True),
    "HAEL": ("Hawaiʻi ʻElepaio", "Chasiempis sandwichensis", True, False),
    "OMAO": ("ʻŌmaʻo", "Myadestes obscurus", True, False),
    "HAWH": ("ʻIo (Hawaiian Hawk)", "Buteo solitarius", True, False),
    "WAWE": ("Warbling White-eye", "Zosterops japonicus", False, False),
    "HWAM": ("Hwamei", "Garrulax canorus", False, False),
    "SBMU": ("Scaly-breasted Munia", "Lonchura punctulata", False, False),
    "RBLE": ("Red-billed Leiothrix", "Leiothrix lutea", False, False),
    "NOCA": ("Northern Cardinal", "Cardinalis cardinalis", False, False),
    "HOFI": ("House Finch", "Haemorhous mexicanus", False, False),
    "ZEBD": ("Zebra Dove", "Geopelia striata", False, False),
    "SPDO": ("Spotted Dove", "Spilopelia chinensis", False, False),
    "MODO": ("Mourning Dove", "Zenaida macroura", False, False),
    "AFSI": ("African Silverbill", "Euodice cantans", False, False),
    "COMY": ("Common Myna", "Acridotheres tristis", False, False),
    "JABW": ("Japanese Bush-warbler", "Horornis diphone", False, False),
    "KAPH": ("Kalij Pheasant", "Lophura leucomelanos", False, False),
    "WITU": ("Wild Turkey", "Meleagris gallopavo", False, False),
    "REJU": ("Red Junglefowl", "Gallus gallus", False, False),
}

# codes that mean the same species as another code; both metadata files give the same
# scientific name for each pair
MERGED_CODES = {
    "JAWE": "WAWE",  # Warbling (formerly Japanese) White-eye
    "AKIA": "AKIP",  # ʻAkiapōlāʻau
    "HWAH": "HAWH",  # ʻIo (Hawaiian Hawk)
    "MELT": "HWAM",  # Hwamei
    "NUMA": "SBMU",  # Scaly-breasted Munia
}

# short notes for rows that need one
NOTES = {
    "NOBI": "Not a species: a count with zero birds detected. Keep it when counting events; "
            "exclude it when counting birds.",
    "HCRE": "CHECK: the two metadata files give different names (Alawi, Manucerthia mana vs. "
            "Hawaii Creeper, Loxops mana); same species either way.",
}


# ===========================================================================
# 1. Load the species codes from both bird files
# ===========================================================================
# keep_default_na=False keeps the guild code "NA" (no data recorded) as text instead of
# turning it into an empty cell
df_counts = pd.read_csv(COUNTS_CSV, usecols=["alphacode", "guild"], keep_default_na=False)
df_blood = pd.read_csv(BLOOD_CSV, usecols=["SPECIES"])

count_codes = set(df_counts["alphacode"])
blood_codes = set(df_blood["SPECIES"])
all_codes = sorted(count_codes | blood_codes)

print("codes in the bird count file:", len(count_codes))
print("codes in the bird blood file:", len(blood_codes))
print("codes in either file:        ", len(all_codes))


# ===========================================================================
# 2. Guild values recorded for each code in the bird count file
# ===========================================================================
# "NA" means no guild was recorded, so it is left out; a code with no other value gets a
# blank guild
guilds = df_counts[df_counts["guild"] != "NA"].groupby("alphacode")["guild"].unique()
print("\nguild values per code:")
print(guilds)


# ===========================================================================
# 3. Build the lookup table: one row per code
# ===========================================================================
rows = []
for code in all_codes:
    # NOBI ("no birds detected") marks a count with zero birds, not a species, so its
    # species columns stay blank
    if code == "NOBI":
        canonical = ""
        common, scientific, native, honeycreeper = "No birds detected", "", "", ""
    else:
        canonical = MERGED_CODES.get(code, code)
        common, scientific, native, honeycreeper = SPECIES[canonical]
        native = str(native).lower()          # True -> "true"
        honeycreeper = str(honeycreeper).lower()

    note = NOTES.get(code, "")
    if code in MERGED_CODES:
        note = f"Same species as {canonical} (same scientific name in both metadata files)."

    rows.append({
        "code": code,
        "canonical_code": canonical,
        "common_name": common,
        "scientific_name": scientific,
        "native": native,
        "honeycreeper": honeycreeper,
        "in_counts": str(code in count_codes).lower(),
        "in_blood": str(code in blood_codes).lower(),
        "count_guild": ";".join(sorted(guilds[code])) if code in guilds else "",
        "notes": note,
    })

df_lookup = pd.DataFrame(rows)
print("\nspecies lookup:")
print(df_lookup.drop(columns="notes").to_string(index=False))


# ===========================================================================
# 4. Quick checks
# ===========================================================================
# number of species once merged codes are combined (NOBI is not a species)
print("\ndistinct species after merging:", df_lookup.loc[df_lookup["canonical_code"] != "", "canonical_code"].nunique())
print(df_lookup["native"].value_counts())
print(df_lookup["honeycreeper"].value_counts())

# the guild and the native column should agree: ENDM rows native, XNTV/GAME rows not
with_guild = df_lookup[df_lookup["count_guild"] != ""]
disagree = with_guild[(with_guild["count_guild"] == "ENDM") != (with_guild["native"] == "true")]
print("codes where guild and native disagree:", len(disagree))


# ===========================================================================
# 5. Write the lookup
# ===========================================================================
df_lookup.to_csv(LOOKUP, index=False)
print("\nwrote data-pipeline/species_lookup.csv:", len(df_lookup), "codes")
