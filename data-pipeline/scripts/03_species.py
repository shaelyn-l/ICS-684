"""Step 1.3: species lookup.

Builds data-pipeline/species_lookup.csv covering every species code in the bird
count file (`alphacode`) and the bird blood file (`SPECIES`), and writes a short
summary to reports/species_check.md.

Code meanings come from the two XML metadata files. Native status comes from the
bird count `guild` column (ENDM = native). Anything taken from outside knowledge
instead is listed in OUTSIDE_KNOWLEDGE below and noted in the output.

Rerunning overwrites the outputs. Raw data is not changed.
Run from anywhere:  python data-pipeline/scripts/03_species.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

PIPELINE = Path(__file__).resolve().parent.parent
RAW = PIPELINE / "raw"
COUNTS_CSV = RAW / "biocomplexity_2001_2004" / "Biocomplexity_bird count data.csv"
BLOOD_CSV = RAW / "bird_malaria_2001_2005" / "Banding Diagnostics Data Final_revised.csv"
COUNTS_XML = RAW / "biocomplexity_2001_2004" / "BiocomplexityDR.xml"
BLOOD_XML = RAW / "bird_malaria_2001_2005" / "Island of Hawaii forest bird malaria infection data 2001-2005 revised.xml"
LOOKUP = PIPELINE / "species_lookup.csv"
REPORT = PIPELINE / "reports" / "species_check.md"

# Codes for the same species in the two files, merged to one canonical code.
# Each merge is justified by both metadata files giving the same scientific name.
CANONICAL = {
    "JAWE": "WAWE",  # Warbling (formerly Japanese) White-eye, Zosterops japonicus
    "AKIA": "AKIP",  # Akiapolaau, Hemignathus wilsoni
    "HWAH": "HAWH",  # Io / Hawaiian Hawk, Buteo solitarius
    "MELT": "HWAM",  # Hwamei / Melodious Laughing-thrush, Garrulax canorus
    "NUMA": "SBMU",  # Scaly-breasted Munia / Nutmeg Mannikin, Lonchura punctulata
}

# Display names per canonical code, used for every row in a merged group. Hawaiian
# names use ʻokina and kahakō; the metadata spells them without. Scientific names
# follow the metadata except where noted in NAME_NOTES.
NAMES = {
    "APAP": ("ʻApapane", "Himatione sanguinea"),
    "HAAM": ("Hawaiʻi ʻAmakihi", "Chlorodrepanis virens"),
    "IIWI": ("ʻIʻiwi", "Drepanis coccinea"),
    "HAAK": ("Hawaiʻi ʻĀkepa", "Loxops coccineus"),
    "AKIP": ("ʻAkiapōlāʻau", "Hemignathus wilsoni"),
    "HCRE": ("Hawaiʻi Creeper (ʻAlawī)", "Loxops mana"),
    "HAEL": ("Hawaiʻi ʻElepaio", "Chasiempis sandwichensis"),
    "OMAO": ("ʻŌmaʻo", "Myadestes obscurus"),
    "HAWH": ("ʻIo (Hawaiian Hawk)", "Buteo solitarius"),
    "WAWE": ("Warbling White-eye", "Zosterops japonicus"),
    "HWAM": ("Hwamei", "Garrulax canorus"),
    "SBMU": ("Scaly-breasted Munia", "Lonchura punctulata"),
    "RBLE": ("Red-billed Leiothrix", "Leiothrix lutea"),
    "NOCA": ("Northern Cardinal", "Cardinalis cardinalis"),
    "HOFI": ("House Finch", "Haemorhous mexicanus"),
    "ZEBD": ("Zebra Dove", "Geopelia striata"),
    "SPDO": ("Spotted Dove", "Spilopelia chinensis"),
    "MODO": ("Mourning Dove", "Zenaida macroura"),
    "AFSI": ("African Silverbill", "Euodice cantans"),
    "COMY": ("Common Myna", "Acridotheres tristis"),
    "JABW": ("Japanese Bush-warbler", "Horornis diphone"),
    "KAPH": ("Kalij Pheasant", "Lophura leucomelanos"),
    "WITU": ("Wild Turkey", "Meleagris gallopavo"),
    "REJU": ("Red Junglefowl", "Gallus gallus"),
}

# Where the metadata differs from NAMES, or the two files disagree.
NAME_NOTES = {
    "ZEBD": "Counts metadata spells it Geopelia striatara (typo); blood metadata has striata.",
    "HWAM": "Blood metadata spells it Garrulax canoris (typo); counts metadata has canorus.",
    "IIWI": "Counts metadata has Vestiaria coccinea (older genus); blood metadata has Drepanis coccinea.",
    "HCRE": ("CHECK: files disagree. Counts metadata: Alawi (formerly Hawaii Creeper), "
             "Manucerthia mana. Blood metadata: Hawaii Creeper, Loxops mana. Same species either way."),
}

# Hawaiian honeycreepers (subfamily Carduelinae, tribe Drepanidini). The metadata does
# not say which species are honeycreepers, so this is outside knowledge.
HONEYCREEPERS = {"APAP", "HAAM", "IIWI", "HAAK", "AKIP", "HCRE"}

# Native status for canonical codes with no guild in the bird count file.
OUTSIDE_KNOWLEDGE = {
    "REJU": (False, "Guild is NA on every count row. Set non-native because the metadata defines "
                    "GAME as all Phasianidae, all introduced, and Gallus gallus is a Phasianidae."),
    "MODO": (False, "Native status from outside knowledge (introduced to Hawaiʻi); not in the counts file."),
    "AFSI": (False, "Native status from outside knowledge (introduced to Hawaiʻi); not in the counts file."),
}

NOT_A_SPECIES = {"NOBI"}  # "No birds detected": a count with zero detections, not a species
GUILD_NATIVE = {"ENDM": True, "XNTV": False, "GAME": False}


def code_domain(xml_path, attr_labels):
    """Map code -> description from the given attribute's enumerated domain in an XML file."""
    out = {}
    for attr in ET.parse(xml_path).getroot().iter("attr"):
        if (attr.findtext("attrlabl") or "").strip() not in attr_labels:
            continue
        for d in attr.iter("edom"):
            code = (d.findtext("edomv") or "").strip()
            desc = " ".join((d.findtext("edomvd") or "").split())
            if code:
                out[code] = desc
    return out


def tf(value):
    return "" if value is None else str(bool(value)).lower()


def main():
    # keep_default_na=False so the literal guild code "NA" (no data recorded) stays visible
    counts = pd.read_csv(COUNTS_CSV, usecols=["alphacode", "guild"], keep_default_na=False)
    blood = pd.read_csv(BLOOD_CSV, usecols=["SPECIES"])
    count_codes = set(counts["alphacode"])
    blood_codes = set(blood["SPECIES"])

    counts_meta = code_domain(COUNTS_XML, {"alphacode"})
    blood_meta = code_domain(BLOOD_XML, {"SPECIES"})
    guild_meta = code_domain(COUNTS_XML, {"guild"})

    # Guild values recorded per code in the counts file ("NA"/blank = not recorded).
    guilds = (counts.groupby("alphacode")["guild"]
              .apply(lambda s: sorted({g for g in s if g not in ("", "NA")})).to_dict())
    guild_missing = counts[counts["guild"].isin(["", "NA"])]["alphacode"].value_counts().to_dict()

    # Native status per canonical code, from the guild of any code in its group.
    canon_native = {}
    for code, gs in guilds.items():
        canon = CANONICAL.get(code, code)
        for g in gs:
            canon_native.setdefault(canon, set()).add(GUILD_NATIVE[g])

    rows, disagreements = [], []
    for code in sorted(count_codes | blood_codes):
        notes = []
        meta = [m for m in (counts_meta.get(code), blood_meta.get(code)) if m]
        if not meta:
            notes.append("CHECK: code not defined in either metadata file.")

        if code in NOT_A_SPECIES:
            rows.append({"code": code, "canonical_code": "", "common_name": "No birds detected",
                         "scientific_name": "", "native": "", "honeycreeper": "",
                         "in_counts": tf(code in count_codes), "in_blood": tf(code in blood_codes),
                         "count_guild": ";".join(guilds.get(code, [])),
                         "notes": "Not a species: marks a count with zero detections. Keep it when "
                                  "counting events; exclude it when counting birds."})
            continue

        canon = CANONICAL.get(code, code)
        common, scientific = NAMES[canon]
        if canon != code:
            other = [c for c, k in CANONICAL.items() if k == canon] + [canon]
            notes.append(f"Merged with {', '.join(c for c in other if c != code)}: "
                         "both metadata files give the same scientific name.")
        if canon in NAME_NOTES:
            notes.append(NAME_NOTES[canon])

        if canon in canon_native:
            values = canon_native[canon]
            native = next(iter(values)) if len(values) == 1 else None
            if native is None:
                notes.append("CHECK: guild values for this species disagree on native status.")
        elif canon in OUTSIDE_KNOWLEDGE:
            native, note = OUTSIDE_KNOWLEDGE[canon]
            notes.append(note)
        else:
            native = None
            notes.append("CHECK: no guild and no native status recorded.")

        honeycreeper = canon in HONEYCREEPERS
        if honeycreeper:
            notes.append("Honeycreeper status from outside knowledge (not in metadata).")
        if honeycreeper and native is False:
            disagreements.append(f"`{code}` is marked honeycreeper but its guild says non-native.")

        code_guild = guilds.get(code, [])
        if code in guild_missing:
            notes.append(f"{guild_missing[code]} count row(s) have guild NA (not recorded).")
        if code_guild and native is not None and any(GUILD_NATIVE[g] != native for g in code_guild):
            disagreements.append(f"`{code}`: guild {code_guild} disagrees with native={native}.")

        rows.append({"code": code, "canonical_code": canon, "common_name": common,
                     "scientific_name": scientific, "native": tf(native),
                     "honeycreeper": tf(honeycreeper),
                     "in_counts": tf(code in count_codes), "in_blood": tf(code in blood_codes),
                     "count_guild": ";".join(code_guild), "notes": " ".join(notes)})

    lookup = pd.DataFrame(rows)
    lookup.to_csv(LOOKUP, index=False)
    print(f"wrote {LOOKUP.relative_to(PIPELINE)} ({len(lookup)} codes: "
          f"{len(count_codes)} in counts, {len(blood_codes)} in blood)")

    missing = (count_codes | blood_codes) - set(lookup["code"])
    assert not missing, f"codes missing from lookup: {missing}"

    write_report(lookup, guild_meta, guild_missing, disagreements)
    print(lookup[["code", "canonical_code", "common_name", "native", "honeycreeper",
                  "in_counts", "in_blood", "count_guild"]].to_string(index=False))


def write_report(lookup, guild_meta, guild_missing, disagreements):
    merged = lookup[lookup["code"] != lookup["canonical_code"]].query("canonical_code != ''")
    check = lookup[lookup["notes"].str.contains("CHECK")]

    lines = ["# Species check", "",
             "Generated by `scripts/03_species.py`. Lookup: `species_lookup.csv`.", "",
             f"- Codes in the bird count file (`alphacode`): {lookup['in_counts'].eq('true').sum()}",
             f"- Codes in the bird blood file (`SPECIES`): {lookup['in_blood'].eq('true').sum()}",
             f"- Codes in the lookup: {len(lookup)}; distinct species after merging: "
             f"{lookup.loc[lookup['canonical_code'] != '', 'canonical_code'].nunique()}", "",
             "## Merged codes", "",
             "Each pair has the same scientific name in the two metadata files.", "",
             "| code | file | merged into | species |", "|---|---|---|---|"]
    for r in merged.itertuples():
        file = "counts" if r.in_counts == "true" else "blood"
        lines.append(f"| {r.code} | {file} | {r.canonical_code} | {r.common_name}, *{r.scientific_name}* |")

    lines += ["", "## Unresolved codes", "",
              "None. HWAH, HWAM and HAWH are resolved by the metadata: HWAH (counts) and HAWH (blood) "
              "are both ʻIo, *Buteo solitarius*; HWAM (blood) is Hwamei, *Garrulax canorus*, which the "
              "counts file codes as MELT.", "",
              "Rows marked `CHECK` (review these):", ""]
    lines += [f"- `{r.code}`: {r.notes}" for r in check.itertuples()] or ["- none"]

    lines += ["", "## Guild values (bird count file)", "",
              "From the Biocomplexity metadata. Only the bird count file has a guild column.", "",
              "| guild | meaning |", "|---|---|"]
    lines += [f"| {g} | {m} |" for g, m in guild_meta.items()]
    if guild_missing:
        lines += ["", "Rows with guild `NA` (pandas reads this as missing unless told otherwise): "
                  + ", ".join(f"{c} ×{n}" for c, n in guild_missing.items())
                  + ". REJU has no other guild value; see its row in the lookup. NOBI is not a species."]

    lines += ["", "## Guild vs. native", "",
              "`native` is true where the guild is ENDM and false for XNTV and GAME. Codes merged "
              "into one species share the native status of the code that has a guild. "
              "MODO and AFSI appear only in the blood file, so their native status is from "
              "outside knowledge (both introduced). REJU's comes from the GAME guild definition.", ""]
    lines += [f"- {d}" for d in disagreements] or ["No disagreements between `count_guild` and `native`."]

    lines += ["", "## Other notes", "",
              "- `NOBI` (\"No birds detected\") is not a species. It marks a counting event with zero "
              "detections, so it matters for birds-per-count denominators in Step 1.5.",
              "- Honeycreeper status is outside knowledge: the metadata doesn't classify species "
              "beyond the guild.",
              "- Hawaiian common names are written with ʻokina and kahakō; the metadata omits them.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(PIPELINE)}")


if __name__ == "__main__":
    main()
