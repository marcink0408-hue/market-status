# run_daily.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from analysis.analyzer import analyze_all
from analysis.alerts import check_and_alert
from analysis.decision_log import append_decisions
import json

def _update_ohlc_history(chart_data, out_dir):
    """Archiwizuje świece OHLC w output/ohlc_history.json (Etap B, instrukcja)."""
    hist_path = out_dir / "ohlc_history.json"
    history = {"schema_version": 1, "timeframe": "4H", "symbols": {}}
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = {"schema_version": 1, "timeframe": "4H", "symbols": {}}

    for symbol, payload in (chart_data.get("symbols") or {}).items():
        new_candles = payload.get("candles") or []
        old_candles = (history.get("symbols") or {}).get(symbol) or []

        # 3. Połącz stare i nowe świece
        merged = list(old_candles) + list(new_candles)

        # 4. Usuń duplikaty po czasie świecy (zostaje ostatnia wersja)
        by_time = {}
        for c in merged:
            t = c.get("time")
            if t is None:
                continue
            by_time[t] = c

        # 5. Posortuj chronologicznie
        history.setdefault("symbols", {})[symbol] = sorted(
            by_time.values(), key=lambda x: x["time"]
        )

    # 6. Zapisz archiwum atomowo
    tmp_hist = hist_path.with_suffix(".json.tmp")
    tmp_hist.write_text(
        json.dumps(history, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp_hist.replace(hist_path)

def main():
    print("=== Market Status – codzienna analiza ===")
    results = analyze_all()
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    chart_data = {
        "schema_version": 1,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeframe": "4H", "symbols": {}
    }
    public_results = []
    for item in results:
        clean = dict(item)
        payload = clean.pop("_chart", None)
        if payload is not None:
            chart_data["symbols"][item.get("symbol")] = payload
        public_results.append(clean)
    chart_path = out_dir / "ohlc.json"
    tmp_chart = chart_path.with_suffix(".json.tmp")
    tmp_chart.write_text(json.dumps(chart_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp_chart.replace(chart_path)
    out = out_dir / "status.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(public_results, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out)
    print(f"Zapisano status i dane wykresów w {out_dir}")

    # --- Etap B: archiwizacja OHLC ---
    _update_ohlc_history(chart_data, out_dir)
    print(f"Zapisano archiwum OHLC w {out_dir / 'ohlc_history.json'}")

    print("\n=== Log decyzji ===")
    append_decisions(results)

    print("\n=== Sprawdzanie alertow ===")
    check_and_alert()
    print("\nGotowe.")


if __name__ == "__main__":
    main()