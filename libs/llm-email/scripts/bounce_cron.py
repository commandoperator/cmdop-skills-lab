#!/usr/bin/env python3
"""
Cron job: scan Mail.app for bounces AND replies.
Sends Telegram notifications for new events.
Runs via launchd every hour.

Usage:
    python bounce_cron.py          # scan last 1 day
    python bounce_cron.py --days 3
"""

import asyncio
import sys
from datetime import datetime

from llm_email.db import init_db, close_db
from llm_email.bounces import scan_bounces, bounce_stats
from llm_email.replies import scan_replies, reply_stats
from llm_email.notify import notify_replies, notify_bounces


async def run(days: int):
    await init_db()
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- Bounce scan ---
        print(f"[{ts}] Bounce scan (last {days} day(s))...")
        b_result = await scan_bounces(days=days, use_llm=False)
        if b_result["new_bounces"] > 0:
            print(f"  NEW bounces: {b_result['new_bounces']}")
            for b in b_result["details"]:
                print(f"    {b['email']} ({b['type']}) — {b['reason']}")
            notify_bounces(b_result["details"])

        b_stats = await bounce_stats()
        print(f"  Bounces total: {b_stats['total']} (hard={b_stats['hard']}, soft={b_stats['soft']})")

        # --- Reply scan ---
        print(f"[{ts}] Reply scan (last {days} day(s))...")
        r_result = await scan_replies(days=days, use_llm=True)
        if r_result["new_replies"] > 0:
            print(f"  NEW replies: {r_result['new_replies']}")
            for r in r_result["details"]:
                emoji = {"interested": "!!!", "ooo": "OOO", "unsubscribe": "UNSUB",
                         "not_relevant": "PASS", "other": "---"}.get(r["type"], "---")
                redirect = f" -> {r['redirect']}" if r.get("redirect") else ""
                print(f"    [{emoji}] {r['from']} — {r['summary']}{redirect}")
            notify_replies(r_result["details"])

        r_stats = await reply_stats()
        print(f"  Replies total: {r_stats['total']} "
              f"(interested={r_stats['interested']}, ooo={r_stats['ooo']}, "
              f"unsub={r_stats['unsubscribe']}, pass={r_stats['not_relevant']}, "
              f"unhandled={r_stats['unhandled']})")

        print(f"[{ts}] Done.")

    finally:
        await close_db()


def main():
    days = 1
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    asyncio.run(run(days))


if __name__ == "__main__":
    main()
