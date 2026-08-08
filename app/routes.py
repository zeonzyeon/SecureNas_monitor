import shutil
import errno
from pathlib import Path, PurePosixPath

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import ServiceUnavailable

from app.auth.decorators import login_required, roles_required
from app.auth.models import block_ip, list_ip_blocks, list_security_logs, list_users, unblock_ip, update_user
from app.config import BASE_DIR
from app.models import list_file_events
from app.monitor.watcher import restart_monitor
from app.nas_paths import NasPathConfigError, resolve_nas_root, to_portal_path


bp = Blueprint("main", __name__)

def _role_permissions(role):
    return {
        "can_read": role in {"admin", "user", "viewer"},
        "can_create": role in {"admin", "user"},
        "can_download": role in {"admin", "user"},
        "can_rename": role in {"admin", "user"},
        "can_delete": role == "admin",
        "can_dashboard": role in {"admin", "user"},
    }


# NAS 루트 경로 조회
def _nas_root_path():
    monitor_path = current_app.config["NAS_MONITOR_PATH"]
    if not monitor_path:
        abort(500, description="NAS_MONITOR_PATH is not configured.")

    try:
        return resolve_nas_root(
            monitor_path,
            allow_mapped_drive=current_app.config.get("NAS_ALLOW_MAPPED_DRIVE", False),
        )
    except NasPathConfigError as error:
        abort(500, description=str(error))


# NAS 하위 경로 검증
def _safe_nas_path(subpath=""):
    root_path = _nas_root_path()
    portal_path = PurePosixPath(subpath)
    parts = tuple(part for part in portal_path.parts if part not in {"", "."})

    if portal_path.is_absolute() or ".." in parts:
        abort(404)

    requested_path = root_path.joinpath(*parts)

    try:
        requested_path.relative_to(root_path)
    except ValueError:
        abort(404)

    return root_path, requested_path


def _abort_nas_unavailable(error):
    raise ServiceUnavailable(_format_nas_os_error(error)) from error


# 파일 목록 리다이렉트
def _redirect_to_files(subpath=""):
    parent = PurePosixPath(subpath).parent.as_posix()
    if parent == ".":
        parent = ""

    return redirect(_files_url(parent))


# 파일 목록 URL 생성
def _files_url(subpath=""):
    normalized_path = PurePosixPath(subpath).as_posix().strip("/")

    if not normalized_path or normalized_path == ".":
        return url_for("main.files")

    return url_for("main.files", subpath=normalized_path)


def _nas_root_label(root_path=None):
    if root_path and root_path.name:
        return root_path.name

    monitor_path = current_app.config.get("NAS_MONITOR_PATH", "")
    if monitor_path:
        return Path(monitor_path).name or "NAS Root"

    return "NAS Root"


def _format_nas_os_error(error):
    if error.errno == errno.EHOSTDOWN:
        return "NAS 서버에 연결할 수 없습니다. 외부 네트워크에서는 NAS VPN, Tailscale 서브넷 라우팅, 또는 CIFS 마운트 상태를 확인하세요."

    if error.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ETIMEDOUT}:
        return "NAS 네트워크 경로에 도달할 수 없습니다. 서버 IP, VPN 연결, 방화벽, 마운트 상태를 확인하세요."

    return f"NAS 경로 확인 중 오류가 발생했습니다: {error}"


def _path_status_error(path, missing_message, not_dir_message):
    access_message = "NAS 경로에 접근할 권한이 없습니다. Windows에서 NAS 공유 인증을 먼저 연결하세요."

    try:
        if not path.exists():
            try:
                path.stat()
            except PermissionError:
                return access_message
            except OSError as error:
                return _format_nas_os_error(error)

            return missing_message

        if not path.is_dir():
            return not_dir_message
    except PermissionError:
        return access_message
    except OSError as error:
        return _format_nas_os_error(error)

    return None


def _format_file_size(size):
    if size is None:
        return "-"

    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            if value >= 100:
                return f"{value:.0f} {unit}"
            if value >= 10:
                return f"{value:.1f} {unit}"
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{size} B"


def _env_path():
    return BASE_DIR / ".env"


def _read_env_values():
    path = _env_path()
    values = {}

    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()

    return values


def _update_env_values(updates):
    path = _env_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen_keys = set()
    next_lines = []

    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in updates:
            next_lines.append(f"{key}={updates[key]}")
            seen_keys.add(key)
        else:
            next_lines.append(line)

    for key, value in updates.items():
        if key not in seen_keys:
            next_lines.append(f"{key}={value}")

    path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


@bp.get("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if session.get("role") in {"admin", "user"}:
        return redirect(url_for("main.dashboard"))

    return redirect(url_for("main.files"))


@bp.get("/dashboard")
@roles_required("admin", "user")
def dashboard():
    return render_template("dashboard.html")


@bp.get("/settings")
@roles_required("admin")
def settings_page():
    return render_template("settings.html")


@bp.get("/users")
@roles_required("admin")
def users_page():
    return render_template("users.html")


@bp.get("/file-events")
@roles_required("admin", "user")
def file_events_page():
    return render_template("file_events.html")


@bp.get("/blocked-ips")
@roles_required("admin")
def blocked_ips_page():
    return render_template("blocked_ips.html")


@bp.get("/security-logs")
@roles_required("admin", "user")
def security_logs_page():
    return render_template("security_logs.html")


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
            root_label=_nas_root_label(),
            current_path="",
            parent_path=parent_path,
            permissions=_role_permissions(session.get("role")),
        )

    root_path, requested_path = _safe_nas_path(subpath)

    try:
        error = _path_status_error(
            root_path,
            "설정된 NAS 경로가 존재하지 않습니다.",
            "설정된 NAS 경로가 폴더가 아닙니다.",
        )

        if not error:
            error = _path_status_error(
                requested_path,
                "요청한 폴더가 존재하지 않습니다.",
                "요청한 경로가 폴더가 아닙니다.",
            )

        if error:
            pass
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
                        "display_size": _format_file_size(stat.st_size if child.is_file() else None),
                        "updated_at": stat.st_mtime,
                    }
                )
    except PermissionError:
        error = "NAS 경로에 접근할 권한이 없습니다."
    except OSError as os_error:
        error = _format_nas_os_error(os_error)

    return render_template(
        "files.html",
        files=files_list,
        error=error,
        breadcrumbs=breadcrumbs,
        root_label=_nas_root_label(root_path),
        current_path=PurePosixPath(subpath).as_posix().strip("/"),
        parent_path=parent_path,
        permissions=_role_permissions(session.get("role")),
    )


@bp.get("/files/open/<path:subpath>")
@login_required
def open_file(subpath):
    root_path, requested_path = _safe_nas_path(subpath)

    try:
        if not requested_path.exists() or not requested_path.is_file():
            abort(404)
        return send_file(requested_path, as_attachment=False)
    except OSError as error:
        _abort_nas_unavailable(error)


@bp.get("/files/download/<path:subpath>")
@roles_required("admin", "user")
def download_file(subpath):
    root_path, requested_path = _safe_nas_path(subpath)

    try:
        if not requested_path.exists() or not requested_path.is_file():
            abort(404)
        return send_file(requested_path, as_attachment=True, download_name=requested_path.name)
    except OSError as error:
        _abort_nas_unavailable(error)


def _save_uploaded_file(current_path, upload):
    if not upload or not upload.filename:
        return False, "업로드할 파일을 선택하세요.", None

    root_path, current_directory = _safe_nas_path(current_path)
    try:
        if not current_directory.exists() or not current_directory.is_dir():
            abort(404)
    except OSError as error:
        return False, _format_nas_os_error(error), None

    filename = Path(upload.filename).name
    if not filename or "/" in filename or "\\" in filename:
        filename = secure_filename(upload.filename)

    if not filename:
        return False, "파일 이름을 확인할 수 없습니다.", None

    target_path = current_directory / filename

    try:
        target_path.relative_to(root_path)
    except ValueError:
        abort(404)

    try:
        if target_path.exists():
            return False, "이미 같은 이름의 파일이 있습니다.", filename

        upload.save(target_path)
    except OSError as error:
        return False, _format_nas_os_error(error), filename

    return True, "업로드가 완료되었습니다.", filename


@bp.post("/files/create")
@roles_required("admin", "user")
def create_file_item():
    current_path = request.form.get("current_path", "").strip("/")
    item_type = request.form.get("item_type", "file")
    name = request.form.get("name", "").strip()

    if not name or "/" in name or "\\" in name:
        flash("파일 또는 폴더 이름을 올바르게 입력하세요.")
        return redirect(_files_url(current_path))

    root_path, current_directory = _safe_nas_path(current_path)
    try:
        if not current_directory.exists() or not current_directory.is_dir():
            abort(404)
    except OSError as error:
        flash(_format_nas_os_error(error))
        return redirect(_files_url(current_path))

    target_path = current_directory / name
    try:
        target_path.relative_to(root_path)
    except ValueError:
        abort(404)

    try:
        if target_path.exists():
            flash("이미 같은 이름의 항목이 있습니다.")
            return redirect(_files_url(current_path))

        if item_type == "folder":
            target_path.mkdir()
        else:
            target_path.touch()
    except OSError as error:
        flash(_format_nas_os_error(error))
        return redirect(_files_url(current_path))

    return redirect(_files_url(current_path))


@bp.post("/files/upload")
@roles_required("admin", "user")
def upload_file():
    current_path = request.form.get("current_path", "").strip("/")
    upload = request.files.get("file")

    ok, message, _filename = _save_uploaded_file(current_path, upload)
    if not ok:
        flash(message)
    return redirect(_files_url(current_path))


@bp.post("/api/files/upload")
@roles_required("admin", "user")
def upload_file_api():
    current_path = request.form.get("current_path", "").strip("/")
    upload = request.files.get("file")
    ok, message, filename = _save_uploaded_file(current_path, upload)

    return jsonify({"ok": ok, "message": message, "filename": filename}), 201 if ok else 400


@bp.post("/files/delete/<path:subpath>")
@roles_required("admin")
def delete_file_item(subpath):
    root_path, requested_path = _safe_nas_path(subpath)

    try:
        if not requested_path.exists():
            abort(404)

        if requested_path.is_dir():
            shutil.rmtree(requested_path)
        else:
            requested_path.unlink()
    except OSError as error:
        flash(_format_nas_os_error(error))
        return _redirect_to_files(subpath)

    return _redirect_to_files(subpath)


@bp.post("/files/rename/<path:subpath>")
@roles_required("admin", "user")
def rename_file_item(subpath):
    root_path, requested_path = _safe_nas_path(subpath)
    new_name = request.form.get("new_name", "").strip()

    try:
        if not requested_path.exists():
            abort(404)
    except OSError as error:
        flash(_format_nas_os_error(error))
        return _redirect_to_files(subpath)

    if not new_name or new_name in {".", ".."} or "/" in new_name or "\\" in new_name:
        flash("파일 또는 폴더 이름을 올바르게 입력하세요.")
        return _redirect_to_files(subpath)

    target_path = requested_path.parent / new_name

    try:
        target_path.relative_to(root_path)
    except ValueError:
        abort(404)

    if target_path == requested_path:
        return _redirect_to_files(subpath)

    try:
        if target_path.exists():
            flash("이미 같은 이름의 항목이 있습니다.")
            return _redirect_to_files(subpath)
    except OSError as error:
        flash(_format_nas_os_error(error))
        return _redirect_to_files(subpath)

    try:
        requested_path.rename(target_path)
    except OSError:
        flash("이름을 변경할 수 없습니다. 사용할 수 없는 문자가 포함되어 있는지 확인하세요.")

    return _redirect_to_files(subpath)


@bp.get("/files/edit/<path:subpath>")
@roles_required("admin", "user")
def edit_file(subpath):
    flash("파일 내용 수정은 비활성화되어 있습니다. 파일명만 변경할 수 있습니다.")
    return _redirect_to_files(subpath)


@bp.post("/files/edit/<path:subpath>")
@roles_required("admin", "user")
def edit_file_post(subpath):
    flash("파일 내용 수정은 비활성화되어 있습니다. 파일명만 변경할 수 있습니다.")
    return _redirect_to_files(subpath)


@bp.get("/health")
@roles_required("admin", "user")
def health():
    monitor_path = current_app.config["NAS_MONITOR_PATH"]
    monitor_active = bool(current_app.config.get("NAS_MONITOR_ACTIVE", False))
    nas_path_error = None
    nas_path_exists = False

    if monitor_path:
        try:
            root_path = resolve_nas_root(
                monitor_path,
                allow_mapped_drive=current_app.config.get("NAS_ALLOW_MAPPED_DRIVE", False),
            )
            nas_path_error = _path_status_error(
                root_path,
                "설정된 NAS 경로가 존재하지 않습니다.",
                "설정된 NAS 경로가 폴더가 아닙니다.",
            )
            nas_path_exists = nas_path_error is None
        except NasPathConfigError as error:
            nas_path_error = str(error)

    return jsonify(
        {
            "status": "ok",
            "database": str(current_app.config["DATABASE_PATH"]),
            "nas_monitor_path": monitor_path,
            "monitor_path_configured": bool(monitor_path),
            "nas_path_exists": nas_path_exists,
            "nas_path_error": nas_path_error,
            "monitor_active": monitor_active,
            "monitor_resolved_path": current_app.config.get("NAS_MONITOR_RESOLVED_PATH"),
        }
    )


@bp.get("/api/settings")
@roles_required("admin")
def settings():
    env_values = _read_env_values()
    runtime_nas_path = current_app.config["NAS_MONITOR_PATH"]
    saved_nas_path = env_values.get("NAS_MONITOR_PATH", runtime_nas_path)
    runtime_allow_mapped_drive = bool(current_app.config.get("NAS_ALLOW_MAPPED_DRIVE", False))
    saved_allow_mapped_drive = env_values.get("NAS_ALLOW_MAPPED_DRIVE", str(runtime_allow_mapped_drive)).lower() == "true"

    return jsonify(
        {
            "database_path": str(current_app.config["DATABASE_PATH"]),
            "nas_monitor_path": saved_nas_path,
            "runtime_nas_monitor_path": runtime_nas_path,
            "nas_allow_mapped_drive": saved_allow_mapped_drive,
            "runtime_nas_allow_mapped_drive": runtime_allow_mapped_drive,
            "restart_required": saved_nas_path != runtime_nas_path
            or saved_allow_mapped_drive != runtime_allow_mapped_drive,
        }
    )


@bp.patch("/api/settings")
@roles_required("admin")
def update_settings():
    data = request.get_json(silent=True) or {}
    nas_monitor_path = str(data.get("nas_monitor_path", "")).strip()
    allow_mapped_drive = bool(data.get("nas_allow_mapped_drive", False))

    if nas_monitor_path:
        try:
            resolve_nas_root(nas_monitor_path, allow_mapped_drive=allow_mapped_drive)
        except NasPathConfigError as error:
            return jsonify({"error": str(error)}), 400

    _update_env_values(
        {
            "NAS_MONITOR_PATH": nas_monitor_path,
            "NAS_ALLOW_MAPPED_DRIVE": "true" if allow_mapped_drive else "false",
        }
    )
    current_app.config["NAS_MONITOR_PATH"] = nas_monitor_path
    current_app.config["NAS_ALLOW_MAPPED_DRIVE"] = allow_mapped_drive
    observer = restart_monitor(current_app)

    return jsonify(
        {
            "database_path": str(current_app.config["DATABASE_PATH"]),
            "nas_monitor_path": nas_monitor_path,
            "nas_allow_mapped_drive": allow_mapped_drive,
            "monitor_active": bool(observer),
            "restart_required": False,
        }
    )


@bp.get("/api/events")
@roles_required("admin", "user")
def events():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)

    try:
        root_path = _nas_root_path()
    except Exception:
        root_path = None

    events = list_file_events(limit=limit, root_path=root_path)

    for event in events:
        event["file_path"] = to_portal_path(event.get("file_path"), root_path)
        event["src_path"] = to_portal_path(event.get("src_path"), root_path)
        event["dest_path"] = to_portal_path(event.get("dest_path"), root_path)

    return jsonify(events)


@bp.get("/api/users")
@roles_required("admin", "user")
def users():
    return jsonify(list_users())


# IP 차단 목록 API
@bp.get("/api/ip-blocks")
@roles_required("admin", "user")
def ip_blocks():
    return jsonify(list_ip_blocks())


# IP 수동 차단 API
@bp.post("/api/ip-blocks")
@roles_required("admin")
def create_ip_block():
    data = request.get_json(silent=True) or {}
    ip_address = str(data.get("ip_address", "")).strip()
    minutes = data.get("minutes", current_app.config["LOGIN_BLOCK_MINUTES"])

    if not ip_address:
        return jsonify({"error": "IP address is required"}), 400

    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return jsonify({"error": "minutes must be an integer"}), 400

    minutes = min(max(minutes, 1), 1440)
    block = block_ip(
        ip_address,
        blocked_by=session.get("username", "admin"),
        reason="Manual block",
        minutes=minutes,
        user_agent=request.headers.get("User-Agent"),
    )
    return jsonify(block), 201


# IP 차단 해제 API
@bp.delete("/api/ip-blocks/<path:ip_address>")
@roles_required("admin")
def delete_ip_block(ip_address):
    block = unblock_ip(
        ip_address,
        blocked_by=session.get("username", "admin"),
        user_agent=request.headers.get("User-Agent"),
    )
    if not block:
        return jsonify({"error": "IP address not found"}), 404

    return jsonify(block)


# 보안 로그 API
@bp.get("/api/security-logs")
@roles_required("admin", "user")
def security_logs():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)
    return jsonify(list_security_logs(limit=limit))


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
