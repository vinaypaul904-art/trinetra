"""
TRINETRA — Signup OTP Verification & Anti-Fraud Checks

Stores pending (not-yet-created) signups keyed by email, each holding a
hashed OTP code and an already-bcrypt-hashed password (never plaintext).
The actual `users` row is only created after the OTP is verified — see
`create_user_from_hash()` in api_key_auth.py, called from routes.py.

Also provides email-quality checks used before an OTP is ever sent:
  - format validation
  - disposable/throwaway email domain blocklist
  - MX record lookup (rejects domains that can't receive mail at all)

Uses the same dedicated SQLite auth database as api_key_auth.py
(AUTH_DB_PATH, default "trinetra_auth.db") so pending-signup lookups can
be checked against the existing `users` table for uniqueness.

This module does not modify any existing table, function, or behavior.
"""

import asyncio
import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta

from app.core.config import settings

logger = logging.getLogger("trinetra.email_otp")

# Same auth DB file used by api_key_auth.py — keep in sync with that module.
_AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "trinetra_auth.db")

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Well-known disposable / throwaway email domains. Not exhaustive, but
# blocks the overwhelming majority of spam/fake signups seen in practice.
DISPOSABLE_EMAIL_DOMAINS: set[str] = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.info", "guerrillamail.biz",
    "10minutemail.com", "10minutemail.net", "temp-mail.org", "tempmail.com",
    "throwawaymail.com", "yopmail.com", "yopmail.net", "yopmail.fr",
    "trashmail.com", "trashmail.net", "dispostable.com", "sharklasers.com",
    "getnada.com", "maildrop.cc", "mintemail.com", "mailnesia.com",
    "fakeinbox.com", "spamgourmet.com", "spam4.me", "discard.email",
    "moakt.com", "mohmal.com", "emailondeck.com", "tempinbox.com",
    "throwam.com", "mailcatch.com", "burnermail.io", "tmpmail.org",
    "tmpmail.net", "tmail.ws", "inboxbear.com", "mailtemp.info",
    "cool.fr.nf", "jetable.org", "harakirimail.com", "mailtothis.com",
    "1secmail.com", "1secmail.org", "1secmail.net", "example.com",
}


# ── Database helpers ───────────────────────────────────────

def _get_db():
    import sqlite3

    conn = sqlite3.connect(_AUTH_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_pending_signups_table():
    """Create the pending_signups table if it doesn't exist."""
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pending_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                otp_salt TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                request_count INTEGER DEFAULT 1,
                window_started_at TEXT NOT NULL,
                last_sent_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_pending_signups_email ON pending_signups(email);
        """)
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to init pending_signups table: %s", e)
        return False
    finally:
        conn.close()


# ── Email quality checks (run BEFORE an OTP is ever sent) ──

def is_valid_email_format(email: str) -> bool:
    return bool(email) and bool(_EMAIL_RE.match(email))


def is_disposable_email(email: str) -> bool:
    """True if the email's domain is a known disposable/throwaway provider."""
    try:
        domain = email.rsplit("@", 1)[1].strip().lower()
    except IndexError:
        return False
    return domain in DISPOSABLE_EMAIL_DOMAINS


def _has_mx_record_sync(domain: str) -> bool:
    """Blocking MX lookup — only call via asyncio.to_thread."""
    try:
        import dns.resolver

        answers = dns.resolver.resolve(domain, "MX", lifetime=8)
        return len(answers) > 0
    except ImportError:
        # dnspython not available — don't block signups over a missing dep
        logger.warning("dnspython not installed — skipping MX check")
        return True
    except dns.resolver.NXDOMAIN:
        return False
    except dns.resolver.NoAnswer:
        # Some domains accept mail via an A record fallback rather than MX —
        # treat "no MX but domain resolves" as inconclusive, not a hard fail.
        try:
            dns.resolver.resolve(domain, "A", lifetime=8)
            return True
        except Exception:
            return False
    except Exception as e:
        logger.warning("MX lookup failed for %s: %s", domain, e)
        # Network hiccup / timeout — don't punish the user for our DNS issue
        return True


async def validate_email_for_signup(email: str) -> tuple[bool, str]:
    """Run all configured email-quality checks. Returns (is_valid, error_message)."""
    if not is_valid_email_format(email):
        return False, "Please enter a valid email address."

    if settings.block_disposable_emails and is_disposable_email(email):
        return False, "Disposable/temporary email addresses are not allowed. Please use a permanent email address."

    if settings.verify_email_mx:
        domain = email.rsplit("@", 1)[1].strip().lower()
        has_mx = await asyncio.to_thread(_has_mx_record_sync, domain)
        if not has_mx:
            return False, "This email domain does not appear to accept mail. Please check for typos or use a different address."

    return True, ""


# ── OTP generation & hashing ────────────────────────────────

def _generate_otp() -> str:
    length = settings.otp_length
    return "".join(secrets.choice("0123456789") for _ in range(length))


def _hash_otp(otp: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()


# ── Uniqueness check against existing users ─────────────────

def is_email_or_username_taken(email: str, username: str) -> bool:
    """Check the existing `users` table (same auth DB) for a conflict."""
    conn = _get_db()
    if not conn:
        return False
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE email = ? OR username = ?",
            (email, username),
        )
        return cursor.fetchone()["count"] > 0
    except Exception as e:
        logger.error("Failed to check existing users: %s", e)
        return False
    finally:
        conn.close()


# ── Request / resend OTP ────────────────────────────────────

def create_or_refresh_otp(username: str, email: str, password_hash: str) -> tuple[bool, str, str | None]:
    """Create a new pending signup + OTP, or refresh one for the same email.

    Enforces:
      - resend cooldown (OTP_RESEND_COOLDOWN_SECONDS)
      - hourly send limit per email (OTP_MAX_REQUESTS_PER_HOUR)

    Returns (success, message, otp_code). otp_code is the plaintext code
    the caller must email to the user — it is never returned again after this.
    """
    now = datetime.now(timezone.utc)
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable.", None

    try:
        row = conn.execute(
            "SELECT * FROM pending_signups WHERE email = ?", (email,)
        ).fetchone()

        window_started_at = now
        request_count = 1

        if row:
            last_sent_at = datetime.fromisoformat(row["last_sent_at"])
            elapsed = (now - last_sent_at).total_seconds()
            if elapsed < settings.otp_resend_cooldown_seconds:
                wait = int(settings.otp_resend_cooldown_seconds - elapsed)
                return False, f"Please wait {wait}s before requesting another code.", None

            window_started_at = datetime.fromisoformat(row["window_started_at"])
            if (now - window_started_at).total_seconds() > 3600:
                # Rolling hourly window has expired — reset it
                window_started_at = now
                request_count = 1
            else:
                request_count = row["request_count"] + 1
                if request_count > settings.otp_max_requests_per_hour:
                    return False, "Too many verification requests for this email. Please try again later.", None

        otp_code = _generate_otp()
        otp_salt = secrets.token_hex(8)
        otp_hash = _hash_otp(otp_code, otp_salt)
        expires_at = now + timedelta(minutes=settings.otp_expiry_minutes)

        conn.execute(
            """
            INSERT INTO pending_signups
                (email, username, password_hash, otp_hash, otp_salt, attempts,
                 request_count, window_started_at, last_sent_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                username = excluded.username,
                password_hash = excluded.password_hash,
                otp_hash = excluded.otp_hash,
                otp_salt = excluded.otp_salt,
                attempts = 0,
                request_count = excluded.request_count,
                window_started_at = excluded.window_started_at,
                last_sent_at = excluded.last_sent_at,
                expires_at = excluded.expires_at
            """,
            (
                email, username, password_hash, otp_hash, otp_salt,
                request_count, window_started_at.isoformat(), now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        return True, "OTP created.", otp_code
    except Exception as e:
        logger.error("Failed to create/refresh OTP for %s: %s", email, e)
        return False, "Could not start email verification. Please try again.", None
    finally:
        conn.close()


# ── Verify OTP ───────────────────────────────────────────────

def verify_and_consume_otp(email: str, otp_code: str) -> tuple[bool, str, dict | None]:
    """Check the OTP for `email`. On success, deletes the pending row and
    returns (True, message, {"username":..., "password_hash":...}) so the
    caller can create the real user account. On failure, increments the
    attempt counter and invalidates the OTP after too many wrong tries.
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable.", None

    try:
        row = conn.execute(
            "SELECT * FROM pending_signups WHERE email = ?", (email,)
        ).fetchone()

        if not row:
            return False, "No pending verification found for this email. Please sign up again.", None

        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(row["expires_at"])
        if now > expires_at:
            conn.execute("DELETE FROM pending_signups WHERE email = ?", (email,))
            conn.commit()
            return False, "This code has expired. Please request a new one.", None

        if row["attempts"] >= settings.otp_max_attempts:
            conn.execute("DELETE FROM pending_signups WHERE email = ?", (email,))
            conn.commit()
            return False, "Too many incorrect attempts. Please request a new code.", None

        expected_hash = _hash_otp(otp_code.strip(), row["otp_salt"])
        if not secrets.compare_digest(expected_hash, row["otp_hash"]):
            conn.execute(
                "UPDATE pending_signups SET attempts = attempts + 1 WHERE email = ?",
                (email,),
            )
            conn.commit()
            remaining = max(settings.otp_max_attempts - row["attempts"] - 1, 0)
            return False, f"Incorrect code. {remaining} attempt(s) remaining.", None

        # Success — consume the pending signup
        result = {"username": row["username"], "password_hash": row["password_hash"]}
        conn.execute("DELETE FROM pending_signups WHERE email = ?", (email,))
        conn.commit()
        return True, "Email verified.", result
    except Exception as e:
        logger.error("Failed to verify OTP for %s: %s", email, e)
        return False, "Could not verify code. Please try again.", None
    finally:
        conn.close()


def cleanup_expired_pending_signups():
    """Remove expired pending signups. Safe to call periodically."""
    conn = _get_db()
    if not conn:
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("DELETE FROM pending_signups WHERE expires_at < ?", (now,))
        conn.commit()
    except Exception as e:
        logger.error("Failed to cleanup expired pending signups: %s", e)
    finally:
        conn.close()

def get_pending_signup_identity(email: str) -> tuple[str, str] | None:
    """Return (username, password_hash) for an existing pending signup, or None.

    Used by the resend-OTP endpoint, which only receives an email address
    and needs to look up the username/password_hash already on file for it.
    """
    conn = _get_db()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT username, password_hash FROM pending_signups WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return None
        return row["username"], row["password_hash"]
    except Exception as e:
        logger.error("Failed to fetch pending signup for %s: %s", email, e)
        return None
    finally:
        conn.close()        