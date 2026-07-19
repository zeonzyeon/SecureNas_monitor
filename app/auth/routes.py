import sqlite3

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.auth.models import (
    create_login_log,
    create_user,
    get_user_by_id,
    get_user_by_username,
    is_ip_blocked,
    record_failed_login,
    reset_ip_failures,
    verify_user_password,
)


bp = Blueprint("auth", __name__)


def _home_for_role(role):
    if role == "admin":
        return url_for("main.dashboard")

    return url_for("main.files")


def _client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.remote_addr


def _blocked_login_response(status_code=429):
    block_minutes = current_app.config["LOGIN_BLOCK_MINUTES"]
    flash(f"로그인 시도가 너무 많습니다. {block_minutes}분 후 다시 시도해주세요.")
    return render_template("login.html"), status_code


@bp.get("/login")
def login():
    ip_address = _client_ip()
    if is_ip_blocked(ip_address):
        return _blocked_login_response()

    current_user = get_user_by_id(session.get("user_id"))
    if current_user and current_user["is_active"]:
        return redirect(_home_for_role(current_user["role"]))

    if session.get("user_id"):
        session.clear()

    return render_template("login.html")


@bp.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = get_user_by_username(username) if username else None
    ip_address = _client_ip()
    user_agent = request.headers.get("User-Agent")

    if is_ip_blocked(ip_address):
        create_login_log(
            username=username or "-",
            user_id=user["id"] if user else None,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            message="Blocked IP attempted login",
            event_type="blocked_attempt",
        )
        return _blocked_login_response()

    if not user or not verify_user_password(user, password):
        block = record_failed_login(
            username=username or "-",
            user_id=user["id"] if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            message="Invalid username or password",
        )
        if block and block["is_blocked"]:
            return _blocked_login_response()

        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
        return render_template("login.html"), 401

    if not user["is_active"]:
        create_login_log(
            username=user["username"],
            user_id=user["id"],
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            message="Inactive account",
        )
        flash("비활성화된 계정입니다. 관리자에게 문의하세요.")
        return render_template("login.html"), 403

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    reset_ip_failures(ip_address)
    create_login_log(
        username=user["username"],
        user_id=user["id"],
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
        message="Login successful",
    )
    return redirect(_home_for_role(user["role"]))


@bp.get("/register")
def register():
    current_user = get_user_by_id(session.get("user_id"))
    if current_user and current_user["is_active"]:
        return redirect(_home_for_role(current_user["role"]))

    if session.get("user_id"):
        session.clear()

    return render_template("register.html")


@bp.post("/register")
def register_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    if len(username) < 3:
        flash("아이디는 3글자 이상으로 입력하세요.")
        return render_template("register.html"), 400

    if len(password) < 8:
        flash("비밀번호는 8글자 이상으로 입력하세요.")
        return render_template("register.html"), 400

    if password != password_confirm:
        flash("비밀번호가 서로 일치하지 않습니다.")
        return render_template("register.html"), 400

    try:
        create_user(username, password, role="viewer", is_active=False)
    except sqlite3.IntegrityError:
        flash("이미 등록된 계정입니다.")
        return render_template("register.html"), 409

    flash("계정 등록이 완료되었습니다.<br>관리자 승인 후 사용할 수 있습니다.")
    return redirect(url_for("auth.login"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
