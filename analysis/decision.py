# analysis/decision.py
from __future__ import annotations
import numpy as np
import pandas as pd

STRONG_BULL = {"Bullish Engulfing", "Hammer", "Morning Star"}
STRONG_BEAR = {"Bearish Engulfing", "Shooting Star", "Evening Star"}


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    if df is None or len(df) < period + 1:
        return 0.0
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    val = tr.rolling(period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def _best_candle(candles: list, direction: str):
    pool = STRONG_BULL if direction == "bullish" else STRONG_BEAR
    strong = [c for c in candles if c.get("name") in pool and c.get("direction") == direction]
    if strong:
        return strong[0]
    weak = [c for c in candles if c.get("direction") == direction]
    return weak[0] if weak else None


def _opposing_candle(candles: list, direction: str):
    opp = "bearish" if direction == "bullish" else "bullish"
    pool = STRONG_BEAR if direction == "bullish" else STRONG_BULL
    strong = [c for c in candles if c.get("name") in pool and c.get("direction") == opp]
    return strong[0] if strong else None


def _best_harmonic(harmonics: list, direction: str):
    same = [h for h in harmonics if h.get("direction") == direction]
    if not same:
        return None
    completed = [h for h in same if h.get("status") == "completed"]
    return completed[0] if completed else same[0]


def _opposing_harmonic(harmonics: list, direction: str):
    opp = "bearish" if direction == "bullish" else "bullish"
    return _best_harmonic(harmonics, opp)


def _renko_leg_strength(renko: dict, atr: float) -> float:
    prev = int(renko.get("prev_leg_length") or 0)
    return float(prev) + min(prev * 0.5, 4)


def _levels(direction: str, last_close: float, atr: float, renko: dict, harmonic):
    entry = last_close
    if harmonic:
        if harmonic.get("status") == "forming" and "D_projected" in harmonic:
            d = float(harmonic["D_projected"])
        elif "D" in harmonic:
            d = float(harmonic["D"])
        else:
            d = None
        if d is not None and abs(d - last_close) / max(abs(last_close), 1e-9) < 0.015:
            entry = d
    if renko.get("last_reversal") and renko.get("last_close"):
        entry = float(renko["last_close"])

    atr = atr if atr > 0 else abs(entry) * 0.005
    min_stop_dist = atr * 1.0
    stop_from_x = None
    if harmonic and "X" in harmonic:
        x = float(harmonic["X"])
        stop_from_x = (x - atr * 0.25) if direction == "bullish" else (x + atr * 0.25)

    if direction == "bullish":
        stop_atr = entry - min_stop_dist
        stop = min(stop_atr, stop_from_x) if stop_from_x is not None else stop_atr
        risk = entry - stop
        if risk <= 0:
            stop = entry - min_stop_dist
            risk = min_stop_dist
        target = entry + risk * 1.5
    else:
        stop_atr = entry + min_stop_dist
        stop = max(stop_atr, stop_from_x) if stop_from_x is not None else stop_atr
        risk = stop - entry
        if risk <= 0:
            stop = entry + min_stop_dist
            risk = min_stop_dist
        target = entry - risk * 1.5
    return round(entry, 5), round(stop, 5), round(target, 5)


def _confidence(has_renko, has_harm, has_candle, renko_leg, harmonic, candle, contradiction, daily_align) -> int:
    score = 0
    if has_renko:
        score += 30
        score += int(min(renko_leg, 8) * 2.5)
    if has_harm:
        score += 28 if harmonic and harmonic.get("status") == "completed" else 14
        err = (harmonic or {}).get("error")
        if err is not None:
            score += max(0, 6 - int(float(err) * 15))
    if has_candle:
        if candle and candle.get("name") in (STRONG_BULL | STRONG_BEAR):
            score += 20
            if candle.get("strength") == "strong":
                score += 4
        else:
            score += 6
    pillars = sum([has_renko, has_harm, has_candle])
    if pillars >= 3:
        score += 15
    elif pillars == 2:
        score += 3
    if contradiction:
        score -= 20
    if daily_align == 1:
        score += 8
    elif daily_align == -1:
        score -= 10
    return int(min(max(score, 0), 95))


def _min_conf_for_combo(has_renko, has_harm, has_candle) -> int:
    if has_renko and has_harm and has_candle:
        return 42
    if has_renko and has_candle and not has_harm:
        return 40
    if has_renko and has_harm and not has_candle:
        return 45
    if has_harm and has_candle and not has_renko:
        return 55
    return 99


def make_decision(df_4h, renko: dict, harmonics: list, candles: list, daily_renko=None) -> dict:
    last_close = float(df_4h["close"].iloc[-1]) if df_4h is not None and len(df_4h) else None
    atr = _atr(df_4h) if df_4h is not None else 0.0
    last_bar_time = str(df_4h.index[-1]) if df_4h is not None and len(df_4h) else None

    result = {
        "decision": "BRAK", "confidence": 0, "entry": None, "stop": None, "target": None, "rr": None,
        "reasons": [], "harmonic": None, "candle": None, "renko_signal": "brak", "price": last_close,
        "pillars": 0, "modules": {"renko": False, "harmonic": False, "candle": False},
        "contradiction": False, "daily_align": 0, "last_bar_time": last_bar_time,
        "atr": round(atr, 5) if atr else None,
    }
    if last_close is None:
        result["reasons"] = ["Brak danych 4H"]
        return result

    renko_long = bool(renko.get("local_low") or (renko.get("last_reversal") and renko.get("direction") == "up"))
    renko_short = bool(renko.get("local_high") or (renko.get("last_reversal") and renko.get("direction") == "down"))
    leg = _renko_leg_strength(renko, atr)
    h_bull = _best_harmonic(harmonics, "bullish")
    h_bear = _best_harmonic(harmonics, "bearish")
    c_bull = _best_candle(candles, "bullish")
    c_bear = _best_candle(candles, "bearish")

    daily_align_long = daily_align_short = 0
    if daily_renko and daily_renko.get("direction") in ("up", "down"):
        if daily_renko["direction"] == "up":
            daily_align_long, daily_align_short = 1, -1
        else:
            daily_align_long, daily_align_short = -1, 1

    def eval_side(is_long: bool):
        reasons = []
        direction = "bullish" if is_long else "bearish"
        has_renko = renko_long if is_long else renko_short
        h = h_bull if is_long else h_bear
        c = c_bull if is_long else c_bear
        has_harm = h is not None
        strong_c = c and c.get("name") in (STRONG_BULL | STRONG_BEAR)
        has_candle = bool(strong_c)
        contradiction = False
        opp_c = _opposing_candle(candles, direction)
        opp_h = _opposing_harmonic(harmonics, direction)
        if has_renko and opp_c:
            contradiction = True
            reasons.append(f"UWAGA: sprzeczna swieca {opp_c['name']}")
        if has_renko and opp_h and opp_h.get("status") == "completed":
            contradiction = True
            reasons.append(f"UWAGA: sprzeczna harmoniczna {opp_h['name']}")
        if has_renko:
            leg_i = max(int(renko.get("prev_leg_length") or 1), 1)
            reasons.append(
                f"Renko: lokalny {'dolek / odwrocenie w gore' if is_long else 'szczyt / odwrocenie w dol'} (noga x{leg_i})"
            )
        if has_harm:
            st = "ukonczona" if h.get("status") == "completed" else "formuje sie (PRZ)"
            reasons.append(f"Harmoniczna: {h['name']} {direction} ({st})")
        if has_candle:
            reasons.append(f"Swieca: {c['name']} (potwierdzenie)")
        elif c and c.get("direction") == direction:
            reasons.append(f"Swieca: {c['name']} (slabsza)")
        daily_align = daily_align_long if is_long else daily_align_short
        if daily_align == 1:
            reasons.append("Daily: zgodny kierunek Renko")
        elif daily_align == -1:
            reasons.append("Daily: przeciwny kierunek Renko")
        conf = _confidence(has_renko, has_harm, has_candle, leg, h, c, contradiction, daily_align)
        pillars = sum([has_renko, has_harm, has_candle])
        min_conf = _min_conf_for_combo(has_renko, has_harm, has_candle)
        return {
            "pillars": pillars, "conf": conf, "min_conf": min_conf, "reasons": reasons,
            "h": h, "c": c, "has_renko": has_renko, "has_harm": has_harm, "has_candle": has_candle,
            "contradiction": contradiction, "daily_align": daily_align,
        }

    long_s = eval_side(True)
    short_s = eval_side(False)

    def can_pick(s):
        if s["contradiction"] and s["pillars"] < 3:
            return False
        if s["pillars"] < 2:
            return False
        if s["conf"] < s["min_conf"]:
            return False
        return True

    pick = None
    if can_pick(long_s) and (not can_pick(short_s) or long_s["conf"] >= short_s["conf"] + 8):
        pick = "LONG"
    if can_pick(short_s) and (not can_pick(long_s) or short_s["conf"] >= long_s["conf"] + 8):
        if pick is None or short_s["conf"] > long_s["conf"] + 8:
            pick = "SHORT"
    if pick is None:
        if long_s["pillars"] >= 3 and can_pick(long_s) and long_s["conf"] >= short_s["conf"]:
            pick = "LONG"
        elif short_s["pillars"] >= 3 and can_pick(short_s) and short_s["conf"] >= long_s["conf"]:
            pick = "SHORT"

    if pick in ("LONG", "SHORT"):
        s = long_s if pick == "LONG" else short_s
        direction = "bullish" if pick == "LONG" else "bearish"
        entry, stop, target = _levels(direction, last_close, atr, renko, s["h"])
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = round(reward / risk, 2) if risk > 0 else None
        result.update({
            "decision": pick, "confidence": s["conf"], "entry": entry, "stop": stop,
            "target": target, "rr": rr, "reasons": s["reasons"], "harmonic": s["h"], "candle": s["c"],
            "pillars": s["pillars"],
            "modules": {"renko": s["has_renko"], "harmonic": s["has_harm"], "candle": s["has_candle"]},
            "contradiction": s["contradiction"], "daily_align": s["daily_align"],
            "renko_signal": s["reasons"][0] if s["reasons"] else "renko",
        })
    else:
        best = long_s if long_s["conf"] >= short_s["conf"] else short_s
        side = "LONG" if long_s["conf"] >= short_s["conf"] else "SHORT"
        result["confidence"] = best["conf"]
        result["pillars"] = best["pillars"]
        result["modules"] = {"renko": best["has_renko"], "harmonic": best["has_harm"], "candle": best["has_candle"]}
        result["contradiction"] = best["contradiction"]
        result["daily_align"] = best["daily_align"]
        if best["reasons"]:
            result["reasons"] = [f"Brak setupu ({side} {best['pillars']}/3, conf {best['conf']}%, prog {best['min_conf']}%):"] + best["reasons"]
        else:
            result["reasons"] = ["Brak sygnalow wejscia na 4H"]
    return result
