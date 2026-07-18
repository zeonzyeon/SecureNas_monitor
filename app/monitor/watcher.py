from pathlib import Path

from watchdog.observers import Observer

from app.monitor.event_handler import AccessEventHandler


def start_monitor(app):
    monitor_path = app.config["NAS_MONITOR_PATH"]

    if not monitor_path:
        app.logger.warning("NAS_MONITOR_PATH is not configured. File monitoring is disabled.")
        return None

    path = Path(monitor_path)
    if not path.exists():
        app.logger.warning("NAS_MONITOR_PATH does not exist: %s", path)
        return None

    event_handler = AccessEventHandler(app)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.daemon = True
    observer.start()

    app.logger.info("Started NAS file monitor: %s", path)
    return observer
