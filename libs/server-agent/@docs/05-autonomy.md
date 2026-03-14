# Autonomy Model

Every action the agent can take is pre-classified into one of three tiers. This classification is hardcoded in `_healer.py` — the agent cannot override it.

---

## SAFE — Executes Immediately

No confirmation needed. Executed in both live and scheduled modes.

| Action | Command | When |
|--------|---------|------|
| Restart container | `docker restart <name>` | State is UNHEALTHY, EXITED, or RESTARTING — AND restart_count < 2 |
| Prune Docker | `docker system prune -f` | Disk mount `/` is CRITICAL AND used >= 90% |

---

## ESCALATE — Sends Telegram, Does Not Act

The agent detects the issue, writes a report marked `[ESCALATED]`, sends a Telegram alert, and stops. No automatic action is taken.

| Condition | Reason |
|-----------|--------|
| Container is in **protected list** | Services where a wrong restart causes data loss or network disruption |
| `restart_count >= 2` | Repeated restarts suggest a deeper problem — restart would just loop again |
| `memory_pct >= 95%` | OOM condition — restarting won't fix the root cause, memory limits need review |
| Any **CRITICAL** CVE found by trivy | Requires human decision on image update |
| Unexpected **open port** detected | Potential intrusion — requires human review |
| SSH auth failures >= 20 in recent logs | Possible brute-force attack |

---

## NEVER — Hardcoded Off

These actions are never taken regardless of what the LLM or any command says.

- Database commands (`psql`, `redis-cli FLUSHALL`, `mongodump`, etc.)
- `rm -rf` outside `/tmp`
- Firewall changes (`iptables`, `ufw`)
- Stopping or removing containers (only restart is allowed)
- Writing to container volumes directly

---

## Protected Containers

```python
PROTECTED_CONTAINERS = {"shared-db-redis", "traefik"}
```

These containers are always escalated, never auto-restarted:

- **`shared-db-redis`** — shared Redis used by all 11 projects. Restarting it without coordination would break active sessions across every service simultaneously.
- **`traefik`** — reverse proxy and TLS terminator. Restarting it drops all incoming traffic.

To add more protected containers, edit `_healer.py:PROTECTED_CONTAINERS`.

---

## Restart Threshold

```python
MAX_AUTO_RESTARTS = 2
```

If `restart_count >= MAX_AUTO_RESTARTS`, the container is escalated instead of restarted. Rationale: if a container has already been restarted twice and is still failing, another restart will not fix it — something in the application or configuration is broken and requires human attention.

---

## `--dry-run` Flag

All commands support `--dry-run`. In dry-run mode:
- All actions are planned and logged
- No `docker` commands are executed
- Reports are written as normal (marked `[DRY RUN]`)
- Telegram is sent as normal

Use dry-run for the first deploy to verify heal logic before enabling live execution:

```bash
server-agent check --dry-run
```
