# analysis/decision_log.py
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone

try:
    from config import DECISIONS_LOG_MAX, DECISIONS_SCHEMA_VERSION
except Exception:
    DECISIONS_LOG_MAX = 200
    DECISIONS_SCHEMA_VERSION = 1

OUTPUT = Path(__file__).resolve().parents[1] / "output"
LOG_PATH = OUTPUT / "decisions_log.json"


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


def _load_log() -> dict:
    if not LOG_PATH.exists():
        return {"schema_version": DECISIONS_SCHEMA_VERSION, "decisions": []}
    try:
        data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"schema_version": DECISIONS_SCHEMA_VERSION, "decisions": data}
        if "decisions" not in data:
            data["decisions"] = []
        data["schema_version"] = data.get("schema_version", DECISIONS_SCHEMA_VERSION)
        return data
    except Exception:
        return {"schema_version": DECISIONS_SCHEMA_VERSION, "decisions": []}


def _archive_old(decisions: list) -> list:
    if len(decisions) <= DECISIONS_LOG_MAX:
        return decisions
    overflow = decisions[:-DECISIONS_LOG_MAX]
    keep = decisions[-DECISIONS_LOG_MAX:]
    by_year = {}
    for d in overflow:
        ts = d.get("timestamp") or d.get("candle_close_time") or ""
        year = ts[:4] if len(ts) >= 4 else str(datetime.now(timezone.utc).year)
        by_year.setdefault(year, []).append(d)
    for year, items in by_year.items():
        arch = OUTPUT / f"decisions_archive_{year}.json"
        existing = []
        if arch.exists():
            try:
                raw = json.loads(arch.read_text(encoding="utf-8"))
                existing = raw if isinstance(raw, list) else raw.get("decisions", [])
            except Exception:
                existing = []
        existing.extend(items)
        arch.write_text(
            json.dumps({"schema_version": DECISIONS_SCHEMA_VERSION, "decisions": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[LOG] Zarchiwizowano {len(items)} -> {arch.name}")
    return keep


def build_entry(result: dict, run_time=None):
    decision = result.get("decision")
    if decision not in ("LONG", "SHORT"):
        return None
    candle_close = _norm_iso(result.get("last_bar_time"))
    ts = run_time or _utc_now_iso()
    symbol = (result.get("symbol") or "?").upper()
    entry_id = f"{candle_close or ts}_{symbol}_4H"
    modules = result.get("modules") or {}
    pillars = int(result.get("pillars") or 0)
    daily_align = result.get("daily_align", 0)
    if daily_align == 1:
        daily_ctx = decision
    elif daily_align == -1:
        daily_ctx = "SHORT" if decision == "LONG" else "LONG"
    else:
        daily_ctx = "NIC"
    return {
        "id": entry_id,
        "timestamp": ts,
        "symbol": result.get("symbol"),
        "timeframe": "4H",
        "candle_close_time": candle_close,
        "decision": decision,
        "confidence": result.get("confidence"),
        "entry": result.get("entry"),
        "stop": result.get("stop"),
        "target": result.get("target"),
        "rr": result.get("rr"),
        "filars": {
            "renko": bool(modules.get("renko")),
            "harmonic": bool(modules.get("harmonic")),
            "candle": bool(modules.get("candle")),
        },
        "confluence": f"{pillars}/3",
        "reasons": result.get("reasons") or [],
        "daily_context": daily_ctx,
        "atr_4h": result.get("atr"),
        "candle_stale": None,
        "gap_weekend": None,
        "outcome": None,
        "outcome_checked_at": None,
        "outcome_result": None,
        # POPRAWKA: pełne timeframes (harmonics, candles, renko) — dla bogatego modala
        "timeframes": result.get("timeframes") or {},
    }


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def append_decisions(results: list) -> None:
    OUTPUT.mkdir(exist_ok=True)
    data = _load_log()
    run_time = _utc_now_iso()
    added = 0
    for r in results:
        entry = build_entry(r, run_time=run_time)
        if entry is None:
            continue
        try:
            if entry["candle_close_time"]:
                from config import STALE_DATA_HOURS
                ct = datetime.fromisoformat(entry["candle_close_time"].replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - ct).total_seconds() / 3600
                entry["candle_stale"] = age_h > STALE_DATA_HOURS
        except Exception:
            entry["candle_stale"] = None
        exists = any(
            d.get("id") == entry["id"] and d.get("timestamp") == entry["timestamp"]
            for d in data["decisions"][-30:]
        )
        if exists:
            continue
        data["decisions"].append(entry)
        added += 1
    data["decisions"] = _archive_old(data["decisions"])
    data["schema_version"] = DECISIONS_SCHEMA_VERSION
    data["updated"] = run_time
    _atomic_write(LOG_PATH, data)
    print(f"[LOG] Dodano {added} decyzji. Biezacy log: {len(data['decisions'])} wpisow.")


def latest_per_symbol(decisions: list) -> dict:
    ranked = sorted(decisions, key=lambda d: (d.get("candle_close_time") or "", d.get("timestamp") or ""))
    by_sym = {}
    for d in ranked:
        by_sym[d.get("symbol")] = d
    return by_sym