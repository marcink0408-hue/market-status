from __future__ import annotations

from typing import Any

import pandas as pd


TF_SECONDS = {"1H": 3600, "4H": 4 * 3600, "1D": 24 * 3600}


def _timestamp(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            return None
        return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    except (TypeError, ValueError, OverflowError):
        return None


def _iso(value: pd.Timestamp | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value is not None else None


def _bar_index(df: pd.DataFrame, value: Any) -> int | None:
    stamp = _timestamp(value)
    if stamp is None or df is None or df.empty:
        return None
    matches = df.index.get_indexer([stamp])
    return int(matches[0]) if len(matches) and matches[0] >= 0 else None


def _pattern_expiry(pattern: dict, df: pd.DataFrame, d_index: int, timeframe: str) -> pd.Timestamp | None:
    """Wejście traci ważność po czasie odpowiadającym ostatniej nodze C-D."""
    seconds = TF_SECONDS.get(timeframe, TF_SECONDS["4H"])
    c_index = _bar_index(df, pattern.get("time_C"))
    leg_bars = max(d_index - c_index, 1) if c_index is not None else 1
    return _timestamp(df.index[d_index]) + pd.Timedelta(seconds=seconds * leg_bars)


def evaluate_harmonic(pattern: dict, df: pd.DataFrame, timeframe: str) -> dict:
    """Rozróżnia PRZ od formacji potwierdzonej, zrealizowanej i zanegowanej."""
    item = dict(pattern)
    item.update({
        "completed_at": None, "entry_reached_at": None, "valid_until": None,
        "closed_at": None, "close_reason": None, "active": False,
    })
    if item.get("status") == "forming":
        item["lifecycle"] = "forming"
        c_index = _bar_index(df, item.get("time_C"))
        b_index = _bar_index(df, item.get("time_B"))
        leg_bars = max(c_index - b_index, 1) if c_index is not None and b_index is not None else 1
        expiry_base = _timestamp(item.get("time_C"))
        item["valid_until"] = _iso(expiry_base + pd.Timedelta(
            seconds=TF_SECONDS.get(timeframe, TF_SECONDS["4H"]) * leg_bars
        )) if expiry_base is not None else None
        if item["valid_until"] and _timestamp(df.index[-1]) > _timestamp(item["valid_until"]):
            item["lifecycle"] = "expired"
            item["close_reason"] = "projected_structure_window_elapsed"
            item["closed_at"] = item["valid_until"]
        return item

    d_index = _bar_index(df, item.get("time_D"))
    if d_index is None:
        item["lifecycle"] = "historical"
        item["close_reason"] = "missing_pattern_bar"
        return item

    d_time = _timestamp(df.index[d_index])
    confirmation_index = d_index + 2  # find_pivots(right=2)
    if confirmation_index >= len(df):
        item["lifecycle"] = "forming"
        return item

    item["completed_at"] = _iso(_timestamp(df.index[confirmation_index]))
    item["entry_reached_at"] = _iso(d_time)
    expiry = _pattern_expiry(item, df, d_index, timeframe)
    item["valid_until"] = _iso(expiry)
    direction = item.get("direction")
    try:
        d_price = float(item["D"])
        a_price = float(item["A"])
    except (KeyError, TypeError, ValueError):
        item["lifecycle"] = "historical"
        item["close_reason"] = "missing_pattern_prices"
        return item

    # Pierwszy standardowy cel harmoniczny: 38,2% zniesienia A-D.
    item["pattern_target"] = d_price + (a_price - d_price) * 0.382
    item["invalidation_level"] = d_price
    lifecycle = "active"
    for stamp, bar in df.iloc[d_index + 1:].iterrows():
        if direction == "bullish":
            invalidated = float(bar["low"]) < d_price
            target_reached = float(bar["high"]) >= item["pattern_target"]
        else:
            invalidated = float(bar["high"]) > d_price
            target_reached = float(bar["low"]) <= item["pattern_target"]
        # Przy zdarzeniach na tej samej świecy stosujemy konserwatywną negację.
        if invalidated:
            lifecycle = "invalidated"
            item["close_reason"] = "price_beyond_D"
        elif target_reached:
            lifecycle = "target_reached"
            item["close_reason"] = "pattern_target_reached"
        if lifecycle != "active":
            item["closed_at"] = _iso(_timestamp(stamp))
            break

    last_time = _timestamp(df.index[-1])
    if lifecycle == "active" and expiry is not None and last_time > expiry:
        lifecycle = "expired"
        item["close_reason"] = "structure_window_elapsed"
        item["closed_at"] = _iso(expiry)
    item["lifecycle"] = lifecycle
    item["active"] = lifecycle == "active"
    return item


def harmonic_is_visible(pattern: dict, df: pd.DataFrame) -> bool:
    """Historia zostaje w JSON; wykres pokazuje PRZ i krótki bufor po zamknięciu."""
    lifecycle = pattern.get("lifecycle")
    if lifecycle in {"forming", "active"}:
        return True
    closed_at = _timestamp(pattern.get("closed_at") or pattern.get("time_D") or pattern.get("time_C"))
    last_time = _timestamp(df.index[-1]) if df is not None and not df.empty else None
    return bool(closed_at is not None and last_time is not None and pd.Timedelta(0) <= last_time - closed_at <= pd.Timedelta(days=5))



def evaluate_signal(decision: dict, df: pd.DataFrame, timeframe: str) -> dict:
    """Wyznacza stan transakcji z pełnej precyzji OHLC, bez zaokrąglania poziomów."""
    result = dict(decision)
    result.update({
        "signal_status": "NONE", "can_enter": False, "signal_origin": None,
        "signal_valid_until": None, "activated_at": None, "closed_at": None,
        "signal_close_reason": None,
    })
    if result.get("decision") not in {"LONG", "SHORT"}:
        return result
    try:
        entry = float(result["entry"])
        stop = float(result["stop"])
        target = float(result["target"])
    except (KeyError, TypeError, ValueError):
        result["signal_status"] = "NO_DATA"
        result["signal_close_reason"] = "incomplete_levels"
        return result
    if df is None or df.empty:
        result["signal_status"] = "NO_DATA"
        result["signal_close_reason"] = "missing_ohlc"
        return result

    harmonic = result.get("harmonic") or {}
    origin_value = harmonic.get("time_D") or result.get("last_bar_time")
    origin_index = _bar_index(df, origin_value)
    if origin_index is None:
        result["signal_status"] = "NO_DATA"
        result["signal_close_reason"] = "missing_signal_origin"
        return result

    origin_time = _timestamp(df.index[origin_index])
    if harmonic:
        expiry = _timestamp(harmonic.get("valid_until")) or _pattern_expiry(harmonic, df, origin_index, timeframe)
    else:
        # Sygnał świecowy/Renko obowiązuje do zamknięcia następnej świecy.
        expiry = origin_time + pd.Timedelta(seconds=TF_SECONDS.get(timeframe, TF_SECONDS["4H"]))
    result["signal_origin"] = _iso(origin_time)
    result["signal_valid_until"] = _iso(expiry)

    long = result["decision"] == "LONG"
    entry_touched = False
    for position, (stamp, bar) in enumerate(df.iloc[origin_index:].iterrows()):
        high, low = float(bar["high"]), float(bar["low"])
        if not entry_touched:
            entry_touched = low <= entry <= high
            if entry_touched:
                result["activated_at"] = _iso(_timestamp(stamp))
            continue
        # Poziomów osiągniętych przed zamknięciem świecy wejścia nie przesuwamy wstecz.
        if position == 0:
            continue
        stop_hit = low <= stop if long else high >= stop
        target_hit = high >= target if long else low <= target
        if stop_hit or target_hit:
            result["signal_status"] = "STOP_LOSS" if stop_hit else "TAKE_PROFIT"
            result["signal_close_reason"] = "stop_reached" if stop_hit else "target_reached"
            result["closed_at"] = _iso(_timestamp(stamp))
            return result

    last_time = _timestamp(df.index[-1])
    if not entry_touched:
        if expiry is not None and last_time > expiry:
            result["signal_status"] = "EXPIRED"
            result["signal_close_reason"] = "entry_window_elapsed"
            result["closed_at"] = _iso(expiry)
        else:
            result["signal_status"] = "PENDING"
            result["can_enter"] = True
    else:
        result["signal_status"] = "ACTIVE"
    return result
