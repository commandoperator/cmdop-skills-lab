"""Docker container inspection and anomaly detection."""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from server_agent._models import (
    Anomaly,
    ContainerInfo,
    ContainerState,
    Severity,
)

# Patterns in logs that indicate problems
_ERROR_PATTERNS: list[tuple[re.Pattern[str], Severity, str]] = [
    (re.compile(r"panic:", re.IGNORECASE), Severity.CRITICAL, "panic in logs"),
    (re.compile(r"FATAL|fatal error", re.IGNORECASE), Severity.CRITICAL, "fatal error in logs"),
    (re.compile(r"out of memory|OOM|killed process", re.IGNORECASE), Severity.CRITICAL, "OOM in logs"),
    (re.compile(r"segmentation fault|sigsegv", re.IGNORECASE), Severity.CRITICAL, "segfault in logs"),
    (re.compile(r"HTTP 5\d\d|\"status\":\s*5\d\d", re.IGNORECASE), Severity.WARNING, "5xx errors in logs"),
    (re.compile(r"connection refused|ECONNREFUSED", re.IGNORECASE), Severity.WARNING, "connection refused in logs"),
    (re.compile(r"timeout|timed out", re.IGNORECASE), Severity.WARNING, "timeout in logs"),
    (re.compile(r"error|exception|traceback", re.IGNORECASE), Severity.INFO, "errors in logs"),
]


def _run(cmd: str, timeout: int = 15) -> tuple[str, str, int]:
    """Run shell command, return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Command timed out after {timeout}s", 1
    except Exception as e:
        return "", str(e), 1


def _parse_json_lines(text: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON objects, skip invalid lines."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def get_containers(scope: str = "all") -> list[ContainerInfo]:
    """Get all running containers with health and resource info."""
    # Get container list
    ps_out, _, rc = _run("docker ps --format '{{json .}}'")
    if rc != 0 or not ps_out:
        return []

    ps_data = _parse_json_lines(ps_out)

    # Get resource stats (non-streaming)
    stats_out, _, _ = _run(
        "docker stats --no-stream --format '{{json .}}'", timeout=20
    )
    stats_by_name: dict[str, dict[str, Any]] = {}
    for s in _parse_json_lines(stats_out):
        name = s.get("Name", "").lstrip("/")
        stats_by_name[name] = s

    containers = []
    for ps in ps_data:
        name = ps.get("Names", "").lstrip("/")
        image = ps.get("Image", "")
        status = ps.get("Status", "")

        # Filter by scope
        if scope != "all" and not name.startswith(scope):
            continue

        # Determine state
        state = _parse_state(ps, status)

        # Parse resource usage
        stats = stats_by_name.get(name, {})
        mem_pct = _parse_pct(stats.get("MemPerc", "0%"))
        cpu_pct = _parse_pct(stats.get("CPUPerc", "0%"))

        # Get restart count from inspect
        restart_count = _get_restart_count(name)

        info = ContainerInfo(
            name=name,
            image=image,
            status=status,
            state=state,
            restart_count=restart_count,
            memory_pct=mem_pct,
            cpu_pct=cpu_pct,
        )

        # Detect anomalies
        info.anomalies = _detect_anomalies(info)

        containers.append(info)

    return containers


def _parse_state(ps: dict[str, Any], status: str) -> ContainerState:
    """Determine container state from docker ps output."""
    status_lower = status.lower()
    if "unhealthy" in status_lower:
        return ContainerState.UNHEALTHY
    if "healthy" in status_lower:
        return ContainerState.HEALTHY
    if "restarting" in status_lower:
        return ContainerState.RESTARTING
    if "exited" in status_lower:
        return ContainerState.EXITED
    if "dead" in status_lower:
        return ContainerState.DEAD
    if "up" in status_lower:
        return ContainerState.RUNNING
    return ContainerState.UNKNOWN


def _get_restart_count(name: str) -> int:
    """Get restart count from docker inspect."""
    out, _, rc = _run(
        f"docker inspect {name} --format '{{{{.RestartCount}}}}'", timeout=5
    )
    if rc != 0:
        return 0
    try:
        return int(out.strip())
    except ValueError:
        return 0


def _parse_pct(value: str) -> float:
    """Parse percentage string like '12.5%' to float."""
    try:
        return float(value.rstrip("%").strip())
    except (ValueError, AttributeError):
        return 0.0


def _detect_anomalies(info: ContainerInfo) -> list[Anomaly]:
    """Detect anomalies for a container based on state and metrics."""
    anomalies: list[Anomaly] = []

    # State-based anomalies
    if info.state == ContainerState.UNHEALTHY:
        anomalies.append(Anomaly(
            type="unhealthy",
            severity=Severity.CRITICAL,
            detail=f"Container is unhealthy: {info.status}",
            recommended_action="inspect_logs_then_restart",
        ))
    elif info.state == ContainerState.RESTARTING:
        anomalies.append(Anomaly(
            type="crash_loop",
            severity=Severity.CRITICAL,
            detail=f"Container is in restart loop (restarts: {info.restart_count})",
            recommended_action="inspect_logs_escalate" if info.restart_count >= 3 else "inspect_logs_then_restart",
        ))
    elif info.state == ContainerState.EXITED:
        anomalies.append(Anomaly(
            type="exited",
            severity=Severity.CRITICAL,
            detail=f"Container has exited unexpectedly: {info.status}",
            recommended_action="inspect_logs_then_restart",
        ))

    # Resource anomalies
    if info.memory_pct >= 95:
        anomalies.append(Anomaly(
            type="memory_critical",
            severity=Severity.CRITICAL,
            detail=f"Memory usage critical: {info.memory_pct:.1f}%",
            recommended_action="escalate_oom",
        ))
    elif info.memory_pct >= 85:
        anomalies.append(Anomaly(
            type="memory_high",
            severity=Severity.WARNING,
            detail=f"Memory usage high: {info.memory_pct:.1f}%",
            recommended_action="monitor",
        ))

    if info.cpu_pct >= 95:
        anomalies.append(Anomaly(
            type="cpu_high",
            severity=Severity.WARNING,
            detail=f"CPU usage very high: {info.cpu_pct:.1f}%",
            recommended_action="monitor",
        ))

    # Restart count anomaly
    if info.restart_count >= 5 and info.state != ContainerState.RESTARTING:
        anomalies.append(Anomaly(
            type="high_restart_count",
            severity=Severity.WARNING,
            detail=f"Container has restarted {info.restart_count} times",
            recommended_action="investigate",
        ))

    return anomalies


def get_container_logs(name: str, tail: int = 100, since: str = "10m") -> str:
    """Get recent logs for a container."""
    out, err, rc = _run(
        f"docker logs {name} --tail {tail} --since {since} 2>&1", timeout=10
    )
    return out or err


def scan_logs_for_errors(logs: str) -> list[Anomaly]:
    """Scan log text for error patterns."""
    anomalies: list[Anomaly] = []
    seen: set[str] = set()

    for pattern, severity, label in _ERROR_PATTERNS:
        matches = pattern.findall(logs)
        if matches and label not in seen:
            seen.add(label)
            # Grab first matching line for context
            for line in logs.splitlines():
                if pattern.search(line):
                    detail = line.strip()[:200]
                    break
            else:
                detail = label

            anomalies.append(Anomaly(
                type="log_" + label.replace(" ", "_"),
                severity=severity,
                detail=detail,
            ))

    return anomalies


def get_disk_usage() -> list[tuple[str, float, str, str]]:
    """Get disk usage for all mounts. Returns list of (mount, pct, used, total)."""
    out, _, rc = _run("df -h --output=target,pcent,used,size 2>/dev/null || df -h")
    if rc != 0 or not out:
        return []

    results = []
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 4:
            continue
        mount = parts[0]
        # Only care about real filesystems
        if not mount.startswith("/") or mount.startswith("/sys") or mount.startswith("/proc"):
            continue
        pct_str = parts[1].rstrip("%")
        try:
            pct = float(pct_str)
        except ValueError:
            continue
        used = parts[2]
        total = parts[3]
        results.append((mount, pct, used, total))

    return results


def get_redis_info() -> dict[str, str]:
    """Get Redis memory info from shared-db-redis container."""
    out, _, rc = _run(
        "docker exec shared-db-redis redis-cli INFO memory 2>/dev/null", timeout=5
    )
    if rc != 0 or not out:
        return {}

    info: dict[str, str] = {}
    for line in out.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            info[key.strip()] = val.strip()
    return info
