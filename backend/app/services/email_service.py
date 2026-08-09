"""
TRINETRA — Reusable Email Service (production-ready)

Clean architecture, responsibilities kept separate:
  - SMTP transport (this file)          — how to actually send bytes over SMTP
  - Jinja2 templates (app/templates/)   — how emails look (HTML), no business logic
  - Email-type functions (this file)    — WHAT to send for each business event
    (OTP, forgot-password, welcome, account-verified),
    built by rendering a template with the right context. No HTML is hardcoded
    in this file.
  - OTP business logic (app/core/email_otp.py) — UNCHANGED. It still owns OTP
    generation/verification/storage; it just calls send_otp_email() from here
    instead of from the old location.

Dev mode: if SMTP isn't configured (settings.smtp_configured is False), no
email is actually sent — the content is logged to the backend console instead,
exactly like before, so local development keeps working without any real
credentials. The moment SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD are filled
into .env, sending switches on automatically — NO code changes required.
This also means switching later from a personal Gmail account to
noreply@hackhalt.org is a pure .env edit, nothing else.

NOTE: This module supersedes app/core/email_service.py. That file is left in
place, untouched and simply no longer imported anywhere, per the project rule
of never deleting existing files. Only the one import line in
app/api/routes.py was repointed here — everything else about the OTP flow
(app/core/email_otp.py, the three /auth/register* endpoints) is unchanged.
"""

import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger("trinetra.email")

# ==================== Template rendering ====================

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, **context) -> str:
    """Render an HTML email template with the given context variables.

    Automatically injects `current_year` and `app_name` so every template
    (via the shared _base.html layout) can use them without every caller
    having to pass them explicitly.
    """
    context.setdefault("current_year", datetime.now(timezone.utc).year)
    context.setdefault("app_name", "TRINETRA")
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


# ==================== SMTP transport ====================

class EmailSendError(Exception):
    """Raised when an email fails to send via SMTP."""


def _build_message(to_email: str, subject: str, html_body: str, text_body: str) -> MIMEMultipart:
    """Build a multipart/alternative email (plain-text fallback + HTML)."""
    msg = MIMEMultipart("alternative")
    from_name = settings.smtp_from_name or "TRINETRA"
    from_addr = settings.smtp_from_email or settings.smtp_username
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


def _send_sync(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    """Blocking SMTP send. Only ever called via asyncio.to_thread — never
    directly inside an async route handler, so it can't stall the event loop.

    Automatically uses STARTTLS (port 587, the default — works for Gmail and
    virtually every provider) or implicit SSL (port 465), based on
    SMTP_USE_TLS / SMTP_USE_SSL in .env. Raises EmailSendError on any failure.
    """
    from_addr = settings.smtp_from_email or settings.smtp_username
    msg = _build_message(to_email, subject, html_body, text_body)

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.ehlo()
                if settings.smtp_use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(from_addr, [to_email], msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP authentication failed: %s", e)
        raise EmailSendError(
            "SMTP authentication failed. Check SMTP_USERNAME/SMTP_PASSWORD "
            "(for Gmail, this must be a 16-character App Password, not your login password)."
        ) from e
    except (smtplib.SMTPException, OSError) as e:
        logger.error("SMTP send failed: %s", e)
        raise EmailSendError(f"Could not send email: {e}") from e


async def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
    """Send an email. Returns (success, message).

    Dev mode (SMTP not configured) -> logs the content instead of sending,
    returns success=True so signup/etc. flows keep working with zero setup.
    Production (SMTP configured)   -> actually sends via SMTP.
    The call site never needs to know or care which mode is active.
    """
    if not settings.smtp_configured:
        logger.warning(
            "SMTP not configured — DEV MODE email (not actually sent) to %s:\nSubject: %s\n%s",
            to_email, subject, text_body,
        )
        return True, "dev-mode: email logged to console instead of sent"

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, html_body, text_body)
        return True, "sent"
    except EmailSendError as e:
        return False, str(e)


# ==================== Business-event email functions ====================
# Each function below: builds context -> renders the matching template ->
# builds a plain-text fallback -> calls send_email(). No HTML lives here.

async def send_otp_email(to_email: str, username: str, otp_code: str) -> tuple[bool, str]:
    """Signup verification OTP email.

    Called from the existing OTP request/resend flow (app/core/email_otp.py
    via app/api/routes.py). Signature is IDENTICAL to the previous
    implementation in app/core/email_service.py, so the only change required
    anywhere else in the codebase is the import path in routes.py.
    """
    expiry_minutes = settings.otp_expiry_minutes
    html_body = render_template(
        "otp.html",
        username=username,
        otp_code=otp_code,
        expiry_minutes=expiry_minutes,
    )
    text_body = (
        f"Hi {username},\n\n"
        f"Your TRINETRA verification code is: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. "
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— TRINETRA OSINT Platform"
    )
    return await send_email(to_email, "Verify your TRINETRA Account", html_body, text_body)


async def send_forgot_password_email(
    to_email: str, username: str, reset_url: str, expiry_minutes: int = 30
) -> tuple[bool, str]:
    """Password-reset email.

    Not yet called anywhere — there's no forgot-password endpoint in the
    codebase yet. Ready to use as soon as that flow is built, e.g.:
        await send_forgot_password_email(user_email, username, reset_link)
    """
    html_body = render_template(
        "forgot_password.html",
        username=username,
        reset_url=reset_url,
        expiry_minutes=expiry_minutes,
    )
    text_body = (
        f"Hi {username},\n\n"
        f"We received a request to reset your TRINETRA password. Open this link to choose a new one:\n"
        f"{reset_url}\n\n"
        f"This link expires in {expiry_minutes} minutes. "
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— TRINETRA OSINT Platform"
    )
    return await send_email(to_email, "Reset your TRINETRA password", html_body, text_body)


async def send_welcome_email(
    to_email: str, username: str, dashboard_url: str = "http://localhost:3000"
) -> tuple[bool, str]:
    """Onboarding email for after successful verification.

    Not yet auto-triggered anywhere — nothing currently calls this. If you
    want it sent automatically after OTP verification, call it from
    auth_register_verify_otp() in routes.py right after create_user_from_hash()
    succeeds, e.g.:
        await send_welcome_email(email, username)
    Left as an explicit opt-in rather than auto-wired, since that's a product
    decision (whether to send both a welcome email AND the OTP email) that
    wasn't part of this task.
    """
    html_body = render_template(
        "welcome.html",
        username=username,
        dashboard_url=dashboard_url,
    )
    text_body = (
        f"Welcome, {username}!\n\n"
        f"Your email is verified and your TRINETRA account is ready. "
        f"You now have access to the full OSINT & SOC analyst dashboard — "
        f"OSINT scans, the live threat map, watchlists, reports, and the AI assistant.\n\n"
        f"Open your dashboard: {dashboard_url}\n\n"
        f"— TRINETRA OSINT Platform"
    )
    return await send_email(to_email, "Welcome to TRINETRA", html_body, text_body)


async def send_account_verified_email(to_email: str, username: str) -> tuple[bool, str]:
    """Short confirmation notice that an email was verified.

    Distinct from send_welcome_email() (the fuller onboarding email with the
    feature list and dashboard button) — this is a brief "you're verified"
    receipt. Use whichever fits your flow, or both. Not yet auto-triggered
    anywhere.
    """
    html_body = render_template("account_verified.html", username=username)
    text_body = (
        f"Hi {username},\n\n"
        f"This confirms your email address has been successfully verified on TRINETRA. "
        f"Your account is fully active.\n\n"
        f"If you didn't perform this action, please contact your administrator immediately.\n\n"
        f"— TRINETRA OSINT Platform"
    )
    return await send_email(to_email, "Your TRINETRA account is verified", html_body, text_body)