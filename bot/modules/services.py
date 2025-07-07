from time import time

from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import send_message, edit_message, send_file
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.bot_commands import BotCommands


@new_task
async def start(_, message):
    buttons = ButtonMaker()
    buttons.url_button(
        "Dépôt", "https://t.me/hyoshcoder"
    )
    buttons.url_button("Propriétaire du code", "https://t.me/hyoshcoder")
    reply_markup = buttons.build_menu(2)
    if CustomFilters.authorized_user(_, message):
        start_string = f"""
Ce bot peut copier des liens|fichiers Telegram|torrents|nzb|cloud rclone vers n'importe quel cloud rclone, Google Drive ou Telegram.
Tapez /{BotCommands.HelpCommand} pour obtenir la liste des commandes disponibles
"""
        await send_message(message, start_string, reply_markup)
    else:
        await send_message(
            message,
            "Ce bot peut copier des liens|fichiers Telegram|torrents|nzb|cloud rclone vers n'importe quel cloud rclone, Google Drive ou Telegram.\n\n⚠️ Vous n'êtes pas un utilisateur autorisé ! Déployez votre propre bot mirror-leech",
            reply_markup,
        )


@new_task
async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await send_message(message, "Démarrage du Ping")
    end_time = int(round(time() * 1000))
    await edit_message(reply, f"{end_time - start_time} ms")


@new_task
async def log(_, message):
    await send_file(message, "log.txt")