"""Auth routes: /register, /login, /logout."""

from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..services import auth as auth_service

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = None
    if uid is not None:
        try:
            g.user = auth_service.get_user(uid)
        except Exception as e:  # noqa: BLE001
            current_app.logger.warning("load_user failed: %s", e)
            g.user = None


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        try:
            user = auth_service.register(
                request.form.get("username", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
            )
        except auth_service.AuthError as e:
            flash(str(e), "error")
            return render_template(
                "auth/register.html",
                form={"username": request.form.get("username", ""), "email": request.form.get("email", "")},
            )
        session.clear()
        session["user_id"] = user.id
        flash(f"Welcome, {user.username}!", "success")
        return redirect(url_for("dashboard.home"))
    return render_template("auth/register.html", form={})


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        try:
            user = auth_service.authenticate(
                request.form.get("username", ""),
                request.form.get("password", ""),
            )
        except auth_service.AuthError as e:
            flash(str(e), "error")
            return render_template(
                "auth/login.html",
                form={"username": request.form.get("username", "")},
            )
        session.clear()
        session["user_id"] = user.id
        flash(f"Signed in as {user.username}", "success")
        target = request.args.get("next") or url_for("dashboard.home")
        if not target.startswith("/"):
            target = url_for("dashboard.home")
        return redirect(target)
    return render_template("auth/login.html", form={})


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))
