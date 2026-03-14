"""Tests for auto-remediation logic."""
from server_agent._healer import heal_container
from server_agent._models import Anomaly, ContainerInfo, ContainerState, Severity


def _make_container(name: str, state: ContainerState, restart_count: int = 0, mem_pct: float = 0.0) -> ContainerInfo:
    anomalies = []
    if state == ContainerState.UNHEALTHY:
        anomalies.append(Anomaly(type="unhealthy", severity=Severity.CRITICAL, detail="failing"))
    if state == ContainerState.RESTARTING:
        anomalies.append(Anomaly(type="crash_loop", severity=Severity.CRITICAL, detail="crash loop"))
    if mem_pct >= 95:
        anomalies.append(Anomaly(type="memory_critical", severity=Severity.CRITICAL, detail=f"memory {mem_pct}%"))
    return ContainerInfo(
        name=name,
        image="test:latest",
        status="test",
        state=state,
        restart_count=restart_count,
        memory_pct=mem_pct,
        anomalies=anomalies,
    )


def test_heal_unhealthy_dry_run():
    c = _make_container("reforms-django", ContainerState.UNHEALTHY)
    action = heal_container(c, dry_run=True)
    assert action.action == "restart"
    assert action.success is True
    assert "dry-run" in action.result
    assert action.escalated is False


def test_heal_protected_container():
    c = _make_container("shared-db-redis", ContainerState.UNHEALTHY)
    action = heal_container(c, dry_run=True)
    assert action.escalated is True
    assert "protected" in action.action


def test_heal_crash_loop_escalated():
    """Container with too many restarts should be escalated, not restarted."""
    c = _make_container("gptkino-rq-worker", ContainerState.UNHEALTHY, restart_count=5)
    action = heal_container(c, dry_run=True)
    assert action.escalated is True
    assert "restart" in action.escalation_reason.lower() or "restarts" in action.escalation_reason.lower()


def test_heal_oom_escalated():
    """OOM containers should be escalated for memory limit review."""
    c = _make_container("gptkino-rq-worker-render", ContainerState.RUNNING, mem_pct=97.0)
    action = heal_container(c, dry_run=True)
    assert action.escalated is True
    assert "memory" in action.escalation_reason.lower()


def test_heal_healthy_container_monitor():
    """Healthy container with no issues → monitor only, no action."""
    c = ContainerInfo(
        name="carapis-django",
        image="carapis:latest",
        status="Up 2 hours",
        state=ContainerState.RUNNING,
    )
    action = heal_container(c, dry_run=True)
    assert action.action == "monitor"
    assert action.escalated is False


def test_heal_exited_container():
    """Exited container should be restarted."""
    c = _make_container("reforms-django", ContainerState.EXITED)
    action = heal_container(c, dry_run=True)
    assert action.action == "restart"
    assert action.command == "docker restart reforms-django"
