# CMDOP Skills — Developer Guide

A skill is a self-contained Python package that extends the CMDOP agent. Each skill has a manifest (`skill/config.py`), a system prompt (`skill/readme.md`), commands, and tests.

```bash
pip install cmdop-skill
cmdop-skill init
```

## Docs

| Document | Description |
|---|---|
| [Getting Started](getting-started.md) | Scaffold, project structure, manifest, LLM prompt |
| [Writing Commands](commands.md) | `@skill.command`, `Arg()`, entry points |
| [Testing](testing.md) | `TestClient`, pytest config, patterns |
| [Publishing](publishing.md) | Marketplace, PyPI, release workflow |
| [Code Guidelines](code-guidelines.md) | Types, models, errors, function style |
| [Streamlit Dashboards](streamlit-dashboards.md) | Adding visual dashboards to skills |

## Reference Skills

See `libs/` for full implementations.
