from psutil import cpu_percent, virtual_memory, disk_usage
from time import time
from asyncio import gather, iscoroutinefunction

from .. import (
    task_dict_lock,
    status_dict,
    task_dict,
    bot_start_time,
    intervals,
    sabnzbd_client,
    DOWNLOAD_DIR,
)
from ..core.torrent_manager import TorrentManager
from ..core.jdownloader_booter import jdownloader
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
    speed_string_to_bytes,
)
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    auto_delete_message,
    send_status_message,
    update_status_message,
    edit_message,
)
from ..helper.telegram_helper.button_build import ButtonMaker


@new_task
async def task_status(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        currentTime = get_readable_time(time() - bot_start_time)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        msg = f"Aucune tâche active !\nChaque utilisateur peut obtenir le statut de ses tâches en ajoutant 'me' ou son user_id après la commande : /{BotCommands.StatusCommand} me"
        msg += (
            f"\n<b>CPU:</b> {cpu_percent()}% | <b>ESPACE:</b> {free}"
            f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {currentTime}"
        )
        reply_message = await send_message(message, msg)
        await auto_delete_message(message, reply_message)
    else:
        text = message.text.split()
        if len(text) > 1:
            user_id = message.from_id if text[1] == "me" else int(text[1])
        else:
            user_id = 0
            sid = message.chat_id
            if obj := intervals["status"].get(sid):
                obj.cancel()
                del intervals["status"][sid]
        await send_status_message(message, user_id)
        await delete_message(message)


async def get_download_status(download):
    tool = download.tool
    if tool in [
        "telegram",
        "yt-dlp",
        "rclone",
        "gDriveApi",
    ]:
        speed = download.speed()
    else:
        speed = 0
    return (
        await download.status()
        if iscoroutinefunction(download.status)
        else download.status()
    ), speed


@new_task
async def status_pages(_, query):
    data = query.text.split()
    key = int(data[1])
    await query.answer(text="...")
    if data[2] == "ref":
        await update_status_message(key, force=True)
    elif data[2] in ["nex", "pre"]:
        async with task_dict_lock:
            if key in status_dict:
                if data[2] == "nex":
                    status_dict[key]["page_no"] += status_dict[key]["page_step"]
                else:
                    status_dict[key]["page_no"] -= status_dict[key]["page_step"]
    elif data[2] == "ps":
        async with task_dict_lock:
            if key in status_dict:
                status_dict[key]["page_step"] = int(data[3])
    elif data[2] == "st":
        async with task_dict_lock:
            if key in status_dict:
                status_dict[key]["status"] = data[3]
        await update_status_message(key, force=True)
    elif data[2] == "ov":
        ds, ss = await TorrentManager.overall_speed()
        if sabnzbd_client.LOGGED_IN:
            sds = await sabnzbd_client.get_downloads()
            sds = int(float(sds["queue"].get("kbpersec", "0"))) * 1024
            ds += sds
        if jdownloader.is_connected:
            jdres = await jdownloader.device.downloadcontroller.get_speed_in_bytes()
            ds += jdres
        tasks = {
            "Téléchargement": 0,
            "Upload": 0,
            "Seed": 0,
            "Archive": 0,
            "Extraction": 0,
            "Division": 0,
            "FileAttenteDL": 0,
            "FileAttenteUP": 0,
            "Clonage": 0,
            "Vérification": 0,
            "Pause": 0,
            "SampleVidéo": 0,
            "Conversion": 0,
            "FFmpeg": 0,
        }
        dl_speed = ds
        up_speed = 0
        seed_speed = ss
        async with task_dict_lock:
            status_results = await gather(
                *(get_download_status(download) for download in task_dict.values())
            )
            for status, speed in status_results:
                match status:
                    case MirrorStatus.STATUS_DOWNLOAD:
                        tasks["Téléchargement"] += 1
                        if speed:
                            dl_speed += speed_string_to_bytes(speed)
                    case MirrorStatus.STATUS_UPLOAD:
                        tasks["Upload"] += 1
                        up_speed += speed_string_to_bytes(speed)
                    case MirrorStatus.STATUS_SEED:
                        tasks["Seed"] += 1
                    case MirrorStatus.STATUS_ARCHIVE:
                        tasks["Archive"] += 1
                    case MirrorStatus.STATUS_EXTRACT:
                        tasks["Extraction"] += 1
                    case MirrorStatus.STATUS_SPLIT:
                        tasks["Division"] += 1
                    case MirrorStatus.STATUS_QUEUEDL:
                        tasks["FileAttenteDL"] += 1
                    case MirrorStatus.STATUS_QUEUEUP:
                        tasks["FileAttenteUP"] += 1
                    case MirrorStatus.STATUS_CLONE:
                        tasks["Clonage"] += 1
                    case MirrorStatus.STATUS_CHECK:
                        tasks["Vérification"] += 1
                    case MirrorStatus.STATUS_PAUSED:
                        tasks["Pause"] += 1
                    case MirrorStatus.STATUS_SAMVID:
                        tasks["SampleVidéo"] += 1
                    case MirrorStatus.STATUS_CONVERT:
                        tasks["Conversion"] += 1
                    case MirrorStatus.STATUS_FFMPEG:
                        tasks["FFmpeg"] += 1
                    case _:
                        tasks["Téléchargement"] += 1

        msg = f"""<b>DL:</b> {tasks['Téléchargement']} | <b>UP:</b> {tasks['Upload']} | <b>SD:</b> {tasks['Seed']} | <b>AR:</b> {tasks['Archive']}
<b>EX:</b> {tasks['Extraction']} | <b>SP:</b> {tasks['Division']} | <b>QD:</b> {tasks['FileAttenteDL']} | <b>QU:</b> {tasks['FileAttenteUP']}
<b>CL:</b> {tasks['Clonage']} | <b>CK:</b> {tasks['Vérification']} | <b>PA:</b> {tasks['Pause']} | <b>SV:</b> {tasks['SampleVidéo']}
<b>CM:</b> {tasks['Conversion']} | <b>FF:</b> {tasks['FFmpeg']}

<b>VDLS:</b> {get_readable_file_size(dl_speed)}/s
<b>VULS:</b> {get_readable_file_size(up_speed)}/s
<b>VSDS:</b> {get_readable_file_size(seed_speed)}/s
"""
        button = ButtonMaker()
        button.data_button("Retour", f"status {data[1]} ref")
        message = await query.getMessage()
        await edit_message(message, msg, button.build_menu())