from flask import Blueprint, current_app, jsonify, render_template, request

from app.models import list_file_events


bp = Blueprint("main", __name__)


@bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@bp.get("/health")
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
def events():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)
    return jsonify(list_file_events(limit=limit))
