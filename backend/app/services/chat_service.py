"""
TRINETRA — AI Chatbot Service

Lightweight wrapper around the Google Gemini API. Acts as an in-app
SOC-analyst assistant: explains the dashboard, and when the frontend
passes along current scan/target data as `context`, can interpret
findings and generate structured investigation reports.
"""

import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("trinetra.chat")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Plain chat replies are quick. Report generation reads a large context
# block and writes a long, structured, table-heavy response — that
# routinely takes well over 45s, especially on a cold connection to the
# API. Give report requests a much longer budget so they don't time out
# on the first try.
CHAT_TIMEOUT_SECONDS = 45
REPORT_TIMEOUT_SECONDS = 120

# Both timeouts and Gemini 503s ("model overloaded") are transient —
# retry once before giving up.
MAX_ATTEMPTS = 2

BASE_SYSTEM_PROMPT = (
    "You are the TRINETRA Assistant, an in-app SOC-analyst-style helper for the "
    "TRINETRA OSINT Dashboard. TRINETRA lets users search a target (domain, email, "
    "IP, username, phone) and runs OSINT plugins (infrastructure, threat, advanced "
    "categories) against it, shows results on a map/graph, and supports 'Watches' "
    "that re-check a target periodically and alert on changes. Be concise, "
    "friendly, and practical. Help users understand features, interpret results, "
    "and navigate the dashboard. If asked something unrelated, answer briefly and "
    "steer back to being useful."
)

REPORT_INSTRUCTIONS = (
    "\n\nThe user's current investigation data is provided below (live OSINT scan "
    "results they are looking at right now). Use it to answer questions about the "
    "target, and if the user asks for a report, summary, or analysis, produce a "
    "comprehensive, professional SOC-analyst investigation report in markdown.\n\n"
    "STRUCTURE (use exactly these headings, in this order, as '## Heading'):\n"
    "## Executive Summary\n"
    "## Target Overview\n"
    "## Key Findings\n"
    "## Risk Assessment\n"
    "## Recommended Actions\n\n"
    "'Executive Summary' must be 2-4 sentences only: overall risk level, the single "
    "biggest concern found (if any), and a one-line bottom-line verdict. No bullets, "
    "no headings inside it — plain prose only.\n\n"
    "Under 'Key Findings', add one '### ' subsection PER PLUGIN CATEGORY that has data "
    "(e.g. '### Infrastructure Analysis', '### Threat Analysis', '### Advanced / OSINT Findings'), "
    "and inside each subsection cover EVERY plugin result present in the data below in full "
    "detail — do not summarize away specific values. Whenever present in the data, always include: "
    "full domain/WHOIS records (registrar, creation/update/expiry dates, name servers), all resolved "
    "IP addresses and ASN/hosting info, every subdomain found (not just a sample) with its discovery "
    "SOURCE listed (not a redundant 'found/not found' status column — every listed subdomain was by "
    "definition found), DNS records (MX, SPF, DKIM, TXT), SSL/TLS certificate details, open ports and "
    "services, security headers, breach/leak counts and sources, CVEs, and any risk/exposure scores. "
    "When stating a count (e.g. 'N headers missing'), always name ALL N items — never trail off with "
    "'etc.' or 'and others'. Use markdown tables for lists of records (subdomains, ports, DNS records) "
    "instead of prose where possible. Base every claim only on the data given — do not invent findings "
    "that aren't present. If a plugin reported no data or an error, say so briefly instead of omitting it.\n\n"
    "=== CURRENT INVESTIGATION DATA ===\n{context}\n=== END DATA ==="
)


class ChatService:
    async def get_reply(
        self,
        message: str,
        history: list[dict] | None = None,
        context: str | None = None,
    ) -> str:
        if not settings.gemini_api_key:
            return (
                "Chatbot isn't configured yet — set GEMINI_API_KEY in your "
                "backend .env file to enable AI responses."
            )

        is_report_request = bool(context)

        system_prompt = BASE_SYSTEM_PROMPT
        if context:
            system_prompt += REPORT_INSTRUCTIONS.format(context=context[:24000])

        contents = []
        for turn in (history or [])[-10:]:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": turn.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {
            "contents": contents,
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"maxOutputTokens": 8192},
        }
        url = GEMINI_URL.format(model=settings.gemini_model)
        timeout = REPORT_TIMEOUT_SECONDS if is_report_request else CHAT_TIMEOUT_SECONDS

        last_error: Exception | None = None

        for attempt in range(MAX_ATTEMPTS):
            is_last_attempt = attempt == MAX_ATTEMPTS - 1

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        url,
                        params={"key": settings.gemini_api_key},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return "Sorry, I didn't get a response — try again."
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    return text or "Sorry, I didn't get a response — try again."

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "Gemini request timed out (attempt %d/%d, timeout=%ds, report=%s)",
                    attempt + 1, MAX_ATTEMPTS, timeout, is_report_request,
                )
                if is_last_attempt:
                    if is_report_request:
                        return (
                            "Generating a full report is taking longer than expected — "
                            "this can happen with large scans. Please try again; it "
                            "usually completes on the next attempt."
                        )
                    return "Chatbot service is temporarily unavailable. Please try again shortly."
                continue  # retry once

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Gemini HTTP error %s (attempt %d/%d): %s",
                    e.response.status_code, attempt + 1, MAX_ATTEMPTS, e.response.text[:300],
                )
                # 503 = "model overloaded" — Google's own transient error, worth retrying.
                if e.response.status_code == 503 and not is_last_attempt:
                    last_error = e
                    continue
                if e.response.status_code == 503:
                    return (
                        "The AI model is under heavy load on Google's side right now. "
                        "This usually clears up within a few seconds — please try again."
                    )
                detail = e.response.text[:300]
                return f"Chatbot service error ({e.response.status_code}): {detail}"

            except Exception as e:
                logger.error("Gemini request failed: %s", e, exc_info=True)
                return "Chatbot service is temporarily unavailable. Please try again shortly."

        # Should be unreachable (loop always returns above), but keep a safe fallback.
        logger.error("Gemini request exhausted all retries: %s", last_error)
        return "Chatbot service is temporarily unavailable. Please try again shortly."


chat_service = ChatService()