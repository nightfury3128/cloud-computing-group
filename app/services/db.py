"""Thin Azure SQL connection helper that reuses the project's mssql_python driver.

- One connection per request, stored on flask.g and closed in teardown.
- `query()` / `execute()` wrappers handle parameterised SQL safely.
- `fetch_dicts()` returns rows as dict for easy template use.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Sequence

import mssql_python
from flask import current_app, g


def _server_fqdn(server: str) -> str:
    if not server:
        return server
    return server if server.endswith(".database.windows.net") else server + ".database.windows.net"


def connect():
    """Create a new mssql_python connection from current_app config."""
    cfg = current_app.config
    return mssql_python.connect(
        server=_server_fqdn(cfg["SQL_SERVER"]),
        database=cfg["SQL_DB"],
        uid=cfg["SQL_ADMIN"],
        pwd=cfg["SQL_PASSWORD"],
        encrypt="yes",
        trustservercertificate="no",
        autocommit=False,
    )


def get_conn():
    """Return (or create) the connection bound to this request."""
    if "db_conn" not in g:
        g.db_conn = connect()
    return g.db_conn


@contextmanager
def cursor():
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:  # noqa: BLE001
            pass


def _columns(cur) -> list[str]:
    return [d[0] for d in cur.description] if cur.description else []


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict]:
    """Run a SELECT and return rows as dicts."""
    with cursor() as cur:
        if params is not None:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        cols = _columns(cur)
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def scalar(sql: str, params: Sequence[Any] | None = None):
    with cursor() as cur:
        if params is not None:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None


def execute(sql: str, params: Sequence[Any] | None = None, commit: bool = True) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns rowcount."""
    conn = get_conn()
    with cursor() as cur:
        if params is not None:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        rc = cur.rowcount
    if commit:
        conn.commit()
    return rc


def executemany(sql: str, rows: Iterable[Sequence[Any]], commit: bool = True) -> int:
    conn = get_conn()
    total = 0
    with cursor() as cur:
        batch: list[Sequence[Any]] = []
        for r in rows:
            batch.append(tuple(r))
            if len(batch) >= 500:
                cur.executemany(sql, batch)
                total += len(batch)
                batch = []
        if batch:
            cur.executemany(sql, batch)
            total += len(batch)
    if commit:
        conn.commit()
    return total


def commit():
    get_conn().commit()


def rollback():
    try:
        get_conn().rollback()
    except Exception:  # noqa: BLE001
        pass
