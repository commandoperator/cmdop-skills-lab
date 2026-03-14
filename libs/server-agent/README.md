# server-agent

> **[CMDOP Skill](https://cmdop.com/skills/server-agent/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install server-agent
> ```
Universal production server monitoring, self-healing, and reporting skill for [cmdop](https://cmdop.com).

Watches over Docker containers, detects anomalies, heals what is safe to heal, scans for vulnerabilities, and writes structured Markdown reports — all driven by the cmdop agent.

## Quick Start

```bash
# Install
pip install -e .
cmdop skills install .

# Quick status check
server-agent status

# Full health check (auto-heals safe issues)
server-agent check

# Security scan
server-agent scan

# Heal a specific container
server-agent heal --container reforms-django

# Daily report
server-agent report --type daily
```

## Commands

| Command | Description |
|---------|-------------|
| `check` | Full health check: containers, disk, Redis. Auto-heals safe issues. |
| `scan` | Security scan: trivy CVEs, open ports, auth logs. |
| `heal` | Targeted remediation for a specific container. |
| `report` | Write structured MD reports (daily, security). |
| `status` | Quick server snapshot — no files written. |

All commands support `--json` for structured output and `--dry-run` to preview actions without executing them.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `REPORTS_DIR` | yes | Absolute path to reports directory |
| `TELEGRAM_BOT_TOKEN` | no | Bot token for Telegram notifications |
| `TELEGRAM_CHAT_ID` | no | Target chat/channel ID |

## Autonomy Model

- **SAFE** (executes immediately): `docker restart`, `docker system prune`
- **ESCALATE** (sends Telegram alert): image rebuild, config changes, containers with >2 restarts, OOM
- **NEVER**: database commands, `rm -rf` outside `/tmp`, firewall changes

Protected containers (never auto-restarted): `shared-db-redis`, `traefik`

## Setup on Production Server

```bash
# 1. Install
pip install server-agent
cmdop skills install server-agent

# 2. Set environment
export REPORTS_DIR=/root/server-agent/reports
export TELEGRAM_BOT_TOKEN=<token>
export TELEGRAM_CHAT_ID=<chat_id>

# 3. Verify
server-agent status --json

# 4. Generate port baseline
server-agent scan --baseline
# Review baseline/ports.json, then set reviewed: true

# 5. Start cmdop agent
cmdop agent start

# 6. Register triggers
cmdop trigger add --name "server-agent-check" --interval 300 \
  --prompt "Run command: server-agent check"

cmdop trigger add --name "server-agent-scan" --interval 1800 \
  --prompt "Run command: server-agent scan"

cmdop trigger add --name "server-agent-daily" --interval 86400 \
  --prompt "Run command: server-agent report --type daily"
```

## Two Modes of Operation

### Scheduled monitoring (Python CLI)

Triggers call `server-agent` binary directly. No LLM in the check loop — fast, deterministic, cheap.

```bash
# Runs every 5 min via trigger
server-agent check
```

### Interactive investigation (cmdop skill)

Use when you need the agent to reason about an incident:

```bash
cmdop run server-agent "reforms-django keeps restarting, investigate and fix"
```

The agent reads `skill/readme.md` as its system prompt and uses `server-agent` CLI as a tool to gather data and take action.

## Reports Structure

```
$REPORTS_DIR/
  index.md
  baseline/ports.json
  2026-03-14/
    10-23-incident-reforms-django.md
    14-05-security-scan.md
    daily-summary.md
```
