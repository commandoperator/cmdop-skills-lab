"""Tests for Docker inspection and anomaly detection logic."""
import pytest
from server_agent._docker import _parse_pct, _parse_state, scan_logs_for_errors
from server_agent._models import ContainerState, Severity


def test_parse_pct():
    assert _parse_pct("12.5%") == 12.5
    assert _parse_pct("0%") == 0.0
    assert _parse_pct("100%") == 100.0
    assert _parse_pct("bad") == 0.0
    assert _parse_pct("") == 0.0


def test_parse_state_healthy():
    ps = {}
    assert _parse_state(ps, "Up 2 hours (healthy)") == ContainerState.HEALTHY


def test_parse_state_unhealthy():
    ps = {}
    assert _parse_state(ps, "Up 5 minutes (unhealthy)") == ContainerState.UNHEALTHY


def test_parse_state_restarting():
    ps = {}
    assert _parse_state(ps, "Restarting (1) 3 seconds ago") == ContainerState.RESTARTING


def test_parse_state_exited():
    ps = {}
    assert _parse_state(ps, "Exited (1) 2 minutes ago") == ContainerState.EXITED


def test_parse_state_running():
    ps = {}
    assert _parse_state(ps, "Up 2 days") == ContainerState.RUNNING


def test_scan_logs_no_errors():
    logs = "INFO Starting server\nINFO Listening on :8000\nINFO Request processed"
    anomalies = scan_logs_for_errors(logs)
    # Only INFO-level matches for "info" — filtered as INFO severity
    critical = [a for a in anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) == 0


def test_scan_logs_panic():
    logs = "INFO Starting...\npanic: runtime error: index out of range\ngoroutine 1 [running]"
    anomalies = scan_logs_for_errors(logs)
    critical = [a for a in anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) >= 1
    assert any("panic" in a.type for a in critical)


def test_scan_logs_oom():
    logs = "Killed process 12345 (python) total-vm:6291456kB, anon-rss:4194304kB"
    anomalies = scan_logs_for_errors(logs)
    critical = [a for a in anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) >= 1


def test_scan_logs_connection_refused():
    logs = "ERROR ConnectionRefusedError: [Errno 111] Connection refused\nretrying..."
    anomalies = scan_logs_for_errors(logs)
    warnings = [a for a in anomalies if a.severity == Severity.WARNING]
    assert len(warnings) >= 1


def test_scan_logs_5xx():
    logs = 'HTTP 500 GET /api/v1/status\n{"status": 503, "error": "service unavailable"}'
    anomalies = scan_logs_for_errors(logs)
    warnings = [a for a in anomalies if a.severity == Severity.WARNING]
    assert len(warnings) >= 1


def test_scan_logs_deduplication():
    """Same pattern multiple times should only produce one anomaly."""
    logs = "\n".join(["panic: error"] * 20)
    anomalies = scan_logs_for_errors(logs)
    panic_anomalies = [a for a in anomalies if "panic" in a.type]
    assert len(panic_anomalies) == 1
