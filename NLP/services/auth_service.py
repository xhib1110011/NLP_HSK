"""Tạo tài khoản và xác thực người dùng cho bản thử nghiệm HSK Tutor."""

import hashlib
import hmac
import re
import secrets
import sqlite3


PASSWORD_ITERATIONS = 600_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def _password_digest(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )


def create_user(conn, username, password):
    """Tạo tài khoản; trả về (user_id, error_message)."""
    username = username.strip()

    if not (
        USERNAME_PATTERN.fullmatch(username)
        or EMAIL_PATTERN.fullmatch(username)
    ):
        return None, (
            "Nhập tên đăng nhập 3–32 ký tự (chữ không dấu, số, dấu chấm, "
            "gạch dưới hoặc gạch ngang) hoặc một email hợp lệ."
        )
    if len(password) < 8:
        return None, "Mật khẩu cần có ít nhất 8 ký tự."

    salt = secrets.token_bytes(16)
    digest = _password_digest(password, salt)

    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, password_salt, password_hash)
                VALUES (?, ?, ?)
                """,
                (username, salt.hex(), digest.hex()),
            )
        return int(cursor.lastrowid), None
    except sqlite3.IntegrityError:
        return None, "Tên đăng nhập này đã được sử dụng."


def authenticate_user(conn, username, password):
    """Trả về thông tin tài khoản nếu mật khẩu hợp lệ."""
    row = conn.execute(
        """
        SELECT id, username, password_salt, password_hash
        FROM users
        WHERE username = ? COLLATE NOCASE
        """,
        (username.strip(),),
    ).fetchone()

    if row is None:
        return None

    try:
        salt = bytes.fromhex(row["password_salt"])
        expected = bytes.fromhex(row["password_hash"])
    except (TypeError, ValueError):
        return None

    actual = _password_digest(password, salt)
    if not hmac.compare_digest(actual, expected):
        return None

    return {"id": int(row["id"]), "username": row["username"]}
