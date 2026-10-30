# analysis/analyzer.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from data.fetcher import fetch_all
from analysis.renko import build_renko, renko_status
from analysis.harmonics import detect_harmonics
from analysis.candles import detect_candlestick_patterns
from analysis.decision import make_decision
from config import SYMBOLS
import json
from datetime import datetime, timezone


def analyze_tf(df, tf: str) -> dict:
    try:
        rdf = build_renko(df)
        rstat = renko_status(rdf)
        harms = detect_harmonics(df)
        cands = detect_candlestick_patterns(df)
        return {
            "renko": rstat,
            "harmonics": harms,
            "candles": cands,
            "bars": len(df),
            "last_close": float(df["close"].iloc[-1]),
            "last_time": str(df.index[-1]),
        }
    except Exception as e:
        return {"error": str(e)}


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
        result["timeframes"][tf] = analyze_tf(df, tf)

    tf4 = result["timeframes"].get("4H")
    if tf4 and "error" not in tf4:
        daily_r = (result["timeframes"].get("Daily") or {}).get("renko") or {}
        dec = make_decision(
            data.get("4H"),
            tf4.get("renko") or {},
            tf4.get("harmonics") or [],
            tf4.get("candles") or [],
            daily_renko=daily_r,
        )
        result["decision"] = dec["decision"]
        result["confidence"] = dec["confidence"]
        result["entry"] = dec["entry"]
        result["stop"] = dec["stop"]
        result["target"] = dec.get("target")
        result["rr"] = dec.get("rr")
        result["price"] = dec["price"]
        result["pillars"] = dec.get("pillars", 0)
        result["modules"] = dec.get("modules") or {}
        result["contradiction"] = dec.get("contradiction", False)
        result["daily_align"] = dec.get("daily_align", 0)
        result["last_bar_time"] = dec.get("last_bar_time")
        result["atr"] = dec.get("atr")
        result["reasons"] = dec["reasons"]
        result["harmonic"] = dec.get("harmonic")
        result["candle"] = dec.get("candle")
        result["renko_signal"] = dec.get("renko_signal")
        from analysis.chart_data import build_chart_payload
        result["_chart"] = build_chart_payload(
            data.get("4H"), tf4.get("candles") or [], tf4.get("harmonics") or [],
            {"entry": dec.get("entry"), "stop": dec.get("stop"), "target": dec.get("target")}
        )

        if dec["decision"] in ("LONG", "SHORT"):
            rr_s = f", R:R 1:{dec.get('rr')}" if dec.get("rr") else ""
            result["summary"] = (
                f"{name} 4H -> {dec['decision']} @ {dec['entry']} "
                f"(stop {dec['stop']}, cel {dec.get('target')}, ocena sygnalu {dec['confidence']}/100{rr_s})"
            )
        else:
            result["summary"] = f"{name} 4H -> brak setupu wejscia"
    else:
        result["summary"] = f"{name}: brak danych 4H"
        result["reasons"] = ["Brak danych 4H"]

    result["overall_bias"] = result["decision"] if result["decision"] != "BRAK" else "NIC"
    result["overall_confidence"] = result["confidence"]
    result["overall_action"] = (
        f"Wejscie {result['decision']} @ {result['entry']}" if result["decision"] in ("LONG", "SHORT")
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
