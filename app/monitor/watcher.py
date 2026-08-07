# 환경변수에 설정된 NAS 공유 폴더를 watchdog으로 감시
from watchdog.observers import Observer

from app.monitor.event_handler import AccessEventHandler
from app.nas_paths import NasPathConfigError, resolve_nas_root


# 감시자 종료
def stop_monitor(app):
    observer = app.extensions.pop("nas_monitor_observer", None)

    if not observer:
        app.config["NAS_MONITOR_ACTIVE"] = False
        return

    observer.stop()
    observer.join(timeout=5)
    app.config["NAS_MONITOR_ACTIVE"] = False


# 감시자 재시작
def restart_monitor(app):
    stop_monitor(app)
    return start_monitor(app)


def start_monitor(app):
    monitor_path = app.config["NAS_MONITOR_PATH"]

    if not monitor_path:
        app.logger.warning("NAS_MONITOR_PATH is not configured. File monitoring is disabled.")
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None

    try:
        path = resolve_nas_root(
            monitor_path,
            allow_mapped_drive=app.config.get("NAS_ALLOW_MAPPED_DRIVE", False),
        )
    except NasPathConfigError as error:
        app.logger.error("Invalid NAS_MONITOR_PATH: %s", error)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None

    try:
        path_exists = path.exists()
    except PermissionError:
        app.logger.warning("NAS_MONITOR_PATH access denied: %s", path)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None
    except OSError as error:
        app.logger.warning("NAS_MONITOR_PATH is not reachable: %s (%s)", path, error)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None

    if not path_exists:
        app.logger.warning("NAS_MONITOR_PATH does not exist: %s", path)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None

    event_handler = AccessEventHandler(app)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.daemon = True
    try:
        observer.start()
    except TypeError as error:
        app.logger.error("Failed to start file monitor. Try upgrading watchdog: %s", error)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None
    except Exception as error:
        app.logger.error("Failed to start file monitor: %s", error)
        app.config["NAS_MONITOR_ACTIVE"] = False
        return None

    app.extensions["nas_monitor_observer"] = observer
    app.config["NAS_MONITOR_ACTIVE"] = True
    app.config["NAS_MONITOR_RESOLVED_PATH"] = str(path)
    app.logger.info("Started NAS file monitor: %s", path)
    return observer
