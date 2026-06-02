#!/usr/bin/env python3
"""
Bounce tracker — reads bounce/undeliverable emails from Mail.app,
classifies them via SDKRouter LLM, and marks contacts as bounced.
"""

import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal
from sdkrouter import SDKRouter

# Paths
DATA_DIR = Path(__file__).parent / "data"
CONTACTS_FILE = DATA_DIR / "developers.json"
BOUNCES_FILE = DATA_DIR / "bounces.json"

# SDKRouter
API_KEY = "test-api-key"
MODEL = "openai/gpt-4.1-nano"

# Mail.app — search for bounce messages
BOUNCE_SENDERS = [
    "mailer-daemon",
    "postmaster",
    "mail delivery subsystem",
]

BOUNCE_SUBJECTS = [
    "Undelivered Mail",
    "Delivery Status Notification",
    "Mail delivery failed",
    "Returned mail",
    "Undeliverable",
    "failure notice",
]


class BounceClassification(BaseModel):
    is_bounce: bool = Field(description="True if this is a bounce/undeliverable notification")
    bounce_type: Literal["hard", "soft", "unknown"] = Field(
        description="hard = permanent (mailbox not found, domain gone), soft = temporary (mailbox full, server down)"
    )
    reason: str = Field(description="Short reason: 'mailbox not found', 'domain expired', 'quota exceeded', etc.")
    original_recipient: str = Field(description="The email address that bounced (extracted from the bounce message)")


def fetch_bounce_emails(days: int = 7, limit: int = 200) -> list[dict]:
    """Fetch potential bounce emails from Mail.app via AppleScript."""
    script = f'''
tell application "Mail"
    set bounceMessages to {{}}
    set cutoffDate to (current date) - ({days} * days)

    repeat with mb in mailboxes of account 1
        try
            set msgs to (messages of mb whose date received > cutoffDate and (sender contains "mailer-daemon" or sender contains "postmaster" or sender contains "Mail Delivery" or subject contains "Undelivered" or subject contains "Delivery Status" or subject contains "delivery failed" or subject contains "Undeliverable"))
            repeat with msg in msgs
                if (count of bounceMessages) >= {limit} then exit repeat
                set msgInfo to (subject of msg) & "|||" & (sender of msg) & "|||" & (content of msg)
                set end of bounceMessages to msgInfo
            end repeat
        end try
        if (count of bounceMessages) >= {limit} then exit repeat
    end repeat

    set AppleScript's text item delimiters to "###SEPARATOR###"
    return bounceMessages as text
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr}")
            return []

        raw = result.stdout.strip()
        if not raw:
            return []

        entries = raw.split("###SEPARATOR###")
        messages = []
        for entry in entries:
            parts = entry.strip().split("|||")
            if len(parts) >= 3:
                messages.append({
                    "subject": parts[0].strip(),
                    "sender": parts[1].strip(),
                    "body": parts[2].strip()[:3000],  # limit body size for LLM
                })
        return messages

    except subprocess.TimeoutExpired:
        print("Timeout reading Mail.app")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def extract_emails_from_text(text: str) -> list[str]:
    """Quick regex extraction of email addresses from text."""
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)


def classify_bounce(client: SDKRouter, msg: dict) -> BounceClassification | None:
    """Classify a bounce message using LLM structured output."""
    body_preview = msg["body"][:2000]

    prompt = f"""Analyze this email and determine if it's a bounce/undeliverable notification.

Subject: {msg['subject']}
From: {msg['sender']}
Body (truncated):
{body_preview}

If it IS a bounce, extract the original recipient email that failed and classify the bounce type."""

    try:
        result = client.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an email delivery analyst. Classify bounce notifications accurately."},
                {"role": "user", "content": prompt},
            ],
            response_format=BounceClassification,
            temperature=0,
            max_tokens=300,
        )
        parsed: BounceClassification = result.choices[0].message.parsed  # type: ignore[assignment]
        return parsed
    except Exception as e:
        print(f"  LLM error: {e}")
        return None


def load_known_bounces() -> dict[str, dict]:
    """Load previously detected bounces."""
    if BOUNCES_FILE.exists():
        with open(BOUNCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {b["email"].lower(): b for b in data}
    return {}


def save_bounces(bounces: dict[str, dict]):
    """Save bounces to file."""
    with open(BOUNCES_FILE, "w", encoding="utf-8") as f:
        json.dump(list(bounces.values()), f, indent=2, ensure_ascii=False)


def update_contact_bounced(email: str, bounce_type: str, reason: str):
    """Mark a contact as bounced in developers.json."""
    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for c in data["contacts"]:
        if c.get("email", "").lower() == email.lower():
            c["bounced"] = True
            c["bounce_type"] = bounce_type
            c["bounce_reason"] = reason
            c["bounce_detected_at"] = datetime.now().isoformat()
            break

    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    import sys

    days = 7
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    print("=" * 60)
    print("Bounce Tracker — Mail.app + SDKRouter LLM")
    print("=" * 60)
    print(f"Scanning last {days} days...")

    # Fetch bounce candidates from Mail.app
    messages = fetch_bounce_emails(days=days)
    print(f"Found {len(messages)} potential bounce messages")

    if not messages:
        print("No bounce messages found.")
        return

    # Load existing bounces
    known = load_known_bounces()
    print(f"Previously known bounces: {len(known)}")

    # Classify each message
    client = SDKRouter(api_key=API_KEY)
    new_bounces = 0

    for i, msg in enumerate(messages, 1):
        # Quick check: any known emails in body?
        emails_in_body = extract_emails_from_text(msg["body"])
        already_known = [e for e in emails_in_body if e.lower() in known]
        if already_known:
            print(f"[{i}/{len(messages)}] Skip — already tracked: {already_known[0]}")
            continue

        print(f"[{i}/{len(messages)}] Classifying: {msg['subject'][:60]}...")
        result = classify_bounce(client, msg)

        if result and result.is_bounce and result.original_recipient:
            email = result.original_recipient.lower()

            if email in known:
                print(f"  Already known bounce: {email}")
                continue

            print(f"  BOUNCE: {email} ({result.bounce_type}) — {result.reason}")

            known[email] = {
                "email": email,
                "bounce_type": result.bounce_type,
                "reason": result.reason,
                "detected_at": datetime.now().isoformat(),
                "source_subject": msg["subject"][:100],
            }

            update_contact_bounced(email, result.bounce_type, result.reason)
            new_bounces += 1
        else:
            print(f"  Not a bounce or no recipient found")

    # Save all bounces
    save_bounces(known)

    print("\n" + "=" * 60)
    print(f"New bounces detected: {new_bounces}")
    print(f"Total bounces tracked: {len(known)}")
    print(f"Saved to: {BOUNCES_FILE}")


if __name__ == "__main__":
    main()
