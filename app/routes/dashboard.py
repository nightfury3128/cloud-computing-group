"""Home dashboard."""

from __future__ import annotations

from flask import Blueprint, render_template

from ..services import households as hh
from .auth import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard", methods=("GET",))
@login_required
def home():
    totals = hh.dashboard_totals()
    by_year = hh.spend_by_year()
    by_dept = hh.spend_by_department(top=10)
    by_month = hh.spend_by_month()
    return render_template(
        "dashboard.html",
        totals=totals,
        by_year=by_year,
        by_dept=by_dept,
        by_month=by_month,
    )
