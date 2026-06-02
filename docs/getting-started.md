# Getting Started

## Scaffold (recommended)

```bash
cmdop-skill init
```

The wizard prompts for name, description, category, visibility, tags, and author. It checks PyPI name availability and generates a complete project.

Programmatic alternative:

```python
from pathlib import Path
from cmdop_skill.scaffold import ScaffoldConfig, scaffold_skill

config = ScaffoldConfig(
    name="my-skill",
    description="Does useful things",
    category="security",
    tags=["network", "ssl"],
)
scaffold_skill(config, target_dir=Path("."))
```

## Project Structure

```
my-skill/
├── pyproject.toml          # Package metadata, deps, build config
├── Makefile                # Dev shortcuts: install, test, lint, publish
├── README.md
├── .gitignore
├── skill/
│   ├── config.py           # SkillConfig manifest
│   └── readme.md           # LLM system prompt
├── src/my_skill/
│   ├── __init__.py
│   └── _skill.py           # Skill commands (you add this)
└── tests/
    ├── conftest.py
    └── test_my_skill.py
```

Without the scaffold, the minimum required files are `skill/config.py` and `pyproject.toml`.

## Skill Manifest

`skill/config.py` is the typed manifest:

```python
from cmdop_skill import SkillCategory, SkillConfig

config = SkillConfig(
    category=SkillCategory.SECURITY,
    visibility="public",
)
```

`name`, `version`, `description`, `requires`, `tags`, and `repository_url` are all auto-resolved from `pyproject.toml`. Only skill-specific fields (`category`, `visibility`, `changelog`) need to be set here.

### Categories

| Category | Slug |
|---|---|
| Development | `development` |
| Code Review | `code-review` |
| Testing & QA | `testing` |
| DevOps & CI/CD | `devops` |
| Cloud & Infrastructure | `cloud` |
| Databases | `databases` |
| Git & Version Control | `git` |
| Web & Browser | `web` |
| APIs & Integrations | `apis` |
| Data & Analytics | `data` |
| AI & Agents | `ai` |
| Writing & Docs | `writing` |
| Communication | `communication` |
| Security | `security` |
| Productivity | `productivity` |
| Finance & Business | `finance` |
| Design & UI | `design` |
| Mobile | `mobile` |
| Research | `research` |
| Other | `other` |

## LLM System Prompt

`skill/readme.md` tells the agent how to use the skill:

```markdown
# my-skill

You help users check SSL certificates for domains.

When the user provides domain names, run `run.py` with the `check` command
and report the results clearly.

## Usage

cmdop my-skill "check github.com and google.com"

## Commands

- `check --domains <DOMAIN> [<DOMAIN> ...]` — check SSL certificate expiry

## Output format

For each domain show:
- Domain name
- Expiry date
- Days remaining
- Issuer organization
```

Guidelines:

- Keep it **under 4000 characters**
- Include a **commands** section with exact CLI syntax
- Include an **output format** section so the agent knows what to expect
- Write it as instructions to an AI assistant, not as docs for a human
