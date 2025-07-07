from asyncio import sleep
from re import match as re_match
from time import time
from pytdbot.types import Error

from ... import LOGGER, status_dict, task_dict_lock, intervals, DOWNLOAD_DIR
from ...core.config_manager import Config
from ...core.telegram_client import TgClient
from ..ext_utils.bot_utils import SetInterval
from ..ext_utils.exceptions import TgLinkException
from ..ext_utils.status_utils import get_readable_message


async def send_message(message, text, buttons=None, block=True):
    res = await message.reply_text(
        text=text,
        disable_web_page_preview=True,
        disable_notification=True,
        reply_markup=buttons,
    )
    if isinstance(res, Error):
        if res["message"].startswith("Trop de demandes : réessayer après"):
            LOGGER.warning(res["message"])
            if block:
                wait_for = int(res["message"].rsplit(" ", 1)[-1])
                await sleep(wait_for * 1.2)
                return await send_message(message, text, buttons)
        LOGGER.error(res["message"])
        return res["message"]
    return res


async def edit_message(message, text, buttons=None, block=True):
    res = await message.edit_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=buttons,
    )
    if isinstance(res, Error):
        if res["message"].startswith("Trop de demandes : réessayer après"):
            LOGGER.warning(res["message"])
            if block:
                wait_for = int(res["message"].rsplit(" ", 1)[-1])
                await sleep(wait_for * 1.2)
                return await edit_message(message, text, buttons)
        LOGGER.error(res["message"])
        return res["message"]
    return res


async def send_file(message, file, caption=""):
    res = await message.reply_document(
        document=file, caption=caption, disable_notification=True
    )
    if isinstance(res, Error):
        if res["message"].startswith("Trop de demandes : réessayer après"):
            LOGGER.warning(res["message"])
            wait_for = int(res["message"].rsplit(" ", 1)[-1])
            await sleep(wait_for * 1.2)
            return await send_file(message, file, caption)
        LOGGER.error(res["message"])
        return res["message"]
    return res


async def send_rss(text, chat_id, thread_id):
    app = TgClient.user or TgClient.bot
    res = await app.sendTextMessage(
        chat_id=chat_id,
        text=text,
        disable_web_page_preview=True,
        message_thread_id=thread_id,
        disable_notification=True,
    )
    if isinstance(res, Error):
        if res["message"].startswith("Trop de demandes : réessayer après"):
            LOGGER.warning(res["message"])
            wait_for = int(res["message"].rsplit(" ", 1)[-1])
            await sleep(wait_for * 1.2)
            return await send_rss(text, chat_id, thread_id)
        LOGGER.error(res["message"])
        return res["message"]
    return res


async def delete_message(message):
    res = await message.delete()
    if isinstance(res, Error):
        LOGGER.error(res["message"])


async def auto_delete_message(cmd_message=None, bot_message=None):
    await sleep(60)
    if cmd_message is not None:
        await delete_message(cmd_message)
    if bot_message is not None:
        await delete_message(bot_message)


async def delete_status():
    async with task_dict_lock:
        for key, data in list(status_dict.items()):
            try:
                await delete_message(data["message"])
                del status_dict[key]
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_message(link):
    message = None
    links = []
    if link.startswith("https://t.me/hyoshcoder/"):
        private = False
        msg = re_match(
            r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9-]+)", link
        )
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9-]+)", link
        )
        if not TgClient.user:
            raise TgLinkException("SESSION_UTILISATEUR requise pour ce lien privé !")

    chat = msg[1]
    msg_id = msg[2]
    if "-" in msg_id:
        start_id, end_id = msg_id.split("-")
        msg_id = start_id = int(start_id)
        end_id = int(end_id)
        btw = end_id - start_id
        if private:
            link = link.split("&message_id=")[0]
            links.append(f"{link}&message_id={start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}&message_id={start_id}")
        else:
            link = link.rsplit("/", 1)[0]
            links.append(f"{link}/{start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}/{start_id}")
    else:
        msg_id = int(msg_id)

    if chat.isdigit():
        chat = int(chat) if private else int(f"-100{chat}")

    if not private:
        message = await TgClient.bot.getMessage(chat_id=chat, message_id=msg_id)
        if isinstance(message, Error):
            private = True
            if not TgClient.user:
                raise TgLinkException(message["message"])

    if not private:
        return (links, "bot") if links else (message, "bot")
    elif TgClient.user:
        user_message = await TgClient.user.getMessage(chat_id=chat, message_id=msg_id)
        if isinstance(user_message, Error):
            raise TgLinkException(
                f"Vous n'avez pas accès à ce chat ! ERREUR : {user_message['message']}"
            )
        return (links, "user") if links else (user_message, "user")
    else:
        raise TgLinkException("Privé : Veuillez signaler !")


async def temp_download(msg):
    res = await msg.download(synchronous=True)
    return res.path


async def update_status_message(sid, force=False):
    if intervals["stopAll"]:
        return
    async with task_dict_lock:
        if not status_dict.get(sid):
            if obj := intervals["status"].get(sid):
                obj.cancel()
                del intervals["status"][sid]
            return
        if not force and time() - status_dict[sid]["time"] < 3:
            return
        status_dict[sid]["time"] = time()
        page_no = status_dict[sid]["page_no"]
        status = status_dict[sid]["status"]
        is_user = status_dict[sid]["is_user"]
        page_step = status_dict[sid]["page_step"]
        text, buttons = await get_readable_message(
            sid, is_user, page_no, status, page_step
        )
        if text is None:
            del status_dict[sid]
            if obj := intervals["status"].get(sid):
                obj.cancel()
                del intervals["status"][sid]
            return
        if text != status_dict[sid]["message"].text:
            message = await edit_message(
                status_dict[sid]["message"], text, buttons, block=False
            )
            if isinstance(message, str):
                if message.startswith("Telegram indique : [40"):
                    del status_dict[sid]
                    if obj := intervals["status"].get(sid):
                        obj.cancel()
                        del intervals["status"][sid]
                else:
                    LOGGER.error(
                        f"Le statut avec l'id : {sid} n'a pas été mis à jour. Erreur : {message}"
                    )
                return
            status_dict[sid]["message"].text = text
            status_dict[sid]["time"] = time()


async def send_status_message(msg, user_id=0):
    if intervals["stopAll"]:
        return
    # Correction ici: utilisation de chat_id au lieu de chat.id
    sid = user_id or (msg.chat_id if hasattr(msg, 'chat_id') else None)
    
    if sid is None:
        LOGGER.error("Impossible de déterminer l'ID de chat")
        return

    is_user = bool(user_id)
    async with task_dict_lock:
        if sid in status_dict:
            page_no = status_dict[sid]["page_no"]
            status = status_dict[sid]["status"]
            page_step = status_dict[sid]["page_step"]
            text, buttons = await get_readable_message(
                sid, is_user, page_no, status, page_step
            )
            if text is None:
                del status_dict[sid]
                if obj := intervals["status"].get(sid):
                    obj.cancel()
                    del intervals["status"][sid]
                return
            old_message = status_dict[sid]["message"]
            message = await send_message(msg, text, buttons, block=False)
            if isinstance(message, str):
                LOGGER.error(
                    f"Le statut avec l'id : {sid} n'a pas été envoyé. Erreur : {message}"
                )
                return
            await delete_message(old_message)
            message.text = text
            status_dict[sid].update({"message": message, "time": time()})
        else:
            text, buttons = await get_readable_message(sid, is_user)
            if text is None:
                return
            message = await send_message(msg, text, buttons, block=False)
            if isinstance(message, str):
                LOGGER.error(
                    f"Le statut avec l'id : {sid} n'a pas été envoyé. Erreur : {message}"
                )
                return
            message.text = text
            status_dict[sid] = {
                "message": message,
                "time": time(),
                "page_no": 1,
                "page_step": 1,
                "status": "Tous",
                "is_user": is_user,
            }
        if not intervals["status"].get(sid) and not is_user:
            intervals["status"][sid] = SetInterval(
                Config.STATUS_UPDATE_INTERVAL, update_status_message, sid
            )