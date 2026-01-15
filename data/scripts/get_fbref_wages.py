import argparse
import os
import re
import time
from typing import Optional, Tuple

import pandas as pd
import requests


def season_slug(season: str) -> str:
    """
    Converts '2013-2014' into '2013-2014' slug used by FBref URLs.
    """
    m = re.match(r"^(\d{4})-(\d{4})$", season.strip())
    if not m:
        raise ValueError("Season must be in YYYY-YYYY format, for example 2013-2014")
    return f"{m.group(1)}-{m.group(2)}"


def parse_money_to_gbp(value) -> Optional[float]:
    """
    Converts strings like '£113,900,000' or '£113.9m' into a float number of GBP.
    Returns None if value cannot be parsed.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()

    if s == "" or s.lower() in {"nan", "none"}:
        return None

    # Remove currency symbol and spaces
    s = s.replace("£", "").replace(",", "").strip()

    # Handle formats like 113.9m
    m = re.match(r"^(\d+(\.\d+)?)\s*[mM]$", s)
    if m:
        return float(m.group(1)) * 1_000_000

    # Handle plain integers
    m = re.match(r"^\d+(\.\d+)?$", s)
    if m:
        return float(s)

    return None


def find_wages_table(df_list: list[pd.DataFrame]) -> Tuple[pd.DataFrame, str]:
    """
    FBref wages pages often contain a wages table with columns like:
    'Squad', 'Annual Wages', 'Weekly Wages' (exact names can vary).
    This function finds the most likely table and the name of the wage column.
    """
    best_df = None
    best_col = None

    for df in df_list:
        cols = [str(c).strip().lower() for c in df.columns]

        # Require a club column candidate
        club_col_candidates = [c for c in df.columns if str(c).strip().lower() in {"squad", "club", "team"}]
        if not club_col_candidates:
            continue

        # Find annual wages column candidate
        wage_col_candidates = []
        for c in df.columns:
            cl = str(c).strip().lower()
            if "annual" in cl and "wage" in cl:
                wage_col_candidates.append(c)
            if cl in {"annual wages", "annual_wages"}:
                wage_col_candidates.append(c)

        if wage_col_candidates:
            best_df = df.copy()
            best_col = wage_col_candidates[0]
            break

    if best_df is None or best_col is None:
        raise RuntimeError("Could not find a wages table with an annual wages column")

    return best_df, best_col


def fetch_fbref_wages_for_season(season: str, sleep_seconds: float = 1.0) -> pd.DataFrame:
    """
    Fetches FBref Premier League wages table for a given season and returns a clean dataframe:
    columns: club, season, total_wage_bill_gbp
    """
    slug = season_slug(season)
    url = f"https://fbref.com/en/comps/9/{slug}/wages/Premier-League-Wages"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; final-year-project; +https://github.com/)"
    }

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    # FBref tables are standard HTML tables
    tables = pd.read_html(r.text)
    wages_df, wage_col = find_wages_table(tables)

    # Normalise club column name
    club_col = None
    for c in wages_df.columns:
        cl = str(c).strip().lower()
        if cl in {"squad", "club", "team"}:
            club_col = c
            break
    if club_col is None:
        raise RuntimeError("Could not identify club column")

    out = wages_df[[club_col, wage_col]].copy()
    out.columns = ["club", "total_wage_bill_gbp_raw"]

    out["season"] = season
    out["total_wage_bill_gbp"] = out["total_wage_bill_gbp_raw"].apply(parse_money_to_gbp)

    # Remove rows that are not clubs
    out = out.dropna(subset=["club"]).copy()
    out["club"] = out["club"].astype(str).str.strip()

    # Keep only rows where we parsed a wage figure
    out = out.dropna(subset=["total_wage_bill_gbp"]).copy()

    # Final shape
    out = out[["club", "season", "total_wage_bill_gbp"]].reset_index(drop=True)

    time.sleep(sleep_seconds)
    return out


def make_season_list(start_season: str, end_season: str) -> list[str]:
    """
    Builds inclusive season list from start to end.
    Example: 2013-2014 to 2015-2016 returns
    ['2013-2014', '2014-2015', '2015-2016']
    """
    sm = re.match(r"^(\d{4})-(\d{4})$", start_season)
    em = re.match(r"^(\d{4})-(\d{4})$", end_season)
    if not sm or not em:
        raise ValueError("Seasons must be in YYYY-YYYY format")

    start_year = int(sm.group(1))
    end_year = int(em.group(1))

    if end_year < start_year:
        raise ValueError("End season must be after start season")

    seasons = []
    for y in range(start_year, end_year + 1):
        seasons.append(f"{y}-{y+1}")
    return seasons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2013-2014", help="Start season in YYYY-YYYY")
    parser.add_argument("--end", default="2023-2024", help="End season in YYYY-YYYY")
    parser.add_argument("--outdir", default="data/raw/fbref_wages", help="Output directory")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between requests")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    seasons = make_season_list(args.start, args.end)

    results = []
    failures = []

    for s in seasons:
        try:
            df = fetch_fbref_wages_for_season(s, sleep_seconds=args.sleep)
            outfile = os.path.join(args.outdir, f"wages_{s.replace('-', '_')}.csv")
            df.to_csv(outfile, index=False)
            results.append((s, len(df), outfile))
            print(f"Saved {s} with {len(df)} rows -> {outfile}")
        except Exception as e:
            failures.append((s, str(e)))
            print(f"FAILED {s}: {e}")

    # Write a simple run log
    log_path = os.path.join(args.outdir, "run_log.csv")
    pd.DataFrame(results, columns=["season", "rows", "file"]).to_csv(log_path, index=False)

    fail_path = os.path.join(args.outdir, "failures.csv")
    pd.DataFrame(failures, columns=["season", "error"]).to_csv(fail_path, index=False)

    print(f"Done. Log: {log_path}. Failures: {fail_path}.")


if __name__ == "__main__":
    main()
