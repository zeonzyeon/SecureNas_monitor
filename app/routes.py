from pathlib import Path, PurePosixPath

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for

from app.auth.decorators import login_required, roles_required
from app.auth.models import list_users, update_user
from app.models import list_file_events


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if session.get("role") == "admin":
        return redirect(url_for("main.dashboard"))

    return redirect(url_for("main.files"))


@bp.get("/dashboard")
@roles_required("admin")
def dashboard():
    return render_template("dashboard.html")


@bp.get("/files", defaults={"subpath": ""})
@bp.get("/files/<path:subpath>")
@login_required
def files(subpath):
    monitor_path = current_app.config["NAS_MONITOR_PATH"]
    files_list = []
    breadcrumbs = []
    parent_path = None
    error = None

    if not monitor_path:
        error = "NAS_MONITOR_PATH가 설정되지 않았습니다."
        return render_template(
            "files.html",
            files=files_list,
            error=error,
            breadcrumbs=breadcrumbs,
            current_path="",
            parent_path=parent_path,
        )

    root_path = Path(monitor_path).resolve()
    requested_path = (root_path / subpath).resolve()

    try:
        requested_path.relative_to(root_path)
    except ValueError:
        abort(404)

    try:
        if not root_path.exists():
            error = "설정된 NAS 경로가 존재하지 않습니다."
        elif not root_path.is_dir():
            error = "설정된 NAS 경로가 폴더가 아닙니다."
        elif not requested_path.exists():
            error = "요청한 폴더가 존재하지 않습니다."
        elif not requested_path.is_dir():
            error = "요청한 경로가 폴더가 아닙니다."
        else:
            relative_path = requested_path.relative_to(root_path)
            parts = () if str(relative_path) == "." else relative_path.parts

            for index, part in enumerate(parts):
                href = "/".join(parts[: index + 1])
                breadcrumbs.append({"name": part, "href": href})

            if parts:
                parent_path = "/".join(parts[:-1])

            for child in sorted(requested_path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
                stat = child.stat()
                files_list.append(
                    {
                        "name": child.name,
                        "href": child.relative_to(root_path).as_posix(),
                        "is_dir": child.is_dir(),
                        "size": stat.st_size if child.is_file() else None,
                        "updated_at": stat.st_mtime,
                    }
                )
    except PermissionError:
        error = "NAS 경로에 접근할 권한이 없습니다."

    return render_template(
        "files.html",
        files=files_list,
        error=error,
        breadcrumbs=breadcrumbs,
        current_path=PurePosixPath(subpath).as_posix().strip("/"),
        parent_path=parent_path,
    )


@bp.get("/health")
@roles_required("admin")
def health():
    monitor_path = current_app.config["NAS_MONITOR_PATH"]
    return jsonify(
        {
            "status": "ok",
            "database": str(current_app.config["DATABASE_PATH"]),
            "monitor_path_configured": bool(monitor_path),
        }
    )


@bp.get("/api/events")
@roles_required("admin")
def events():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)
    return jsonify(list_file_events(limit=limit))


@bp.get("/api/users")
@roles_required("admin")
def users():
    return jsonify(list_users())


@bp.patch("/api/users/<int:user_id>")
@roles_required("admin")
def update_user_api(user_id):
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    is_active = data.get("is_active")

    if role is not None and role not in {"admin", "user", "viewer"}:
        return jsonify({"error": "Invalid role"}), 400

    if is_active is not None and not isinstance(is_active, bool):
        return jsonify({"error": "is_active must be boolean"}), 400

    current_user_id = session.get("user_id")
    if user_id == current_user_id and (role not in (None, "admin") or is_active is False):
        return jsonify({"error": "Cannot remove your own admin access"}), 400

    user = update_user(user_id, role=role, is_active=is_active)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.pop("password_hash", None)
    return jsonify(user)
