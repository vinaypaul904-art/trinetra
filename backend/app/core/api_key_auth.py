"""
TRINETRA — User Authentication with Registration

Users register with username + email + password (stored in SQLite with
bcrypt-hashed passwords). Session tokens are stored in the database
for persistence across server restarts.

Security features:
- bcrypt password hashing (GPU-resistant)
- Database-backed session storage (survives restarts)
- Account lockout after 5 failed login attempts (15-minute window)
- Generic error messages to prevent username enumeration

Usage:
    POST /api/auth/register  { "username": "...", "email": "...", "password": "..." }
    → { "success": true, "token": "...", "username": "..." }

    POST /api/auth/login  { "username": "...", "password": "..." }
    → { "success": true, "token": "...", "username": "..." }
"""

import secrets
import logging
import os
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException

logger = logging.getLogger("trinetra.auth")

# Dedicated SQLite database for auth (works regardless of main DATABASE_URL)
# File is created in the app working directory (current dir or /app in Docker)
_AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "trinetra_auth.db")

# Account lockout settings
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Password strength requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
PASSWORD_HISTORY_SIZE = 5  # Number of previous passwords to remember


# ── Password Strength Validation ──────────────────────────

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength requirements.
    
    Returns (is_valid, error_message). If valid, error_message is empty.
    
    Requirements:
    - Minimum 8 characters
    - Maximum 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    if not password:
        return False, "Password is required."
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must not exceed {MAX_PASSWORD_LENGTH} characters."
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    
    special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?')
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    
    # Check for common weak passwords
    weak_passwords = [
        'password', 'password1', 'password123', 'qwerty', 'qwerty123',
        'abc123', 'letmein', 'admin', 'admin123', 'welcome', 'monkey',
        'master', 'dragon', 'login', 'princess', 'football', 'shadow',
        'sunshine', 'trustno1', 'iloveyou', 'batman', 'access', 'hello',
        'charlie', 'donald', 'password!', 'passw0rd', '12345678',
    ]
    if password.lower() in weak_passwords:
        return False, "This password is too common. Please choose a stronger password."
    
    return True, ""


# ── Password hashing (bcrypt) ──────────────────────────────


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (GPU-resistant).
    Returns the bcrypt hash string directly.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = good balance of security/speed
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored bcrypt hash."""
    try:
        password_bytes = password.encode('utf-8')
        stored_bytes = stored_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, stored_bytes)
    except Exception:
        return False


# ── Database helpers — direct SQLite access ───────────────


def _get_db():
    """Get a synchronous SQLite connection for auth operations.
    Uses a dedicated auth database file independent of the main DATABASE_URL.
    """
    import sqlite3

    conn = sqlite3.connect(_AUTH_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_users_table():
    """Create the users, sessions, login_attempts, password_history,
    and payment-related tables if they don't exist."""
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT,
                attempted_at TEXT DEFAULT (datetime('now')),
                success INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS password_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'INR',
                credits INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_method TEXT,
                cf_payment_id TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_login_attempts_username ON login_attempts(username, attempted_at);
            CREATE INDEX IF NOT EXISTS idx_password_history_user_id ON password_history(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_payment_history_order_id ON payment_history(order_id);
            CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id);
        """)
        conn.commit()
        # Migrate: add credits column to existing users table if missing
        try:
            conn.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass  # Column already exists
        return True
    except Exception as e:
        logger.error("Failed to init users table: %s", e)
        return False
    finally:
        conn.close()


def _add_password_to_history(user_id: int, password_hash: str):
    """Store a password hash in the user's password history."""
    conn = _get_db()
    if not conn:
        return
    try:
        conn.execute(
            "INSERT INTO password_history (user_id, password_hash) VALUES (?, ?)",
            (user_id, password_hash),
        )
        # Keep only the last PASSWORD_HISTORY_SIZE passwords for this user
        conn.execute("""
            DELETE FROM password_history WHERE user_id = ? AND id NOT IN (
                SELECT id FROM password_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            )
        """, (user_id, user_id, PASSWORD_HISTORY_SIZE))
        conn.commit()
    except Exception as e:
        logger.error("Failed to add password to history: %s", e)
    finally:
        conn.close()


def _is_password_reused(user_id: int, new_password: str) -> bool:
    """Check if the new password was used recently by this user.
    
    Returns True if the password matches any in the user's history.
    """
    conn = _get_db()
    if not conn:
        return False
    try:
        cursor = conn.execute(
            "SELECT password_hash FROM password_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, PASSWORD_HISTORY_SIZE),
        )
        for row in cursor:
            if _verify_password(new_password, row["password_hash"]):
                return True
        return False
    except Exception as e:
        logger.error("Failed to check password history: %s", e)
        return False
    finally:
        conn.close()


def _is_password_used_by_any_user(new_password: str) -> bool:
    """Check if the password was recently used by ANY user (for registration).
    
    Returns True if the password matches any recent password in the system.
    This prevents password reuse across all accounts.
    """
    conn = _get_db()
    if not conn:
        return False
    try:
        # Check against all users' recent password history
        cursor = conn.execute(
            "SELECT password_hash FROM password_history ORDER BY created_at DESC LIMIT ?",
            (PASSWORD_HISTORY_SIZE * 10,),  # Check more entries across all users
        )
        for row in cursor:
            if _verify_password(new_password, row["password_hash"]):
                return True
        return False
    except Exception as e:
        logger.error("Failed to check password history across users: %s", e)
        return False
    finally:
        conn.close()


def create_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """Create a new user. Returns (success, message).

    Note: Error messages are generic to prevent username/email enumeration.
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable"

    try:
        # Check if this is the first user (becomes admin)
        cursor = conn.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()["count"]
        is_admin = 1 if count == 0 else 0

        # Check password history for reuse (skip for first user with no history)
        if count > 0 and _is_password_used_by_any_user(password):
            return False, "This password was recently used. Please choose a different password."

        password_hash = _hash_password(password)
        # New users start with 0 credits — they must purchase a plan
        # (via PaymentPage / Cashfree) before using the OSINT tools.
        conn.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, credits) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, is_admin, 0),
        )
        conn.commit()
        
        # Get the new user's ID and add password to history
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _add_password_to_history(user_id, password_hash)
        
        role = "admin" if is_admin else "user"
        return True, role
    except Exception as e:
        err = str(e)
        # Generic error message to prevent username/email enumeration
        if "UNIQUE" in err:
            return False, "Username or email already exists"
        return False, "Registration failed. Please try again."
    finally:
        conn.close()


def get_user(username: str) -> dict | None:
    """Get a user by username. Returns None if not found."""
    conn = _get_db()
    if not conn:
        return None
    try:
        cursor = conn.execute(
            "SELECT id, username, email, password_hash, is_admin, created_at, credits FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception:
        return None
    finally:
        conn.close()


# ── Auth functions ────────────────────────────────────────


def is_auth_enabled() -> bool:
    """Auth is always enabled."""
    return True


def _record_login_attempt(username: str, success: bool, ip_address: str | None = None):
    """Record a login attempt for lockout tracking."""
    conn = _get_db()
    if not conn:
        return
    try:
        conn.execute(
            "INSERT INTO login_attempts (username, ip_address, success) VALUES (?, ?, ?)",
            (username, ip_address, 1 if success else 0),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to record login attempt: %s", e)
    finally:
        conn.close()


def _is_account_locked(username: str) -> bool:
    """Check if an account is locked due to too many failed attempts."""
    conn = _get_db()
    if not conn:
        return False
    try:
        # Use SQLite-compatible datetime format (matches datetime('now') default)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_DURATION_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM login_attempts WHERE username = ? AND attempted_at >= ? AND success = 0",
            (username, cutoff),
        )
        count = cursor.fetchone()["count"]
        return count >= MAX_LOGIN_ATTEMPTS
    except Exception as e:
        logger.error("Failed to check account lockout: %s", e)
        return False
    finally:
        conn.close()


def _clear_failed_attempts(username: str):
    """Clear failed login attempts after successful login."""
    conn = _get_db()
    if not conn:
        return
    try:
        conn.execute(
            "DELETE FROM login_attempts WHERE username = ? AND success = 0",
            (username,),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to clear login attempts: %s", e)
    finally:
        conn.close()


def login(username: str, password: str, ip_address: str | None = None) -> str | None:
    """Validate credentials and generate a session token.

    Features:
    - Account lockout after MAX_LOGIN_ATTEMPTS failed attempts
    - Generic error messages to prevent username enumeration
    - Database-backed session storage

    Returns the token string on success, or None on failure.
    """
    if not username or not password:
        return None

    # Check if account is locked
    if _is_account_locked(username):
        logger.warning("Login attempt for locked account: %s", username)
        # Still verify password to prevent timing attacks, but don't create session
        user = get_user(username)
        if user:
            _verify_password(password, user["password_hash"])
        return None

    user = get_user(username)
    if not user:
        # Record failed attempt even for non-existent users (prevents timing attacks)
        _record_login_attempt(username, False, ip_address)
        return None

    if not _verify_password(password, user["password_hash"]):
        _record_login_attempt(username, False, ip_address)
        return None

    # Successful login
    _record_login_attempt(username, True, ip_address)
    _clear_failed_attempts(username)

    # Generate a cryptographically random token
    token = secrets.token_hex(32)
    
    # Store session in database
    conn = _get_db()
    if conn:
        try:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            conn.execute(
                "INSERT INTO sessions (token, user_id, username, expires_at) VALUES (?, ?, ?, ?)",
                (token, user["id"], username, expires_at),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to create session: %s", e)
        finally:
            conn.close()
    
    return token


def create_session_for_user(username: str) -> str | None:
    """Issue a new session token for `username` WITHOUT checking a password.

    Only safe to call immediately after the caller has independently
    verified identity another way — specifically, right after
    create_user_from_hash() succeeds following OTP email verification.
    Never expose this to an endpoint that takes arbitrary user input.
    """
    user = get_user(username)
    if not user:
        return None

    token = secrets.token_hex(32)
    conn = _get_db()
    if not conn:
        return None
    try:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        conn.execute(
            "INSERT INTO sessions (token, user_id, username, expires_at) VALUES (?, ?, ?, ?)",
            (token, user["id"], username, expires_at),
        )
        conn.commit()
        return token
    except Exception as e:
        logger.error("Failed to create session for verified user: %s", e)
        return None
    finally:
        conn.close()


def logout_token(token: str) -> bool:
    """Invalidate a session token. Returns True if it existed."""
    conn = _get_db()
    if not conn:
        return False
    try:
        cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Failed to logout: %s", e)
        return False
    finally:
        conn.close()


def validate_token(token: str | None) -> bool:
    """Check if a session token is valid.

    Returns True if the token exists in the database and hasn't expired.
    """
    if not token:
        return False

    conn = _get_db()
    if not conn:
        return False
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "SELECT id FROM sessions WHERE token = ? AND expires_at >= ?",
            (token, now),
        )
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error("Failed to validate token: %s", e)
        return False
    finally:
        conn.close()


def get_username_for_token(token: str) -> str | None:
    """Get the username associated with a token, or None."""
    conn = _get_db()
    if not conn:
        return None
    try:
        cursor = conn.execute(
            "SELECT username FROM sessions WHERE token = ?",
            (token,),
        )
        row = cursor.fetchone()
        return row["username"] if row else None
    except Exception:
        return None
    finally:
        conn.close()


def clear_all_tokens():
    """Clear all session tokens (used for security purposes)."""
    conn = _get_db()
    if not conn:
        return
    try:
        conn.execute("DELETE FROM sessions")
        conn.commit()
    except Exception as e:
        logger.error("Failed to clear tokens: %s", e)
    finally:
        conn.close()


# ── Credits system ───────────────────────────────────────


def get_user_credits(username: str) -> int:
    """Get the credit balance for a user."""
    user = get_user(username)
    if not user:
        return 0
    return user.get("credits", 0)


def get_user_id(username: str) -> int | None:
    """Get the user ID for a username."""
    conn = _get_db()
    if not conn:
        return None
    try:
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return row["id"] if row else None
    except Exception:
        return None
    finally:
        conn.close()


def add_credits(username: str, amount: int) -> bool:
    """Add credits to a user's account. Returns True on success."""
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.execute(
            "UPDATE users SET credits = credits + ? WHERE username = ?",
            (amount, username),
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        logger.error("Failed to add credits: %s", e)
        return False
    finally:
        conn.close()


def deduct_credits(username: str, amount: int = 1) -> tuple[bool, int]:
    """Deduct credits from a user's account atomically.

    Returns (success, remaining_credits).
    If insufficient credits, returns (False, current_balance).
    """
    conn = _get_db()
    if not conn:
        return False, 0
    try:
        # Atomic: only deduct if enough credits available
        cursor = conn.execute(
            "UPDATE users SET credits = credits - ? WHERE username = ? AND credits >= ?",
            (amount, username, amount),
        )
        if cursor.rowcount == 0:
            # No row updated — either user not found or insufficient credits
            check = conn.execute(
                "SELECT credits FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return False, (check["credits"] if check else 0)
        conn.commit()
        # Fetch remaining balance
        row = conn.execute(
            "SELECT credits FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        remaining = row["credits"] if row else 0
        return True, remaining
    except Exception as e:
        logger.error("Failed to deduct credits: %s", e)
        return False, 0
    finally:
        conn.close()


def record_payment(
    order_id: str,
    username: str,
    amount: float,
    credits: int,
    status: str = "pending",
    payment_method: str | None = None,
    cf_payment_id: str | None = None,
) -> bool:
    """Record a payment in the payment_history table."""
    user_id = get_user_id(username)
    if not user_id:
        return False
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.execute(
            "INSERT OR IGNORE INTO payment_history (order_id, user_id, amount, credits, status, payment_method, cf_payment_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (order_id, user_id, amount, credits, status, payment_method, cf_payment_id),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to record payment: %s", e)
        return False
    finally:
        conn.close()


def update_payment_status(
    order_id: str,
    status: str,
    payment_method: str | None = None,
    cf_payment_id: str | None = None,
) -> bool:
    """Update the status of a payment order."""
    conn = _get_db()
    if not conn:
        return False
    try:
        updates = ["status = ?", "updated_at = datetime('now')"]
        params: list = [status]
        if payment_method:
            updates.append("payment_method = ?")
            params.append(payment_method)
        if cf_payment_id:
            updates.append("cf_payment_id = ?")
            params.append(cf_payment_id)
        params.append(order_id)
        conn.execute(
            f"UPDATE payment_history SET {', '.join(updates)} WHERE order_id = ?",
            params,
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to update payment status: %s", e)
        return False
    finally:
        conn.close()


def get_payment_by_order(order_id: str) -> dict | None:
    """Get a payment record by order ID."""
    conn = _get_db()
    if not conn:
        return None
    try:
        cursor = conn.execute(
            "SELECT ph.*, u.username FROM payment_history ph JOIN users u ON ph.user_id = u.id WHERE ph.order_id = ?",
            (order_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def get_user_payment_history(username: str) -> list[dict]:
    """Get payment history for a user."""
    user_id = get_user_id(username)
    if not user_id:
        return []
    conn = _get_db()
    if not conn:
        return []
    try:
        cursor = conn.execute(
            "SELECT * FROM payment_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def cleanup_expired_sessions():
    """Remove expired sessions from the database."""
    conn = _get_db()
    if not conn:
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 day'))")
        conn.commit()
    except Exception as e:
        logger.error("Failed to cleanup sessions: %s", e)
    finally:
        conn.close()


# ── Header extraction (kept from previous API key system) ─


def _extract_key_from_headers(request: Request) -> str | None:
    """Extract token from request headers.

    Supports:
        - Authorization: Bearer <token>
        - X-API-Key: <token>  (legacy name)
    """
    token = request.headers.get("x-api-key")
    if token:
        return token

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return None


def _extract_key_from_query(request: Request) -> str | None:
    """Extract token from query string (for WebSocket upgrade requests)."""
    return request.query_params.get("api_key")


# ── FastAPI dependency ────────────────────────────────────


async def require_api_key(request: Request) -> str | None:
    """FastAPI dependency for HTTP endpoints.

    Checks for a valid session token in headers.
    Raises 401 if no valid token is provided.
    """
    token = _extract_key_from_headers(request)
    if token is None:
        token = _extract_key_from_query(request)

    if not validate_token(token):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "detail": "Valid session token required. "
                "Register via POST /api/auth/register then "
                "log in via POST /api/auth/login.",
            },
        )

    return token


def validate_ws_message_key(data: dict) -> bool:
    """Validate session token from the first WebSocket JSON message."""
    return validate_token(data.get("api_key"))


def change_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
    """Change a user's password.
    
    Returns (success, message).
    
    Security features:
    - Verifies current password before allowing change
    - Checks password history to prevent reuse
    - Validates new password strength
    - Adds new password to history
    """
    # Validate new password strength
    password_valid, password_error = validate_password_strength(new_password)
    if not password_valid:
        return False, password_error
    
    # Check if new password is same as current
    if current_password == new_password:
        return False, "New password must be different from current password."
    
    # Get user
    user = get_user(username)
    if not user:
        return False, "User not found."
    
    # Verify current password
    if not _verify_password(current_password, user["password_hash"]):
        return False, "Current password is incorrect."
    
    # Check password history
    if _is_password_reused(user["id"], new_password):
        return False, f"This password was recently used. Please choose a different password (last {PASSWORD_HISTORY_SIZE} passwords are remembered)."
    
    # Update password
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable"
    
    try:
        new_hash = _hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user["id"]),
        )
        conn.commit()
        
        # Add to history
        _add_password_to_history(user["id"], new_hash)
        
        return True, "Password changed successfully."
    except Exception as e:
        logger.error("Failed to change password: %s", e)
        return False, "Failed to change password. Please try again."
    finally:
        conn.close()


# ── OTP signup support (additive — used by email_otp.py / routes.py) ──
# These functions do not alter any existing behavior above; they exist so
# the OTP-gated signup flow can validate/hash a password up front (while
# it still has the plaintext) and only insert the `users` row after the
# email has been verified, without double-hashing the password.


def hash_password_for_storage(password: str) -> str:
    """Public wrapper around the internal bcrypt hasher, for use by the
    OTP signup flow (which must hash the password before the OTP is sent,
    then store only the hash — never the plaintext — until verified).
    """
    return _hash_password(password)


def check_password_reuse_any_user(password: str) -> bool:
    """Public wrapper: True if `password` was recently used by any account.

    Used by the OTP request step (which still has the plaintext password)
    to preserve the existing password-reuse protection even though the
    actual `users` row isn't created until after OTP verification.
    """
    return _is_password_used_by_any_user(password)


def create_user_from_hash(username: str, email: str, password_hash: str) -> tuple[bool, str]:
    """Create a new user from an already-computed bcrypt hash.

    Identical to create_user() except it skips hashing (the OTP flow hashes
    the password at request time, before the plaintext is discarded) and
    skips the reuse check (already performed at request time via
    check_password_reuse_any_user). Returns (success, message_or_role).

    New users start with 0 credits — same as create_user() — they must
    purchase a plan (via PaymentPage / Cashfree) before using the OSINT
    tools, exactly like accounts created through the direct signup path.
    """
    conn = _get_db()
    if not conn:
        return False, "Service temporarily unavailable"

    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()["count"]
        is_admin = 1 if count == 0 else 0

        conn.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, credits) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, is_admin, 0),
        )
        conn.commit()

        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _add_password_to_history(user_id, password_hash)

        role = "admin" if is_admin else "user"
        return True, role
    except Exception as e:
        err = str(e)
        if "UNIQUE" in err:
            return False, "Username or email already exists"
        return False, "Registration failed. Please try again."
    finally:
        conn.close()

def get_user_id_by_email(email: str) -> tuple[int, str] | None:
    """Look up (user_id, username) by email. Used by the forgot-password flow."""
    conn = _get_db()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT id, username FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return None
        return row["id"], row["username"]
    except Exception as e:
        logger.error("Failed to look up user by email: %s", e)
        return None
    finally:
        conn.close()

def set_user_password_hash(user_id: int, new_hash: str) -> bool:
    """Directly set a user's password hash by user_id (used by the
    forgot-password reset flow, where there's no 'current password' to
    verify — the emailed token is the proof of identity instead).
    """
    conn = _get_db()
    if not conn:
        return False
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
        _add_password_to_history(user_id, new_hash)
        return True
    except Exception as e:
        logger.error("Failed to set password hash for user_id %s: %s", user_id, e)
        return False
    finally:
        conn.close()