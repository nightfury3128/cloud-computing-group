"""Household queries against Azure SQL.

All queries are parameterised. The join order and sort order follow the
assignment README: HSHD_NUM -> BASKET_NUM -> DATE -> PRODUCT_NUM ->
DEPARTMENT -> COMMODITY.
"""

from __future__ import annotations

from typing import Any

from . import db


SORT_CLAUSE = (
    "ORDER BY t.HSHD_NUM, t.BASKET_NUM, t.[DATE], t.PRODUCT_NUM, "
    "p.DEPARTMENT, p.COMMODITY"
)

# Columns selected for the transaction grid.
BASE_SELECT = """
SELECT
    t.HSHD_NUM, t.BASKET_NUM, t.[DATE] AS PURCHASE_DATE, t.PRODUCT_NUM,
    p.DEPARTMENT, p.COMMODITY, p.BRAND_TY, p.NATURAL_ORGANIC_FLAG,
    t.SPEND, t.UNITS, t.STORE_R, t.WEEK_NUM, t.YEAR
FROM dbo.transactions t
LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
"""


def get_household(hshd_num: int) -> dict | None:
    return db.query_one(
        "SELECT HSHD_NUM, L, AGE_RANGE, MARITAL, INCOME_RANGE, HOMEOWNER, "
        "HSHD_COMPOSITION, HH_SIZE, CHILDREN FROM dbo.households WHERE HSHD_NUM = ?",
        (int(hshd_num),),
    )


def count_transactions(hshd_num: int) -> int:
    val = db.scalar(
        "SELECT COUNT(*) FROM dbo.transactions WHERE HSHD_NUM = ?",
        (int(hshd_num),),
    )
    return int(val or 0)


def spending_summary(hshd_num: int) -> dict:
    row = db.query_one(
        """
        SELECT
            COUNT(*) AS lines,
            COUNT(DISTINCT BASKET_NUM) AS baskets,
            COALESCE(SUM(SPEND), 0) AS total_spend,
            COALESCE(SUM(UNITS), 0) AS total_units,
            MIN([DATE]) AS first_date,
            MAX([DATE]) AS last_date
        FROM dbo.transactions WHERE HSHD_NUM = ?
        """,
        (int(hshd_num),),
    )
    return row or {
        "lines": 0, "baskets": 0, "total_spend": 0, "total_units": 0,
        "first_date": None, "last_date": None,
    }


def transactions_page(
    hshd_num: int,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """Return a page of transactions for a household plus the total row count."""
    page = max(1, int(page))
    per_page = max(10, min(int(per_page), 500))
    offset = (page - 1) * per_page

    rows = db.query(
        BASE_SELECT
        + " WHERE t.HSHD_NUM = ? "
        + SORT_CLAUSE
        + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (int(hshd_num), offset, per_page),
    )
    total = count_transactions(hshd_num)
    return rows, total


def search_households(query: str, limit: int = 20) -> list[dict]:
    """Suggest households by number prefix. Handy for search autocomplete."""
    q = (query or "").strip()
    if not q.isdigit():
        return []
    like = f"{q}%"
    return db.query(
        """
        SELECT TOP (?) HSHD_NUM, HSHD_COMPOSITION, INCOME_RANGE
        FROM dbo.households
        WHERE CAST(HSHD_NUM AS NVARCHAR(20)) LIKE ?
        ORDER BY HSHD_NUM
        """,
        (int(limit), like),
    )


def dashboard_totals() -> dict:
    """Headline counts for the dashboard."""
    hh = db.scalar("SELECT COUNT(*) FROM dbo.households") or 0
    tx = db.scalar("SELECT COUNT(*) FROM dbo.transactions") or 0
    pr = db.scalar("SELECT COUNT(*) FROM dbo.products") or 0
    spend = db.scalar("SELECT COALESCE(SUM(SPEND), 0) FROM dbo.transactions") or 0
    baskets = db.scalar("SELECT COUNT(DISTINCT BASKET_NUM) FROM dbo.transactions") or 0
    return {
        "households": int(hh),
        "transactions": int(tx),
        "products": int(pr),
        "total_spend": float(spend),
        "baskets": int(baskets),
    }


def spend_by_year() -> list[dict]:
    return db.query(
        """
        SELECT YEAR AS year,
               COUNT(*) AS lines,
               COALESCE(SUM(SPEND), 0) AS spend
        FROM dbo.transactions
        GROUP BY YEAR
        ORDER BY YEAR
        """
    )


def spend_by_department(top: int = 12) -> list[dict]:
    return db.query(
        """
        SELECT TOP (?) p.DEPARTMENT AS department,
               COUNT(*) AS lines,
               COALESCE(SUM(t.SPEND), 0) AS spend
        FROM dbo.transactions t
        LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
        GROUP BY p.DEPARTMENT
        ORDER BY spend DESC
        """,
        (int(top),),
    )


def spend_by_month() -> list[dict]:
    return db.query(
        """
        SELECT YEAR([DATE]) AS year, MONTH([DATE]) AS month,
               COUNT(*) AS lines,
               COALESCE(SUM(SPEND), 0) AS spend
        FROM dbo.transactions
        GROUP BY YEAR([DATE]), MONTH([DATE])
        ORDER BY year, month
        """
    )


def household_trend(hshd_num: int) -> list[dict]:
    return db.query(
        """
        SELECT YEAR([DATE]) AS year, MONTH([DATE]) AS month,
               COUNT(*) AS lines,
               COALESCE(SUM(SPEND), 0) AS spend
        FROM dbo.transactions
        WHERE HSHD_NUM = ?
        GROUP BY YEAR([DATE]), MONTH([DATE])
        ORDER BY year, month
        """,
        (int(hshd_num),),
    )


def household_by_department(hshd_num: int) -> list[dict]:
    return db.query(
        """
        SELECT p.DEPARTMENT AS department,
               COUNT(*) AS lines,
               COALESCE(SUM(t.SPEND), 0) AS spend,
               COALESCE(SUM(t.UNITS), 0) AS units
        FROM dbo.transactions t
        LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
        WHERE t.HSHD_NUM = ?
        GROUP BY p.DEPARTMENT
        ORDER BY spend DESC
        """,
        (int(hshd_num),),
    )


def household_by_commodity(hshd_num: int, top: int = 15) -> list[dict]:
    return db.query(
        """
        SELECT TOP (?) p.COMMODITY AS commodity,
               p.DEPARTMENT AS department,
               COUNT(*) AS lines,
               COALESCE(SUM(t.SPEND), 0) AS spend
        FROM dbo.transactions t
        LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
        WHERE t.HSHD_NUM = ?
        GROUP BY p.COMMODITY, p.DEPARTMENT
        ORDER BY spend DESC
        """,
        (int(top), int(hshd_num)),
    )


def household_brand_mix(hshd_num: int) -> list[dict]:
    return db.query(
        """
        SELECT p.BRAND_TY AS brand,
               COUNT(*) AS lines,
               COALESCE(SUM(t.SPEND), 0) AS spend
        FROM dbo.transactions t
        LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
        WHERE t.HSHD_NUM = ?
        GROUP BY p.BRAND_TY
        ORDER BY spend DESC
        """,
        (int(hshd_num),),
    )


def private_label_savings(hshd_num: int) -> dict:
    """Rough estimate: how much a household already saves by buying PRIVATE
    products, assuming NATIONAL equivalents would cost ~22% more (industry average
    private-label discount). Clearly labelled as an estimate in the UI."""
    row = db.query_one(
        """
        SELECT
            COALESCE(SUM(CASE WHEN p.BRAND_TY = 'PRIVATE' THEN t.SPEND ELSE 0 END), 0) AS private_spend,
            COALESCE(SUM(CASE WHEN p.BRAND_TY = 'NATIONAL' THEN t.SPEND ELSE 0 END), 0) AS national_spend,
            COALESCE(SUM(t.SPEND), 0) AS total_spend
        FROM dbo.transactions t
        LEFT JOIN dbo.products p ON p.PRODUCT_NUM = t.PRODUCT_NUM
        WHERE t.HSHD_NUM = ?
        """,
        (int(hshd_num),),
    ) or {}
    private = float(row.get("private_spend") or 0)
    national = float(row.get("national_spend") or 0)
    total = float(row.get("total_spend") or 0)
    # Savings captured: private lines priced ~22% below their national equivalents
    est_savings = round(private * 0.22, 2)
    # Potential if national lines were switched to private
    est_potential = round(national * 0.22, 2)
    private_share = round((private / total) * 100, 1) if total else 0.0
    return {
        "private_spend": round(private, 2),
        "national_spend": round(national, 2),
        "total_spend": round(total, 2),
        "private_share_pct": private_share,
        "est_savings_realised": est_savings,
        "est_savings_potential": est_potential,
    }
