#!/usr/bin/env python3
"""
Generate personalized outreach emails for OpenClaw developers using SDKRouter.
Uses structured output (Pydantic) + gpt-4.1-nano for fast, cheap generation.
"""

import json
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from sdkrouter import SDKRouter

# Paths
DATA_DIR = Path(__file__).parent / "data"
CONTACTS_FILE = DATA_DIR / "developers.json"
OUTPUT_FILE = DATA_DIR / "personalized_messages.json"

# SDKRouter settings
API_KEY = "test-api-key"
MODEL = "openai/gpt-4.1-nano"
MAX_WORKERS = 10

# Base pitch about OpenClaw / Cmdop
BASE_PITCH = """We're building Cmdop — a new execution layer for agentic and distributed systems. It introduces a persistent session-object architecture where execution state is a first-class primitive, not an external concern handled by queues, logs, or orchestration glue.

Instead of stateless RPC-style control, Cmdop allows execution to persist, migrate, resume, and be inspected across machines — locally or remotely. This makes it possible to build agentic workflows and distributed automation that are long-running, stateful, and deterministic by design.

We're looking for contributors and early adopters who understand the challenges of building reliable agent systems.

If this resonates, I'd love to hear your thoughts or hop on a quick call.

Best,
Mark
Founder, Cmdop
https://cmdop.com

---
If you don't want to hear from me, just reply "unsubscribe" and I won't email again."""


class PersonalizedEmail(BaseModel):
    subject: str = Field(description="Email subject line, max 60 chars. Must feel like a real person wrote it — varied, curious, relevant. No ALL CAPS, no exclamation marks, no generic 'exciting opportunity'. Examples: 'Stateful agents for chatgpt-on-wechat?', 'Quick thought on cc-switch architecture', 'Re: distributed execution for AI tools'")
    greeting: str = Field(description="Short greeting: 'Hi Jason,' or 'Hey Hesam,' — casual dev-to-dev tone")
    hook: str = Field(description="1-2 sentences that show you actually looked at their work. Reference a specific repo, tech choice, or problem they solve. Be technical and genuine, not salesy.")


# Thread-safe counters
lock = threading.Lock()
counters = {"generated": 0, "errors": 0, "processed": 0}


def create_client():
    return SDKRouter(api_key=API_KEY)


def generate_for_contact(client: SDKRouter, contact: dict, total: int) -> dict:
    """Generate personalized email parts for a single contact."""
    name = contact.get("name", "").strip() or contact.get("username", "")
    email = contact.get("email", "")
    bio = contact.get("bio", "")
    org = contact.get("organization", "")
    source_context = contact.get("source_context", "")
    repos = contact.get("repos_public", 0)
    followers = contact.get("followers", 0)

    # Clean source_context for prompt
    clean_source = source_context.replace("owner of ", "").replace(" (topic:openclaw)", "")

    prompt = f"""Personalize a cold outreach email to a developer. Write like a fellow developer, not a marketer.

Contact:
- Name: {name}
- Bio: {bio or 'N/A'}
- Organization: {org or 'N/A'}
- Notable project: {clean_source or 'N/A'}
- Public repos: {repos}, Followers: {followers}

Rules:
- Subject must be unique and specific to THIS person — reference their repo name or tech stack
- Hook must show you actually looked at their project — mention something concrete
- NO generic phrases like "exciting opportunity", "I came across your profile", "impressive work"
- Tone: casual, technical, peer-to-peer"""

    try:
        result = client.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a developer relations specialist writing personalized outreach. Be concise, authentic, technical."},
                {"role": "user", "content": prompt},
            ],
            response_format=PersonalizedEmail,
            temperature=0.7,
            max_tokens=500,
        )

        parsed: PersonalizedEmail = result.choices[0].message.parsed  # type: ignore[assignment]

        # Build full message body
        body = parsed.greeting + "\n\n" + parsed.hook + "\n\n" + BASE_PITCH

        entry = {
            "email": email,
            "username": contact.get("username", ""),
            "name": name,
            "subject": parsed.subject,
            "message": body,
            "status": "generated",
        }

    except Exception as e:
        entry = {
            "email": email,
            "username": contact.get("username", ""),
            "name": name,
            "subject": "",
            "message": "",
            "status": f"error: {e}",
        }

    with lock:
        counters["processed"] += 1
        if entry["status"] == "generated":
            counters["generated"] += 1
            tag = "OK"
        else:
            counters["errors"] += 1
            tag = "ERR"
        print(f"[{counters['processed']}/{total}] {email[:45]:<45} {tag}")

    return entry


def main():
    import sys

    print("=" * 60)
    print("OpenClaw Developer Outreach — Message Generator")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Workers: {MAX_WORKERS}")

    # Load contacts
    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    contacts = [c for c in data["contacts"] if c.get("email") and not c.get("email_sent") and not c.get("bounced")]
    print(f"Contacts with email (unsent): {len(contacts)}")

    if not contacts:
        print("No contacts to process.")
        return

    # Load existing to resume
    existing_emails: set[str] = set()
    existing_messages: list[dict] = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing_messages = json.load(f)
        existing_emails = {m["email"].lower() for m in existing_messages if m.get("status") == "generated"}
    print(f"Already generated: {len(existing_emails)}")

    to_generate = [c for c in contacts if c["email"].lower() not in existing_emails]
    print(f"To generate: {len(to_generate)}")

    if not to_generate:
        print("All messages already generated.")
        return

    # Limit for testing
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
            to_generate = to_generate[:limit]
            print(f"Limited to: {limit}")

    # Confirm
    if "--yes" not in sys.argv:
        resp = input(f"\nGenerate {len(to_generate)} messages? (yes/no): ").strip().lower()
        if resp != "yes":
            print("Aborted.")
            return
    else:
        print(f"\nGenerating {len(to_generate)} messages (--yes flag)...")

    client = create_client()
    total = len(to_generate)
    results = list(existing_messages)

    print(f"\nStarting generation with {MAX_WORKERS} threads...\n")
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(generate_for_contact, client, c, total): c for c in to_generate}
        try:
            for future in as_completed(futures):
                entry = future.result()
                results.append(entry)
                # Save every 10
                if counters["processed"] % 10 == 0:
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving progress...")
            pool.shutdown(wait=False, cancel_futures=True)

    # Final save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"Generated: {counters['generated']}, Errors: {counters['errors']}")
    if elapsed > 0:
        print(f"Speed: {counters['processed']/elapsed:.1f} messages/sec")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
