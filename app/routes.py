# 대시보드 화면과 상태/이벤트 조회 API 라우트를 정의
from flask import Blueprint, current_app, jsonify, render_template, request

from app.models import list_file_events


bp = Blueprint("main", __name__)


# 메인 대시보드 화면
@bp.get("/")
def dashboard():
    return render_template("dashboard.html")


# # 서버 상태와 기본 설정 정보를 반환
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


# 저장된 파일 이벤트 목록을 조회
@bp.get("/api/events")
def events():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)
    return jsonify(list_file_events(limit=limit))
