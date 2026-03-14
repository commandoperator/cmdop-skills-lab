# Testing

## Running Tests

```bash
# Install dev dependencies (first time)
uv add --dev pytest pytest-asyncio pytest-cov ruff

# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ -v --cov=src/server_agent --cov-report=term-missing

# Run single test file
uv run python -m pytest tests/test_healer.py -v

# Lint
uv run ruff check src/
```

Or via Makefile:

```bash
make test
make lint
```

---

## Test Coverage

**30 tests across 4 files. All tests run without Docker, without a real server.**

### `tests/test_docker.py` — 12 tests

Tests for parsing and log scanning logic. No real Docker calls.

| Test | What it verifies |
|------|-----------------|
| `test_parse_pct` | `"12.5%"` → `12.5`, `"bad"` → `0.0` |
| `test_parse_state_healthy` | `"Up 2 hours (healthy)"` → `HEALTHY` |
| `test_parse_state_unhealthy` | `"Up 5 minutes (unhealthy)"` → `UNHEALTHY` |
| `test_parse_state_restarting` | `"Restarting (1) 3 seconds ago"` → `RESTARTING` |
| `test_parse_state_exited` | `"Exited (1) 2 minutes ago"` → `EXITED` |
| `test_parse_state_running` | `"Up 2 days"` → `RUNNING` |
| `test_scan_logs_no_errors` | INFO-only logs → no CRITICAL anomalies |
| `test_scan_logs_panic` | `"panic: runtime error"` → CRITICAL `log_panic` |
| `test_scan_logs_oom` | `"Killed process ... total-vm"` → CRITICAL |
| `test_scan_logs_connection_refused` | `"Connection refused"` → WARNING |
| `test_scan_logs_5xx` | `"HTTP 500"` → WARNING |
| `test_scan_logs_deduplication` | Same panic line × 20 → only 1 anomaly |

### `tests/test_healer.py` — 6 tests

Tests for heal/escalate decisions. Uses `dry_run=True` throughout — no shell commands executed.

| Test | What it verifies |
|------|-----------------|
| `test_heal_unhealthy_dry_run` | UNHEALTHY → action=restart, escalated=False |
| `test_heal_protected_container` | `shared-db-redis` → always escalated |
| `test_heal_crash_loop_escalated` | restart_count=5 → escalated, reason mentions restarts |
| `test_heal_oom_escalated` | memory_pct=97% → escalated, reason mentions memory |
| `test_heal_healthy_container_monitor` | RUNNING, no anomalies → action=monitor |
| `test_heal_exited_container` | EXITED → action=restart, command=`docker restart reforms-django` |

### `tests/test_models.py` — 7 tests

Tests for model behavior and computed properties.

| Test | What it verifies |
|------|-----------------|
| `test_severity_ordering` | CRITICAL > WARNING > INFO |
| `test_container_info_healthy` | HEALTHY state → `is_healthy=True`, `max_severity=None` |
| `test_container_info_unhealthy` | UNHEALTHY + anomaly → `is_healthy=False`, `max_severity=CRITICAL` |
| `test_container_max_severity_warning` | WARNING anomaly → `max_severity=WARNING` |
| `test_disk_info_severity` | 96% → CRITICAL, 87% → WARNING, 50% → None |
| `test_redis_info_severity` | 92% → CRITICAL, 77% → WARNING |
| `test_guardian_run_summary` | `to_summary()` returns correct counts |

### `tests/test_reporter.py` — 5 tests

Tests for file writing. Uses `tmp_path` fixture — writes to temp directories, no real `$REPORTS_DIR` needed.

| Test | What it verifies |
|------|-----------------|
| `test_write_incident_report` | File exists, contains container name, CRITICAL, RESOLVED, docker command |
| `test_write_incident_report_escalated` | File contains ESCALATED and escalation_reason |
| `test_write_daily_summary` | `daily-summary.md` created, contains date and container names |
| `test_update_index` | `index.md` created, contains day dir and filenames |
| `test_report_file_naming_convention` | Filename matches `HH-MM-incident-reforms-django.md` pattern |

---

## What Is NOT Tested

These require a real server and are verified manually on first deploy:

- `get_containers()` — actual `docker ps` output parsing
- `get_disk_usage()` — actual `df -h` output
- `get_redis_info()` — actual Redis container connection
- `scan_images()` — actual `trivy` execution
- `check_open_ports()` — actual `ss -tlnp` output
- `check_auth_logs()` — actual `journalctl` or `/var/log/auth.log`
- `send_telegram()` — actual Telegram API call
- Live heal (non-dry-run) — actual `docker restart`

**First deploy checklist:**
```bash
# Verify container parsing works on the real server
server-agent status --json

# Verify heal logic before going live
server-agent check --dry-run

# Verify scan works (trivy must be installed)
server-agent scan --json
```
