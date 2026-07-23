import os

from app import create_app
from app.monitor.watcher import start_monitor, stop_monitor


app = create_app()


def should_start_monitor():
    return not app.config["DEBUG"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true"


if __name__ == "__main__":
    observer = start_monitor(app) if should_start_monitor() else None

    try:
        app.run(debug=app.config["DEBUG"], reloader_type="stat")
    finally:
        stop_monitor(app)
