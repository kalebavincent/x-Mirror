from aiofiles.os import remove, path as aiopath
from asyncio import iscoroutinefunction

from .. import (
    task_dict,
    task_dict_lock,
    user_data,
    LOGGER,
    sabnzbd_client,
)
from ..core.config_manager import Config
from ..core.torrent_manager import TorrentManager
from ..helper.ext_utils.bot_utils import bt_selection_buttons, new_task
from ..helper.ext_utils.status_utils import get_task_by_gid, MirrorStatus
from ..helper.telegram_helper.message_utils import (
    send_message,
    send_status_message,
    delete_message,
)


@new_task
async def select(_, message):
    if not Config.BASE_URL:
        await send_message(message, "URL de base non définie !")
        return
    user_id = message.from_id
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        task = await get_task_by_gid(gid)
        if task is None:
            await send_message(message, f"GID : <code>{gid}</code> non trouvé.")
            return
    elif reply_to := message.reply_to:
        async with task_dict_lock:
            task = task_dict.get(reply_to.message_id)
        if task is None:
            await send_message(message, "Ce n'est pas une tâche active !")
            return
    elif len(msg) == 1:
        msg = (
            "Répondez à une commande active /cmd qui a démarré le téléchargement ou ajoutez le GID avec la commande\n\n"
            + "Cette commande sert principalement à la sélection lorsque vous décidez de choisir des fichiers depuis un torrent/nzb déjà ajouté. "
            + "Mais vous pouvez toujours utiliser /cmd avec l'argument `s` pour sélectionner les fichiers avant le début du téléchargement."
        )
        await send_message(message, msg)
        return
    if (
        Config.OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (user_id not in user_data or not user_data[user_id].get("SUDO"))
    ):
        await send_message(message, "Cette tâche ne vous est pas destinée !")
        return
    if not iscoroutinefunction(task.status):
        await send_message(message, "La tâche a terminé l'étape de téléchargement !")
        return
    if await task.status() not in [
        MirrorStatus.STATUS_DOWNLOAD,
        MirrorStatus.STATUS_PAUSED,
        MirrorStatus.STATUS_QUEUEDL,
    ]:
        await send_message(
            message,
            "La tâche doit être en cours de téléchargement, en pause (si le message a été supprimé par erreur) ou en file d'attente (si vous avez utilisé un torrent ou un fichier nzb) !",
        )
        return
    if task.name().startswith("[METADATA]") or task.name().startswith("Trying"):
        await send_message(message, "Réessayez après la fin du téléchargement des métadonnées !")
        return

    try:
        if not task.queued:
            await task.update()
            id_ = task.gid()
            if task.listener.is_nzb:
                await sabnzbd_client.pause_job(id_)
            elif task.listener.is_qbit:
                id_ = task.hash()
                await TorrentManager.qbittorrent.torrents.stop([id_])
            else:
                try:
                    await TorrentManager.aria2.forcePause(id_)
                except Exception as e:
                    LOGGER.error(
                        f"{e} Erreur lors de la pause, cela se produit généralement après un abus d'aria2"
                    )
        task.listener.select = True
    except:
        await send_message(message, "Ce n'est pas une tâche bittorrent ou sabnzbd !")
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = "Votre téléchargement est en pause. Choisissez les fichiers puis appuyez sur le bouton 'Terminer la sélection' pour reprendre le téléchargement."
    await send_message(message, msg, SBUTTONS)


@new_task
async def confirm_selection(_, query):
    user_id = query.sender_user_id
    data = query.text.split()
    message = await query.getMessage()
    task = await get_task_by_gid(data[2])
    if task is None:
        await query.answer("Cette tâche a été annulée !", show_alert=True)
        await delete_message(message)
        return
    if user_id != task.listener.user_id:
        await query.answer("Cette tâche ne vous est pas destinée !", show_alert=True)
    elif data[1] == "pin":
        await query.answer(data[3], show_alert=True)
    elif data[1] == "done":
        await query.answer()
        id_ = data[3]
        if hasattr(task, "seeding"):
            if task.listener.is_qbit:
                tor_info = (
                    await TorrentManager.qbittorrent.torrents.info(hashes=[id_])
                )[0]
                path = tor_info.content_path.rsplit("/", 1)[0]
                res = await TorrentManager.qbittorrent.torrents.files(id_)
                for f in res:
                    if f.priority == 0:
                        f_paths = [f"{path}/{f.name}", f"{path}/{f.name}.!qB"]
                        for f_path in f_paths:
                            if await aiopath.exists(f_path):
                                try:
                                    await remove(f_path)
                                except:
                                    pass
                if not task.queued:
                    await TorrentManager.qbittorrent.torrents.start([id_])
            else:
                res = await TorrentManager.aria2.getFiles(id_)
                for f in res:
                    if f["selected"] == "false" and await aiopath.exists(f["path"]):
                        try:
                            await remove(f["path"])
                        except:
                            pass
                if not task.queued:
                    try:
                        await TorrentManager.aria2.unpause(id_)
                    except Exception as e:
                        LOGGER.error(
                            f"{e} Erreur lors de la reprise, cela se produit généralement après un abus d'aria2. Essayez d'utiliser à nouveau la commande de sélection !"
                        )
        elif task.listener.is_nzb:
            await sabnzbd_client.resume_job(id_)
        await send_status_message(message)
        await delete_message(message)
    else:
        await delete_message(message)
        await task.cancel_task()