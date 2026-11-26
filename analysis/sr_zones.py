# analysis/sr_zones.py — osobny moduł stref wsparcia i oporu (S/R)
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from config import (
    SR_GROUP_TOLERANCE_ATR_MULT,
    SR_MAX_ZONES_ABOVE,
    SR_MAX_ZONES_BELOW,
    SR_MULTITF_TOLERANCE_ATR_MULT,
    SWING_CONFIRMATION_BARS,
)


def _atr(df: pd.DataFrame, period: int = 14) -> float | None:
    if df is None or len(df) < period + 1:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    val = tr.rolling(period).mean().iloc[-1]
    return float(val) if not pd.isna(val) else None


def detect_swings(df: pd.DataFrame, timeframe: str, symbol: str = "") -> list[dict]:
    if df is None or df.empty:
        return []
    n = len(df)
    need = 2 * SWING_CONFIRMATION_BARS + 1
    if n < need:
        return []

    highs = df["high"].values
    lows = df["low"].values
    times = df.index
    left = SWING_CONFIRMATION_BARS
    right = SWING_CONFIRMATION_BARS

    swings: list[dict] = []
    for i in range(left, n - right):
        window_high = highs[i - left : i + right + 1]
        window_low = lows[i - left : i + right + 1]
        if highs[i] == max(window_high):
            swings.append({
                "id": f"{symbol}_{timeframe}_HIGH_{i}",
                "price": float(highs[i]),
                "time": str(times[i]),
                "interval": timeframe,
                "symbol": symbol,
                "type": "HIGH",
                "bar_index": i,
                "confirmed": True,
            })
        if lows[i] == min(window_low):
            swings.append({
                "id": f"{symbol}_{timeframe}_LOW_{i}",
                "price": float(lows[i]),
                "time": str(times[i]),
                "interval": timeframe,
                "symbol": symbol,
                "type": "LOW",
                "bar_index": i,
                "confirmed": True,
            })

    swings.sort(key=lambda s: s["time"])
    return swings


def group_swings_into_zones(
    swings: list[dict],
    df: pd.DataFrame | None,
    atr: float | None,
    current_price: float | None = None,
) -> list[dict]:
    if not swings:
        return []

    tolerance = SR_GROUP_TOLERANCE_ATR_MULT * atr if (atr and atr > 0) else None
    last_bar_index = (len(df) - 1) if (df is not None and not df.empty) else 0

    zones: list[dict] = []
    for zone_raw_type in ("HIGH", "LOW"):
        type_swings = [s for s in swings if s["type"] == zone_raw_type]
        if not type_swings:
            continue

        type_swings.sort(key=lambda s: s["price"])

        groups: list[list[dict]] = []
        current_group = [type_swings[0]]
        for s in type_swings[1:]:
            prev_price = current_group[-1]["price"]
            if tolerance is not None and abs(s["price"] - prev_price) <= tolerance:
                current_group.append(s)
            else:
                groups.append(current_group)
                current_group = [s]
        groups.append(current_group)

        zone_type = "RESISTANCE" if zone_raw_type == "HIGH" else "SUPPORT"

        for group in groups:
            prices = [s["price"] for s in group]
            lower = round(min(prices), 5)
            upper = round(max(prices), 5)
            center = round((lower + upper) / 2, 5)
            reaction_count = len(group)

            latest_bar = max(s["bar_index"] for s in group)
            age_bars = max(0, last_bar_index - latest_bar)

            zone = {
                "id": f"{zone_type}_{symbol}_{group[0]['interval']}_{int(center * 10000)}",
                "type": zone_type,
                "lower": lower,
                "upper": upper,
                "center": center,
                "reaction_count": reaction_count,
                "interval": group[0]["interval"],
                "symbol": group[0]["symbol"],
                "age_bars": age_bars,
                "distance_from_price": round(abs(center - current_price), 5) if current_price is not None else None,
                "rank_score": 0.0,
                "rank_position": 0,
                "status": "active",
            }
            zones.append(zone)

    return zones


def rank_zones(
    zones: list[dict],
    current_price: float | None = None,
    atr: float | None = None,
) -> list[dict]:
    for zone in zones:
        score = float(zone["reaction_count"]) * 10.0

        age = zone.get("age_bars", 0)
        score += max(0.0, 10.0 - float(age))

        dist = zone.get("distance_from_price")
        if dist is not None and atr and atr > 0:
            score += max(0.0, 10.0 - (dist / atr) * 5.0)
        elif dist is not None and current_price and current_price > 0:
            score += max(0.0, 10.0 - (dist / current_price) * 1000.0)

        zone["rank_score"] = round(score, 2)

    zones.sort(key=lambda z: (-z["rank_score"], z.get("distance_from_price") or math.inf))
    for i, zone in enumerate(zones):
        zone["rank_position"] = i + 1

    return zones


def filter_top_zones(
    zones: list[dict],
    current_price: float,
    max_above: int = SR_MAX_ZONES_ABOVE,
    max_below: int = SR_MAX_ZONES_BELOW,
) -> list[dict]:
    above = [z for z in zones if z["center"] > current_price]
    below = [z for z in zones if z["center"] < current_price]
    above = above[:max_above]
    below = below[:max_below]
    result = above + below
    result.sort(key=lambda z: z["center"])
    return result


def match_multitf_zones(
    zones_by_tf: dict[str, list[dict]],
    atr_by_tf: dict[str, float],
) -> list[dict]:
    multitf: list[dict] = []
    tfs = list(zones_by_tf.keys())

    for i in range(len(tfs)):
        for j in range(i + 1, len(tfs)):
            tf_a, tf_b = tfs[i], tfs[j]
            atr_tol = SR_MULTITF_TOLERANCE_ATR_MULT * (
                atr_by_tf.get(tf_a) or atr_by_tf.get(tf_b) or 0
            )
            if atr_tol <= 0:
                continue

            for za in zones_by_tf[tf_a]:
                for zb in zones_by_tf[tf_b]:
                    if za["type"] != zb["type"]:
                        continue
                    if (za["lower"] - atr_tol) <= zb["upper"] and (zb["lower"] - atr_tol) <= za["upper"]:
                        merged_lower = min(za["lower"], zb["lower"])
                        merged_upper = max(za["upper"], zb["upper"])
                        multitf.append({
                            "id": f"multitf_{za['id']}_{zb['id']}",
                            "type": za["type"],
                            "lower": round(merged_lower, 5),
                            "upper": round(merged_upper, 5),
                            "center": round((merged_lower + merged_upper) / 2, 5),
                            "interval": "MULTITF",
                            "reaction_count": za["reaction_count"] + zb["reaction_count"],
                            "symbol": za.get("symbol", ""),
                            "source_timeframes": [tf_a, tf_b],
                            "age_bars": max(za.get("age_bars", 0), zb.get("age_bars", 0)),
                            "distance_from_price": None,
                            "rank_score": round(za["rank_score"] + zb["rank_score"], 2),
                            "rank_position": 0,
                            "status": "active",
                        })

    return multitf


def compute_zones_for_symbol(
    data_by_tf: dict[str, dict],
    symbol: str,
) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    atr_by_tf: dict[str, float] = {}

    for tf, data in data_by_tf.items():
        df = data.get("df")
        current_price = data.get("current_price")
        atr_val = data.get("atr") or (_atr(df) if df is not None else None)
        atr_by_tf[tf] = atr_val or 0.0

        swings = detect_swings(df, tf, symbol) if df is not None else []
        zones = group_swings_into_zones(swings, df, atr_val, current_price)
        zones = rank_zones(zones, current_price, atr_val)
        result[tf] = zones

    multitf = match_multitf_zones(result, atr_by_tf)
    if multitf:
        result["MULTITF"] = multitf

    return result


def zones_for_chart(
    zones_by_tf: dict[str, list[dict]],
    timeframe: str,
    current_price: float,
) -> list[dict]:
    zones = zones_by_tf.get(timeframe, [])
    zones = [z for z in zones if z.get("status") == "active"]
    return filter_top_zones(zones, current_price)


def validate_zones(zones: list[dict]) -> list[dict]:
    valid: list[dict] = []
    for z in zones:
        try:
            lower = float(z.get("lower"))
            upper = float(z.get("upper"))
            center = float(z.get("center"))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(lower) and math.isfinite(upper) and math.isfinite(center)):
            continue
        if lower <= 0 or upper <= 0:
            continue
        if upper <= lower:
            continue
        if z.get("type") not in ("SUPPORT", "RESISTANCE"):
            continue
        valid.append(z)
    return valid