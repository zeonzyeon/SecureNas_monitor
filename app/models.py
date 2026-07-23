# 파일 접근 이벤트를 SQLite에 저장하고 조회하는 데이터 접근 함수
from datetime import datetime
from pathlib import Path, PureWindowsPath

from app.db import get_db


# 파일 이벤트 정보 저장
def create_file_event(event_type, file_path, is_directory=False, src_path=None, dest_path=None):
    path = Path(file_path)
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO file_events (
            event_type,
            file_path,
            file_name,
            src_path,
            dest_path,
            is_directory
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            str(file_path),
            path.name,
            str(src_path) if src_path else None,
            str(dest_path) if dest_path else None,
            1 if is_directory else 0,
        ),
    )
    db.commit()
    return cursor.lastrowid


# 저장된 파일 이벤트 최신순 조회
def list_file_events(limit=100, root_path=None):
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,
            event_type,
            file_path,
            file_name,
            src_path,
            dest_path,
            is_directory,
            source,
            user_name,
            ip_address,
            created_at
        FROM file_events
        WHERE event_type IN ('created', 'modified', 'deleted')
            AND file_name NOT LIKE ':TMPNAME:%'
            AND file_path NOT LIKE '%:TMPNAME:%'
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit * 5,),
    ).fetchall()
    events = [dict(row) for row in rows]

    if root_path:
        events = [event for event in events if _is_event_under_root(event, root_path)]

    return _collapse_near_duplicates(events, limit)


def _is_event_under_root(event, root_path):
    return _path_is_under_root(event.get("file_path"), root_path)


def _path_is_under_root(path_value, root_path):
    if not path_value:
        return False

    try:
        Path(path_value).resolve().relative_to(root_path)
        return True
    except (OSError, ValueError):
        pass

    try:
        PureWindowsPath(str(path_value)).relative_to(PureWindowsPath(str(root_path)))
        return True
    except ValueError:
        return False


def _collapse_near_duplicates(events, limit):
    collapsed_events = []
    recent_keys = {}
    window_seconds = 5

    for event in events:
        key = (event["event_type"], event["file_path"])
        created_at = _parse_created_at(event["created_at"])
        previous_created_at = recent_keys.get(key)

        if previous_created_at and created_at:
            seconds = abs((previous_created_at - created_at).total_seconds())
            if seconds <= window_seconds:
                continue

        if created_at:
            recent_keys[key] = created_at

        collapsed_events.append(event)

        if len(collapsed_events) >= limit:
            break

    return collapsed_events


def _parse_created_at(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
