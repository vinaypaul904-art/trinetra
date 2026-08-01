"""
TRINETRA — In-Memory Rate Limiter Middleware

Sliding-window rate limiter that tracks requests per client IP.
No external dependencies (no Redis required) — uses an in-memory
dict that is pruned periodically.

Limits:
    - /api/search  : 10 requests per minute (expensive — spawns 19 plugins)
    - /ws/*        : 20 connections per minute
    - Everything else: 60 requests per minute
"""

import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("trinetra.rate_limiter")

# ── Rate limit configuration ────────────────────────────────

RATE_LIMITS: dict[str, tuple[int, int]] = {
    # path_prefix: (max_requests, window_seconds)
    # NOTE: order matters — more specific prefixes must come before shorter
    # ones they overlap with, since the first startswith() match wins below.
    "/api/auth/register/verify-otp": (15, 300),   # OTP-guessing brute force protection (5 min window)
    "/api/auth/register/resend-otp": (5, 300),    # resend spam protection (also has its own per-email cooldown)
    "/api/auth/register": (5, 300),               # signup-request spam protection (5 per 5 min per IP)
    "/api/search": (10, 60),
    "/ws/": (20, 60),
}
DEFAULT_LIMIT = (60, 60)  # 60 requests per minute for everything else
PRUNE_INTERVAL = 120  # prune stale entries every 2 minutes


def _get_client_ip(request: Request, trust_proxy: bool = False) -> str:
    """Extract client IP.

    When trust_proxy is False (default), always uses the direct connection IP.
    Set TRUST_PROXY_HEADERS=true when behind a known reverse proxy.
    """
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces per-IP rate limits."""

    def __init__(self, app, custom_limits: dict[str, tuple[int, int]] | None = None, trust_proxy: bool = False):
        super().__init__(app)
        # {ip: {path_key: [(timestamp, ...), ...]}}
        self._hits: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._last_prune = time.time()
        self._limits = {**RATE_LIMITS, **(custom_limits or {})}
        self._trust_proxy = trust_proxy

    def _prune_if_needed(self):
        """Remove entries older than the largest window to prevent memory leaks."""
        now = time.time()
        if now - self._last_prune < PRUNE_INTERVAL:
            return
        self._last_prune = now
        max_window = max(
            (window for _, window in self._limits.values()),
            default=DEFAULT_LIMIT[1],
        )
        cutoff = time.time() - max_window - 10
        stale_ips = []
        for ip, paths in self._hits.items():
            stale_paths = []
            for path_key, timestamps in paths.items():
                paths[path_key] = [t for t in timestamps if t > cutoff]
                if not paths[path_key]:
                    stale_paths.append(path_key)
            for pk in stale_paths:
                del paths[pk]
            if not paths:
                stale_ips.append(ip)
        for ip in stale_ips:
            del self._hits[ip]

    def _match_limit(self, path: str) -> tuple[int, int]:
        """Find the matching rate limit for a request path."""
        for prefix, limit in self._limits.items():
            if path.startswith(prefix):
                return limit
        return DEFAULT_LIMIT

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health checks, root, and OPTIONS preflights
        path = request.url.path
        if request.method == "OPTIONS" or path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        self._prune_if_needed()

        client_ip = _get_client_ip(request, trust_proxy=self._trust_proxy)
        max_requests, window_seconds = self._match_limit(path)
        now = time.time()
        cutoff = now - window_seconds

        # Get the relevant key (use path prefix for matching)
        path_key = path
        for prefix in self._limits:
            if path.startswith(prefix):
                path_key = prefix
                break

        # Record this hit
        hits = self._hits[client_ip][path_key]
        # Remove expired entries
        self._hits[client_ip][path_key] = [t for t in hits if t > cutoff]
        hits = self._hits[client_ip][path_key]

        if len(hits) >= max_requests:
            retry_after = int(hits[0] + window_seconds - now) + 1
            logger.warning(
                "Rate limit exceeded for %s on %s (%d/%d in %ds)",
                client_ip,
                path_key,
                len(hits),
                max_requests,
                window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests to {path_key}. "
                    f"Limit: {max_requests} per {window_seconds}s.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        response = await call_next(request)
        # Add rate limit headers for transparency
        remaining = max(0, max_requests - len(hits))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
        return response