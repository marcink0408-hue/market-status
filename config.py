# config.py
SYMBOLS = {
    "w20": {"yf": "WIG20.WA", "name": "WIG20"},
    "us500": {"yf": "^GSPC", "name": "S&P 500"},
    "gold": {"yf": "GC=F", "name": "Gold"},
    "silver": {"yf": "SI=F", "name": "Silver"},
    "eurpln": {"yf": "EURPLN=X", "name": "EUR/PLN"},
    "eurusd": {"yf": "EURUSD=X", "name": "EUR/USD"},
    "usdpln": {"yf": "USDPLN=X", "name": "USD/PLN"},
    "usdjpy": {"yf": "USDJPY=X", "name": "USD/JPY"},
    "copper": {"yf": "HG=F", "name": "Copper"},
    "eu50": {"yf": "^STOXX50E", "name": "Euro Stoxx 50"},
    "uk100": {"yf": "^FTSE", "name": "FTSE 100"},
}

TIMEFRAMES = {
    "1H": {"interval": "1h", "period": "60d"},
    "4H": {"interval": "1h", "period": "120d"},
    "Daily": {"interval": "1d", "period": "2y"},
}

RENKO_ATR_PERIOD = 14
RENKO_ATR_MULTIPLIER = 0.5
HARMONIC_PATTERNS = ["Gartley", "Bat", "Crab", "Deep Crab", "Butterfly"]
