# Data Models

All models are Pydantic v2. Source: `src/server_agent/_models.py`.

---

## `Severity`

```python
class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING  = "warning"
    INFO     = "info"
```

Ordering: `CRITICAL > WARNING > INFO`. Used on `Anomaly`, `SecurityFinding`, `DiskInfo`, `RedisInfo`.

---

## `ContainerState`

```python
class ContainerState(str, Enum):
    HEALTHY    = "healthy"
    UNHEALTHY  = "unhealthy"
    RESTARTING = "restarting"
    RUNNING    = "running"
    EXITED     = "exited"
    DEAD       = "dead"
    UNKNOWN    = "unknown"
```

Parsed from `docker ps` status string by `_docker._parse_state()`.

| Status string | State |
|---|---|
| `Up ... (healthy)` | `HEALTHY` |
| `Up ... (unhealthy)` | `UNHEALTHY` |
| `Restarting ...` | `RESTARTING` |
| `Exited ...` | `EXITED` |
| `Up ...` (no health) | `RUNNING` |

---

## `Anomaly`

```python
class Anomaly(BaseModel):
    type: str                          # e.g. "unhealthy", "crash_loop", "memory_critical"
    severity: Severity
    detail: str                        # human-readable description
    recommended_action: str = ""       # optional hint
```

Created by `_docker._detect_anomalies()` and `_docker.scan_logs_for_errors()`.

**Anomaly types:**

| Type | Severity | Trigger |
|------|----------|---------|
| `unhealthy` | CRITICAL | docker healthcheck failing |
| `crash_loop` | CRITICAL | state = RESTARTING |
| `exited` | CRITICAL | state = EXITED |
| `memory_critical` | CRITICAL | memory_pct >= 95% |
| `cpu_critical` | CRITICAL | cpu_pct >= 95% |
| `restart_loop` | WARNING | restart_count >= 3 |
| `memory_high` | WARNING | memory_pct >= 85% |
| `cpu_high` | WARNING | cpu_pct >= 85% |
| `log_panic` | CRITICAL | "panic:" in logs |
| `log_fatal` | CRITICAL | "FATAL" / "fatal error" in logs |
| `log_oom` | CRITICAL | "Killed process" / "out of memory" in logs |
| `log_segfault` | CRITICAL | "segfault" / "SIGSEGV" in logs |
| `log_5xx` | WARNING | HTTP 5xx in logs |
| `log_connection_error` | WARNING | "Connection refused" in logs |
| `log_timeout` | WARNING | "timed out" / "deadline exceeded" in logs |

---

## `ContainerInfo`

```python
class ContainerInfo(BaseModel):
    name: str
    image: str
    status: str                        # raw docker ps status string
    state: ContainerState
    restart_count: int = 0
    memory_pct: float = 0.0           # percentage 0-100
    cpu_pct: float = 0.0
    anomalies: list[Anomaly] = []

    @property
    def is_healthy(self) -> bool: ...

    @property
    def max_severity(self) -> Severity | None: ...
```

---

## `DiskInfo`

```python
class DiskInfo(BaseModel):
    mount: str                         # e.g. "/"
    used_pct: float                    # percentage 0-100
    used: str                          # human string e.g. "42G"
    total: str                         # e.g. "100G"

    @property
    def severity(self) -> Severity | None:
        # >= 95% → CRITICAL
        # >= 85% → WARNING
        # else   → None
```

---

## `RedisInfo`

```python
class RedisInfo(BaseModel):
    used_memory_human: str             # e.g. "128.5M"
    max_memory_human: str              # e.g. "512M"
    memory_pct: float                  # used / max * 100
    connected_clients: int = 0

    @property
    def severity(self) -> Severity | None:
        # >= 90% → CRITICAL
        # >= 75% → WARNING
        # else   → None
```

---

## `SecurityFinding`

```python
class SecurityFinding(BaseModel):
    type: str                          # "cve", "open_port", "auth_failure", "disk_critical"
    severity: Severity
    detail: str
    target: str = ""                   # container name, port number, etc.
```

---

## `HealAction`

```python
class HealAction(BaseModel):
    container: str
    action: str                        # "restart", "prune", "monitor", "escalate", "protected_escalate"
    command: str = ""                  # actual shell command executed
    result: str = ""                   # stdout/stderr or description
    success: bool = False
    escalated: bool = False
    escalation_reason: str = ""
```

---

## `GuardianRun`

Top-level aggregation model for a single run of `check`.

```python
class GuardianRun(BaseModel):
    timestamp: datetime
    mode: str                          # "check", "scan", "heal"
    scope: str = "all"
    containers: list[ContainerInfo] = []
    disk: list[DiskInfo] = []
    redis: RedisInfo | None = None
    actions: list[HealAction] = []

    @property
    def total_containers(self) -> int: ...

    @property
    def unhealthy_containers(self) -> list[ContainerInfo]: ...

    @property
    def critical_count(self) -> int: ...

    @property
    def warning_count(self) -> int: ...

    def to_summary(self) -> dict: ...
    # Returns: {total, unhealthy, critical, warning, actions_taken, escalated}
```
