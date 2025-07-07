from time import time
from re import search as research
from asyncio import gather
from aiofiles.os import path as aiopath
from psutil import (
    disk_usage,
    cpu_percent,
    swap_memory,
    cpu_count,
    virtual_memory,
    net_io_counters,
    boot_time,
)

from .. import bot_start_time
from ..helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from ..helper.ext_utils.bot_utils import cmd_exec, new_task
from ..helper.telegram_helper.message_utils import send_message
from pytdbot.types import Message, UpdateNewCallbackQuery

# Définition constante des commandes et regex
COMMANDS_INFO = {
    "aria2": (["aria2c", "--version"], r"aria2 version ([\d.]+)"),
    "qBittorrent": (["qbittorrent-nox", "--version"], r"qBittorrent v([\d.]+)"),
    "SABnzbd+": (["sabnzbdplus", "--version"], r"sabnzbdplus-([\d.]+)"),
    "python": (["python3", "--version"], r"Python ([\d.]+)"),
    "rclone": (["rclone", "--version"], r"rclone v([\d.]+)"),
    "yt-dlp": (["yt-dlp", "--version"], r"([\d.]+)"),
    "ffmpeg": (["ffmpeg", "-version"], r"ffmpeg version ([\d.]+(-\w+)?).*"),
    "7z": (["7z", "i"], r"7-Zip ([\d.]+)"),
}

@new_task
async def bot_stats(_, message):
    total, used, free, disk = disk_usage("/")
    swap = swap_memory()
    memory = virtual_memory()
    
    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd <b>De</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "Pas de UPSTREAM_REPO"

    versions = await get_packages_version()

    versions_str = "\n".join(
        f"<b>{tool}:</b> {version}" for tool, version in versions.items()
    )

    stats = f"""
<b>Date du commit:</b> {last_commit}

<b>Temps de fonctionnement du bot:</b> {get_readable_time(time() - bot_start_time)}
<b>Temps de fonctionnement du système:</b> {get_readable_time(time() - boot_time())}

<b>Espace disque total:</b> {get_readable_file_size(total)}
<b>Utilisé:</b> {get_readable_file_size(used)} | <b>Libre:</b> {get_readable_file_size(free)}

<b>Téléversement:</b> {get_readable_file_size(net_io_counters().bytes_sent)}
<b>Téléchargement:</b> {get_readable_file_size(net_io_counters().bytes_recv)}

<b>CPU:</b> {cpu_percent(interval=0.5)}%
<b>RAM:</b> {memory.percent}%
<b>DISQUE:</b> {disk}%

<b>Cœurs physiques:</b> {cpu_count(logical=False)}
<b>Cœurs totaux:</b> {cpu_count()}
<b>SWAP:</b> {get_readable_file_size(swap.total)} | <b>Utilisé:</b> {swap.percent}%

<b>Mémoire totale:</b> {get_readable_file_size(memory.total)}
<b>Mémoire libre:</b> {get_readable_file_size(memory.available)}
<b>Mémoire utilisée:</b> {get_readable_file_size(memory.used)}

{versions_str}
"""
    await send_message(message, stats)

async def get_version_async(command, regex):
    try:
        out, err, code = await cmd_exec(command)
        if code != 0:
            return f"Erreur: {err}"
        match = research(regex, out)
        return match.group(1) if match else "Version non trouvée"
    except Exception as e:
        return f"Exception: {str(e)}"

async def get_packages_version():
    versions = {}
    tasks = []
    
    for tool, (command, regex) in COMMANDS_INFO.items():
        tasks.append(get_version_async(command, regex))
    
    results = await gather(*tasks)
    
    for tool, version in zip(COMMANDS_INFO.keys(), results):
        versions[tool] = version
    
    return versions