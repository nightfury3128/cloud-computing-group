"""CSV upload parsing and inserts.

Accepts cleaned files (plain integers, ISO dates) and raw files (padded
with spaces, zero-padded IDs, "null" strings, "17-AUG-18" dates) per
analysis/clean.py conventions.

Each upload is one SQL transaction. Duplicate primary keys are skipped
rather than failing the whole file.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from . import db


# ---- schema ----
HOUSEHOLD_COLUMNS = [
    "HSHD_NUM", "L", "AGE_RANGE", "MARITAL", "INCOME_RANGE",
    "HOMEOWNER", "HSHD_COMPOSITION", "HH_SIZE", "CHILDREN",
]
PRODUCT_COLUMNS = [
    "PRODUCT_NUM", "DEPARTMENT", "COMMODITY", "BRAND_TY", "NATURAL_ORGANIC_FLAG",
]
# Raw transactions have PURCHASE_ (date string); cleaned ones also include DATE.
TRANSACTION_REQUIRED = [
    "BASKET_NUM", "HSHD_NUM", "PURCHASE_", "PRODUCT_NUM",
    "SPEND", "UNITS", "STORE_R", "WEEK_NUM", "YEAR",
]

INTEGER_FIELDS = {"HSHD_NUM", "PRODUCT_NUM", "BASKET_NUM", "YEAR", "WEEK_NUM"}
DECIMAL_FIELDS = {"SPEND", "UNITS"}


class CsvError(ValueError):
    """Raised when a CSV cannot be parsed or imported."""


@dataclass
class ImportResult:
    kind: str
    received: int
    inserted: int
    skipped_duplicates: int
    skipped_bad_rows: int
    errors: list[str]


def _norm_header(h: str) -> str:
    return (h or "").strip().upper().replace("﻿", "")


def _norm(value):
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "null":
        return None
    return s


def _parse_int(value, col):
    v = _norm(value)
    if v is None:
        return None
    try:
        # raw files pad with leading zeros - int() handles that.
        return int(v)
    except ValueError as e:
        raise CsvError(f"{col}: expected integer, got {value!r}") from e


def _parse_decimal(value, col):
    v = _norm(value)
    if v is None:
        return None
    try:
        return Decimal(v)
    except InvalidOperation as e:
        raise CsvError(f"{col}: expected number, got {value!r}") from e


def _parse_date(value):
    v = _norm(value)
    if v is None:
        return None
    # cleaned CSV: YYYY-MM-DD; raw: DD-MON-YY (e.g. 17-AUG-18)
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d-%B-%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise CsvError(f"PURCHASE_/DATE: unrecognised date {value!r}")


def _read_csv(data: bytes) -> tuple[list[str], list[dict]]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CsvError("CSV has no header row.")
    headers = [_norm_header(h) for h in reader.fieldnames]
    rows = []
    for raw in reader:
        rows.append({_norm_header(k): v for k, v in raw.items() if k is not None})
    return headers, rows


def _require_headers(got: list[str], required: list[str]) -> None:
    missing = [c for c in required if c not in got]
    if missing:
        raise CsvError(f"Missing required column(s): {', '.join(missing)}")


# ---- importers ---------------------------------------------------------

def import_households(data: bytes) -> ImportResult:
    headers, rows = _read_csv(data)
    _require_headers(headers, ["HSHD_NUM"])

    errors: list[str] = []
    skipped_bad = 0
    valid: list[tuple] = []

    for i, row in enumerate(rows, start=2):
        try:
            hshd = _parse_int(row.get("HSHD_NUM"), "HSHD_NUM")
            if hshd is None:
                raise CsvError("HSHD_NUM is required")
            valid.append((
                hshd,
                _norm(row.get("L")),
                _norm(row.get("AGE_RANGE")),
                _norm(row.get("MARITAL")),
                _norm(row.get("INCOME_RANGE")),
                _norm(row.get("HOMEOWNER")),
                _norm(row.get("HSHD_COMPOSITION")),
                _norm(row.get("HH_SIZE")),
                _norm(row.get("CHILDREN")),
            ))
        except CsvError as e:
            skipped_bad += 1
            if len(errors) < 10:
                errors.append(f"row {i}: {e}")

    if not valid:
        return ImportResult("households", len(rows), 0, 0, skipped_bad, errors)

    # Dedup within file against existing keys
    existing = {r["HSHD_NUM"] for r in db.query(
        "SELECT HSHD_NUM FROM dbo.households WHERE HSHD_NUM IN "
        + "(" + ",".join("?" for _ in valid) + ")",
        tuple(v[0] for v in valid),
    )} if valid else set()
    to_insert = [v for v in valid if v[0] not in existing]
    skipped_dupes = len(valid) - len(to_insert)

    if to_insert:
        db.executemany(
            "INSERT INTO dbo.households "
            "(HSHD_NUM, L, AGE_RANGE, MARITAL, INCOME_RANGE, HOMEOWNER, "
            " HSHD_COMPOSITION, HH_SIZE, CHILDREN) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            to_insert,
        )
    return ImportResult(
        kind="households",
        received=len(rows),
        inserted=len(to_insert),
        skipped_duplicates=skipped_dupes,
        skipped_bad_rows=skipped_bad,
        errors=errors,
    )


def import_products(data: bytes) -> ImportResult:
    headers, rows = _read_csv(data)
    _require_headers(headers, ["PRODUCT_NUM"])

    errors: list[str] = []
    skipped_bad = 0
    valid: list[tuple] = []

    for i, row in enumerate(rows, start=2):
        try:
            pnum = _parse_int(row.get("PRODUCT_NUM"), "PRODUCT_NUM")
            if pnum is None:
                raise CsvError("PRODUCT_NUM is required")
            valid.append((
                pnum,
                _norm(row.get("DEPARTMENT")),
                _norm(row.get("COMMODITY")),
                _norm(row.get("BRAND_TY")),
                _norm(row.get("NATURAL_ORGANIC_FLAG")),
            ))
        except CsvError as e:
            skipped_bad += 1
            if len(errors) < 10:
                errors.append(f"row {i}: {e}")

    if not valid:
        return ImportResult("products", len(rows), 0, 0, skipped_bad, errors)

    # Dedup in chunks of 500 (SQL Server parameter limit ~2100).
    existing: set[int] = set()
    for start in range(0, len(valid), 500):
        chunk = valid[start : start + 500]
        existing.update(r["PRODUCT_NUM"] for r in db.query(
            "SELECT PRODUCT_NUM FROM dbo.products WHERE PRODUCT_NUM IN "
            + "(" + ",".join("?" for _ in chunk) + ")",
            tuple(v[0] for v in chunk),
        ))
    to_insert = [v for v in valid if v[0] not in existing]
    skipped_dupes = len(valid) - len(to_insert)

    if to_insert:
        db.executemany(
            "INSERT INTO dbo.products "
            "(PRODUCT_NUM, DEPARTMENT, COMMODITY, BRAND_TY, NATURAL_ORGANIC_FLAG) "
            "VALUES (?, ?, ?, ?, ?)",
            to_insert,
        )
    return ImportResult("products", len(rows), len(to_insert), skipped_dupes, skipped_bad, errors)


def import_transactions(data: bytes) -> ImportResult:
    headers, rows = _read_csv(data)
    _require_headers(headers, TRANSACTION_REQUIRED)

    errors: list[str] = []
    skipped_bad = 0
    to_insert: list[tuple] = []

    for i, row in enumerate(rows, start=2):
        try:
            basket = _parse_int(row.get("BASKET_NUM"), "BASKET_NUM")
            hshd = _parse_int(row.get("HSHD_NUM"), "HSHD_NUM")
            prod = _parse_int(row.get("PRODUCT_NUM"), "PRODUCT_NUM")
            spend = _parse_decimal(row.get("SPEND"), "SPEND")
            units = _parse_decimal(row.get("UNITS"), "UNITS")
            week = _parse_int(row.get("WEEK_NUM"), "WEEK_NUM")
            year = _parse_int(row.get("YEAR"), "YEAR")
            # Prefer DATE if given, else derive from PURCHASE_
            purchase_raw = _norm(row.get("PURCHASE_"))
            date_val = _parse_date(row.get("DATE") or purchase_raw)
            if None in (basket, hshd, prod, week, year):
                raise CsvError("BASKET_NUM / HSHD_NUM / PRODUCT_NUM / WEEK_NUM / YEAR are required")
            to_insert.append((
                basket, hshd, purchase_raw, prod, spend, units,
                _norm(row.get("STORE_R")), week, year, date_val,
            ))
        except CsvError as e:
            skipped_bad += 1
            if len(errors) < 10:
                errors.append(f"row {i}: {e}")

    if to_insert:
        db.executemany(
            "INSERT INTO dbo.transactions "
            "(BASKET_NUM, HSHD_NUM, PURCHASE_, PRODUCT_NUM, SPEND, UNITS, "
            " STORE_R, WEEK_NUM, YEAR, [DATE]) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            to_insert,
        )
    # transactions has no natural PK in the source, so we rely on the user
    # not to upload the same file twice. We don't dedupe here.
    return ImportResult(
        kind="transactions",
        received=len(rows),
        inserted=len(to_insert),
        skipped_duplicates=0,
        skipped_bad_rows=skipped_bad,
        errors=errors,
    )


IMPORTERS = {
    "households": import_households,
    "products": import_products,
    "transactions": import_transactions,
}
