# tg-notify

> **[CMDOP Skill](https://cmdop.com/skills/tg-notify/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install tg-notify
> ```
Rate-limited Telegram notifications with priority queue.

## Install

```bash
pip install tg-notify
```

## Quick Start

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="-1001234567890"
```

```python
from tg_notify import send_telegram_message

send_telegram_message("Hello from tg-notify!")
```

## Shortcuts

```python
from tg_notify import send_error, send_success, send_warning, send_info, send_stats, send_alert

send_error("DB connection failed", {"host": "db.example.com"})
send_success("Deploy complete", {"version": "1.2.3"})
send_warning("Disk usage high", {"usage": "89%"})
send_info("New user registered", {"email": "user@example.com"})
send_stats("Daily Report", {"users": 1500, "revenue": "$3200"})
send_alert("Server down!", {"server": "prod-1"})
```

## TelegramSender

```python
from tg_notify import TelegramSender

sender = TelegramSender(bot_token="your-token", chat_id=-123456)
sender.send_message("Hello!")
sender.send_photo("chart.png", caption="Daily stats")
sender.send_document("report.pdf")
```

## Priority Queue

Messages are queued with 4 priority levels and rate-limited to 20 msg/sec:

| Priority | Use case |
|---|---|
| `CRITICAL` (1) | Security alerts, system down |
| `HIGH` (2) | Errors, important warnings |
| `NORMAL` (3) | Info, success messages |
| `LOW` (4) | Stats, debug |

Auto-cleanup drops low-priority messages when queue fills up.

```python
from tg_notify import telegram_queue

# Flush before exit (CLI scripts)
telegram_queue.flush(timeout=5)
```

## License

MIT
