# Solution

## Problem

A production server running 11 Docker projects needs continuous oversight:

- Containers crash, restart-loop, or go unhealthy at any hour
- Disk fills up silently until something breaks
- CVEs accumulate in images that never get updated
- Unauthorized SSH access attempts go unnoticed
- Incidents have no structured record — no audit trail, no timeline

Manual monitoring is not viable. Hiring dedicated ops for a small fleet is not justified.

## Solution

`server-agent` is a cmdop skill that runs autonomously on the production server. It monitors Docker containers, detects anomalies, heals what is safe to heal, escalates what is risky, and writes structured Markdown reports — all driven by the cmdop agent on a schedule.

```
cmdop agent (daemon)
  ├── trigger every 5 min  → server-agent check
  ├── trigger every 30 min → server-agent scan
  └── trigger every 24 h   → server-agent report --type daily
```

No external monitoring SaaS. No separate infrastructure. One Python package + three triggers.

## Key Design Decisions

### One skill, five commands

Instead of five separate skills (`docker-monitor`, `security-scanner`, `healer`, `reporter`, `notifier`), everything lives in one package with subcommands. Simpler to install, version, and maintain.

### Python CLI, not LLM in the check loop

The scheduled `check` and `scan` commands run as Python processes — no LLM involved. Docker inspection, anomaly detection, and healing decisions are deterministic code. This makes monitoring:
- Fast (no LLM latency on every 5-min check)
- Cheap (no token cost for routine runs)
- Reliable (no hallucinations in production actions)

The LLM enters only when a human types `cmdop run server-agent "investigate this incident"` — then the skill's `readme.md` becomes the system prompt for interactive investigation.

### SAFE / ESCALATE / NEVER autonomy model

The agent never guesses about blast radius. Every possible action is pre-classified:

- **SAFE** — executes without asking: `docker restart`, `docker system prune`
- **ESCALATE** — sends Telegram alert, waits: any action on containers with 2+ restarts, OOM, protected services
- **NEVER** — hardcoded off: database commands, `rm -rf` outside `/tmp`, firewall changes

### Structured Markdown reports

Reports are plain `.md` files in `$REPORTS_DIR/YYYY-MM-DD/`. No database. No proprietary format. Git-friendly, readable in any editor, linkable from Telegram messages.

### tg-notify for notifications, not cmdop_bot

`tg-notify` is a push-only library (send alert → done). `cmdop_bot` provides bidirectional Telegram ↔ agent control but requires a persistent extra process. For a single server with one operator, push notifications are sufficient — the cmdop.com dashboard provides terminal access when interactive control is needed.

## What It Does Not Do

- Does not monitor multiple servers (single-server scope)
- Does not manage deployments or CI/CD
- Does not replace application-level APM (no request traces, no DB query analysis)
- Does not restart databases — `shared-db-redis` and `traefik` are always escalated, never auto-restarted
