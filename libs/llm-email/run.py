#!/usr/bin/env python3
"""
llm-email skill runner — send emails via macOS Mail.app AppleScript.

Subcommands:
    send            Send an email immediately
    draft           Create a draft in Mail.app
    accounts        List available Mail.app accounts
    accounts-status Per-account limits, warmup day, capacity
    health          Check if Mail.app is available
    status          Show recent sent email log
    stats           Show extended email statistics
    plan            Plan a campaign (how long to send N emails)
    bounces-check   Scan Mail.app for bounce messages
    bounces-list    List all detected bounces
    bounces-stats   Bounce statistics
"""

import argparse
import asyncio
import json
import sys

from llm_email.db import init_db, close_db
from llm_email.mailer import send_email, list_accounts, check_health, show_status, show_stats
from llm_email.account_manager import AccountManager
from llm_email.bounces import scan_bounces, get_bounced_emails, bounce_stats
from llm_email.replies import scan_replies, get_replies, reply_stats


def json_output(ok: bool, **kwargs):
    """Print JSON result and exit."""
    result = {"ok": ok, **kwargs}
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if ok else 1)


async def main_async(args: argparse.Namespace):
    """Async entry point: init DB -> dispatch -> close DB."""
    await init_db()
    try:
        if args.command == "send":
            result = await send_email(
                to=args.to, subject=args.subject, body=args.body,
                from_account=args.from_account, cc=args.cc, bcc=args.bcc,
            )
            json_output(**result)

        elif args.command == "draft":
            result = await send_email(
                to=args.to, subject=args.subject, body=args.body,
                from_account=args.from_account, draft_only=True,
            )
            json_output(**result)

        elif args.command == "accounts":
            result = await list_accounts()
            json_output(**result)

        elif args.command == "accounts-status":
            mgr = await AccountManager.create()
            summary = mgr.accounts_summary()
            json_output(ok=True, total_capacity=mgr.total_capacity_today(), accounts=summary)

        elif args.command == "health":
            result = check_health()
            json_output(**result)

        elif args.command == "status":
            result = await show_status()
            json_output(**result)

        elif args.command == "stats":
            result = await show_stats()
            json_output(**result)

        elif args.command == "plan":
            mgr = await AccountManager.create()
            plan = mgr.plan_campaign(args.count)
            json_output(
                ok=True,
                total_emails=plan.total_emails,
                capacity_today=plan.total_capacity_today,
                can_finish_today=plan.can_finish_today,
                days_needed=plan.days_needed,
                estimated_hours_today=round(plan.estimated_hours_today, 1),
                accounts_used=plan.accounts_used,
                daily_breakdown=plan.daily_breakdown,
            )

        elif args.command == "bounces-check":
            result = await scan_bounces(days=args.days, use_llm=not args.no_llm)
            json_output(**result)

        elif args.command == "bounces-list":
            bounces = await get_bounced_emails()
            json_output(ok=True, count=len(bounces), bounces=bounces)

        elif args.command == "bounces-stats":
            result = await bounce_stats()
            json_output(**result)

        elif args.command == "replies-check":
            result = await scan_replies(days=args.days, use_llm=not args.no_llm)
            json_output(**result)

        elif args.command == "replies-list":
            rtype = getattr(args, "type", None)
            replies = await get_replies(reply_type=rtype, limit=args.limit)
            json_output(ok=True, count=len(replies), replies=replies)

        elif args.command == "replies-stats":
            result = await reply_stats()
            json_output(**result)

    finally:
        await close_db()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments and return namespace (or exit on missing subcommand)."""
    parser = argparse.ArgumentParser(description="llm-email skill runner")
    sub = parser.add_subparsers(dest="command")

    # send
    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body", required=True)
    p_send.add_argument("--from", dest="from_account", default="")
    p_send.add_argument("--cc", default="")
    p_send.add_argument("--bcc", default="")

    # draft
    p_draft = sub.add_parser("draft", help="Create a draft in Mail.app")
    p_draft.add_argument("--to", required=True)
    p_draft.add_argument("--subject", required=True)
    p_draft.add_argument("--body", required=True)
    p_draft.add_argument("--from", dest="from_account", default="")

    # accounts
    sub.add_parser("accounts", help="List Mail.app accounts")

    # accounts-status
    sub.add_parser("accounts-status", help="Per-account limits, warmup, capacity")

    # health
    sub.add_parser("health", help="Check Mail.app availability")

    # status
    sub.add_parser("status", help="Show recent sent log")

    # stats
    sub.add_parser("stats", help="Show extended statistics")

    # plan
    p_plan = sub.add_parser("plan", help="Plan campaign: estimate days for N emails")
    p_plan.add_argument("count", type=int, help="Total emails to send")

    # bounces-check
    p_bc = sub.add_parser("bounces-check", help="Scan Mail.app for bounce messages")
    p_bc.add_argument("--days", type=int, default=7, help="Scan last N days (default: 7)")
    p_bc.add_argument("--no-llm", action="store_true", help="Use regex-only detection (no LLM)")

    # bounces-list
    sub.add_parser("bounces-list", help="List all detected bounces")

    # bounces-stats
    sub.add_parser("bounces-stats", help="Bounce statistics")

    # replies-check
    p_rc = sub.add_parser("replies-check", help="Scan Mail.app for replies to outreach")
    p_rc.add_argument("--days", type=int, default=1, help="Scan last N days (default: 1)")
    p_rc.add_argument("--no-llm", action="store_true", help="Use regex-only classification")

    # replies-list
    p_rl = sub.add_parser("replies-list", help="List detected replies")
    p_rl.add_argument("--type", choices=["interested", "ooo", "unsubscribe", "not_relevant", "other"])
    p_rl.add_argument("--limit", type=int, default=50)

    # replies-stats
    sub.add_parser("replies-stats", help="Reply statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    return args


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
