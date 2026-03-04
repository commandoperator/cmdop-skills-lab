# cmdop-sdkrouter

> **[CMDOP Skill](https://cmdop.com/skills/cmdop-sdkrouter/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install cmdop-sdkrouter
> ```
CMDOP skill wrapper for [SDKRouter](https://sdkrouter.com) — unified AI services SDK.

## Install

```bash
pip install cmdop-sdkrouter
```

## Quick start

```bash
export SDKROUTER_API_KEY=your-key
cmdop-sdkrouter chat --model openai/gpt-4o --message "Hello!"
cmdop-sdkrouter search --query "AI news"
cmdop-sdkrouter --help
```
