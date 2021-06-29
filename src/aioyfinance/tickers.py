
import aiohttp
import asyncio
import aiohttp.web as aioweb
from bs4 import BeautifulSoup
import json
from typing import AnyStr, List, Union
from .urldict import base, funcs, query, query_opt, offsets
from datetime import datetime, timedelta
from functools import wraps
import logging


def _merge_dicts(dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key-value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

def symbol_check(func):
    """
    does request and checkes if symbol is correct, if it is not raises NameError

    passes souped html to the method
    :param func: item from funcs dictionary
    :return: async method
    """
    def decorator(method):

        @wraps(method)
        async def load_and_check(self, *args, **kwargs):
            html = await self._make_request(func)

            if html is None:
                raise NameError(self.ticker)

            souped = BeautifulSoup(html)

            if (tag := souped.h2.span) is not None:
                # ON THIS TIME THERE IS NO SUCH ELEMENT WHEN QUOTE IS FOUND.
                if 'Symbols similar' in tag.text:
                    raise NameError

            return await method(self, *args, souped=souped, **kwargs)
        return load_and_check
    return decorator


class Ticker:
    def __init__(self, ticker: AnyStr):
        self.ticker = ticker
        self._statistics = None
        self._profile = None
        self._timeseries = None

    async def get_statistics(self):
        if self._statistics is None:
            await self._get_statistics()

        return self._statistics

    async def get_timeseries(self, interval, range_):
        if self._timeseries is None:
            await self._get_timeseries(interval, range_)

        return self._timeseries

    async def get_profile(self):

        if self._profile is None:
            await self._get_profile()

        return self._profile

    async def _make_request(self, func):
        url = f'{base}/{self.ticker}/{func}'
        html = await self._base_request(url)
        return html

    async def _request_timeseries(self, interval='1wk', range_:Union[str, timedelta]='1y'):
        """

        :param interval: granularity
        valid ranges: 1m, 5m, 30m, 1h, 1d, 1wk, 1mo
        :param range_: whole range of dates
        valid ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y or timedelta
        :return:
        """
        #TODO support for second query type: param1 & param2 date segment
        #TODO find out if other parameters are actually doing anything
        now = datetime.now()
        if isinstance(range_, str):
            param1 = now - offsets[range_]
        else:
            param1 = now - range_

        url = f'{query}/{self.ticker}?symbol={self.ticker}&{query_opt}&interval={interval}&period1={int(param1.timestamp())}&period2={int(now.timestamp())}&events=div|split|earn&useYfid=true&includePrePost=true'
        ts_json = await self._base_request(url, is_json=True)
        logging.critical(url)
        return ts_json


    @staticmethod
    async def _base_request(url, is_json=False):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                try:
                    if not is_json:
                        ress = await resp.text()
                        html = ress
                    else:
                        html = await resp.json()
                except aioweb.HTTPError:
                    return None
                else:
                    return html

    @symbol_check(funcs['statistics'])
    async def _get_statistics(self, souped):

        tables = souped.find_all('section')[1].find_all('tbody')
        self._statistics = _merge_dicts([self._parse_table(tb)for tb in tables])

    async def _get_timeseries(self, interval, range_:Union[str, timedelta]):
        """

        :param interval: granularity
        valid ranges: 1m, 5m, 30m, 1h, 1d, 1wk, 1mo
        :param range_: whole range of dates
        valid ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y or timedelta
        :return:
        """
        ts_json = await self._request_timeseries(interval, range_)
        if ts_json['chart']['result'] is None:
            raise NameError(ts_json['chart']['error']['code'])
        else:
            reform_ts = {}
            base_ts = ts_json['chart']['result'][0]
            reform_ts['timestamp'] = base_ts['timestamp']
            if 'events' in base_ts:
                events = base_ts['events']
                if 'dividends' in events:
                    reform_ts['dividends'] = events['dividends']
                if 'splits' in events:
                    reform_ts['splits'] = events['splits']
            data_ts = base_ts['indicators']
            reform_ts = _merge_dicts(reform_ts, data_ts['quote'][0], data_ts['adjclose'][0])
            self._timeseries = reform_ts

    @symbol_check(funcs['profile'])
    async def _get_profile(self, *, souped):

        section = souped.find_all('section')[1]
        data = section.find_all('p')[1].find_all('span')
        name = section.h3.text
        self._profile = {
            'Sector': data[1].text,
            'Industry': data[3].text,
            'Name': name
        }

    def _parse_table(self, table):
        dict_table = {}
        for row in table.children:
            first, second = list(row.children)
            first = self._replace_keys(first.text)
            dict_table[first] = second.text

        return dict_table

    @staticmethod
    def _replace_keys(key: str):
        key = key.replace(' ', '')

        return key


class Tickers:

    def __init__(self, tickers: List[str]):
        self._tickers_names = tickers
        self._tickers = [Ticker(ticker) for ticker in tickers]

    async def get_profiles(self):
        coro_arr = [tick.get_profile() for tick in self._tickers]
        return await self._get_tasks(coro_arr)

    async def get_statistics(self):
        coro_arr = [tick.get_statistics() for tick in self._tickers]
        return await self._get_tasks(coro_arr)

    async def get_timeseries(self, interval, range_):
        coro_arr = [tick.get_timeseries(interval, range_) for tick in self._tickers]
        return await self._get_tasks(coro_arr)

    async def _get_tasks(self, coroutine_array):
        """
        hopefully universal function. For it to work
        every async function in Task must raise NameError if anything goes wrong
        :param coroutine_array:
        :return: array of completed data and array of misspeled quote
        """
        completed = await asyncio.gather(*coroutine_array, return_exceptions=True)
        wrong_indexes = []
        wrong_names = []
        for i, value in enumerate(completed):
            if isinstance(value, NameError):
                wrong_indexes.append(i)
                wrong_names.append(self._tickers_names[i])
        for ind in sorted(wrong_indexes, reverse=True):
            del self._tickers_names[ind]
            del self._tickers[ind]
            del completed[ind]

        return completed, wrong_names


