"""Smart account manager with auto-calculated limits, warmup, and rotation.

Usage:
    mgr = await AccountManager.create()
    acc = mgr.pick_account()          # next available account
    plan = mgr.plan_campaign(3000)    # schedule for N emails
    summary = mgr.accounts_summary()  # per-account status
"""

import random
from datetime import datetime, timedelta, timezone, date
from dataclasses import dataclass, field

from llm_email.mailer import list_accounts
from llm_email.models import SentEmail
from llm_email.logger import log


# ---------------------------------------------------------------------------
# Gmail limits (conservative safe-zone values)
# ---------------------------------------------------------------------------

GMAIL_HARD_LIMIT = 500          # Google hard limit per account per day
GMAIL_SAFE_LIMIT = 400          # safe zone to avoid triggers
GMAIL_HOURLY_SAFE = 20          # ~5 per 15 min feels natural
MAX_ACCOUNTS_PER_IP = 3         # Google's threshold for suspicious activity

# Warmup: day number -> max emails for that day
WARMUP_SCHEDULE = {
    1: 30,
    2: 60,
    3: 120,
    4: 200,
    5: 300,
    6: 400,     # day 6+ = full capacity
}

# Delay settings (seconds)
MIN_DELAY = 20
MAX_DELAY = 45
BATCH_SIZE = 12
BATCH_PAUSE_MIN = 60
BATCH_PAUSE_MAX = 120


@dataclass
class AccountStatus:
    email: str
    name: str
    is_default: bool
    first_send_date: date | None      # when this account first sent (warmup start)
    warmup_day: int                    # days since first send (0 = never used)
    daily_limit: int                   # effective limit today (warmup-aware)
    hourly_limit: int
    sent_today: int
    sent_this_hour: int
    remaining_today: int
    available: bool                    # can send right now?


@dataclass
class CampaignPlan:
    total_emails: int
    total_capacity_today: int
    can_finish_today: bool
    days_needed: int
    daily_breakdown: list[dict] = field(default_factory=list)
    avg_delay: float = 0.0
    estimated_hours_today: float = 0.0
    accounts_used: int = 0


class AccountManager:
    """Auto-discovers Mail.app accounts, calculates limits from DB history."""

    def __init__(self, accounts: list[dict], stats: dict[str, dict]):
        self._accounts = accounts       # from list_accounts()
        self._stats = stats             # per-account send counts from DB
        self._runtime_counts: dict[str, dict] = {}  # in-session tracking

        for acc in accounts:
            email = acc["email"]
            self._runtime_counts[email] = {
                "hour_start": datetime.now(timezone.utc),
                "hour_count": 0,
                "day_count": 0,
            }

    @classmethod
    async def create(cls, only: list[str] | None = None) -> "AccountManager":
        """Factory: discover accounts + load stats from DB.

        Args:
            only: Whitelist of email addresses to use. If None, uses all Mail.app accounts.
        """
        result = await list_accounts()
        if not result.ok:
            log.warning("Failed to list Mail.app accounts: %s", result.error)
            return cls([], {})

        accounts = [{"email": a.email, "name": a.name, "default": a.default} for a in result.accounts]

        # Whitelist filter
        if only:
            only_set = {e.lower() for e in only}
            accounts = [a for a in accounts if a["email"].lower() in only_set]
        stats = await cls._load_account_stats([a["email"] for a in accounts])

        mgr = cls(accounts, stats)
        log.info(
            "AccountManager: %d accounts, total capacity=%d/day",
            len(accounts), mgr.total_capacity_today(),
        )
        return mgr

    @staticmethod
    async def _load_account_stats(emails: list[str]) -> dict[str, dict]:
        """Load per-account send history from DB."""
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hour_ago = now - timedelta(hours=1)

        stats: dict[str, dict] = {}
        for email in emails:
            # Sent today
            sent_today = await SentEmail.filter(
                from_account=email, status="ok", action="send",
                sent_at__gte=day_start,
            ).count()

            # Sent this hour
            sent_hour = await SentEmail.filter(
                from_account=email, status="ok", action="send",
                sent_at__gte=hour_ago,
            ).count()

            # First ever send date (for warmup calculation)
            first = await SentEmail.filter(
                from_account=email, status="ok", action="send",
            ).order_by("sent_at").first()

            first_date = first.sent_at.date() if first and first.sent_at else None

            stats[email] = {
                "sent_today": sent_today,
                "sent_this_hour": sent_hour,
                "first_send_date": first_date,
            }

        return stats

    def _warmup_day(self, email: str) -> int:
        """How many days since first send (0 = never used)."""
        st = self._stats.get(email, {})
        first = st.get("first_send_date")
        if not first:
            return 0
        return (date.today() - first).days + 1

    def _effective_daily_limit(self, email: str) -> int:
        """Daily limit adjusted for warmup phase."""
        day = self._warmup_day(email)
        if day == 0:
            return WARMUP_SCHEDULE[1]  # first time = warmup day 1
        for d in sorted(WARMUP_SCHEDULE.keys(), reverse=True):
            if day >= d:
                return WARMUP_SCHEDULE[d]
        return WARMUP_SCHEDULE[1]

    def account_status(self, email: str) -> AccountStatus:
        """Full status for a single account."""
        acc = next((a for a in self._accounts if a["email"] == email), None)
        if not acc:
            raise ValueError(f"Unknown account: {email}")

        st = self._stats.get(email, {})
        runtime = self._runtime_counts.get(email, {})

        warmup_day = self._warmup_day(email)
        daily_limit = self._effective_daily_limit(email)

        sent_today = st.get("sent_today", 0) + runtime.get("day_count", 0)
        sent_hour = st.get("sent_this_hour", 0) + runtime.get("hour_count", 0)
        remaining = max(0, daily_limit - sent_today)

        return AccountStatus(
            email=email,
            name=acc.get("name", ""),
            is_default=acc.get("default", False),
            first_send_date=st.get("first_send_date"),
            warmup_day=warmup_day,
            daily_limit=daily_limit,
            hourly_limit=GMAIL_HOURLY_SAFE,
            sent_today=sent_today,
            sent_this_hour=sent_hour,
            remaining_today=remaining,
            available=remaining > 0 and sent_hour < GMAIL_HOURLY_SAFE,
        )

    def accounts_summary(self) -> list[dict]:
        """Summary for all accounts."""
        result = []
        for acc in self._accounts:
            s = self.account_status(acc["email"])
            result.append({
                "email": s.email,
                "name": s.name,
                "warmup_day": s.warmup_day,
                "daily_limit": s.daily_limit,
                "sent_today": s.sent_today,
                "remaining": s.remaining_today,
                "available": s.available,
            })
        return result

    def total_capacity_today(self) -> int:
        """Sum of remaining capacity across all accounts."""
        return sum(
            self.account_status(a["email"]).remaining_today
            for a in self._accounts
        )

    def pick_account(self) -> str | None:
        """Pick a random available account. Returns email or None."""
        now = datetime.now(timezone.utc)

        available = []
        for acc in self._accounts:
            email = acc["email"]
            rt = self._runtime_counts[email]

            # Reset hourly counter if needed
            if (now - rt["hour_start"]).total_seconds() > 3600:
                rt["hour_start"] = now
                rt["hour_count"] = 0

            status = self.account_status(email)
            if status.available:
                available.append(email)

        if not available:
            return None

        return random.choice(available)

    def record_send(self, email: str):
        """Record a send in runtime counters (called after successful send)."""
        rt = self._runtime_counts.get(email)
        if rt:
            rt["hour_count"] += 1
            rt["day_count"] += 1

    def plan_campaign(self, total_emails: int) -> CampaignPlan:
        """Plan how to send N emails: days needed, daily breakdown, estimated time."""
        remaining = total_emails
        day = 0
        breakdown = []

        # Simulate day by day
        while remaining > 0:
            day += 1
            day_capacity = 0

            for acc in self._accounts:
                email = acc["email"]
                warmup = self._warmup_day(email) + day - 1  # future warmup day
                if warmup == 0:
                    warmup = 1

                for d in sorted(WARMUP_SCHEDULE.keys(), reverse=True):
                    if warmup >= d:
                        day_capacity += WARMUP_SCHEDULE[d]
                        break

            sends_today = min(remaining, day_capacity)
            breakdown.append({
                "day": day,
                "capacity": day_capacity,
                "sends": sends_today,
                "remaining_after": remaining - sends_today,
            })
            remaining -= sends_today

            if day > 30:  # safety cap
                break

        # Time estimate for today
        today_sends = breakdown[0]["sends"] if breakdown else 0
        avg_delay = (MIN_DELAY + MAX_DELAY) / 2
        batches = today_sends // BATCH_SIZE
        batch_pause_avg = (BATCH_PAUSE_MIN + BATCH_PAUSE_MAX) / 2
        est_seconds = today_sends * avg_delay + batches * batch_pause_avg

        can_finish_today = len(breakdown) == 1 and breakdown[0]["remaining_after"] == 0

        return CampaignPlan(
            total_emails=total_emails,
            total_capacity_today=self.total_capacity_today(),
            can_finish_today=can_finish_today,
            days_needed=len(breakdown),
            daily_breakdown=breakdown,
            avg_delay=avg_delay,
            estimated_hours_today=est_seconds / 3600,
            accounts_used=len(self._accounts),
        )

    def get_delay_settings(self) -> dict:
        """Return current delay configuration."""
        return {
            "min_delay": MIN_DELAY,
            "max_delay": MAX_DELAY,
            "batch_size": BATCH_SIZE,
            "batch_pause_min": BATCH_PAUSE_MIN,
            "batch_pause_max": BATCH_PAUSE_MAX,
        }
