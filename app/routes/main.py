"""Catch-all routes: health check, favicon."""

from flask import Blueprint, current_app

from ..services import db

bp = Blueprint("main", __name__)


@bp.route("/healthz")
def healthz():
    try:
        db.scalar("SELECT 1")
        return {"ok": True}, 200
    except Exception as e:  # noqa: BLE001
        current_app.logger.exception("healthz failed")
        return {"ok": False, "error": str(e)}, 500
