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


def get_account_stats() -> pd.DataFrame:
    """Per-account send counts (today and total)."""
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            from_account,
            COUNT(*) as total_sent,
            SUM(CASE WHEN sent_at >= date('now', '-1 day') THEN 1 ELSE 0 END) as sent_today,
            SUM(CASE WHEN sent_at >= datetime('now', '-1 hour') THEN 1 ELSE 0 END) as sent_this_hour,
            MIN(sent_at) as first_send
        FROM sent_emails
        WHERE status='ok' AND action='send'
        GROUP BY from_account
        ORDER BY total_sent DESC
        """,
        conn,
    )
    conn.close()
    return df


def get_bounces(limit: int = 200) -> pd.DataFrame:
    """All bounce records, newest first."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM bounce_emails ORDER BY detected_at DESC LIMIT ?",
            conn,
            params=[limit],
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if not df.empty and "detected_at" in df.columns:
        df["detected_at"] = pd.to_datetime(df["detected_at"])
    return df


def get_bounce_stats() -> dict:
    """Bounce type counts."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM bounce_emails").fetchone()[0]
        hard = cur.execute("SELECT COUNT(*) FROM bounce_emails WHERE bounce_type='hard'").fetchone()[0]
        soft = cur.execute("SELECT COUNT(*) FROM bounce_emails WHERE bounce_type='soft'").fetchone()[0]
    except Exception:
        total = hard = soft = 0
    conn.close()
    return {"total": total, "hard": hard, "soft": soft}


def db_exists() -> bool:
    """Check if the database file exists."""
    return os.path.isfile(DB_PATH)
