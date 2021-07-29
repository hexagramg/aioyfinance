import unittest
import aioyfinance as yf
import asyncio as asy
from aioyfinance.old_urls import *
from aioyfinance.tickers import strip_old_json
from collections import defaultdict
from pprint import pprint

loop = asy.get_event_loop()

class MyTestCase(unittest.TestCase):

    def test_right(self):
        right_ticker = 'nvda'
        ticker = yf.Ticker(right_ticker)

        fails = []
        data = []
        def try_block(callable):
            nonlocal fails

            try:
                d = loop.run_until_complete(callable)
            except Exception as e:
                fails.append(False)
            else:
                fails.append(True)
                data.append(d)

        try_block(ticker.get_timeseries('1d', '1mo'))
        try_block(ticker.get_statistics())
        try_block(ticker.get_profile())

        self.assertNotIn(False, fails)
    def test_wrong(self):
        wrong_ticker = 'lalaboba'
        ticker = yf.Ticker(wrong_ticker)

        fails = []
        data = []
        def try_block(callable):
            nonlocal fails

            try:
                d = loop.run_until_complete(callable)
            except Exception as e:
                fails.append(True)
            else:
                fails.append(False)
                data.append(d)

        try_block(ticker.get_timeseries('1d', '1mo'))
        try_block(ticker.get_statistics())
        try_block(ticker.get_profile())
        try_block(ticker.get_income())

        self.assertNotIn(False, fails)

        tickers = yf.Tickers(['lolololololo'])
        r,w = loop.run_until_complete(tickers.get_income())
        self.assertListEqual(w, ['lolololololo'])


    def test_mult_wrong(self):
        wrong_tickers = ['amd', 'lalaboba', 'nvda', 'fb', 'goog', 'tsla', 'v', 'bac']
        tickers = yf.Tickers(wrong_tickers)


        right, wrong = loop.run_until_complete(tickers.get_statistics())

        self.assertEqual(len(right), 7)
        self.assertEqual(len(wrong), 1)

        wrong_tickers = ['amd', 'lalaboba', 'nvda', 'fb', 'goog', 'tsla', 'v', 'bac']
        tickers = yf.Tickers(wrong_tickers)
        right, wrong = loop.run_until_complete(tickers.get_income())
        self.assertEqual(len(right), 7)
        self.assertEqual(len(wrong), 1)

    def test_fund_strip(self):

        ticker = yf.Ticker('nvda')

        data = loop.run_until_complete(ticker._get_fundamentals(INCOME_STATEMENT_ANNUAL))

        strip = strip_old_json(data)

        self.assertIsNotNone(strip)

    def test_income(self):
        #TODO probably better tests needed, these are shallow
        ticker = yf.Ticker('nvda')

        data = loop.run_until_complete(ticker.get_income())
        data_quarterly = loop.run_until_complete(ticker.get_income(False))

        self.assertIsNotNone(data)
        self.assertIsNotNone(data_quarterly)

    def test_gettitem(self):
        names = ['aapl', 'goog', 'msft', 'v']
        tickers = yf.Tickers(names)
        ticker = tickers['goog']
        data = loop.run_until_complete(ticker.get_income())
        data_ = loop.run_until_complete(tickers.get_income())

        self.assertIsNotNone(data)
        self.assertIsNotNone(data_)

    def test_ETF(self):
        ticker = yf.Ticker('SPY')
        data = loop.run_until_complete(ticker.get_timeseries('1d', '1mo'))
        with self.assertRaises(NameError):
            loop.run_until_complete(ticker.get_statistics())

        self.assertIsNotNone(data)

    def test_config(self):
        tickers = yf.Tickers(['aapl', 'nvda', 'actuallywrong'])
        ri_wro = loop.run_until_complete(tickers.get_balance())

        conf = yf.Config.create(handle_exceptions=False)
        both = loop.run_until_complete(tickers.get_income())

        self.assertIsInstance(both, list)
        self.assertIsInstance(ri_wro, tuple)
        self.assertIsNotNone(ri_wro[1])
        self.assertIsInstance(ri_wro[0][0], dict)

        conf = yf.Config.create()

    def test_stat(self):
        tickers = yf.Tickers(['aapl', 'nvda'])
        conf = yf.Config.create(handle_exceptions=False)
        right= loop.run_until_complete(tickers.get_statistics())
        for res in right:
            self.assertNotIsInstance(res, Exception)
        conf = yf.Config.create(handle_exceptions=True)

if __name__ == '__main__':
    unittest.main()
