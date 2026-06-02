"""Reply detection: scan Mail.app for replies to our outreach, classify via LLM.

Scans inbox of each sending account for replies (emails that contain "Re:" or
reference our sent subjects). Classifies each reply into:
  - interested: wants call/demo/more info
  - ooo: out of office, often with redirect contact
  - unsubscribe: wants to stop receiving emails
  - not_relevant: not interested, wrong person, etc.
  - other: anything else

Usage:
    results = await scan_replies(days=1)
    replies = await get_replies(reply_type="interested")
    stats = await reply_stats()
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from llm_email.applescript import run_osascript
from llm_email.logger import log
from llm_email.mailer import list_accounts
from llm_email.models import EmailReply, SentEmail


class ReplyClassification(BaseModel):
    reply_type: Literal["interested", "ooo", "unsubscribe", "not_relevant", "other"] = Field(
        description="interested=wants call/demo/more info, ooo=out of office auto-reply, "
        "unsubscribe=wants to stop, not_relevant=not interested/wrong person, other=anything else"
    )
    summary: str = Field(
        description="1 sentence summary of the reply, e.g. 'Wants a 15-min call next week' or "
        "'OOO until April 13, redirect to john@fund.com'"
    )
    redirect_email: str = Field(
        default="",
        description="If OOO with redirect, the email to contact instead. Empty if none."
    )


async def _get_sent_subjects() -> set[str]:
    """Get subjects of emails we sent (to match replies)."""
    sent = await SentEmail.filter(status="ok", action="send").values_list("subject", flat=True)
    # Normalize: lowercase, strip "Re: " prefix
    subjects = set()
    for s in sent:
        if s:
            subjects.add(s.lower().strip())
    return subjects


async def _fetch_reply_candidates(days: int = 1) -> list[dict]:
    """Scan inbox of each Mail.app account for potential replies."""
    result = await list_accounts()
    if not result.ok:
        log.error("Cannot list accounts for reply scan: %s", result.error)
        return []

    accounts = [{"email": a.email, "name": a.name} for a in result.accounts]
    all_replies: list[dict] = []

    for acc in accounts:
        email = acc.get("email", "")
        if not email:
            continue

        # Fetch recent non-bounce, non-system emails (potential replies)
        script = f'''tell application "Mail"
try
set acct to account "{email}"
set mb to inbox of acct
set cutoffDate to (current date) - ({days} * days)
set msgs to (messages of mb whose date received > cutoffDate and sender does not contain "mailer-daemon" and sender does not contain "postmaster" and sender does not contain "noreply" and sender does not contain "no-reply")
set result to ""
set msgCount to 0
repeat with msg in msgs
if msgCount >= 50 then exit repeat
set fromAddr to sender of msg
set msgSubj to subject of msg
set msgBody to content of msg
set result to result & fromAddr & "|||" & msgSubj & "|||" & msgBody & "###SEP###"
set msgCount to msgCount + 1
end repeat
return result
on error
return ""
end try
end tell'''

        ok, output = run_osascript(script, timeout=30)
        if not ok or not output.strip():
            continue

        for entry in output.strip().split("###SEP###"):
            parts = entry.strip().split("|||")
            if len(parts) >= 3:
                sender = parts[0].strip()
                # Skip our own accounts
                if email.lower() in sender.lower():
                    continue
                all_replies.append({
                    "from": sender,
                    "subject": parts[1].strip(),
                    "body": parts[2].strip()[:3000],
                    "to_account": email,
                })

    log.info("Reply scan: found %d candidates across %d accounts", len(all_replies), len(accounts))
    return all_replies


def _extract_email_from_sender(sender: str) -> str:
    """Extract email from sender string like 'Name <email@x.com>'."""
    match = re.search(r"<([^>]+@[^>]+)>", sender)
    if match:
        return match.group(1).lower()
    if "@" in sender:
        return sender.strip().lower()
    return ""


def _extract_name_from_sender(sender: str) -> str:
    """Extract name from sender string."""
    match = re.match(r"^([^<]+)<", sender)
    if match:
        return match.group(1).strip()
    return ""


def _is_reply_to_our_outreach(subject: str, sent_subjects: set[str]) -> bool:
    """Check if this email is a reply to something we sent."""
    subj = subject.lower().strip()
    # Remove "Re: ", "Fwd: " etc.
    clean = re.sub(r"^(re|fwd|fw):\s*", "", subj, flags=re.I).strip()
    return clean in sent_subjects


def _classify_reply_regex(msg: dict) -> ReplyClassification:
    """Fast regex classification (fallback)."""
    text = (msg.get("subject", "") + " " + msg.get("body", "")).lower()

    # OOO patterns
    ooo_patterns = ["out of office", "out of the office", "on vacation", "on leave",
                    "maternity leave", "paternity leave", "auto-reply", "automatic reply",
                    "autoresponder", "i am currently out", "i will be out", "returning"]
    if any(p in text for p in ooo_patterns):
        redirect = ""
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", msg.get("body", ""))
        from_email = _extract_email_from_sender(msg.get("from", ""))
        redirects = [e for e in emails if e.lower() != from_email]
        if redirects:
            redirect = redirects[0]
        return ReplyClassification(
            reply_type="ooo",
            summary=f"Out of office. {'Redirect to ' + redirect if redirect else 'No redirect.'}",
            redirect_email=redirect,
        )

    # Unsubscribe
    unsub_patterns = ["unsubscribe", "remove me", "stop emailing", "opt out",
                      "don't contact", "do not contact", "no longer interested"]
    if any(p in text for p in unsub_patterns):
        return ReplyClassification(
            reply_type="unsubscribe",
            summary="Wants to unsubscribe.",
            redirect_email="",
        )

    # Not relevant
    not_relevant_patterns = ["not investing", "not the right fit", "not a fit",
                             "no longer with", "left the firm", "moved on", "wrong person",
                             "not our focus", "pass on this"]
    if any(p in text for p in not_relevant_patterns):
        redirect = ""
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", msg.get("body", ""))
        from_email = _extract_email_from_sender(msg.get("from", ""))
        redirects = [e for e in emails if e.lower() != from_email]
        if redirects:
            redirect = redirects[0]
        return ReplyClassification(
            reply_type="not_relevant",
            summary=f"Not relevant/moved on. {'Redirect to ' + redirect if redirect else ''}".strip(),
            redirect_email=redirect,
        )

    # Interested (positive signals)
    interested_patterns = ["let's chat", "happy to", "would love to", "schedule a call",
                          "set up a meeting", "interested", "sounds interesting", "tell me more",
                          "send me more", "pitch deck", "let's connect", "calendar",
                          "free to talk", "hop on a call"]
    if any(p in text for p in interested_patterns):
        return ReplyClassification(
            reply_type="interested",
            summary="Shows interest / wants to connect.",
            redirect_email="",
        )

    return ReplyClassification(
        reply_type="other",
        summary="Unclassified reply.",
        redirect_email="",
    )


async def _classify_reply_llm(msg: dict, client=None) -> ReplyClassification:
    """Classify reply using LLM for better accuracy."""
    if client is None:
        try:
            from sdkrouter import SDKRouter
            client = SDKRouter(api_key="test-api-key")
        except ImportError:
            return _classify_reply_regex(msg)

    body_preview = msg["body"][:2000]
    prompt = f"""Classify this email reply to our outreach.

From: {msg['from']}
Subject: {msg['subject']}
Body:
{body_preview}

Classify as: interested (wants call/demo), ooo (out of office), unsubscribe, not_relevant (pass/wrong person), other.
If OOO or redirect, extract the alternative contact email."""

    try:
        result = client.parse(
            model="openai/gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "Classify email replies to sales outreach. Be accurate and concise."},
                {"role": "user", "content": prompt},
            ],
            response_format=ReplyClassification,
            temperature=0,
            max_tokens=300,
        )
        return result.choices[0].message.parsed  # type: ignore[return-value]
    except Exception as e:
        log.error("LLM reply classification failed: %s", e)
        return _classify_reply_regex(msg)


async def scan_replies(days: int = 1, use_llm: bool = True) -> dict:
    """Scan Mail.app for replies, classify, and store in DB.

    Returns: {"ok": bool, "new_replies": int, "by_type": {...}, "details": [...]}
    """
    log.info("Scanning for replies (last %d days, llm=%s)", days, use_llm)

    # Get our sent subjects to match replies
    sent_subjects = await _get_sent_subjects()
    if not sent_subjects:
        return {"ok": True, "new_replies": 0, "by_type": {}, "details": []}

    # Get already-known reply emails to avoid duplicates
    known = set()
    for r in await EmailReply.all().values_list("from_email", "subject"):
        known.add((r[0].lower(), r[1].lower()))

    # Fetch candidates
    candidates = await _fetch_reply_candidates(days=days)

    # Filter: only replies to our outreach
    replies_to_us = [
        msg for msg in candidates
        if _is_reply_to_our_outreach(msg["subject"], sent_subjects)
    ]
    log.info("Filtered %d replies to our outreach (from %d candidates)", len(replies_to_us), len(candidates))

    # LLM client
    llm_client = None
    if use_llm:
        try:
            from sdkrouter import SDKRouter
            llm_client = SDKRouter(api_key="test-api-key")
        except ImportError:
            log.warning("sdkrouter not available, falling back to regex")

    new_replies = []
    by_type: dict[str, int] = {}

    for msg in replies_to_us:
        from_email = _extract_email_from_sender(msg["from"])
        from_name = _extract_name_from_sender(msg["from"])
        subject = msg.get("subject", "")

        # Skip if already processed
        if (from_email, subject.lower()) in known:
            continue

        # Classify
        if use_llm and llm_client:
            classification = await _classify_reply_llm(msg, client=llm_client)
        else:
            classification = _classify_reply_regex(msg)

        # Save to DB
        await EmailReply.create(
            from_email=from_email,
            from_name=from_name,
            to_account=msg.get("to_account", ""),
            subject=subject,
            body=msg.get("body", "")[:5000],
            reply_type=classification.reply_type,
            summary=classification.summary,
            redirect_email=classification.redirect_email,
            handled=False,
        )

        known.add((from_email, subject.lower()))
        by_type[classification.reply_type] = by_type.get(classification.reply_type, 0) + 1

        detail = {
            "from": from_email,
            "name": from_name,
            "type": classification.reply_type,
            "summary": classification.summary,
        }
        if classification.redirect_email:
            detail["redirect"] = classification.redirect_email

        new_replies.append(detail)
        log.info("Reply: %s (%s) — %s", from_email, classification.reply_type, classification.summary)

    return {
        "ok": True,
        "new_replies": len(new_replies),
        "by_type": by_type,
        "details": new_replies,
    }


async def get_replies(
    reply_type: str | None = None,
    handled: bool | None = None,
    limit: int = 100,
) -> list[dict]:
    """Get replies from DB with optional filters."""
    qs = EmailReply.all()
    if reply_type:
        qs = qs.filter(reply_type=reply_type)
    if handled is not None:
        qs = qs.filter(handled=handled)

    replies = await qs.order_by("-detected_at").limit(limit)
    return [
        {
            "id": r.id,
            "from": r.from_email,
            "name": r.from_name,
            "to_account": r.to_account,
            "subject": r.subject,
            "type": r.reply_type,
            "summary": r.summary,
            "redirect": r.redirect_email,
            "handled": r.handled,
            "detected_at": r.detected_at.isoformat() if r.detected_at else "",
        }
        for r in replies
    ]


async def mark_handled(reply_id: int) -> bool:
    """Mark a reply as handled."""
    updated = await EmailReply.filter(id=reply_id).update(handled=True)
    return updated > 0


async def reply_stats() -> dict:
    """Reply statistics by type."""
    total = await EmailReply.all().count()
    interested = await EmailReply.filter(reply_type="interested").count()
    ooo = await EmailReply.filter(reply_type="ooo").count()
    unsubscribe = await EmailReply.filter(reply_type="unsubscribe").count()
    not_relevant = await EmailReply.filter(reply_type="not_relevant").count()
    other = await EmailReply.filter(reply_type="other").count()
    unhandled = await EmailReply.filter(handled=False).count()

    return {
        "ok": True,
        "total": total,
        "unhandled": unhandled,
        "interested": interested,
        "ooo": ooo,
        "unsubscribe": unsubscribe,
        "not_relevant": not_relevant,
        "other": other,
    }
