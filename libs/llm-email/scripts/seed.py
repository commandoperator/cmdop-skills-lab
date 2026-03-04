#!/usr/bin/env python3
"""Seed the emails.db with test data for dashboard development."""

import os
import random
import sqlite3
from datetime import datetime, timedelta

import click

from llm_email.config import DATA_DIR, DB_PATH

RECIPIENTS = [
    "alice@example.com",
    "bob@company.org",
    "carol@startup.io",
    "dave@agency.net",
    "eve@university.edu",
    "frank@corp.com",
    "grace@design.co",
    "heidi@marketing.biz",
]

SUBJECTS = [
    "Weekly sync notes",
    "Invoice #{}",
    "Project update — Q1",
    "Meeting follow-up",
    "Quick question about the API",
    "Contract review",
    "Design feedback needed",
    "Re: Launch timeline",
    "Onboarding docs",
    "Bug report — dashboard",
]

ACCOUNTS = ["work@gmail.com", "personal@icloud.com", "default"]

BODIES = [
    "Hi,\n\nPlease find the attached report.\n\nBest regards",
    "Hey,\n\nJust following up on our earlier conversation.\n\nThanks!",
    "Hello,\n\nCould you review this by EOD Friday?\n\nCheers",
    "Hi team,\n\nHere are the updated numbers for this week.\n\nBest",
    "Hey,\n\nQuick heads up — the deployment is scheduled for tonight.\n\nThanks",
]


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_addr VARCHAR(512) NOT NULL,
            cc_addr VARCHAR(512) DEFAULT '',
            bcc_addr VARCHAR(512) DEFAULT '',
            subject VARCHAR(1024) NOT NULL,
            body TEXT NOT NULL,
            from_account VARCHAR(256) DEFAULT 'default',
            action VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL,
            error_message TEXT DEFAULT '',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def generate_row(base_time: datetime) -> dict:
    status = random.choices(["ok", "error"], weights=[90, 10])[0]
    action = random.choices(["send", "draft"], weights=[85, 15])[0]
    offset = timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    subject = random.choice(SUBJECTS).format(random.randint(1000, 9999))

    return {
        "to_addr": random.choice(RECIPIENTS),
        "cc_addr": random.choice(RECIPIENTS) if random.random() < 0.2 else "",
        "bcc_addr": "",
        "subject": subject,
        "body": random.choice(BODIES),
        "from_account": random.choice(ACCOUNTS),
        "action": action,
        "status": status,
        "error_message": "osascript timed out" if status == "error" else "",
        "sent_at": (base_time + offset).isoformat(),
    }


@click.command()
@click.option("-n", "--count", default=50, show_default=True, help="Number of records to generate.")
@click.option("-d", "--days", default=30, show_default=True, help="Spread records over this many days.")
@click.option("--clear", is_flag=True, help="Clear existing records before seeding.")
def seed(count: int, days: int, clear: bool) -> None:
    """Seed emails.db with random test data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_table(conn)

    if clear:
        conn.execute("DELETE FROM sent_emails")
        conn.commit()
        click.echo("Cleared existing records.")

    now = datetime.now()
    rows = []
    for _ in range(count):
        day_offset = random.randint(0, days - 1)
        base = now - timedelta(days=day_offset)
        rows.append(generate_row(base))

    conn.executemany(
        "INSERT INTO sent_emails (to_addr, cc_addr, bcc_addr, subject, body, from_account, action, status, error_message, sent_at) "
        "VALUES (:to_addr, :cc_addr, :bcc_addr, :subject, :body, :from_account, :action, :status, :error_message, :sent_at)",
        rows,
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
    conn.close()

    click.echo(f"Inserted {count} records ({days} days). Total in DB: {total}")
    click.echo(f"DB: {DB_PATH}")


if __name__ == "__main__":
    seed()
