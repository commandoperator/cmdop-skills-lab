#!/usr/bin/env python3
"""
Campaign sender via SDKRouter SMTP (SES/Gmail/any SMTP).
Alternative to Mail.app — works on any OS, no AppleScript.

Usage:
    # Send investor campaign via SMTP
    python send_campaign_smtp.py --dataset investor-outreach --limit 10 --yes

    # Send developer campaign
    python send_campaign_smtp.py --dataset openclaw-outreach --limit 50 --yes

    # Specify account
    python send_campaign_smtp.py --dataset investor-outreach --account ses-us-east-1 --yes
"""

import csv
import json
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from sdkrouter import SDKRouter

API_KEY = "test-api-key"
DEMO_DIR = Path(__file__).parent.parent

# Sending settings
MIN_DELAY = 5       # SMTP is faster, less delay needed
MAX_DELAY = 15
BATCH_SIZE = 20
BATCH_PAUSE_MIN = 30
BATCH_PAUSE_MAX = 60


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


def load_investor_dataset():
    data_dir = DEMO_DIR / "investor-outreach/data"
    csv_file = data_dir / "investors.csv"
    messages_file = data_dir / "personalized_messages.json"

    if not messages_file.exists():
        return [], csv_file, "csv"

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
    return contacts, csv_file, "csv"


def load_developer_dataset():
    data_dir = DEMO_DIR / "openclaw-outreach/data"
    contacts_file = data_dir / "developers.json"
    messages_file = data_dir / "personalized_messages.json"

    if not messages_file.exists():
        return [], contacts_file, "json"

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
    return contacts, contacts_file, "json"


def mark_sent(contacts_file: Path, email: str, fmt: str):
    if fmt == "csv":
        rows = []
        with open(contacts_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                if row["Email"].lower().strip() == email.lower():
                    row["Sent"] = "Yes"
                rows.append(row)
        with open(contacts_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    elif fmt == "json":
        with open(contacts_file, "r") as f:
            data = json.load(f)
        for c in data["contacts"]:
            if c.get("email", "").lower() == email.lower():
                c["email_sent"] = True
                c["email_sent_at"] = datetime.now().isoformat()
                break
        with open(contacts_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    dataset = "investor-outreach"
    account_alias = ""
    limit = None
    auto_yes = "--yes" in sys.argv

    if "--dataset" in sys.argv:
        idx = sys.argv.index("--dataset")
        if idx + 1 < len(sys.argv):
            dataset = sys.argv[idx + 1]

    if "--account" in sys.argv:
        idx = sys.argv.index("--account")
        if idx + 1 < len(sys.argv):
            account_alias = sys.argv[idx + 1]

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    # Load dataset
    if dataset == "investor-outreach":
        contacts, contacts_file, fmt = load_investor_dataset()
    elif dataset == "openclaw-outreach":
        contacts, contacts_file, fmt = load_developer_dataset()
    else:
        print(f"Unknown dataset: {dataset}")
        return

    client = SDKRouter(api_key=API_KEY)

    # List accounts
    print("=" * 60)
    print(f"SMTP Campaign Sender — {dataset}")
    print("=" * 60)

    accounts = client.email.list_accounts()
    if not accounts:
        print("\nNo SMTP accounts. Run setup_account.py first.")
        return

    print(f"\nSMTP Accounts:")
    for a in accounts:
        marker = " <-- using" if (account_alias and a.alias == account_alias) or (not account_alias and a.is_default) else ""
        print(f"  {a.alias:<20} {a.from_email:<35}{marker}")

    print(f"\nContacts ready: {len(contacts)}")

    if not contacts:
        print("Nothing to send.")
        return

    if limit:
        contacts = contacts[:limit]

    if not auto_yes:
        resp = input(f"\nSend {len(contacts)} email(s) via SMTP? (yes/no): ").strip().lower()
        if resp != "yes":
            print("Aborted.")
            return

    # Send
    sent = 0
    failed = 0
    start = time.time()

    for i, contact in enumerate(contacts, 1):
        email = contact["email"]
        subject = contact["subject"]
        body = contact["body"]

        print(f"\n[{i}/{len(contacts)}] {email}")
        print(f"  Subject: {subject[:55]}")

        try:
            kwargs = {"to": email, "subject": subject, "body": body}
            if account_alias:
                kwargs["account_alias"] = account_alias

            result = client.email.send(**kwargs)
            print(f"  Status: OK (msg_id: {result.message_id})")
            mark_sent(contacts_file, email, fmt)
            sent += 1
        except Exception as e:
            print(f"  Status: FAILED — {e}")
            failed += 1

        # Delays
        if i < len(contacts):
            if i % BATCH_SIZE == 0:
                pause = human_delay(BATCH_PAUSE_MIN, BATCH_PAUSE_MAX)
                print(f"\n  Batch #{i // BATCH_SIZE} done. Pause {format_time(pause)}...")
                time.sleep(pause)
            else:
                delay = human_delay(MIN_DELAY, MAX_DELAY)
                print(f"  Waiting {delay:.0f}s...")
                time.sleep(delay)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"Done in {format_time(elapsed)}")
    print(f"Sent: {sent}, Failed: {failed}")


if __name__ == "__main__":
    main()
