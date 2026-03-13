"""prompts-chat CMDOP skill — browse and search prompts.chat library."""

import random as _random

from cmdop_skill import Arg, Skill

from prompts_chat._data import load_prompts
from prompts_chat._models import PromptList, PromptResult

skill = Skill()


@skill.command
def search(
    query: str = Arg(help="Search term (matches act name or prompt text)", required=True),
    dev: bool = Arg("--dev", default=False, help="Filter to developer-oriented prompts only"),
) -> dict:
    """Search prompts by act name or prompt text."""
    prompts = load_prompts()
    q = query.lower()
    results = [
        p for p in prompts
        if q in p.act.lower() or q in p.prompt.lower()
        if not dev or p.for_devs
    ]
    return PromptList(count=len(results), prompts=results).model_dump()


@skill.command
def get(
    act: str = Arg(help="Act name to retrieve (case-insensitive)", required=True),
) -> dict:
    """Get a specific prompt by act name."""
    prompts = load_prompts()
    act_lower = act.lower()
    match = next((p for p in prompts if p.act.lower() == act_lower), None)
    if match:
        return PromptResult(found=True, prompt=match).model_dump()
    # fallback: partial match
    partial = next((p for p in prompts if act_lower in p.act.lower()), None)
    if partial:
        return PromptResult(found=True, prompt=partial).model_dump()
    return PromptResult(found=False, error=f"No prompt found for act: {act!r}").model_dump()


@skill.command
def list(
    dev: bool = Arg("--dev", default=False, help="Show only developer-oriented prompts"),
) -> dict:
    """List all available prompts."""
    prompts = load_prompts()
    if dev:
        prompts = [p for p in prompts if p.for_devs]
    return PromptList(count=len(prompts), prompts=prompts).model_dump()


@skill.command
def random(
    dev: bool = Arg("--dev", default=False, help="Pick from developer-oriented prompts only"),
) -> dict:
    """Get a random prompt."""
    prompts = load_prompts()
    if dev:
        prompts = [p for p in prompts if p.for_devs]
    if not prompts:
        return PromptResult(found=False, error="No prompts available").model_dump()
    pick = _random.choice(prompts)
    return PromptResult(found=True, prompt=pick).model_dump()


def main() -> None:
    """CLI entry point."""
    skill.run()
