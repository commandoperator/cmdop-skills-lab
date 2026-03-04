#!/usr/bin/env python3
"""
llm-email skill runner — send emails via macOS Mail.app AppleScript.

Subcommands:
    send     Send an email immediately
    draft    Create a draft in Mail.app
    accounts List available Mail.app accounts
    health   Check if Mail.app is available
    status   Show recent sent email log
    stats    Show extended email statistics
"""

import argparse
import asyncio
import json
import sys

from llm_email.db import init_db, close_db
from llm_email.mailer import send_email, list_accounts, check_health, show_status, show_stats


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

        elif args.command == "health":
            result = check_health()
            json_output(**result)

        elif args.command == "status":
            result = await show_status()
            json_output(**result)

        elif args.command == "stats":
            result = await show_stats()
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

    # health
    sub.add_parser("health", help="Check Mail.app availability")

    # status
    sub.add_parser("status", help="Show recent sent log")

    # stats
    sub.add_parser("stats", help="Show extended statistics")

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
