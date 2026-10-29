# analysis/harmonics.py
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PatternRatio:
    name: str
    xab: Tuple[float, float] | float
    abc: Tuple[float, float]
    bcd: Tuple[float, float] | None
    xad: Tuple[float, float] | float


PATTERNS = [
    PatternRatio("Gartley", 0.618, (0.382, 0.886), (1.13, 1.618), 0.786),
    PatternRatio("Bat", (0.382, 0.50), (0.382, 0.886), (1.618, 2.618), 0.886),
    PatternRatio("Butterfly", 0.786, (0.382, 0.886), (1.618, 2.24), (1.27, 1.618)),
    PatternRatio("Crab", (0.382, 0.618), (0.382, 0.886), (2.24, 3.618), 1.618),
    PatternRatio("Deep Crab", 0.886, (0.382, 0.886), (2.0, 3.618), 1.618),
]


def find_pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        if highs[i] == max(highs[i - left:i + right + 1]):
            is_high[i] = True
        if lows[i] == min(lows[i - left:i + right + 1]):
            is_low[i] = True
    pivots = []
    for i in range(n):
        if is_high[i]:
            pivots.append({"idx": i, "price": highs[i], "type": "high", "time": df.index[i]})
        if is_low[i]:
            pivots.append({"idx": i, "price": lows[i], "type": "low", "time": df.index[i]})
    return pd.DataFrame(pivots)


def _in_range(val: float, target) -> bool:
    if isinstance(target, (int, float)):
        return abs(val - target) / target < 0.08
    low, high = target
    return low * 0.92 <= val <= high * 1.08


def detect_harmonics(df: pd.DataFrame, lookback_pivots: int = 40) -> List[dict]:
    pivots = find_pivots(df, left=2, right=2)
    if len(pivots) < 5:
        return []
    pivots = pivots.tail(lookback_pivots).reset_index(drop=True)
    results = []

    for i in range(len(pivots) - 4):
        pts = pivots.iloc[i:i + 5]
        types = pts["type"].tolist()
        prices = pts["price"].values
        times = pts["time"].tolist()
        if not (types[0] != types[1] and types[1] != types[2] and types[2] != types[3] and types[3] != types[4]):
            continue
        X, A, B, C, D = prices
        bullish = types[0] == "low"
        XA, AB, BC, CD, AD = abs(A - X), abs(B - A), abs(C - B), abs(D - C), abs(D - A)
        if XA == 0 or AB == 0 or BC == 0:
            continue
        xab, abc, bcd, xad = AB / XA, BC / AB, CD / BC if BC else 0, AD / XA
        for pat in PATTERNS:
            if not _in_range(xab, pat.xab): continue
            if not _in_range(abc, pat.abc): continue
            if pat.bcd is not None and not _in_range(bcd, pat.bcd): continue
            if not _in_range(xad, pat.xad): continue
            results.append({"name": pat.name, "direction": "bullish" if bullish else "bearish", "status": "completed",
                "X": float(X), "A": float(A), "B": float(B), "C": float(C), "D": float(D),
                "time_D": str(times[4]), "error": round(abs(xad - (pat.xad if isinstance(pat.xad, float) else sum(pat.xad)/2)), 4)})

    if len(pivots) >= 4:
        pts = pivots.iloc[-4:]
        types = pts["type"].tolist()
        prices = pts["price"].values
        times = pts["time"].tolist()
        current = float(df["close"].iloc[-1])
        if types[0] != types[1] and types[1] != types[2] and types[2] != types[3]:
            X, A, B, C = prices
            bullish = types[0] == "low"
            XA, AB, BC = abs(A - X), abs(B - A), abs(C - B)
            if XA > 0 and AB > 0 and BC > 0:
                xab, abc = AB / XA, BC / AB
                for pat in PATTERNS:
                    if not _in_range(xab, pat.xab): continue
                    if not _in_range(abc, pat.abc): continue
                    target_ad = XA * (pat.xad if isinstance(pat.xad, float) else (pat.xad[0] + pat.xad[1]) / 2)
                    d_target = A - target_ad if bullish else A + target_ad
                    if abs(current - d_target) / abs(d_target) < 0.06:
                        results.append({"name": pat.name, "direction": "bullish" if bullish else "bearish", "status": "forming",
                            "X": float(X), "A": float(A), "B": float(B), "C": float(C),
                            "D_projected": round(d_target, 5), "current": current, "time_C": str(times[3])})

    results = sorted(results, key=lambda x: 0 if x["status"] == "forming" else 1)
    return results[:5]
