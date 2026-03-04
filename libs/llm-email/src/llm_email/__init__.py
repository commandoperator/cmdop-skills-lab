"""llm-email — Send emails via macOS Mail.app with AppleScript integration and Tortoise ORM tracking."""

from llm_email.applescript import escape_applescript, run_osascript, split_addrs
from llm_email.config import DB_PATH, DB_URL, SKILL_DIR
from llm_email.db import init_db, close_db
from llm_email.logger import log
from llm_email.mailer import send_email, list_accounts, check_health, show_status, show_stats, check_duplicate
from llm_email.models import SentEmail

__all__ = [
    "escape_applescript", "run_osascript", "split_addrs",
    "DB_PATH", "DB_URL", "SKILL_DIR",
    "init_db", "close_db",
    "log",
    "send_email", "list_accounts", "check_health", "show_status", "show_stats", "check_duplicate",
    "SentEmail",
]
