"""Shared types, enums, and result dataclasses for llm-email."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EmailAction(str, Enum):
    SEND = "send"
    DRAFT = "draft"


class EmailStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class BounceType(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    UNKNOWN = "unknown"


class ReplyType(str, Enum):
    INTERESTED = "interested"
    OOO = "ooo"
    UNSUBSCRIBE = "unsubscribe"
    NOT_RELEVANT = "not_relevant"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Result dataclasses (returned by mailer, bounces, replies, account_manager)
# ---------------------------------------------------------------------------

@dataclass
class SendResult:
    ok: bool
    action: EmailAction
    to: str = ""
    subject: str = ""
    error: str = ""


@dataclass
class AccountInfo:
    name: str
    email: str
    default: bool = False


@dataclass
class AccountsResult:
    ok: bool
    accounts: list[AccountInfo] = field(default_factory=list)
    error: str = ""


@dataclass
class HealthResult:
    ok: bool
    mail_running: bool = False
    error: str = ""


@dataclass
class StatsResult:
    ok: bool
    total_sent: int = 0
    sent_today: int = 0
    sent_this_week: int = 0
    total_errors: int = 0
    top_recipients: list[dict] = field(default_factory=list)


@dataclass
class StatusEntry:
    to: str
    subject: str
    from_account: str
    action: EmailAction
    status: EmailStatus
    sent_at: str


@dataclass
class StatusResult:
    ok: bool
    total_sent: int = 0
    recent: list[StatusEntry] = field(default_factory=list)


@dataclass
class BounceDetail:
    email: str
    type: BounceType
    reason: str


@dataclass
class BounceResult:
    ok: bool
    new_bounces: int = 0
    total_bounces: int = 0
    details: list[BounceDetail] = field(default_factory=list)


@dataclass
class BounceStatsResult:
    ok: bool
    total: int = 0
    hard: int = 0
    soft: int = 0
    unknown: int = 0


@dataclass
class ReplyDetail:
    from_email: str
    name: str
    type: ReplyType
    summary: str
    redirect: str = ""


@dataclass
class ReplyResult:
    ok: bool
    new_replies: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    details: list[ReplyDetail] = field(default_factory=list)


@dataclass
class ReplyStatsResult:
    ok: bool
    total: int = 0
    unhandled: int = 0
    interested: int = 0
    ooo: int = 0
    unsubscribe: int = 0
    not_relevant: int = 0
    other: int = 0
