# 파일 접근 이벤트를 SQLite에 저장하고 조회하는 데이터 접근 함수
from pathlib import Path

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


# 저장된 파일 이벤트 최신순으로 조회
def list_file_events(limit=100):
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
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
