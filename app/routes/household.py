"""Household pages: search, listing, detail analytics."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from ..services import analytics, households as hh
from .auth import login_required

bp = Blueprint("household", __name__)


def _parse_hshd(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw.isdigit():
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


@bp.route("/household", methods=("GET",))
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = hh.search_households(q, limit=25) if q else []
    hshd = None
    if q.isdigit():
        hshd = hh.get_household(int(q))
    return render_template(
        "household/search.html",
        q=q, results=results, hshd=hshd,
    )


@bp.route("/household/search", methods=("POST",))
@login_required
def search_submit():
    n = _parse_hshd(request.form.get("hshd_num", ""))
    if n is None:
        flash("Enter a positive HSHD_NUM.", "error")
        return redirect(url_for("household.search"))
    return redirect(url_for("household.detail", hshd_num=n))


@bp.route("/household/suggest", methods=("GET",))
@login_required
def suggest():
    q = request.args.get("q", "")
    return jsonify(hh.search_households(q, limit=10))


@bp.route("/household/<int:hshd_num>", methods=("GET",))
@login_required
def detail(hshd_num: int):
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = int(request.args.get("per_page", 50) or 50)
    per_page = max(10, min(per_page, 500))

    household = hh.get_household(hshd_num)
    rows, total = hh.transactions_page(hshd_num, page=page, per_page=per_page)
    summary = hh.spending_summary(hshd_num)

    if household is None and total == 0:
        return render_template(
            "household/not_found.html",
            hshd_num=hshd_num,
        ), 404

    trend = hh.household_trend(hshd_num)
    by_dept = hh.household_by_department(hshd_num)
    by_commodity = hh.household_by_commodity(hshd_num, top=12)
    brand_mix = hh.household_brand_mix(hshd_num)
    private_label = hh.private_label_savings(hshd_num)

    churn = analytics.load_churn(hshd_num)
    clv = analytics.load_clv(hshd_num)
    recs = analytics.load_recommendations(hshd_num)

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "household/detail.html",
        hshd_num=hshd_num,
        household=household,
        rows=rows,
        summary=summary,
        page=page, per_page=per_page, total=total, total_pages=total_pages,
        trend=trend, by_dept=by_dept, by_commodity=by_commodity,
        brand_mix=brand_mix, private_label=private_label,
        churn=churn, clv=clv, recs=recs,
    )
