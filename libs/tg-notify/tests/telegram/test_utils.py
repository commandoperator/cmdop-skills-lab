"""Tests for telegram utils module."""

from unittest.mock import MagicMock, patch


class TestUtils:
    """Tests for utility functions."""

    @patch("tg_notify.utils.TelegramSender")
    def test_send_telegram_message(self, mock_sender_class):
        mock_sender = MagicMock()
        mock_sender.send_message.return_value = True
        mock_sender_class.return_value = mock_sender

        from tg_notify import send_telegram_message

        result = send_telegram_message(
            "Hello",
            bot_token="token",
            chat_id="123",
        )
        assert result is True
        mock_sender.send_message.assert_called_once()

    @patch("tg_notify.utils.TelegramSender")
    def test_send_telegram_photo(self, mock_sender_class):
        mock_sender = MagicMock()
        mock_sender.send_photo.return_value = True
        mock_sender_class.return_value = mock_sender

        from tg_notify import send_telegram_photo

        result = send_telegram_photo(
            "http://example.com/image.jpg",
            caption="Test",
            bot_token="token",
            chat_id="123",
        )
        assert result is True
        mock_sender.send_photo.assert_called_once()

    @patch("tg_notify.utils.TelegramSender")
    def test_send_telegram_document(self, mock_sender_class):
        mock_sender = MagicMock()
        mock_sender.send_document.return_value = True
        mock_sender_class.return_value = mock_sender

        from tg_notify import send_telegram_document

        result = send_telegram_document(
            "http://example.com/file.pdf",
            caption="Report",
            bot_token="token",
            chat_id="123",
        )
        assert result is True
        mock_sender.send_document.assert_called_once()
