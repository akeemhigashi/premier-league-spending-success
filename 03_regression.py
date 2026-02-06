import pandas as pd
import statsmodels.formula.api as smf

# Load the cleaned dataset you saved
df = pd.read_csv("pl_financials_analysis_ready.csv")

# Make sure key columns are numeric and usable
df["points_total"] = pd.to_numeric(df["points_total"], errors="coerce")
df["league_position"] = pd.to_numeric(df["league_position"], errors="coerce")
df["total_wage_bill_gbp_m"] = pd.to_numeric(df["total_wage_bill_gbp_m"], errors="coerce")
df["gross_transfer_spend_gbp_m"] = pd.to_numeric(df["gross_transfer_spend_gbp_m"], errors="coerce")

# Fix common missing patterns
df["gross_transfer_spend_gbp_m"] = df["gross_transfer_spend_gbp_m"].fillna(0)
df["promoted"] = pd.to_numeric(df["promoted"], errors="coerce").fillna(0).astype(int)

# Drop any rows missing the core dependent variable
df = df.dropna(subset=["points_total", "total_wage_bill_gbp_m"])

print("Rows used:", len(df))
print(df[["season", "club"]].head())

# -------------------------
# Model 1: Points ~ Wages
# -------------------------
m1 = smf.ols(
    "points_total ~ total_wage_bill_gbp_m",
    data=df
).fit(cov_type="HC3")

print("\nMODEL 1: points_total ~ total_wage_bill_gbp_m (robust SE)")
print(m1.summary())

# -----------------------------------------
# Model 2: Points ~ Wages + Transfers
# -----------------------------------------
m2 = smf.ols(
    "points_total ~ total_wage_bill_gbp_m + gross_transfer_spend_gbp_m",
    data=df
).fit(cov_type="HC3")

print("\nMODEL 2: points_total ~ wages + transfers (robust SE)")
print(m2.summary())

# ---------------------------------------------------
# Optional Model 3: Add promoted control + season FE
# (Season fixed effects control for league-wide shifts)
# ---------------------------------------------------
m3 = smf.ols(
    "points_total ~ total_wage_bill_gbp_m + gross_transfer_spend_gbp_m + promoted + C(season)",
    data=df
).fit(cov_type="HC3")

print("\nMODEL 3: wages + transfers + promoted + season fixed effects (robust SE)")
print(m3.summary())

# -----------------------------------------
# Optional: League position as robustness
# (lower is better, so coefficients will flip sign)
# -----------------------------------------
m4 = smf.ols(
    "league_position ~ total_wage_bill_gbp_m + gross_transfer_spend_gbp_m + promoted + C(season)",
    data=df
).fit(cov_type="HC3")

print("\nMODEL 4: league_position ~ wages + transfers + promoted + season FE (robust SE)")
print(m4.summary())

# Save regression tables to text for your appendix
with open("regression_outputs.txt", "w") as f:
    f.write("MODEL 1\n")
    f.write(m1.summary().as_text())
    f.write("\n\nMODEL 2\n")
    f.write(m2.summary().as_text())
    f.write("\n\nMODEL 3\n")
    f.write(m3.summary().as_text())
    f.write("\n\nMODEL 4\n")
    f.write(m4.summary().as_text())

print("\nSaved: regression_outputs.txt")