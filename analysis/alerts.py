# analysis/alerts.py
import json
import os
from pathlib import Path
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from analysis.chart_png import render_chart_png

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

def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

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

def send_telegram_photo(text: str, png_path: Path) -> bool:
    """Wysyla wiadomosc + PNG przez sendPhoto (multipart/form-data)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT] Brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID – pomijam")
        print("[ALERT] Tresc:\n", text)
        print(f"[ALERT] PNG: {png_path}")
        return False
    try:
        import uuid
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        with open(png_path, "rb") as f:
            png_data = f.read()
        parts = []
        for k, v in [("chat_id", TELEGRAM_CHAT_ID), ("caption", text), ("parse_mode", "HTML")]:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{png_path.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n".encode() + png_data + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ALERT] Blad Telegram sendPhoto: {e}")
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


def _load_candles(symbol: str) -> list:
    """Wczytuje swiece z output/ohlc.json dla danego symbolu."""
    chart = load_json(OUTPUT_DIR / "ohlc.json") or {}
    payload = ((chart.get("symbols") or {}).get(symbol) or {})
    return payload.get("candles") or []


def _signal_key(item: dict) -> str:
    """Unikalny klucz sygnalu (symbol + candle_close_time + decision)."""
    return f"{item.get('symbol')}|{item.get('candle_close_time') or item.get('timestamp')}|{item.get('decision')}"


def check_and_alert():
    """Wysyla alert TYLKO przy zmianie stanu sygnalu (instrukcja, sekcja 7).

    Zmiana stanu = nowy sygnal (nowy candle_close_time + decision) albo nowy confidence.
    Porownujemy z ostatnim wyslanym stanem w output/alerts_state.json.
    """
    current = load_json(CURRENT_FILE)
    if not current:
        print("[ALERT] Brak status.json")
        return

    state_path = OUTPUT_DIR / "alerts_state.json"
    state = load_json(state_path) or {"sent_keys": []}
    sent_keys = set(state.get("sent_keys", []))

    sent = 0
    new_keys = []
    for item in current:
        sym = item.get("symbol")
        if not sym:
            continue
        if not significant_change(None, item):
            # nie LONG/SHORT albo conf < MIN_CONFIDENCE -> pomijamy
            continue
        key = _signal_key(item)
        if key in sent_keys:
            continue  # juz wyslany ten sam sygnal

        # generujemy PNG
        try:
            candles = _load_candles(sym)
            png_path = render_chart_png(
                sym, candles,
                entry=item.get("entry"), stop=item.get("stop"), target=item.get("target"),
                title=f"{sym.upper()} 4H · {item.get('decision')} · conf {item.get('confidence')}%"
            )
        except Exception as e:
            print(f"[ALERT] Nie udalo sie wygenerowac PNG dla {sym}: {e}")
            png_path = None

        msg = build_message(item)
        if png_path is not None:
            ok = send_telegram_photo(msg, png_path)
        else:
            ok = send_telegram(msg)
        print(f"[ALERT] {sym}: {'wyslano' if ok else 'NIE wyslano'}")
        if ok:
            new_keys.append(key)
            sent += 1

    state["sent_keys"] = list(sent_keys | set(new_keys))[-500:]  # max 500 kluczy
    state["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write(state_path, state)

    print(f"[ALERT] Gotowe. Wyslano {sent} alertow.")