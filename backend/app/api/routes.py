import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import httpx
from app.models.schemas import SearchRequest, SearchResponse, PluginResultData
from app.services.orchestrator import OrchestratorService
from app.core.detector import AutoDetect
from app.core.sanitizer import sanitize_target, validate_target, InputValidationError
from app.core.api_key_auth import (
    require_api_key, login, logout_token, is_auth_enabled, validate_token,
    create_user, validate_password_strength, change_password, get_username_for_token,
    hash_password_for_storage, check_password_reuse_any_user, create_user_from_hash,
    create_session_for_user, get_user_credits, deduct_credits, add_credits,
)
from app.core.email_otp import (
    validate_email_for_signup, is_email_or_username_taken, create_or_refresh_otp,
    verify_and_consume_otp, get_pending_signup_identity, cleanup_expired_pending_signups,
)
from app.core.email_service import send_otp_email
from app.core.config import settings
import re

logger = logging.getLogger("trinetra.target_intel")

router = APIRouter(prefix="/api", tags=["search"])
orchestrator = OrchestratorService()


@router.get("/auth/status")
async def auth_status():
    """Check authentication status and app info.

    This endpoint is intentionally unauthenticated so the login page
    can determine whether auth is needed.
    Auth is always enabled. Registration is open.
    """
    return {
        "auth_enabled": is_auth_enabled(),
        "registration_open": True,
        "app_name": settings.app_name,
        "version": settings.version,
        "payment_configured": bool(settings.cashfree_app_id and settings.cashfree_secret_key),
    }


@router.post("/auth/register")
async def auth_register(body: dict):
    """Start registration by validating input and emailing a verification code.

    Accepts: {"username": "...", "email": "...", "password": "..."}
    Returns {"success": true, "otp_required": true, "email": "..."} on success —
    the account is NOT created yet. It's only created after the code is
    confirmed via POST /api/auth/register/verify-otp.
    This endpoint is intentionally unauthenticated.
    """
    username = body.get("username", "").strip()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    # Validate input (unchanged from before)
    if not username or len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters.", "auth_enabled": True}
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return {"success": False, "error": "Username can only contain letters, numbers, underscores, and hyphens.", "auth_enabled": True}
    password_valid, password_error = validate_password_strength(password)
    if not password_valid:
        return {"success": False, "error": password_error, "auth_enabled": True}

    # Email quality checks — format, disposable-domain blocklist, MX record lookup
    email_valid, email_error = await validate_email_for_signup(email)
    if not email_valid:
        return {"success": False, "error": email_error, "auth_enabled": True}

    # Reject if this username/email is already a real account
    if is_email_or_username_taken(email, username):
        return {"success": False, "error": "Username or email already exists", "auth_enabled": True}

    # Password-reuse check (moved here from create_user — still has the
    # plaintext password at this point, which is discarded right after)
    if check_password_reuse_any_user(password):
        return {
            "success": False,
            "error": "This password was recently used. Please choose a different password.",
            "auth_enabled": True,
        }

    # Hash the password now — only the hash is ever stored while pending
    password_hash = hash_password_for_storage(password)

    ok, message, otp_code = create_or_refresh_otp(username, email, password_hash)
    if not ok:
        return {"success": False, "error": message, "auth_enabled": True}

    sent, send_message = await send_otp_email(email, username, otp_code)
    if not sent:
        logger.error("Failed to send OTP email to %s: %s", email, send_message)
        return {
            "success": False,
            "error": "Could not send verification email. Please try again in a moment.",
            "auth_enabled": True,
        }

    return {
        "success": True,
        "otp_required": True,
        "email": email,
        "message": f"We sent a verification code to {email}. Enter it to finish creating your account.",
        "auth_enabled": True,
    }


@router.post("/auth/register/verify-otp")
async def auth_register_verify_otp(body: dict):
    """Confirm the emailed OTP and create the account.

    Accepts: {"email": "...", "otp": "..."}
    Returns a session token on success, just like the old one-step register did.
    This endpoint is intentionally unauthenticated.
    """
    email = body.get("email", "").strip().lower()
    otp = str(body.get("otp", "")).strip()

    if not email or not otp:
        return {"success": False, "error": "Email and code are required.", "auth_enabled": True}

    verified, message, pending = verify_and_consume_otp(email, otp)
    if not verified:
        return {"success": False, "error": message, "auth_enabled": True}

    username = pending["username"]
    password_hash = pending["password_hash"]

    created, result = create_user_from_hash(username, email, password_hash)
    if not created:
        # Most likely a race: someone else took the username/email while this
        # OTP was pending. The email is verified, but the account can't be made.
        return {"success": False, "error": result, "auth_enabled": True}

    role = result  # "admin" or "user"
    token = create_session_for_user(username)

    return {
        "success": True,
        "token": token,
        "username": username,
        "role": role,
        "auth_enabled": True,
        "message": f"Email verified! Account created — you are logged in as {role}.",
    }


@router.post("/auth/register/resend-otp")
async def auth_register_resend_otp(body: dict):
    """Resend a verification code for an in-progress signup.

    Accepts: {"email": "..."}
    Subject to the same resend cooldown / hourly limit as the initial send.
    This endpoint is intentionally unauthenticated.
    """
    email = body.get("email", "").strip().lower()
    if not email:
        return {"success": False, "error": "Email is required.", "auth_enabled": True}

    identity = get_pending_signup_identity(email)
    if not identity:
        return {
            "success": False,
            "error": "No pending verification found for this email. Please sign up again.",
            "auth_enabled": True,
        }
    username, password_hash = identity

    ok, message, otp_code = create_or_refresh_otp(username, email, password_hash)
    if not ok:
        return {"success": False, "error": message, "auth_enabled": True}

    sent, send_message = await send_otp_email(email, username, otp_code)
    if not sent:
        logger.error("Failed to resend OTP email to %s: %s", email, send_message)
        return {
            "success": False,
            "error": "Could not send verification email. Please try again in a moment.",
            "auth_enabled": True,
        }

    return {
        "success": True,
        "otp_required": True,
        "email": email,
        "message": f"We sent a new verification code to {email}.",
        "auth_enabled": True,
    }


@router.post("/auth/login")
async def auth_login(body: dict):
    """Log in with username and password.

    Accepts: {"username": "...", "password": "..."}
    Returns a session token on success, or an error on failure.
    This endpoint is intentionally unauthenticated.
    """
    username = body.get("username", "")
    password = body.get("password", "")

    token = login(username, password)
    if token:
        return {
            "success": True,
            "token": token,
            "username": username,
            "auth_enabled": True,
        }

    return {
        "success": False,
        "error": "Invalid username or password.",
        "auth_enabled": True,
    }


@router.post("/auth/verify")
async def auth_verify(body: dict):
    """Check if a session token is still valid.

    Accepts: {"token": "..."}
    Used by the frontend on reload to verify the stored session.
    """
    token = body.get("token", "")
    if not is_auth_enabled():
        return {"valid": False, "auth_enabled": False}
    return {
        "valid": validate_token(token),
        "auth_enabled": True,
    }


@router.post("/auth/logout")
async def auth_logout(_key: str = Depends(require_api_key)):
    """Log out and invalidate the current session token.

    Requires a valid session token (the one to invalidate).
    After calling this, the token can no longer be used.
    """
    token = _key
    if token and logout_token(token):
        return {"success": True, "message": "Logged out successfully."}
    return {"success": True, "message": "Session already expired."}


@router.post("/auth/change-password")
async def auth_change_password(body: dict, _key: str = Depends(require_api_key)):
    """Change the authenticated user's password.

    Accepts: {"current_password": "...", "new_password": "..."}
    Requires authentication.
    """
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")
    
    if not current_password:
        return {"success": False, "error": "Current password is required."}
    
    if not new_password:
        return {"success": False, "error": "New password is required."}
    
    # Get username from token
    username = get_username_for_token(_key)
    if not username:
        return {"success": False, "error": "Invalid session."}
    
    success, message = change_password(username, current_password, new_password)
    
    if success:
        return {"success": True, "message": message}
    
    return {"success": False, "error": message}


@router.get("/target-intel")
async def target_intel(target: str, _key: str = Depends(require_api_key)):
    """Fetch target-specific web intelligence.
    
    Searches the web for information about the given target using
    DuckDuckGo's free Instant Answer API and filters local RSS news
    for relevant mentions.
    """
    try:
        target = sanitize_target(target)
    except InputValidationError as e:
        raise HTTPException(400, detail={"error": e.message, "detail": e.detail})

    target_type = AutoDetect.detect(target)
    web_results = []
    news_results = []
    related_info = {}

    async def search_duckduckgo():
        """Search DuckDuckGo Instant Answer API (free, no key)."""
        nonlocal web_results, related_info
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # DuckDuckGo Instant Answer API
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": target,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1,
                    },
                    headers={"User-Agent": "TRINETRA-OSINT/1.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText", "")
                    abstract_source = data.get("AbstractSource", "")
                    abstract_url = data.get("AbstractURL", "")
                    
                    if abstract:
                        web_results.append({
                            "title": f"Wikipedia / {abstract_source}" if abstract_source else "Summary",
                            "snippet": abstract[:500],
                            "url": abstract_url,
                            "source": abstract_source or "DuckDuckGo",
                            "type": "abstract",
                        })
                        related_info["abstract"] = abstract[:500]
                        related_info["source"] = abstract_source
                        related_info["url"] = abstract_url

                    # Related topics
                    related = data.get("RelatedTopics", [])
                    for topic in related[:8]:
                        if "Text" in topic and "FirstURL" in topic:
                            web_results.append({
                                "title": topic.get("Text", "").split(" - ")[0][:100],
                                "snippet": topic.get("Text", "")[:300],
                                "url": topic.get("FirstURL", ""),
                                "source": topic.get("Icon", {}).get("URL", "DuckDuckGo") or "DuckDuckGo",
                                "type": "related",
                            })
                        elif "Topics" in topic:
                            for sub in topic["Topics"][:4]:
                                if "Text" in sub and "FirstURL" in sub:
                                    web_results.append({
                                        "title": sub.get("Text", "").split(" - ")[0][:100],
                                        "snippet": sub.get("Text", "")[:300],
                                        "url": sub.get("FirstURL", ""),
                                        "source": "DuckDuckGo",
                                        "type": "related",
                                    })

                    # Results from the web
                    results = data.get("Results", [])
                    for r in results[:5]:
                        if "Text" in r and "FirstURL" in r:
                            web_results.append({
                                "title": r.get("Text", "").split(" - ")[0][:100],
                                "snippet": r.get("Text", "")[:300],
                                "url": r.get("FirstURL", ""),
                                "source": r.get("Source", "Web"),
                                "type": "result",
                            })

        except Exception as e:
            logger.debug("DuckDuckGo search failed for %s: %s", target, e)

    async def search_news():
        """Search local RSS news cache for target mentions."""
        nonlocal news_results
        try:
            from app.services.real_news_service import real_news_service
            headlines = real_news_service.get_latest(100)
            target_lower = target.lower()
            for item in headlines:
                text = (item.get("text", "") + " " + item.get("source", "")).lower()
                keywords = target_lower.split(".") if "." in target_lower else [target_lower]
                if any(kw in text for kw in keywords if len(kw) > 2):
                    news_results.append(item)
            # Limit to top 10 matches
            news_results[:] = news_results[:10]
        except Exception as e:
            logger.debug("News search failed for %s: %s", target, e)

    # Run both searches in parallel
    await asyncio.gather(search_duckduckgo(), search_news(), return_exceptions=True)

    detected_type = AutoDetect.detect_full(target) if target_type != "unknown" else {
        "target": target,
        "detected_type": "unknown",
        "confidence": 0,
    }

    return {
        "target": target,
        "target_type": target_type,
        "detected": detected_type,
        "web_results": web_results[:15],
        "news_mentions": news_results,
        "related_info": related_info,
        "total_web": len(web_results),
        "total_news": len(news_results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/search")
async def search(request: SearchRequest, _key: str = Depends(require_api_key)):
    """Run all applicable OSINT plugins against a target.

    Flat credit billing:
      - Every search costs a flat CREDITS_PER_SEARCH (10) credits,
        regardless of how many plugins match.
      - Credits are deducted BEFORE the scan.
      - The full amount is REFUNDED if the entire scan crashes or
        returns zero successful results.
    """
    from app.core.config import settings as app_settings
    from app.services.payment_service import CREDITS_PER_SEARCH

    username = get_username_for_token(_key)
    if not username:
        raise HTTPException(401, detail={"error": "Invalid session"})

    # Sanitize input
    try:
        target = sanitize_target(request.target)
    except InputValidationError as e:
        raise HTTPException(400, detail={"error": e.message, "detail": e.detail})

    # Validate target type
    is_valid, detected_type, validation_error = validate_target(target)
    if not is_valid and not request.type:
        raise HTTPException(400, detail={"error": validation_error})

    # Auto-detect type
    target_type = request.type or detected_type
    if target_type == "unknown":
        target_type = "domain"  # default fallback

    # ── Flat credit billing ─────────────────────────────────────────
    payment_configured = bool(app_settings.cashfree_app_id and app_settings.cashfree_secret_key)
    credits_used = 0
    credits_refunded = 0
    remaining = None

    if payment_configured:
        total_cost = CREDITS_PER_SEARCH

        user_credits = get_user_credits(username)
        if user_credits < total_cost:
            raise HTTPException(
                402,
                detail={
                    "error": "Insufficient credits",
                    "detail": f"Each search costs {total_cost} credits. You have {user_credits}.",
                    "credits": user_credits,
                    "credits_required": total_cost,
                },
            )

        # Deduct flat cost before running scan
        success, remaining = deduct_credits(username, total_cost)
        if not success:
            raise HTTPException(402, detail={"error": "Failed to deduct credits. Please try again."})
        credits_used = total_cost

    # ── Run plugins ──────────────────────────────────────────────────
    try:
        results = await orchestrator.run_all(target, target_type)
    except Exception as e:
        logger.error("Scan failed for target=%s: %s", target, e)
        if payment_configured:
            add_credits(username, credits_used)
            remaining = get_user_credits(username)
        raise HTTPException(500, detail={"error": "Scan failed. Credits have been refunded."})

    # ── Refund if the entire scan failed (zero successful results) ───
    if payment_configured and credits_used > 0:
        completed_count = sum(1 for r in results if r.get("status") == "completed")
        if completed_count == 0:
            refund_ok = add_credits(username, credits_used)
            if not refund_ok:
                logger.error(
                    "Failed to refund %d credits for user=%s target=%s",
                    credits_used, username, target,
                )
            credits_refunded = credits_used
            remaining = get_user_credits(username)
            logger.info(
                "Refunded %d credits — scan produced no successful results (target=%s user=%s)",
                credits_used, target, username,
            )

    return SearchResponse(
        target=target,
        type=target_type,
        timestamp=datetime.now(timezone.utc),
        total_plugins=len(results),
        completed_plugins=sum(1 for r in results if r.get("status") == "completed"),
        results=results,
        credits_used=credits_used if payment_configured else None,
        credits_refunded=credits_refunded if payment_configured else None,
        credits_remaining=remaining,
    )


@router.get("/search/{target}")
async def search_get(target: str, _key: str = Depends(require_api_key)):
    """GET version of search for simple lookups.

    Same flat credit billing as POST /search.
    """
    from app.core.config import settings as app_settings
    from app.services.payment_service import CREDITS_PER_SEARCH

    username = get_username_for_token(_key)
    if not username:
        raise HTTPException(401, detail={"error": "Invalid session"})

    # Sanitize input
    try:
        target = sanitize_target(target)
    except InputValidationError as e:
        raise HTTPException(400, detail={"error": e.message, "detail": e.detail})

    target_type = AutoDetect.detect(target)
    if target_type == "unknown":
        target_type = "domain"

    # Flat credit billing
    payment_configured = bool(app_settings.cashfree_app_id and app_settings.cashfree_secret_key)
    credits_used = 0
    credits_refunded = 0
    remaining = None

    if payment_configured:
        total_cost = CREDITS_PER_SEARCH

        user_credits = get_user_credits(username)
        if user_credits < total_cost:
            raise HTTPException(
                402,
                detail={
                    "error": "Insufficient credits",
                    "detail": f"Each search costs {total_cost} credits. You have {user_credits}.",
                    "credits": user_credits,
                    "credits_required": total_cost,
                },
            )

        success, remaining = deduct_credits(username, total_cost)
        if not success:
            raise HTTPException(402, detail={"error": "Failed to deduct credits. Please try again."})
        credits_used = total_cost

    try:
        results = await orchestrator.run_all(target, target_type)
    except Exception as e:
        logger.error("Scan failed for target=%s: %s", target, e)
        if payment_configured and credits_used > 0:
            add_credits(username, credits_used)
            remaining = get_user_credits(username)
        raise HTTPException(500, detail={"error": "Scan failed. Credits have been refunded."})

    # Refund if the entire scan failed (zero successful results)
    if payment_configured and credits_used > 0:
        completed_count = sum(1 for r in results if r.get("status") == "completed")
        if completed_count == 0:
            refund_ok = add_credits(username, credits_used)
            if not refund_ok:
                logger.error("Failed to refund %d credits for user=%s target=%s", credits_used, username, target)
            credits_refunded = credits_used
            remaining = get_user_credits(username)

    return SearchResponse(
        target=target,
        type=target_type,
        timestamp=datetime.now(timezone.utc),
        total_plugins=len(results),
        completed_plugins=sum(1 for r in results if r.get("status") == "completed"),
        results=results,
        credits_used=credits_used if payment_configured else None,
        credits_refunded=credits_refunded if payment_configured else None,
        credits_remaining=remaining,
    )


@router.get("/detect")
async def detect_target(target: str, _key: str = Depends(require_api_key)):
    """Auto-detect what type of target this is."""
    try:
        target = sanitize_target(target)
    except InputValidationError as e:
        raise HTTPException(400, detail={"error": e.message, "detail": e.detail})
    return AutoDetect.detect_full(target)


@router.get("/plugins")
async def list_plugins(_key: str = Depends(require_api_key)):
    """List all available OSINT plugins with their credit costs."""
    from app.plugins.registry import plugin_registry
    return {
        "total": len(plugin_registry.plugins),
        "plugins": [
            {
                "id": p.plugin_id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "input_types": p.input_types,
                "credit_cost": p.credit_cost,
            }
            for p in plugin_registry.plugins
        ],
    }