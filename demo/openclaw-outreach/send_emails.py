#!/usr/bin/env python3
"""
Send personalized emails to OpenClaw developers via llm-email skill.
Uses AccountManager for smart limits, warmup, and rotation.
"""

import asyncio
import json
import random
import sys
import time
from pathlib import Path
from datetime import datetime

# Paths
DATA_DIR = Path(__file__).parent / "data"
CONTACTS_FILE = DATA_DIR / "developers.json"
MESSAGES_FILE = DATA_DIR / "personalized_messages.json"
LOG_FILE = DATA_DIR / "send_log.txt"

# Test mode: set to an email address for single-recipient testing, or None
TEST_EMAIL = None


def log_send(email, status, from_acc="", subject="", message=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} | {status} | {from_acc} | {email} | {subject[:50]} | {message}\n")


def update_contacts_sent(email):
    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for c in data["contacts"]:
        if c.get("email", "").lower() == email.lower():
            c["email_sent"] = True
            c["email_sent_at"] = datetime.now().isoformat()
            break
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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


async def run():
    from llm_email.db import init_db, close_db
    from llm_email.mailer import send_email
    from llm_email.account_manager import AccountManager
    from llm_email.bounces import is_bounced

    await init_db()

    try:
        # Init account manager
        mgr = await AccountManager.create()
        delays = mgr.get_delay_settings()

        print("=" * 60)
        print("OpenClaw Developer Outreach — Email Sender")
        print("=" * 60)

        # Print account status
        summary = mgr.accounts_summary()
        print(f"\nAccounts ({len(summary)}):")
        for a in summary:
            status = "READY" if a["available"] else "LIMIT"
            print(f"  {a['email']:<30} day={a['warmup_day']}  limit={a['daily_limit']}  sent={a['sent_today']}  remaining={a['remaining']}  [{status}]")

        capacity = mgr.total_capacity_today()
        print(f"\nTotal capacity today: {capacity}")

        if TEST_EMAIL:
            print(f"\n*** TEST MODE: Only sending to {TEST_EMAIL} ***")

        # Load messages
        if not MESSAGES_FILE.exists():
            print("\nERROR: No messages found. Run generate_messages.py first.")
            return

        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            raw_messages = json.load(f)
        messages = {m["email"].lower(): m for m in raw_messages if m.get("status") == "generated"}
        print(f"Personalized messages: {len(messages)}")

        # Load contacts — unsent, not bounced, with messages ready
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        contacts = []
        for c in data["contacts"]:
            if not c.get("email") or c.get("email_sent") or c.get("bounced"):
                continue
            if c["email"].lower() not in messages:
                continue
            # Check bounce DB
            if await is_bounced(c["email"]):
                continue
            contacts.append(c)

        print(f"Contacts ready to send: {len(contacts)}")

        if not contacts:
            print("Nothing to send.")
            return

        # Test mode
        if TEST_EMAIL:
            contacts = [c for c in contacts if c["email"].lower() == TEST_EMAIL.lower()]
            if not contacts:
                first = next(iter(messages.values()))
                contacts = [{"email": TEST_EMAIL, "username": "test", "name": "Test"}]
                messages[TEST_EMAIL.lower()] = first

        contacts = contacts[:capacity]

        # Plan
        plan = mgr.plan_campaign(len(contacts))
        print(f"Estimated time today: {format_time(plan.estimated_hours_today * 3600)}")
        if not plan.can_finish_today:
            print(f"Full campaign needs {plan.days_needed} days")

        if "--yes" not in sys.argv:
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
            msg = messages[email.lower()]
            subject = msg.get("subject", "Quick question about your project")
            body = msg.get("message", "")

            from_acc = mgr.pick_account()
            if not from_acc:
                print("\nAll accounts hit limits. Waiting 1 hour...")
                time.sleep(3600)
                from_acc = mgr.pick_account()
                if not from_acc:
                    print("Still no accounts available. Stopping.")
                    break

            print(f"\n[{i}/{len(contacts)}] {email}")
            print(f"  From: {from_acc}")
            print(f"  Subject: {subject[:50]}")

            result = await send_email(
                to=email, subject=subject, body=body, from_account=from_acc,
            )

            if result.get("ok"):
                print("  Status: OK")
                log_send(email, "SENT", from_acc, subject)
                update_contacts_sent(email)
                mgr.record_send(from_acc)
                sent += 1
            else:
                error = result.get("error", "unknown")
                print(f"  Status: FAILED - {error}")
                log_send(email, "FAILED", from_acc, subject, error)
                failed += 1

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
        print("\n" + "=" * 60)
        print(f"Done in {format_time(elapsed)}")
        print(f"Sent: {sent}, Failed: {failed}")
        print(f"Log: {LOG_FILE}")

    finally:
        await close_db()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
