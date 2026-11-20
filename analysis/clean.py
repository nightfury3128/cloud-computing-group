"""
Clean the retail analytics raw data (households, products, transactions).

Input  : ./data/raw/400_households.csv, 400_products.csv, 400_transactions.csv
Output : ./data/clean/households.csv
         ./data/clean/products.csv
         ./data/clean/transactions.csv   (filtered to the last 7 days of Aug-Dec, plus DATE)
         ./data/clean/joined.csv         (transactions + products + households, sorted)

Run from the project root:
    python analysis/clean.py

Notes for teammates
- The raw files pad column names and values with spaces, so we read every column as text,
  strip it, and only then convert types.
- ID columns (HSHD_NUM, BASKET_NUM, PRODUCT_NUM) are zero-padded in the raw files
  (e.g. "0010"). We convert them to integers so joins and sorts are simple and
  HSHD_NUM == 10 works. The leading zeros are not kept in the output.
- Household attributes such as HH_SIZE ("5+") and CHILDREN ("3+") stay as text.
- Cleaning only reformats the source data. It does not add interpretive columns
  (e.g. "is this a return?") or fill in missing values; each analysis does that
  itself and documents its choice. Rows with zero or negative SPEND/UNITS are kept
  and counted in the report below.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to the project root, which is the parent of this script's folder)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"

# Months to keep (Aug-Dec) and how many days at the end of each month to keep.
KEEP_MONTHS = [8, 9, 10, 11, 12]
LAST_N_DAYS = 7

SORT_COLUMNS = ["HSHD_NUM", "BASKET_NUM", "DATE", "PRODUCT_NUM", "DEPARTMENT", "COMMODITY"]


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------
def load_raw_csv(filename):
    """Read a raw CSV as text, strip whitespace from headers and values,
    and turn the string "null" (and empty strings) into real NaN."""
    # dtype=str keeps zero-padded IDs intact until we convert them ourselves.
    # keep_default_na=False stops pandas from guessing NaNs; we handle "null" below.
    df = pd.read_csv(RAW_DIR / filename, dtype=str, keep_default_na=False)

    df.columns = df.columns.str.strip()
    for col in df.columns:
        df[col] = df[col].str.strip()

    # "null" and "" both mean missing.
    df = df.replace({"null": np.nan, "": np.nan})
    return df


def load_households():
    df = load_raw_csv("400_households.csv")
    df["HSHD_NUM"] = df["HSHD_NUM"].astype(int)
    return df


def load_products():
    df = load_raw_csv("400_products.csv")
    df["PRODUCT_NUM"] = df["PRODUCT_NUM"].astype(int)
    return df


def load_transactions():
    df = load_raw_csv("400_transactions.csv")

    # IDs -> integers
    for col in ["BASKET_NUM", "HSHD_NUM", "PRODUCT_NUM"]:
        df[col] = df[col].astype(int)

    # Numeric measures
    df["SPEND"] = pd.to_numeric(df["SPEND"])   # values like ".59" parse fine
    df["UNITS"] = pd.to_numeric(df["UNITS"])
    df["WEEK_NUM"] = df["WEEK_NUM"].astype(int)
    df["YEAR"] = df["YEAR"].astype(int)

    # PURCHASE_ looks like "17-AUG-18" -> day-monthabbrev-2digityear
    df["DATE"] = pd.to_datetime(df["PURCHASE_"], format="%d-%b-%y")
    return df


# ---------------------------------------------------------------------------
# Cleaning steps
# ---------------------------------------------------------------------------
def filter_last_days_of_months(df):
    """Keep only rows from the last LAST_N_DAYS days of the months in KEEP_MONTHS.
    A row is kept when day >= days_in_month - (LAST_N_DAYS - 1),
    e.g. Aug 25-31, Sep 24-30, Nov 24-30."""
    in_month = df["DATE"].dt.month.isin(KEEP_MONTHS)
    in_last_days = df["DATE"].dt.day >= df["DATE"].dt.days_in_month - (LAST_N_DAYS - 1)
    return df[in_month & in_last_days].copy()


def join_tables(transactions, products, households):
    """Left-join so every transaction is kept, even if its product or
    household is missing from the lookup tables (those columns become NaN)."""
    joined = transactions.merge(products, on="PRODUCT_NUM", how="left")
    joined = joined.merge(households, on="HSHD_NUM", how="left")
    joined = joined.sort_values(SORT_COLUMNS).reset_index(drop=True)
    return joined


# ---------------------------------------------------------------------------
# Data quality report
# ---------------------------------------------------------------------------
def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_quality_report(raw_tx, tx, products, households, joined):
    print_section("ROW COUNTS")
    print(f"Households              : {len(households):,}")
    print(f"Products                : {len(products):,}")
    print(f"Transactions (raw)      : {len(raw_tx):,}")
    print(f"Transactions (filtered) : {len(tx):,}  "
          f"({len(tx) / len(raw_tx):.1%} of raw)")
    print(f"Households in filtered  : {tx['HSHD_NUM'].nunique():,}")
    print(f"Years in filtered       : {sorted(tx['DATE'].dt.year.unique().tolist())}")

    print_section("FILTERED ROWS PER YEAR AND MONTH")
    per_month = (
        tx.groupby([tx["DATE"].dt.year.rename("YEAR"), tx["DATE"].dt.month.rename("MONTH")])
        .agg(ROWS=("DATE", "size"), FIRST_DAY=("DATE", "min"), LAST_DAY=("DATE", "max"))
    )
    per_month["FIRST_DAY"] = per_month["FIRST_DAY"].dt.strftime("%Y-%m-%d")
    per_month["LAST_DAY"] = per_month["LAST_DAY"].dt.strftime("%Y-%m-%d")
    print(per_month.to_string())

    # These rows are kept as-is. The data doesn't say why they exist
    # (refunds, free items, coupons, ...), so each analysis decides how to treat them.
    print_section("ZERO OR NEGATIVE SPEND / UNITS (kept, not flagged)")
    print(f"SPEND < 0 : {(tx['SPEND'] < 0).sum():,}")
    print(f"SPEND = 0 : {(tx['SPEND'] == 0).sum():,}")
    print(f"UNITS < 0 : {(tx['UNITS'] < 0).sum():,}")
    print(f"UNITS = 0 : {(tx['UNITS'] == 0).sum():,}")

    print_section("REFERENTIAL INTEGRITY")
    missing_products = set(tx["PRODUCT_NUM"]) - set(products["PRODUCT_NUM"])
    missing_hshds = set(tx["HSHD_NUM"]) - set(households["HSHD_NUM"])
    rows_missing_product = tx["PRODUCT_NUM"].isin(missing_products).sum()
    print(f"Products in transactions missing from products.csv : "
          f"{len(missing_products):,} products, {rows_missing_product:,} rows")
    if missing_products:
        print(f"  examples: {sorted(missing_products)[:10]}")
    print(f"Households in transactions missing from households.csv: {len(missing_hshds):,}")

    print_section("NULL COUNTS PER COLUMN")
    for name, df in [("households", households), ("products", products),
                     ("transactions (filtered)", tx), ("joined", joined)]:
        print(f"\n-- {name} ({len(df):,} rows)")
        print(df.isna().sum().to_string())


def print_sanity_check(joined, hshd_num=10):
    print_section(f"SANITY CHECK: HSHD_NUM = {hshd_num}")
    rows = joined[joined["HSHD_NUM"] == hshd_num]
    print(f"{len(rows):,} rows (expected about 137)\n")
    with pd.option_context("display.max_rows", None, "display.width", 250,
                           "display.max_columns", None):
        print(rows[SORT_COLUMNS + ["SPEND", "UNITS"]].to_string(index=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # 1-2. Load and parse
    households = load_households()
    products = load_products()
    raw_transactions = load_transactions()

    # 3. Keep only the last 7 days of Aug-Dec
    transactions = filter_last_days_of_months(raw_transactions)

    # 4. Join and sort
    joined = join_tables(transactions, products, households)

    # 5. Save
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    households.to_csv(CLEAN_DIR / "households.csv", index=False)
    products.to_csv(CLEAN_DIR / "products.csv", index=False)
    transactions.sort_values(SORT_COLUMNS[:4]).to_csv(
        CLEAN_DIR / "transactions.csv", index=False, date_format="%Y-%m-%d")
    joined.to_csv(CLEAN_DIR / "joined.csv", index=False, date_format="%Y-%m-%d")
    print(f"Saved cleaned files to {CLEAN_DIR}")

    # 6. Data quality report
    print_quality_report(raw_transactions, transactions, products, households, joined)

    # 7. Sanity check
    print_sanity_check(joined, hshd_num=10)


if __name__ == "__main__":
    main()
