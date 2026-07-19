from werkzeug.security import check_password_hash, generate_password_hash
from flask import current_app

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


def create_login_log(
    username,
    user_id,
    success,
    ip_address=None,
    user_agent=None,
    message=None,
    event_type=None,
):
    if event_type is None:
        event_type = "login_success" if success else "login_failure"

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO login_logs (
            event_type,
            username,
            user_id,
            success,
            ip_address,
            user_agent,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_type, username, user_id, 1 if success else 0, ip_address, user_agent, message),
    )
    db.commit()
    return cursor.lastrowid


def get_ip_block(ip_address):
    if not ip_address:
        return None

    clear_expired_ip_blocks(ip_address)
    row = get_db().execute(
        """
        SELECT
            ip_address,
            failed_attempts,
            last_failed_at,
            blocked_at,
            blocked_until,
            is_blocked,
            blocked_by,
            block_reason,
            updated_at
        FROM ip_blocks
        WHERE ip_address = ?
        """,
        (ip_address,),
    ).fetchone()
    return dict(row) if row else None


def is_ip_blocked(ip_address):
    block = get_ip_block(ip_address)
    return bool(block and block["is_blocked"])


def record_failed_login(username, user_id, ip_address, user_agent=None, message="Invalid username or password"):
    create_login_log(
        username=username or "-",
        user_id=user_id,
        success=False,
        ip_address=ip_address,
        user_agent=user_agent,
        message=message,
        event_type="login_failure",
    )

    if not ip_address:
        return None

    db = get_db()
    db.execute(
        """
        INSERT INTO ip_blocks (
            ip_address,
            failed_attempts,
            last_failed_at,
            updated_at
        )
        VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(ip_address) DO UPDATE SET
            failed_attempts = failed_attempts + 1,
            last_failed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """,
        (ip_address,),
    )
    db.commit()

    block = get_ip_block(ip_address)
    if block and block["failed_attempts"] >= current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"]:
        block_ip(
            ip_address,
            blocked_by="system",
            reason="Too many failed login attempts",
            minutes=current_app.config["LOGIN_BLOCK_MINUTES"],
            user_agent=user_agent,
            log_event=True,
        )
        block = get_ip_block(ip_address)

    return block


def reset_ip_failures(ip_address):
    if not ip_address:
        return

    db = get_db()
    db.execute(
        """
        INSERT INTO ip_blocks (
            ip_address,
            failed_attempts,
            updated_at
        )
        VALUES (?, 0, CURRENT_TIMESTAMP)
        ON CONFLICT(ip_address) DO UPDATE SET
            failed_attempts = 0,
            last_failed_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (ip_address,),
    )
    db.commit()


def block_ip(ip_address, blocked_by="admin", reason="Manual block", minutes=None, user_agent=None, log_event=True):
    if not ip_address:
        return None

    if minutes is None:
        minutes = current_app.config["LOGIN_BLOCK_MINUTES"]

    db = get_db()
    db.execute(
        """
        INSERT INTO ip_blocks (
            ip_address,
            failed_attempts,
            blocked_at,
            blocked_until,
            is_blocked,
            blocked_by,
            block_reason,
            updated_at
        )
        VALUES (?, 0, CURRENT_TIMESTAMP, datetime('now', ?), 1, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(ip_address) DO UPDATE SET
            blocked_at = CURRENT_TIMESTAMP,
            blocked_until = datetime('now', ?),
            is_blocked = 1,
            blocked_by = ?,
            block_reason = ?,
            updated_at = CURRENT_TIMESTAMP
        """,
        (ip_address, f"+{minutes} minutes", blocked_by, reason, f"+{minutes} minutes", blocked_by, reason),
    )
    db.commit()

    if log_event:
        create_login_log(
            username="-",
            user_id=None,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            message=reason,
            event_type="ip_blocked" if blocked_by == "system" else "manual_ip_blocked",
        )

    return get_ip_block(ip_address)


def unblock_ip(ip_address, blocked_by="admin", user_agent=None, log_event=True):
    if not ip_address:
        return None

    if not get_ip_block(ip_address):
        return None

    db = get_db()
    db.execute(
        """
        UPDATE ip_blocks
        SET
            failed_attempts = 0,
            is_blocked = 0,
            blocked_until = NULL,
            blocked_by = ?,
            block_reason = 'Manual unblock',
            updated_at = CURRENT_TIMESTAMP
        WHERE ip_address = ?
        """,
        (blocked_by, ip_address),
    )
    db.commit()

    if log_event:
        create_login_log(
            username="-",
            user_id=None,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            message="IP manually unblocked",
            event_type="ip_unblocked",
        )

    return get_ip_block(ip_address)


def clear_expired_ip_blocks(ip_address=None):
    db = get_db()
    if ip_address:
        db.execute(
            """
            UPDATE ip_blocks
            SET
                failed_attempts = 0,
                is_blocked = 0,
                block_reason = 'Expired block',
                updated_at = CURRENT_TIMESTAMP
            WHERE ip_address = ?
                AND is_blocked = 1
                AND blocked_until IS NOT NULL
                AND blocked_until <= CURRENT_TIMESTAMP
            """,
            (ip_address,),
        )
    else:
        db.execute(
            """
            UPDATE ip_blocks
            SET
                failed_attempts = 0,
                is_blocked = 0,
                block_reason = 'Expired block',
                updated_at = CURRENT_TIMESTAMP
            WHERE is_blocked = 1
                AND blocked_until IS NOT NULL
                AND blocked_until <= CURRENT_TIMESTAMP
            """
        )
    db.commit()


def list_ip_blocks():
    clear_expired_ip_blocks()
    rows = get_db().execute(
        """
        SELECT
            ip_address,
            failed_attempts,
            last_failed_at,
            blocked_at,
            blocked_until,
            is_blocked,
            blocked_by,
            block_reason,
            updated_at
        FROM ip_blocks
        WHERE is_blocked = 1 OR failed_attempts > 0 OR blocked_at IS NOT NULL
        ORDER BY is_blocked DESC, blocked_at DESC, last_failed_at DESC, updated_at DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_security_logs(limit=100):
    rows = get_db().execute(
        """
        SELECT
            id,
            event_type,
            username,
            user_id,
            success,
            ip_address,
            user_agent,
            message,
            created_at
        FROM login_logs
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
