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
        self.pending_file_creates = {}
        self.dedupe_seconds = 5.0
        self.directory_create_delay = 1.5
        self.file_create_delay = 0.8
        self.default_directory_create_delay = 5.0
        self.default_file_create_delay = 3.0

    def on_created(self, event):
        if self._is_temporary_smb_path(event.src_path):
            return

        if event.is_directory:
            self._schedule_directory_create(event.src_path)
            return

        self._schedule_file_create(event.src_path)

    def on_modified(self, event):
        if event.is_directory or self._is_temporary_smb_path(event.src_path):
            return

        if event.src_path in self.pending_file_creates:
            return

        self._record("modified", event.src_path, False)

    def on_deleted(self, event):
        if event.is_directory:
            self._cancel_pending_directory_create(event.src_path)
        else:
            self._cancel_pending_file_create(event.src_path)

        self._record("deleted", event.src_path, event.is_directory)

    def on_moved(self, event):
        was_pending_directory = self._cancel_pending_directory_create(event.src_path)
        was_pending_file = self._cancel_pending_file_create(event.src_path)

        if self._is_temporary_smb_path(event.dest_path):
            return

        if (
            event.is_directory
            and (
                was_pending_directory
                or self._is_temporary_smb_path(event.src_path)
                or self._is_default_new_directory_path(event.src_path)
            )
        ):
            self._schedule_directory_create(event.dest_path)
            return

        if not event.is_directory and (
            was_pending_file
            or self._is_default_new_file_path(event.src_path)
        ):
            self._schedule_file_create(event.dest_path)
            return

        self._record("modified", event.dest_path, event.is_directory, src_path=event.src_path, dest_path=event.dest_path)

    def _schedule_directory_create(self, directory_path):
        self._cancel_pending_directory_create(directory_path)

        delay = (
            self.default_directory_create_delay
            if self._is_default_new_directory_path(directory_path)
            else self.directory_create_delay
        )
        timer = threading.Timer(
            delay,
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
            return True

        return False

    def _schedule_file_create(self, file_path):
        self._cancel_pending_file_create(file_path)

        delay = (
            self.default_file_create_delay
            if self._is_default_new_file_path(file_path)
            else self.file_create_delay
        )
        timer = threading.Timer(
            delay,
            self._record,
            args=("created", file_path, False),
        )
        timer.daemon = True
        self.pending_file_creates[file_path] = timer
        timer.start()

    def _cancel_pending_file_create(self, file_path):
        timer = self.pending_file_creates.pop(file_path, None)

        if timer:
            timer.cancel()
            return True

        return False

    def _record(self, event_type, file_path, is_directory, src_path=None, dest_path=None):
        self.pending_directory_creates.pop(file_path, None)
        self.pending_file_creates.pop(file_path, None)

        if self._is_temporary_smb_path(file_path):
            return

        if self._is_duplicate(event_type, file_path):
            return

        with self.app.app_context():
            create_file_event(
                event_type=event_type,
                file_path=file_path,
                is_directory=is_directory,
                src_path=src_path,
                dest_path=dest_path,
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

    def _is_default_new_directory_path(self, file_path):
        directory_name = str(file_path).rstrip("\\/").split("\\")[-1].split("/")[-1]
        return directory_name == "새 폴더" or directory_name.startswith("새 폴더 (")

    def _is_default_new_file_path(self, file_path):
        file_name = str(file_path).rstrip("\\/").split("\\")[-1].split("/")[-1]
        return file_name == "새 텍스트 문서.txt" or file_name.startswith("새 텍스트 문서 (")
