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
DECISIONS_LOG = OUTPUT_DIR / "decisions_log.json"


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


def latest_decisions_map(log_data):
    """Zwraca dict symbol -> najnowsza decyzja (po candle_close_time)."""
    if not log_data:
        return {}
    decisions = log_data.get("decisions", []) if isinstance(log_data, dict) else log_data
    by_sym = {}
    for d in decisions:
        sym = d.get("symbol")
        if not sym:
            continue
        cur = by_sym.get(sym)
        dT = d.get("candle_close_time") or d.get("timestamp") or ""
        cT = (cur.get("candle_close_time") or cur.get("timestamp") or "") if cur else ""
        if not cur or dT > cT:
            by_sym[sym] = d
    return by_sym


def significant_change(old_decision, new_decision) -> bool:
    """Wysyła alert, gdy:
       - nowa decyzja to LONG/SHORT z conf >= MIN_CONFIDENCE
       - brak poprzedniej decyzji LUB zmiana kierunku LUB wzrost conf o >= 15 LUB zmiana entry
    """
    if not new_decision:
        return False
    bias = new_decision.get("decision")
    conf = new_decision.get("confidence") or 0
    if bias not in ("LONG", "SHORT") or conf < MIN_CONFIDENCE:
        return False
    if old_decision is None:
        return True
    old_bias = old_decision.get("decision")
    old_conf = old_decision.get("confidence") or 0
    if old_bias != bias:
        return True
    if conf >= old_conf + 15:
        return True
    old_entry = old_decision.get("entry")
    new_entry = new_decision.get("entry")
    if old_entry is not None and new_entry is not None and old_entry != new_entry:
        return True
    return False


def build_message(item: dict) -> str:
    sym = (item.get("symbol") or "?").upper()
    name = item.get("symbol", "") or ""
    bias = item.get("decision") or "?"
    conf = item.get("confidence") or 0
    entry = item.get("entry")
    stop = item.get("stop")
    target = item.get("target")
    rr = item.get("rr")
    reasons = item.get("reasons") or []
    emoji = "🟢" if bias == "LONG" else "🔴"
    lines = [f"{emoji} <b>{sym}</b>", f"Decyzja: <b>{bias}</b> | Pewnosc: {conf}%"]
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
    log_data = load_json(DECISIONS_LOG)
    if not log_data:
        print("[ALERT] Brak decisions_log.json – nie ma z czym porownac, pomijam")
        return
    prev_map = latest_decisions_map(log_data)
    sent = 0
    for item in current:
        sym = item.get("symbol")
        if not sym:
            continue
        if significant_change(prev_map.get(sym), item):
            msg = build_message(item)
            ok = send_telegram(msg)
            print(f"[ALERT] {sym}: {'wyslano' if ok else 'NIE wyslano'}")
            sent += 1
    print(f"[ALERT] Gotowe. Wyslano {sent} alertow.")


if __name__ == "__main__":
    check_and_alert()