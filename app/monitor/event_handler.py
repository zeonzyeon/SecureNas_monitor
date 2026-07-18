# watchdog 파일 시스템 이벤트 중 파일/폴더 생성과 삭제만 SQLite 이벤트 기록
import threading
import time

from watchdog.events import FileSystemEventHandler

from app.models import create_file_event


class AccessEventHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.recent_events = {}
        self.pending_directory_creates = {}
        self.dedupe_seconds = 5.0
        self.directory_create_delay = 1.5

    def on_created(self, event):
        if self._is_temporary_smb_path(event.src_path):
            return

        if event.is_directory:
            self._schedule_directory_create(event.src_path)
            return

        self._record("created", event.src_path, event.is_directory)

    def on_modified(self, event):
        return

    def on_deleted(self, event):
        if event.is_directory:
            self._cancel_pending_directory_create(event.src_path)

        self._record("deleted", event.src_path, event.is_directory)

    def on_moved(self, event):
        if event.is_directory:
            self._cancel_pending_directory_create(event.src_path)

            if not self._is_temporary_smb_path(event.dest_path):
                self._schedule_directory_create(event.dest_path)

    def _schedule_directory_create(self, directory_path):
        self._cancel_pending_directory_create(directory_path)

        timer = threading.Timer(
            self.directory_create_delay,
            self._record,
            args=("created", directory_path, True),
        )
        timer.daemon = True
        self.pending_directory_creates[directory_path] = timer
        timer.start()

    def _cancel_pending_directory_create(self, directory_path):
        timer = self.pending_directory_creates.pop(directory_path, None)

        if timer:
            timer.cancel()

    def _record(self, event_type, file_path, is_directory):
        self.pending_directory_creates.pop(file_path, None)

        if self._is_temporary_smb_path(file_path):
            return

        if self._is_duplicate(event_type, file_path):
            return

        with self.app.app_context():
            create_file_event(
                event_type=event_type,
                file_path=file_path,
                is_directory=is_directory,
            )

    def _is_duplicate(self, event_type, file_path):
        now = time.monotonic()
        key = (event_type, file_path)
        previous_time = self.recent_events.get(key)
        self.recent_events[key] = now

        if previous_time is None:
            return False

        return now - previous_time < self.dedupe_seconds

    def _is_temporary_smb_path(self, file_path):
        return ":TMPNAME:" in str(file_path)
