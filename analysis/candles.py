# analysis/candles.py
import pandas as pd
import numpy as np
from datetime import datetime, timezone

TF_SECONDS = {"1H": 3600, "4H": 4 * 3600, "1D": 24 * 3600}


def detect_candlestick_patterns(df: pd.DataFrame, lookback: int = 10) -> list:
    if len(df) < 5:
        return []
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    n = len(df)
    patterns = []

    for i in range(max(3, n - lookback), n):
        body = abs(c[i] - o[i])
        upper = h[i] - max(o[i], c[i])
        lower = min(o[i], c[i]) - l[i]
        range_ = h[i] - l[i]
        if range_ == 0:
            continue

        if (c[i] > o[i] and c[i-1] < o[i-1] and c[i] >= o[i-1] and o[i] <= c[i-1] and body > abs(c[i-1] - o[i-1]) * 0.9):
            patterns.append({"name": "Bullish Engulfing", "direction": "bullish", "bar": i, "time": str(df.index[i]), "strength": "strong"})

        if (c[i] < o[i] and c[i-1] > o[i-1] and c[i] <= o[i-1] and o[i] >= c[i-1] and body > abs(c[i-1] - o[i-1]) * 0.9):
            patterns.append({"name": "Bearish Engulfing", "direction": "bearish", "bar": i, "time": str(df.index[i]), "strength": "strong"})

        # POPRAWKA: Hammer musi być świecą byczą (c > o), bez mnożnika 0.99
        if lower >= body * 2 and upper <= body * 0.4 and c[i] > o[i]:
            patterns.append({"name": "Hammer", "direction": "bullish", "bar": i, "time": str(df.index[i]), "strength": "medium"})

        # POPRAWKA: Shooting Star musi być świecą niedźwiedzią (c < o), bez mnożnika 1.01
        if upper >= body * 2 and lower <= body * 0.4 and c[i] < o[i]:
            patterns.append({"name": "Shooting Star", "direction": "bearish", "bar": i, "time": str(df.index[i]), "strength": "medium"})

        if body / range_ < 0.1:
            patterns.append({"name": "Doji", "direction": "neutral", "bar": i, "time": str(df.index[i]), "strength": "weak"})

        if i >= 2:
            body1 = abs(c[i-2] - o[i-2])
            range1 = h[i-2] - l[i-2]
            # POPRAWKA: Morning Star — pierwsza świeca musi być długa (body1 > 50% range1)
            if (c[i-2] < o[i-2] and range1 > 0 and body1 > range1 * 0.5
                and abs(c[i-1] - o[i-1]) / (h[i-1] - l[i-1] + 1e-9) < 0.3
                and c[i] > o[i] and c[i] > (o[i-2] + c[i-2]) / 2):
                patterns.append({"name": "Morning Star", "direction": "bullish", "bar": i, "time": str(df.index[i]), "strength": "strong"})
            # POPRAWKA: Evening Star — pierwsza świeca musi być długa (body1 > 50% range1)
            if (c[i-2] > o[i-2] and range1 > 0 and body1 > range1 * 0.5
                and abs(c[i-1] - o[i-1]) / (h[i-1] - l[i-1] + 1e-9) < 0.3
                and c[i] < o[i] and c[i] < (o[i-2] + c[i-2]) / 2):
                patterns.append({"name": "Evening Star", "direction": "bearish", "bar": i, "time": str(df.index[i]), "strength": "strong"})

    seen = set()
    unique = []
    for p in reversed(patterns):
        key = (p["name"], p["direction"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique[:6]

def _is_candle_closed(bar_time, timeframe, now=None):
    """Określa czy świeca jest zamknięta na podstawie czasu końca i interwału."""
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        stamp = pd.Timestamp(bar_time)
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize("UTC")
        else:
            stamp = stamp.tz_convert("UTC")
    except (TypeError, ValueError, OverflowError):
        return False
    end_time = stamp + pd.Timedelta(seconds=TF_SECONDS.get(timeframe, 3600))
    now_ts = pd.Timestamp(now)
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize("UTC")
    return bool(now_ts >= end_time)


def analyze_candle(df, index=-1, timeframe="4H", now=None):
    """Analizuje pojedynczą świecę i eksportuje pola dla wyzwalacza i S/R.

    Zwraca dict z polami: time, open, high, low, close, body, upper_wick,
    lower_wick, range, body_direction, close_position, close_location,
    is_closed, timeframe.
    """
    if df is None or df.empty:
        return None
    n = len(df)
    idx = index if index >= 0 else n + index
    if idx < 0 or idx >= n:
        return None
    row = df.iloc[idx]
    try:
        o = float(row["open"])
        h = float(row["high"])
        l = float(row["low"])
        c = float(row["close"])
    except (TypeError, ValueError):
        return None
    if not all(v == v and abs(v) != float("inf") for v in (o, h, l, c)):
        return None
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    range_ = h - l
    if c > o:
        body_direction = "bullish"
    elif c < o:
        body_direction = "bearish"
    else:
        body_direction = "neutral"
    if range_ > 0:
        close_position = (c - l) / range_
        if close_position >= 0.66:
            close_location = "upper"
        elif close_position <= 0.33:
            close_location = "lower"
        else:
            close_location = "middle"
    else:
        close_position = None
        close_location = "undefined"
    bar_time = str(df.index[idx])
    is_closed = _is_candle_closed(bar_time, timeframe, now)
    return {
        "time": bar_time,
        "open": round(o, 5),
        "high": round(h, 5),
        "low": round(l, 5),
        "close": round(c, 5),
        "body": round(body, 5),
        "upper_wick": round(upper_wick, 5),
        "lower_wick": round(lower_wick, 5),
        "range": round(range_, 5),
        "body_direction": body_direction,
        "close_position": round(close_position, 4) if close_position is not None else None,
        "close_location": close_location,
        "is_closed": bool(is_closed),
        "timeframe": timeframe,
    }


def analyze_candle_sequence(df, lookback=5, timeframe="4H", now=None):
    """Zwraca analizę sekwencji ostatnich N świec z opisem sytuacji."""
    if df is None or df.empty:
        return {
            "candles": [],
            "description": "Brak danych OHLC",
            "timeframe": timeframe,
            "lookback": lookback,
            "analyzed_at": None,
        }
    n = len(df)
    start = max(0, n - lookback)
    candles = []
    for i in range(start, n):
        c = analyze_candle(df, i, timeframe, now)
        if c:
            candles.append(c)
    if not candles:
        description = "Brak analizowalnych świec"
    else:
        directions = [c["body_direction"] for c in candles]
        bullish = directions.count("bullish")
        bearish = directions.count("bearish")
        neutral = directions.count("neutral")
        parts = []
        if bullish:
            parts.append(f"{bullish} wzrostowa{'e' if bullish > 1 else ''}")
        if bearish:
            parts.append(f"{bearish} spadkowa{'e' if bearish > 1 else ''}")
        if neutral:
            parts.append(f"{neutral} neutralna")
        description = ", ".join(parts) if parts else "Brak wyraźnego trendu"
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "candles": candles,
        "description": description,
        "timeframe": timeframe,
        "lookback": lookback,
        "analyzed_at": analyzed_at,
    }


def candle_analysis_summary(df, timeframe="4H", now=None, lookback=5):
    """Zwraca podsumowanie analizy świec: ostatnia zamknięta świeca, sekwencja,
    interwał i czas analizy. Opis wynika wyłącznie z rzeczywistych danych OHLC."""
    if df is None or df.empty:
        return {
            "timeframe": timeframe,
            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_closed_candle": None,
            "last_candle_description": "Brak danych OHLC",
            "sequence_description": "Brak danych OHLC",
            "candles": [],
        }
    n = len(df)
    seq = analyze_candle_sequence(df, lookback, timeframe, now)
    last_closed = None
    for i in range(n - 1, -1, -1):
        c = analyze_candle(df, i, timeframe, now)
        if c and c["is_closed"]:
            last_closed = c
            break
    last_desc = "Brak zamkniętej świecy do analizy"
    if last_closed:
        dir_pl = {
            "bullish": "wzrostowa",
            "bearish": "spadkowa",
            "neutral": "neutralna",
        }[last_closed["body_direction"]]
        last_desc = (
            f"Ostatnia zamknięta świeca ({timeframe}) o {last_closed['time']}: "
            f"{dir_pl}, korpus {last_closed['body']}, "
            f"zamknięcie w {last_closed['close_location']} części zakresu, "
            f"górny cień {last_closed['upper_wick']}, dolny cień {last_closed['lower_wick']}."
        )
    return {
        "timeframe": timeframe,
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_closed_candle": last_closed,
        "last_candle_description": last_desc,
        "sequence_description": seq["description"],
        "candles": seq["candles"],
    }