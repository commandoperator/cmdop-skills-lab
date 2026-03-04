"""
Telegram Shortcut Functions.

Convenience functions for common notification patterns.
All functions use environment variables for config and fail silently.

Required environment variables:
    TELEGRAM_BOT_TOKEN: Bot token
    TELEGRAM_CHAT_ID: Default chat ID
"""

from typing import Any, Dict, Optional

from .formatters import EMOJI_MAP, format_to_yaml
from .queue import MessagePriority
from .types import ParseMode


def send_error(
    error: str,
    context: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send error notification with HIGH priority.

    Args:
        error: Error message
        context: Optional context dict to include
        bot_token: Override bot token (uses TELEGRAM_BOT_TOKEN if not provided)
        chat_id: Override chat ID (uses TELEGRAM_CHAT_ID if not provided)
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['error']} <b>Error</b>\n\n{error}"
        if context:
            text += "\n\n<pre>" + format_to_yaml(context) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.HIGH,
            fail_silently=True,
        )
    except Exception:
        pass


def send_success(
    message: str,
    details: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send success notification with NORMAL priority.

    Args:
        message: Success message
        details: Optional details dict to include
        bot_token: Override bot token
        chat_id: Override chat ID
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['success']} <b>Success</b>\n\n{message}"
        if details:
            text += "\n\n<pre>" + format_to_yaml(details) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.NORMAL,
            fail_silently=True,
        )
    except Exception:
        pass


def send_warning(
    warning: str,
    context: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send warning notification with HIGH priority.

    Args:
        warning: Warning message
        context: Optional context dict to include
        bot_token: Override bot token
        chat_id: Override chat ID
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['warning']} <b>Warning</b>\n\n{warning}"
        if context:
            text += "\n\n<pre>" + format_to_yaml(context) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.HIGH,
            fail_silently=True,
        )
    except Exception:
        pass


def send_info(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send informational message with NORMAL priority.

    Args:
        message: Info message
        data: Optional data dict to include
        bot_token: Override bot token
        chat_id: Override chat ID
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['info']} <b>Info</b>\n\n{message}"
        if data:
            text += "\n\n<pre>" + format_to_yaml(data) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.NORMAL,
            fail_silently=True,
        )
    except Exception:
        pass


def send_stats(
    title: str,
    stats: Dict[str, Any],
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send statistics data with LOW priority.

    Args:
        title: Stats title
        stats: Stats dict to format
        bot_token: Override bot token
        chat_id: Override chat ID
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['stats']} <b>{title}</b>"
        text += "\n\n<pre>" + format_to_yaml(stats) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.LOW,
            fail_silently=True,
        )
    except Exception:
        pass


def send_alert(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> None:
    """
    Send critical alert with CRITICAL priority.

    Args:
        message: Alert message
        context: Optional context dict to include
        bot_token: Override bot token
        chat_id: Override chat ID
    """
    try:
        from .sender import TelegramSender

        sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)
        text = f"{EMOJI_MAP['alert']} <b>ALERT</b>\n\n{message}"
        if context:
            text += "\n\n<pre>" + format_to_yaml(context) + "</pre>"
        sender.send_message(
            text,
            parse_mode=ParseMode.HTML,
            priority=MessagePriority.CRITICAL,
            fail_silently=True,
        )
    except Exception:
        pass


__all__ = [
    "send_error",
    "send_success",
    "send_warning",
    "send_info",
    "send_stats",
    "send_alert",
]
