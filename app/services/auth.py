"""User registration / login helpers backed by dbo.app_users."""

from __future__ import annotations

import re
from dataclasses import dataclass

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(ValueError):
    pass


@dataclass
class User:
    id: int
    username: str
    email: str


def ensure_users_table() -> None:
    """Idempotently create dbo.app_users and supporting indexes."""
    db.execute(
        """
        IF OBJECT_ID('dbo.app_users', 'U') IS NULL
        CREATE TABLE dbo.app_users (
            id            INT IDENTITY(1,1) PRIMARY KEY,
            username      NVARCHAR(64)  NOT NULL UNIQUE,
            email         NVARCHAR(254) NOT NULL UNIQUE,
            password_hash NVARCHAR(255) NOT NULL,
            created_at    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
        )
        """
    )


def validate_registration(username: str, email: str, password: str) -> None:
    username = (username or "").strip()
    email = (email or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3-64 chars, letters/numbers/._-")
    if not EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address")
    if not password or len(password) < 8:
        raise AuthError("Password must be at least 8 characters")
    if password.lower() in {"password", "12345678", "qwertyui"}:
        raise AuthError("Password is too common")


def register(username: str, email: str, password: str) -> User:
    username = username.strip()
    email = email.strip().lower()
    validate_registration(username, email, password)

    existing = db.query_one(
        "SELECT id FROM dbo.app_users WHERE username = ? OR email = ?",
        (username, email),
    )
    if existing:
        raise AuthError("Username or email already in use")

    db.execute(
        "INSERT INTO dbo.app_users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, generate_password_hash(password)),
    )
    row = db.query_one(
        "SELECT id, username, email FROM dbo.app_users WHERE username = ?",
        (username,),
    )
    assert row is not None
    return User(id=row["id"], username=row["username"], email=row["email"])


def authenticate(username_or_email: str, password: str) -> User:
    ident = (username_or_email or "").strip().lower()
    if not ident or not password:
        raise AuthError("Enter your credentials")

    row = db.query_one(
        "SELECT id, username, email, password_hash FROM dbo.app_users "
        "WHERE LOWER(username) = ? OR LOWER(email) = ?",
        (ident, ident),
    )
    if not row or not check_password_hash(row["password_hash"], password):
        raise AuthError("Invalid credentials")
    return User(id=row["id"], username=row["username"], email=row["email"])


def get_user(user_id: int) -> User | None:
    row = db.query_one(
        "SELECT id, username, email FROM dbo.app_users WHERE id = ?",
        (int(user_id),),
    )
    if not row:
        return None
    return User(id=row["id"], username=row["username"], email=row["email"])
