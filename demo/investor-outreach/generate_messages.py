#!/usr/bin/env python3
"""
Generate personalized investor outreach emails using SDKRouter.
Structured output + gpt-4.1-nano. Tailored to each investor's thesis.
"""

import csv
import json
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from sdkrouter import SDKRouter

DATA_DIR = Path(__file__).parent / "data"
CSV_FILE = DATA_DIR / "investors.csv"
OUTPUT_FILE = DATA_DIR / "personalized_messages.json"

API_KEY = "test-api-key"
MODEL = "openai/gpt-4.1-nano"
MAX_WORKERS = 10

# Pitch context (extracted from deck)
PITCH_CONTEXT = """Cmdop — AI Agents That Actually Work.

OpenClaw went viral (344K GitHub stars), but it's broken: single-machine only, no NAT traversal, breaking updates, no enterprise features. 14,000+ open issues.

Cmdop solves this with a Client-Relay-Agent architecture:
- Agents connect outbound from YOUR servers (no inbound ports, works through any firewall)
- Relay handles auth, encryption, routing
- Single binary: pip install cmdop-agent (no Docker)
- 1 to 1000 servers, managed from anywhere

Platform: Bot (Telegram/Discord/Slack) + SDK (Python/Node.js) + CLI + Desktop/Mobile Apps.
5 lines of code: from pip install to managing 100 servers.

Market: $40B+ TAM ($25B DevOps Automation + $15B AI Agent Infrastructure + 100M+ servers worldwide)
Wedge: OpenClaw refugees (344K stars = massive demand, 14K issues = frustrated users) + DevOps teams (10-100 servers)
Business model: SaaS (Free → $29/mo Pro → $99/mo Team → Enterprise)
Metrics: $0 CAC (organic), 85% gross margin, 5% free-to-paid target, 110% NRR target

Go-to-market: Land & Expand
- Phase 1 (Now-M6): OpenClaw refugees — migration guides, feature comparisons
- Phase 2 (M6-M12): DevOps teams — Telegram bot virality, DevRel
- Phase 3 (M12-M18): Enterprise — on-prem relay, SOC2/GDPR

Traction: MVP ready. Core architecture proven. Client-Relay-Agent working. NAT traversal, multi-server fleet, Telegram bot, Python SDK v0.1.

Team: Igor K. (CEO, 24+ years dev, SaaS architect) + Evgeniy S. (CTO, 15+ years, distributed systems/crypto/trading)

The Ask: $7-10M Seed. 30+ month runway to Series A.
Use: Engineering 50%, Go-To-Market 30%, Operations 20%
Milestones: M6=5K agents, M12=25K agents/$500K ARR, M18=100K agents/$2M ARR

Pitch deck: https://pitch.cmdop.com/"""


BASE_EMAIL = """{investor_hook}

{pitch_summary}

We're raising a $7-10M seed to build Cmdop into the infrastructure layer for AI agents — the production-grade alternative to OpenClaw.

Pitch deck: https://pitch.cmdop.com/

Would love 20 minutes to walk you through the architecture and traction. Happy to work around your schedule.

Best,
Mark
Cmdop | https://cmdop.com

---
If you'd prefer not to hear from me, just reply "unsubscribe"."""


class InvestorEmail(BaseModel):
    subject: str = Field(description="Email subject, max 50 chars. Must feel personal, not mass-mailed. Reference their fund name or thesis. No 'exciting opportunity', no exclamation marks. Examples: 'Cmdop — the missing infra for AI agents', 'Quick note re: your AI infrastructure thesis', 'OpenClaw's 344K stars, zero production users'")
    investor_hook: str = Field(description="1-2 sentences explaining WHY this investor specifically. Start with 'I'm reaching out because...' or 'I noticed that...'. Reference their fund's thesis, a portfolio company, or their known focus area. Do NOT start with the investor's name or 'Given'. Be specific and genuine.")
    pitch_summary: str = Field(description="2-3 sentences summarizing Cmdop tailored to this investor's interests. If they focus on DevTools, emphasize the SDK. If AI infra, emphasize the agent architecture. If enterprise, emphasize the SaaS model.")


lock = threading.Lock()
counters = {"generated": 0, "errors": 0, "processed": 0}


def generate_for_investor(client: SDKRouter, contact: dict, total: int) -> dict:
    name = contact.get("Name", "").strip()
    email = contact.get("Email", "").strip()
    company = contact.get("Company", "").strip()
    role = contact.get("Role", "").strip()
    focus = contact.get("Focus", "").strip()

    prompt = f"""Personalize a seed-stage fundraising email to a VC investor.

Investor:
- Name: {name}
- Fund: {company}
- Role: {role or 'Partner'}
- Focus/Thesis: {focus or 'Tech/AI'}

Company context:
{PITCH_CONTEXT}

Rules:
- Subject must reference their fund name or thesis — NOT generic
- Hook must explain why THIS investor specifically (their thesis, a portfolio company overlap, their known interest)
- Pitch summary: 2-3 sentences tailored to their focus area
- Tone: confident founder, not desperate. Peer-to-peer.
- NO fluff words like "exciting", "revolutionary", "game-changing"
- Be concise — investors read 100 emails/day"""

    try:
        result = client.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are helping a technical founder write personalized investor outreach. Be concise, specific, and confident."},
                {"role": "user", "content": prompt},
            ],
            response_format=InvestorEmail,
            temperature=0.7,
            max_tokens=600,
        )

        parsed: InvestorEmail = result.choices[0].message.parsed  # type: ignore[assignment]

        body = BASE_EMAIL.format(
            investor_hook=parsed.investor_hook,
            pitch_summary=parsed.pitch_summary,
        )

        greeting = f"Hi {name.split()[0]}," if name else f"Hi {company} team,"

        entry = {
            "email": email,
            "name": name,
            "company": company,
            "focus": focus,
            "subject": parsed.subject,
            "message": greeting + "\n\n" + body,
            "status": "generated",
        }

    except Exception as e:
        entry = {
            "email": email,
            "name": name,
            "company": company,
            "focus": focus,
            "subject": "",
            "message": "",
            "status": f"error: {e}",
        }

    with lock:
        counters["processed"] += 1
        tag = "OK" if entry["status"] == "generated" else "ERR"
        if tag == "OK":
            counters["generated"] += 1
        else:
            counters["errors"] += 1
        print(f"[{counters['processed']}/{total}] {name:<25} {company:<20} {tag}")

    return entry


def main():
    import sys

    print("=" * 60)
    print("Investor Outreach — Message Generator")
    print("=" * 60)
    print(f"Model: {MODEL}")

    # Load unsent investors
    contacts = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Sent", "").lower() == "yes":
                continue
            if not row.get("Email", "").strip():
                continue
            contacts.append(row)

    print(f"Unsent investors: {len(contacts)}")

    if not contacts:
        print("All investors already contacted.")
        return

    # Load existing
    existing_emails: set[str] = set()
    existing: list[dict] = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
        existing_emails = {m["email"].lower() for m in existing if m.get("status") == "generated"}

    to_generate = [c for c in contacts if c["Email"].lower() not in existing_emails]
    print(f"To generate: {len(to_generate)}")

    if not to_generate:
        print("All messages already generated.")
        return

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            to_generate = to_generate[:int(sys.argv[idx + 1])]
            print(f"Limited to: {len(to_generate)}")

    if "--yes" not in sys.argv:
        resp = input(f"\nGenerate {len(to_generate)} messages? (yes/no): ").strip().lower()
        if resp != "yes":
            print("Aborted.")
            return

    client = SDKRouter(api_key=API_KEY)
    total = len(to_generate)
    results = list(existing)

    print(f"\nGenerating with {MAX_WORKERS} threads...\n")
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(generate_for_investor, client, c, total): c for c in to_generate}
        try:
            for future in as_completed(futures):
                results.append(future.result())
        except KeyboardInterrupt:
            print("\nInterrupted! Saving...")
            pool.shutdown(wait=False, cancel_futures=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s — Generated: {counters['generated']}, Errors: {counters['errors']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
