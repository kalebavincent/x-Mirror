from .. import user_data
from ..helper.ext_utils.bot_utils import update_user_ldata, new_task
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.message_utils import send_message


@new_task
async def authorize(_, message):
    msg = message.text.split()
    thread_id = None
    if len(msg) > 1:
        if "|" in msg:
            chat_id, thread_id = list(map(int, msg[1].split("|")))
        else:
            chat_id = int(msg[1].strip())
    elif (
        reply_to := message.reply_to
    ) and reply_to.message_id != message.message_thread_id:
        reply = await message.getRepliedMessage()
        chat_id = reply.from_id
    else:
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get("AUTH"):
        if (
            thread_id is not None
            and thread_id in user_data[chat_id].get("thread_ids", [])
            or thread_id is None
        ):
            msg = "Déjà autorisé !"
        else:
            if "thread_ids" in user_data[chat_id]:
                user_data[chat_id]["thread_ids"].append(thread_id)
            else:
                user_data[chat_id]["thread_ids"] = [thread_id]
            msg = "Autorisé"
    else:
        update_user_ldata(chat_id, "AUTH", True)
        if thread_id is not None:
            update_user_ldata(chat_id, "thread_ids", [thread_id])
        await database.update_user_data(chat_id)
        msg = "Autorisé"
    await send_message(message, msg)


@new_task
async def unauthorize(_, message):
    msg = message.text.split()
    thread_id = None
    if len(msg) > 1:
        if "|" in msg:
            chat_id, thread_id = list(map(int, msg[1].split("|")))
        else:
            chat_id = int(msg[1].strip())
    elif (
        reply_to := message.reply_to
    ) and reply_to.message_id != message.message_thread_id:
        reply = await message.getRepliedMessage()
        chat_id = reply.from_id
    else:
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat_id
    if chat_id in user_data and user_data[chat_id].get("AUTH"):
        if thread_id is not None and thread_id in user_data[chat_id].get(
            "thread_ids", []
        ):
            user_data[chat_id]["thread_ids"].remove(thread_id)
        else:
            update_user_ldata(chat_id, "AUTH", False)
        await database.update_user_data(chat_id)
        msg = "Autorisation révoquée"
    else:
        msg = "Déjà non autorisé !"
    await send_message(message, msg)


@new_task
async def add_sudo(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif message.reply_to:
        reply = await message.getRepliedMessage()
        id_ = reply.from_id
    if id_:
        if id_ in user_data and user_data[id_].get("SUDO"):
            msg = "Déjà Sudo !"
        else:
            update_user_ldata(id_, "SUDO", True)
            await database.update_user_data(id_)
            msg = "Promu en tant que Sudo"
    else:
        msg = "Donnez un ID ou répondez au message de la personne à promouvoir."
    await send_message(message, msg)


@new_task
async def remove_sudo(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif message.reply_to:
        reply = await message.getRepliedMessage()
        id_ = reply.from_id
    if id_ and id_ not in user_data or user_data[id_].get("SUDO"):
        update_user_ldata(id_, "SUDO", False)
        await database.update_user_data(id_)
        msg = "Rétrogradé"
    else:
        msg = "Donnez un ID ou répondez au message de la personne à retirer des Sudo"
    await send_message(message, msg)