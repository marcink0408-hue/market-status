# analysis/chart_data.py
from __future__ import annotations
import math
import pandas as pd

from analysis.sr_zones import validate_zones

def _unix_seconds(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None: ts = ts.tz_localize("UTC")
    else: ts = ts.tz_convert("UTC")
    return int(ts.timestamp())

def _num(value):
    try:
        v=float(value)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):
        return None

def build_chart_payload(df, candles, harmonics, levels, symbol=None, timeframe="4H", levels_timeframe=None, signal_status=None, can_enter=False, sr_zones=None, current_price=None):
    rows=[]
    if df is not None and not df.empty:
        for stamp,row in df.iterrows():
            vals=[_num(row[k]) for k in ("open","high","low","close")]
            if all(v is not None for v in vals):
                rows.append({"time":_unix_seconds(stamp),"open":vals[0],"high":vals[1],"low":vals[2],"close":vals[3]})
    valid_times={x["time"] for x in rows}
    markers=[]
    for p in candles or []:
        try: t=_unix_seconds(p.get("time"))
        except Exception: continue
        if t not in valid_times: continue
        bull=p.get("direction")=="bullish"
        short_name = str(p.get("name","Świeca")).replace("Engulfing", "Eng.").replace("Shooting Star", "Shooting ★").replace("Morning Star", "Morning ★").replace("Evening Star", "Evening ★")
        markers.append({"time":t,"position":"belowBar" if bull else "aboveBar","color":"#22c55e" if bull else "#ef4444","shape":"arrowUp" if bull else "arrowDown","text":short_name[:24]})
    for p in harmonics or []:
        try: t=_unix_seconds(p.get("time_D") if p.get("status")=="completed" else p.get("time_C"))
        except Exception: continue
        if t not in valid_times: continue
        bull=p.get("direction")=="bullish"
        markers.append({"time":t,"position":"belowBar" if bull else "aboveBar","color":"#60a5fa","shape":"circle","text":str(p.get("name","Harmoniczna"))+(" ✓" if p.get("status")=="completed" else " …")})

    # --- NOWA SEKCJA: linie XABCD dla formacji harmonicznych ---
    harmonic_lines = []
    for p in harmonics or []:
        roles = ["X", "A", "B", "C"]
        if p.get("status") == "completed":
            roles.append("D")
        points = []
        for role in roles:
            try:
                timestamp = _unix_seconds(p.get(f"time_{role}"))
                price = _num(p.get(role))
                if timestamp not in valid_times or price is None:
                    continue
                points.append({
                    "time": timestamp,
                    "value": price,
                    "label": role
                })
            except Exception:
                continue
        if p.get("status") == "forming" and p.get("D_projected") is not None and points:
            projected = _num(p.get("D_projected"))
            if projected is not None:
                points.append({"time": rows[-1]["time"], "value": projected, "label": "D?"})
        if len(points) >= 4:
            harmonic_lines.append({
                "name": p.get("name", "Harmoniczna"),
                "symbol": symbol or p.get("symbol"),
                "timeframe": timeframe,
                "created_at": p.get("created_at") or p.get("time_D") or p.get("time_C"),
                "lifecycle": p.get("lifecycle"),
                "direction": p.get("direction"),
                "status": p.get("status"),
                "points": points
            })

    markers.sort(key=lambda x:(x["time"],x["text"]))

    # --- ZMIENIONY RETURN: dodajemy "harmonics" i podnosimy schema_version ---
    zones = validate_zones(sr_zones or []) if sr_zones else []
    return {
        "schema_version": 3,
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": rows,
        "markers": [{**marker, "symbol": symbol, "timeframe": timeframe} for marker in markers],
        "harmonics": harmonic_lines,
        "levels_timeframe": levels_timeframe or timeframe,
        "signal_status": signal_status or "NONE",
        "can_enter": bool(can_enter),
        "levels": {k: _num((levels or {}).get(k)) for k in ("entry","stop","target")},
        "sr_zones": zones,
        "sr_zones_timeframe": timeframe,
        "sr_zones_current_price": _num(current_price),
    }
