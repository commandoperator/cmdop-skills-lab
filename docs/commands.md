# Writing Commands

## Skill + Command

Use the `Skill` class and `@skill.command` decorator:

```python
# src/my_skill/_skill.py
from cmdop_skill import Arg, Skill

skill = Skill()  # name, version, description from pyproject.toml

@skill.command
async def check(
    domain: str = Arg(help="Domain to check", required=True),
    timeout: int = Arg("--timeout", help="Timeout in seconds", default=10),
) -> dict:
    """Check SSL certificate for a domain."""
    result = await do_check(domain, timeout)
    return {"domain": domain, "days_left": result.days_left}

@skill.command
def health() -> dict:
    """Health check."""
    return {"status": "ok"}

def main() -> None:
    skill.run()
```

- Commands can be `async` or sync
- Return a `dict` — automatically wrapped as `{"ok": true, ...}`
- Each command becomes a CLI subcommand
- Docstring becomes the command help text

## Arg()

`Arg()` defines argument metadata:

| Parameter | Description | Example |
|---|---|---|
| `help` | Help text | `Arg(help="Domain to check")` |
| `required` | Must be provided | `Arg(required=True)` |
| `default` | Default value | `Arg(default=10)` |
| `choices` | Allowed values | `Arg(choices=["json", "text"])` |
| `action` | Argparse action | `Arg(action="store_true")` |
| `nargs` | Number of args | `Arg(nargs="+")` |

First positional argument to `Arg()` overrides the CLI flag name:

```python
verbose: bool = Arg("-v", "--verbose", action="store_true", default=False)
```

## Entry Point

Add to `pyproject.toml`:

```toml
[project.scripts]
my-skill = "my_skill._skill:main"
```

Create `run.py` for direct execution:

```python
#!/usr/bin/env python3
from my_skill._skill import main

if __name__ == "__main__":
    main()
```

## Lifecycle Hooks

Optional setup/teardown around command execution:

```python
@skill.setup
async def on_start():
    # Initialize connections, load config
    ...

@skill.teardown
async def on_stop():
    # Close connections, flush logs
    ...
```

Setup runs before the first command. Teardown runs after.

## Return Values

Commands return a `dict`. The framework wraps it:

```python
# Your command returns:
return {"message": "Hello!"}

# Framework outputs:
{"ok": true, "message": "Hello!"}
```

For errors:

```python
return {"ok": False, "error": "Something went wrong"}
```

Or raise an exception — the framework catches it and returns a structured error.
