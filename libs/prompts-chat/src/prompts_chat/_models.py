"""Pydantic models for prompts-chat skill."""

from pydantic import BaseModel


class Prompt(BaseModel):
    act: str
    prompt: str
    for_devs: bool
    contributor: str


class PromptList(BaseModel):
    count: int
    prompts: list[Prompt]


class PromptResult(BaseModel):
    found: bool
    prompt: Prompt | None = None
    error: str | None = None
