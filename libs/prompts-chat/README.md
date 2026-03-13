# prompts-chat

> **[CMDOP Skill](https://cmdop.com/skills/prompts-chat/)** — install via [CMDOP](https://cmdop.com):
> ```
> cmdop-skill install prompts-chat
> ```

Browse and search 1400+ curated LLM prompts from [prompts.chat](https://prompts.chat) (originally "Awesome ChatGPT Prompts"). Works with ChatGPT, Claude, Gemini, Llama, and more.

## Install

```bash
pip install prompts-chat
```

## Commands

| Command | Description |
|---|---|
| `search --query <text>` | Search by act name or prompt text |
| `get --act <name>` | Get a specific prompt (case-insensitive) |
| `list [--dev]` | List all prompts (optionally dev-only) |
| `random [--dev]` | Get a random prompt |

## Examples

```bash
prompts-chat search --query "code review"
prompts-chat get --act "Linux Terminal"
prompts-chat list --dev
prompts-chat random
```

```json
{
  "ok": true,
  "found": true,
  "prompt": {
    "act": "Linux Terminal",
    "prompt": "I want you to act as a linux terminal...",
    "for_devs": true,
    "contributor": "f"
  }
}
```

## Data

Prompts are loaded from [`f/prompts.chat`](https://github.com/f/prompts.chat) (CC0 1.0 — public domain). The CSV is fetched once and cached locally using [`SkillCache`](https://github.com/commandoperator/cmdop-skill/blob/main/@docs/cache.md):

- Cache location: `~/Library/Caches/cmdop/skills/prompts-chat/prompts_csv.json` (macOS)
- TTL: 24 hours — refreshed automatically on next invocation
