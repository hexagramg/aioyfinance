# aioyfinance

Yahoo Finance asynchronous data downloader built with aiohttp and inspired by [yfinance](https://github.com/ranaroussi/yfinance)

#### Current progress:
- [x] timeseries getter
- [x] statistics getter (raw names)
- [x] profile getter
- [x] multiple tickers simultaneously 
- [ ] parsing different financials (income statement, balance sheet, cash flow) [partial support] 
- [ ] parsing analysis and holders
- [ ] ETF support  
- [ ] global settings
- [x] proxy implementation
- [ ] easy pandas conversion

### Ticker object
```python
import aioyfinance as yf
from datetime import timedelta

async def quick():
    nvda = yf.Ticker('nvda')
    
    #getting raw timeseries
    timeseries = await nvda.get_timeseries('1wk', '2y')
    #or you can do
    delta = timedelta(hours=2)
    timeseries = await nvda.get_timeseries('5m', delta)
    
    #getting statistics
    stats = await nvda.get_statistics()
    
    #getting profile
    profile = await nvda.get_profile()
    
    #fundamentals methods
    #False if quarterly
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
    
    #doing any task will return 2 values, list of results
    #and list of tickers that catched exceptions
    ts, excepted = await tickers.get_timeseries('1d', '6mo')
    data, _ = await tickers.get_statistics()
    data, _ = await tickers.get_profiles()
```

There is a way to configure some requests handling parameters

```python
import aioyfinance as yf


async def params():
    yf.PARALLEL = True  # allow overlapping of requests
    yf.MAX_BATCH = 5  # maximum requests active
    yf.PROXY_URL = None  # set this parameter according to aiohttp documentation
    yf.MAX_RETRIES = 3  # amount of retries
    yf.RETRY_DELAY = 1  # delay between retries

    # there is a random delay between each request, set them according to your needs
    yf.MAX_RAND_DELAY = 0.5
    yf.MIN_RAND_DELAY = 0.1

    yf.HANDLE_EXCEPTIONS = True 
    #Setting this variable to False alters tickers return argument. Only list of results is returned
    #With exceptions untouched
    
    tickers = yf.Tickers(['aapl', 'wrong'])
    data_with_exceptions = await tickers.get_statistics()

```
