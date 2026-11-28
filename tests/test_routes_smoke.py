"""Route smoke tests (no DB) via the Flask test client.

These confirm the URL table loads, protected routes redirect anonymous
users, and the login/register pages render."""

import pytest


def test_index_redirects_to_dashboard(client):
    r = client.get("/")
    assert r.status_code in (301, 302)
    assert "/dashboard" in r.headers["Location"]


def test_dashboard_requires_login(client):
    r = client.get("/dashboard")
    assert r.status_code in (301, 302)
    assert "/login" in r.headers["Location"]


def test_household_requires_login(client):
    r = client.get("/household/10")
    assert r.status_code in (301, 302)
    assert "/login" in r.headers["Location"]


def test_upload_requires_login(client):
    r = client.get("/upload")
    assert r.status_code in (301, 302)
    assert "/login" in r.headers["Location"]


def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert b"Sign in" in r.data


def test_register_page_renders(client):
    r = client.get("/register")
    assert r.status_code == 200
    assert b"Create an account" in r.data
