from re import compile as re_compile, I, S, escape
from pytdbot.types import Message

from ... import user_data, auth_chats, sudo_users
from ...core.config_manager import Config
from ...core.telegram_client import TgClient


class CustomFilters:

    def owner_filter(_, message, pattern=None):
        # Gestion des messages édités et différents types de contenu
        text_content = None
        if hasattr(message, 'text'):
            text_content = message.text
        elif hasattr(message, 'content') and hasattr(message.content, 'text'):
            text_content = message.content.text
        
        if pattern:
            if not text_content:
                return False
            match = pattern.match(text_content)
            if not match:
                return False
        return message.from_id == Config.OWNER_ID

    def authorized_user(_, message, pattern=None):
        # Gestion des messages édités et différents types de contenu
        text_content = None
        if hasattr(message, 'text'):
            text_content = message.text
        elif hasattr(message, 'content') and hasattr(message.content, 'text'):
            text_content = message.content.text
        
        if pattern:
            if not text_content:
                return False
            match = pattern.match(text_content)
            if not match:
                return False
        
        uid = message.from_id
        chat_id = message.chat_id
        thread_id = getattr(message, 'message_thread_id', None)
        return bool(
            uid == Config.OWNER_ID
            or (
                uid in user_data
                and (
                    user_data[uid].get("AUTH", False)
                    or user_data[uid].get("SUDO", False)
                )
            )
            or (
                chat_id in user_data
                and user_data[chat_id].get("AUTH", False)
                and (
                    thread_id is None
                    or thread_id in user_data[chat_id].get("thread_ids", [])
                )
            )
            or uid in sudo_users
            or uid in auth_chats
            or chat_id in auth_chats
            and (
                auth_chats[chat_id]
                and thread_id
                and thread_id in auth_chats[chat_id]
                or not auth_chats[chat_id]
            )
        )

    def sudo_user(self, event, pattern=None):
        # Get user ID based on event type
        if hasattr(event, 'sender_user_id'):  # CallbackQuery events
            uid = event.sender_user_id
        elif hasattr(event, 'from_id') and hasattr(event.from_id, 'user_id'):  # Message events
            uid = event.from_id.user_id
        else:
            return False
        
        # Gestion du texte pour différents types d'événements
        text_content = None
        if hasattr(event, 'text'):
            text_content = event.text
        elif hasattr(event, 'content') and hasattr(event.content, 'text'):
            text_content = event.content.text
        
        if pattern:
            if not text_content:
                return False
            match = pattern.match(text_content)
            if not match:
                return False
        
        return bool(
            uid == Config.OWNER_ID
            or uid in user_data
            and user_data[uid].get("SUDO")
            or uid in sudo_users
        )

    def public_user(self, message, pattern=None):
        # Gestion des messages édités et différents types de contenu
        text_content = None
        if hasattr(message, 'text'):
            text_content = message.text
        elif hasattr(message, 'content') and hasattr(message.content, 'text'):
            text_content = message.content.text
        
        if pattern:
            if not text_content:
                return False
            match = pattern.match(text_content)
            return bool(match)
        return False


def match_cmd(cmd):
    if not isinstance(cmd, list):
        return re_compile(rf"^/{cmd}(?:@{TgClient.NAME})?(?:\s+.*)?$", flags=I | S)
    pattern = "|".join(escape(c) for c in cmd)
    return re_compile(rf"^/({pattern})(?:@{TgClient.NAME})?(?:\s+.*)?$", flags=I | S)