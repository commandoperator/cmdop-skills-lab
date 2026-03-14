# CLI Commands

Entry point: `server-agent` (installed via `pyproject.toml` scripts).

All commands support `--json` for structured output and `--dry-run` to preview actions without executing.

---

## `check`

Full health check: containers, disk, Redis. Auto-heals safe issues.

```bash
server-agent check [--scope all] [--heal] [--dry-run] [--notify] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--scope` | `all` | Filter containers (not yet implemented, reserved) |
| `--heal` | `True` | Auto-heal safe anomalies |
| `--dry-run` | `False` | Plan actions without executing |
| `--notify` | `True` | Send Telegram alerts for escalations |
| `--json` | `False` | Output `GuardianRun.model_dump()` as JSON |

**What it does:**
1. `docker ps` + `docker stats` — collect all container states and resource usage
2. Detect anomalies (unhealthy, crash loop, high memory/CPU, log errors)
3. For each anomaly: heal (restart) or escalate
4. Check disk usage on all mounts
5. If disk CRITICAL and used >= 90%: `docker system prune -f`
6. Check Redis memory
7. Write incident report for each affected container
8. Send Telegram if any escalations

**Example output (human-readable):**
```
server-agent check
✓ 11 containers checked
⚠ reforms-django: UNHEALTHY — restarted (dry-run)
✓ Disk /: 67% OK
✓ Redis: 128M / 512M (25%)
```

---

## `scan`

Security scan: CVE vulnerabilities, open ports, auth log failures, disk.

```bash
server-agent scan [--scope all] [--baseline] [--notify] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--scope` | `all` | Reserved |
| `--baseline` | `False` | Generate/update `baseline/ports.json` instead of scanning |
| `--notify` | `True` | Send Telegram for CRITICAL findings |
| `--json` | `False` | Output findings list as JSON |

**What it does:**
1. `trivy image` on all unique container images — extracts HIGH/CRITICAL CVEs
2. `ss -tlnp` — compare open ports against `baseline/ports.json`
3. Parse `/var/log/auth.log` or `journalctl` — count SSH failures
4. Check disk usage

**Port baseline workflow:**
```bash
# First time: generate baseline
server-agent scan --baseline
# Edit baseline/ports.json, set reviewed: true for known ports
# Then on every scan: unexpected ports trigger WARNING findings
```

---

## `heal`

Targeted remediation for a specific container.

```bash
server-agent heal --container <name> [--dry-run] [--notify] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--container` | required | Container name (e.g. `reforms-django`) |
| `--dry-run` | `False` | Plan action without executing |
| `--notify` | `True` | Send Telegram if escalated |
| `--json` | `False` | Output `HealAction.model_dump()` as JSON |

**Example:**
```bash
server-agent heal --container reforms-django --dry-run
# → action: restart, command: docker restart reforms-django, escalated: false
```

---

## `report`

Write structured Markdown reports to `$REPORTS_DIR`.

```bash
server-agent report --type <daily|security|status> [--date YYYY-MM-DD] [--notify] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--type` | required | Report type: `daily`, `security`, `status` |
| `--date` | today | Target date for daily report |
| `--notify` | `True` | Send Telegram with report path |
| `--json` | `False` | Output report path as JSON |

**Report types:**
- `daily` — aggregates all check runs for the day, lists incidents and actions
- `security` — summarizes latest scan findings grouped by type
- `status` — current snapshot (same as `status` but written to file)

**Daily report trigger:**
```bash
cmdop trigger add --name "server-agent-daily" --interval 86400 \
  --prompt "Run command: server-agent report --type daily"
```

---

## `status`

Quick server snapshot. No files written, no Telegram.

```bash
server-agent status [--json]
```

Outputs:
- All containers with state and anomaly count
- Disk usage per mount
- Redis memory

**Example:**
```bash
server-agent status --json
{
  "timestamp": "2026-03-14T10:23:00Z",
  "containers": [...],
  "disk": [...],
  "redis": {...}
}
```

Use this to verify the installation works before setting up triggers:
```bash
server-agent status --json | python3 -m json.tool
```

---

## Trigger Setup (Recommended)

```bash
# Health check every 5 min
cmdop trigger add --name "server-agent-check" --interval 300 \
  --prompt "Run command: server-agent check"

# Security scan every 30 min
cmdop trigger add --name "server-agent-scan" --interval 1800 \
  --prompt "Run command: server-agent scan"

# Daily report at midnight
cmdop trigger add --name "server-agent-daily" --interval 86400 \
  --prompt "Run command: server-agent report --type daily"
```

Note: use `"Run command: server-agent check"` — the LLM calls the binary directly via `cmd_execute`. This is faster and cheaper than `"Run skill server-agent check"` which routes through an inner skill session.
