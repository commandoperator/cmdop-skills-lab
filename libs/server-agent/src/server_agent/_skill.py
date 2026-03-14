"""Server Agent skill — universal production server monitoring."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from cmdop_skill import Arg, Skill

from server_agent._docker import (
    get_container_logs,
    get_containers,
    get_disk_usage,
    get_redis_info,
    scan_logs_for_errors,
)
from server_agent._healer import heal_container, prune_docker
from server_agent._models import (
    DiskInfo,
    GuardianRun,
    RedisInfo,
    Severity,
)
from server_agent._reporter import (
    send_telegram,
    update_index,
    write_daily_summary,
    write_incident_report,
    write_security_report,
)
from server_agent._security import (
    check_auth_logs,
    check_disk,
    check_open_ports,
    generate_port_baseline,
    scan_images,
)

skill = Skill()


# ─────────────────────────────────────────────────────────────────────────────
# check — full health check (main trigger command)
# ─────────────────────────────────────────────────────────────────────────────

@skill.command
def check(
    scope: str = Arg("--scope", help="Project scope: 'all' or project name prefix", default="all"),
    heal: bool = Arg("--heal", help="Auto-heal safe issues", action="store_true", default=True),
    dry_run: bool = Arg("--dry-run", help="Simulate actions without executing", action="store_true", default=False),
    notify: bool = Arg("--notify", help="Send Telegram notification", action="store_true", default=True),
    json_out: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Full production health check: containers, disk, Redis. Auto-heals safe issues."""
    run = GuardianRun(mode="check", scope=scope)

    # 1. Collect container states
    containers = get_containers(scope=scope)
    run.containers = containers

    # 2. For unhealthy containers — get logs and enrich anomalies
    for c in containers:
        if not c.is_healthy:
            logs = get_container_logs(c.name, tail=100, since="10m")
            log_anomalies = scan_logs_for_errors(logs)
            c.anomalies.extend(log_anomalies)

    # 3. Disk usage
    for mount, pct, used, total in get_disk_usage():
        di = DiskInfo(mount=mount, used_pct=pct, used=used, total=total)
        run.disk.append(di)

    # 4. Redis info
    redis_raw = get_redis_info()
    if redis_raw:
        used_bytes = int(redis_raw.get("used_memory", 0))
        max_bytes = int(redis_raw.get("maxmemory", 0))
        pct = (used_bytes / max_bytes * 100) if max_bytes > 0 else 0.0
        run.redis = RedisInfo(
            used_memory_human=redis_raw.get("used_memory_human", ""),
            maxmemory_human=redis_raw.get("maxmemory_human", ""),
            used_pct=round(pct, 1),
            connected_clients=int(redis_raw.get("connected_clients", 0)),
        )

    # 5. Disk CRITICAL → maybe prune
    for di in run.disk:
        if di.severity == Severity.CRITICAL and di.mount == "/" and heal and di.used_pct >= 90:
                action = prune_docker(dry_run=dry_run)
                run.actions.append(action)

    # 6. Heal unhealthy containers
    if heal:
        for c in containers:
            if not c.is_healthy:
                action = heal_container(c, dry_run=dry_run)
                run.actions.append(action)

    # 7. Write incident reports for each problem container
    reports_dir = os.environ.get("REPORTS_DIR", "/tmp/server-agent/reports")
    report_paths = []
    for c in containers:
        if c.max_severity in (Severity.CRITICAL, Severity.WARNING):
            path = write_incident_report(run, c.name)
            report_paths.append(path)
            if not run.report_path:
                run.report_path = path

    # 8. Update index
    if report_paths:
        update_index(reports_dir)

    # 9. Telegram notification
    if notify and (run.unhealthy_containers or any(d.severity for d in run.disk)):
        msg = _build_check_telegram_message(run)
        send_telegram(msg, level="error" if run.critical_count > 0 else "warning")

    summary = run.to_summary()

    if not json_out:
        _print_check_summary(run)
        sys.exit(0)

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# scan — security vulnerability and threat scan
# ─────────────────────────────────────────────────────────────────────────────

@skill.command
def scan(
    scope: str = Arg("--scope", help="Project scope: 'all' or project name prefix", default="all"),
    baseline: bool = Arg("--baseline", help="Generate/update port baseline and exit", action="store_true", default=False),
    notify: bool = Arg("--notify", help="Send Telegram notification for findings", action="store_true", default=True),
    json_out: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Security scan: trivy CVE scan, open ports, auth logs, disk."""
    reports_dir = os.environ.get("REPORTS_DIR", "/tmp/server-agent/reports")

    # Baseline generation mode
    if baseline:
        b = generate_port_baseline(reports_dir)
        if not json_out:
            print(f"✅ Port baseline generated: {len(b['tcp_listen'])} ports")
            print(f"   Set 'reviewed: true' in {reports_dir}/baseline/ports.json when ready")
            sys.exit(0)
        return {"ok": True, "baseline": b}

    run = GuardianRun(mode="scan", scope=scope)

    # 1. Get running images for trivy scan
    containers = get_containers(scope=scope)
    images = list({c.image for c in containers if c.image})

    # 2. CVE scan
    run.security.extend(scan_images(images))

    # 3. Open ports
    run.security.extend(check_open_ports(reports_dir))

    # 4. Auth logs
    run.security.extend(check_auth_logs())

    # 5. Disk (as security finding)
    run.security.extend(check_disk(reports_dir))

    # 6. Write security report
    if run.security:
        path = write_security_report(run)
        run.report_path = path
        update_index(reports_dir)

    # 7. Telegram for critical findings
    critical = [f for f in run.security if f.severity == Severity.CRITICAL]
    if notify and critical:
        lines = ["🔒 SECURITY — Critical findings:"]
        for f in critical[:5]:  # cap at 5 to avoid spam
            lines.append(f"  • {f.detail} ({f.target})")
        if len(critical) > 5:
            lines.append(f"  ... and {len(critical) - 5} more")
        send_telegram("\n".join(lines), level="critical")

    result = {
        "findings": len(run.security),
        "critical": len(critical),
        "warnings": len([f for f in run.security if f.severity == Severity.WARNING]),
        "report_path": run.report_path,
        "details": [f.model_dump() for f in run.security],
    }

    if not json_out:
        _print_scan_summary(run)
        sys.exit(0)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# heal — targeted remediation for a specific container
# ─────────────────────────────────────────────────────────────────────────────

@skill.command
def heal(
    container: str = Arg("--container", help="Container name to heal", required=True),
    dry_run: bool = Arg("--dry-run", help="Simulate without executing", action="store_true", default=False),
    notify: bool = Arg("--notify", help="Send Telegram notification", action="store_true", default=True),
    json_out: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Targeted auto-remediation for a specific container."""
    # Get fresh container state
    containers = get_containers(scope="all")
    target = next((c for c in containers if c.name == container), None)

    if not target:
        if not json_out:
            print(f"❌ Container '{container}' not found or not running")
            sys.exit(1)
        return {"ok": False, "error": f"Container '{container}' not found"}

    action = heal_container(target, dry_run=dry_run)

    if notify:
        if action.escalated:
            msg = f"⚠️ ESCALATION REQUIRED — {container}\n\n{action.escalation_reason}\n\nProposed: `{action.command}`"
            send_telegram(msg, level="warning")
        elif action.success:
            msg = f"✅ HEALED — {container}\nAction: `{action.command}`\nResult: {action.result}"
            send_telegram(msg, level="success")

    result = action.model_dump()

    if not json_out:
        icon = "✅" if action.success else "⚠️" if action.escalated else "❌"
        print(f"{icon} {container}: {action.action}")
        if action.result:
            print(f"   {action.result}")
        if action.escalated:
            print(f"   Escalation: {action.escalation_reason}")
        sys.exit(0)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# report — write aggregated reports
# ─────────────────────────────────────────────────────────────────────────────

@skill.command
def report(
    report_type: str = Arg("--type", help="Report type: daily | security | status", default="daily"),
    date: str = Arg("--date", help="Date YYYY-MM-DD (default: today)", default=""),
    notify: bool = Arg("--notify", help="Send Telegram with report summary", action="store_true", default=True),
    json_out: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Write structured MD reports: daily summary, security, or status."""
    reports_dir = os.environ.get("REPORTS_DIR", "/tmp/server-agent/reports")

    target_date: datetime | None = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return {"ok": False, "error": f"Invalid date format: {date} (expected YYYY-MM-DD)"}

    if report_type == "daily":
        # Write empty daily summary (real aggregation happens when runs are stored)
        # For now, run a quick check and summarize it
        run = GuardianRun(mode="report")
        run.containers = get_containers()
        for mount, pct, used, total in get_disk_usage():
            run.disk.append(DiskInfo(mount=mount, used_pct=pct, used=used, total=total))
        path = write_daily_summary([run], date=target_date)
        update_index(reports_dir)

        if notify:
            summary = run.to_summary()
            msg = (
                f"📊 Daily Summary — {(target_date or datetime.now(timezone.utc)).strftime('%Y-%m-%d')}\n\n"
                f"Containers: {summary['containers']['healthy']}/{summary['containers']['total']} healthy\n"
                f"Critical: {summary['containers']['critical']} | Warnings: {summary['containers']['warning']}\n"
                f"Report: {path}"
            )
            send_telegram(msg, level="info")

        if not json_out:
            print(f"✅ Daily report written: {path}")
            sys.exit(0)
        return {"ok": True, "report_path": path, "type": "daily"}

    if report_type == "security":
        run = GuardianRun(mode="scan")
        containers = get_containers()
        images = list({c.image for c in containers if c.image})
        run.security.extend(scan_images(images))
        run.security.extend(check_open_ports(reports_dir))
        run.security.extend(check_auth_logs())
        run.security.extend(check_disk(reports_dir))
        path = write_security_report(run)
        update_index(reports_dir)

        if not json_out:
            print(f"✅ Security report written: {path}")
            sys.exit(0)
        return {"ok": True, "report_path": path, "type": "security"}

    if report_type == "status":
        # Quick status snapshot — no file written, just JSON/print
        containers = get_containers()
        healthy = [c for c in containers if c.is_healthy]
        unhealthy = [c for c in containers if not c.is_healthy]

        if not json_out:
            print(f"Containers: {len(healthy)}/{len(containers)} healthy")
            for c in unhealthy:
                sev = c.max_severity.value if c.max_severity else "?"
                print(f"  ❌ {c.name} [{sev}] — {c.status}")
            sys.exit(0)

        return {
            "ok": True,
            "type": "status",
            "containers": {
                "total": len(containers),
                "healthy": len(healthy),
                "unhealthy": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "severity": c.max_severity.value if c.max_severity else None,
                        "anomalies": [a.model_dump() for a in c.anomalies],
                    }
                    for c in unhealthy
                ],
            },
        }

    return {"ok": False, "error": f"Unknown report type: {report_type}. Use: daily, security, status"}


# ─────────────────────────────────────────────────────────────────────────────
# status — quick server snapshot (no files written)
# ─────────────────────────────────────────────────────────────────────────────

@skill.command
def status(
    json_out: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Quick health snapshot: containers, disk, Redis. No files written."""
    containers = get_containers()
    healthy = [c for c in containers if c.is_healthy]
    unhealthy = [c for c in containers if not c.is_healthy]

    disk = []
    for mount, pct, used, total in get_disk_usage():
        disk.append(DiskInfo(mount=mount, used_pct=pct, used=used, total=total))

    redis_raw = get_redis_info()
    redis_str = ""
    if redis_raw:
        used = redis_raw.get("used_memory_human", "?")
        max_mem = redis_raw.get("maxmemory_human", "?")
        redis_str = f"{used} / {max_mem}"

    if not json_out:
        overall = "✅ OK" if not unhealthy else f"⚠️ {len(unhealthy)} issues"
        print(f"\nServer Status: {overall}")
        print(f"Containers: {len(healthy)}/{len(containers)} healthy")
        for c in unhealthy:
            sev = c.max_severity.value if c.max_severity else "?"
            print(f"  ❌ {c.name} [{sev}] — {c.status}")
        print(f"Disk: {', '.join(f'{d.mount} {d.used_pct:.0f}%' for d in disk)}")
        if redis_str:
            print(f"Redis: {redis_str}")
        sys.exit(0)

    return {
        "containers": {
            "total": len(containers),
            "healthy": len(healthy),
            "unhealthy": [
                {"name": c.name, "status": c.status, "severity": c.max_severity}
                for c in unhealthy
            ],
        },
        "disk": [{"mount": d.mount, "used_pct": d.used_pct} for d in disk],
        "redis": redis_str,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_check_summary(run: GuardianRun) -> None:
    total = run.total_containers
    healthy = total - len(run.unhealthy_containers)
    actions = [a for a in run.actions if a.success and not a.escalated]
    escalated = [a for a in run.actions if a.escalated]

    icon = "✅" if run.critical_count == 0 and run.warning_count == 0 else "⚠️" if run.critical_count == 0 else "❌"
    print(f"\n{icon} Guardian check complete")
    print(f"  Containers: {healthy}/{total} healthy")
    if run.critical_count:
        print(f"  Critical: {run.critical_count}")
    if run.warning_count:
        print(f"  Warnings: {run.warning_count}")
    if actions:
        print(f"  Auto-healed: {len(actions)}")
    if escalated:
        print(f"  Escalated: {len(escalated)} (check Telegram)")
    if run.report_path:
        print(f"  Report: {run.report_path}")


def _print_scan_summary(run: GuardianRun) -> None:
    critical = [f for f in run.security if f.severity == Severity.CRITICAL]
    warnings = [f for f in run.security if f.severity == Severity.WARNING]
    icon = "❌" if critical else "⚠️" if warnings else "✅"
    print(f"\n{icon} Security scan complete")
    print(f"  Critical: {len(critical)}")
    print(f"  Warnings: {len(warnings)}")
    if run.report_path:
        print(f"  Report: {run.report_path}")
    for f in critical[:3]:
        print(f"  🔴 {f.detail} ({f.target})")


def _build_check_telegram_message(run: GuardianRun) -> str:
    lines = []
    if run.critical_count > 0:
        lines.append(f"❌ CRITICAL — {run.critical_count} container(s) need attention")
    elif run.warning_count > 0:
        lines.append(f"⚠️ WARNING — {run.warning_count} container(s) degraded")

    for c in run.unhealthy_containers[:5]:
        sev = c.max_severity.value if c.max_severity else "?"
        lines.append(f"  • {c.name} [{sev}]: {c.status}")

    actions_done = [a for a in run.actions if a.success and not a.escalated]
    escalated = [a for a in run.actions if a.escalated]

    if actions_done:
        lines.append(f"\nAuto-healed: {len(actions_done)}")
    if escalated:
        lines.append(f"Needs approval: {len(escalated)} — check Telegram")
    if run.report_path:
        lines.append(f"Report: {run.report_path}")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    skill.run()
