from httpx import AsyncClient
from html import escape
from urllib.parse import quote

from .. import LOGGER
from ..core.config_manager import Config
from ..core.torrent_manager import TorrentManager
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.ext_utils.telegraph_helper import telegraph
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import edit_message, send_message

PLUGINS = []
SITES = None
TELEGRAPH_LIMIT = 300


async def initiate_search_tools():
    qb_plugins = await TorrentManager.qbittorrent.search.plugins()
    if qb_plugins:
        names = [plugin.name for plugin in qb_plugins]
        await TorrentManager.qbittorrent.search.uninstall_plugin(names)
        PLUGINS.clear()
    if Config.SEARCH_PLUGINS:
        await TorrentManager.qbittorrent.search.install_plugin(Config.SEARCH_PLUGINS)

    if Config.SEARCH_API_LINK:
        global SITES
        try:
            async with AsyncClient() as client:
                response = await client.get(f"{Config.SEARCH_API_LINK}/api/v1/sites")
                data = response.json()
            SITES = {
                str(site): str(site).capitalize() for site in data["supported_sites"]
            }
            SITES["all"] = "Tous"
        except Exception as e:
            LOGGER.error(
                f"{e} Impossible de récupérer les sites depuis SEARCH_API_LINK, assurez-vous d'utiliser la dernière version de l'API"
            )
            SITES = None


async def search(key, site, message, method):
    if method.startswith("api"):
        if method == "apisearch":
            LOGGER.info(f"Recherche API : {key} depuis {site}")
            if site == "all":
                api = f"{Config.SEARCH_API_LINK}/api/v1/all/search?query={key}&limit={Config.SEARCH_LIMIT}"
            else:
                api = f"{Config.SEARCH_API_LINK}/api/v1/search?site={site}&query={key}&limit={Config.SEARCH_LIMIT}"
        elif method == "apitrend":
            LOGGER.info(f"Tendances API depuis {site}")
            if site == "all":
                api = f"{Config.SEARCH_API_LINK}/api/v1/all/trending?limit={Config.SEARCH_LIMIT}"
            else:
                api = f"{Config.SEARCH_API_LINK}/api/v1/trending?site={site}&limit={Config.SEARCH_LIMIT}"
        elif method == "apirecent":
            LOGGER.info(f"Récents API depuis {site}")
            if site == "all":
                api = f"{Config.SEARCH_API_LINK}/api/v1/all/recent?limit={Config.SEARCH_LIMIT}"
            else:
                api = f"{Config.SEARCH_API_LINK}/api/v1/recent?site={site}&limit={Config.SEARCH_LIMIT}"
        try:
            async with AsyncClient() as client:
                response = await client.get(api)
                search_results = response.json()
            if "error" in search_results or search_results["total"] == 0:
                await edit_message(
                    message,
                    f"Aucun résultat trouvé pour <i>{key}</i>\nSite Torrent : <i>{SITES.get(site)}</i>",
                )
                return
            msg = f"<b>Trouvé {min(search_results['total'], TELEGRAPH_LIMIT)}</b>"
            if method == "apitrend":
                msg += f" <b>résultat(s) tendance\nSite Torrent : <i>{SITES.get(site)}</i></b>"
            elif method == "apirecent":
                msg += (
                    f" <b>résultat(s) récent(s)\nSite Torrent : <i>{SITES.get(site)}</i></b>"
                )
            else:
                msg += f" <b>résultat(s) pour <i>{key}</i>\nSite Torrent : <i>{SITES.get(site)}</i></b>"
            search_results = search_results["data"]
        except Exception as e:
            await edit_message(message, str(e))
            return
    else:
        LOGGER.info(f"Recherche PLUGINS : {key} depuis {site}")
        search = await TorrentManager.qbittorrent.search.start(
            pattern=key, plugins=[site], category="all"
        )
        search_id = search.id
        while True:
            result_status = await TorrentManager.qbittorrent.search.status(search_id)
            status = result_status[0].status
            if status != "En cours":
                break
        dict_search_results = await TorrentManager.qbittorrent.search.results(
            id=search_id, limit=TELEGRAPH_LIMIT
        )
        search_results = dict_search_results.results
        total_results = dict_search_results.total
        if total_results == 0:
            await edit_message(
                message,
                f"Aucun résultat trouvé pour <i>{key}</i>\nSite Torrent : <i>{site.capitalize()}</i>",
            )
            return
        msg = f"<b>Trouvé {min(total_results, TELEGRAPH_LIMIT)}</b>"
        msg += f" <b>résultat(s) pour <i>{key}</i>\nSite Torrent : <i>{site.capitalize()}</i></b>"
        await TorrentManager.qbittorrent.search.delete(search_id)
    link = await get_result(search_results, key, message, method)
    buttons = ButtonMaker()
    buttons.url_button("🔎 VOIR", link)
    button = buttons.build_menu(1)
    await edit_message(message, msg, button)


async def get_result(search_results, key, message, method):
    telegraph_content = []
    if method == "apirecent":
        msg = "<h4>Résultats API récents</h4>"
    elif method == "apisearch":
        msg = f"<h4>Résultat(s) API pour {key}</h4>"
    elif method == "apitrend":
        msg = "<h4>Tendances API</h4>"
    else:
        msg = f"<h4>Résultat(s) PLUGINS pour {key}</h4>"
    for index, result in enumerate(search_results, start=1):
        if method.startswith("api"):
            try:
                if "name" in result.keys():
                    msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
                if "torrents" in result.keys():
                    for subres in result["torrents"]:
                        msg += f"<b>Qualité : </b>{subres['quality']} | <b>Type : </b>{subres['type']} | "
                        msg += f"<b>Taille : </b>{subres['size']}<br>"
                        if "torrent" in subres.keys():
                            msg += f"<a href='{subres['torrent']}'>Lien direct</a><br>"
                        elif "magnet" in subres.keys():
                            msg += "<b>Partager le Magnet sur </b> "
                            msg += f"<a href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a><br>"
                    msg += "<br>"
                else:
                    msg += f"<b>Taille : </b>{result['size']}<br>"
                    try:
                        msg += f"<b>Seeders : </b>{result['seeders']} | <b>Leechers : </b>{result['leechers']}<br>"
                    except:
                        pass
                    if "torrent" in result.keys():
                        msg += f"<a href='{result['torrent']}'>Lien direct</a><br><br>"
                    elif "magnet" in result.keys():
                        msg += "<b>Partager le Magnet sur </b> "
                        msg += f"<a href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a><br><br>"
                    else:
                        msg += "<br>"
            except:
                continue
        else:
            msg += f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
            msg += f"<b>Taille : </b>{get_readable_file_size(result.fileSize)}<br>"
            msg += f"<b>Seeders : </b>{result.nbSeeders} | <b>Leechers : </b>{result.nbLeechers}<br>"
            link = result.fileUrl
            if link.startswith("magnet:"):
                msg += f"<b>Partager le Magnet sur </b> <a href='http://t.me/share/url?url={quote(link)}'>Telegram</a><br><br>"
            else:
                msg += f"<a href='{link}'>Lien direct</a><br><br>"

        if len(msg.encode("utf-8")) > 39000:
            telegraph_content.append(msg)
            msg = ""

        if index == TELEGRAPH_LIMIT:
            break

    if msg != "":
        telegraph_content.append(msg)

    await edit_message(
        message, f"<b>Création</b> de {len(telegraph_content)} <b>pages Telegraph.</b>"
    )
    path = [
        (
            await telegraph.create_page(
                title="Recherche Torrent Mirror-leech-bot", content=content
            )
        )["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await edit_message(
            message, f"<b>Édition</b> de {len(telegraph_content)} <b>pages Telegraph.</b>"
        )
        await telegraph.edit_telegraph(path, telegraph_content)
    return f"https://telegra.ph/{path[0]}"


def api_buttons(user_id, method):
    buttons = ButtonMaker()
    for data, name in SITES.items():
        buttons.data_button(name, f"torser {user_id} {data} {method}")
    buttons.data_button("Annuler", f"torser {user_id} cancel")
    return buttons.build_menu(2)


async def plugin_buttons(user_id):
    buttons = ButtonMaker()
    if not PLUGINS:
        pl = await TorrentManager.qbittorrent.search.plugins()
        for i in pl:
            PLUGINS.append(i.name)
    for siteName in PLUGINS:
        buttons.data_button(
            siteName.capitalize(), f"torser {user_id} {siteName} plugin"
        )
    buttons.data_button("Tous", f"torser {user_id} all plugin")
    buttons.data_button("Annuler", f"torser {user_id} cancel")
    return buttons.build_menu(2)


@new_task
async def torrent_search(_, message):
    user_id = message.from_id
    buttons = ButtonMaker()
    key = message.text.split()
    if SITES is None and not Config.SEARCH_PLUGINS:
        await send_message(
            message, "Aucun lien API ou PLUGINS de recherche ajouté pour cette fonction"
        )
    elif len(key) == 1 and SITES is None:
        await send_message(message, "Envoyez une clé de recherche avec la commande")
    elif len(key) == 1:
        buttons.data_button("Tendances", f"torser {user_id} apitrend")
        buttons.data_button("Récents", f"torser {user_id} apirecent")
        buttons.data_button("Annuler", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        await send_message(message, "Envoyez une clé de recherche avec la commande", button)
    elif SITES is not None and Config.SEARCH_PLUGINS:
        buttons.data_button("API", f"torser {user_id} apisearch")
        buttons.data_button("Plugins", f"torser {user_id} plugin")
        buttons.data_button("Annuler", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        await send_message(message, "Choisissez l'outil de recherche :", button)
    elif SITES is not None:
        button = api_buttons(user_id, "apisearch")
        await send_message(message, "Choisissez le site à rechercher | API :", button)
    else:
        button = await plugin_buttons(user_id)
        await send_message(message, "Choisissez le site à rechercher | Plugins :", button)


@new_task
async def torrent_search_update(_, query):
    user_id = query.sender_user_id
    message = await query.getMessage()
    reply_to = await message.getRepliedMessage()
    key = reply_to.text.split(maxsplit=1)
    key = key[1].strip() if len(key) > 1 else None
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer("Ce n'est pas à vous !", show_alert=True)
    elif data[2].startswith("api"):
        await query.answer()
        button = api_buttons(user_id, data[2])
        await edit_message(message, "Choisissez le site :", button)
    elif data[2] == "plugin":
        await query.answer()
        button = await plugin_buttons(user_id)
        await edit_message(message, "Choisissez le site :", button)
    elif data[2] != "cancel":
        await query.answer()
        site = data[2]
        method = data[3]
        if method.startswith("api"):
            if key is None:
                if method == "apirecent":
                    endpoint = "Récents"
                elif method == "apitrend":
                    endpoint = "Tendances"
                await edit_message(
                    message,
                    f"<b>Liste des éléments {endpoint}...\nSite Torrent : <i>{SITES.get(site)}</i></b>",
                )
            else:
                await edit_message(
                    message,
                    f"<b>Recherche de <i>{key}</i>\nSite Torrent : <i>{SITES.get(site)}</i></b>",
                )
        else:
            await edit_message(
                message,
                f"<b>Recherche de <i>{key}</i>\nSite Torrent : <i>{site.capitalize()}</i></b>",
            )
        await search(key, site, message, method)
    else:
        await query.answer()
        await edit_message(message, "Recherche annulée !")