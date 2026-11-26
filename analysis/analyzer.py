# analysis/analyzer.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from data.fetcher import fetch_all
from analysis.renko import build_renko, renko_status
from analysis.harmonics import detect_harmonics
from analysis.candles import detect_candlestick_patterns, analyze_candle
from analysis.classic_patterns import detect_classic_patterns
from analysis.decision import make_decision
from analysis.lifecycle import evaluate_harmonic, evaluate_signal, harmonic_is_visible
from analysis.sr_zones import compute_zones_for_symbol, zones_for_chart, validate_zones
from analysis.readiness import calculate_readiness
from analysis.setup_lifecycle import manage_lifecycle
from analysis.chart_data import build_chart_payload
from config import SYMBOLS, MAX_DATA_AGE, INVALIDATION_BUFFER_ATR_MULT
import json
from datetime import datetime, timezone


def analyze_tf(df, tf: str, symbol: str = "") -> dict:
    try:
        canonical_tf = "1D" if tf == "Daily" else tf
        rdf = build_renko(df)
        rstat = renko_status(rdf)
        harms = []
        for pattern in detect_harmonics(df):
            item = evaluate_harmonic(dict(pattern, symbol=symbol, timeframe=canonical_tf), df, canonical_tf)
            item["created_at"] = item.get("time_D") or item.get("time_C")
            harms.append(item)
        cands = [dict(p, symbol=symbol, timeframe=canonical_tf) for p in detect_candlestick_patterns(df)]
        classic = detect_classic_patterns(df) if tf == "4H" else []
        recent = df.tail(20)
        return {
            "symbol": symbol, "timeframe": canonical_tf,
            "renko": rstat,
            "harmonics": harms,
            "candles": cands,
            "classic_patterns": classic,
            "market_levels": {
                "recent_high": float(recent["high"].max()),
                "recent_low": float(recent["low"].min()),
                "period_bars": len(recent), "timeframe": canonical_tf,
            },
            "bars": len(df),
            "last_close": float(df["close"].iloc[-1]),
            "last_time": str(df.index[-1]),
        }
    except Exception as e:
        return {"symbol": symbol, "timeframe": "1D" if tf == "Daily" else tf, "error": str(e)}


def _nearest_zone_breakout(zones: list[dict], zone_type: str, current_price: float | None) -> dict | None:
    """Dla wybicia (wariant A): strefa po właściwej stronie ceny.

    Dla RESISTANCE: strefa poniżej ceny (upper <= close) — cena wybiła się powyżej.
    Dla SUPPORT: strefa powyżej ceny (lower >= close) — cena wybiła się poniżej.
    Zwraca najbliższą strefę w tym kierunku.
    """
    if not zones or current_price is None:
        return None
    candidates = [z for z in zones if z.get("type") == zone_type]
    if not candidates:
        return None
    if zone_type == "RESISTANCE":
        below = [z for z in candidates if z.get("upper") is not None and z["upper"] <= current_price]
        if not below:
            return None
        return max(below, key=lambda z: z["upper"])
    if zone_type == "SUPPORT":
        above = [z for z in candidates if z.get("lower") is not None and z["lower"] >= current_price]
        if not above:
            return None
        return min(above, key=lambda z: z["lower"])
    return None


def _zone_containing_or_near(
    zones: list[dict],
    zone_type: str,
    current_price: float | None,
    atr_value: float | None,
) -> dict | None:
    """Dla formacji (wariant B): strefa w której cena jest wewnątrz,
    lub najbliższa strefa w odległości <= 0.5 ATR od jej centrum."""
    if not zones or current_price is None:
        return None
    candidates = [z for z in zones if z.get("type") == zone_type]
    if not candidates:
        return None
    inside = [z for z in candidates
              if z.get("lower") is not None and z.get("upper") is not None
              and z["lower"] <= current_price <= z["upper"]]
    if inside:
        return inside[0]
    if atr_value is not None:
        best = None
        best_dist = float("inf")
        for z in candidates:
            center = z.get("center")
            if center is None:
                continue
            dist = abs(current_price - center)
            if dist <= 0.5 * atr_value and dist < best_dist:
                best = z
                best_dist = dist
        if best is not None:
            return best
    return None


def evaluate_trigger_1h(
    df_1h: Any,
    sr_zones: list[dict],
    atr: float | None,
    side: str,
) -> tuple[bool, float | None]:
    """Sprawdza czy wyzwalacz 1H jest potwierdzony dla danego kierunku.

    Wariant A: zamknięcie świecy 1H za poziomem wyzwalającym (granica strefy S/R).
    Wariant B: zamknięta, kierunkowa formacja świecowa 1H wewnątrz strefy S/R
    lub w odległości <= 0.5 ATR od niej.

    Zwraca (potwierdzone, poziom_wyzwalajacy).
    """
    if df_1h is None or df_1h.empty:
        return False, None

    # Ostatnia zamknięta świeca 1H (wyłącznie zamknięte, bez lookahead w przyszłość).
    last_closed = None
    for i in range(len(df_1h) - 1, -1, -1):
        candle = analyze_candle(df_1h, i, "1H")
        if candle and candle.get("is_closed"):
            last_closed = candle
            break
    if last_closed is None:
        return False, None

    close = last_closed["close"]

    # --- Wariant A: wybicie poziomu wyzwalającego ---
    if side == "LONG":
        zone = _nearest_zone_breakout(sr_zones, "RESISTANCE", close)
        if zone is not None and zone.get("upper") is not None and close > zone["upper"]:
            return True, float(zone["upper"])
    else:  # SHORT
        zone = _nearest_zone_breakout(sr_zones, "SUPPORT", close)
        if zone is not None and zone.get("lower") is not None and close < zone["lower"]:
            return True, float(zone["lower"])

    # --- Wariant B: kierunkowa formacja świecowa 1H w strefie lub <= 0.5 ATR od niej ---
    atr_value = _atr_value(atr) if atr is not None else None
    candles_1h = detect_candlestick_patterns(df_1h)
    for candle in candles_1h:
        # Formacja musi być na ostatniej zamkniętej świecy.
        if candle.get("time") != last_closed["time"]:
            continue
        if side == "LONG" and candle.get("direction") == "bullish":
            zone = _zone_containing_or_near(sr_zones, "SUPPORT", close, atr_value)
            if zone is None:
                continue
            zone_center = zone.get("center")
            if zone_center is not None:
                return True, float(zone_center)
        if side == "SHORT" and candle.get("direction") == "bearish":
            zone = _zone_containing_or_near(sr_zones, "RESISTANCE", close, atr_value)
            if zone is None:
                continue
            zone_center = zone.get("center")
            if zone_center is not None:
                return True, float(zone_center)

    return False, None


def _atr_value(atr) -> float | None:
    try:
        v = float(atr)
        if v != v or abs(v) == float("inf") or v <= 0:
            return None
        return v
    except (TypeError, ValueError):
        return None


def _nearest_zone_above(zones: list[dict], zone_type: str, price: float | None) -> dict | None:
    """Najbliższa strefa danego typu z center powyżej ceny (dla TP LONG)."""
    if not zones or price is None:
        return None
    candidates = [z for z in zones if z.get("type") == zone_type and z.get("center") is not None and z["center"] > price]
    if not candidates:
        return None
    return min(candidates, key=lambda z: z["center"])


def _nearest_zone_below(zones: list[dict], zone_type: str, price: float | None) -> dict | None:
    """Najbliższa strefa danego typu z center poniżej ceny (dla TP SHORT)."""
    if not zones or price is None:
        return None
    candidates = [z for z in zones if z.get("type") == zone_type and z.get("center") is not None and z["center"] < price]
    if not candidates:
        return None
    return max(candidates, key=lambda z: z["center"])


def calculate_sl(side: str, entry: float | None, sr_zones: list[dict], current_price: float | None, invalidation_buffer: float | None) -> float | None:
    """SL = poziom unieważnienia z buforem 0.25 ATR.

    LONG: SL = lower granica najbliższej strefy SUPPORT poniżej ceny - bufor.
    SHORT: SL = upper granica najbliższej strefy RESISTANCE powyżej ceny + bufor.
    """
    if entry is None or invalidation_buffer is None:
        return None
    if side == "LONG":
        zone = _nearest_zone_below(sr_zones, "SUPPORT", current_price)
        if zone is not None and zone.get("lower") is not None:
            sl = float(zone["lower"]) - invalidation_buffer
            return sl if sl < entry else None
    else:
        zone = _nearest_zone_above(sr_zones, "RESISTANCE", current_price)
        if zone is not None and zone.get("upper") is not None:
            sl = float(zone["upper"]) + invalidation_buffer
            return sl if sl > entry else None
    return None


def calculate_tp(side: str, entry: float | None, sr_zones: list[dict]) -> float | None:
    """TP = najbliższa przeciwna strefa S/R (środek strefy).

    LONG: RESISTANCE powyżej Entry.
    SHORT: SUPPORT poniżej Entry.
    """
    if entry is None:
        return None
    if side == "LONG":
        zone = _nearest_zone_above(sr_zones, "RESISTANCE", entry)
        if zone is not None and zone.get("center") is not None:
            return float(zone["center"])
    else:
        zone = _nearest_zone_below(sr_zones, "SUPPORT", entry)
        if zone is not None and zone.get("center") is not None:
            return float(zone["center"])
    return None


def calculate_rr(side: str, entry: float | None, sl: float | None, tp: float | None) -> tuple[float | None, str]:
    """RR = |TP - Entry| / |Entry - SL| z walidacją stron."""
    if entry is None or sl is None or tp is None:
        return None, "Brak kompletnych poziomów"
    if side == "LONG":
        if not (tp > entry and sl < entry):
            return None, "Poziomy nieprawidłowe dla LONG"
    else:
        if not (tp < entry and sl > entry):
            return None, "Poziomy nieprawidłowe dla SHORT"
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0 or reward <= 0:
        return None, "RR nieprawidłowy"
    rr = reward / risk
    return rr, f"RR: {round(rr, 2)}"


def fallback_tp_from_levels(side: str, entry: float | None, dec_levels: dict) -> float | None:
    """Fallback TP z _levels() tylko po walidacji stron i odległości > 0."""
    if entry is None:
        return None
    fb_entry = dec_levels.get("entry")
    fb_stop = dec_levels.get("stop")
    fb_target = dec_levels.get("target")
    if fb_entry is None or fb_stop is None or fb_target is None:
        return None
    fb_entry = float(fb_entry)
    fb_stop = float(fb_stop)
    fb_target = float(fb_target)
    if side == "LONG":
        if fb_target > fb_entry:
            return fb_target
    else:
        if fb_target < fb_entry:
            return fb_target
    return None


def analyze_symbol(symbol_key: str) -> dict:
    data = fetch_all(symbol_key)
    if not data:
        return {"symbol": symbol_key, "error": "no data"}

    name = SYMBOLS[symbol_key]["name"]
    result = {
        "symbol": symbol_key,
        "name": name,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeframes": {},
        "decision": "BRAK",
        "confidence": 0,
        "entry": None,
        "stop": None,
        "price": None,
        "reasons": [],
        "summary": "",
    }

    for tf, df in data.items():
        result["timeframes"][tf] = analyze_tf(df, tf, symbol_key)
    if "Daily" in result["timeframes"]:
        result["timeframes"]["1D"] = result["timeframes"]["Daily"]

    # --- Strefy S/R per interwał ---
    sr_data_by_tf = {}
    for raw_tf, df in data.items():
        canonical = "1D" if raw_tf == "Daily" else raw_tf
        frame = result["timeframes"].get(canonical)
        if df is not None and not df.empty and frame and "error" not in frame:
            sr_data_by_tf[canonical] = {
                "df": df,
                "current_price": frame.get("last_close"),
                "atr": frame.get("atr"),
            }
    if sr_data_by_tf:
        all_zones = compute_zones_for_symbol(sr_data_by_tf, symbol_key)
        for tf, zones in all_zones.items():
            if tf == "MULTITF":
                continue
            raw_tf = "Daily" if tf == "1D" else tf
            frame = result["timeframes"].get(raw_tf)
            if frame:
                frame["sr_zones"] = validate_zones(zones)
                frame["sr_zones_timeframe"] = tf

    decisions = {}
    for tf, canonical in (("1H", "1H"), ("Daily", "1D")):
        frame = result["timeframes"].get(tf)
        if frame and "error" not in frame:
            raw_decision = make_decision(
                data.get(tf), frame.get("renko") or {}, frame.get("harmonics") or [],
                frame.get("candles") or [], timeframe=canonical,
            )
            decisions[canonical] = evaluate_signal(raw_decision, data.get(tf), canonical)

    tf4 = result["timeframes"].get("4H")
    if tf4 and "error" not in tf4:
        dec = make_decision(
            data.get("4H"), tf4.get("renko") or {}, tf4.get("harmonics") or [],
            tf4.get("candles") or [], daily_analysis=decisions.get("1D"),
            hourly_analysis=decisions.get("1H"), timeframe="4H",
        )
        if dec.get("levels_timeframe") == "1H" and decisions.get("1H"):
            hourly = decisions["1H"]
            for key in ("signal_status", "can_enter", "signal_origin", "signal_valid_until",
                        "activated_at", "closed_at", "signal_close_reason"):
                dec[key] = hourly.get(key)
        else:
            dec = evaluate_signal(dec, data.get("4H"), "4H")
        decisions["4H"] = dec
        result["decision"] = dec["decision"]
        result["confidence"] = dec["confidence"]
        result["base_confidence"] = dec.get("base_confidence")
        result["entry"] = dec["entry"]
        result["stop"] = dec["stop"]
        result["target"] = dec.get("target")
        result["rr"] = dec.get("rr")
        result["levels_source_timeframe"] = dec.get("levels_timeframe", "4H")
        result["price"] = dec["price"]
        result["pillars"] = dec.get("pillars", 0)
        result["modules"] = dec.get("modules") or {}
        result["contradiction"] = dec.get("contradiction", False)
        result["daily_align"] = dec.get("daily_align", 0)
        result["timeframe_alignment"] = dec.get("timeframe_alignment") or {}
        result["levels_timeframe"] = dec.get("levels_timeframe", "4H")
        result["levels_basis"] = dec.get("levels_basis")
        result["levels_by_timeframe"] = dec.get("levels_by_timeframe") or {}
        result["main_signal_timeframe"] = "4H"
        result["last_bar_time"] = dec.get("last_bar_time")
        result["atr"] = dec.get("atr")
        result["reasons"] = dec["reasons"]
        result["harmonic"] = dec.get("harmonic")
        result["candle"] = dec.get("candle")
        result["renko_signal"] = dec.get("renko_signal")
        for key in ("signal_status", "can_enter", "signal_origin", "signal_valid_until",
                    "activated_at", "closed_at", "signal_close_reason"):
            result[key] = dec.get(key)

        for canonical, frame_decision in decisions.items():
            raw_tf = "Daily" if canonical == "1D" else canonical
            frame = result["timeframes"].get(raw_tf) or {}
            frame.update({
                "decision": frame_decision.get("decision"),
                "bias": (dec.get("timeframe_alignment", {}).get(canonical) or {}).get("bias")
                    if canonical != "4H" else (dec.get("timeframe_alignment", {}).get("4H") or {}).get("bias"),
                "confidence": frame_decision.get("confidence"),
                "base_confidence": frame_decision.get("base_confidence"),
                "atr": frame_decision.get("atr"),
                "entry": frame_decision.get("entry"),
                "stop": frame_decision.get("stop"),
                "target": frame_decision.get("target"),
                "rr": frame_decision.get("rr"),
                "levels_timeframe": frame_decision.get("levels_timeframe", canonical),
                "levels_by_timeframe": frame_decision.get("levels_by_timeframe") or {},
                "reasons": frame_decision.get("reasons") or [],
                "signal_status": frame_decision.get("signal_status"),
                "can_enter": frame_decision.get("can_enter", False),
                "signal_origin": frame_decision.get("signal_origin"),
                "signal_valid_until": frame_decision.get("signal_valid_until"),
                "activated_at": frame_decision.get("activated_at"),
                "closed_at": frame_decision.get("closed_at"),
                "signal_close_reason": frame_decision.get("signal_close_reason"),
            })
        daily_r = (result["timeframes"].get("Daily") or {}).get("renko") or {}
        result["daily_context"] = {"up": "wzrostowy", "down": "spadkowy"}.get(daily_r.get("direction"), "neutralny")

        # --- entry_readiness: model gotowości + cykl życia setupu ---
        import pandas as _pd
        df_4h = data.get("4H")
        current_price = dec.get("price")
        atr_val = dec.get("atr")

        data_fresh = True
        if df_4h is not None and not df_4h.empty:
            try:
                last_bar = df_4h.index[-1]
                if hasattr(last_bar, "tz_convert"):
                    last_bar = last_bar.tz_convert("UTC")
                else:
                    last_bar = last_bar.tz_localize("UTC")
                now_utc = datetime.now(timezone.utc)
                max_age_delta = _pd.Timedelta(hours=MAX_DATA_AGE * 4)
                data_fresh = (now_utc - last_bar) <= max_age_delta
            except Exception:
                data_fresh = False

        renko = tf4.get("renko") or {}
        harmonics = tf4.get("harmonics") or []
        harmonic_active = any(h.get("lifecycle") in ("forming", "active") for h in harmonics)
        renko_dir = renko.get("direction", "unknown")
        renko_aligned_long = bool(renko.get("local_low") or (renko.get("last_reversal") and renko_dir == "up"))
        renko_aligned_short = bool(renko.get("local_high") or (renko.get("last_reversal") and renko_dir == "down"))

        sr_zones = tf4.get("sr_zones") or []
        sr_position_long = {"price_in_zone": False, "zone_distance_atr": None, "zone_type": None, "note": ""}
        sr_position_short = {"price_in_zone": False, "zone_distance_atr": None, "zone_type": None, "note": ""}
        if current_price is not None and atr_val:
            for z in sr_zones:
                z_type = z.get("type")
                z_lower = z.get("lower")
                z_upper = z.get("upper")
                z_center = z.get("center")
                if z_type == "SUPPORT":
                    in_zone = (z_lower is not None and z_upper is not None
                               and z_lower <= current_price <= z_upper)
                    dist = abs(current_price - z_center) / atr_val if z_center is not None else None
                    if in_zone:
                        sr_position_long = {"price_in_zone": True, "zone_distance_atr": 0.0,
                                            "zone_type": "SUPPORT", "note": "Cena wewnątrz strefy wsparcia"}
                    elif dist is not None and dist <= 0.5:
                        sr_position_long = {"price_in_zone": False, "zone_distance_atr": dist,
                                            "zone_type": "SUPPORT", "note": "W odległości <= 0.5 ATR od wsparcia"}
                elif z_type == "RESISTANCE":
                    in_zone = (z_lower is not None and z_upper is not None
                               and z_lower <= current_price <= z_upper)
                    dist = abs(current_price - z_center) / atr_val if z_center is not None else None
                    if in_zone:
                        sr_position_short = {"price_in_zone": True, "zone_distance_atr": 0.0,
                                             "zone_type": "RESISTANCE", "note": "Cena wewnątrz strefy oporu"}
                    elif dist is not None and dist <= 0.5:
                        sr_position_short = {"price_in_zone": False, "zone_distance_atr": dist,
                                             "zone_type": "RESISTANCE", "note": "W odległości <= 0.5 ATR od oporu"}
        charts = {}
        for raw_tf, canonical in (("1H", "1H"), ("4H", "4H"), ("Daily", "1D")):
            df = data.get(raw_tf)
            frame = result["timeframes"].get(raw_tf)
            frame_decision = decisions.get(canonical)
            if df is None or not frame or not frame_decision:
                continue
            own_levels = (frame_decision.get("levels_by_timeframe") or {}).get(canonical) or {
                "entry": frame_decision.get("entry"), "stop": frame_decision.get("stop"),
                "target": frame_decision.get("target"),
            }
            if frame_decision.get("signal_status") not in {"PENDING", "ACTIVE"}:
                own_levels = {}
            visible_harmonics = [h for h in (frame.get("harmonics") or []) if harmonic_is_visible(h, df)]
            charts[canonical] = build_chart_payload(
                df, frame.get("candles") or [], visible_harmonics, own_levels,
                symbol=symbol_key, timeframe=canonical, levels_timeframe=canonical,
                signal_status=frame_decision.get("signal_status"),
                can_enter=frame_decision.get("can_enter", False),
                sr_zones=(frame or {}).get("sr_zones", []),
                current_price=frame.get("last_close"),
            )
        # --- Prawdziwy wyzwalacz 1H (Etap 10A) ---
        df_1h = data.get("1H")
        frame_1h = result["timeframes"].get("1H") or {}
        sr_zones_1h = frame_1h.get("sr_zones") or []
        atr_1h = frame_1h.get("atr")

        trigger_confirmed_long, trigger_level_long = evaluate_trigger_1h(
            df_1h, sr_zones_1h, atr_1h, "LONG"
        )
        trigger_confirmed_short, trigger_level_short = evaluate_trigger_1h(
            df_1h, sr_zones_1h, atr_1h, "SHORT"
        )

        # --- Etap 10B: Entry, SL, TP, RR osobno dla LONG i SHORT ---
        current_price = dec.get("price")
        atr_for_levels = _atr_value(atr_val) if atr_val is not None else None
        invalidation_buffer = (atr_for_levels * INVALIDATION_BUFFER_ATR_MULT) if atr_for_levels else None

        sr_zones_4h = tf4.get("sr_zones") or [] if tf4 else []

        entry_long = float(trigger_level_long) if (trigger_confirmed_long and trigger_level_long is not None) else None
        entry_short = float(trigger_level_short) if (trigger_confirmed_short and trigger_level_short is not None) else None

        stop_long = calculate_sl("LONG", entry_long, sr_zones_4h, current_price, invalidation_buffer)
        stop_short = calculate_sl("SHORT", entry_short, sr_zones_4h, current_price, invalidation_buffer)

        tp_long = calculate_tp("LONG", entry_long, sr_zones_4h)
        if tp_long is None:
            tp_long = fallback_tp_from_levels("LONG", entry_long, dec)

        tp_short = calculate_tp("SHORT", entry_short, sr_zones_4h)
        if tp_short is None:
            tp_short = fallback_tp_from_levels("SHORT", entry_short, dec)

        rr_long, rr_long_note = calculate_rr("LONG", entry_long, stop_long, tp_long)
        rr_short, rr_short_note = calculate_rr("SHORT", entry_short, stop_short, tp_short)

        long_data = {
            "context_1d": {"bias": (decisions.get("1D") or {}).get("decision", "BRAK"),
                           "note": "Kontekst 1D: " + str((decisions.get("1D") or {}).get("decision", "BRAK"))},
            "structure_4h": {
                "renko_aligned": renko_aligned_long,
                "harmonic_active": harmonic_active,
                "direction_match": True,
                "note": "Renko: " + str(renko_dir) + ", harmoniczna aktywna: " + str(harmonic_active),
            },
            "sr_position": sr_position_long,
            "trigger": {"confirmed": trigger_confirmed_long, "trigger_level": trigger_level_long,
                        "note": "Wyzwalacz 1H potwierdzony" if trigger_confirmed_long
                        else "Brak potwierdzonego wyzwalacza 1H"},
            "rr": {"rr": rr_long, "entry": entry_long, "stop": stop_long, "target": tp_long,
                   "invalidation_level": stop_long,
                   "note": rr_long_note},
        }
        short_data = {
            "context_1d": {"bias": (decisions.get("1D") or {}).get("decision", "BRAK"),
                           "note": "Kontekst 1D: " + str((decisions.get("1D") or {}).get("decision", "BRAK"))},
            "structure_4h": {
                "renko_aligned": renko_aligned_short,
                "harmonic_active": harmonic_active,
                "direction_match": True,
                "note": "Renko: " + str(renko_dir) + ", harmoniczna aktywna: " + str(harmonic_active),
            },
            "sr_position": sr_position_short,
            "trigger": {"confirmed": trigger_confirmed_short, "trigger_level": trigger_level_short,
                        "note": "Wyzwalacz 1H potwierdzony" if trigger_confirmed_short
                        else "Brak potwierdzonego wyzwalacza 1H"},
            "rr": {"rr": rr_short, "entry": entry_short, "stop": stop_short, "target": tp_short,
                   "invalidation_level": stop_short,
                   "note": rr_short_note},
        }

        entry_readiness = calculate_readiness(
            symbol=symbol_key,
            main_timeframe="4H",
            long_data=long_data,
            short_data=short_data,
            current_price=current_price,
            atr=atr_val,
            data_fresh=data_fresh,
            long_invalidated=False,
            short_invalidated=False,
            long_expired=False,
            short_expired=False,
        )

        # Wybierz poziomy strony kierunkowej dla cyklu życia
        chosen_direction = dec.get("decision")
        if chosen_direction == "LONG":
            lifecycle_entry = entry_long
            lifecycle_stop = stop_long
            lifecycle_target = tp_long
            lifecycle_invalidation = stop_long
            lifecycle_trigger_confirmed = trigger_confirmed_long
            lifecycle_trigger_level = trigger_level_long
        elif chosen_direction == "SHORT":
            lifecycle_entry = entry_short
            lifecycle_stop = stop_short
            lifecycle_target = tp_short
            lifecycle_invalidation = stop_short
            lifecycle_trigger_confirmed = trigger_confirmed_short
            lifecycle_trigger_level = trigger_level_short
        else:
            lifecycle_entry = None
            lifecycle_stop = None
            lifecycle_target = None
            lifecycle_invalidation = None
            lifecycle_trigger_confirmed = False
            lifecycle_trigger_level = None

        lifecycle_state = manage_lifecycle(
            symbol=symbol_key,
            direction=chosen_direction,
            readiness_pct=entry_readiness["readiness_pct"],
            trigger_confirmed=lifecycle_trigger_confirmed,
            blockers=entry_readiness["blockers"],
            invalidation_level=lifecycle_invalidation,
            entry=lifecycle_entry,
            stop=lifecycle_stop,
            target=lifecycle_target,
            df_4h=df_4h,
            current_bar_index=len(df_4h) - 1 if df_4h is not None else 0,
            next_check_time=entry_readiness.get("next_check_time"),
            data_fresh=data_fresh,
        )

        result["entry_readiness"] = entry_readiness
        result["setup_lifecycle"] = lifecycle_state
        result["_charts"] = charts
        result["_chart"] = charts.get("4H")

        if dec["decision"] in ("LONG", "SHORT") and dec.get("signal_status") in {"PENDING", "ACTIVE"}:
            rr_s = f", R:R 1:{dec.get('rr')}" if dec.get("rr") else ""
            result["summary"] = (
                f"{name} 4H -> {dec['decision']} @ {dec['entry']} ({dec.get('levels_timeframe', '4H')}) "
                f"(stop {dec['stop']}, cel {dec.get('target')}, ocena sygnalu {dec['confidence']}/100{rr_s})"
            )
        else:
            result["summary"] = f"{name} 4H -> brak setupu wejscia; kontekst 1D/1H uwzgledniony w ocenie"
    else:
        result["summary"] = f"{name}: brak danych 4H"
        result["reasons"] = ["Brak danych 4H"]

    result["overall_bias"] = (
        result["decision"] if result.get("signal_status") in {"PENDING", "ACTIVE"} else "NIC"
    )
    result["overall_confidence"] = result["confidence"]
    result["overall_action"] = (
        f"Oczekuje na wejscie {result['decision']} @ {result['entry']}" if result.get("can_enter")
        else "Pozycja po wejsciu – nie otwieraj nowej" if result.get("signal_status") == "ACTIVE"
        else "Brak wejscia – czekaj"
    )
    result["overall_summary"] = result["summary"]
    return result


def analyze_all() -> list:
    results = []
    for key in SYMBOLS:
        print(f"Analyzing {key}...")
        results.append(analyze_symbol(key))
    return results


if __name__ == "__main__":
    all_res = analyze_all()
    out_path = Path(__file__).resolve().parents[1] / "output" / "status.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_res, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
    for r in all_res:
        d = r.get("decision", "?")
        print(f"{r['symbol']:8} -> {d:5} conf={r.get('confidence',0)} entry={r.get('entry')}")
