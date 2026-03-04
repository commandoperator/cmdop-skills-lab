"""Tests for telegram module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from tg_notify import (
    EMOJI_MAP,
    MessagePriority,
    ParseMode,
    TelegramConfigError,
    TelegramSender,
    format_message_with_context,
    format_to_yaml,
    telegram_queue,
)


class TestParseMode:
    """Tests for ParseMode enum."""

    def test_parse_modes(self):
        assert ParseMode.HTML.value == "HTML"
        assert ParseMode.MARKDOWN.value == "Markdown"
        assert ParseMode.MARKDOWN_V2.value == "MarkdownV2"


class TestMessagePriority:
    """Tests for MessagePriority."""

    def test_priority_levels(self):
        assert MessagePriority.CRITICAL == 1
        assert MessagePriority.HIGH == 2
        assert MessagePriority.NORMAL == 3
        assert MessagePriority.LOW == 4

    def test_priority_ordering(self):
        assert MessagePriority.CRITICAL < MessagePriority.HIGH
        assert MessagePriority.HIGH < MessagePriority.NORMAL
        assert MessagePriority.NORMAL < MessagePriority.LOW


class TestFormatters:
    """Tests for formatters module."""

    def test_emoji_map(self):
        assert "success" in EMOJI_MAP
        assert "error" in EMOJI_MAP
        assert "warning" in EMOJI_MAP
        assert "info" in EMOJI_MAP
        assert "stats" in EMOJI_MAP
        assert "alert" in EMOJI_MAP

    def test_format_to_yaml(self):
        data = {"key": "value", "number": 42}
        result = format_to_yaml(data)
        assert "key: value" in result
        assert "number: 42" in result

    def test_format_to_yaml_unicode(self):
        data = {"message": "Привет мир"}
        result = format_to_yaml(data)
        assert "Привет мир" in result

    def test_format_message_with_context(self):
        result = format_message_with_context(
            emoji_key="success",
            title="Test Title",
            message="Test message body",
            context={"key": "value"},
        )
        assert "<b>Test Title</b>" in result
        assert "Test message body" in result
        assert "<pre>" in result
        assert "key: value" in result

    def test_format_message_without_context(self):
        result = format_message_with_context(
            emoji_key="error",
            title="Error",
            message="Something went wrong",
            context=None,
        )
        assert "<b>Error</b>" in result
        assert "Something went wrong" in result
        assert "<pre>" not in result


class TestTelegramSender:
    """Tests for TelegramSender class."""

    def test_init_with_credentials(self, mock_bot_token, mock_chat_id):
        sender = TelegramSender(
            bot_token=mock_bot_token,
            chat_id=mock_chat_id,
            message_prefix="[Test] ",
        )
        assert sender.bot_token == mock_bot_token
        assert sender.chat_id == mock_chat_id
        assert sender.message_prefix == "[Test] "

    def test_init_from_env_vars(self):
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "env_token",
            "TELEGRAM_CHAT_ID": "12345",
        }):
            sender = TelegramSender()
            assert sender.bot_token == "env_token"
            assert sender.chat_id == 12345

    def test_is_configured_true(self, mock_bot_token):
        sender = TelegramSender(bot_token=mock_bot_token)
        assert sender.is_configured is True

    def test_is_configured_false(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            sender = TelegramSender()
            assert sender.is_configured is False

    def test_get_config_info(self, mock_bot_token, mock_chat_id):
        sender = TelegramSender(
            bot_token=mock_bot_token,
            chat_id=mock_chat_id,
        )
        info = sender.get_config_info()
        assert info["configured"] is True
        assert "queue_size" in info
        assert "max_size" in info

    def test_send_message_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            os.environ.pop("TELEGRAM_CHAT_ID", None)
            sender = TelegramSender()
            with pytest.raises(TelegramConfigError):
                sender.send_message("test", fail_silently=False)

    def test_send_message_no_chat_id(self, mock_bot_token):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TELEGRAM_CHAT_ID", None)
            sender = TelegramSender(bot_token=mock_bot_token)
            with pytest.raises(TelegramConfigError):
                sender.send_message("test", fail_silently=False)

    def test_send_message_fail_silently(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            sender = TelegramSender()
            result = sender.send_message("test", fail_silently=True)
            assert result is False

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_message_success(self, mock_telebot, mock_bot_token, mock_chat_id):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        sender = TelegramSender(
            bot_token=mock_bot_token,
            chat_id=mock_chat_id,
        )
        result = sender.send_message("Hello!")
        assert result is True

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_photo_success(self, mock_telebot, mock_bot_token, mock_chat_id):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        sender = TelegramSender(
            bot_token=mock_bot_token,
            chat_id=mock_chat_id,
        )
        result = sender.send_photo("http://example.com/image.jpg", caption="Test")
        assert result is True

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_document_success(self, mock_telebot, mock_bot_token, mock_chat_id):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        sender = TelegramSender(
            bot_token=mock_bot_token,
            chat_id=mock_chat_id,
        )
        result = sender.send_document("http://example.com/file.pdf", caption="Test")
        assert result is True


class TestTelegramQueue:
    """Tests for TelegramMessageQueue."""

    def test_singleton(self):
        from tg_notify.queue import TelegramMessageQueue
        q1 = TelegramMessageQueue()
        q2 = TelegramMessageQueue()
        assert q1 is q2

    def test_get_stats(self):
        stats = telegram_queue.get_stats()
        assert "queue_size" in stats
        assert "max_size" in stats
        assert "usage_percent" in stats
        assert "status" in stats

    def test_enqueue(self):
        initial_size = telegram_queue.size()
        telegram_queue.enqueue(lambda: None, MessagePriority.LOW)
        # Queue should have at least same size or more
        assert telegram_queue.size() >= initial_size


class TestExceptions:
    """Tests for exception classes."""

    def test_telegram_error_hierarchy(self):
        from tg_notify import (
            TelegramConfigError,
            TelegramError,
            TelegramSendError,
        )
        assert issubclass(TelegramConfigError, TelegramError)
        assert issubclass(TelegramSendError, TelegramError)

    def test_exception_messages(self):
        from tg_notify import TelegramConfigError
        error = TelegramConfigError("Test error message")
        assert str(error) == "Test error message"
