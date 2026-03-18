# CMDOP Skills Lab

![CMDOP Skills Lab](https://raw.githubusercontent.com/markolofsen/assets/main/libs/cmdop/cmdop-skills-lab.webp)

Skills are plugins for the CMDOP agent. Each skill is a small Python package with commands, a manifest, and a system prompt. Two commands to get started:

```bash
pip install cmdop-skill
cmdop-skill init
```

That's it — the wizard scaffolds a ready-to-run project. Write a function, decorate it, publish:

```python
from cmdop_skill import Skill, Arg

skill = Skill()  # name, version, description from pyproject.toml

@skill.command
async def check(domain: str = Arg(help="Domain to check", required=True)) -> dict:
    """Check SSL certificate for a domain."""
    return await do_check(domain)
```

```bash
cmdop-skill release   # bump + build + publish to PyPI & CMDOP
```

Published skills appear on [cmdop.com/skills](https://cmdop.com/skills/).

## Skills

| Skill | Description |
|---|---|
| `ssl-cert-checker` | Check SSL certificate expiry dates |
| `cmdop-coder` | Code analysis with tree-sitter AST |
| `cmdop-sdkrouter` | Unified AI services SDK wrapper |
| `tg-notify` | Telegram notifications |
| `llm-email` | Email processing for LLM |
| `llm-html` | HTML processing for LLM |

## Documentation

| Doc | What it covers |
|---|---|
| [@docs/getting-started](@docs/getting-started.md) | Scaffold, project structure, manifest |
| [@docs/commands](@docs/commands.md) | `@skill.command`, `Arg()`, entry points |
| [@docs/testing](@docs/testing.md) | `TestClient`, pytest patterns |
| [@docs/publishing](@docs/publishing.md) | Marketplace, PyPI, release workflow |
| [@docs/code-guidelines](@docs/code-guidelines.md) | Types, models, errors, style |
