# llm-email

> **[CMDOP Skill](https://cmdop.com/skills/llm-email/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install llm-email
> ```
Send emails via macOS Mail.app — compose, draft, send with AppleScript.

## Install

```bash
pip install llm-email
```

## Quick Start

```python
from llm_email import send_email, init_db, close_db

await init_db()
result = await send_email(
    to="user@example.com",
    subject="Hello",
    body="Message body",
)
print(result)  # {"ok": True, "action": "send", ...}
await close_db()
```

## CLI

```bash
python run.py send --to "a@b.com" --subject "Hello" --body "Message"
python run.py draft --to "a@b.com" --subject "Hello" --body "Message"
python run.py accounts
python run.py health
python run.py status
python run.py stats
```

All commands output JSON. Parse the `ok` field to check success.

## Dashboard

```bash
email-dashboard
```

## API

```python
from llm_email import (
    send_email,      # send or draft an email
    list_accounts,   # list Mail.app accounts
    check_health,    # check if Mail.app is running
    show_status,     # recent sent email log
    show_stats,      # extended statistics
    check_duplicate, # deduplication check
)
```

## License

MIT
