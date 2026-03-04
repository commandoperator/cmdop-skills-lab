# tg-notify

Rate-limited Telegram notification service with priority queue.

Send messages, photos, and documents via Telegram Bot API with built-in rate limiting (20 msg/sec) and 4-level priority queue (CRITICAL > HIGH > NORMAL > LOW).

## Quick Start

```python
from tg_notify import send_telegram_message, send_error, send_success

# Simple message (uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars)
send_telegram_message("Hello!")

# Formatted notifications
send_error("Database connection failed", {"host": "db.example.com"})
send_success("Deploy complete", {"version": "1.2.3"})
```

## Features

- Priority queue with rate limiting (20 msg/sec)
- Auto-cleanup when queue is full (drops low priority first)
- Shortcuts: `send_error`, `send_success`, `send_warning`, `send_info`, `send_stats`, `send_alert`
- Custom bot token / chat ID per call
- Photos and documents support
- Fail-silently mode for graceful degradation

## Environment Variables

- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather
- `TELEGRAM_CHAT_ID` — Default chat/group/channel ID
