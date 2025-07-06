from .. import (
    task_dict,
    task_dict_lock,
    user_data,
    queued_up,
    queued_dl,
    queue_dict_lock,
)
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_task_by_gid
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.message_utils import send_message
from ..helper.ext_utils.task_manager import start_dl_from_queued, start_up_from_queued


@new_task
async def remove_from_queue(_, message):
    user_id = message.from_id
    msg = message.text.split()
    status = msg[1] if len(msg) > 1 and msg[1] in ["fd", "fu"] else ""
    if status and len(msg) > 2 or not status and len(msg) > 1:
        gid = msg[2] if status else msg[1]
        task = await get_task_by_gid(gid)
        if task is None:
            await send_message(message, f"GID: <code>{gid}</code> non trouvé.")
            return
    elif reply_to := message.reply_to:
        async with task_dict_lock:
            task = task_dict.get(reply_to.message_id)
        if task is None:
            await send_message(message, "Ce n'est pas une tâche active !")
            return
    elif len(msg) in {1, 2}:
        msg = f"""Répondez à un message de commande actif qui a démarré le téléchargement/upload.
<code>/{BotCommands.ForceStartCommand[0]}</code> fd (pour le retirer de la file de téléchargement) ou fu (pour le retirer de la file d'upload) ou rien pour le retirer des deux files.
Vous pouvez aussi envoyer <code>/{BotCommands.ForceStartCommand[0]} GID</code> fu|fd ou seulement le GID pour forcer le démarrage en retirant la tâche de la file !
Exemples :
<code>/{BotCommands.ForceStartCommand[1]}</code> GID fu (forcer l'upload)
<code>/{BotCommands.ForceStartCommand[1]}</code> GID (forcer téléchargement et upload)
Par réponse à une commande :
<code>/{BotCommands.ForceStartCommand[1]}</code> (forcer téléchargement et upload)
<code>/{BotCommands.ForceStartCommand[1]}</code> fd (forcer téléchargement)
"""
        await send_message(message, msg)
        return
    if (
        Config.OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (user_id not in user_data or not user_data[user_id].get("SUDO"))
    ):
        await send_message(message, "Cette tâche ne vous appartient pas !")
        return
    listener = task.listener
    msg = ""
    async with queue_dict_lock:
        if status == "fu":
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Tâche forcée pour l'upload !"
            else:
                msg = "Forçage d'upload activé pour cette tâche !"
        elif status == "fd":
            listener.force_download = True
            if listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Tâche forcée pour le téléchargement uniquement !"
            else:
                msg = "Cette tâche n'est pas dans la file de téléchargement !"
        else:
            listener.force_download = True
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Tâche forcée pour l'upload !"
            elif listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Tâche forcée pour le téléchargement, l'upload démarrera une fois terminé !"
            else:
                msg = "Cette tâche n'est dans aucune file !"
    if msg:
        await send_message(message, msg)