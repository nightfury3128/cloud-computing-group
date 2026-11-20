# Retail Analytics – Final Project

Cleaned data for the retail case study (about 400 households, AnalyticsIQ sample), filtered to the assignment's time window and ready for the database, dashboard and ML parts.

**If you only need the data:** use the CSVs in [`data/clean/`](data/clean/). You don't need to run anything.

## Which file to use

| File | Rows | Use it for |
|---|---|---|
| `households.csv` | 400 | Loading into the database (households table) |
| `products.csv` | 67,284 | Loading into the database (products table) |
| `transactions.csv` | 84,609 | Loading into the database (transactions table) |
| `joined.csv` | 84,609 | Analysis (dashboard, churn, CLV, basket) and checking the web app's output |

**Don't load `joined.csv` into the database.** Requirement 5 lets users upload new households, products and transactions CSVs, and the search page (Requirement 4) has to show the new data. That only works if the database stores the three tables separately and the join happens in the query.

**Checking the web app:** `joined.csv` is already joined and sorted the way Requirements 3 and 4 ask (HSHD_NUM → BASKET_NUM → DATE → PRODUCT_NUM → DEPARTMENT → COMMODITY). The page for `HSHD_NUM = 10` should show the same **137 rows** in the same order.

## What the cleaning did

The cleaning only reformats the source data. No rows were removed for quality reasons, no missing values were filled in, and the only new column is `DATE`, a parsed copy of `PURCHASE_`.

1. **Stripped whitespace.** The raw files pad column names and values with spaces (`"HSHD_NUM        "`).
2. **Turned `"null"` into real missing values.** In the CSVs they appear as empty fields. When loading into SQL, make sure empty fields become `NULL`, not `''`.
3. **Converted IDs to integers.** `HSHD_NUM`, `BASKET_NUM` and `PRODUCT_NUM` are zero-padded in the raw files (`0010`). They are plain numbers now (`10`).
4. **Added a `DATE` column** parsed from `PURCHASE_` (`17-AUG-18` → `2018-08-17`). The original `PURCHASE_` column is kept.
5. **Kept only the last 7 days of August–December**, as the assignment requires. See [Time window](#time-window) below.
6. **Joined the three tables** (left joins, so every transaction is kept) and sorted them, for `joined.csv` only.

Columns are the same as the raw files, plus `DATE` in transactions.

`households.csv` keeps all 400 households, but only **347** have transactions in the time window. The other 53 have none, so they don't appear in `joined.csv`. `products.csv` keeps all 67,284 products, including ones never bought in the window.

### Checks that passed

- No duplicate rows, and no product appears twice in the same basket
- Every basket belongs to exactly one household
- Every product and household in the transactions exists in products and households
- `DATE` and `YEAR` always agree

## Things to know before analysing

### Time window

The assignment says to use only these days for all analysis:

| Month | Days kept |
|---|---|
| August | 25–31 |
| September | 24–30 |
| October | 25–31 |
| November | 24–30 |
| December | 25–31 (no transactions on the 25th) |

After filtering, only **2018 and 2019** remain. The raw data ends on 2020-08-15, before the August window, so there is no 2020 (or COVID-period) data in the filtered set. That leaves **10 one-week windows**, which limits what churn and forecasting can do. For example, "inactive for 3 months" can't be measured. Compare 2019 windows with 2018, or count how many of the 10 windows a household shopped in.

### Zero and negative spend

These rows are kept and not flagged, because the data doesn't say why they exist:

| | Rows | Possible meaning |
|---|---|---|
| `SPEND < 0` | 71 | Refunds or returns |
| `SPEND = 0` | 304 | Free items, coupons, promotions (almost all have `UNITS = 1`) |
| `UNITS < 0` | 42 | Returns |
| `UNITS = 0` | 9 | Unclear |

Decide in your own analysis whether to drop them, and write the rule in the report. For example: keep them when summing revenue, drop them for basket analysis and purchase counts.

### Missing household demographics

| Column | Missing (of 400) |
|---|---|
| `AGE_RANGE` | 61 |
| `MARITAL` | 67 |
| `INCOME_RANGE` | 55 |
| `HOMEOWNER` | 70 |
| `HSHD_COMPOSITION` | 55 |
| `HH_SIZE` | 68 |
| `CHILDREN` | 228 |

Missing values were left missing, not filled in. Two things to watch:

- **`CHILDREN` is mostly missing for households without children.** Of the 228 missing, 160 have a `HSHD_COMPOSITION` with no kids (`2 Adults`, `Single Male`, `Single Female`, `1 Adult`). If you drop rows with missing `CHILDREN`, you drop most childless households. To compare households with and without kids, group by whether `HSHD_COMPOSITION` contains `Kids` instead.
- **55 households (14%) have no demographics at all.** Show them as an "Unknown" group or exclude them, and say which.

`HH_SIZE` (`5+`) and `CHILDREN` (`3+`) are text, not numbers.

## Re-running the cleaning

You only need this if the raw data or the cleaning rules change.

1. Download `The_Complete_Retail_Journey_Sample.zip` from the assignment page and put the three CSVs in `data/raw/`. That folder isn't in git, because `400_transactions.csv` is 128 MB and GitHub rejects files over 100 MB.
2. Install the requirements (pandas 2.x or 3.x):
   ```
   pip install -r requirements.txt
   ```
3. Run from the project root:
   ```
   python analysis/clean.py
   ```

It takes a few seconds, overwrites `data/clean/`, and prints a data quality report. The report covers row counts, rows per month, zero or negative spend, missing products and nulls per column, and ends with the 137 rows for household 10.

### For the CSV upload feature (Requirement 5)

If uploaded files are in the raw format (padded with spaces, `"null"` for missing values, zero-padded IDs), they need the same cleaning before they go into the database. The logic in `load_raw_csv()` and the `load_*()` functions in [`analysis/clean.py`](analysis/clean.py) can be reused, but they currently read only from `data/raw/` by file name. To clean an uploaded file, change them to accept a file path or file object.
