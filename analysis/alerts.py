# analysis/alerts.py
import json
import os
from pathlib import Path
import urllib.request
import urllib.parse

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MIN_CONFIDENCE = 40

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
CURRENT_FILE = OUTPUT_DIR / "status.json"
PREVIOUS_FILE = OUTPUT_DIR / "status_previous.json"


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def send_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT] Brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID – pomijam")
        print("[ALERT] Tresc:\n", text)
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ALERT] Blad Telegram: {e}")
        return False


def significant_change(old, new) -> bool:
    bias = new.get("decision") or new.get("overall_bias", "NIC")
    conf = new.get("confidence") or new.get("overall_confidence", 0)
    if bias not in ("LONG", "SHORT") or conf < MIN_CONFIDENCE:
        return False
    if old is None:
        return True
    old_bias = old.get("decision") or old.get("overall_bias", "NIC")
    old_conf = old.get("confidence") or old.get("overall_confidence", 0)
    if old_bias != bias:
        return True
    if conf >= old_conf + 15:
        return True
    if old.get("entry") is not None and new.get("entry") is not None and old.get("entry") != new.get("entry"):
        return True
    return False


def build_message(item: dict) -> str:
    sym = item.get("symbol", "?").upper()
    name = item.get("name", "")
    bias = item.get("decision") or item.get("overall_bias", "?")
    conf = item.get("confidence") or item.get("overall_confidence", 0)
    entry = item.get("entry")
    stop = item.get("stop")
    target = item.get("target")
    rr = item.get("rr")
    reasons = item.get("reasons") or []
    emoji = "🟢" if bias == "LONG" else "🔴"
    lines = [f"{emoji} <b>{sym}</b> ({name})", f"Decyzja: <b>{bias}</b> | Pewnosc: {conf}%"]
    if entry is not None:
        lines.append(f"Wejscie: <b>{entry}</b>")
    if stop is not None:
        lines.append(f"Stop: {stop}")
    if target is not None:
        lines.append(f"Cel: {target}" + (f" (R:R 1:{rr})" if rr else ""))
    if reasons:
        lines.append("")
        lines.extend(reasons[:4])
    return "\n".join(lines)


def check_and_alert():
    current = load_json(CURRENT_FILE)
    if not current:
        print("[ALERT] Brak status.json")
        return
    previous = load_json(PREVIOUS_FILE)
    prev_map = {p["symbol"]: p for p in previous} if previous else {}
    sent = 0
    for item in current:
        sym = item.get("symbol")
        if significant_change(prev_map.get(sym), item):
            msg = build_message(item)
            ok = send_telegram(msg)
            print(f"[ALERT] {sym}: {'wyslano' if ok else 'NIE wyslano'}")
            sent += 1
    try:
        PREVIOUS_FILE.write_text(CURRENT_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as e:
        print(f"[ALERT] Nie zapisano previous: {e}")
    print(f"[ALERT] Gotowe. Wyslano {sent} alertow.")


if __name__ == "__main__":
    check_and_alert()
