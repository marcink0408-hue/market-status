# analysis/analyzer.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from data.fetcher import fetch_all
from analysis.renko import build_renko, renko_status
from analysis.harmonics import detect_harmonics
from analysis.candles import detect_candlestick_patterns
from config import SYMBOLS
import json
from datetime import datetime, timezone


def score_bias(renko: dict, harmonics: list, candles: list):
    score = 0
    if renko.get("direction") == "up":
        score += 15 + min(renko.get("consecutive", 0) * 3, 20)
        if renko.get("local_low"):
            score += 15
    elif renko.get("direction") == "down":
        score -= 15 + min(renko.get("consecutive", 0) * 3, 20)
        if renko.get("local_high"):
            score -= 15
    if renko.get("last_reversal"):
        score = int(score * 0.6)

    for h in harmonics:
        weight = 25 if h["status"] == "completed" else 18
        if h["direction"] == "bullish":
            score += weight
        else:
            score -= weight

    for c in candles:
        w = 12 if c["strength"] == "strong" else 7
        if c["direction"] == "bullish":
            score += w
        elif c["direction"] == "bearish":
            score -= w

    conf = min(abs(score), 95)
    if score >= 25:
        return "LONG", conf, "Szykuj longa – warunki sprzyjaja"
    elif score <= -25:
        return "SHORT", conf, "Szykuj shorta – warunki sprzyjaja"
    elif abs(score) >= 12:
        return "WATCH", conf, "Obserwuj – cos sie formuje"
    else:
        return "NIC", conf, "Na razie odpusc – brak setupu"


def make_summary(symbol: str, tf: str, renko: dict, harmonics: list, candles: list, bias: str, action: str) -> str:
    parts = []
    name = SYMBOLS[symbol]["name"]
    if renko.get("direction") == "up":
        parts.append(f"Renko ({tf}): trend wzrostowy ({renko.get('consecutive',0)} cegielek w gore)")
    elif renko.get("direction") == "down":
        parts.append(f"Renko ({tf}): trend spadkowy ({renko.get('consecutive',0)} cegielek w dol)")
    if renko.get("local_low"):
        parts.append("lokalny dolek na Renko")
    if renko.get("local_high"):
        parts.append("lokalny szczyt na Renko")
    if renko.get("last_reversal"):
        parts.append("swieze odwrocenie kierunku Renko")
    for h in harmonics[:2]:
        status = "formuje sie" if h["status"] == "forming" else "ukonczona"
        parts.append(f"{h['name']} {h['direction']} ({status})")
    for c in candles[:2]:
        parts.append(f"{c['name']} ({c['direction']})")
    if not parts:
        return f"{name} ({tf}): brak wyraznych sygnalow."
    return f"{name} ({tf}): " + ", ".join(parts) + f". -> {action}."


def analyze_symbol(symbol_key: str) -> dict:
    data = fetch_all(symbol_key)
    if not data:
        return {"symbol": symbol_key, "error": "no data"}

    result = {
        "symbol": symbol_key,
        "name": SYMBOLS[symbol_key]["name"],
        "updated": datetime.now(timezone.utc).isoformat(),
        "timeframes": {},
        "overall_bias": "NIC",
        "overall_confidence": 0,
        "overall_action": "Brak danych",
        "overall_summary": "",
    }

    biases = []
    summaries = []

    for tf, df in data.items():
        try:
            rdf = build_renko(df)
            rstat = renko_status(rdf)
            harms = detect_harmonics(df)
            cands = detect_candlestick_patterns(df)
            bias, conf, action = score_bias(rstat, harms, cands)
            summary = make_summary(symbol_key, tf, rstat, harms, cands, bias, action)
            result["timeframes"][tf] = {
                "renko": rstat, "harmonics": harms, "candles": cands,
                "bias": bias, "confidence": conf, "action": action,
                "summary": summary, "bars": len(df),
            }
            biases.append((bias, conf, tf))
            summaries.append(summary)
        except Exception as e:
            result["timeframes"][tf] = {"error": str(e)}

    priority = {"Daily": 3, "4H": 2, "1H": 1}
    best = None
    best_score = -1
    for b, c, tf in biases:
        sc = c * priority.get(tf, 1)
        if b in ("LONG", "SHORT") and sc > best_score:
            best_score = sc
            best = (b, c, tf)
        elif best is None:
            best = (b, c, tf)

    if best:
        result["overall_bias"] = best[0]
        result["overall_confidence"] = best[1]
        result["overall_action"] = result["timeframes"].get(best[2], {}).get("action", "")
        result["overall_summary"] = " | ".join(summaries[:2])
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
        print(f"{r['symbol']:8} -> {r.get('overall_bias','?'):6} ({r.get('overall_confidence',0)}%)  {r.get('overall_action','')}")
