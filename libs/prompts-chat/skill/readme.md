# prompts-chat

Browse and search the [prompts.chat](https://prompts.chat) library — 200+ curated LLM prompts (ChatGPT, Claude, Gemini, etc.). Data is fetched from the official CSV and cached locally for 24 hours.

## Commands

- `search <query>` — search prompts by act name or prompt text
- `get <act>` — get a specific prompt by act name (case-insensitive)
- `list [--dev]` — list all available prompts (optionally filter to dev-oriented ones)
- `random [--dev]` — get a random prompt

## Usage

```
prompts-chat search --query "linux terminal"
prompts-chat get --act "Linux Terminal"
prompts-chat list --dev
prompts-chat random
prompts-chat random --dev
```
