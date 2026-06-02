"""Telegram notifications for llm-email events.

Reads config from .env file in llm-email root, or from environment variables:
    LLM_EMAIL_TG_BOT_TOKEN  — Telegram bot token
    LLM_EMAIL_TG_CHAT_ID    — Telegram chat/group ID
"""

import os
from pathlib import Path

import requests

from llm_email.config import SKILL_DIR
from llm_email.logger import log


def _load_env() -> dict[str, str]:
    """Load .env file from llm-email root."""
    env_file = Path(SKILL_DIR) / ".env"
    values: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


_env = _load_env()

TELEGRAM_BOT_TOKEN = os.environ.get("LLM_EMAIL_TG_BOT_TOKEN") or _env.get("LLM_EMAIL_TG_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("LLM_EMAIL_TG_CHAT_ID") or _env.get("LLM_EMAIL_TG_CHAT_ID", "")


def send_telegram(message: str) -> bool:
    """Send a message to the configured Telegram chat.

    Returns False silently if not configured.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.debug("Telegram not configured (set in .env or env vars)")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        if resp.status_code != 200:
            log.warning("Telegram API returned %d", resp.status_code)
        return resp.status_code == 200
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


def notify_replies(replies: list[dict]) -> None:
    """Notify about new email replies."""
    if not replies:
        return

    emoji_map = {
        "interested": "\U0001f525",
        "ooo": "\U0001f4c5",
        "unsubscribe": "\U0001f6ab",
        "not_relevant": "\U0001f44e",
        "other": "\U00002709",
    }

    lines = [f"<b>\U0001f4e8 {len(replies)} new email replies</b>\n"]
    for r in replies:
        emoji = emoji_map.get(r["type"], "\U00002709")
        rtype = r["type"].upper()
        line = f"{emoji} <b>[{rtype}]</b> {r.get('name') or r['from']}"
        if r.get("summary"):
            line += f"\n    {r['summary']}"
        if r.get("redirect"):
            line += f"\n    \U000027A1 Redirect: {r['redirect']}"
        lines.append(line)

    send_telegram("\n".join(lines))


def notify_bounces(bounces: list[dict]) -> None:
    """Notify about new bounced emails."""
    if not bounces:
        return

    msg = f"\U0001f4ad <b>{len(bounces)} new bounces</b>\n\n"
    for b in bounces[:10]:
        msg += f"  \U0000274c {b['email']} ({b['type']})\n"
    if len(bounces) > 10:
        msg += f"  ... and {len(bounces) - 10} more"

    send_telegram(msg)


def notify_campaign_done(sent: int, failed: int, remaining: int) -> None:
    """Notify when a campaign batch finishes."""
    msg = (
        f"\U0001f4e7 <b>Campaign batch done</b>\n\n"
        f"\U00002705 Sent: {sent}\n"
        f"\U0000274c Failed: {failed}\n"
        f"\U0001f4ec Remaining: {remaining}"
    )
    send_telegram(msg)
