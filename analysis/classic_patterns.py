# analysis/classic_patterns.py
"""
ETAP 11L: detekcja klasycznych formacji cenowych (własna, bez ta_patterns).
Obsługa interwałów 1H, 4H, 1D, wyłącznie na zamkniętych świecach.
Zapis do output/classic_patterns.json (schemat v2, kompatybilny wstecz)
oraz output/classic_patterns_state.json (stan trwały między uruchomieniami).
Formacje to informacja analityczna, nie sygnał LONG/SHORT.
"""
from __future__ import annotations
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from config import (
    CLASSIC_PATTERN_TIMEFRAMES,
    CLASSIC_PATTERN_TOLERANCE_ATR_MULT,
    CLASSIC_CHANNEL_TOLERANCE_ATR_MULT,
    CLASSIC_FLAG_IMPULSE_ATR_MULT,
    CLASSIC_FLAG_MIN_CONSOLIDATION_BARS,
    CLASSIC_FLAG_MAX_CONSOLIDATION_BARS,
    CLASSIC_MAX_PATTERNS_PER_TF,
    CLASSIC_HISTORY_BARS,
    CLASSIC_UPDATE_WINDOW_BARS,
    CLASSIC_INVALIDATION_BUFFER_ATR_MULT,
    CLASSIC_STATE_FILE,
    CLASSIC_OUTPUT_FILE,
    CLASSIC_SCHEMA_VERSION,
)

OUTPUT = Path(__file__).resolve().parents[1] / "output"
CLASSIC_PATH = OUTPUT / CLASSIC_OUTPUT_FILE
CLASSIC_STATE_PATH = OUTPUT / CLASSIC_STATE_FILE

STATUS_FORMING = "FORMUJĄCA SIĘ"
STATUS_CONFIRMED = "POTWIERDZONA"
STATUS_BREAKOUT = "WYBITA"
STATUS_RETEST = "RETEST"
STATUS_INVALIDATED = "UNIEWAŻNIONA"
STATUS_EXPIRED = "WYGASŁA"




def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n, dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    atr = np.full(n, np.nan, dtype=float)
    if n < period:
        return atr
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _pivots(high: np.ndarray, low: np.ndarray, confirm: int = 3) -> tuple:
    n = len(high)
    highs = []
    lows = []
    for i in range(confirm, n - confirm):
        is_high = all(high[i] >= high[j] for j in range(i - confirm, i + confirm + 1) if j != i)
        is_low = all(low[i] <= low[j] for j in range(i - confirm, i + confirm + 1) if j != i)
        if is_high:
            highs.append((i, float(high[i])))
        if is_low:
            lows.append((i, float(low[i])))
    return highs, lows


def _pattern_id(symbol: str, timeframe: str, ptype: str, pivots: list) -> str:
    pivot_key = "_".join(f"{b}:{p:.4f}" for b, p in pivots[:5])
    raw = f"{symbol}|{timeframe}|{ptype}|{pivot_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _empty_state() -> dict:
    return {"schema_version": CLASSIC_SCHEMA_VERSION, "symbols": {}}


def _get_symbol_state(state: dict, symbol: str, timeframe: str) -> dict:
    sym = state["symbols"].setdefault(symbol, {})
    return sym.setdefault(timeframe, {"patterns": [], "updated": None})


def _detect_double_top_bottom(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
) -> list:
    """Wykrywa podwójny szczyt (M) i podwójne dno (W). Zwraca listę kandydatów."""
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    # Podwójny szczyt: dwa high na podobnym poziomie, neckline między nimi
    for a in range(len(highs) - 1):
        for b in range(a + 1, len(highs)):
            i1, p1 = highs[a]
            i2, p2 = highs[b]
            if i2 > i_now:
                continue
            if abs(p1 - p2) > tol:
                continue
            # Neckline: minimum między dwoma szczytami
            between = low[i1:i2 + 1]
            neckline = float(np.min(between))
            neckline_idx = int(i1 + int(np.argmin(between)))
            if neckline_idx > i_now:
                continue
            neckline_price = float(close[neckline_idx]) if neckline_idx < len(close) else neckline
            level = (p1 + p2) / 2.0
            results.append({
                "type": "double_top",
                "subtype": "reversal",
                "direction": "bearish",
                "pivots": [(i1, p1), ("neckline", neckline_price), (i2, p2)],
                "trendlines": [
                    {"role": "resistance", "points": [(i1, p1), (i2, p2)], "tolerance_atr": tol_mult},
                    {"role": "neckline", "points": [(neckline_idx, neckline_price), (i_now, neckline_price)], "tolerance_atr": tol_mult},
                ],
                "boundary": {"upper": level, "lower": neckline_price},
                "breakout_level": neckline_price,
                "retest_level": neckline_price,
                "measured_move": level - neckline_price,
            })

    # Podwójne dno: dwa low na podobnym poziomie, neckline między nimi
    for a in range(len(lows) - 1):
        for b in range(a + 1, len(lows)):
            i1, p1 = lows[a]
            i2, p2 = lows[b]
            if i2 > i_now:
                continue
            if abs(p1 - p2) > tol:
                continue
            between = high[i1:i2 + 1]
            neckline = float(np.max(between))
            neckline_idx = int(i1 + int(np.argmax(between)))
            if neckline_idx > i_now:
                continue
            neckline_price = float(close[neckline_idx]) if neckline_idx < len(close) else neckline
            level = (p1 + p2) / 2.0
            results.append({
                "type": "double_bottom",
                "subtype": "reversal",
                "direction": "bullish",
                "pivots": [(i1, p1), ("neckline", neckline_price), (i2, p2)],
                "trendlines": [
                    {"role": "support", "points": [(i1, p1), (i2, p2)], "tolerance_atr": tol_mult},
                    {"role": "neckline", "points": [(neckline_idx, neckline_price), (i_now, neckline_price)], "tolerance_atr": tol_mult},
                ],
                "boundary": {"upper": neckline_price, "lower": level},
                "breakout_level": neckline_price,
                "retest_level": neckline_price,
                "measured_move": neckline_price - level,
            })

    return results


def _detect_triangle(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
) -> list:
    """Wykrywa trójkąty: symetryczny, wzrostowy, spadkowy. Zwraca listę kandydatów."""
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    if len(highs) < 2 or len(lows) < 2:
        return results

    # Druga połowa pivotów — na niej budujemy linie trendu
    h_recent = highs[-3:] if len(highs) >= 3 else highs
    l_recent = lows[-3:] if len(lows) >= 3 else lows

    if len(h_recent) >= 2 and len(l_recent) >= 2:
        (ih1, ph1), (ih2, ph2) = h_recent[-2], h_recent[-1]
        (il1, pl1), (il2, pl2) = l_recent[-2], l_recent[-1]

        if ih2 > i_now or il2 > i_now:
            return results

        # Pochylenie linii górnej i dolnej
        slope_top = (ph2 - ph1) / max(ih2 - ih1, 1)
        slope_bot = (pl2 - pl1) / max(il2 - il1, 1)

        # Zbieżność: linie muszą się zbliżać (punkt przecięcia w przyszłości lub bliżej)
        converging = (slope_top < 0 and slope_bot > 0) or abs(slope_top - slope_bot) < tol * 0.1

        # Symetryczny: obie nachylone, zbieżne
        # Wzrostowy: górna płaska, dolna rosnąca
        # Spadkowy: górna malejąca, dolna płaska
        is_flat_top = abs(slope_top) < tol * 0.3
        is_flat_bot = abs(slope_bot) < tol * 0.3
        is_rising_bot = slope_bot > tol * 0.2
        is_falling_top = slope_top < -tol * 0.2

        subtype = None
        if converging and not is_flat_top and not is_flat_bot:
            subtype = "symmetrical"
        elif is_flat_top and is_rising_bot:
            subtype = "ascending"
        elif is_falling_top and is_flat_bot:
            subtype = "descending"

        if subtype:
            # Punkt przecięcia linii (projeksja w przyszłość)
            if abs(slope_top - slope_bot) > 1e-9:
                x_intersect = (pl1 - ph1 + slope_top * ih1 - slope_bot * il1) / (slope_top - slope_bot)
                y_intersect = ph1 + slope_top * (x_intersect - ih1)
            else:
                x_intersect = float(i_now)
                y_intersect = (ph2 + pl2) / 2.0

            results.append({
                "type": "triangle",
                "subtype": subtype,
                "direction": "neutral",
                "pivots": [(ih1, ph1), (ih2, ph2), (il1, pl1), (il2, pl2)],
                "trendlines": [
                    {"role": "resistance", "points": [(ih1, ph1), (ih2, ph2)], "tolerance_atr": tol_mult},
                    {"role": "support", "points": [(il1, pl1), (il2, pl2)], "tolerance_atr": tol_mult},
                ],
                "boundary": {
                    "upper": ph2 + slope_top * (i_now - ih2),
                    "lower": pl2 + slope_bot * (i_now - il2),
                },
                "breakout_level": max(ph2, pl2),
                "retest_level": max(ph2, pl2),
                "measured_move": abs(ph2 - pl2),
                "apex": (float(x_intersect), float(y_intersect)),
            })

    return results


def _detect_wedge(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
) -> list:
    """Wykrywa kliny: wzrostowy (oba nachylone w górę, zbieżne) i spadkowy (oba nachylone w dół, zbieżne)."""
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    if len(highs) < 2 or len(lows) < 2:
        return results

    h_recent = highs[-3:] if len(highs) >= 3 else highs
    l_recent = lows[-3:] if len(lows) >= 3 else lows

    if len(h_recent) >= 2 and len(l_recent) >= 2:
        (ih1, ph1), (ih2, ph2) = h_recent[-2], h_recent[-1]
        (il1, pl1), (il2, pl2) = l_recent[-2], l_recent[-1]

        if ih2 > i_now or il2 > i_now:
            return results

        slope_top = (ph2 - ph1) / max(ih2 - ih1, 1)
        slope_bot = (pl2 - pl1) / max(il2 - il1, 1)

        same_direction = (slope_top > 0 and slope_bot > 0) or (slope_top < 0 and slope_bot < 0)
        converging = (slope_top > 0 and slope_bot > 0 and slope_top < slope_bot) or \
                     (slope_top < 0 and slope_bot < 0 and slope_top > slope_bot)

        subtype = None
        if same_direction and converging and slope_top > 0:
            subtype = "rising"
        elif same_direction and converging and slope_top < 0:
            subtype = "falling"

        if subtype:
            if abs(slope_top - slope_bot) > 1e-9:
                x_intersect = (pl1 - ph1 + slope_top * ih1 - slope_bot * il1) / (slope_top - slope_bot)
                y_intersect = ph1 + slope_top * (x_intersect - ih1)
            else:
                x_intersect = float(i_now)
                y_intersect = (ph2 + pl2) / 2.0

            results.append({
                "type": "wedge",
                "subtype": subtype,
                "direction": "bearish" if subtype == "rising" else "bullish",
                "pivots": [(ih1, ph1), (ih2, ph2), (il1, pl1), (il2, pl2)],
                "trendlines": [
                    {"role": "resistance", "points": [(ih1, ph1), (ih2, ph2)], "tolerance_atr": tol_mult},
                    {"role": "support", "points": [(il1, pl1), (il2, pl2)], "tolerance_atr": tol_mult},
                ],
                "boundary": {
                    "upper": ph2 + slope_top * (i_now - ih2),
                    "lower": pl2 + slope_bot * (i_now - il2),
                },
                "breakout_level": pl2 if subtype == "rising" else ph2,
                "retest_level": pl2 if subtype == "rising" else ph2,
                "measured_move": abs(ph2 - pl2),
                "apex": (float(x_intersect), float(y_intersect)),
            })

    return results


def _detect_flag_pennant(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
    impulse_mult: float,
    min_cons: int,
    max_cons: int,
) -> list:
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    if i_now < min_cons + 10:
        return results

    cons_start = max(0, i_now - max_cons)
    cons_end = max(0, i_now - min_cons)
    if cons_end <= cons_start:
        return results

    impulse_start = max(0, cons_start - 10)
    impulse_end = cons_start
    if impulse_end <= impulse_start:
        return results

    impulse_move = float(close[impulse_end - 1] - close[impulse_start])
    if abs(impulse_move) < impulse_mult * tol:
        return results

    impulse_dir = 1 if impulse_move > 0 else -1

    cons_high = float(np.max(high[cons_start:cons_end]))
    cons_low = float(np.min(low[cons_start:cons_end]))
    cons_range = cons_high - cons_low

    if cons_range > 3 * tol:
        return results

    cons_slope = (close[cons_end - 1] - close[cons_start]) / max(cons_end - cons_start, 1)
    if impulse_dir * cons_slope > 0:
        return results

    subtype = "flag" if cons_range > 1.5 * tol else "pennant"
    breakout = cons_high if impulse_dir > 0 else cons_low

    results.append({
        "type": "flag",
        "subtype": subtype,
        "direction": "bullish" if impulse_dir > 0 else "bearish",
        "pivots": [(cons_start, cons_high), (cons_end - 1, cons_low)],
        "trendlines": [
            {"role": "resistance", "points": [(cons_start, cons_high), (cons_end - 1, cons_high)], "tolerance_atr": tol_mult},
            {"role": "support", "points": [(cons_start, cons_low), (cons_end - 1, cons_low)], "tolerance_atr": tol_mult},
        ],
        "boundary": {"upper": cons_high, "lower": cons_low},
        "breakout_level": breakout,
        "retest_level": breakout,
        "measured_move": abs(impulse_move),
    })

    return results


def _detect_head_and_shoulders(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
) -> list:
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    if len(highs) < 3 or len(lows) < 2:
        return results

    h_recent = highs[-3:] if len(highs) >= 3 else highs
    if len(h_recent) == 3:
        (i1, p1), (i2, p2), (i3, p3) = h_recent
        if i3 > i_now:
            return results
        head_higher = p2 > p1 and p2 > p3
        shoulders_similar = abs(p1 - p3) <= tol
        if head_higher and shoulders_similar:
            neckline_idx = int(i1 + int(np.argmin(low[i1:i3 + 1])))
            neckline_price = float(close[neckline_idx]) if neckline_idx < len(close) else float(low[neckline_idx])
            results.append({
                "type": "head_and_shoulders",
                "subtype": "reversal",
                "direction": "bearish",
                "pivots": [(i1, p1), (i2, p2), (i3, p3)],
                "trendlines": [
                    {"role": "resistance", "points": [(i1, p1), (i3, p3)], "tolerance_atr": tol_mult},
                    {"role": "neckline", "points": [(neckline_idx, neckline_price), (i_now, neckline_price)], "tolerance_atr": tol_mult},
                ],
                "boundary": {"upper": p2, "lower": neckline_price},
                "breakout_level": neckline_price,
                "retest_level": neckline_price,
                "measured_move": p2 - neckline_price,
            })

    l_recent = lows[-3:] if len(lows) >= 3 else lows
    if len(l_recent) == 3:
        (i1, p1), (i2, p2), (i3, p3) = l_recent
        if i3 > i_now:
            return results
        head_lower = p2 < p1 and p2 < p3
        shoulders_similar = abs(p1 - p3) <= tol
        if head_lower and shoulders_similar:
            neckline_idx = int(i1 + int(np.argmax(high[i1:i3 + 1])))
            neckline_price = float(close[neckline_idx]) if neckline_idx < len(close) else float(high[neckline_idx])
            results.append({
                "type": "inverse_head_and_shoulders",
                "subtype": "reversal",
                "direction": "bullish",
                "pivots": [(i1, p1), (i2, p2), (i3, p3)],
                "trendlines": [
                    {"role": "support", "points": [(i1, p1), (i3, p3)], "tolerance_atr": tol_mult},
                    {"role": "neckline", "points": [(neckline_idx, neckline_price), (i_now, neckline_price)], "tolerance_atr": tol_mult},
                ],
                "boundary": {"upper": neckline_price, "lower": p2},
                "breakout_level": neckline_price,
                "retest_level": neckline_price,
                "measured_move": neckline_price - p2,
            })

    return results


def _detect_channel(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    highs: list,
    lows: list,
    i_now: int,
    tol_mult: float,
    channel_tol_mult: float,
) -> list:
    results = []
    tol = atr[i_now] if not np.isnan(atr[i_now]) else 0.0

    if len(highs) < 2 or len(lows) < 2:
        return results

    h_recent = highs[-3:] if len(highs) >= 3 else highs
    l_recent = lows[-3:] if len(lows) >= 3 else lows

    if len(h_recent) >= 2 and len(l_recent) >= 2:
        (ih1, ph1), (ih2, ph2) = h_recent[-2], h_recent[-1]
        (il1, pl1), (il2, pl2) = l_recent[-2], l_recent[-1]

        if ih2 > i_now or il2 > i_now:
            return results

        slope_top = (ph2 - ph1) / max(ih2 - ih1, 1)
        slope_bot = (pl2 - pl1) / max(il2 - il1, 1)

        parallel = abs(slope_top - slope_bot) < channel_tol_mult * tol
        if not parallel:
            return results

        upper_now = ph2 + slope_top * (i_now - ih2)
        lower_now = pl2 + slope_bot * (i_now - il2)

        in_channel = True
        for (idx, px) in highs[-3:]:
            if px > upper_now + tol:
                in_channel = False
                break
        for (idx, px) in lows[-3:]:
            if px < lower_now - tol:
                in_channel = False
                break

        if not in_channel:
            return results

        slope_avg = (slope_top + slope_bot) / 2.0
        if abs(slope_avg) < channel_tol_mult * tol * 0.5:
            subtype = "flat"
            direction = "neutral"
        elif slope_avg > 0:
            subtype = "ascending"
            direction = "bullish"
        else:
            subtype = "descending"
            direction = "bearish"

        results.append({
            "type": "channel",
            "subtype": subtype,
            "direction": direction,
            "pivots": [(ih1, ph1), (ih2, ph2), (il1, pl1), (il2, pl2)],
            "trendlines": [
                {"role": "resistance", "points": [(ih1, ph1), (ih2, ph2)], "tolerance_atr": channel_tol_mult},
                {"role": "support", "points": [(il1, pl1), (il2, pl2)], "tolerance_atr": channel_tol_mult},
            ],
            "boundary": {"upper": upper_now, "lower": lower_now},
            "breakout_level": upper_now if direction == "bullish" else lower_now,
            "retest_level": upper_now if direction == "bullish" else lower_now,
            "measured_move": upper_now - lower_now,
        })

    return results


def _candidate_to_pattern(
    symbol: str,
    timeframe: str,
    candidate: dict,
    i_now: int,
    times: list,
    status: str,
    now_iso: str,
    existing: dict | None = None,
) -> dict:
    pid = candidate.get("id") or _pattern_id(symbol, timeframe, candidate["type"], candidate["pivots"])
    pivots_out = []
    for pv in candidate["pivots"]:
        label, price = pv
        t = times[int(label)] if isinstance(label, int) and int(label) < len(times) else None
        pivots_out.append({"role": str(label), "time": t, "price": float(price), "bar": int(label) if isinstance(label, int) else None})
    tl_out = []
    for tl in candidate.get("trendlines", []):
        pts = []
        for (b, pr) in tl["points"]:
            t = times[int(b)] if isinstance(b, int) and int(b) < len(times) else None
            pts.append({"time": t, "value": float(pr), "bar": int(b) if isinstance(b, int) else None})
        tl_out.append({"role": tl["role"], "points": pts, "tolerance_atr": tl.get("tolerance_atr", CLASSIC_PATTERN_TOLERANCE_ATR_MULT)})
    boundary = candidate.get("boundary", {})
    apex = candidate.get("apex")
    pat = {
        "id": pid,
        "symbol": symbol,
        "timeframe": timeframe,
        "type": candidate["type"],
        "subtype": candidate.get("subtype"),
        "direction": candidate.get("direction", "neutral"),
        "status": status,
        "created_at": existing.get("created_at", now_iso) if existing else now_iso,
        "confirmed_at": existing.get("confirmed_at") if existing else None,
        "breakout_at": existing.get("breakout_at") if existing else None,
        "retest_at": existing.get("retest_at") if existing else None,
        "invalidated_at": existing.get("invalidated_at") if existing else None,
        "expired_at": existing.get("expired_at") if existing else None,
        "pivots": pivots_out,
        "trendlines": tl_out,
        "boundary": boundary,
        "breakout_level": candidate.get("breakout_level"),
        "retest_level": candidate.get("retest_level"),
        "measured_move": candidate.get("measured_move"),
        "atr_at_confirmation": None,
        "bars_since_last_update": 0,
        "report_count": (existing.get("report_count", 0) + 1) if existing else 1,
    }
    if apex is not None:
        pat["apex"] = {"time": None, "value": apex[1], "bar": int(apex[0]) if isinstance(apex[0], (int, float)) else None}
    if status == STATUS_CONFIRMED and not existing:
        pat["confirmed_at"] = now_iso
    if status == STATUS_BREAKOUT:
        pat["breakout_at"] = now_iso
    if status == STATUS_RETEST:
        pat["retest_at"] = now_iso
    if status == STATUS_INVALIDATED:
        pat["invalidated_at"] = now_iso
    if status == STATUS_EXPIRED:
        pat["expired_at"] = now_iso
    return pat


def detect_for_symbol_tf(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
) -> list:
    """
    Główna funkcja detekcji dla jednego symbolu i interwału.
    Działa wyłącznie na zamkniętych świecach (df zawiera tylko zamknięte).
    Zwraca listę kandydatów formacji (bez statusu - nadawany przez update_patterns_for_symbol_tf).
    """
    if df is None or len(df) < 20:
        return []

    required = {"open", "high", "low", "close"}
    if not required.issubset(set(df.columns)):
        return []

    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    times = [str(ts) for ts in df.index]

    atr = _atr(h, l, c)
    highs, lows = _pivots(h, l, confirm=3)
    i_now = len(c) - 1

    tol_mult = CLASSIC_PATTERN_TOLERANCE_ATR_MULT
    ctol_mult = CLASSIC_CHANNEL_TOLERANCE_ATR_MULT

    candidates = []
    candidates.extend(_detect_double_top_bottom(h, l, c, atr, highs, lows, i_now, tol_mult))
    candidates.extend(_detect_triangle(h, l, c, atr, highs, lows, i_now, tol_mult))
    candidates.extend(_detect_wedge(h, l, c, atr, highs, lows, i_now, tol_mult))
    candidates.extend(
        _detect_flag_pennant(h, l, c, atr, highs, lows, i_now, tol_mult,
                             CLASSIC_FLAG_IMPULSE_ATR_MULT,
                             CLASSIC_FLAG_MIN_CONSOLIDATION_BARS,
                             CLASSIC_FLAG_MAX_CONSOLIDATION_BARS)
    )
    candidates.extend(_detect_head_and_shoulders(h, l, c, atr, highs, lows, i_now, tol_mult))
    candidates.extend(_detect_channel(h, l, c, atr, highs, lows, i_now, tol_mult, ctol_mult))

    # Dodaj metadane wspólne
    for cand in candidates:
        cand["symbol"] = symbol
        cand["timeframe"] = timeframe
        cand["bar_index"] = i_now
        cand["detected_at"] = _utc_now_iso()

    return candidates


STATUS_ORDER = {
    STATUS_FORMING: 0,
    STATUS_CONFIRMED: 1,
    STATUS_BREAKOUT: 2,
    STATUS_RETEST: 3,
    STATUS_INVALIDATED: 4,
    STATUS_EXPIRED: 5,
}


def _status_can_transition(from_status: str, to_status: str) -> bool:
    return STATUS_ORDER.get(to_status, 0) >= STATUS_ORDER.get(from_status, 0)


def _check_breakout(
    close_price: float,
    high_price: float,
    low_price: float,
    pattern: dict,
    direction: str,
    atr_val: float,
) -> tuple:
    boundary = pattern.get("boundary", {})
    upper = boundary.get("upper")
    lower = boundary.get("lower")
    buf = CLASSIC_INVALIDATION_BUFFER_ATR_MULT * atr_val if atr_val else 0.0

    if direction == "bullish" and upper is not None:
        if close_price > upper + buf:
            return True, upper
    elif direction == "bearish" and lower is not None:
        if close_price < lower - buf:
            return True, lower
    elif direction == "neutral":
        if upper is not None and close_price > upper + buf:
            return True, upper
        if lower is not None and close_price < lower - buf:
            return True, lower

    return False, None


def _check_retest(
    close_price: float,
    breakout_level: float,
    atr_val: float,
) -> bool:
    buf = CLASSIC_INVALIDATION_BUFFER_ATR_MULT * atr_val if atr_val else 0.0
    return abs(close_price - breakout_level) <= buf


def update_patterns_for_symbol_tf(
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    candidates: list,
    state: dict,
) -> tuple:
    sym_state = _get_symbol_state(state, symbol, timeframe)
    existing_patterns = sym_state.get("patterns", [])
    now_iso = _utc_now_iso()
    i_now = len(df) - 1 if df is not None and len(df) > 0 else 0

    close_price = float(df["close"].iloc[i_now]) if df is not None and len(df) > 0 else 0.0
    high_price = float(df["high"].iloc[i_now]) if df is not None and len(df) > 0 else 0.0
    low_price = float(df["low"].iloc[i_now]) if df is not None and len(df) > 0 else 0.0

    atr_arr = _atr(df["high"].to_numpy(dtype=float), df["low"].to_numpy(dtype=float), df["close"].to_numpy(dtype=float)) if df is not None and len(df) > 0 else np.array([0.0])
    atr_val = float(atr_arr[-1]) if len(atr_arr) > 0 and not np.isnan(atr_arr[-1]) else 0.0

    times = [str(ts) for ts in df.index] if df is not None else []

    existing_by_id = {p["id"]: p for p in existing_patterns}
    updated_patterns = []

    for pid, p in existing_by_id.items():
        new_status = p["status"]
        p = dict(p)
        p["bars_since_last_update"] = p.get("bars_since_last_update", 0) + 1

        if p["status"] in (STATUS_INVALIDATED, STATUS_EXPIRED):
            updated_patterns.append(p)
            continue

        if p["status"] in (STATUS_FORMING, STATUS_CONFIRMED):
            is_bo, bo_level = _check_breakout(close_price, high_price, low_price, p, p.get("direction", "neutral"), atr_val)
            if is_bo:
                new_status = STATUS_BREAKOUT
                p["breakout_at"] = now_iso
                p["breakout_level"] = bo_level

        if p["status"] == STATUS_BREAKOUT:
            bl = p.get("breakout_level")
            if bl is not None and _check_retest(close_price, bl, atr_val):
                new_status = STATUS_RETEST
                p["retest_at"] = now_iso

        if p["status"] in (STATUS_CONFIRMED, STATUS_BREAKOUT, STATUS_RETEST):
            boundary = p.get("boundary", {})
            upper = boundary.get("upper")
            lower = boundary.get("lower")
            buf = CLASSIC_INVALIDATION_BUFFER_ATR_MULT * atr_val if atr_val else 0.0
            invalidated = False
            if p.get("direction") == "bullish" and lower is not None and close_price < lower - buf * 2:
                invalidated = True
            elif p.get("direction") == "bearish" and upper is not None and close_price > upper + buf * 2:
                invalidated = True
            elif p.get("direction") == "neutral":
                if upper is not None and close_price > upper + buf * 2:
                    invalidated = True
                if lower is not None and close_price < lower - buf * 2:
                    invalidated = True
            if invalidated:
                new_status = STATUS_INVALIDATED
                p["invalidated_at"] = now_iso

        if p.get("bars_since_last_update", 0) > 100 and p["status"] == STATUS_FORMING:
            new_status = STATUS_EXPIRED
            p["expired_at"] = now_iso

        if not _status_can_transition(p["status"], new_status):
            new_status = p["status"]

        p["status"] = new_status
        updated_patterns.append(p)

    for cand in candidates:
        pid = _pattern_id(symbol, timeframe, cand["type"], cand.get("pivots", []))
        if pid in existing_by_id:
            continue
        pat = _candidate_to_pattern(symbol, timeframe, cand, i_now, times, STATUS_FORMING, now_iso)
        updated_patterns.append(pat)

    active_order = {STATUS_FORMING: 0, STATUS_CONFIRMED: 1, STATUS_BREAKOUT: 2, STATUS_RETEST: 3}
    updated_patterns.sort(key=lambda p: (active_order.get(p["status"], 99), -(p.get("created_at") or "")))

    active = [p for p in updated_patterns if p["status"] in (STATUS_FORMING, STATUS_CONFIRMED, STATUS_BREAKOUT, STATUS_RETEST)]
    inactive = [p for p in updated_patterns if p["status"] in (STATUS_INVALIDATED, STATUS_EXPIRED)]
    if len(active) > CLASSIC_MAX_PATTERNS_PER_TF:
        active = active[:CLASSIC_MAX_PATTERNS_PER_TF]
    updated_patterns = active + inactive

    sym_state["patterns"] = updated_patterns
    sym_state["updated"] = now_iso


    presentation = {
        "schema_version": CLASSIC_SCHEMA_VERSION,
        "timeframe": timeframe,
        "updated": now_iso,
        "symbols": {
            symbol: [
                {
                    "name": p["type"],
                    "direction": p["direction"],
                    "bar": p["pivots"][-1]["bar"] if p["pivots"] else i_now,
                    "time": p["pivots"][-1]["time"] if p["pivots"] else (times[-1] if times else ""),
                    "price": p["pivots"][-1]["price"] if p["pivots"] else close_price,
                    "status": p["status"],
                    "subtype": p.get("subtype"),
                    "id": p["id"],
                    "breakout_level": p.get("breakout_level"),
                    "retest_level": p.get("retest_level"),
                    "measured_move": p.get("measured_move"),
                    "trendlines": p.get("trendlines", []),
                    "boundary": p.get("boundary", {}),
                    "pivots": p.get("pivots", []),
                    "created_at": p.get("created_at"),
                    "confirmed_at": p.get("confirmed_at"),
                    "breakout_at": p.get("breakout_at"),
                    "retest_at": p.get("retest_at"),
                    "invalidated_at": p.get("invalidated_at"),
                    "expired_at": p.get("expired_at"),
                }
                for p in updated_patterns
            ]
        },
    }

    return updated_patterns, presentation, state


def save_state(state: dict) -> None:
    _atomic_write(CLASSIC_STATE_PATH, state)


def load_state() -> dict:
    return _load_json(CLASSIC_STATE_PATH, _empty_state())


def save_presentation(all_presentations: dict) -> None:
    """
    Zapisuje output/classic_patterns.json w formacie kompatybilnym ze starym.
    Łączy z istniejącymi danymi (wielokrotne wywołania per symbol nie nadpisują siebie nawzajem).
    all_presentations: dict timeframe -> presentation payload
    """
    existing = _load_json(CLASSIC_PATH, {
        "schema_version": CLASSIC_SCHEMA_VERSION,
        "timeframe": "4H",
        "updated": _utc_now_iso(),
        "timeframes": {},
        "symbols": {},
    })
    existing["updated"] = _utc_now_iso()
    existing["schema_version"] = CLASSIC_SCHEMA_VERSION
    for tf, pres in all_presentations.items():
        existing["timeframes"][tf] = pres
        for sym, pats in (pres.get("symbols") or {}).items():
            existing["symbols"].setdefault(sym, []).extend(pats)

    _atomic_write(CLASSIC_PATH, existing)


def run_detection_all(
    data_by_symbol_tf: dict,
    state: dict | None = None,
) -> tuple:
    """
    Główna funkcja wywoływana przez analyzer.py.
    data_by_symbol_tf: {(symbol, timeframe): df} — dane OHLC dla każdego symbolu i interwału.
    Zwraca (state, all_presentations).
    """
    if state is None:
        state = load_state()

    all_presentations = {}

    for (symbol, timeframe), df in data_by_symbol_tf.items():
        if timeframe not in CLASSIC_PATTERN_TIMEFRAMES:
            continue
        candidates = detect_for_symbol_tf(df, symbol, timeframe)
        _, presentation, state = update_patterns_for_symbol_tf(symbol, timeframe, df, candidates, state)
        all_presentations[timeframe] = presentation

    save_state(state)
    save_presentation(all_presentations)

    return state, all_presentations