# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────┐
│                  Production Server                   │
│                                                      │
│  cmdop agent (daemon)                                │
│    ├── TriggerScheduler                              │
│    │     ├── every 300s  → server-agent check        │
│    │     ├── every 1800s → server-agent scan         │
│    │     └── every 86400s→ server-agent report daily │
│    └── ChatAgent (for interactive cmdop run)         │
│                                                      │
│  server-agent (Python package)                       │
│    ├── _skill.py      ← CLI entry point (5 commands) │
│    ├── _docker.py     ← Docker inspection            │
│    ├── _healer.py     ← Remediation logic            │
│    ├── _security.py   ← CVE / ports / auth scanning  │
│    ├── _reporter.py   ← Markdown report writing      │
│    └── _models.py     ← Pydantic data models         │
│                                                      │
│  Docker Engine                                       │
│    └── 11 project containers + shared services       │
│                                                      │
│  $REPORTS_DIR/                                       │
│    └── Markdown reports, index, port baseline        │
└─────────────────────────────────────────────────────┘
                         │ Telegram
                         ▼
                   tg-notify → your phone
```

## Module Map

| Module | Responsibility | Key functions |
|--------|---------------|---------------|
| `_models.py` | Data structures | `ContainerInfo`, `GuardianRun`, `HealAction`, `SecurityFinding` |
| `_docker.py` | Docker inspection | `get_containers()`, `scan_logs_for_errors()`, `get_disk_usage()`, `get_redis_info()` |
| `_healer.py` | Remediation decisions | `heal_container()`, `prune_docker()` |
| `_security.py` | Security scanning | `scan_images()`, `check_open_ports()`, `check_auth_logs()` |
| `_reporter.py` | Report writing + notifications | `write_incident_report()`, `write_daily_summary()`, `update_index()`, `send_telegram()` |
| `_skill.py` | CLI entry point | `check()`, `scan()`, `heal()`, `report()`, `status()` |

## Data Flow — `check` Command

```
server-agent check
       │
       ▼
_docker.get_containers()
  docker ps --format json
  docker stats --no-stream
  docker inspect (restart count)
       │
       ▼
_docker._detect_anomalies()
  unhealthy state?
  restart_count >= 3?
  memory_pct >= 95%?
  cpu_pct >= 95%?
       │
       ▼
_docker.get_container_logs() + scan_logs_for_errors()
  panic / FATAL / OOM / 5xx / timeout
       │
       ▼
GuardianRun (aggregated result)
       │
       ├── anomalies found?
       │       ▼
       │   _healer.heal_container()
       │     protected? → escalate
       │     restart_count >= 2? → escalate
       │     OOM? → escalate
       │     else → docker restart (SAFE)
       │       │
       │       ├── healed → write_incident_report() [RESOLVED]
       │       └── escalated → write_incident_report() [ESCALATED]
       │                     + send_telegram()
       │
       └── disk CRITICAL + used >= 90%?
               ▼
           prune_docker()
```

## Data Flow — `scan` Command

```
server-agent scan
       │
       ├── scan_images()     → trivy image <name> --format json
       ├── check_open_ports() → ss -tlnp, compare to baseline/ports.json
       ├── check_auth_logs()  → journalctl / /var/log/auth.log
       └── check_disk()       → df -h
       │
       ▼
SecurityReport (list of SecurityFinding)
       │
       ├── write_security_report()
       └── send_telegram() if CRITICAL findings
```

## Two Execution Modes

### Mode 1 — Scheduled CLI (via trigger)

```
cmdop trigger fires
  → AgentService.RunChatAgent("Run command: server-agent check")
  → LLM calls cmd_execute("server-agent check")
  → Python process runs, no LLM in the check loop
  → Results written to $REPORTS_DIR/
  → Telegram sent if needed
```

### Mode 2 — Interactive Investigation (via `cmdop run`)

```
cmdop run server-agent "reforms-django keeps crashing"
  → skill/readme.md becomes LLM system prompt
  → LLM calls cmd_execute("server-agent status --json")
  → LLM reads JSON output, reasons about it
  → LLM calls cmd_execute("server-agent heal --container reforms-django --dry-run")
  → LLM explains findings and actions taken
```

## Directory Structure

```
server-agent/
  pyproject.toml          ← package, entry point: server-agent = server_agent._skill:main
  Makefile                ← make install / test / lint / skill-install
  README.md               ← user-facing documentation
  skill/
    readme.md             ← LLM system prompt (used in Mode 2)
    config.py             ← SkillConfig() auto-read from pyproject.toml
  src/server_agent/
    __init__.py
    _models.py
    _docker.py
    _healer.py
    _reporter.py
    _security.py
    _skill.py
  tests/
    test_models.py
    test_docker.py
    test_healer.py
    test_reporter.py
  @docs/                  ← this documentation
```
