"""Tests for server-agent data models."""
import pytest
from server_agent._models import (
    Anomaly,
    ContainerInfo,
    ContainerState,
    DiskInfo,
    GuardianRun,
    HealAction,
    RedisInfo,
    Severity,
)


def test_severity_ordering():
    assert Severity.CRITICAL == "CRITICAL"
    assert Severity.WARNING == "WARNING"
    assert Severity.INFO == "INFO"


def test_container_info_healthy():
    c = ContainerInfo(name="test", image="test:latest", status="Up 2 hours", state=ContainerState.RUNNING)
    assert c.is_healthy is True
    assert c.max_severity is None


def test_container_info_unhealthy():
    c = ContainerInfo(
        name="test",
        image="test:latest",
        status="Up (unhealthy)",
        state=ContainerState.UNHEALTHY,
        anomalies=[
            Anomaly(type="unhealthy", severity=Severity.CRITICAL, detail="healthcheck failing"),
        ],
    )
    assert c.is_healthy is False
    assert c.max_severity == Severity.CRITICAL


def test_container_max_severity_warning():
    c = ContainerInfo(
        name="test",
        image="test:latest",
        status="Up",
        state=ContainerState.RUNNING,
        memory_pct=88.0,
        anomalies=[
            Anomaly(type="memory_high", severity=Severity.WARNING, detail="memory 88%"),
        ],
    )
    assert c.is_healthy is False  # has anomalies
    assert c.max_severity == Severity.WARNING


def test_disk_info_severity():
    d_ok = DiskInfo(mount="/", used_pct=60.0)
    assert d_ok.severity is None

    d_warn = DiskInfo(mount="/", used_pct=87.0)
    assert d_warn.severity == Severity.WARNING

    d_crit = DiskInfo(mount="/", used_pct=96.0)
    assert d_crit.severity == Severity.CRITICAL


def test_redis_info_severity():
    r_ok = RedisInfo(used_pct=50.0)
    assert r_ok.severity is None

    r_warn = RedisInfo(used_pct=91.0)
    assert r_warn.severity == Severity.WARNING

    r_err = RedisInfo(error="connection refused")
    assert r_err.severity == Severity.WARNING


def test_guardian_run_summary():
    from datetime import datetime, timezone

    run = GuardianRun(
        timestamp=datetime(2026, 3, 14, 10, 23, tzinfo=timezone.utc),
        mode="check",
        scope="all",
        containers=[
            ContainerInfo(
                name="reforms-django",
                image="reforms:latest",
                status="Up (unhealthy)",
                state=ContainerState.UNHEALTHY,
                anomalies=[Anomaly(type="unhealthy", severity=Severity.CRITICAL, detail="failing")],
            ),
            ContainerInfo(
                name="carapis-django",
                image="carapis:latest",
                status="Up 2 hours",
                state=ContainerState.RUNNING,
            ),
        ],
        actions=[
            HealAction(container="reforms-django", action="restart", command="docker restart reforms-django", success=True, result="ok"),
        ],
    )

    assert run.total_containers == 2
    assert len(run.unhealthy_containers) == 1
    assert run.critical_count == 1
    assert run.warning_count == 0

    summary = run.to_summary()
    assert summary["containers"]["total"] == 2
    assert summary["containers"]["healthy"] == 1
    assert summary["containers"]["unhealthy"] == 1
    assert summary["containers"]["critical"] == 1
    assert summary["actions_taken"] == 1
