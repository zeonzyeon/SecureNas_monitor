from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db


def get_user_by_id(user_id):
    if not user_id:
        return None

    row = get_db().execute(
        """
        SELECT id, username, password_hash, role, is_active, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def get_user_by_username(username):
    row = get_db().execute(
        """
        SELECT id, username, password_hash, role, is_active, created_at, updated_at
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()
    return dict(row) if row else None


def create_user(username, password, role="user", is_active=True):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO users (username, password_hash, role, is_active)
        VALUES (?, ?, ?, ?)
        """,
        (username, generate_password_hash(password), role, 1 if is_active else 0),
    )
    db.commit()
    return cursor.lastrowid


def list_users():
    rows = get_db().execute(
        """
        SELECT id, username, role, is_active, created_at, updated_at
        FROM users
        ORDER BY is_active ASC, created_at DESC, id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def update_user(user_id, role=None, is_active=None):
    updates = []
    values = []

    if role is not None:
        updates.append("role = ?")
        values.append(role)

    if is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if is_active else 0)

    if not updates:
        return get_user_by_id(user_id)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)

    db = get_db()
    db.execute(
        f"""
        UPDATE users
        SET {", ".join(updates)}
        WHERE id = ?
        """,
        values,
    )
    db.commit()
    return get_user_by_id(user_id)


def verify_user_password(user, password):
    return bool(user and check_password_hash(user["password_hash"], password))


def ensure_default_admin(username, password):
    if not username or not password:
        return None

    existing = get_user_by_username(username)
    if existing:
        return existing["id"]

    return create_user(username, password, role="admin", is_active=True)


def create_login_log(username, user_id, success, ip_address=None, user_agent=None, message=None):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO login_logs (
            username,
            user_id,
            success,
            ip_address,
            user_agent,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, user_id, 1 if success else 0, ip_address, user_agent, message),
    )
    db.commit()
    return cursor.lastrowid
