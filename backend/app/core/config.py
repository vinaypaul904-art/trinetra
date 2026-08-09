from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "TRINETRA OSINT API"
    version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./trinetra.db"

    # Redis (optional for dev)
    redis_url: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Frontend base URL — used to build links inside emails (password reset, etc.)
    frontend_url: str = "http://localhost:3000"

    # Rate limiting
    trust_proxy_headers: bool = False  # Set true behind a known reverse proxy

    # Cache TTLs (seconds)
    cache_ttl_default: int = 3600  # 1 hour
    cache_ttl_long: int = 86400    # 24 hours

    # Plugin timeouts (seconds)
    plugin_timeout: int = 30

    # Authentication settings
    # Auth is always enabled. Users register via POST /api/auth/register
    # and log in via POST /api/auth/login.
    # First registered user becomes admin.

    # External API keys
    hibp_api_key: str = ""  # Have I Been Pwned v3 API key (set via HIBP_API_KEY env var)

    # Telegram OSINT Bot
    telegram_bot_token: str = ""  # Telegram Bot token from @BotFather
    telegram_osint_api_url: str = ""  # OSINT Leak API base URL
    telegram_osint_api_key: str = ""  # API key for OSINT API (sent as X-API-Key header)

    # AI Chatbot (Google Gemini)
    gemini_api_key: str = ""  # set via GEMINI_API_KEY env var
    gemini_model: str = "gemini-flash-latest"

    # ==================== Email Verification (SMTP) ====================
    # Generic SMTP settings — works with Gmail, SendGrid, Mailgun, Amazon SES,
    # Zoho Mail, Outlook/Office365, or any standard SMTP provider.
    #
    # Leave SMTP_HOST empty to run in "dev mode": OTPs are logged to the
    # backend console instead of emailed, so local development still works
    # without real credentials.
    smtp_host: str = ""            # e.g. smtp.gmail.com / smtp.sendgrid.net
    smtp_port: int = 587           # 587 = STARTTLS (most common), 465 = implicit SSL
    smtp_username: str = ""        # SMTP auth username (often your full email)
    smtp_password: str = ""        # SMTP auth password / app password / API key
    smtp_use_tls: bool = True      # STARTTLS — use with port 587
    smtp_use_ssl: bool = False     # Implicit SSL — use with port 465 (mutually exclusive with TLS)
    smtp_from_email: str = ""      # "From" address shown to recipients (defaults to smtp_username if empty)
    smtp_from_name: str = "TRINETRA"  # "From" display name

    # OTP behavior
    otp_length: int = 6                     # number of digits in the OTP code
    otp_expiry_minutes: int = 10            # how long an OTP stays valid
    otp_max_attempts: int = 5               # wrong-code attempts before the OTP is invalidated
    otp_resend_cooldown_seconds: int = 60   # minimum wait between resend requests
    otp_max_requests_per_hour: int = 5      # max OTP sends per email address per hour (anti-spam)

    # Fake/disposable email protection
    block_disposable_emails: bool = True   # reject known throwaway-email domains (mailinator, etc.)
    verify_email_mx: bool = True           # reject domains with no mail server (DNS MX lookup)

    @property
    def smtp_configured(self) -> bool:
        """True if enough SMTP settings are present to actually send email."""
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)

    # Cashfree Payment Gateway
    cashfree_app_id: str = ""       # set via CASHFREE_APP_ID env var
    cashfree_secret_key: str = ""   # set via CASHFREE_SECRET_KEY env var
    cashfree_env: str = "sandbox"   # "sandbox" or "production"
    cashfree_webhook_url: str = "http://localhost:8000/api/payment/webhook"  # set via CASHFREE_WEBHOOK_URL env var

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()