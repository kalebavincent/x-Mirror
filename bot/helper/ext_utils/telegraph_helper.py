from asyncio import sleep
from secrets import token_urlsafe
from telegraph.aio import Telegraph
from telegraph.exceptions import RetryAfterError

from ... import LOGGER


class TelegraphHelper:
    def __init__(self, author_name=None, author_url=None):
        self._telegraph = Telegraph(domain="graph.org")
        self._author_name = author_name
        self._author_url = author_url

    async def create_account(self):
        LOGGER.info("Création du compte Telegraph")
        try:
            await self._telegraph.create_account(
                short_name=token_urlsafe(8),
                author_name=self._author_name,
                author_url=self._author_url,
            )
        except Exception as e:
            LOGGER.error(f"Échec de la création du compte Telegraph : {e}")

    async def create_page(self, title, content):
        try:
            return await self._telegraph.create_page(
                title=title,
                author_name=self._author_name,
                author_url=self._author_url,
                html_content=content,
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f"Limite flood Telegraph dépassée. Pause de {st.retry_after} secondes."
            )
            await sleep(st.retry_after)
            return await self.create_page(title, content)

    async def edit_page(self, path, title, content):
        try:
            return await self._telegraph.edit_page(
                path=path,
                title=title,
                author_name=self._author_name,
                author_url=self._author_url,
                html_content=content,
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f"Limite flood Telegraph dépassée. Pause de {st.retry_after} secondes."
            )
            await sleep(st.retry_after)
            return await self.edit_page(path, title, content)

    async def edit_telegraph(self, path, telegraph_content):
        nxt_page = 1
        prev_page = 0
        num_of_path = len(path)
        for content in telegraph_content:
            if nxt_page == 1:
                content += (
                    f'<b><a href="https://telegra.ph/{path[nxt_page]}">Suivant</a></b>'
                )
                nxt_page += 1
            else:
                if prev_page <= num_of_path:
                    content += f'<b><a href="https://telegra.ph/{path[prev_page]}">Précédent</a></b>'
                    prev_page += 1
                if nxt_page < num_of_path:
                    content += f'<b> | <a href="https://telegra.ph/{path[nxt_page]}">Suivant</a></b>'
                    nxt_page += 1
            await self.edit_page(
                path=path[prev_page],
                title="Recherche Torrent du bot Mirror-leech",
                content=content,
            )
        return


telegraph = TelegraphHelper(
    "Mirror-Leech-Telegram-Bot", "https://github.com/anasty17/mirror-leech-telegram-bot"
)

print(__name__)