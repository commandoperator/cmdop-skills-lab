"""Tests for report writing."""
import os
import tempfile
from datetime import datetime, timezone

from server_agent._models import (
    Anomaly,
    ContainerInfo,
    ContainerState,
    GuardianRun,
    HealAction,
    Severity,
)
from server_agent._reporter import (
    update_index,
    write_daily_summary,
    write_incident_report,
)


def _make_run(with_incident: bool = False) -> GuardianRun:
    containers = [
        ContainerInfo(
            name="reforms-django",
            image="reforms:latest",
            status="Up (unhealthy)" if with_incident else "Up 2 hours (healthy)",
            state=ContainerState.UNHEALTHY if with_incident else ContainerState.HEALTHY,
            anomalies=[
                Anomaly(type="unhealthy", severity=Severity.CRITICAL, detail="failing")
            ] if with_incident else [],
        ),
        ContainerInfo(
            name="carapis-django",
            image="carapis:latest",
            status="Up 2 hours (healthy)",
            state=ContainerState.HEALTHY,
        ),
    ]
    actions = []
    if with_incident:
        actions.append(HealAction(
            container="reforms-django",
            action="restart",
            command="docker restart reforms-django",
            success=True,
            result="Container restarted",
        ))

    return GuardianRun(
        timestamp=datetime(2026, 3, 14, 10, 23, tzinfo=timezone.utc),
        mode="check",
        scope="all",
        containers=containers,
        actions=actions,
    )


def test_write_incident_report(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    run = _make_run(with_incident=True)
    path = write_incident_report(run, "reforms-django")

    assert os.path.exists(path)
    content = open(path).read()
    assert "reforms-django" in content
    assert "CRITICAL" in content
    assert "RESOLVED" in content
    assert "docker restart reforms-django" in content


def test_write_incident_report_escalated(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    run = _make_run(with_incident=False)
    # Add escalated action
    run.containers[0].state = ContainerState.UNHEALTHY
    run.containers[0].anomalies = [
        Anomaly(type="unhealthy", severity=Severity.CRITICAL, detail="failing")
    ]
    run.actions = [HealAction(
        container="reforms-django",
        action="escalate",
        command="docker restart reforms-django",
        escalated=True,
        escalation_reason="Too many restarts",
    )]
    path = write_incident_report(run, "reforms-django")
    content = open(path).read()
    assert "ESCALATED" in content
    assert "Too many restarts" in content


def test_write_daily_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    runs = [_make_run(with_incident=True), _make_run(with_incident=False)]
    path = write_daily_summary(runs, date=datetime(2026, 3, 14, tzinfo=timezone.utc))

    assert os.path.exists(path)
    assert "daily-summary.md" in path
    content = open(path).read()
    assert "2026-03-14" in content
    assert "reforms-django" in content


def test_update_index(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))

    # Create a fake day dir with reports
    day_dir = tmp_path / "2026-03-14"
    day_dir.mkdir()
    (day_dir / "10-23-incident-reforms.md").write_text("# test")
    (day_dir / "daily-summary.md").write_text("# test")

    index_path = update_index(str(tmp_path))
    assert os.path.exists(index_path)
    content = open(index_path).read()
    assert "2026-03-14" in content
    assert "10-23-incident-reforms.md" in content
    assert "daily-summary.md" in content


def test_report_file_naming_convention(tmp_path, monkeypatch):
    """Report files should follow HH-MM-type-project.md pattern."""
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    run = _make_run(with_incident=True)
    path = write_incident_report(run, "reforms-django")
    filename = os.path.basename(path)
    # Should match HH-MM-incident-container.md
    import re
    assert re.match(r"\d{2}-\d{2}-incident-reforms-django\.md", filename), f"Bad filename: {filename}"
