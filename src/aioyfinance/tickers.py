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


from .base_requests import BaseRequest

HANDLE_EXCEPTIONS = True  # you can either let library throw errors in data list or separate them


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


def strip_old_json(fund_json):
    """
    format of returned fundamentals json is not good, many elements without data
    trying to clean things up a bit

    :param fund_json: dictionary from fundamentals api
    :return: probably cleaner dictionary
    """

    inside = fund_json['timeseries']['result']

    inside = list(filter(lambda x: 'timestamp' in x, inside))

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
        self.ticker = ticker
        self._statistics = None
        self._profile = None
        self._timeseries = None
        self._income = None
        self._balance = None
        self._cashflow = None

        self._income_quarterly = None
        self._balance_quarterly = None
        self._cashflow_quarterly = None

    async def get_statistics(self):
        if self._statistics is None:
            await self._get_statistics()

        return self._statistics

    async def get_cashflow(self, annual=True):
        """
        gets cash  flow or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            if self._cashflow is not None:
                return self._cashflow
            else:
                main = cash_flow_annual
        else:
            if self._cashflow_quarterly is not None:
                return self._cashflow_quarterly
            else:
                main = cash_flow_quarter

        data = await self._get_fundamentals(main, annual=annual)
        return strip_old_json(data)

    async def get_balance(self, annual=True):
        """
        gets balance or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            if self._balance is not None:
                return self._balance
            else:
                main = balance_annual
        else:
            if self._balance_quarterly is not None:
                return self._balance_quarterly
            else:
                main = balance_quarter

        data = await self._get_fundamentals(main, annual=annual)
        return strip_old_json(data)

    async def get_income(self, annual=True):
        """
        gets income or quarterly income
        :param annual: True if Annual, False if Quraterly
        :return: stripped dictionary
        """
        if annual:
            if self._income is not None:
                return self._income
            else:
                main = income_statement_annual
        else:
            if self._income_quarterly is not None:
                return self._income_quarterly
            else:
                main = income_statement_quarter

        data = await self._get_fundamentals(main, annual=annual)
        return strip_old_json(data)

    async def get_timeseries(self, interval, range_):
        """

        :param interval: granularity
        valid ranges: 1m, 5m, 30m, 1h, 1d, 1wk, 1mo
        :param range_: whole range of dates
        valid ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y or timedelta
        :return:
        """
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

    async def _get_fundamentals(self, main_part, annual=True):
        url = fundamentals_url + self.ticker + main_part
        now = datetime.now()

        if annual:
            delta = timedelta(days=5 * 444)
        else:
            delta = timedelta(days=2 * 444)

        url += fundamental_formatter.format(period1=round((now - delta).timestamp()), period2=round(now.timestamp()),
                                            symbol=self.ticker)

        fundamental_json = await self._base_request(url, is_json=True)

        return fundamental_json

    async def _request_timeseries(self, interval='1wk', range_: Union[str, timedelta] = '1y'):
        # TODO support for second query type: param1 & param2 date segment
        # TODO find out if other parameters are actually doing anything
        now = datetime.now()
        if isinstance(range_, str):
            param1 = now - offsets[range_]
        else:
            param1 = now - range_

        url = f'{query}/{self.ticker}?symbol={self.ticker}&{query_opt}&interval={interval}&period1={int(param1.timestamp())}&period2={int(now.timestamp())}&events=div|split|earn&useYfid=true&includePrePost=true'
        ts_json = await self._base_request(url, is_json=True)
        logging.debug(url)
        return ts_json

    @staticmethod
    async def _base_request(url, is_json=False):
        return await BaseRequest.get(url, is_json)

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
        self._statistics = _merge_dicts([self._parse_table(tb) for tb in tables])

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
        last_numbers = re.compile(r'((?!\d+$)(?:\S+)|^\d+$)') #search for all non whitespace characters
        # that are not numbers at the end of the string
        key = ''.join(last_numbers.findall(key))

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
        except KeyError as e:
            raise KeyError(f'no such {ticker}')

    async def _base_get(self, func: AnyStr, *args, **kwargs):
        coro_arr = [getattr(tick, func)(*args, **kwargs) for tick in self._tickers]
        return await self._get_tasks(coro_arr)

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

    async def _get_tasks(self, coroutine_array: List[Coroutine]) -> Union[Tuple[List[Dict], List[AnyStr]], \
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
