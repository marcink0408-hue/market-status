# analysis/analyzer.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from data.fetcher import fetch_all
from analysis.renko import build_renko, renko_status
from analysis.harmonics import detect_harmonics
from analysis.candles import detect_candlestick_patterns
from analysis.classic_patterns import detect_classic_patterns
from analysis.decision import make_decision
from analysis.lifecycle import evaluate_harmonic, evaluate_signal, harmonic_is_visible
from config import SYMBOLS
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

        from analysis.chart_data import build_chart_payload
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
            )
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
