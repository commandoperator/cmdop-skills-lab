# CMDOP Skills Lab

Development workspace for building CMDOP skills. Contains reference implementations, shared libraries, and developer documentation.

## Quick Start

```bash
pip install cmdop-skill
cmdop-skill init
```

This scaffolds a new skill project with everything you need: manifest, tests, Makefile, and packaging config.

## Structure

```
skills-lab/
├── @docs/              Developer documentation
├── libs/               Reference skills and shared libraries
│   ├── ssl-cert-checker/   SSL certificate expiry checker
│   ├── tg-notify/          Telegram notifications
│   ├── llm-email/          Email processing for LLM
│   ├── llm-html/           HTML processing for LLM
│   ├── hello-world/        Demo skill (scaffold example)
│   └── demo-scaffold/      Auto-generated scaffold demo
└── README.md
```

## Documentation

| Doc | What it covers |
|---|---|
| [@docs/getting-started](@docs/getting-started.md) | Scaffold, project structure, manifest, LLM prompt |
| [@docs/commands](@docs/commands.md) | `@skill.command`, `Arg()`, entry points |
| [@docs/testing](@docs/testing.md) | `TestClient`, pytest patterns |
| [@docs/publishing](@docs/publishing.md) | Marketplace, PyPI, release workflow |
| [@docs/code-guidelines](@docs/code-guidelines.md) | Types, models, errors, style |
| [@docs/streamlit-dashboards](@docs/streamlit-dashboards.md) | Adding visual dashboards |

## Skill Anatomy

Every skill follows the same structure:

```
my-skill/
├── pyproject.toml          Package config
├── Makefile                Dev shortcuts
├── skill/
│   ├── config.py           Manifest (name, category, visibility)
│   └── readme.md           Instructions for the LLM agent
├── src/my_skill/
│   └── _skill.py           Commands (@skill.command)
└── tests/
```

## Common Commands

```bash
cmdop-skill init              # Scaffold new skill
cmdop-skill check-name foo    # Check PyPI availability
cmdop-skill install .         # Register locally
cmdop-skill release           # Bump + build + publish
make test                     # Run tests
make lint                     # Run linter
```

## Contributing a Skill

1. Scaffold: `cmdop-skill init`
2. Write commands in `src/<pkg>/_skill.py`
3. Write tests with `TestClient`
4. Run `make test && make lint`
5. Publish: `cmdop-skill release`
