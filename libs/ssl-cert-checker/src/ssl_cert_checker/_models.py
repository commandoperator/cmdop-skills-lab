"""Data models for SSL certificate check results."""

from pydantic import BaseModel


class CertResult(BaseModel):
    """Result of an SSL certificate check for a single domain."""

    domain: str
    expires: str = ""
    days_left: int = 0
    issuer: str = ""
    error: str | None = None


def status_emoji(days: int) -> str:
    """Return a status emoji based on days until expiry."""
    if days < 7:
        return "\U0001f534"  # red circle
    if days < 30:
        return "\u26a0\ufe0f"  # warning
    return "\u2705"  # green check
