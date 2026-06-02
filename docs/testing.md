# Testing

## TestClient

Use `TestClient` to test commands without subprocess execution:

```python
import pytest
from cmdop_skill import TestClient
from my_skill._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)


class TestCheck:
    async def test_check_domain(self, client: TestClient) -> None:
        result = await client.run("check", domain="github.com")
        assert result["ok"] is True
        assert result["days_left"] > 0

    async def test_check_via_cli(self, client: TestClient) -> None:
        result = await client.run_cli("check", "--domain", "github.com")
        assert result["ok"] is True
```

### run() vs run_cli()

| Method | Input style | Example |
|---|---|---|
| `client.run("cmd", key=val)` | Keyword arguments | `await client.run("check", domain="github.com")` |
| `client.run_cli("cmd", "--flag", "val")` | CLI-style strings | `await client.run_cli("check", "--domain", "github.com")` |

Both return the same result dict.

### Lifecycle

`TestClient` supports lifecycle hooks:

```python
async with TestClient(skill) as client:
    result = await client.run("check", domain="github.com")
# teardown runs automatically on exit
```

## pyproject.toml Config

Ensure async tests work:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Dev dependencies:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```

## Running Tests

```bash
make test
# or
pytest tests/ -v
```

## Patterns

### Mocking external calls

```python
from unittest.mock import patch, AsyncMock

class TestWithMock:
    @patch("my_skill._checker.httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_check_mocked(self, mock_get, client):
        mock_get.return_value.json.return_value = {"status": "ok"}
        result = await client.run("check", domain="example.com")
        assert result["ok"] is True
```

### Testing error cases

```python
class TestErrors:
    async def test_unknown_command(self, client: TestClient) -> None:
        result = await client.run("nonexistent")
        assert result["ok"] is False

    async def test_missing_required_arg(self, client: TestClient) -> None:
        result = await client.run("check")  # domain is required
        assert result["ok"] is False
```

### Shared fixtures

Put shared fixtures in `tests/conftest.py`:

```python
import pytest
from cmdop_skill import TestClient
from my_skill._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)
```
