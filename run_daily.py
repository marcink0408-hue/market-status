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
    out = ROOT / "output" / "status.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Zapisano: {out}")

    print("\n=== Log decyzji ===")
    append_decisions(results)

    print("\n=== Sprawdzanie alertow ===")
    check_and_alert()
    print("\nGotowe.")


if __name__ == "__main__":
    main()