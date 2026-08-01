import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trinetra")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.rate_limiter import RateLimitMiddleware
from app.plugins.registry import plugin_registry
from app.api.routes import router
from app.api.websocket_routes import router as ws_router
from app.api.watch_routes import router as watch_router
from app.api.threat_routes import router as threat_router
from app.api.data_routes import router as data_router
from app.api.chat_routes import router as chat_router
from app.api.report_routes import router as report_router
from app.api.payment_routes import router as payment_router
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.services.threat_feed import threat_feed
from app.services.telegram_bot import TelegramBotService


# Telegram OSINT bot instance (initialized in lifespan)
telegram_bot: TelegramBotService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: discover plugins
    plugin_registry.discover()
    
    # Create DB tables if they don't exist (PostgreSQL init.sql handles this via Docker)
    _ensure_db_tables()
    # Init users table for registration auth
    from app.core.api_key_auth import init_users_table
    init_users_table()

    # Init OTP signup-verification table (email verification feature)
    from app.core.email_otp import init_pending_signups_table, cleanup_expired_pending_signups
    init_pending_signups_table()
    cleanup_expired_pending_signups()
    
    # Start background watch scheduler
    start_scheduler()
    
    # Start threat feed generator
    await threat_feed.start()
    
    # Start Telegram OSINT bot if token is configured
    global telegram_bot
    if settings.telegram_bot_token:
        telegram_bot = TelegramBotService(
            token=settings.telegram_bot_token,
            api_url=settings.telegram_osint_api_url,
            api_key=settings.telegram_osint_api_key,
        )
        await telegram_bot.start()
    else:
        logger.info("Telegram OSINT Bot: not configured (set TELEGRAM_BOT_TOKEN to enable)")
    
    logger.info("TRINETRA initialized - %d OSINT plugins registered", plugin_registry.count)
    logger.info(
        "  Categories: Infrastructure (%d), Threat (%d), Advanced (%d)",
        len(plugin_registry.get_by_category('infrastructure')),
        len(plugin_registry.get_by_category('threat')),
        len(plugin_registry.get_by_category('advanced')),
    )
    logger.info("  Watch scheduler: running")

    yield

    # Shutdown
    if telegram_bot:
        await telegram_bot.stop()
    await threat_feed.stop()
    await stop_scheduler()
    logger.info("TRINETRA shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

# CORS — use specific methods in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Security response headers
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Rate limiting — in-memory, per-IP sliding window
app.add_middleware(RateLimitMiddleware, trust_proxy=settings.trust_proxy_headers)

# Routes
app.include_router(router)
app.include_router(ws_router)
app.include_router(watch_router)
app.include_router(threat_router)
app.include_router(data_router)
app.include_router(chat_router)
app.include_router(report_router)
app.include_router(payment_router)

@app.get("/")
async def root():
    """Root endpoint with API overview."""
    return {
        "app": settings.app_name,
        "version": settings.version,
        "status": "running",
        "plugins_available": plugin_registry.count,
        "docs": "/docs",
        "endpoints": {
            "search": "POST /api/search — run OSINT scan on a target",
            "detect": "GET /api/detect?target=example.com — auto-detect target type",
            "plugins": "GET /api/plugins — list all available plugins",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint — lightweight, returns instantly."""
    return {
        "status": "healthy",
        "plugins_available": plugin_registry.count,
        "categories": {
            "infrastructure": len(plugin_registry.get_by_category("infrastructure")),
            "threat": len(plugin_registry.get_by_category("threat")),
            "advanced": len(plugin_registry.get_by_category("advanced")),
        },
    }


def _ensure_db_tables():
    """Ensure database tables exist for SQLite dev mode.
    
    In Docker/PostgreSQL mode, init.sql handles this.
    For local SQLite dev, we create the tables here.
    """
    import sqlite3
    import os
    from app.core.config import settings

    if not settings.database_url.startswith("sqlite"):
        return  # PostgreSQL mode — init.sql handles it

    # Extract file path from sqlite+aiosqlite:///path or sqlite+aiosqlite:// (in-memory)
    db_path = settings.database_url.removeprefix("sqlite+aiosqlite://")
    # Strip leading / for path resolution
    if db_path.startswith("/"):
        db_path = db_path[1:]
    # In-memory database (no path) — nothing to do
    if not db_path:
        return
    if os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create tables matching init.sql for SQLite
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            target_type TEXT NOT NULL,
            plugin_id TEXT NOT NULL,
            plugin_name TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            gui_data TEXT DEFAULT '{}',
            terminal_data TEXT DEFAULT '',
            freshness TEXT DEFAULT 'fresh',
            error TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS watches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            target_type TEXT NOT NULL,
            plugin_ids TEXT DEFAULT '[]',
            interval_seconds INTEGER DEFAULT 3600,
            webhook_url TEXT,
            email TEXT,
            is_active INTEGER DEFAULT 1,
            last_checked_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watch_id INTEGER REFERENCES watches(id) ON DELETE CASCADE,
            target TEXT NOT NULL,
            plugin_id TEXT NOT NULL,
            old_data TEXT DEFAULT '{}',
            new_data TEXT DEFAULT '{}',
            summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_watches_active ON watches(is_active, last_checked_at);
        CREATE INDEX IF NOT EXISTS idx_scan_results_target ON scan_results(target);
        CREATE INDEX IF NOT EXISTS idx_alerts_watch_id ON alerts(watch_id);
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)