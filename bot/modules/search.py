import math
import qbittorrentapi as qba
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot import dispatcher, LOGGER, get_client, search_dict_lock, search_dict, application
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper import button_build


@new_thread  # si new_thread est une fonction compatible async, sinon gérer autrement
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = update.message.text.split(" ", maxsplit=1)[1]
        client = get_client()
        search = client.search_start(pattern=str(key), plugins='all', category='all')
        srchmsg = await sendMessage("Recherche en cours...", context.bot, update)
        user_id = update.message.from_user.id
        search_id = search.id
        LOGGER.info(f"Recherche qBittorrent : {key}")

        # Poller le status de recherche
        while True:
            result_status = client.search_status(search_id=search_id)
            status = result_status[0].status
            if status != 'Running':
                break
            await asyncio.sleep(1)  # pause pour ne pas bloquer la boucle

        dict_search_results = client.search_results(search_id=search_id)
        search_results = dict_search_results.results
        total_results = dict_search_results.total

        if total_results != 0:
            total_pages = math.ceil(total_results / 3)
            msg = getResult(search_results)
            buttons = button_build.ButtonMaker()
            if total_results > 3:
                msg += f"<b>Pages : </b>1/{total_pages} | <b>Résultats : </b>{total_results}"
                buttons.sbutton("Précédent", f"srchprev {user_id} {search_id}")
                buttons.sbutton("Suivant", f"srchnext {user_id} {search_id}")
            buttons.sbutton("Fermer", f"closesrch {user_id} {search_id}")
            button = InlineKeyboardMarkup(buttons.build_menu(2))
            await editMessage(msg, srchmsg, button)
            async with search_dict_lock:
                search_dict[search_id] = (client, search_results, total_results, total_pages, 1, 0)
        else:
            await editMessage(f"Aucun résultat trouvé pour <i>{key}</i>", srchmsg)

    except IndexError:
        await sendMessage("Veuillez envoyer un mot-clé de recherche avec la commande", context.bot, update)
    except Exception as e:
        LOGGER.error(str(e))


async def searchPages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.split(" ")
    search_id = int(data[2])

    if user_id != int(data[1]):
        await query.answer(text="Ce n'est pas pour vous !", show_alert=True)
        return

    async with search_dict_lock:
        try:
            client, search_results, total_results, total_pages, pageNo, start = search_dict[search_id]
        except KeyError:
            await query.answer(text="Résultat expiré", show_alert=True)
            await query.message.delete()
            return

    if data[0] == "srchnext":
        if pageNo == total_pages:
            start = 0
            pageNo = 1
        else:
            start += 3
            pageNo += 1
    elif data[0] == "srchprev":
        if pageNo == 1:
            pageNo = total_pages
            start = 3 * (total_pages - 1)
        else:
            pageNo -= 1
            start -= 3
    elif data[0] == "closesrch":
        client.search_delete(search_id)
        client.auth_log_out()
        async with search_dict_lock:
            search_dict.pop(search_id, None)
        await query.message.delete()
        return

    async with search_dict_lock:
        search_dict[search_id] = (client, search_results, total_results, total_pages, pageNo, start)

    msg = getResult(search_results, start=start)
    msg += f"<b>Pages : </b>{pageNo}/{total_pages} | <b>Résultats : </b>{total_results}"
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Précédent", f"srchprev {user_id} {search_id}")
    buttons.sbutton("Suivant", f"srchnext {user_id} {search_id}")
    buttons.sbutton("Fermer", f"closesrch {user_id} {search_id}")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    await editMessage(msg, query.message, button)


def getResult(search_results, start=0):
    msg = ""
    for index, result in enumerate(search_results[start:], start=1):
        msg += f"<a href='{result.descrLink}'>{result.fileName}</a>\n"
        msg += f"<b>Taille : </b>{get_readable_file_size(result.fileSize)}\n"
        msg += f"<b>Seeders : </b>{result.nbSeeders} | <b>Leechers : </b>{result.nbLeechers}\n"
        msg += f"<b>Lien : </b><code>{result.fileUrl}</code>\n\n"
        if index == 3:
            break
    return msg


application.add_handler(CommandHandler(
    BotCommands.SearchCommand,
    search,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user
))

application.add_handler(CallbackQueryHandler(
    searchPages,
    pattern="srchnext"
))

application.add_handler(CallbackQueryHandler(
    searchPages,
    pattern="srchprev"
))

application.add_handler(CallbackQueryHandler(
    searchPages,
    pattern="closesrch"
))
