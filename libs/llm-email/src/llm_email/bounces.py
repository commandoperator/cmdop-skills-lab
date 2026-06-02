"""Bounce detection: scan Mail.app for bounce messages, classify, and store in DB.

Usage:
    results = await scan_bounces(days=1)
    bounced = await get_bounced_emails()
    is_bad = await is_bounced("user@example.com")
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from llm_email.applescript import run_osascript
from llm_email.logger import log
from llm_email.mailer import list_accounts
from llm_email.models import BounceEmail


class BounceClassification(BaseModel):
    is_bounce: bool = Field(description="True if this is a bounce/undeliverable notification")
    bounce_type: Literal["hard", "soft", "unknown"] = Field(
        description="hard=permanent (mailbox not found, domain gone), soft=temporary (full, server down)"
    )
    reason: str = Field(description="Short reason: 'mailbox not found', 'domain expired', 'quota exceeded'")
    original_recipient: str = Field(description="The email address that bounced")


async def _fetch_bounce_candidates(days: int = 1) -> list[dict]:
    """Scan inbox of each Mail.app account for bounce messages.

    Scans per-account with short timeout to avoid AppleScript hanging
    on large mailboxes.
    """
    # Discover accounts
    result = await list_accounts()
    if not result.ok:
        log.error("Cannot list accounts for bounce scan: %s", result.error)
        return []

    accounts = [{"email": a.email, "name": a.name} for a in result.accounts]
    all_messages: list[dict] = []

    for acc in accounts:
        email = acc.get("email", "")
        if not email:
            continue

        script = f'''tell application "Mail"
try
set acct to account "{email}"
set mb to inbox of acct
set cutoffDate to (current date) - ({days} * days)
set msgs to (messages of mb whose date received > cutoffDate and (sender contains "mailer-daemon" or sender contains "postmaster" or subject contains "Undelivered" or subject contains "Delivery Status" or subject contains "Undeliverable" or subject contains "Address not found"))
set result to ""
repeat with msg in msgs
set result to result & (subject of msg) & "|||" & (sender of msg) & "|||" & (content of msg) & "###SEP###"
end repeat
return result
on error
return ""
end try
end tell'''

        ok, output = run_osascript(script, timeout=20)
        if not ok or not output.strip():
            continue

        for entry in output.strip().split("###SEP###"):
            parts = entry.strip().split("|||")
            if len(parts) >= 3:
                all_messages.append({
                    "subject": parts[0].strip(),
                    "sender": parts[1].strip(),
                    "body": parts[2].strip()[:3000],
                    "account": email,
                })

    log.info("Bounce scan: found %d candidates across %d accounts", len(all_messages), len(accounts))
    return all_messages


def _extract_bounced_from_body(body: str) -> set[str]:
    """Extract bounced email addresses from a bounce message body using regex."""
    bounced: set[str] = set()

    # RFC Final-Recipient header
    for m in re.findall(r"Final-Recipient:\s*rfc822;\s*(\S+@\S+)", body):
        bounced.add(m.strip().lower().rstrip("."))

    # Russian Gmail: "адрес X не найден"
    for m in re.findall(r"адрес\s+(\S+@\S+)\s+не найден", body):
        bounced.add(m.strip().lower().rstrip("."))

    # English patterns
    for m in re.findall(r"address\s+(\S+@\S+)\s+(?:not found|rejected|does not exist)", body, re.I):
        bounced.add(m.strip().lower().rstrip("."))

    for m in re.findall(r"(\S+@\S+)\s+(?:could not be delivered|was not delivered)", body, re.I):
        bounced.add(m.strip().lower().rstrip("."))

    # Filter system addresses
    return {
        e for e in bounced
        if "mailer-daemon" not in e
        and "google" not in e
        and "postmaster" not in e
    }


async def _classify_bounce_llm(msg: dict, client=None) -> BounceClassification | None:
    """Classify a bounce message using SDKRouter LLM (optional)."""
    if client is None:
        try:
            from sdkrouter import SDKRouter
            client = SDKRouter(api_key="test-api-key")
        except ImportError:
            log.warning("sdkrouter not installed, using regex-only bounce detection")
            return _classify_bounce_regex(msg)

    body_preview = msg["body"][:2000]
    prompt = f"""Analyze this email. Is it a bounce/undeliverable notification?

Subject: {msg['subject']}
From: {msg['sender']}
Body (truncated):
{body_preview}

If it IS a bounce, extract the original recipient email and classify the type."""

    try:
        result = client.parse(
            model="openai/gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "Classify email bounce notifications. Be accurate."},
                {"role": "user", "content": prompt},
            ],
            response_format=BounceClassification,
            temperature=0,
            max_tokens=300,
        )
        return result.choices[0].message.parsed  # type: ignore[return-value]
    except Exception as e:
        log.error("LLM bounce classification failed: %s", e)
        return _classify_bounce_regex(msg)


def _classify_bounce_regex(msg: dict) -> BounceClassification | None:
    """Fallback: regex-based bounce detection (no LLM needed)."""
    text = (msg.get("subject", "") + " " + msg.get("body", "")).lower()

    hard_patterns = ["user unknown", "mailbox not found", "no such user", "does not exist",
                     "invalid recipient", "address rejected", "account disabled", "не найден"]
    soft_patterns = ["mailbox full", "quota exceeded", "try again later", "temporarily",
                     "connection timed out", "service unavailable"]

    is_bounce = any(p in text for p in hard_patterns + soft_patterns + [
        "undelivered", "delivery failed", "undeliverable", "returned mail"])

    if not is_bounce:
        return None

    # Extract bounced email from body
    body_emails = _extract_bounced_from_body(msg.get("body", ""))
    if not body_emails:
        return None

    bounce_type: Literal["hard", "soft", "unknown"] = "unknown"
    reason = "bounce detected"

    for p in hard_patterns:
        if p in text:
            bounce_type = "hard"
            reason = p
            break
    for p in soft_patterns:
        if p in text:
            bounce_type = "soft"
            reason = p
            break

    return BounceClassification(
        is_bounce=True,
        bounce_type=bounce_type,
        reason=reason,
        original_recipient=next(iter(body_emails)),
    )


async def scan_bounces(days: int = 1, use_llm: bool = False) -> dict:
    """Scan Mail.app inboxes for bounces, classify, and store in DB.

    Returns: {"ok": bool, "new_bounces": int, "total_bounces": int, "details": [...]}
    """
    log.info("Scanning for bounces (last %d days, llm=%s)", days, use_llm)

    # Get known bounced emails
    known = {b.email.lower() for b in await BounceEmail.all()}

    # Fetch candidates from Mail.app inboxes
    candidates = await _fetch_bounce_candidates(days=days)

    if not candidates:
        return {"ok": True, "new_bounces": 0, "total_bounces": len(known), "details": []}

    # Optionally init LLM client once
    llm_client = None
    if use_llm:
        try:
            from sdkrouter import SDKRouter
            llm_client = SDKRouter(api_key="test-api-key")
        except ImportError:
            log.warning("sdkrouter not available, falling back to regex")

    new_bounces = []
    for msg in candidates:
        # Try regex first (fast) — extract all bounced emails from body
        body_bounces = _extract_bounced_from_body(msg.get("body", ""))

        for email in body_bounces:
            if email in known:
                continue

            # Determine bounce type
            if use_llm and llm_client:
                result = await _classify_bounce_llm(msg, client=llm_client)
                if result and result.is_bounce:
                    btype = result.bounce_type
                    reason = result.reason
                else:
                    btype = "unknown"
                    reason = "bounce detected"
            else:
                regex_result = _classify_bounce_regex(msg)
                btype = regex_result.bounce_type if regex_result else "unknown"
                reason = regex_result.reason if regex_result else "bounce detected"

            await BounceEmail.create(
                email=email,
                bounce_type=btype,
                reason=reason,
                source_subject=msg.get("subject", "")[:500],
            )
            known.add(email)
            new_bounces.append({
                "email": email,
                "type": btype,
                "reason": reason,
            })
            log.info("New bounce: %s (%s) — %s", email, btype, reason)

    total = await BounceEmail.all().count()
    return {
        "ok": True,
        "new_bounces": len(new_bounces),
        "total_bounces": total,
        "details": new_bounces,
    }


async def get_bounced_emails() -> list[dict]:
    """Get all bounced emails from DB."""
    bounces = await BounceEmail.all().order_by("-detected_at")
    return [
        {
            "email": b.email,
            "type": b.bounce_type,
            "reason": b.reason,
            "detected_at": b.detected_at.isoformat() if b.detected_at else "",
        }
        for b in bounces
    ]


async def is_bounced(email: str) -> bool:
    """Check if an email address is in the bounce list."""
    return await BounceEmail.filter(email=email.lower()).exists()


async def bounce_stats() -> dict:
    """Bounce statistics."""
    total = await BounceEmail.all().count()
    hard = await BounceEmail.filter(bounce_type="hard").count()
    soft = await BounceEmail.filter(bounce_type="soft").count()
    unknown = await BounceEmail.filter(bounce_type="unknown").count()
    return {
        "ok": True,
        "total": total,
        "hard": hard,
        "soft": soft,
        "unknown": unknown,
    }
