"""CSV upload route."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..services import csv_import, db
from .auth import login_required

bp = Blueprint("upload", __name__)

MAX_FILENAME_LEN = 255


@bp.route("/upload", methods=("GET",))
@login_required
def form():
    return render_template("upload.html", result=None)


@bp.route("/upload", methods=("POST",))
@login_required
def submit():
    kind = request.form.get("kind", "").strip()
    if kind not in csv_import.IMPORTERS:
        flash("Pick a dataset to upload.", "error")
        return redirect(url_for("upload.form"))

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Attach a CSV file.", "error")
        return redirect(url_for("upload.form"))
    if len(f.filename) > MAX_FILENAME_LEN or not f.filename.lower().endswith(".csv"):
        flash("Only .csv files are accepted.", "error")
        return redirect(url_for("upload.form"))

    data = f.read()
    if not data:
        flash("The uploaded file was empty.", "error")
        return redirect(url_for("upload.form"))

    try:
        result = csv_import.IMPORTERS[kind](data)
        db.commit()
    except csv_import.CsvError as e:
        db.rollback()
        flash(f"Upload failed: {e}", "error")
        return redirect(url_for("upload.form"))
    except Exception as e:  # noqa: BLE001
        db.rollback()
        current_app.logger.exception("upload failed")
        flash(f"Upload failed unexpectedly: {e}", "error")
        return redirect(url_for("upload.form"))

    flash(
        f"{kind}: imported {result.inserted:,} row(s), "
        f"{result.skipped_duplicates:,} duplicate(s), "
        f"{result.skipped_bad_rows:,} invalid.",
        "success",
    )
    return render_template("upload.html", result=result)
