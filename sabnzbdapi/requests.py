import asyncio
import json
from httpx import AsyncClient, AsyncHTTPTransport, HTTPStatusError, Timeout, RequestError, DecodingError
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from functools import wraps

from .job_functions import JobFunctions
from .exception import APIConnectionError


class SabnzbdSession(AsyncClient):
    @wraps(AsyncClient.request)
    async def request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", Timeout(connect=30, read=60, write=60, pool=None))
        kwargs.setdefault("follow_redirects", True)
        return await super().request(method, url, **kwargs)


class SabnzbdClient(JobFunctions):

    LOGGED_IN = False

    def __init__(
        self,
        host: str,
        api_key: str,
        port: str = "8070",
        VERIFY_CERTIFICATE: bool = False,
        RETRIES: int = 10,
        HTTPX_REQUETS_ARGS: dict = None,
    ):
        if HTTPX_REQUETS_ARGS is None:
            HTTPX_REQUETS_ARGS = {}
        self._base_url = f"{host.rstrip('/')}:{port}/sabnzbd/api"
        self._default_params = {"apikey": api_key, "output": "json"}
        self._VERIFY_CERTIFICATE = VERIFY_CERTIFICATE
        self._RETRIES = RETRIES
        self._HTTPX_REQUETS_ARGS = HTTPX_REQUETS_ARGS
        self._http_session = None
        if not self._VERIFY_CERTIFICATE:
            disable_warnings(InsecureRequestWarning)
        super().__init__()

    def _session(self):
        if self._http_session is not None:
            return self._http_session

        transport = AsyncHTTPTransport(
            retries=self._RETRIES, verify=self._VERIFY_CERTIFICATE
        )

        self._http_session = SabnzbdSession(transport=transport)

        self._http_session.verify = self._VERIFY_CERTIFICATE

        return self._http_session


    async def call(
        self,
        params: dict = None,
        api_method: str = "GET",
        requests_args: dict = None,
        **kwargs,
    ):
        if requests_args is None:
            requests_args = {}
        if params is None:
            params = {}
        session = self._session()
        params |= kwargs
        requests_kwargs = {**self._HTTPX_REQUETS_ARGS, **requests_args}
        retries = 5

        for retry_count in range(retries):
            try:
                res = await session.request(
                    method=api_method,
                    url=self._base_url,
                    params={**self._default_params, **params},
                    **requests_kwargs,
                )
                
                # Vérifie le status HTTP
                res.raise_for_status()
                
                # Vérifie si body vide
                if not res.text.strip():
                    raise APIConnectionError(f"Empty response from Sabnzbd API. URL: {res.url}")

                try:
                    response = res.json()
                except json.JSONDecodeError as e:
                    # Log body invalide pour debug
                    raise APIConnectionError(f"Invalid JSON response from Sabnzbd API. Body: {res.text}") from e

                return response

            except (RequestError, HTTPStatusError, DecodingError, json.JSONDecodeError) as err:
                print(f"[SABNZBD] Error on attempt {retry_count+1}/{retries}: {err}")
                if retry_count >= (retries - 1):
                    raise APIConnectionError(f"Failed to connect to Sabnzbd API after {retries} attempts. Last error: {err}") from err
                await asyncio.sleep(2)  # Backoff avant retry
