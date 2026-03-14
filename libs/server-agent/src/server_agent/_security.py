"""Security scanning: trivy, ports, auth logs."""
from __future__ import annotations

import contextlib
import json
import re
import subprocess
from typing import Any

from server_agent._models import SecurityFinding, Severity

# Ports that are always expected — expanded during baseline generation
_DEFAULT_KNOWN_PORTS: set[int] = {22, 80, 443, 6379}


def _run(cmd: str, timeout: int = 60) -> tuple[str, str, int]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1


def _load_baseline_ports(reports_dir: str) -> set[int]:
    """Load known port baseline from reports dir."""
    import os

    baseline_path = os.path.join(reports_dir, "baseline", "ports.json")
    if not os.path.exists(baseline_path):
        return _DEFAULT_KNOWN_PORTS.copy()
    try:
        with open(baseline_path) as f:
            data = json.load(f)
        return set(data.get("tcp_listen", list(_DEFAULT_KNOWN_PORTS)))
    except Exception:
        return _DEFAULT_KNOWN_PORTS.copy()


def scan_images(images: list[str]) -> list[SecurityFinding]:
    """Run trivy on each unique image, return HIGH/CRITICAL findings."""
    findings: list[SecurityFinding] = []
    seen_images: set[str] = set()

    for image in images:
        if image in seen_images:
            continue
        seen_images.add(image)

        # Check if trivy is available
        _, _, rc = _run("which trivy", timeout=3)
        if rc != 0:
            findings.append(SecurityFinding(
                type="tool_missing",
                severity=Severity.WARNING,
                detail="trivy not installed — skipping vulnerability scan",
                target="system",
            ))
            break

        out, _, rc = _run(
            f"trivy image {image} --format json --severity HIGH,CRITICAL --quiet 2>/dev/null",
            timeout=120,
        )
        if rc != 0 or not out:
            continue

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue

        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []) or []:
                severity = Severity.CRITICAL if vuln.get("Severity") == "CRITICAL" else Severity.WARNING
                cve = vuln.get("VulnerabilityID", "unknown")
                pkg = vuln.get("PkgName", "")
                installed = vuln.get("InstalledVersion", "")
                fixed = vuln.get("FixedVersion", "")
                detail = f"{cve} in {pkg} {installed}"
                if fixed:
                    detail += f" (fix: {fixed})"

                findings.append(SecurityFinding(
                    type="cve",
                    severity=severity,
                    detail=detail,
                    target=image,
                ))

    return findings


def check_open_ports(reports_dir: str) -> list[SecurityFinding]:
    """Check for unexpected open ports against baseline."""
    findings: list[SecurityFinding] = []
    known_ports = _load_baseline_ports(reports_dir)

    out, _, rc = _run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    if rc != 0 or not out:
        return findings

    # Parse port numbers from ss/netstat output
    port_pattern = re.compile(r":(\d+)\s")
    current_ports: set[int] = set()

    for line in out.splitlines()[1:]:  # skip header
        matches = port_pattern.findall(line)
        for m in matches:
            with contextlib.suppress(ValueError):
                current_ports.add(int(m))

    # Find new ports not in baseline
    new_ports = current_ports - known_ports
    for port in sorted(new_ports):
        if port < 1024 or port in {8080, 8443}:  # common and expected
            continue
        findings.append(SecurityFinding(
            type="open_port",
            severity=Severity.WARNING,
            detail=f"Port {port} is open but not in baseline",
            target=str(port),
        ))

    return findings


def check_auth_logs() -> list[SecurityFinding]:
    """Check for suspicious authentication activity."""
    findings: list[SecurityFinding] = []

    # Try auth.log first, then journalctl
    out, _, rc = _run(
        "tail -n 200 /var/log/auth.log 2>/dev/null || "
        "journalctl -u ssh --since '1 hour ago' --no-pager 2>/dev/null | tail -200"
    )

    if not out:
        return findings

    # Count failed attempts
    failed_attempts = len(re.findall(r"Failed password|Invalid user|authentication failure", out, re.IGNORECASE))

    if failed_attempts >= 20:
        findings.append(SecurityFinding(
            type="auth_failure",
            severity=Severity.CRITICAL,
            detail=f"{failed_attempts} failed SSH login attempts in recent logs",
            target="sshd",
        ))
    elif failed_attempts >= 5:
        findings.append(SecurityFinding(
            type="auth_failure",
            severity=Severity.WARNING,
            detail=f"{failed_attempts} failed SSH login attempts in recent logs",
            target="sshd",
        ))

    return findings


def check_disk(reports_dir: str) -> list[SecurityFinding]:
    """Check disk usage, return findings for high usage."""
    # This is also in _docker.py but security scan includes it as a finding
    findings: list[SecurityFinding] = []

    out, _, rc = _run("df -h /")
    if rc != 0 or not out:
        return findings

    lines = out.splitlines()
    if len(lines) < 2:
        return findings

    parts = lines[1].split()
    if len(parts) < 5:
        return findings

    try:
        pct = float(parts[4].rstrip("%"))
    except ValueError:
        return findings

    if pct >= 95:
        findings.append(SecurityFinding(
            type="disk_critical",
            severity=Severity.CRITICAL,
            detail=f"Root disk usage critical: {pct:.0f}% ({parts[2]} used of {parts[1]})",
            target="/",
        ))
    elif pct >= 85:
        findings.append(SecurityFinding(
            type="disk_warning",
            severity=Severity.WARNING,
            detail=f"Root disk usage high: {pct:.0f}% ({parts[2]} used of {parts[1]})",
            target="/",
        ))

    return findings


def generate_port_baseline(reports_dir: str) -> dict[str, Any]:
    """Generate initial port baseline from current state."""
    import os
    from datetime import datetime, timezone

    out, _, _ = _run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    port_pattern = re.compile(r":(\d+)\s")
    ports: set[int] = set()

    for line in out.splitlines()[1:]:
        for m in port_pattern.findall(line):
            with contextlib.suppress(ValueError):
                ports.add(int(m))

    baseline: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reviewed": False,
        "tcp_listen": sorted(ports),
        "notes": {},
    }

    # Add known annotations
    known: dict[int, str] = {
        22: "SSH",
        80: "Traefik HTTP",
        443: "Traefik HTTPS",
        6379: "shared-db-redis",
        50051: "django-cfg-grpc",
        50052: "djangocfg-grpc",
        50053: "democfg-grpc",
        50054: "cmdop-grpc",
        50055: "unrealon-grpc",
    }
    for port in sorted(ports):
        if port in known:
            baseline["notes"][str(port)] = known[port]

    # Write baseline
    baseline_dir = os.path.join(reports_dir, "baseline")
    os.makedirs(baseline_dir, exist_ok=True)
    path = os.path.join(baseline_dir, "ports.json")
    with open(path, "w") as f:
        json.dump(baseline, f, indent=2)

    return baseline
