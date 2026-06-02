#!/usr/bin/env python3
"""
Auto-collect bounces from Mail.app and mark in contact databases.
Uses AppleScript `search` command for speed (searches across all mailboxes at once).

Usage:
    python collect_bounces.py              # scan last 1 day
    python collect_bounces.py --days 7     # scan last 7 days
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Contact databases
INVESTOR_CSV = Path(__file__).parent / "investor-outreach/data/investors.csv"
DEVELOPER_JSON = Path(__file__).parent / "openclaw-outreach/data/developers.json"
BOUNCE_LOG = Path(__file__).parent / "bounces_log.json"

# Our sending accounts
SEND_ACCOUNTS = [
    "eurodotster@gmail.com",
    "imconfirmer@gmail.com",
    "anydatescom@gmail.com",
    "mark2much@gmail.com",
    "globalidorg@gmail.com",
    "kupinetwork@gmail.com",
    "hackandluck@gmail.com",
]


def fetch_bounces_from_mail(days: int = 1) -> str:
    """Fetch bounce message content using per-account inbox scan with short timeout."""
    all_content = []

    for account_email in SEND_ACCOUNTS:
        account_name = account_email.split("@")[0]
        # Only scan inbox of each account — fast and where bounces land
        script = f'''tell application "Mail"
try
set acct to account "{account_email}"
set mb to inbox of acct
set cutoffDate to (current date) - ({days} * days)
set msgs to (messages of mb whose date received > cutoffDate and (sender contains "mailer-daemon" or sender contains "postmaster" or subject contains "Undelivered" or subject contains "Delivery Status" or subject contains "Undeliverable"))
set result to ""
repeat with msg in msgs
set result to result & content of msg & "###SEP###"
end repeat
return result
on error
return ""
end try
end tell'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode == 0 and result.stdout.strip():
                all_content.append(result.stdout.strip())
                count = result.stdout.count("###SEP###")
                if count > 0:
                    print(f"  {account_name}: {count} bounce(s)")
        except subprocess.TimeoutExpired:
            print(f"  {account_name}: timeout (skipped)")
        except Exception as e:
            print(f"  {account_name}: error — {e}")

    return "###SEP###".join(all_content)


def extract_bounced_emails(raw: str) -> set[str]:
    """Extract bounced email addresses from bounce message bodies."""
    bounced = set()

    # RFC Final-Recipient header
    for m in re.findall(r"Final-Recipient:\s*rfc822;\s*(\S+@\S+)", raw):
        bounced.add(m.strip().lower().rstrip("."))

    # Russian Gmail: "адрес X не найден"
    for m in re.findall(r"адрес\s+(\S+@\S+)\s+не найден", raw):
        bounced.add(m.strip().lower().rstrip("."))

    # English patterns
    for m in re.findall(r"address\s+(\S+@\S+)\s+(?:not found|rejected|does not exist)", raw, re.I):
        bounced.add(m.strip().lower().rstrip("."))

    for m in re.findall(r"(\S+@\S+)\s+(?:could not be delivered|was not delivered)", raw, re.I):
        bounced.add(m.strip().lower().rstrip("."))

    # Filter system addresses
    bounced = {
        e for e in bounced
        if "@" in e
        and "mailer-daemon" not in e
        and "google" not in e
        and "postmaster" not in e
    }

    return bounced


def load_existing_bounces() -> set[str]:
    """Load previously detected bounces."""
    if BOUNCE_LOG.exists():
        with open(BOUNCE_LOG, "r") as f:
            return set(json.load(f))
    return set()


def mark_investor_csv(bounced: set[str]) -> int:
    if not INVESTOR_CSV.exists():
        return 0
    rows = []
    marked = 0
    with open(INVESTOR_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "Bounced" not in fieldnames:
            fieldnames.append("Bounced")
        for row in reader:
            if row.get("Email", "").lower().strip() in bounced:
                row["Bounced"] = "Yes"
                marked += 1
            elif "Bounced" not in row:
                row["Bounced"] = ""
            rows.append(row)
    with open(INVESTOR_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return marked


def mark_developer_json(bounced: set[str]) -> int:
    if not DEVELOPER_JSON.exists():
        return 0
    with open(DEVELOPER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    marked = 0
    for c in data["contacts"]:
        if c.get("email", "").lower().strip() in bounced and not c.get("bounced"):
            c["bounced"] = True
            c["bounce_detected_at"] = datetime.now().isoformat()
            marked += 1
    with open(DEVELOPER_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return marked


def save_bounce_log(bounced: set[str]) -> int:
    existing = load_existing_bounces()
    all_bounces = sorted(existing | bounced)
    new_count = len(all_bounces) - len(existing)
    with open(BOUNCE_LOG, "w") as f:
        json.dump(all_bounces, f, indent=2)
    return new_count


def main():
    days = 1
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    print(f"Scanning Mail.app for bounces (last {days} day(s))...")
    print(f"Checking {len(SEND_ACCOUNTS)} accounts...\n")

    raw = fetch_bounces_from_mail(days=days)

    if not raw.strip():
        print("\nNo new bounce messages found in inboxes.")
        existing = load_existing_bounces()
        if existing:
            print(f"Previously known bounces: {len(existing)}")
        return

    bounced = extract_bounced_emails(raw)
    existing = load_existing_bounces()
    new_bounces = bounced - existing
    all_bounces = bounced | existing

    print(f"\nExtracted: {len(bounced)} bounced addresses ({len(new_bounces)} new)")

    if new_bounces:
        inv_marked = mark_investor_csv(all_bounces)
        dev_marked = mark_developer_json(all_bounces)
        new_saved = save_bounce_log(all_bounces)

        print(f"Investors marked: {inv_marked}")
        print(f"Developers marked: {dev_marked}")

        print(f"\nNew bounces:")
        for e in sorted(new_bounces):
            print(f"  {e}")
    else:
        print("No new bounces (all already known).")

    print(f"\nTotal bounced addresses: {len(all_bounces)}")


if __name__ == "__main__":
    main()
