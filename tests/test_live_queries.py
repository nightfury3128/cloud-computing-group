"""Live tests against Azure SQL.

Marked with `live` and skipped automatically when SQL_SERVER / SQL_PASSWORD
aren't set (see conftest.py)."""

import pytest


pytestmark = pytest.mark.live


def test_household_10_has_137_transactions(app):
    from app.services import households as hh
    with app.app_context():
        assert hh.count_transactions(10) == 137


def test_household_10_sort_order_matches_readme(app):
    """First row of HSHD_NUM=10 should match data/clean/joined.csv (6583 FOOD / IN STORE FOOD SERVICE)."""
    from app.services import households as hh
    with app.app_context():
        rows, total = hh.transactions_page(10, 1, 10)
    assert total == 137
    first = rows[0]
    assert first["HSHD_NUM"] == 10
    assert first["BASKET_NUM"] == 1120
    assert first["PRODUCT_NUM"] == 6583
    assert first["DEPARTMENT"] == "FOOD"
    assert first["COMMODITY"] == "IN STORE FOOD SERVICE"


def test_dashboard_totals_are_populated(app):
    from app.services import households as hh
    with app.app_context():
        t = hh.dashboard_totals()
    assert t["households"] == 400
    assert t["transactions"] == 84609
    assert t["products"] == 67284
    assert t["total_spend"] > 0


def test_search_for_household_10(app):
    from app.services import households as hh
    with app.app_context():
        results = hh.search_households("1", limit=25)
    hshd_nums = {r["HSHD_NUM"] for r in results}
    assert 10 in hshd_nums or 1 in hshd_nums
