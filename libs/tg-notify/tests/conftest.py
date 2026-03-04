"""Pytest configuration and fixtures."""

import logging

import pytest


@pytest.fixture
def mock_bot_token():
    """Mock bot token for testing."""
    return "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"


@pytest.fixture
def mock_chat_id():
    """Mock chat ID for testing."""
    return -1001234567890


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset logging state before each test."""
    logging.root.handlers.clear()
    yield
    logging.root.handlers.clear()
