import pandas as pd

FILE_PATH = "PL-financials.xlsx"  # put the Excel file in the same folder as this script

xls = pd.ExcelFile(FILE_PATH)

dfs = []

def normalise_season_value(s: str) -> str:
    s = str(s).strip().replace("–", "-")  # convert en-dash to hyphen
    # If season is like "13-14", convert to "2013-14"
    m = pd.Series([s]).str.extract(r"^(\d{2})-(\d{2})$").iloc[0].tolist()
    if m[0] is not None and m[1] is not None:
        return f"20{m[0]}-{m[1]}"
    # If season is like "2013-14", keep as-is
    if pd.Series([s]).str.match(r"^\d{4}-\d{2}$").iloc[0]:
        return s
    return s

for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)

    # Normalise column names
    df.columns = [str(c).strip() for c in df.columns]

    # Force season from the sheet name (prevents Excel auto-fill issues like 22-24, 22-25, etc.)
    df["season"] = normalise_season_value(sheet)

    # Standardise club column name
    if "club" not in df.columns:
        club_like = [c for c in df.columns if "club" in c.lower()]
        if club_like:
            df = df.rename(columns={club_like[0]: "club"})

    # Standardise promoted column name
    prom_like = [c for c in df.columns if "promot" in c.lower()]
    if prom_like and prom_like[0] != "promoted":
        df = df.rename(columns={prom_like[0]: "promoted"})

    # Standardise transfer spend column name
    spend_like = [
        c for c in df.columns
        if ("transfer" in c.lower() and ("spend" in c.lower() or "expend" in c.lower()))
    ]
    if spend_like and spend_like[0] != "gross_transfer_spend_gbp_m":
        df = df.rename(columns={spend_like[0]: "gross_transfer_spend_gbp_m"})

    dfs.append(df)

stacked = pd.concat(dfs, ignore_index=True)

# Quick integrity checks
print("Rows:", len(stacked))
print("Seasons:", stacked["season"].nunique())
print("Unique clubs:", stacked["club"].nunique())

print("\nRows per season:")
print(stacked.groupby("season")["club"].count().sort_index())

# Optional: check duplicates within a season
dupes = stacked[stacked.duplicated(subset=["season", "club"], keep=False)].sort_values(["season", "club"])
print("\nDuplicate season,club rows:", len(dupes))

# Save analysis-ready file
stacked.to_csv("pl_financials_stacked.csv", index=False)
print("\nSaved: pl_financials_stacked.csv")