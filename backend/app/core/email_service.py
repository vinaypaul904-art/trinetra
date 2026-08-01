"""
TRINETRA — Email Sending Service (SMTP)

Generic SMTP mailer used to deliver signup OTP codes. Works with Gmail,
SendGrid, Mailgun, Amazon SES, Zoho, Outlook/Office365, or any provider
that speaks standard SMTP (STARTTLS on 587 or implicit SSL on 465).

Dev mode: if SMTP isn't configured (settings.smtp_configured is False),
emails are not sent — instead the OTP is logged to the backend console
so local development keeps working without real credentials. This mirrors
how TELEGRAM_BOT_TOKEN / GEMINI_API_KEY are handled elsewhere in this app.

This module does not touch any existing auth, session, or plugin code.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("trinetra.email")


class EmailSendError(Exception):
    """Raised when an email fails to send via SMTP."""


def _build_message(to_email: str, subject: str, html_body: str, text_body: str) -> MIMEMultipart:
    """Build a multipart/alternative email (plain-text + HTML)."""
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
    """Blocking SMTP send — runs in a worker thread via asyncio.to_thread.

    Raises EmailSendError on any failure (auth, connection, etc.).
    """
    from_addr = settings.smtp_from_email or settings.smtp_username
    msg = _build_message(to_email, subject, html_body, text_body)

    try:
        if settings.smtp_use_ssl:
            # Implicit SSL — typically port 465
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            # STARTTLS — typically port 587 (default, works for Gmail and most providers)
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
            "(for Gmail, this must be an App Password, not your login password)."
        ) from e
    except (smtplib.SMTPException, OSError) as e:
        logger.error("SMTP send failed: %s", e)
        raise EmailSendError(f"Could not send email: {e}") from e


async def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
    """Send an email. Returns (success, message).

    In dev mode (SMTP not configured), logs the email content instead of
    sending and returns success=True so signup flows still work locally.
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


def _otp_templates(username: str, otp_code: str, expiry_minutes: int) -> tuple[str, str]:
    """Build (html_body, text_body) for the OTP verification email."""
    text_body = (
        f"Hi {username},\n\n"
        f"Your TRINETRA verification code is: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. "
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— TRINETRA OSINT Platform"
    )

    html_body = f"""\
<div style="font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#050810; padding:32px; color:#f0f2f5;">
  <div style="max-width:420px; margin:0 auto; background:#0b0f1a; border:1px solid rgba(50,65,90,0.45); border-radius:12px; padding:28px;">
    <div style="font-size:13px; letter-spacing:2px; color:#3b82f6; font-weight:700;">TRINETRA</div>
    <h2 style="margin:12px 0 4px; font-size:18px; color:#f0f2f5;">Verify your email</h2>
    <p style="margin:0 0 20px; font-size:13px; color:#94a3b8;">Hi {username}, use the code below to finish creating your account.</p>
    <div style="background:#101728; border:1px solid rgba(59,130,246,0.35); border-radius:8px; padding:16px; text-align:center; margin-bottom:20px;">
      <span style="font-family:'JetBrains Mono', monospace; font-size:28px; letter-spacing:8px; font-weight:700; color:#3b82f6;">{otp_code}</span>
    </div>
    <p style="margin:0; font-size:12px; color:#5a6a80;">This code expires in {expiry_minutes} minutes. If you didn't request this, you can safely ignore this email.</p>
  </div>
</div>"""

    return html_body, text_body


async def send_otp_email(to_email: str, username: str, otp_code: str) -> tuple[bool, str]:
    """Send (or, in dev mode, log) a signup verification OTP email.

    Returns (success, message).
    """
    html_body, text_body = _otp_templates(username, otp_code, settings.otp_expiry_minutes)
    subject = "Your TRINETRA verification code"
    return await send_email(to_email, subject, html_body, text_body)