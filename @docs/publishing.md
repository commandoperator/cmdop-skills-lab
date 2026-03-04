# Publishing

## Workflow

```
develop → test → publish → install
```

## Local Install (symlink)

Register a skill on your machine without publishing:

```bash
cmdop-skill install .
# ✓ Installed my-skill → ~/Library/Application Support/cmdop/skills/my-skill

cmdop-skill uninstall my-skill
```

## CMDOP Marketplace

```bash
cmdop-skill publish
```

Interactive mode prompts for confirmation. For CI:

```bash
cmdop-skill publish --json
```

## PyPI + CMDOP (release)

Full release pipeline — bump version, build, upload to PyPI, publish to marketplace:

```bash
cmdop-skill release                     # bump patch + build + PyPI + CMDOP
cmdop-skill release -b minor            # bump minor
cmdop-skill release -b major            # bump major
cmdop-skill release --no-bump           # current version, no bump
cmdop-skill release --test-pypi         # TestPyPI only (skips CMDOP)
cmdop-skill release --no-publish        # PyPI only (skips CMDOP)
```

## Version Bumping

Standalone version bump (no build/upload):

```bash
cmdop-skill bump                        # patch: 0.1.0 → 0.1.1
cmdop-skill bump --minor                # minor: 0.1.1 → 0.2.0
cmdop-skill bump --major                # major: 0.2.0 → 1.0.0
```

## Check Name on PyPI

Before publishing, check if the name is taken:

```bash
cmdop-skill check-name my-cool-skill
# ✓ my-cool-skill is available on PyPI
```

## API Key

Required for marketplace operations. Resolved in order:

1. `--api-key` flag
2. `CMDOP_API_KEY` environment variable
3. Saved config
4. Interactive prompt

```bash
cmdop-skill config set-key              # interactive (masked input)
cmdop-skill config set-key cmdop_xxx    # direct
cmdop-skill config show
cmdop-skill config reset
```

On 401/403 errors, the CLI prompts for a new key automatically.

## Makefile Shortcuts

The scaffold generates these targets:

```bash
make install          # pip install -e '.[dev]'
make test             # pytest tests/ -v
make lint             # ruff check src/
make install-skill    # cmdop-skill install .
make publish          # cmdop-skill publish --path .
make release          # cmdop-skill release .
```
