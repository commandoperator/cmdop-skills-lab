# Code Guidelines

## JSON Output

All commands return structured data. The framework wraps the return dict as `{"ok": true, ...}` automatically.

On errors, raise an exception or return `{"ok": false, "error": "message"}`.

## Type Annotations

All functions must have complete type annotations. Use Python 3.10+ syntax:

```python
def check_cert(domain: str, timeout: int = 10) -> CertResult:
    ...

items: list[str]
mapping: dict[str, int]
optional: str | None
```

Never use `Any`. Use specific types or `Union` when needed.

## Data Models

Use Pydantic `BaseModel` for structured data instead of raw dicts:

```python
from pydantic import BaseModel

class CertResult(BaseModel):
    domain: str
    days_left: int
    issuer: str
    error: str | None = None
```

## Function Size

- Functions: **under 20 lines** — extract helpers when longer
- Single responsibility per function
- Guard clauses over deep nesting:

```python
# Prefer
def process(data: Data | None) -> Result | None:
    if not data or not data.valid:
        return None
    return do_work(data)

# Over
def process(data):
    if data:
        if data.valid:
            return do_work(data)
    return None
```

## Error Handling

Catch specific exceptions, never bare `except:`:

```python
try:
    result = do_something()
    return {"data": result}
except FileNotFoundError as e:
    return {"ok": False, "error": f"File not found: {e.filename}"}
except subprocess.TimeoutExpired:
    return {"ok": False, "error": "Command timed out"}
```

## Code Style

- Linter: **ruff** (line length 100)
- Type checker: **mypy** (strict mode)
- Import order: stdlib, third-party, local
- No mutable default arguments (`def f(items=[])` — use `None` + guard)
- No global mutable state — pass dependencies as arguments
- Constants: `SCREAMING_SNAKE_CASE` at module level
- Private helpers: prefix with `_`

## Dependencies

Keep dependencies minimal. Prefer the standard library when possible.

```toml
dependencies = [
    "cmdop",
    "cmdop-skill",
    "pydantic>=2.12.0",
    # add your deps here
]
```

## Best Practices

1. **Confirm destructive actions** — never send emails, delete files, or modify state without asking
2. **Idempotent operations** — scripts should be safe to re-run
3. **Progressive disclosure** — start with a summary, show details only when asked
4. **Error as JSON** — return `{"ok": false, "error": "message"}`, not stderr text
5. **Audit trail** — keep a local JSON log for actions taken
