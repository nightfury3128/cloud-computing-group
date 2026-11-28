"""Pure-Python tests for the CSV parser helpers (no DB)."""

from datetime import date
from decimal import Decimal

import pytest

from app.services import csv_import as ci


def test_norm_strips_and_nulls():
    assert ci._norm(" hello ") == "hello"
    assert ci._norm("") is None
    assert ci._norm("null") is None
    assert ci._norm("NULL") is None
    assert ci._norm(None) is None


def test_parse_int_handles_zero_padding():
    assert ci._parse_int("0010", "HSHD_NUM") == 10
    assert ci._parse_int("  42  ", "HSHD_NUM") == 42
    assert ci._parse_int("null", "HSHD_NUM") is None


def test_parse_int_rejects_garbage():
    with pytest.raises(ci.CsvError):
        ci._parse_int("abc", "HSHD_NUM")


def test_parse_decimal_handles_pennies():
    assert ci._parse_decimal(".59", "SPEND") == Decimal(".59")
    assert ci._parse_decimal("null", "SPEND") is None


def test_parse_date_supports_both_formats():
    assert ci._parse_date("2018-08-17") == date(2018, 8, 17)
    assert ci._parse_date("17-AUG-18") == date(2018, 8, 17)
    with pytest.raises(ci.CsvError):
        ci._parse_date("not-a-date")


def test_read_csv_strips_headers_and_bom():
    data = b"\xef\xbb\xbfHSHD_NUM , FOO \n 0010, hi \n"
    headers, rows = ci._read_csv(data)
    assert headers == ["HSHD_NUM", "FOO"]
    assert rows == [{"HSHD_NUM": " 0010", "FOO": " hi "}]


def test_require_headers():
    ci._require_headers(["A", "B"], ["A"])
    with pytest.raises(ci.CsvError):
        ci._require_headers(["A"], ["A", "B"])
