from flask import Flask

from app.config import Config
from app.db import close_db, init_db
from app.routes import bp


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)

    with app.app_context():
        init_db()

    return app
