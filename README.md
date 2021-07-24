# aioyfinance

Yahoo Finance asynchronous data downloader built with aiohttp and inspired by [yfinance](https://github.com/ranaroussi/yfinance)

### Current progress:
####Implemented:
- timeseries getter
- statistics getter (raw names)
- profile getter
- multiple tickers simultaneously 
- parsing different financials (income statement, balance sheet, cash flow)
- global settings
- proxy implementation with support for random proxy from list

####ToDo:
- parsing analysis and holders
- ETF support (You can get timeseries, other methods will raise exceptions)
- easy pandas conversion

### Ticker object

For single ticker operations. 
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
    
    # all the results are cached, to make new requests call
    nvda.clear()

```

Exception handling is really primitive right now. *NameError* is raised if ticker is misspelled
or *HTTPError* is raised if request failed after several retries

### Tickers object
For multiple tickers. 
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
    # also you can get corresponding ticker object by __gettitem__
    ticker = tickers['msft']
    # all the results from requests are saved in corresponding ticker object, so 
    data = await ticker.get_income(annual=False) # won`t make requests to server
    # to clean all tickers together from data call
    tickers.clear()
    
    
```
### Configuration
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
        # and tickers that caught exceptions are cleared from tickers object
    )
    
    no_exc = yf.Config.create(handle_exceptions=False)
    
    tickers = yf.Tickers(['aapl', 'wrong'])
    data_with_exceptions = await tickers.get_statistics()

```
