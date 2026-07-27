import atexit

from app import create_app
from app.monitor.watcher import start_monitor, stop_monitor


app = create_app()
observer = start_monitor(app)


@atexit.register
def shutdown_monitor():
    stop_monitor(app)
