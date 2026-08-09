"""
TRINETRA — Forgot Password: Reset Token Storage & Verification

Mirrors the pattern used by app/core/email_otp.py: tokens are stored
hashed (never plaintext) in the same dedicated auth SQLite DB used by
api_key_auth.py, with expiry and single-use consumption.

This module does not modify any existing table, function, or behavior.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

from app.core.config import settings

logger = logging.getLogger("trinetra.password_reset")

_AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "trinetra_auth.db")

RESET_TOKEN_EXPIRY_MINUTES = 30
RESET_REQUEST_COOLDOWN_SECONDS = 60  # prevent spamming a user's inbox


def _get_db():
    import sqlite3

    conn = sqlite3.connect(_AUTH_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_password_resets_table():
    """Create the password_resets table if it doesn't exist."""
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token_hash);
            CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email);
        """)
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to init password_resets table: %s", e)
        return False
    finally:
        conn.close()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(user_id: int, email: str) -> tuple[bool, str, str | None]:
    """Create a new password-reset token for a user.

    Returns (success, message, plaintext_token). The plaintext token is
    only ever available here — only its hash is stored.
    Enforces a cooldown per email to prevent inbox-spamming abuse.
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable.", None

    try:
        now = datetime.now(timezone.utc)
        recent = conn.execute(
            "SELECT created_at FROM password_resets WHERE email = ? ORDER BY created_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        if recent:
            last_created = datetime.fromisoformat(recent["created_at"]).replace(tzinfo=timezone.utc) \
                if "Z" not in recent["created_at"] and "+" not in recent["created_at"] \
                else datetime.fromisoformat(recent["created_at"])
            elapsed = (now - last_created.replace(tzinfo=timezone.utc) if last_created.tzinfo is None else now - last_created).total_seconds()
            if elapsed < RESET_REQUEST_COOLDOWN_SECONDS:
                return False, f"Please wait before requesting another reset link.", None

        # Invalidate any previous unused tokens for this user
        conn.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))

        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires_at = now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

        conn.execute(
            "INSERT INTO password_resets (user_id, email, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, email, token_hash, expires_at.isoformat()),
        )
        conn.commit()
        return True, "Reset token created.", token
    except Exception as e:
        logger.error("Failed to create reset token for %s: %s", email, e)
        return False, "Could not start password reset. Please try again.", None
    finally:
        conn.close()


def verify_reset_token(token: str) -> tuple[bool, str, dict | None]:
    """Verify a reset token without consuming it (used before showing the
    'set new password' form, so we can tell the user upfront if it's dead).

    Returns (valid, message, {"user_id":..., "email":...} or None).
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable.", None
    try:
        token_hash = _hash_token(token)
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token_hash = ?", (token_hash,)
        ).fetchone()

        if not row:
            return False, "This reset link is invalid.", None
        if row["used"]:
            return False, "This reset link has already been used.", None

        expires_at = datetime.fromisoformat(row["expires_at"])
        now = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.utcnow()
        if now > expires_at:
            return False, "This reset link has expired. Please request a new one.", None

        return True, "Valid.", {"user_id": row["user_id"], "email": row["email"]}
    except Exception as e:
        logger.error("Failed to verify reset token: %s", e)
        return False, "Could not verify reset link. Please try again.", None
    finally:
        conn.close()


def consume_reset_token(token: str) -> tuple[bool, str, dict | None]:
    """Verify AND mark a token used in one atomic step (call this right
    before actually changing the password, not in verify_reset_token,
    so a token isn't burned just from loading the reset-password page).
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable.", None
    try:
        token_hash = _hash_token(token)
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token_hash = ?", (token_hash,)
        ).fetchone()

        if not row:
            return False, "This reset link is invalid.", None
        if row["used"]:
            return False, "This reset link has already been used.", None

        expires_at = datetime.fromisoformat(row["expires_at"])
        now = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.utcnow()
        if now > expires_at:
            return False, "This reset link has expired. Please request a new one.", None

        conn.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (row["id"],))
        conn.commit()
        return True, "Token consumed.", {"user_id": row["user_id"], "email": row["email"]}
    except Exception as e:
        logger.error("Failed to consume reset token: %s", e)
        return False, "Could not verify reset link. Please try again.", None
    finally:
        conn.close()


def cleanup_expired_reset_tokens():
    """Remove expired/used reset tokens. Safe to call periodically."""
    conn = _get_db()
    if not conn:
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("DELETE FROM password_resets WHERE expires_at < ? OR used = 1", (now,))
        conn.commit()
    except Exception as e:
        logger.error("Failed to cleanup expired reset tokens: %s", e)
    finally:
        conn.close()