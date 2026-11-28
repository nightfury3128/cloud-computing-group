"""Flask application factory for the Retail Analytics web app."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, redirect, url_for

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    app = Flask(__name__, instance_relative_config=True)

    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-insecure-change-me"),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_BYTES", 52_428_800)),
        SQL_SERVER=os.environ.get("SQL_SERVER", ""),
        SQL_DB=os.environ.get("SQL_DB", ""),
        SQL_ADMIN=os.environ.get("SQL_ADMIN", ""),
        SQL_PASSWORD=os.environ.get("SQL_PASSWORD", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_SESSION_COOKIE_SECURE", "0") == "1",
        PROJECT_ROOT=str(PROJECT_ROOT),
    )

    if test_config:
        app.config.update(test_config)

    # Register blueprints
    from .routes import auth, dashboard, household, upload, main

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(household.bp)
    app.register_blueprint(upload.bp)

    # Ensure the app_users table exists (idempotent).
    from .services import db, auth as auth_service

    @app.teardown_appcontext
    def _close_db(exc):  # noqa: ARG001
        conn = g.pop("db_conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    with app.app_context():
        try:
            auth_service.ensure_users_table()
        except Exception as e:  # noqa: BLE001
            app.logger.warning("Could not ensure app_users table: %s", e)

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.home"))

    return app
