from re import compile as re_compile, I, S, escape
from pytdbot.types import Message, UpdateMessageEdited, UpdateNewMessage

from ... import user_data, auth_chats, sudo_users
from ...core.config_manager import Config
from ...core.telegram_client import TgClient


class CustomFilters:

    def owner_filter(_, message, pattern=None):
        text = None

        if isinstance(message, (UpdateNewMessage, UpdateMessageEdited)):
            text = getattr(message.message.content.text, 'text', None)
            uid = getattr(message.message.sender_user, 'user_id', None)
        else:
            text = getattr(message, 'text', None)
            uid = getattr(message, 'from_id', None)

        if pattern and text:
            match = pattern.match(text)
            if not match:
                return False
        return uid == Config.OWNER_ID

    def authorized_user(_, message, pattern=None):
        text = None
        uid = None
        chat_id = getattr(message, 'chat_id', None)
        thread_id = getattr(message, 'message_thread_id', None)

        if isinstance(message, (UpdateNewMessage, UpdateMessageEdited)):
            text = getattr(message.message.content.text, 'text', None)
            uid = getattr(message.message.sender_user, 'user_id', None)
        else:
            text = getattr(message, 'text', None)
            uid = getattr(message, 'from_id', None)

        if pattern and text:
            match = pattern.match(text)
            if not match:
                return False

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

    def sudo_user(_, message, pattern=None):
        text = None
        uid = None

        if isinstance(message, (UpdateNewMessage, UpdateMessageEdited)):
            text = getattr(message.message.content.text, 'text', None)
            uid = getattr(message.message.sender_user, 'user_id', None)
        else:
            text = getattr(message, 'text', None)
            uid = getattr(message, 'from_id', None)

        if pattern and text:
            match = pattern.match(text)
            if not match:
                return False

        return bool(
            uid == Config.OWNER_ID
            or uid in user_data
            and user_data[uid].get("SUDO")
            or uid in sudo_users
        )

    def public_user(_, message, pattern=None):
        text = None

        if isinstance(message, (UpdateNewMessage, UpdateMessageEdited)):
            text = getattr(message.message.content.text, 'text', None)
        else:
            text = getattr(message, 'text', None)

        if pattern and text:
            match = pattern.match(text)
            return bool(match)


def match_cmd(cmd):
    if not isinstance(cmd, list):
        return re_compile(rf"^/{cmd}(?:@{TgClient.NAME})?(?:\s+.*)?$", flags=I | S)
    pattern = "|".join(escape(c) for c in cmd)
    return re_compile(rf"^/({pattern})(?:@{TgClient.NAME})?(?:\s+.*)?$", flags=I | S)
