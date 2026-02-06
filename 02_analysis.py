import pandas as pd

# Load stacked dataset
df = pd.read_csv("pl_financials_stacked.csv")

# ----
# 1) Normalise column names (handles your current "League position" vs league_position issue)
# ----
rename_map = {
    "Season": "season_excel",          # keep if you want to compare, but we'll use `season` going forward
    "League position": "league_position",
    "Points total": "points_total",
}

df = df.rename(columns=rename_map)

# If you have both `season` and `season_excel`, prefer `season` (generated from sheet name)
if "season_excel" in df.columns:
    # Drop season_excel unless you want to audit differences
    df = df.drop(columns=["season_excel"])

# ----
# 2) Quick inspection
# ----
print("Columns:")
print(df.columns.tolist())

print("\nHead (season, club):")
print(df[["season", "club"]].head())

# ----
# 3) Missing value check (key columns)
# ----
key_cols = [
    "total_wage_bill_gbp_m",
    "league_position",
    "points_total",
    "gross_transfer_spend_gbp_m",
    "promoted",
]

print("\nMissing values in key columns:")
print(df[key_cols].isna().sum())

# ----
# 4) Ensure numeric types (helps correlation/regression)
# ----
numeric_cols = ["total_wage_bill_gbp_m", "league_position", "points_total", "gross_transfer_spend_gbp_m", "promoted"]
for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Fix promoted column: treat missing as 0 (not promoted)
df["promoted"] = df["promoted"].fillna(0).astype(int)

# ----
# 5) Correlations
# ----
print("\nCorrelation with points_total:")
print(
    df[["points_total", "total_wage_bill_gbp_m", "gross_transfer_spend_gbp_m"]]
    .corr()["points_total"]
    .sort_values(ascending=False)
)

print("\nCorrelation with league_position (lower is better):")
print(
    df[["league_position", "total_wage_bill_gbp_m", "gross_transfer_spend_gbp_m"]]
    .corr()["league_position"]
    .sort_values()
)

# ----
# 6) Optional: save a cleaned analysis-ready CSV
# ----
df.to_csv("pl_financials_analysis_ready.csv", index=False)
print("\nSaved: pl_financials_analysis_ready.csv")