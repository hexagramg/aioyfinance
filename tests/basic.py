import unittest
import aioyfinance as yf
import asyncio as asy

class MyTestCase(unittest.TestCase):

    def test_wrong(self):
        loop = asy.get_event_loop()

        wrong_ticker = 'lalaboba'
        ticker = yf.Ticker(wrong_ticker)

        fails = []

        def try_block(callable):
            nonlocal fails

            try:
                loop.run_until_complete(callable)
            except NameError as e:
                fails.append(True)
            else:
                fails.append(False)

        try_block(ticker.get_timeseries('1d', '1mo'))
        try_block(ticker.get_statistics())
        try_block(ticker.get_profile())

        self.assertNotIn(False, fails)

    def test_mult_wrong(self):

        loop = asy.get_event_loop()

        wrong_tickers = ['amd', 'lalaboba', 'nvda']
        tickers = yf.Tickers(wrong_tickers)


        right, wrong = loop.run_until_complete(tickers.get_statistics())

        self.assertEqual(len(right), 2)
        self.assertEqual(len(wrong), 1)

if __name__ == '__main__':
    unittest.main()
