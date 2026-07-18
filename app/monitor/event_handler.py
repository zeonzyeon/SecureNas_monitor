from watchdog.events import FileSystemEventHandler

from app.models import create_file_event


class AccessEventHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        self._record("created", event.src_path, event.is_directory)

    def on_modified(self, event):
        self._record("modified", event.src_path, event.is_directory)

    def on_deleted(self, event):
        self._record("deleted", event.src_path, event.is_directory)

    def on_moved(self, event):
        self._record(
            "moved",
            event.dest_path,
            event.is_directory,
            src_path=event.src_path,
            dest_path=event.dest_path,
        )

    def _record(self, event_type, file_path, is_directory, src_path=None, dest_path=None):
        with self.app.app_context():
            create_file_event(
                event_type=event_type,
                file_path=file_path,
                is_directory=is_directory,
                src_path=src_path,
                dest_path=dest_path,
            )
