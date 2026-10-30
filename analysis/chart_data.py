# analysis/chart_data.py
from __future__ import annotations
import math
import pandas as pd

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

def build_chart_payload(df, candles, harmonics, levels):
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
        markers.append({"time":t,"position":"belowBar" if bull else "aboveBar","color":"#22c55e" if bull else "#ef4444","shape":"arrowUp" if bull else "arrowDown","text":str(p.get("name","Świeca"))[:32]})
    for p in harmonics or []:
        try: t=_unix_seconds(p.get("time_D") if p.get("status")=="completed" else p.get("time_C"))
        except Exception: continue
        if t not in valid_times: continue
        bull=p.get("direction")=="bullish"
        markers.append({"time":t,"position":"belowBar" if bull else "aboveBar","color":"#60a5fa","shape":"circle","text":str(p.get("name","Harmoniczna"))+(" ✓" if p.get("status")=="completed" else " …")})
    markers.sort(key=lambda x:(x["time"],x["text"]))
    return {"schema_version":1,"candles":rows,"markers":markers,
            "levels":{k:_num((levels or {}).get(k)) for k in ("entry","stop","target")}}
