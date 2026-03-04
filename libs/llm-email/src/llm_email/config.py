"""Configuration for llm-email package.

Paths (data, db, logs) and operational constants.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_PKG_DIR)
SKILL_DIR = os.path.dirname(_SRC_DIR)

# Data directory (db + logs)
DATA_DIR = os.path.join(SKILL_DIR, "data")

# Database
DB_PATH = os.path.join(DATA_DIR, "emails.db")
DB_URL = f"sqlite://{DB_PATH}"

# Logging
LOG_DIR = os.path.join(DATA_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "llm-email.log")

# ---------------------------------------------------------------------------
# AppleScript
# ---------------------------------------------------------------------------

OSASCRIPT_TIMEOUT = 30
OSASCRIPT_ACCOUNTS_TIMEOUT = 10
OSASCRIPT_HEALTH_TIMEOUT = 5

# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

DEDUP_HOURS = 24

# ---------------------------------------------------------------------------
# Status / Stats
# ---------------------------------------------------------------------------

STATUS_DEFAULT_LIMIT = 10
STATS_TOP_RECIPIENTS = 5
