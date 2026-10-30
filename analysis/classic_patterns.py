# analysis/classic_patterns.py
"""
Etap D: detekcja klasycznych formacji cenowych przez ta_patterns 1.2.1.
Zapis do output/classic_patterns.json w jednolitym formacie JSON.

UWAGA (zgodnie z instrukcja):
- NIE podpinamy do make_decision() - formacje sa tylko wykrywane i zapisywane.
- NIE rysujemy geometrii - ta_patterns zwraca tablice sygnalow (bar -> wartosc),
  a nie wspolrzedne punktow formacji.
- FILTR: zapisujemy tylko klasyczne formacje (head_and_shoulders, double_top,
  triangle, wedge, flag, pennant, cup_and_handle, itd.) - bez wzorcow swiecowych
  (white_candle, black_candle, doji, two_dance, ...), bo te sa juz w candles.py.
  Bez filtra plik rosnie do ~20 MB dziennie.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

try:
    import ta_patterns as tap
    _TAP_OK = True
except Exception:
    _TAP_OK = False

OUTPUT = Path(__file__).resolve().parents[1] / "output"
CLASSIC_PATH = OUTPUT / "classic_patterns.json"
CLASSIC_SCHEMA_VERSION = 1

# Klasyczne formacje - filtr (bez wzorcow swiecowych typu white_candle/doji)
CLASSIC_KEYWORDS = (
    "head_and_shoulders",
    "inverse_head_and_shoulders",
    "double_top",
    "double_bottom",
    "triple_top",
    "triple_bottom",
    "triangle",
    "wedge",
    "flag",
    "pennant",
    "cup_and_handle",
    "rounding",
    "diamond",
    "broadening",
    "channel",
    "rectangle",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _is_classic(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in CLASSIC_KEYWORDS)


def detect_classic_patterns(df) -> list:
    """
    Dokladnie wedlug instrukcji (sekcja 2, 'Przykladowe uzycie w analysis/analyzer.py').
    Zwraca liste zdarzen: name, direction, bar, time, price.
    """
    if not _TAP_OK:
        return []
    if df is None or len(df) == 0:
        return []
    if "open" not in df.columns or "close" not in df.columns:
        return []

    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = None
    if "volume" in df.columns:
        v = df["volume"].fillna(0).to_numpy(dtype=float)

    try:
        signals = tap.scan_all_patterns(o, h, l, c, v=v)
    except Exception:
        return []

    results = []
    for name, values in (signals or {}).items():
        values = np.asarray(values)
        for i in np.flatnonzero(values):
            val = values[i]
            results.append({
                "name": str(name),
                "direction": "bullish" if val > 0 else "bearish",
                "bar": int(i),
                "time": str(df.index[i]),
                "price": float(c[i]),
            })
    # sortowanie po czasie, potem po nazwie (stabilnie)
    results.sort(key=lambda x: (x["time"], x["name"]))
    return results


def append_classic_patterns(results_all: list) -> None:
    """
    Zapisuje klasyczne formacje dla wszystkich symboli do output/classic_patterns.json.
    Filtruje tylko formacje klasyczne (bez wzorcow swiecowych typu white_candle/doji),
    zeby plik nie rosl do setek MB.
    """
    OUTPUT.mkdir(exist_ok=True)
    run_time = _utc_now_iso()
    payload = {
        "schema_version": CLASSIC_SCHEMA_VERSION,
        "timeframe": "4H",
        "updated": run_time,
        "symbols": {},
    }
    total = 0
    for r in results_all:
        symbol = (r.get("symbol") or "?").lower()
        tf4 = (r.get("timeframes") or {}).get("4H") or {}
        patterns = tf4.get("classic_patterns") or []
        clean = []
        for p in patterns:
            name = p.get("name") or ""
            if not _is_classic(name):
                continue
            try:
                ts = p.get("time")
                clean.append({
                    "name": name,
                    "direction": p.get("direction"),
                    "bar": int(p.get("bar")),
                    "time": str(ts),
                    "price": float(p.get("price")),
                })
            except (TypeError, ValueError):
                continue
        payload["symbols"][symbol] = clean
        total += len(clean)

    _atomic_write(CLASSIC_PATH, payload)
    print(f"[CLASSIC] Zapisano {total} klasycznych formacji w {CLASSIC_PATH.name}.")