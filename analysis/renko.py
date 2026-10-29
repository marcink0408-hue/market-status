# analysis/renko.py
import pandas as pd
import numpy as np


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def build_renko(df: pd.DataFrame, brick_size=None, atr_period: int = 14, atr_mult: float = 0.5) -> pd.DataFrame:
    if brick_size is None:
        a = atr(df, atr_period).iloc[-1]
        if pd.isna(a) or a == 0:
            brick_size = float(df["close"].std() * 0.1) if len(df) > 5 else 0.001
        else:
            brick_size = float(a * atr_mult)

    bricks = []
    prices = df["close"].values
    times = df.index
    brick_open = float(prices[0])
    direction = 0

    for i in range(1, len(prices)):
        price = float(prices[i])
        ts = times[i]
        while True:
            if direction >= 0:
                if price >= brick_open + brick_size:
                    brick_close = brick_open + brick_size
                    bricks.append({"datetime": ts, "open": brick_open, "high": brick_close, "low": brick_open, "close": brick_close, "direction": 1})
                    brick_open = brick_close
                    direction = 1
                    continue
                elif direction == 1 and price <= brick_open - brick_size:
                    brick_close = brick_open - brick_size
                    bricks.append({"datetime": ts, "open": brick_open, "high": brick_open, "low": brick_close, "close": brick_close, "direction": -1})
                    brick_open = brick_close
                    direction = -1
                    continue
            if direction <= 0:
                if price <= brick_open - brick_size:
                    brick_close = brick_open - brick_size
                    bricks.append({"datetime": ts, "open": brick_open, "high": brick_open, "low": brick_close, "close": brick_close, "direction": -1})
                    brick_open = brick_close
                    direction = -1
                    continue
                elif direction == -1 and price >= brick_open + brick_size:
                    brick_close = brick_open + brick_size
                    bricks.append({"datetime": ts, "open": brick_open, "high": brick_close, "low": brick_open, "close": brick_close, "direction": 1})
                    brick_open = brick_close
                    direction = 1
                    continue
            break

    if not bricks:
        return pd.DataFrame()
    rdf = pd.DataFrame(bricks).set_index("datetime")
    rdf["brick_num"] = range(1, len(rdf) + 1)
    return rdf


def renko_status(rdf: pd.DataFrame) -> dict:
    if rdf.empty or len(rdf) < 3:
        return {"direction": "unknown", "consecutive": 0, "last_reversal": False, "local_high": False, "local_low": False, "bricks_total": 0, "last_close": None, "prev_leg_length": 0}

    directions = rdf["direction"].values
    last_dir = int(directions[-1])
    consecutive = 1
    for d in reversed(directions[:-1]):
        if d == last_dir:
            consecutive += 1
        else:
            break

    prev_leg = 0
    if consecutive < len(directions):
        start = len(directions) - consecutive - 1
        opp = -last_dir
        for i in range(start, -1, -1):
            if directions[i] == opp:
                prev_leg += 1
            else:
                break

    last_reversal = consecutive == 1 and len(directions) >= 2 and int(directions[-2]) != last_dir
    local_high = last_reversal and last_dir == -1 and prev_leg >= 2
    local_low = last_reversal and last_dir == 1 and prev_leg >= 2

    return {
        "direction": "up" if last_dir == 1 else "down",
        "consecutive": consecutive,
        "last_reversal": bool(last_reversal),
        "local_high": bool(local_high),
        "local_low": bool(local_low),
        "bricks_total": len(rdf),
        "last_close": float(rdf["close"].iloc[-1]),
        "prev_leg_length": prev_leg,
    }
