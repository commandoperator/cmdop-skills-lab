#!/usr/bin/env python3
"""
Universal campaign sender via llm-email module.
Sends personalized emails with smart account rotation, bounce checking,
and full tracking in SQLite.

Usage:
    # Developers
    python send_campaign.py --dataset openclaw-outreach

    # Investors
    python send_campaign.py --dataset investor-outreach

    # Test mode (one email to yourself)
    python send_campaign.py --dataset openclaw-outreach --test markolofsen@gmail.com

    # Limit number of sends
    python send_campaign.py --dataset investor-outreach --limit 50 --yes
"""

import asyncio
import csv
import json
import random
import sys
import time
from pathlib import Path
from datetime import datetime

# Add llm-email to path
LLM_EMAIL_SRC = Path(__file__).parent.parent / "libs/llm-email/src"
sys.path.insert(0, str(LLM_EMAIL_SRC))

from llm_email.db import init_db, close_db
from llm_email.mailer import send_email, check_duplicate
from llm_email.account_manager import AccountManager
from llm_email.bounces import is_bounced

DEMO_DIR = Path(__file__).parent

# Accounts used for campaign sending (whitelist)
SEND_ACCOUNTS = [
    "eurodotster@gmail.com",
    "imconfirmer@gmail.com",
    "anydatescom@gmail.com",
    "mark2much@gmail.com",
    "globalidorg@gmail.com",
    "kupinetwork@gmail.com",
    "hackandluck@gmail.com",
]


def human_delay(min_sec, max_sec):
    delay = random.uniform(min_sec, max_sec)
    delay += random.gauss(0, delay * 0.1)
    return max(min_sec, delay)


def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    return f"{seconds/3600:.1f}h"


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_developer_dataset():
    """Load openclaw-outreach: developers.json + personalized_messages.json."""
    data_dir = DEMO_DIR / "openclaw-outreach/data"
    contacts_file = data_dir / "developers.json"
    messages_file = data_dir / "personalized_messages.json"

    if not messages_file.exists():
        return [], {}, contacts_file, "json"

    with open(messages_file, "r") as f:
        raw = json.load(f)
    messages = {m["email"].lower(): m for m in raw if m.get("status") == "generated"}

    with open(contacts_file, "r") as f:
        data = json.load(f)

    contacts = []
    for c in data["contacts"]:
        email = c.get("email", "").lower()
        if email and not c.get("email_sent") and not c.get("bounced") and email in messages:
            contacts.append({
                "email": c["email"],
                "name": c.get("name", ""),
                "subject": messages[email].get("subject", ""),
                "body": messages[email].get("message", ""),
            })

    return contacts, messages, contacts_file, "json"


def load_investor_dataset():
    """Load investor-outreach: investors.csv + personalized_messages.json."""
    data_dir = DEMO_DIR / "investor-outreach/data"
    csv_file = data_dir / "investors.csv"
    messages_file = data_dir / "personalized_messages.json"

    if not messages_file.exists():
        return [], {}, csv_file, "csv"

    with open(messages_file, "r") as f:
        raw = json.load(f)
    messages = {m["email"].lower(): m for m in raw if m.get("status") == "generated"}

    contacts = []
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("Email", "").lower().strip()
            if (email
                    and row.get("Sent", "").lower() != "yes"
                    and row.get("Bounced", "").lower() != "yes"
                    and email in messages):
                contacts.append({
                    "email": row["Email"],
                    "name": row.get("Name", ""),
                    "subject": messages[email].get("subject", ""),
                    "body": messages[email].get("message", ""),
                })

    return contacts, messages, csv_file, "csv"


def mark_sent_json(contacts_file, email):
    """Mark email as sent in developers.json."""
    with open(contacts_file, "r") as f:
        data = json.load(f)
    for c in data["contacts"]:
        if c.get("email", "").lower() == email.lower():
            c["email_sent"] = True
            c["email_sent_at"] = datetime.now().isoformat()
            break
    with open(contacts_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def mark_sent_csv(contacts_file, email):
    """Mark email as sent in investors.csv."""
    rows = []
    with open(contacts_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["Email"].lower().strip() == email.lower():
                row["Sent"] = "Yes"
            rows.append(row)
    with open(contacts_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run():
    # Parse args
    dataset = "openclaw-outreach"
    if "--dataset" in sys.argv:
        idx = sys.argv.index("--dataset")
        if idx + 1 < len(sys.argv):
            dataset = sys.argv[idx + 1]

    test_email = None
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        if idx + 1 < len(sys.argv):
            test_email = sys.argv[idx + 1]

    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    auto_yes = "--yes" in sys.argv

    # Load dataset
    if dataset == "openclaw-outreach":
        contacts, messages, contacts_file, fmt = load_developer_dataset()
        mark_sent = mark_sent_json
    elif dataset == "investor-outreach":
        contacts, messages, contacts_file, fmt = load_investor_dataset()
        mark_sent = mark_sent_csv
    else:
        print(f"Unknown dataset: {dataset}")
        return

    # Init llm-email DB
    await init_db()

    try:
        # Init account manager — whitelist only campaign accounts
        mgr = await AccountManager.create(
            only=SEND_ACCOUNTS,
        )
        delays = mgr.get_delay_settings()

        print("=" * 60)
        print(f"Campaign Sender — {dataset}")
        print("=" * 60)

        # Account status
        summary = mgr.accounts_summary()
        print(f"\nAccounts ({len(summary)}):")
        for a in summary:
            status = "READY" if a["available"] else "LIMIT"
            print(f"  {a['email']:<30} day={a['warmup_day']}  limit={a['daily_limit']}  sent={a['sent_today']}  [{status}]")

        capacity = mgr.total_capacity_today()
        print(f"\nCapacity today: {capacity}")
        print(f"Contacts with messages: {len(contacts)}")

        if not contacts:
            print("Nothing to send. Generate messages first.")
            return

        # Filter bounced (from llm-email DB)
        filtered = []
        bounced_count = 0
        for c in contacts:
            if await is_bounced(c["email"]):
                bounced_count += 1
                continue
            if await check_duplicate(c["email"], c["subject"]):
                continue
            filtered.append(c)

        if bounced_count:
            print(f"Skipped {bounced_count} bounced addresses")
        contacts = filtered
        print(f"Ready to send: {len(contacts)}")

        if not contacts:
            print("Nothing to send (all bounced/duplicated).")
            return

        # Test mode
        if test_email:
            first_msg = contacts[0] if contacts else None
            if first_msg:
                contacts = [{
                    "email": test_email,
                    "name": "Test",
                    "subject": first_msg["subject"],
                    "body": first_msg["body"],
                }]
            print(f"\n*** TEST MODE: sending to {test_email} ***")

        # Apply limits
        if limit:
            contacts = contacts[:limit]
        contacts = contacts[:capacity]

        # Plan
        plan = mgr.plan_campaign(len(contacts))
        print(f"Sending: {len(contacts)} emails")
        print(f"Estimated time: {format_time(plan.estimated_hours_today * 3600)}")

        if not auto_yes:
            resp = input(f"\nSend {len(contacts)} email(s)? (yes/no): ").strip().lower()
            if resp != "yes":
                print("Aborted.")
                return

        # Send loop
        sent = 0
        failed = 0
        start = time.time()

        for i, contact in enumerate(contacts, 1):
            email = contact["email"]
            subject = contact["subject"]
            body = contact["body"]

            from_acc = mgr.pick_account()
            if not from_acc:
                print("\nAll accounts hit limits. Waiting 1 hour...")
                time.sleep(3600)
                from_acc = mgr.pick_account()
                if not from_acc:
                    print("Still no accounts. Stopping.")
                    break

            print(f"\n[{i}/{len(contacts)}] {email}")
            print(f"  From: {from_acc}")
            print(f"  Subject: {subject[:55]}")

            # Send via llm-email (tracks in SQLite automatically)
            result = await send_email(
                to=email, subject=subject, body=body, from_account=from_acc,
            )

            if result.ok:
                print("  Status: OK")
                mgr.record_send(from_acc)
                mark_sent(contacts_file, email)
                sent += 1
            else:
                print(f"  Status: FAILED — {result.error}")
                failed += 1

            # Delays
            if i < len(contacts):
                if i % delays["batch_size"] == 0:
                    pause = human_delay(delays["batch_pause_min"], delays["batch_pause_max"])
                    print(f"\n  Batch #{i // delays['batch_size']} done. Pause {format_time(pause)}...")
                    time.sleep(pause)
                else:
                    delay = human_delay(delays["min_delay"], delays["max_delay"])
                    print(f"  Waiting {delay:.0f}s...")
                    time.sleep(delay)

        elapsed = time.time() - start

        # Summary
        print("\n" + "=" * 60)
        print("Account summary:")
        for a in mgr.accounts_summary():
            print(f"  {a['email']:<30} sent={a['sent_today']}/{a['daily_limit']}")

        print(f"\nDone in {format_time(elapsed)}")
        print(f"Sent: {sent}, Failed: {failed}")

    finally:
        await close_db()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
