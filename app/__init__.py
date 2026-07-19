# Flask 애플리케이션을 생성하고 초기 설정을 수행하는 파일
from flask import Flask, flash, jsonify, redirect, request, url_for

from app.config import Config
from app.db import close_db, init_db
from app.auth import bp as auth_bp
from app.auth.models import ensure_default_admin
from app.routes import bp


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)
    app.register_error_handler(403, forbidden)

    with app.app_context():
        init_db()
        ensure_default_admin(app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"])

    return app


def forbidden(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "권한이 없습니다."}), 403

    flash("이 작업을 수행할 권한이 없습니다.")
    return redirect(request.referrer or url_for("main.files"))
