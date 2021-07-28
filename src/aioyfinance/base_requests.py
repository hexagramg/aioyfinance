"""
Config and requests implementation
"""
from __future__ import annotations
import logging
import asyncio

from asyncio import Semaphore, Lock
from random import uniform, choice
from typing import Union, Dict, AnyStr, List, Optional
import aiohttp
import aiohttp.web as aioweb

class Config:
    """
    Config class
    """
    internal: Optional[Config] = None
    def __init__(self, parallel: bool = True, max_batch: int = 5, proxy_url: Union[AnyStr, List[AnyStr]] = None,
                 max_retries: int = 3, retry_delay: int = 1, max_rand_delay: float = 0.5, min_rand_delay: float = 0.01,
                 handle_exceptions: bool = True):
        """
        Do not use init directly, use create method
        """
        self.parallel = parallel
        self.max_batch = max_batch
        self.proxy_url = proxy_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_rand_delay = max_rand_delay
        self.min_rand_delay = min_rand_delay
        self.handle_exceptions = handle_exceptions

    @classmethod
    def create(cls, *, parallel: bool = True, max_batch: int = 5, proxy_url: Union[AnyStr, List[AnyStr]] = None,
               max_retries: int = 3, retry_delay: int = 1, max_rand_delay: float = 0.5,
               min_rand_delay: float = 0.01, handle_exceptions: bool = True) -> Config:
        """
        Sets global settings variable, keywords only
        :param parallel: Controls overlapping of requests
        :param max_batch: Maximum requests active
        :param proxy_url: Set strings according to aiohttp docs
        String or array of strings for random choice of proxy
        :param max_retries: Amount of retries if request fails
        :param retry_delay: Delay between retries
        :param max_rand_delay: Maximum random delay between requests
        :param min_rand_delay: Minimum random delay between requests
        :param handle_exceptions: Tickers returns tuple(list of results, list of tickers names that caught
            exceptions) if True or list of results with exceptions if False
        :return: global Config.internal class
        """

        Config.internal = cls(parallel=parallel, max_batch=max_batch, proxy_url=proxy_url, max_retries=max_retries,
                     retry_delay=retry_delay, max_rand_delay=max_rand_delay, min_rand_delay=min_rand_delay,
                     handle_exceptions=handle_exceptions)

        return Config.internal

    @property
    def pick_rand_delay(self):
        return uniform(self.min_rand_delay, self.max_rand_delay)

    @property
    def proxy_url(self):
        return self._proxy_url

    @proxy_url.setter
    def proxy_url(self, proxy: Union[AnyStr, List[AnyStr]]):
        if isinstance(proxy, List):
            self._proxy_rand = True
        else:
            self._proxy_rand = False

        self._proxy_url = proxy

    @property
    def proxy(self):
        if self._proxy_rand:
            return choice(self._proxy_url)

        return self._proxy_url

    @property
    def parallel(self):
        return self._parallel

    @parallel.setter
    def parallel(self, value: bool):
        if not value:
            self._lock = Lock()
        else:
            self._lock = None

        self._parallel = value

    @property
    def max_batch(self):
        return self._max_batch

    @max_batch.setter
    def max_batch(self, value: int):
        self._max_batch = value
        self._semaphore_batch = Semaphore(self._max_batch)

    @property
    def lock(self):
        return self._lock

    @property
    def semaphore_batch(self):
        return self._semaphore_batch


Config.create()


class BaseRequest:
    @staticmethod
    async def get(url: AnyStr, is_json=False) -> Union[Dict, AnyStr]:

        await Config.internal.semaphore_batch.acquire()
        if not Config.internal.parallel:
            await Config.internal.lock.acquire()

        await asyncio.sleep(Config.internal.pick_rand_delay)

        async with aiohttp.ClientSession() as session:

            retries = Config.internal.max_retries

            while retries > 0:
                async with session.get(url, proxy=Config.internal.proxy) as resp:
                    try:
                        if not is_json:
                            result = await resp.text()
                        else:
                            result = await resp.json()

                    except aioweb.HTTPError as e:
                        logging.error(url + ' ' + repr(e))
                        retries -= 1
                        if retries:  # if > 0
                            await asyncio.sleep(Config.internal.retry_delay)
                        else:
                            result = e
                    else:
                        break

            Config.internal.semaphore_batch.release()
            if not Config.internal.parallel:
                Config.internal.lock.release()

            await asyncio.sleep(0)  # next code is computational, let other requests finish

            if isinstance(result, Exception):  # ensure that everything is released, then raise
                raise result

            return result
