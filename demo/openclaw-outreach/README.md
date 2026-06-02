# OpenClaw Developer Outreach

Personalized email outreach to developers from the OpenClaw ecosystem.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### 1. Generate personalized messages

```bash
# Test with 5 contacts
python generate_messages.py --limit 5 --yes

# Generate all
python generate_messages.py --yes
```

### 2. Send emails via Mail.app

```bash
# Test mode (edit TEST_EMAIL in send_emails.py)
python send_emails.py --yes

# Production
python send_emails.py
```

## Data

- `data/developers.json` — 3,553 developer contacts from GitHub (topic:openclaw)
- `data/personalized_messages.json` — generated messages (resume-capable)
- `data/send_log.txt` — sending history

## Architecture

- **generate_messages.py** — SDKRouter + structured output (Pydantic) + gpt-4.1-nano
- **send_emails.py** — Mail.app via AppleScript, multi-account rotation, anti-spam delays
