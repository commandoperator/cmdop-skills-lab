"""Tests for prompts-chat skill."""

from unittest.mock import patch

import pytest

from prompts_chat._models import Prompt, PromptList, PromptResult

SAMPLE_PROMPTS = [
    Prompt(act="Linux Terminal", prompt="Act as a linux terminal...", for_devs=True, contributor="f"),
    Prompt(act="English Translator", prompt="I want you to translate...", for_devs=False, contributor="f"),
    Prompt(act="Job Interviewer", prompt="Act as a job interviewer...", for_devs=False, contributor="f"),
]


@pytest.fixture(autouse=True)
def mock_load():
    with patch("prompts_chat._skill.load_prompts", return_value=SAMPLE_PROMPTS):
        yield


def test_search_by_act():
    from prompts_chat._skill import search
    result = search(query="linux")
    assert result["count"] == 1
    assert result["prompts"][0]["act"] == "Linux Terminal"


def test_search_no_results():
    from prompts_chat._skill import search
    result = search(query="zzznomatch")
    assert result["count"] == 0


def test_search_dev_filter():
    from prompts_chat._skill import search
    result = search(query="", dev=True)
    assert all(p["for_devs"] for p in result["prompts"])


def test_get_exact():
    from prompts_chat._skill import get
    result = get(act="Linux Terminal")
    assert result["found"] is True
    assert result["prompt"]["act"] == "Linux Terminal"


def test_get_case_insensitive():
    from prompts_chat._skill import get
    result = get(act="linux terminal")
    assert result["found"] is True


def test_get_not_found():
    from prompts_chat._skill import get
    result = get(act="Nonexistent Prompt XYZ")
    assert result["found"] is False
    assert result["error"] is not None


def test_list_all():
    from prompts_chat._skill import list
    result = list(dev=False)
    assert result["count"] == 3


def test_list_dev_only():
    from prompts_chat._skill import list
    result = list(dev=True)
    assert result["count"] == 1


def test_random_returns_prompt():
    from prompts_chat._skill import random
    result = random(dev=False)
    assert result["found"] is True
    assert result["prompt"] is not None


def test_random_dev_only():
    from prompts_chat._skill import random
    result = random(dev=True)
    assert result["found"] is True
    assert result["prompt"]["for_devs"] is True
