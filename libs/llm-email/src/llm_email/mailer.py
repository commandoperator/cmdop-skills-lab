"""Business logic for sending emails via macOS Mail.app."""

from datetime import datetime, timedelta, timezone

from tortoise.functions import Count

from llm_email.applescript import escape_applescript, run_osascript, split_addrs
from llm_email.config import (
    OSASCRIPT_ACCOUNTS_TIMEOUT, OSASCRIPT_HEALTH_TIMEOUT,
    DEDUP_HOURS, STATUS_DEFAULT_LIMIT, STATS_TOP_RECIPIENTS,
)
from llm_email.logger import log
from llm_email.models import SentEmail


async def send_email(
    to: str,
    subject: str,
    body: str,
    from_account: str = "",
    cc: str = "",
    bcc: str = "",
    draft_only: bool = False,
) -> dict:
    """Compose and send (or draft) an email via Mail.app. Returns result dict."""
    es = escape_applescript
    visible = "true" if draft_only else "false"

    lines = ['tell application "Mail"']

    if from_account:
        lines.append(f'    set senderAccount to account "{es(from_account)}"')
        lines.append('    set senderAddr to email addresses of senderAccount')
        lines.append(
            f'    set newMessage to make new outgoing message with properties '
            f'{{subject:"{es(subject)}", content:"{es(body)}", '
            f'visible:{visible}, sender:item 1 of senderAddr}}'
        )
    else:
        lines.append(
            f'    set newMessage to make new outgoing message with properties '
            f'{{subject:"{es(subject)}", content:"{es(body)}", visible:{visible}}}'
        )

    lines.append('    tell newMessage')

    for addr in split_addrs(to):
        lines.append(
            f'        make new to recipient at end of to recipients '
            f'with properties {{address:"{es(addr)}"}}'
        )
    for addr in split_addrs(cc):
        lines.append(
            f'        make new cc recipient at end of cc recipients '
            f'with properties {{address:"{es(addr)}"}}'
        )
    for addr in split_addrs(bcc):
        lines.append(
            f'        make new bcc recipient at end of bcc recipients '
            f'with properties {{address:"{es(addr)}"}}'
        )

    lines.append('    end tell')
    if not draft_only:
        lines.append('    send newMessage')
    lines.append('end tell')

    script = "\n".join(lines)
    action = "draft" if draft_only else "send"
    log.info("%s email to=%s subject=%r", action, to, subject)
    ok, output = run_osascript(script)

    status = "ok" if ok else "error"
    if not ok:
        log.error("%s failed: %s", action, output)

    await SentEmail.create(
        to_addr=to,
        cc_addr=cc,
        bcc_addr=bcc,
        subject=subject,
        body=body,
        from_account=from_account or "default",
        action=action,
        status=status,
        error_message="" if ok else output,
    )

    if ok:
        return {"ok": True, "action": action, "to": to, "subject": subject}
    return {"ok": False, "action": action, "error": output}


async def list_accounts() -> dict:
    """List available Mail.app email accounts."""
    script = '''
tell application "Mail"
    set accountList to {}
    repeat with acc in accounts
        try
            set accName to name of acc
            set accEmail to email addresses of acc
            if (count of accEmail) > 0 then
                set end of accountList to (accName & "|" & (item 1 of accEmail as string))
            end if
        end try
    end repeat
    set AppleScript's text item delimiters to "\\n"
    return accountList as string
end tell
'''
    ok, output = run_osascript(script, timeout=OSASCRIPT_ACCOUNTS_TIMEOUT)
    if not ok:
        return {"ok": False, "error": output}

    accounts = []
    for i, line in enumerate(output.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            name, email = line.split("|", 1)
            accounts.append({"name": name.strip(), "email": email.strip(), "default": i == 0})
        elif "@" in line:
            accounts.append({"email": line, "default": i == 0})

    return {"ok": True, "accounts": accounts}


def check_health() -> dict:
    """Check if Mail.app is running and accessible."""
    script = 'tell application "System Events" to return exists application process "Mail"'
    ok, output = run_osascript(script, timeout=OSASCRIPT_HEALTH_TIMEOUT)
    if not ok:
        return {"ok": False, "error": output}

    running = output.strip() == "true"
    return {"ok": True, "mail_running": running}


async def show_status(limit: int = STATUS_DEFAULT_LIMIT) -> dict:
    """Show recent sent email log from DB."""
    total = await SentEmail.all().count()
    recent_qs = await SentEmail.all().order_by("-sent_at").limit(limit).values(
        "to_addr", "subject", "from_account", "action", "status", "sent_at",
    )
    recent = [
        {
            "to": r["to_addr"],
            "subject": r["subject"],
            "from": r["from_account"],
            "action": r["action"],
            "status": r["status"],
            "sent_at": r["sent_at"].isoformat() if r["sent_at"] else "",
        }
        for r in recent_qs
    ]
    return {"ok": True, "total_sent": total, "recent": recent}


async def show_stats() -> dict:
    """Extended statistics: daily/weekly/total counts, top recipients."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    total = await SentEmail.filter(status="ok").count()
    today_count = await SentEmail.filter(status="ok", sent_at__gte=day_ago).count()
    week_count = await SentEmail.filter(status="ok", sent_at__gte=week_ago).count()
    error_count = await SentEmail.filter(status="error").count()

    top_recipients = (
        await SentEmail.filter(status="ok")
        .annotate(cnt=Count("id"))
        .group_by("to_addr")
        .order_by("-cnt")
        .limit(STATS_TOP_RECIPIENTS)
        .values("to_addr", "cnt")
    )

    return {
        "ok": True,
        "total_sent": total,
        "sent_today": today_count,
        "sent_this_week": week_count,
        "total_errors": error_count,
        "top_recipients": [
            {"to": r["to_addr"], "count": r["cnt"]} for r in top_recipients
        ],
    }


async def check_duplicate(to: str, subject: str, hours: int = DEDUP_HOURS) -> bool:
    """Check if an email with same recipient+subject was sent recently."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return await SentEmail.filter(
        to_addr=to,
        subject=subject,
        status="ok",
        action="send",
        sent_at__gte=cutoff,
    ).exists()
