"""Tests for ssl-cert-checker."""

from ssl_cert_checker._checker import check_cert, check_certs
from ssl_cert_checker._models import CertResult, status_emoji


def test_check_cert_valid():
    """Check a known valid domain returns a CertResult with days_left > 0."""
    result = check_cert("github.com")
    assert isinstance(result, CertResult)
    assert result.domain == "github.com"
    assert result.error is None
    assert result.days_left > 0
    assert result.expires != ""
    assert result.issuer != ""


def test_check_cert_invalid():
    """Check a nonexistent domain returns a CertResult with an error."""
    result = check_cert("nonexistent.invalid", timeout=3)
    assert isinstance(result, CertResult)
    assert result.domain == "nonexistent.invalid"
    assert result.error is not None


def test_check_certs():
    """Batch check returns a list of CertResult."""
    results = check_certs(["github.com"])
    assert len(results) == 1
    assert results[0].domain == "github.com"
    assert results[0].error is None


def test_cert_result_model():
    """Pydantic model validates correctly."""
    r = CertResult(
        domain="example.com",
        expires="2026-12-31",
        days_left=300,
        issuer="Let's Encrypt",
    )
    assert r.domain == "example.com"
    assert r.days_left == 300
    assert r.error is None

    r_err = CertResult(domain="bad.com", error="connection refused")
    assert r_err.error == "connection refused"
    assert r_err.days_left == 0


def test_status_emoji():
    """status_emoji returns correct emoji for different day ranges."""
    assert status_emoji(3) == "\U0001f534"   # red circle (< 7 days)
    assert status_emoji(15) == "\u26a0\ufe0f"  # warning (< 30 days)
    assert status_emoji(90) == "\u2705"       # green check (>= 30 days)
