# analysis/candles.py
import pandas as pd
import numpy as np


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

        if lower >= body * 2 and upper <= body * 0.4 and c[i] > o[i] * 0.99:
            patterns.append({"name": "Hammer", "direction": "bullish", "bar": i, "time": str(df.index[i]), "strength": "medium"})

        if upper >= body * 2 and lower <= body * 0.4 and c[i] < o[i] * 1.01:
            patterns.append({"name": "Shooting Star", "direction": "bearish", "bar": i, "time": str(df.index[i]), "strength": "medium"})

        if body / range_ < 0.1:
            patterns.append({"name": "Doji", "direction": "neutral", "bar": i, "time": str(df.index[i]), "strength": "weak"})

        if i >= 2:
            if (c[i-2] < o[i-2] and abs(c[i-1] - o[i-1]) / (h[i-1] - l[i-1] + 1e-9) < 0.3 and c[i] > o[i] and c[i] > (o[i-2] + c[i-2]) / 2):
                patterns.append({"name": "Morning Star", "direction": "bullish", "bar": i, "time": str(df.index[i]), "strength": "strong"})
            if (c[i-2] > o[i-2] and abs(c[i-1] - o[i-1]) / (h[i-1] - l[i-1] + 1e-9) < 0.3 and c[i] < o[i] and c[i] < (o[i-2] + c[i-2]) / 2):
                patterns.append({"name": "Evening Star", "direction": "bearish", "bar": i, "time": str(df.index[i]), "strength": "strong"})

    seen = set()
    unique = []
    for p in reversed(patterns):
        key = (p["name"], p["direction"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique[:6]
