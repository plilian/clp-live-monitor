from __future__ import annotations

import time
from typing import Any, Dict, Optional

import pandas as pd
import requests

FAPI_BASE = "https://fapi.binance.com"


class BinanceAPIError(RuntimeError):
    pass


def _get(url: str, params: Dict[str, Any], timeout: int = 15, retries: int = 3) -> Any:
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code != 200:
                raise BinanceAPIError(f"HTTP {r.status_code}: {r.text[:250]}")
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (i + 1))
    raise BinanceAPIError(f"Binance request failed after retries: {last_err}")


def fetch_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    url = f"{FAPI_BASE}/fapi/v1/klines"
    data = _get(url, {"symbol": symbol, "interval": interval, "limit": limit})

    cols = [
        "open_time", "Open", "High", "Low", "Close", "Volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]
    df = pd.DataFrame(data, columns=cols)

    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df[["open_time", "Open", "High", "Low", "Close", "Volume"]]


def fetch_funding_rate(symbol: str, limit: int = 200) -> pd.DataFrame:
    url = f"{FAPI_BASE}/fapi/v1/fundingRate"
    data = _get(url, {"symbol": symbol, "limit": limit})

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["time", "fundingRate"])

    df["time"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df = df.sort_values("time").reset_index(drop=True)
    return df[["time", "fundingRate"]]


def fetch_open_interest_hist(symbol: str, period: str, limit: int = 200) -> pd.DataFrame:
    url = f"{FAPI_BASE}/futures/data/openInterestHist"
    data = _get(url, {"symbol": symbol, "period": period, "limit": limit})

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["time", "openInterest"])

    df["time"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["openInterest"] = pd.to_numeric(df["sumOpenInterest"], errors="coerce")
    df = df.sort_values("time").reset_index(drop=True)
    return df[["time", "openInterest"]]


def build_merged_frame(symbol: str, interval: str, lookback_limit: int = 500) -> pd.DataFrame:

    price = fetch_klines(symbol=symbol, interval=interval, limit=lookback_limit)
    oi = fetch_open_interest_hist(symbol=symbol, period=interval, limit=min(200, lookback_limit))
    fr = fetch_funding_rate(symbol=symbol, limit=200)

    df = price.rename(columns={"open_time": "time"}).copy()

    df = pd.merge_asof(
        df.sort_values("time"),
        fr.sort_values("time"),
        on="time",
        direction="backward",
    )
    df = pd.merge_asof(
        df.sort_values("time"),
        oi.sort_values("time"),
        on="time",
        direction="backward",
    )

    return df