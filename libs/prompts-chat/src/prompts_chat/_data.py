"""Data loading and caching for prompts.chat CSV."""

import csv
import sys

import httpx
from cmdop_skill import SkillCache

from prompts_chat._models import Prompt

CSV_URL = "https://raw.githubusercontent.com/f/prompts.chat/main/prompts.csv"
CACHE_KEY = "prompts_csv"
CACHE_TTL = 86400.0  # 24 hours

_cache = SkillCache("prompts-chat")


def load_prompts() -> list[Prompt]:
    """Load all prompts from cache or remote CSV."""
    raw: str | None = _cache.get(CACHE_KEY)

    if raw is None:
        response = httpx.get(CSV_URL, timeout=15, follow_redirects=True)
        response.raise_for_status()
        raw = response.text
        _cache.set(CACHE_KEY, raw, ttl=CACHE_TTL)

    csv.field_size_limit(sys.maxsize)
    prompts = []
    for row in csv.DictReader(raw.splitlines()):
        prompts.append(
            Prompt(
                act=row.get("act", "").strip(),
                prompt=row.get("prompt", "").strip(),
                for_devs=row.get("for_devs", "").strip().upper() == "TRUE",
                contributor=row.get("contributor", "").strip(),
            )
        )
    return prompts
