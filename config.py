# config.py
SYMBOLS = {
    "w20": {"yf": "WIG20.WA", "name": "WIG20", "daily_timezone": "Europe/Warsaw"},
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
    "1H": {"interval": "1h", "period": "120d"},
    "4H": {"interval": "1h", "period": "120d"},
    "Daily": {"interval": "1d", "period": "2y"},
}

# Wagi kontekstu są jawnymi założeniami modelu, nie wynikami optymalizacji.
# 4H wyznacza kierunek i bazową ocenę; 1D i 1H tylko ją korygują.
MTF_CONTEXT_WEIGHTS = {"1D": 0.15, "1H": 0.10}

RENKO_ATR_PERIOD = 14
RENKO_ATR_MULTIPLIER = 0.5
HARMONIC_PATTERNS = ["Gartley", "Bat", "Crab", "Deep Crab", "Butterfly"]

# --- Parametry stref wsparcia/oporu (S/R) ---
# Swing high/low jest potwierdzany po tej liczbie świec z każdej strony (brak lookahead).
SWING_CONFIRMATION_BARS = 3
# Tolerancja grupowania swingów w strefę: 0.5 * ATR(14) danego interwału.
SR_GROUP_TOLERANCE_ATR_MULT = 0.5
# Tolerancja dopasowania stref wielointerwałowych: 0.5 * ATR(14) odpowiedniego interwału.
SR_MULTITF_TOLERANCE_ATR_MULT = 0.5
# Maksymalna liczba najważniejszych stref pokazywanych nad ceną i pod ceną.
SR_MAX_ZONES_ABOVE = 2
SR_MAX_ZONES_BELOW = 2

# --- Parametry modelu gotowości (readiness) ---
# Wagi kryteriów (razem 100 pkt), identyczne dla LONG i SHORT.
READINESS_WEIGHTS = {
    "context_1d": 15,   # Kontekst 1D
    "structure_4h": 25, # Struktura 4H
    "sr_position": 20,  # Położenie względem S/R
    "trigger": 30,      # Wyzwalacz 1H
    "rr": 10,           # Stosunek zysk/ryzyko
}
# Progi gotowości (stałe, nie oznaczają prawdopodobieństwa zysku).
READINESS_THRESHOLD_NO_DIRECTION = 29   # 0-29: BRAK KIERUNKU
READINESS_THRESHOLD_OBSERVE = 54        # 30-54: OBSERWUJ
READINESS_THRESHOLD_PREPARATION = 79    # 55-79: PRZYGOTOWANIE
READINESS_THRESHOLD_ENTRY_CANDIDATE = 80 # 80-100: kandydat do WEJŚCIA
# Minimalna różnica punktowa między LONG i SHORT (konfiguracyjny parametr).
MIN_DIFFERENCE_POINTS = 5
# Minimalne RR dla wejścia.
MIN_RR = 1.5
# Bufor unieważnienia w ATR.
INVALIDATION_BUFFER_ATR_MULT = 0.25
# Maksymalny wiek danych (liczba oczekiwanych świec danego interwału).
MAX_DATA_AGE = 2
# Czas życia setupu (liczba świec 4H z realnej sesji).
SETUP_EXPIRY_BARS = 3
CONFIRMED_VALID_BARS = 2

STALE_DATA_HOURS = 8
STALE_DATA_WARN_HOURS = 5
DECISIONS_LOG_MAX = 200
DECISIONS_SCHEMA_VERSION = 1
PRIMARY_TIMEFRAME = "4H"
