import os
import aiohttp

from random import shuffle

from typing import Dict, List
from Logger import Logger
from dotenv import load_dotenv

load_dotenv()


class ProxyManager:
    _instance = None
    MAX_PROXY_USES = 250

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProxyManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.proxies: List[Dict[str, str]] = []
        self.current_index: int = 0
        self.uses_count: int = 0
        self._initialized = True
        Logger.info("ProxyManager initialized")

    async def initialize(self):
        """Initialize the proxy pool on first use"""
        if not self.proxies:
            await self._fetch_proxies()

    async def _fetch_proxies(self) -> None:
        """Fetch proxies from Webshare API"""
        Logger.info("Fetching new proxies from Webshare")
        WEBSHARE_API_TOKEN = os.getenv('WEBSHARE_API_TOKEN')
        formatted_proxies = []
        page = 1

        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        async with session.get(
                                f"https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page={page}&page_size=100",
                                headers={"Authorization": f"Token {WEBSHARE_API_TOKEN}"},
                                timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            response.raise_for_status()

                            proxies_data = await response.json()
                            proxies_list = proxies_data.get('results', [])

                            if not proxies_list:
                                break

                            for proxy in proxies_list:
                                url = f"http://{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}"
                                proxy['http'] = url
                                proxy['https'] = url
                                formatted_proxies.append(proxy)

                            if not proxies_data.get('next'):
                                break

                            page += 1
                    except Exception as e:
                        Logger.error("Error during proxy fetch", e)
                        break

            shuffle(formatted_proxies)
            self.proxies = formatted_proxies
            self.current_index = 0
            self.uses_count = 0

            Logger.info(f"Successfully loaded {len(self.proxies)} proxies")
        except Exception as e:
            Logger.error("Fatal error in proxy fetching", e)
            raise

    async def get_proxy(self) -> Dict[str, str]:
        """Get next proxy using round-robin method"""

        if self.uses_count >= self.MAX_PROXY_USES:
            Logger.info("Proxy use limit reached, refreshing proxies")
            await self._fetch_proxies()

        proxy = self.proxies[self.current_index]

        self.current_index = (self.current_index + 1) % len(self.proxies)
        self.uses_count += 1

        Logger.debug("Providing proxy", proxy)
        return proxy
