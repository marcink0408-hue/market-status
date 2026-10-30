# data/fetcher.py
import yfinance as yf
import pandas as pd
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import SYMBOLS, TIMEFRAMES


def fetch_ohlc(symbol_key: str, timeframe: str = "Daily"):
    cfg = SYMBOLS.get(symbol_key)
    if not cfg:
        print(f"Unknown symbol: {symbol_key}")
        return None

    tf = TIMEFRAMES.get(timeframe)
    if not tf:
        print(f"Unknown timeframe: {timeframe}")
        return None

    ticker = cfg["yf"]
    try:
        df = yf.download(
            ticker,
            period=tf["period"],
            interval=tf["interval"],
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if df.empty:
            print(f"No data for {ticker}")
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        df = df[["open", "high", "low", "close"]].dropna().copy()
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "datetime"
        df = df[~df.index.duplicated(keep="last")].sort_index()
        for col in ("open", "high", "low", "close"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        valid = ((df["high"] >= df[["open", "close", "low"]].max(axis=1)) &
                 (df["low"] <= df[["open", "close", "high"]].min(axis=1)))
        df = df.loc[valid]

        if timeframe == "4H":
            df = df.resample("4h", label="left", closed="left").agg({
                "open": "first", "high": "max",
                "low": "min", "close": "last",
            }).dropna()
            if len(df):
                now_utc = pd.Timestamp.now(tz="UTC")
                if df.index[-1] + pd.Timedelta(hours=4) > now_utc:
                    df = df.iloc[:-1]

        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def fetch_all(symbol_key: str):
    result = {}
    for tf in TIMEFRAMES:
        df = fetch_ohlc(symbol_key, tf)
        if df is not None and len(df) > 50:
            result[tf] = df
    return result
