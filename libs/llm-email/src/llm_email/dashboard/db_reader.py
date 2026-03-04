"""Sync SQLite reader for the llm-email dashboard."""

import os
import sqlite3

import pandas as pd

from llm_email.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def get_all_emails(limit: int = 500) -> pd.DataFrame:
    """All records from sent_emails, newest first."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM sent_emails ORDER BY sent_at DESC LIMIT ?",
        conn,
        params=[limit],
    )
    conn.close()
    if not df.empty:
        df["sent_at"] = pd.to_datetime(df["sent_at"])
    return df


def get_stats() -> dict:
    """Aggregated send statistics."""
    conn = get_connection()
    cur = conn.cursor()
    total = cur.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE status='ok'"
    ).fetchone()[0]
    errors = cur.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE status='error'"
    ).fetchone()[0]
    today = cur.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE status='ok' AND sent_at >= date('now', '-1 day')"
    ).fetchone()[0]
    week = cur.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE status='ok' AND sent_at >= date('now', '-7 days')"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "errors": errors, "today": today, "week": week}


def get_top_recipients(limit: int = 10) -> pd.DataFrame:
    """Top recipients by send count."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT to_addr, COUNT(*) as count FROM sent_emails "
        "WHERE status='ok' GROUP BY to_addr ORDER BY count DESC LIMIT ?",
        conn,
        params=[limit],
    )
    conn.close()
    return df


def db_exists() -> bool:
    """Check if the database file exists."""
    return os.path.isfile(DB_PATH)
