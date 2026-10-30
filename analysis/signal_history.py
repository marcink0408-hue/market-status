# analysis/signal_history.py
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from config import DECISIONS_SCHEMA_VERSION
except Exception:
    DECISIONS_SCHEMA_VERSION = 1

OUTPUT = Path(__file__).resolve().parents[1] / "output"
SIGNALS_PATH = OUTPUT / "signals_history.json"
SIGNALS_SCHEMA_VERSION = 1

# 4H = 4 godziny = 14400 sekund
TF_4H_SECONDS = 4 * 3600
# right=2 w harmonics.py -> pivot potwierdzony 2 świece po D
PIVOT_CONFIRM_BARS = 2


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_iso(ts):
    if ts is None:
        return None
    s = str(ts).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError):
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None


def _load_signals() -> dict:
    if not SIGNALS_PATH.exists():
        return {"schema_version": SIGNALS_SCHEMA_VERSION, "signals": []}
    try:
        data = json.loads(SIGNALS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"schema_version": SIGNALS_SCHEMA_VERSION, "signals": data}
        if "signals" not in data:
            data["signals"] = []
        data["schema_version"] = data.get("schema_version", SIGNALS_SCHEMA_VERSION)
        return data
    except Exception:
        return {"schema_version": SIGNALS_SCHEMA_VERSION, "signals": []}


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _next_signal_id(signals: list, symbol: str, pattern: str) -> str:
    """Unikalny identyfikator sygnalu: US500_4H_BUTTERFLY_001."""
    sym = (symbol or "?").upper()
    pat = (pattern or "PATTERN").upper().replace(" ", "")
    prefix = f"{sym}_4H_{pat}_"
    max_n = 0
    for s in signals:
        sid = s.get("signal_id") or ""
        if sid.startswith(prefix):
            tail = sid[len(prefix):]
            if tail.isdigit():
                max_n = max(max_n, int(tail))
    return f"{prefix}{max_n + 1:03d}"


def _candle_time_plus_bars(candle_iso: str, bars: int) -> str | None:
    """Czas swiecy + N swiec 4H (dla confirmed_at przy pivot right=2)."""
    if not candle_iso:
        return None
    try:
        dt = datetime.fromisoformat(candle_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (dt + timedelta(seconds=TF_4H_SECONDS * bars)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError):
        return None


def _extract_completed_harmonics(result: dict) -> list:
    """Zwraca liste completed harmonics z result['timeframes']['4H']['harmonics']."""
    tf4 = (result.get("timeframes") or {}).get("4H") or {}
    return [h for h in (tf4.get("harmonics") or []) if h.get("status") == "completed"]


def build_signal_entry(result: dict, harmonic: dict, run_time: str | None = None) -> dict | None:
    """Buduje wpis sygnalu dla jednej completed harmonicznej (instrukcja Etap C)."""
    if not harmonic:
        return None
    direction = harmonic.get("direction") or "bullish"
    if direction not in ("bullish", "bearish"):
        return None
    # Mapowanie bullish/bearish -> LONG/SHORT (zgodnie z harmonami: bullish = LONG)
    decision = "LONG" if direction == "bullish" else "SHORT"

    # detected_at = czas D (kiedy formacja sie uformowala)
    detected_iso = _norm_iso(harmonic.get("time_D"))
    if not detected_iso:
        return None
    # confirmed_at = czas D + PIVOT_CONFIRM_BARS swiec 4H (right=2 w harmonics.py)
    confirmed_iso = _candle_time_plus_bars(detected_iso, PIVOT_CONFIRM_BARS)

    ts = run_time or _utc_now_iso()
    signal_id = _next_signal_id(_load_signals().get("signals", []), result.get("symbol"), harmonic.get("name"))

    # entry/stop/target z decyzji systemu (jesli sa); jesli nie ma - None
    entry = result.get("entry")
    stop = result.get("stop")
    target = result.get("target")

    return {
        "signal_id": signal_id,
        "symbol": (result.get("symbol") or "?").lower(),
        "timeframe": "4H",
        "pattern": harmonic.get("name"),
        "direction": direction,
        "status": "DETECTED",
        "detected_at": detected_iso,
        "confirmed_at": confirmed_iso,
        "activated_at": None,
        "invalidated_at": None,
        "closed_at": None,
        "entry": entry,
        "stop": stop,
        "target": target,
        "decision": decision,
        "confidence": result.get("confidence"),
        "detected_run_at": ts,
    }


def append_signal_history(results: list) -> None:
    """Dopisuje nowe sygnaly (completed harmonics) do output/signals_history.json."""
    OUTPUT.mkdir(exist_ok=True)
    data = _load_signals()
    run_time = _utc_now_iso()
    added = 0
    for r in results:
        harmonics = _extract_completed_harmonics(r)
        for h in harmonics:
            entry = build_signal_entry(r, h, run_time=run_time)
            if entry is None:
                continue
            # deduplikacja: ten sam signal_id (symbol+pattern+numer) i detected_at
            exists = any(
                s.get("signal_id") == entry["signal_id"]
                and s.get("detected_at") == entry["detected_at"]
                for s in data["signals"]
            )
            if exists:
                continue
            data["signals"].append(entry)
            added += 1
    data["schema_version"] = SIGNALS_SCHEMA_VERSION
    data["updated"] = run_time
    _atomic_write(SIGNALS_PATH, data)
    print(f"[SIGNAL] Dodano {added} sygnalow. Biezacy log: {len(data['signals'])} wpisow.")