# run_daily.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from analysis.analyzer import analyze_all
from analysis.alerts import check_and_alert
from analysis.decision_log import append_decisions
import json


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

    print("\n=== Log decyzji ===")
    append_decisions(results)

    print("\n=== Sprawdzanie alertow ===")
    check_and_alert()
    print("\nGotowe.")


if __name__ == "__main__":
    main()