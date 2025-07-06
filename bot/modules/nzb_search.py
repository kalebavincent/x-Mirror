from xml.etree import ElementTree as ET
from aiohttp import ClientSession

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.ext_utils.telegraph_helper import telegraph
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import edit_message, send_message


@new_task
async def hydra_search(_, message):
    key = message.text.split()
    if len(key) == 1:
        await send_message(
            message,
            "Veuillez fournir une requête de recherche. Exemple : `/nzbsearch titre du film`.",
        )
        return

    query = " ".join(key[1:]).strip()
    message = await send_message(message, f"Recherche de '{query}'...")
    try:
        items = await search_nzbhydra(query)
        if not items:
            await edit_message(message, "Aucun résultat trouvé.")
            LOGGER.info(f"Aucun résultat trouvé pour la requête : {query}")
            return

        page_url = await create_telegraph_page(query, items)
        buttons = ButtonMaker()
        buttons.url_button("Résultats", page_url)
        button = buttons.build_menu()
        await edit_message(
            message,
            f"Les résultats de recherche pour '{query}' sont disponibles ici",
            button,
        )
    except Exception as e:
        LOGGER.error(f"Erreur dans hydra_search : {e!s}")
        await edit_message(message, "Une erreur s'est produite.")


async def search_nzbhydra(query, limit=50):
    search_url = f"{Config.HYDRA_IP}/api"
    params = {
        "apikey": Config.HYDRA_API_KEY,
        "t": "search",
        "q": query,
        "limit": limit,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    }

    async with ClientSession() as session:
        try:
            async with session.get(
                search_url,
                params=params,
                headers=headers,
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ET.fromstring(content)
                    return root.findall(".//item")

                LOGGER.error(
                    f"Échec de la recherche NZBHydra. Code d'état : {response.status}",
                )
                LOGGER.error(f"Réponse : {await response.text()}")
                return None
        except ET.ParseError:
            LOGGER.error("Échec de l'analyse de la réponse XML.")
            return None
        except Exception as e:
            LOGGER.error(f"Erreur dans search_nzbhydra : {e!s}")
            return None


async def create_telegraph_page(query, items):
    content = "<b>Résultats de la recherche :</b><br><br>"
    sorted_items = sorted(
        [
            (
                int(item.find("size").text) if item.find("size") is not None else 0,
                item,
            )
            for item in items[:100]
        ],
        reverse=True,
        key=lambda x: x[0],
    )

    for idx, (size_bytes, item) in enumerate(sorted_items, 1):
        title = (
            item.find("title").text
            if item.find("title") is not None
            else "Titre non disponible"
        )
        download_url = (
            item.find("link").text
            if item.find("link") is not None
            else "Lien non disponible"
        )
        size = get_readable_file_size(size_bytes)

        content += (
            f"{idx}. {title}<br>"
            f"<b><a href='{download_url}'>Télécharger</a> | <a href='http://t.me/share/url?url={download_url}'>Partager</a></b><br>"
            f"<b>Taille :</b> {size}<br>"
            f"━━━━━━━━━━━━━━━━━━━━━━<br><br>"
        )

    response = await telegraph.create_page(
        title=f"Résultats pour '{query}'",
        content=content,
    )
    LOGGER.info(f"Page Telegraph créée pour la recherche : {query}")
    return f"https://telegra.ph/{response['path']}"