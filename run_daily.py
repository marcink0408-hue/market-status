# run_daily.py
from analysis.analyzer import analyze_all
from analysis.alerts import check_and_alert
from pathlib import Path
import json

def main():
    print("=== Market Status – codzienna analiza ===")
    results = analyze_all()
    out = Path(__file__).parent / "output" / "status.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Zapisano: {out}")
    print("\n=== Sprawdzanie alertow ===")
    check_and_alert()
    print("\nGotowe.")

if __name__ == "__main__":
    main()
