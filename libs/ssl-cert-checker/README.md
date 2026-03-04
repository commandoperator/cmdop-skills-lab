# ssl-cert-checker

> **[CMDOP Skill](https://cmdop.com/skills/ssl-cert-checker/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install ssl-cert-checker
> ```
Check SSL certificate expiry for one or more domains. CMDOP skill + standalone Python library.

## Install

```bash
pip install ssl-cert-checker
```

Or as a CMDOP skill:

```bash
cmdop-skill install path/to/ssl-cert-checker
```

## CLI

```bash
ssl-cert-checker check --domains github.com google.com
```

```
✅  github.com: expires 2026-04-05 (33 days) — Sectigo Limited
✅  google.com: expires 2026-04-27 (54 days) — Google Trust Services
```

JSON output (for scripts/CMDOP bot):

```bash
ssl-cert-checker check --domains github.com --json
```

## Python API

```python
from ssl_cert_checker import check_cert, check_certs, CertResult, status_emoji

# Single domain
result = check_cert("github.com")
print(result.domain, result.expires, result.days_left, result.issuer)

# Batch
results = check_certs(["github.com", "google.com"])

# Status emoji: red (<7d), warning (<30d), green (>=30d)
print(status_emoji(result.days_left))
```
