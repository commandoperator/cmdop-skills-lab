"""Core SSL certificate checking logic."""

import socket
import ssl
from datetime import datetime, timezone

from ssl_cert_checker._models import CertResult


def check_cert(domain: str, timeout: int = 10) -> CertResult:
    """Check SSL certificate for a single domain."""
    ctx = ssl.create_default_context()
    try:
        with ctx.wrap_socket(
            socket.create_connection((domain, 443), timeout=timeout),
            server_hostname=domain,
        ) as sock:
            cert = sock.getpeercert()
    except Exception as e:
        return CertResult(domain=domain, error=str(e))

    not_after = datetime.strptime(
        cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
    ).replace(tzinfo=timezone.utc)
    days_left = (not_after - datetime.now(timezone.utc)).days
    issuer = dict(x[0] for x in cert.get("issuer", []))

    return CertResult(
        domain=domain,
        expires=not_after.strftime("%Y-%m-%d"),
        days_left=days_left,
        issuer=issuer.get("organizationName", "unknown"),
    )


def check_certs(domains: list[str], timeout: int = 10) -> list[CertResult]:
    """Check SSL certificates for multiple domains."""
    return [check_cert(domain, timeout=timeout) for domain in domains]
