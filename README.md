# aioyfinance

Yahoo Finance asynchronous data downloader built with aiohttp and inspired by [yfinance](https://github.com/ranaroussi/yfinance)

#### Current progress:
- [x] timeseries getter
- [x] statistics getter (raw names)
- [x] profile getter
- [x] multiple tickers simultaneously 
- [ ] parsing different financials (income statement, balance sheet, cash flow)
- [ ] parsing analysis and holders
- [ ] ETF support  
- [ ] global settings
- [ ] proxy implementation
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

```

Exception handling is really primitive right now. *NameError* is returned if ticker is misspelled

### Tickers object

```python
import aioyfinance as yf

async def quick():
    tickers_names = ['nvda','aapl', 'msft']
    
    tickers = yf.Tickers(tickers_names)
    
    #doing any task will return 2 values, list of results
    #and list of misspelled tickers
    ts, wrong_names = await tickers.get_timeseries('1d', '6mo')
    data, _ = await tickers.get_statistics()
    data, _ = await tickers.get_profiles()
```

