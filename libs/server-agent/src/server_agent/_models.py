"""Pydantic models for server-agent."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ContainerState(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    RUNNING = "running"
    EXITED = "exited"
    DEAD = "dead"
    UNKNOWN = "unknown"


class Anomaly(BaseModel):
    type: str
    severity: Severity
    detail: str
    recommended_action: str = ""


class ContainerInfo(BaseModel):
    name: str
    image: str
    status: str
    state: ContainerState = ContainerState.UNKNOWN
    restart_count: int = 0
    memory_pct: float = 0.0
    cpu_pct: float = 0.0
    anomalies: list[Anomaly] = Field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.state == ContainerState.HEALTHY or (
            self.state == ContainerState.RUNNING and not self.anomalies
        )

    @property
    def max_severity(self) -> Severity | None:
        if not self.anomalies:
            return None
        order = [Severity.CRITICAL, Severity.WARNING, Severity.INFO]
        for s in order:
            if any(a.severity == s for a in self.anomalies):
                return s
        return None


class DiskInfo(BaseModel):
    mount: str
    used_pct: float
    used: str = ""
    total: str = ""
    available: str = ""

    @property
    def severity(self) -> Severity | None:
        if self.used_pct >= 95:
            return Severity.CRITICAL
        if self.used_pct >= 85:
            return Severity.WARNING
        return None


class RedisInfo(BaseModel):
    used_memory_human: str = ""
    maxmemory_human: str = ""
    used_pct: float = 0.0
    connected_clients: int = 0
    error: str | None = None

    @property
    def severity(self) -> Severity | None:
        if self.error:
            return Severity.WARNING
        if self.used_pct >= 90:
            return Severity.WARNING
        return None


class SecurityFinding(BaseModel):
    type: str  # cve | open_port | auth_failure | process
    severity: Severity
    detail: str
    target: str = ""  # container/image/port/process name


class HealAction(BaseModel):
    container: str
    action: str
    command: str
    result: str = ""
    success: bool = False
    escalated: bool = False
    escalation_reason: str = ""


class GuardianRun(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: str = "check"
    scope: str = "all"
    containers: list[ContainerInfo] = Field(default_factory=list)
    disk: list[DiskInfo] = Field(default_factory=list)
    redis: RedisInfo | None = None
    security: list[SecurityFinding] = Field(default_factory=list)
    actions: list[HealAction] = Field(default_factory=list)
    report_path: str = ""
    errors: list[str] = Field(default_factory=list)

    @property
    def total_containers(self) -> int:
        return len(self.containers)

    @property
    def unhealthy_containers(self) -> list[ContainerInfo]:
        return [c for c in self.containers if not c.is_healthy]

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.containers if c.max_severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.containers if c.max_severity == Severity.WARNING)

    def to_summary(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "mode": self.mode,
            "scope": self.scope,
            "containers": {
                "total": self.total_containers,
                "healthy": self.total_containers - len(self.unhealthy_containers),
                "unhealthy": len(self.unhealthy_containers),
                "critical": self.critical_count,
                "warning": self.warning_count,
            },
            "disk": [
                {"mount": d.mount, "used_pct": d.used_pct, "severity": d.severity}
                for d in self.disk
                if d.severity
            ],
            "security_findings": len(self.security),
            "actions_taken": len([a for a in self.actions if a.success]),
            "escalated": len([a for a in self.actions if a.escalated]),
            "report_path": self.report_path,
            "errors": self.errors,
        }
