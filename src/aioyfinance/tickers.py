import asyncio
from bs4 import BeautifulSoup
import json
from .urldict import base, funcs, query, query_opt, offsets
from datetime import datetime, timedelta
from functools import wraps
from .old_urls import *
import re
import logging
from collections import defaultdict
from typing import Callable, List, Dict, Union, AnyStr, Tuple, Coroutine
from enum import Enum

from .base_requests import BaseRequest

HANDLE_EXCEPTIONS = True  # you can either let library throw errors in data list or separate them


class Stats(Enum):
    """
    These are keys to Ticker.__data dictionary
    """
    TIME_SERIES = 1
    PROFILE = 2
    CASHFLOW = 3
    CASHFLOW_Q = 4
    STATISTICS = 5
    BALANCE = 6
    BALANCE_Q = 7
    INCOME = 8
    INCOME_Q = 9


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

            if souped.h2 is None:
                raise NameError(f'{self.ticker} is ETF probably')

            if (tag := souped.h2.span) is not None:
                # ON THIS TIME THERE IS NO SUCH ELEMENT WHEN QUOTE IS FOUND.
                if 'Symbols similar' in tag.text:
                    raise NameError

            return await method(self, *args, souped=souped, **kwargs)

        return load_and_check

    return decorator


def strip_old_json(fund_json):
    """
    format of returned fundamentals json is not good, many elements without data
    trying to clean things up a bit

    :param fund_json: dictionary from fundamentals api
    :return: probably cleaner dictionary
    """

    inside = fund_json['timeseries']['result']

    inside = list(filter(lambda z: 'timestamp' in z, inside))

    parsed_dict = defaultdict(dict)
    capital_splitter = re.compile('(?=[A-Z])')
    for i, x in enumerate(inside):
        full_name = x['meta']['type'][0]
        mod, name = capital_splitter.split(full_name, 1)

        values = []
        for d in x[full_name]:
            if d is not None:  # array of values may consist of None if there is no value.
                values.append(d['reportedValue']['raw'])
            else:
                values.append(d)

        parsed_dict[mod][name] = {
            'timestamp': x['timestamp'],
            'data': values,
            'info': [d for d in x[full_name]]
        }

    return parsed_dict


class Ticker:
    def __init__(self, ticker: AnyStr):
        self.__ticker = ticker
        self.__data = dict()

    @property
    def ticker(self):
        return self.__ticker

    def clear(self, key_arr: List[AnyStr] = None):
        """
        clears internal dictionary, allows to make requests again
        :param key_arr: list of keys to clear, if None clean everything
        """
        if key_arr:
            for key in key_arr:
                if key in self.__data:
                    del self.__data[key]
        else:
            self.__data = dict()

    async def get_statistics(self):
        if Stats.STATISTICS not in self.__data:
            await self._get_statistics()

        return self.__data[Stats.STATISTICS]

    @symbol_check(funcs['statistics'])
    async def _get_statistics(self, souped):
        """
        mrq = Most Recent Quarter
        ttm = Trailing Twelve Months
        yoy = Year Over Year
        lfy = Last Fiscal Year
        fye = Fiscal Year Ending
        """
        tables = souped.find_all('section')[1].find_all('tbody')
        self.__data[Stats.STATISTICS] = _merge_dicts([self._parse_table(tb) for tb in tables])

    async def get_cashflow(self, annual=True):
        """
        gets cash  flow or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            key = Stats.CASHFLOW
            main = cash_flow_annual
        else:
            key = Stats.CASHFLOW_Q
            main = cash_flow_quarter

        return self._get_fund(key, main, annual)

    async def get_balance(self, annual=True):
        """
        gets balance or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            key = Stats.BALANCE
            main = balance_annual
        else:
            key = Stats.BALANCE_Q
            main = balance_quarter

        return self._get_fund(key, main, annual)

    async def get_income(self, annual=True):
        """
        gets income or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            key = Stats.INCOME
            main = income_statement_annual
        else:
            key = Stats.INCOME_Q
            main = income_statement_quarter

        return self._get_fund(key, main, annual)

    async def _get_fund(self, key, main, annual):
        """
            Middle man method cheking is data was already requested
            if it is not gets requests and does preprocessing
        """
        if key in self.__data:
            return self.__data[key]

        data = await self._get_fundamentals(main, annual=annual)
        self.__data[key] = strip_old_json(data)
        return self.__data[key]

    async def _get_fundamentals(self, main_part, annual=True) -> Dict:
        url = fundamentals_url + self.__ticker + main_part
        now = datetime.now()

        if annual:
            delta = timedelta(days=5 * 444)
        else:
            delta = timedelta(days=2 * 444)

        url += fundamental_formatter.format(period1=round((now - delta).timestamp()), period2=round(now.timestamp()),
                                            symbol=self.__ticker)

        fundamental_json = await self._base_request(url, is_json=True)

        return fundamental_json

    async def get_timeseries(self, interval, range_) -> Dict:
        """

        :param interval: granularity
        valid ranges: 1m, 5m, 30m, 1h, 1d, 1wk, 1mo
        :param range_: whole range of dates
        valid ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y or timedelta
        :return:
        """
        if Stats.TIME_SERIES not in self.__data:
            await self._get_timeseries(interval, range_)

        return self.__data[Stats.TIME_SERIES]

    async def _get_timeseries(self, interval, range_: Union[str, timedelta]):
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
            reform_ts = _merge_dicts([reform_ts, data_ts['quote'][0], data_ts['adjclose'][0]])
            self.__data[Stats.TIME_SERIES] = reform_ts

    async def _request_timeseries(self, interval='1wk', range_: Union[str, timedelta] = '1y') -> Dict:
        # TODO support for second query type: param1 & param2 date segment
        # TODO find out if other parameters are actually doing anything
        now = datetime.now()
        if isinstance(range_, str):
            param1 = now - offsets[range_]
        else:
            param1 = now - range_

        url = f'{query}/{self.__ticker}?symbol={self.__ticker}&{query_opt}&interval={interval}&period1=' \
              f'{int(param1.timestamp())}&period2={int(now.timestamp())}' \
              f'&events=div|split|earn&useYfid=true&includePrePost=true'
        ts_json = await self._base_request(url, is_json=True)
        logging.debug(url)
        return ts_json

    async def get_profile(self) -> Dict:

        if Stats.PROFILE not in self.__data:
            await self._get_profile()

        return self.__data[Stats.PROFILE]

    @symbol_check(funcs['profile'])
    async def _get_profile(self, *, souped):

        section = souped.find_all('section')[1]
        data = section.find_all('p')[1].find_all('span')
        name = section.h3.text
        self.__data[Stats.PROFILE] = {
            'Sector': data[1].text,
            'Industry': data[3].text,
            'Name': name
        }

    async def _make_request(self, func) -> AnyStr:
        url = f'{base}/{self.__ticker}/{func}'
        html = await self._base_request(url)
        return html

    @staticmethod
    async def _base_request(url, is_json=False) -> Union[AnyStr, Dict]:
        return await BaseRequest.get(url, is_json)

    def _parse_table(self, table) -> Dict:
        """
        method for parsing HTML table
        """
        dict_table = {}
        for row in table.children:
            first, second = list(row.children)
            first = self._replace_keys(first.text)
            dict_table[first] = second.text

        return dict_table

    @staticmethod
    def _replace_keys(key: AnyStr) -> AnyStr:
        """
        cleaning table keys from unnecessary symbols, such as:
        1) numbers at the end of the string
        2) brackets with date inside of them for consistency
        """
        last_numbers = re.compile(r'((?!\d+$)(?:\S+)|^\d+$)')
        #  search for all non whitespace characters
        #  that are not numbers at the end of the string

        key = ''.join(last_numbers.findall(key))
        #  exclude dates in brackets, only dates have comas in them
        if ',' in key:
            key = key.split('(')[0]  # include everything before opening bracket

        return key


class Tickers:

    def __init__(self, tickers: List[str]):
        self._tickers_names = tickers
        self.order_hash = {
            x: i for i, x in enumerate(self._tickers_names)
        }
        self._tickers: List[Ticker] = [Ticker(ticker) for ticker in tickers]

    def __getitem__(self, ticker: AnyStr):
        try:
            index = self.order_hash[ticker]
            return self._tickers[index]
        except KeyError:
            raise KeyError(f'no such {ticker}')

    async def clear(self, key_arr: List[AnyStr] = None):
        """
        clearing data dictionary inside every __ticker
        :param key_arr: array of keys to clean, if None clean every key
        """
        for tick in self._tickers:
            tick.clear(key_arr)

    async def get_profiles(self):
        return await self._base_get('get_profile')

    async def get_statistics(self):
        return await self._base_get('get_statistics')

    async def get_timeseries(self, interval, range_):
        return await self._base_get('get_timeseries', interval, range_)

    async def get_cashflow(self, annual=True):
        return await self._base_get('get_cashflow', annual)

    async def get_balance(self, annual=True):
        return await self._base_get('get_balance', annual)

    async def get_income(self, annual=True):
        return await self._base_get('get_income', annual)

    async def _base_get(self, func: AnyStr, *args, **kwargs):
        """
        call method without reusing code for each one
        :param func: method name
        """
        coro_arr = [getattr(tick, func)(*args, **kwargs) for tick in self._tickers]
        return await self._get_tasks(coro_arr)

    async def _get_tasks(self, coroutine_array: List[Coroutine]) -> Union[Tuple[List[Dict], List[AnyStr]],
                                                                          List[Union[Dict, BaseException]]]:
        """
        hopefully universal function. For it to work
        every async function in Task must raise NameError if anything goes wrong
        :param coroutine_array:
        :return: array of completed data and array of quotes that catched exceptions or
        array of data and exceptions mixed. See HANDLE_EXCEPTIONS variable
        """
        completed = await asyncio.gather(*coroutine_array, return_exceptions=True)
        if HANDLE_EXCEPTIONS:
            wrong_indexes = []
            excepted_tickers = []
            for i, value in enumerate(completed):
                if isinstance(value, Exception):
                    wrong_indexes.append(i)
                    excepted_tickers.append(self._tickers_names[i])
            for ind in sorted(wrong_indexes, reverse=True):
                del self._tickers_names[ind]
                del self._tickers[ind]
                del completed[ind]

            return completed, excepted_tickers
        else:
            return completed
