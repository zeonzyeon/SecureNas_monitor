# 환경변수에 설정된 NAS 공유 폴더를 watchdog으로 감시
from watchdog.observers import Observer

from app.monitor.event_handler import AccessEventHandler
from app.nas_paths import NasPathConfigError, resolve_nas_root


def start_monitor(app):
    monitor_path = app.config["NAS_MONITOR_PATH"]

    if not monitor_path:
        app.logger.warning("NAS_MONITOR_PATH is not configured. File monitoring is disabled.")
        return None

    try:
        path = resolve_nas_root(
            monitor_path,
            allow_mapped_drive=app.config.get("NAS_ALLOW_MAPPED_DRIVE", False),
        )
    except NasPathConfigError as error:
        app.logger.error("Invalid NAS_MONITOR_PATH: %s", error)
        return None

    try:
        path_exists = path.exists()
    except PermissionError:
        app.logger.warning("NAS_MONITOR_PATH access denied: %s", path)
        return None

    if not path_exists:
        app.logger.warning("NAS_MONITOR_PATH does not exist: %s", path)
        return None

    event_handler = AccessEventHandler(app)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.daemon = True
    try:
        observer.start()
    except TypeError as error:
        app.logger.error("Failed to start file monitor. Try upgrading watchdog: %s", error)
        return None
    except Exception as error:
        app.logger.error("Failed to start file monitor: %s", error)
        return None

    app.logger.info("Started NAS file monitor: %s", path)
    return observer
