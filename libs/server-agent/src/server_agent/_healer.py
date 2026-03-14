"""Auto-remediation logic with safe/escalate boundary."""
from __future__ import annotations

import subprocess

from server_agent._models import ContainerInfo, ContainerState, HealAction

# Containers that should NEVER be auto-restarted without human approval
_PROTECTED_CONTAINERS = {
    "shared-db-redis",
    "traefik",
}

# Max auto-restarts before escalating
_MAX_AUTO_RESTARTS = 2


def _run(cmd: str, timeout: int = 30) -> tuple[str, str, int]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1


def heal_container(container: ContainerInfo, dry_run: bool = False) -> HealAction:
    """
    Decide and (optionally) execute remediation for an unhealthy container.

    Returns HealAction describing what was done or escalated.
    """
    name = container.name

    # Never touch protected containers automatically
    if name in _PROTECTED_CONTAINERS:
        return HealAction(
            container=name,
            action="protected",
            command="",
            escalated=True,
            escalation_reason=f"{name} is a protected container — manual intervention required",
        )

    # Too many restarts → escalate instead of retrying
    if container.restart_count >= _MAX_AUTO_RESTARTS:
        return HealAction(
            container=name,
            action="escalate_crash_loop",
            command=f"docker restart {name}",
            escalated=True,
            escalation_reason=(
                f"Container has restarted {container.restart_count} times — "
                "auto-restart disabled, manual investigation required"
            ),
        )

    # OOM → escalate (need memory limit increase, not just restart)
    for anomaly in container.anomalies:
        if anomaly.type == "memory_critical":
            return HealAction(
                container=name,
                action="escalate_oom",
                command=f"docker update --memory 0 {name} && docker restart {name}",
                escalated=True,
                escalation_reason=(
                    f"Memory usage critical ({container.memory_pct:.1f}%) — "
                    "memory limit adjustment required before restart"
                ),
            )

    # Standard unhealthy / exited / crash → safe to restart
    if container.state in (
        ContainerState.UNHEALTHY,
        ContainerState.EXITED,
        ContainerState.RESTARTING,
    ):
        cmd = f"docker restart {name}"
        action = HealAction(
            container=name,
            action="restart",
            command=cmd,
        )

        if dry_run:
            action.result = "dry-run: would execute"
            action.success = True
            return action

        out, err, rc = _run(cmd)
        action.success = rc == 0
        action.result = out if rc == 0 else err
        return action

    # No actionable state
    return HealAction(
        container=name,
        action="monitor",
        command="",
        result="No actionable state — monitoring only",
        success=True,
    )


def prune_docker(dry_run: bool = False) -> HealAction:
    """Remove stopped containers, dangling images, unused networks."""
    cmd = "docker system prune -f"
    action = HealAction(
        container="system",
        action="prune",
        command=cmd,
    )

    if dry_run:
        action.result = "dry-run: would execute docker system prune -f"
        action.success = True
        return action

    out, err, rc = _run(cmd, timeout=60)
    action.success = rc == 0
    action.result = out if rc == 0 else err
    return action
