from datetime import datetime, timedelta

base = 'https://finance.yahoo.com/quote'
query = 'https://query1.finance.yahoo.com/v8/finance/chart'
query_opt = 'region=US&lang=en-US'
funcs = {
    'statistics': 'key-statistics',
    'financials': 'financials',
    'balance_sheet': 'balance-sheet',
    'cash_flow': 'cash-flow',
    'main': '',
    'analysis': 'analysis',
    'profile': 'profile'
}

offsets = {
    '1d': timedelta(days=1),
    '5d': timedelta(days=5),
    '1mo': timedelta(days=30),
    '3mo': timedelta(days=90),
    '6mo': timedelta(days=180),
    '1y': timedelta(days=365),
    '2y': timedelta(days=730),
    '5y': timedelta(days=1825),
    '20y': timedelta(days=7300)
}
