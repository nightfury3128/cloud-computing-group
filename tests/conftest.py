"""Shared fixtures. Tests that touch the real Azure SQL are marked `live`
and only run when SQL_SERVER/SQL_PASSWORD are set in the environment.

Pure-Python tests (csv parsing, validators) don't need the DB and run
unconditionally."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


def _db_configured() -> bool:
    return bool(os.environ.get("SQL_SERVER") and os.environ.get("SQL_PASSWORD"))


def pytest_collection_modifyitems(config, items):
    if _db_configured():
        return
    skip = pytest.mark.skip(reason="Azure SQL credentials not configured")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def app():
    from app import create_app
    a = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "WTF_CSRF_ENABLED": False})
    return a


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def pytest_configure(config):
    config.addinivalue_line("markers", "live: requires a live Azure SQL connection")
