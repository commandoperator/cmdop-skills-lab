"""
Telegram Sender Service.

Standalone Telegram notification service (no Django dependency).
Supports custom bot_token and chat_id per-call with fallback to environment variables.
"""

import logging
import os
from typing import Any, BinaryIO, Dict, Optional, Union

import telebot

from .exceptions import TelegramConfigError, TelegramSendError
from .formatters import EMOJI_MAP
from .queue import MessagePriority, telegram_queue
from .types import ParseMode

logger = logging.getLogger("tg_notify.sender")


class TelegramSender:
    """
    Telegram Sender for sending messages, photos, and documents.

    Provides Telegram messaging functionality with automatic configuration
    from environment variables or explicit parameters.

    All messages are queued through a global singleton queue with rate limiting
    (20 messages/second) to avoid hitting Telegram API limits.

    Supports custom bot_token and chat_id per-call with fallback to defaults.

    Environment variables:
        TELEGRAM_BOT_TOKEN: Default bot token
        TELEGRAM_CHAT_ID: Default chat ID
    """

    # Reference to EMOJI_MAP for convenience
    EMOJI_MAP = EMOJI_MAP

    # Cache for custom bot instances by token
    _custom_bots: Dict[str, telebot.TeleBot] = {}

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[Union[int, str]] = None,
        message_prefix: Optional[str] = None,
    ):
        """
        Initialize Telegram sender.

        Args:
            bot_token: Custom bot token (uses TELEGRAM_BOT_TOKEN env var if not provided)
            chat_id: Custom chat ID (uses TELEGRAM_CHAT_ID env var if not provided)
            message_prefix: Optional prefix to add to all messages (e.g., "[MyApp] ")
        """
        self._bot = None
        self._is_configured = None
        self._custom_bot_token = bot_token
        self._custom_chat_id = chat_id
        self._message_prefix = message_prefix or ""

    # ========== CONFIG PROPERTIES ==========

    @property
    def bot_token(self) -> Optional[str]:
        """Get effective bot token (custom or from env)."""
        return self._custom_bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")

    @property
    def chat_id(self) -> Optional[Union[int, str]]:
        """Get effective chat ID (custom or from env)."""
        if self._custom_chat_id:
            return self._custom_chat_id
        env_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if env_chat_id:
            # Try to convert to int if it looks like a number
            try:
                return int(env_chat_id)
            except ValueError:
                return env_chat_id
        return None

    @property
    def message_prefix(self) -> str:
        """Get message prefix."""
        return self._message_prefix

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured (has bot token)."""
        if self._is_configured is None:
            token = self.bot_token
            self._is_configured = token is not None and len(token.strip()) > 0
        return self._is_configured

    # ========== BOT MANAGEMENT ==========

    @property
    def bot(self) -> telebot.TeleBot:
        """Get Telegram bot instance (custom or default)."""
        return self._get_bot()

    def _get_bot(self, bot_token: Optional[str] = None) -> telebot.TeleBot:
        """Get bot instance by token (cached)."""
        token = bot_token or self.bot_token

        if not token:
            raise TelegramConfigError(
                "No bot token provided. Set TELEGRAM_BOT_TOKEN environment variable "
                "or pass bot_token parameter."
            )

        if token not in self._custom_bots:
            try:
                self._custom_bots[token] = telebot.TeleBot(token)
                logger.debug(f"Created bot instance (token: {token[:10]}...)")
            except Exception as e:
                raise TelegramConfigError(f"Failed to initialize Telegram bot: {e}")

        return self._custom_bots[token]

    # ========== RESOLVERS ==========

    def _resolve_chat_id(
        self, chat_id: Optional[Union[int, str]] = None
    ) -> Optional[Union[int, str]]:
        """Resolve chat_id from param > instance > env."""
        return chat_id or self.chat_id

    def _resolve_parse_mode(self, parse_mode: Optional[ParseMode] = None) -> Optional[str]:
        """Resolve parse_mode and convert to string."""
        if parse_mode:
            if isinstance(parse_mode, ParseMode):
                return parse_mode.value
            return parse_mode
        return None

    # ========== CONFIG INFO ==========

    def get_config_info(self) -> Dict[str, Any]:
        """Get Telegram configuration information with queue stats."""
        queue_stats = telegram_queue.get_stats()

        token = self.bot_token
        chat = self.chat_id

        return {
            "configured": self.is_configured,
            "bot_token": f"{token[:10]}..." if token else "Not configured",
            "chat_id": chat or "Not configured",
            "message_prefix": self._message_prefix or "None",
            "rate_limit": "20 messages/second",
            **queue_stats,
        }

    @staticmethod
    def get_queue_size() -> int:
        """Get current number of messages in the global queue."""
        return telegram_queue.size()

    @staticmethod
    def get_queue_stats() -> dict:
        """Get detailed queue statistics."""
        return telegram_queue.get_stats()

    # ========== SEND METHODS ==========

    def _enqueue_message(self, func, priority=MessagePriority.NORMAL, *args, **kwargs):
        """Add message to global queue with priority and rate limiting."""
        telegram_queue.enqueue(func, priority, *args, **kwargs)

    def send_message(
        self,
        message: str,
        chat_id: Optional[Union[int, str]] = None,
        bot_token: Optional[str] = None,
        parse_mode: Optional[ParseMode] = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        fail_silently: bool = False,
        priority: int = MessagePriority.NORMAL,
    ) -> bool:
        """
        Send a text message to Telegram via global queue (non-blocking, rate-limited).

        Args:
            message: Message text to send
            chat_id: Target chat ID (uses default if not provided)
            bot_token: Custom bot token (uses default if not provided)
            parse_mode: Message parse mode (Markdown, MarkdownV2, HTML)
            disable_notification: Send silently without notification
            reply_to_message_id: Message ID to reply to
            fail_silently: Don't raise exceptions on failure
            priority: Message priority (use MessagePriority constants)

        Returns:
            True if message was queued successfully
        """
        try:
            effective_token = bot_token or self.bot_token

            if not effective_token:
                error_msg = (
                    "Telegram is not configured. Set TELEGRAM_BOT_TOKEN environment variable "
                    "or pass bot_token parameter."
                )
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            target_chat_id = self._resolve_chat_id(chat_id)
            if not target_chat_id:
                error_msg = (
                    "No chat_id provided. Set TELEGRAM_CHAT_ID environment variable "
                    "or pass chat_id parameter."
                )
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            parse_mode_str = self._resolve_parse_mode(parse_mode)
            bot_instance = self._get_bot(effective_token)

            def _do_send():
                prefixed_message = f"{self._message_prefix}{message}"
                bot_instance.send_message(
                    chat_id=target_chat_id,
                    text=prefixed_message,
                    parse_mode=parse_mode_str,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                )
                logger.info(f"Telegram message sent successfully to chat {target_chat_id}")

            self._enqueue_message(_do_send, priority=priority)
            return True

        except TelegramConfigError:
            raise
        except Exception as e:
            error_msg = f"Failed to send Telegram message: {e}"
            logger.error(error_msg)
            if not fail_silently:
                raise TelegramSendError(error_msg) from e
            return False

    def send_photo(
        self,
        photo: Union[str, BinaryIO],
        caption: Optional[str] = None,
        chat_id: Optional[Union[int, str]] = None,
        bot_token: Optional[str] = None,
        parse_mode: Optional[ParseMode] = None,
        fail_silently: bool = False,
        priority: int = MessagePriority.NORMAL,
    ) -> bool:
        """
        Send a photo to Telegram via global queue (non-blocking, rate-limited).

        Args:
            photo: Photo file path, URL, or file-like object
            caption: Photo caption
            chat_id: Target chat ID (uses default if not provided)
            bot_token: Custom bot token (uses default if not provided)
            parse_mode: Caption parse mode
            fail_silently: Don't raise exceptions on failure
            priority: Message priority

        Returns:
            True if photo was queued successfully
        """
        try:
            effective_token = bot_token or self.bot_token

            if not effective_token:
                error_msg = "Telegram is not configured"
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            target_chat_id = self._resolve_chat_id(chat_id)
            if not target_chat_id:
                error_msg = "No chat_id provided and none configured"
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            parse_mode_str = self._resolve_parse_mode(parse_mode)
            bot_instance = self._get_bot(effective_token)

            def _do_send():
                prefixed_caption = (
                    f"{self._message_prefix}{caption}"
                    if caption
                    else self._message_prefix.strip() if self._message_prefix else None
                )
                bot_instance.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=prefixed_caption,
                    parse_mode=parse_mode_str,
                )
                logger.info(f"Telegram photo sent successfully to chat {target_chat_id}")

            self._enqueue_message(_do_send, priority=priority)
            return True

        except TelegramConfigError:
            raise
        except Exception as e:
            error_msg = f"Failed to send Telegram photo: {e}"
            logger.error(error_msg)
            if not fail_silently:
                raise TelegramSendError(error_msg) from e
            return False

    def send_document(
        self,
        document: Union[str, BinaryIO],
        caption: Optional[str] = None,
        chat_id: Optional[Union[int, str]] = None,
        bot_token: Optional[str] = None,
        parse_mode: Optional[ParseMode] = None,
        fail_silently: bool = False,
        priority: int = MessagePriority.NORMAL,
    ) -> bool:
        """
        Send a document to Telegram via global queue (non-blocking, rate-limited).

        Args:
            document: Document file path, URL, or file-like object
            caption: Document caption
            chat_id: Target chat ID (uses default if not provided)
            bot_token: Custom bot token (uses default if not provided)
            parse_mode: Caption parse mode
            fail_silently: Don't raise exceptions on failure
            priority: Message priority

        Returns:
            True if document was queued successfully
        """
        try:
            effective_token = bot_token or self.bot_token

            if not effective_token:
                error_msg = "Telegram is not configured"
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            target_chat_id = self._resolve_chat_id(chat_id)
            if not target_chat_id:
                error_msg = "No chat_id provided and none configured"
                logger.error(error_msg)
                if not fail_silently:
                    raise TelegramConfigError(error_msg)
                return False

            parse_mode_str = self._resolve_parse_mode(parse_mode)
            bot_instance = self._get_bot(effective_token)

            def _do_send():
                prefixed_caption = (
                    f"{self._message_prefix}{caption}"
                    if caption
                    else self._message_prefix.strip() if self._message_prefix else None
                )
                bot_instance.send_document(
                    chat_id=target_chat_id,
                    document=document,
                    caption=prefixed_caption,
                    parse_mode=parse_mode_str,
                )
                logger.info(f"Telegram document sent successfully to chat {target_chat_id}")

            self._enqueue_message(_do_send, priority=priority)
            return True

        except TelegramConfigError:
            raise
        except Exception as e:
            error_msg = f"Failed to send Telegram document: {e}"
            logger.error(error_msg)
            if not fail_silently:
                raise TelegramSendError(error_msg) from e
            return False

    # ========== BOT INFO ==========

    def get_me(self) -> Optional[Dict[str, Any]]:
        """Get information about the bot."""
        try:
            if not self.is_configured:
                return None

            bot_info = self.bot.get_me()
            return {
                "id": bot_info.id,
                "is_bot": bot_info.is_bot,
                "first_name": bot_info.first_name,
                "username": bot_info.username,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries,
            }
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None

    def get_updates(self, limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        """
        Get recent updates (messages) received by the bot.

        Useful for discovering chat_id of groups/channels where the bot is added.
        Note: Bot must have received at least one message after being added to a chat.

        Args:
            limit: Maximum number of updates to retrieve (1-100)
            offset: Identifier of the first update to be returned

        Returns:
            List of update dicts with chat info
        """
        try:
            if not self.is_configured:
                return []

            updates = self.bot.get_updates(limit=min(limit, 100), offset=offset)
            result = []

            for update in updates:
                update_data = {"update_id": update.update_id}

                # Extract message info if present
                message = update.message or update.edited_message or update.channel_post
                if message:
                    chat = message.chat
                    update_data["chat"] = {
                        "id": chat.id,
                        "type": chat.type,
                        "title": getattr(chat, "title", None),
                        "username": getattr(chat, "username", None),
                        "first_name": getattr(chat, "first_name", None),
                        "last_name": getattr(chat, "last_name", None),
                    }
                    update_data["message"] = {
                        "message_id": message.message_id,
                        "date": message.date,
                        "text": getattr(message, "text", None),
                    }
                    if message.from_user:
                        update_data["from"] = {
                            "id": message.from_user.id,
                            "username": getattr(message.from_user, "username", None),
                            "first_name": getattr(message.from_user, "first_name", None),
                        }

                result.append(update_data)

            return result
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return []

    def get_chats(self) -> list[Dict[str, Any]]:
        """
        Get unique chats where the bot received messages.

        Convenience method that extracts unique chats from recent updates.
        Use this to discover chat_id for configuration.

        Returns:
            List of unique chat dicts: [{"id": -123, "type": "group", "title": "My Group"}, ...]
        """
        updates = self.get_updates(limit=100)
        seen_ids = set()
        chats = []

        for update in updates:
            chat = update.get("chat")
            if chat and chat["id"] not in seen_ids:
                seen_ids.add(chat["id"])
                chats.append(chat)

        return chats

    # ========== CLASS METHOD SHORTCUTS ==========

    @classmethod
    def send_error(cls, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Send error notification. See shortcuts.send_error for details."""
        from .shortcuts import send_error
        send_error(error, context)

    @classmethod
    def send_success(cls, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Send success notification. See shortcuts.send_success for details."""
        from .shortcuts import send_success
        send_success(message, details)

    @classmethod
    def send_warning(cls, warning: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Send warning notification. See shortcuts.send_warning for details."""
        from .shortcuts import send_warning
        send_warning(warning, context)

    @classmethod
    def send_info(cls, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Send info notification. See shortcuts.send_info for details."""
        from .shortcuts import send_info
        send_info(message, data)

    @classmethod
    def send_stats(cls, title: str, stats: Dict[str, Any]) -> None:
        """Send stats notification. See shortcuts.send_stats for details."""
        from .shortcuts import send_stats
        send_stats(title, stats)


__all__ = [
    "TelegramSender",
]
