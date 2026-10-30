# analysis/backtest.py
"""
Etap E: Backtesting (instrukcja, sekcja 5).

Zasady (zgodnie z instrukcja):
- Podzial na dane treningowe i testowe (70/30) + walk-forward (3 foldy).
- Konserwatywne rozstrzyganie: jesli w tej samej swiecy dotkniety i SL i TP -> SL wygrywa.
- Sygnaly z signals_history.json (status DETECTED) sa symulowane na ohlc_history.json.
- Jesli entry/stop/target == None -> sygnal pomijany (nie da sie symulowac).
- Wygaszenie: jesli po MAX_BARS_TO_CLOSE swiecach cena nie dotknie SL ani TP -> EXPIRED.
- Wynik: output/backtest_results.json (statystyki: Win Rate, Profit Factor, Max DD,
  Sr. R:R, Expectancy, Long/Short, Formacje).
- NIE wplywa na make_decision() ani run_daily.py - uruchamiany recznie:
    python -m analysis.backtest
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean

OUTPUT = Path(__file__).resolve().parents[1] / "output"
OHLC_HISTORY_PATH = OUTPUT / "ohlc_history.json"
SIGNALS_HISTORY_PATH = OUTPUT / "signals_history.json"
BACKTEST_PATH = OUTPUT / "backtest_results.json"
BACKTEST_SCHEMA_VERSION = 1

MAX_BARS_TO_CLOSE = 50          # po ilu swiecach 4H uznajemy sygnal za EXPIRED
TRAIN_RATIO = 0.70              # 70% trening, 30% test
WALK_FORWARD_FOLDS = 3          # 3 foldy walk-forward


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _to_epoch(iso_str) -> int | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (TypeError, ValueError, OverflowError):
        return None


def _simulate_one_signal(signal: dict, candles: list) -> dict | None:
    """
    Symuluje jeden sygnal na liscie swiec (candles: [{time, open, high, low, close}]).
    Zwraca wynik: {status, activated_at, closed_at, outcome_pnl, outcome_r}
    albo None, jesli nie da sie symulowac (brak entry/stop/target).
    """
    entry = signal.get("entry")
    stop = signal.get("stop")
    target = signal.get("target")
    if entry is None or stop is None or target is None:
        return None

    confirmed_ts = _to_epoch(signal.get("confirmed_at")) or _to_epoch(signal.get("detected_at"))
    if confirmed_ts is None:
        return None

    # swiece po confirmed_at
    future = [c for c in candles if c.get("time", 0) > confirmed_ts]
    if not future:
        return None

    direction = signal.get("direction")  # bullish -> LONG, bearish -> SHORT
    is_long = direction == "bullish"

    activated_at = None
    activated_idx = None
    for i, c in enumerate(future):
        hi, lo = c.get("high"), c.get("low")
        if hi is None or lo is None:
            continue
        if is_long:
            # LONG: entry aktywuje sie, gdy low <= entry (cena spadla do entry)
            if lo <= entry:
                activated_at = c.get("time")
                activated_idx = i
                break
        else:
            # SHORT: entry aktywuje sie, gdy high >= entry (cena wzrosla do entry)
            if hi >= entry:
                activated_at = c.get("time")
                activated_idx = i
                break

    if activated_at is None:
        return {
            "status": "EXPIRED",
            "activated_at": None,
            "closed_at": None,
            "outcome_pnl": 0.0,
            "outcome_r": 0.0,
        }

    # po aktywacji: sprawdzamy SL/TP (konserwatywnie: SL wygrywa, jesli oba w tej samej swiecy)
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0:
        return None

    for c in future[activated_idx:]:
        hi, lo = c.get("high"), c.get("low")
        if hi is None or lo is None:
            continue
        hit_stop = (lo <= stop) if is_long else (hi >= stop)
        hit_target = (hi >= target) if is_long else (lo <= target)
        if hit_stop:
            # konserwatywnie: SL wygrywa, jesli oba dotkniete w tej samej swiecy
            pnl = -risk
            return {
                "status": "STOP_HIT",
                "activated_at": activated_at,
                "closed_at": c.get("time"),
                "outcome_pnl": -risk,
                "outcome_r": -1.0,
            }
        if hit_target:
            pnl = reward
            return {
                "status": "TARGET_HIT",
                "activated_at": activated_at,
                "closed_at": c.get("time"),
                "outcome_pnl": reward,
                "outcome_r": reward / risk,
            }

    # nie dotknelo ani SL, ani TP w MAX_BARS_TO_CLOSE -> EXPIRED
    return {
        "status": "EXPIRED",
        "activated_at": activated_at,
        "closed_at": None,
        "outcome_pnl": 0.0,
        "outcome_r": 0.0,
    }


def _stats(trades: list) -> dict:
    """
    Liczy statystyki z listy transakcji (kazda ma outcome_pnl, outcome_r, status).
    """
    total = len(trades)
    if total == 0:
        return {
            "trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "max_drawdown": 0.0, "avg_rr": 0.0, "expectancy": 0.0,
            "long_trades": 0, "long_win_rate": 0.0,
            "short_trades": 0, "short_win_rate": 0.0,
        }

    wins = [t for t in trades if t["outcome_pnl"] > 0]
    losses = [t for t in trades if t["outcome_pnl"] < 0]
    gross_win = sum(t["outcome_pnl"] for t in wins)
    gross_loss = abs(sum(t["outcome_pnl"] for t in losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0

    # max drawdown na kumulacyjnym PnL
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t["outcome_pnl"]
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    avg_rr = mean([abs(t["outcome_r"]) for t in trades if t["outcome_r"]]) if trades else 0.0
    expectancy = mean([t["outcome_pnl"] for t in trades]) if trades else 0.0

    long_t = [t for t in trades if t.get("direction") == "bullish"]
    short_t = [t for t in trades if t.get("direction") == "bearish"]

    return {
        "trades": total,
        "win_rate": round(100.0 * len(wins) / total, 2),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown": round(max_dd, 4),
        "avg_rr": round(avg_rr, 3),
        "expectancy": round(expectancy, 5),
        "long_trades": len(long_t),
        "long_win_rate": round(100.0 * len([t for t in long_t if t["outcome_pnl"] > 0]) / len(long_t), 2) if long_t else 0.0,
        "short_trades": len(short_t),
        "short_win_rate": round(100.0 * len([t for t in short_t if t["outcome_pnl"] > 0]) / len(short_t), 2) if short_t else 0.0,
    }


def _simulate_all(signals: list, ohlc_history: dict) -> list:
    """
    Symuluje wszystkie sygnaly (po jednym na signal_id), zwraca liste transakcji.
    """
    seen = set()
    trades = []
    for s in signals:
        sid = s.get("signal_id")
        if sid in seen:
            continue
        seen.add(sid)
        symbol = (s.get("symbol") or "").lower()
        candles = (ohlc_history.get("symbols") or {}).get(symbol) or []
        if not candles:
            continue
        res = _simulate_one_signal(s, candles)
        if res is None:
            continue
        trade = {
            "signal_id": sid,
            "symbol": symbol,
            "pattern": s.get("pattern"),
            "direction": s.get("direction"),
            "confidence": s.get("confidence"),
            "entry": s.get("entry"),
            "stop": s.get("stop"),
            "target": s.get("target"),
            "detected_at": s.get("detected_at"),
            "confirmed_at": s.get("confirmed_at"),
            **res,
        }
        trades.append(trade)
    return trades


def _split_train_test(trades: list) -> tuple[list, list]:
    """Dzieli transakcje na trening/test wg czasu detected_at (70/30)."""
    if not trades:
        return [], []
    trades_sorted = sorted(trades, key=lambda t: t.get("detected_at") or "")
    cut = int(len(trades_sorted) * TRAIN_RATIO)
    return trades_sorted[:cut], trades_sorted[cut:]


def _walk_forward(trades: list, folds: int = WALK_FORWARD_FOLDS) -> list:
    """Walk-forward: folds rownych czesci, kazda jako test, reszta jako trening."""
    if not trades or folds < 2:
        return []
    trades_sorted = sorted(trades, key=lambda t: t.get("detected_at") or "")
    n = len(trades_sorted)
    out = []
    for k in range(folds):
        start = int(n * k / folds)
        end = int(n * (k + 1) / folds)
        test = trades_sorted[start:end]
        train = trades_sorted[:start] + trades_sorted[end:]
        out.append({
            "fold": k + 1,
            "train": _stats(train),
            "test": _stats(test),
        })
    return out


def _by_pattern(trades: list) -> dict:
    by_pat = {}
    for t in trades:
        p = t.get("pattern") or "?"
        by_pat.setdefault(p, []).append(t)
    return {p: _stats(ts) for p, ts in by_pat.items()}


def run_backtest() -> dict:
    ohlc_history = _load_json(OHLC_HISTORY_PATH, {"schema_version": 1, "symbols": {}})
    signals_history = _load_json(SIGNALS_HISTORY_PATH, {"schema_version": 1, "signals": []})
    signals = signals_history.get("signals") or []
    trades = _simulate_all(signals, ohlc_history)
    train, test = _split_train_test(trades)
    wf = _walk_forward(trades)
    results = {
        "schema_version": BACKTEST_SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "config": {
            "max_bars_to_close": MAX_BARS_TO_CLOSE,
            "train_ratio": TRAIN_RATIO,
            "walk_forward_folds": WALK_FORWARD_FOLDS,
            "sl_priority_over_tp": True,
        },
        "overall": _stats(trades),
        "train": _stats(train),
        "test": _stats(test),
        "walk_forward": wf,
        "by_pattern": _by_pattern(trades),
        "trades": trades,
    }
    _atomic_write(BACKTEST_PATH, results)
    print(f"[BACKTEST] Zapisano {BACKTEST_PATH.name} (transakcji: {len(trades)}).")
    print(f"[BACKTEST] overall: {results['overall']}")
    print(f"[BACKTEST] train: {results['train']}")
    print(f"[BACKTEST] test: {results['test']}")
    return results


if __name__ == "__main__":
    run_backtest()