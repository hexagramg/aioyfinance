# aioyfinance

Yahoo Finance asynchronous data downloader built with aiohttp and inspired by [yfinance](https://github.com/ranaroussi/yfinance)

#### Current progress:
- [x] timeseries getter
- [x] statistics getter (raw names)
- [x] profile getter
- [x] multiple tickers simultaneously 
- [x] parsing different financials (income statement, balance sheet, cash flow) 
- [ ] parsing analysis and holders
- [ ] ETF support (You can get timeseries, other methods will raise exceptions)
- [x] global settings
- [x] proxy implementation with support for random proxy from list
- [ ] easy pandas conversion

### Ticker object
```python
import aioyfinance as yf
from datetime import timedelta

async def quick():
    nvda = yf.Ticker('nvda')
    
    # getting raw timeseries
    timeseries = await nvda.get_timeseries('1wk', '2y')
    # or you can do
    delta = timedelta(hours=2)
    timeseries = await nvda.get_timeseries('5m', delta)
    
    # getting statistics
    stats = await nvda.get_statistics()
    
    # getting profile
    profile = await nvda.get_profile()
    
    # fundamentals methods
    # annual=False if quarterly
    balance_sheet_quarterly = await nvda.get_balance(annual=False) 
    cash_flow = await nvda.get_cashflow()
    income = await nvda.get_income()

```

Exception handling is really primitive right now. *NameError* is raised if ticker is misspelled
or *HTTPError* is raised if request failed after several retries

### Tickers object

```python
import aioyfinance as yf

async def quick():
    tickers_names = ['nvda','aapl', 'msft']
    
    tickers = yf.Tickers(tickers_names)
    
    # doing any task will return 2 values,
    # list of results and list of tickers that catched exceptions
    # unless variable HANDLE_EXCEPTION is set to False
    ts, excepted = await tickers.get_timeseries('1d', '6mo')
    data, _ = await tickers.get_statistics()
    data, _ = await tickers.get_profiles()
    data, _ = await tickers.get_income(annual=False)
    # for every method in Ticker there is a caller in Tickers
    
```

There is a way to configure some requests handling parameters. There is special class Config that controls
all of them. If you don`t intend changing defaults, you can skip this part as config is created by default

```python
import aioyfinance as yf


async def params():
    # here are the defaults
    conf = yf.Config.create( # only kwargs are accepted
        parallel=True, # allow overlapping of requests
        max_batch=5, # maximum requests active
        proxy_url=None, # either string or list of strings. If it is list, proxy is picked randomly
        max_retries=3, # amount of retries
        retry_delay=1, # delay between retries
        
        # there is a random delay between each request, set them according to your needs 
        max_rand_delay=0.5,
        min_rand_delay=0.01,
        
        handle_exceptions=True # this variable alters tickers return behaviour. 
        # setting it to False  results in Tickers returning single list of Union[dict, BaseException]
        # by default it is True and tuple(Results, TickersThatCaughtExceptions) is returned
    )
    
    no_exc = yf.Config.create(handle_exceptions=False)
    
    tickers = yf.Tickers(['aapl', 'wrong'])
    data_with_exceptions = await tickers.get_statistics()

```
