"""Tests for telegram shortcuts module."""

from unittest.mock import MagicMock, patch


class TestShortcuts:
    """Tests for shortcut functions."""

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_error(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_error

        # Will fail silently since no env vars set
        send_error("Test error", {"detail": "info"}, bot_token="test_token", chat_id="123")

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_success(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_success

        send_success("Task completed", {"items": 10}, bot_token="test_token", chat_id="123")

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_warning(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_warning

        send_warning("Low memory", bot_token="test_token", chat_id="123")

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_info(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_info

        send_info("Processing started", bot_token="test_token", chat_id="123")

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_stats(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_stats

        send_stats("Daily Report", {"users": 100, "orders": 50}, bot_token="test_token", chat_id="123")

    @patch("tg_notify.sender.telebot.TeleBot")
    def test_send_alert(self, mock_telebot):
        mock_bot = MagicMock()
        mock_telebot.return_value = mock_bot

        from tg_notify import send_alert

        send_alert("Server down!", {"server": "prod-1"}, bot_token="test_token", chat_id="123")

    def test_shortcuts_fail_silently(self):
        """Test that shortcuts don't raise exceptions even when not configured."""
        from tg_notify import (
            send_alert,
            send_error,
            send_info,
            send_stats,
            send_success,
            send_warning,
        )

        # These should not raise any exceptions
        send_error("test")
        send_success("test")
        send_warning("test")
        send_info("test")
        send_stats("test", {"key": "value"})
        send_alert("test")
