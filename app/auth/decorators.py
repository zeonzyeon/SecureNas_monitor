from functools import wraps

from flask import abort, redirect, session, url_for

from app.auth.models import get_user_by_id


def _load_active_user():
    user = get_user_by_id(session.get("user_id"))
    if not user or not user["is_active"]:
        session.clear()
        return None

    session["username"] = user["username"]
    session["role"] = user["role"]
    return user


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not _load_active_user():
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = _load_active_user()
            if not user:
                return redirect(url_for("auth.login"))

            if user["role"] not in roles:
                abort(403)

            return view(*args, **kwargs)

        return wrapped_view

    return decorator
