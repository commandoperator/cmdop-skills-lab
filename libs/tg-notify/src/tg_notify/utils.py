"""
Telegram utilities and convenience functions.

Supports custom credentials per-call with fallback to environment variables.
"""

from typing import BinaryIO, Optional, Union

from .sender import TelegramSender
from .types import ParseMode


def send_telegram_message(
    message: str,
    chat_id: Optional[Union[int, str]] = None,
    bot_token: Optional[str] = None,
    parse_mode: Optional[ParseMode] = None,
    fail_silently: bool = False,
) -> bool:
    """
    Send a Telegram message using auto-configured sender.

    Args:
        message: Message text to send
        chat_id: Target chat ID (uses TELEGRAM_CHAT_ID env var if not provided)
        bot_token: Custom bot token (uses TELEGRAM_BOT_TOKEN env var if not provided)
        parse_mode: Message parse mode
        fail_silently: Don't raise exceptions on failure

    Returns:
        True if message queued successfully
    """
    sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
    return sender.send_message(
        message=message,
        parse_mode=parse_mode,
        fail_silently=fail_silently,
    )


def send_telegram_photo(
    photo: Union[str, BinaryIO],
    caption: Optional[str] = None,
    chat_id: Optional[Union[int, str]] = None,
    bot_token: Optional[str] = None,
    fail_silently: bool = False,
) -> bool:
    """
    Send a Telegram photo using auto-configured sender.

    Args:
        photo: Photo file path, URL, or file-like object
        caption: Photo caption
        chat_id: Target chat ID (uses TELEGRAM_CHAT_ID env var if not provided)
        bot_token: Custom bot token (uses TELEGRAM_BOT_TOKEN env var if not provided)
        fail_silently: Don't raise exceptions on failure

    Returns:
        True if photo queued successfully
    """
    sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
    return sender.send_photo(
        photo=photo,
        caption=caption,
        fail_silently=fail_silently,
    )


def send_telegram_document(
    document: Union[str, BinaryIO],
    caption: Optional[str] = None,
    chat_id: Optional[Union[int, str]] = None,
    bot_token: Optional[str] = None,
    fail_silently: bool = False,
) -> bool:
    """
    Send a Telegram document using auto-configured sender.

    Args:
        document: Document file path, URL, or file-like object
        caption: Document caption
        chat_id: Target chat ID (uses TELEGRAM_CHAT_ID env var if not provided)
        bot_token: Custom bot token (uses TELEGRAM_BOT_TOKEN env var if not provided)
        fail_silently: Don't raise exceptions on failure

    Returns:
        True if document queued successfully
    """
    sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
    return sender.send_document(
        document=document,
        caption=caption,
        fail_silently=fail_silently,
    )


__all__ = [
    "send_telegram_message",
    "send_telegram_photo",
    "send_telegram_document",
]
