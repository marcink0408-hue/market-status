# data/fetcher.py
import yfinance as yf
import pandas as pd
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import SYMBOLS, TIMEFRAMES


def _clean_ohlc(df: pd.DataFrame) -> pd.DataFrame:
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
    return df.loc[valid]


def drop_incomplete_bar(df: pd.DataFrame, hours: int, now=None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    now_utc = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now_utc.tzinfo is None:
        now_utc = now_utc.tz_localize("UTC")
    else:
        now_utc = now_utc.tz_convert("UTC")
    if df.index[-1] + pd.Timedelta(hours=hours) > now_utc:
        return df.iloc[:-1]
    return df


def resample_ohlc(df: pd.DataFrame, hours: int, now=None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close"])
    result = df.resample(
        f"{hours}h", label="left", closed="left", origin="epoch"
    ).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return drop_incomplete_bar(result, hours, now=now)


def build_daily_from_hourly(df: pd.DataFrame, timezone="UTC", now=None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close"])
    local = df.copy()
    local.index = local.index.tz_convert(timezone)
    session_day = local.index.normalize()
    result = local.groupby(session_day).agg({
        "open": "first", "high": "max", "low": "min", "close": "last",
    }).dropna()
    now_utc = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now_utc.tzinfo is None:
        now_utc = now_utc.tz_localize("UTC")
    current_session = now_utc.tz_convert(timezone).normalize()
    result = result.loc[result.index < current_session]
    result.index = result.index.tz_convert("UTC")
    result.index.name = "datetime"
    return result


def _download(symbol_key: str, timeframe: str):
    cfg = SYMBOLS.get(symbol_key)
    tf = TIMEFRAMES.get(timeframe)
    if not cfg or not tf:
        return None
    ticker = cfg["yf"]
    try:
        df = yf.download(
            ticker, period=tf["period"], interval=tf["interval"],
            progress=False, auto_adjust=True, threads=False,
        )
        if df.empty:
            print(f"No data for {ticker}")
            return None
        df = _clean_ohlc(df)
        hours = 24 if tf["interval"] == "1d" else 1
        return drop_incomplete_bar(df, hours)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def fetch_ohlc(symbol_key: str, timeframe: str = "Daily"):
    if symbol_key not in SYMBOLS or timeframe not in TIMEFRAMES:
        print(f"Unknown symbol or timeframe: {symbol_key} / {timeframe}")
        return None
    if timeframe == "4H":
        hourly = _download(symbol_key, "1H")
        return resample_ohlc(hourly, 4)
    daily = _download(symbol_key, timeframe)
    if timeframe == "Daily" and (daily is None or len(daily) <= 50):
        hourly = _download(symbol_key, "1H")
        daily = build_daily_from_hourly(
            hourly, SYMBOLS[symbol_key].get("daily_timezone", "UTC")
        )
    return daily


def fetch_all(symbol_key: str):
    result = {}
    hourly = _download(symbol_key, "1H")
    if hourly is not None and len(hourly) > 50:
        result["1H"] = hourly
        four_hour = resample_ohlc(hourly, 4)
        if len(four_hour) > 50:
            result["4H"] = four_hour
    daily = _download(symbol_key, "Daily")
    if (daily is None or len(daily) <= 50) and hourly is not None:
        daily = build_daily_from_hourly(
            hourly, SYMBOLS[symbol_key].get("daily_timezone", "UTC")
        )
    if daily is not None and len(daily) > 50:
        result["Daily"] = daily
    return result
