import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import SYMBOLS

output = ROOT / "output"
status = json.loads((output / "status.json").read_text(encoding="utf-8-sig"))
ohlc = json.loads((output / "ohlc.json").read_text(encoding="utf-8-sig"))
assert len(status) == len(SYMBOLS) and len(ohlc["symbols"]) == len(SYMBOLS)
assert ohlc["timeframes"] == ["1H", "4H", "1D"]
counts = {}
patterns = 0
for item in status:
    symbol = item["symbol"]
    assert 0 <= item.get("confidence", 0) <= 100
    frames = ohlc["symbols"][symbol]["timeframes"]
    counts[symbol] = {tf: len(frames[tf]["candles"]) for tf in ("1H", "4H", "1D")}
    for timeframe in ("1H", "4H", "1D"):
        payload = frames[timeframe]
        assert payload["symbol"] == symbol
        assert payload["timeframe"] == timeframe
        assert payload["levels_timeframe"] == timeframe
        assert payload["candles"]
        signal_status = payload.get("signal_status", "NONE")
        assert signal_status in {"NONE", "NO_DATA", "PENDING", "ACTIVE", "STOP_LOSS", "TAKE_PROFIT", "EXPIRED", "INVALIDATED"}
        assert not payload.get("can_enter") or signal_status == "PENDING"
        if signal_status in {"STOP_LOSS", "TAKE_PROFIT", "EXPIRED", "INVALIDATED", "NO_DATA", "NONE"}:
            assert all(payload["levels"].get(key) is None for key in ("entry", "stop", "target"))
        for harmonic in payload["harmonics"]:
            patterns += 1
            assert harmonic["symbol"] == symbol and harmonic["timeframe"] == timeframe
            assert harmonic["lifecycle"] in {"active", "historical", "forming", "target_reached", "invalidated", "expired"}
        for marker in payload["markers"]:
            assert marker["symbol"] == symbol and marker["timeframe"] == timeframe
        atr = item["timeframes"][timeframe]["atr"]
        assert atr is None or (math.isfinite(atr) and atr > 0)
print(counts)
print(f"Validated {patterns} harmonic overlays; schema and identities OK")
